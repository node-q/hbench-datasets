import email.message
import io
import json
import unittest
import urllib.error
import urllib.parse

import images_lock
import pin_images

DIGEST = "sha256:" + "0123456789abcdef" * 4
DOCKER_HUB_CHALLENGE = (
    'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",'
    'scope="repository:alexgshaw/build-pmars:pull"'
)


def headers(values):
    message = email.message.Message()
    for name, value in values.items():
        message[name] = value
    return message


class FakeResponse:
    def __init__(self, response_headers=None, body=b""):
        self.headers = headers(response_headers or {})
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class FakeRegistry:
    def __init__(self, digests, failures=()):
        self.digests = digests
        self.failures = list(failures)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        url = urllib.parse.urlsplit(request.full_url)
        if url.netloc == "auth.docker.io":
            query = urllib.parse.parse_qs(url.query)
            repository = query["scope"][0].split(":")[1]
            return FakeResponse(body=json.dumps({"token": f"token-for-{repository}"}).encode())
        self.assertHeadForManifests(request)
        repository, tag = url.path.removeprefix("/v2/").split("/manifests/")
        if self.failures:
            raise self.failures.pop(0)
        if request.get_header("Authorization") != f"Bearer token-for-{repository}":
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                headers(
                    {"WWW-Authenticate": DOCKER_HUB_CHALLENGE.replace("alexgshaw/build-pmars", repository)}
                ),
                io.BytesIO(),
            )
        digest = self.digests.get(f"{repository}:{tag}")
        if digest is None:
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", headers({}), io.BytesIO())
        return FakeResponse({"Docker-Content-Digest": digest})

    @staticmethod
    def assertHeadForManifests(request):
        assert request.get_method() == "HEAD", request.get_method()
        accepted = [media_type.strip() for media_type in request.get_header("Accept").split(",")]
        assert accepted == list(pin_images.MANIFEST_MEDIA_TYPES), accepted


def http_error(code, reason):
    return urllib.error.HTTPError("https://registry-1.docker.io/v2/", code, reason, headers({}), io.BytesIO())


class RegistryLocationTest(unittest.TestCase):
    def test_docker_hub_references_resolve_to_registry_1_with_library_for_official_images(self):
        self.assertEqual(
            pin_images.registry_location("alexgshaw/build-pmars:20251031"),
            ("registry-1.docker.io", "alexgshaw/build-pmars", "20251031"),
        )
        self.assertEqual(
            pin_images.registry_location("busybox:1.37"), ("registry-1.docker.io", "library/busybox", "1.37")
        )
        self.assertEqual(
            pin_images.registry_location("docker.io/swebench/sweb.eval.x86_64.django:latest"),
            ("registry-1.docker.io", "swebench/sweb.eval.x86_64.django", "latest"),
        )

    def test_other_registries_keep_their_host_and_port(self):
        self.assertEqual(pin_images.registry_location("ghcr.io/org/image:v1"), ("ghcr.io", "org/image", "v1"))
        self.assertEqual(
            pin_images.registry_location("localhost:5000/image:v1"), ("localhost:5000", "image", "v1")
        )

    def test_refuses_a_reference_without_a_tag(self):
        for reference in ("alexgshaw/build-pmars", f"alexgshaw/build-pmars@{DIGEST}"):
            with self.subTest(reference=reference), self.assertRaises(images_lock.LockError):
                pin_images.registry_location(reference)


class ManifestResolverTest(unittest.TestCase):
    def resolver(self, registry):
        self.sleeps = []
        return pin_images.ManifestResolver(
            open_url=registry, sleep=self.sleeps.append, log=lambda message: None
        )

    def test_resolves_a_tag_with_a_head_request_after_the_anonymous_token_flow(self):
        registry = FakeRegistry({"alexgshaw/build-pmars:20251031": DIGEST})
        self.assertEqual(self.resolver(registry).digest("alexgshaw/build-pmars:20251031"), DIGEST)
        methods_and_hosts = [
            (request.get_method(), urllib.parse.urlsplit(request.full_url).netloc)
            for request in registry.requests
        ]
        self.assertEqual(
            methods_and_hosts,
            [("HEAD", "registry-1.docker.io"), ("GET", "auth.docker.io"), ("HEAD", "registry-1.docker.io")],
        )
        token_query = urllib.parse.parse_qs(urllib.parse.urlsplit(registry.requests[1].full_url).query)
        self.assertEqual(
            token_query,
            {"service": ["registry.docker.io"], "scope": ["repository:alexgshaw/build-pmars:pull"]},
        )

    def test_retries_rate_limits_and_server_errors_with_exponential_backoff(self):
        registry = FakeRegistry(
            {"alexgshaw/build-pmars:20251031": DIGEST},
            failures=[http_error(429, "Too Many Requests"), http_error(503, "Service Unavailable")],
        )
        self.assertEqual(self.resolver(registry).digest("alexgshaw/build-pmars:20251031"), DIGEST)
        self.assertEqual(self.sleeps, [30, 60])

    def test_refuses_a_missing_tag_or_a_missing_digest_header(self):
        resolver = self.resolver(FakeRegistry({}))
        with self.assertRaisesRegex(pin_images.PinError, "alexgshaw/build-pmars:20251031 does not exist"):
            resolver.digest("alexgshaw/build-pmars:20251031")
        resolver = self.resolver(FakeRegistry({"alexgshaw/build-pmars:20251031": "md5:abc"}))
        with self.assertRaisesRegex(pin_images.PinError, "reported digest 'md5:abc', not a sha256 digest"):
            resolver.digest("alexgshaw/build-pmars:20251031")
        self.assertEqual(self.sleeps, [])


class PinnedUpstreamLockTest(unittest.TestCase):
    def test_writes_a_pinned_upstream_entry_per_task(self):
        registry = FakeRegistry(
            {
                "alexgshaw/build-pmars:20251031": DIGEST,
                "alexgshaw/adaptive-rejection-sampler:20251031": DIGEST,
            }
        )
        resolver = pin_images.ManifestResolver(
            open_url=registry, sleep=lambda seconds: None, log=lambda message: None
        )
        declared_images = {
            "build-pmars": "alexgshaw/build-pmars:20251031",
            "adaptive-rejection-sampler": "alexgshaw/adaptive-rejection-sampler:20251031",
        }
        lock = pin_images.pinned_upstream_lock(declared_images, resolver, "terminal-bench")
        self.assertEqual(list(lock), ["adaptive-rejection-sampler", "build-pmars"])
        self.assertEqual(
            lock["build-pmars"],
            {
                "source": "alexgshaw/build-pmars:20251031",
                "source_digest": DIGEST,
                "pinned": f"alexgshaw/build-pmars@{DIGEST}",
            },
        )
        self.assertEqual(
            images_lock.lock_problems(
                lock, "terminal-bench", "pinned-upstream", 2, "alexgshaw/{task}:20251031"
            ),
            [],
        )

    def test_reports_every_task_it_cannot_pin(self):
        resolver = pin_images.ManifestResolver(
            open_url=FakeRegistry({}), sleep=lambda seconds: None, log=lambda message: None
        )
        with self.assertRaises(pin_images.PinError) as raised:
            pin_images.pinned_upstream_lock(
                {"a": "alexgshaw/a:1", "b": "alexgshaw/b"}, resolver, "terminal-bench"
            )
        self.assertIn("a: registry-1.docker.io/alexgshaw/a:1 does not exist", str(raised.exception))
        self.assertIn("b: 'alexgshaw/b' names no tag", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
