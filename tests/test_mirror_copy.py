import subprocess
import unittest

import images_lock
import mirror_copy

MIRROR_REPOSITORY = "ghcr.io/node-q/hbench-envs/terminal-bench"
IDENTITY = "^https://github.com/node-q/hbench-datasets/.github/workflows/mirror-images.yml@"
ISSUER = "https://token.actions.githubusercontent.com"
SOURCE_DIGEST = "sha256:" + "1" * 64
OTHER_DIGEST = "sha256:" + "2" * 64
RATE_LIMITED = (
    "2026/10/22 HEAD request failed, falling back on GET: HEAD https://index.docker.io/v2/alexgshaw/build-pmars/"
    "manifests/20251031: unexpected status code 429 Too Many Requests (HEAD responses have no body)\n"
    "Error: GET https://index.docker.io/v2/alexgshaw/build-pmars/manifests/20251031: TOOMANYREQUESTS: You have "
    "reached your unauthenticated pull rate limit."
)


def image(task_name):
    return {
        "task": task_name,
        "source": f"alexgshaw/{task_name}:20251031",
        "mirror_tag": f"{task_name}-20251031",
    }


class FakeRegistries:
    def __init__(self, sources):
        self.sources = dict(sources)
        self.mirror_tags = {}
        self.signed = set()
        self.package_exists = False
        self.scripted_failures = {}
        self.commands = []

    def fail(self, reference, stderr, times):
        self.scripted_failures[reference] = [stderr] * times

    def __call__(self, command, capture_output, text):
        self.commands.append(command)
        reference = command[2] if command[:2] != ["crane", "copy"] else command[3]
        scripted = self.scripted_failures.get(reference)
        if scripted:
            return subprocess.CompletedProcess(command, 1, "", scripted.pop(0))
        handler = {
            ("crane", "digest"): self.crane_digest,
            ("crane", "copy"): self.crane_copy,
            ("cosign", "verify"): self.cosign_verify,
            ("cosign", "sign"): self.cosign_sign,
            ("gh", "api"): self.gh_api,
        }[tuple(command[:2])]
        returncode, stdout, stderr = handler(command)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    def crane_digest(self, command):
        reference = command[2]
        digest = self.sources.get(reference) or self.mirror_tags.get(reference)
        if digest:
            return 0, digest + "\n", ""
        if reference.startswith(MIRROR_REPOSITORY) and not self.package_exists:
            return (
                1,
                "",
                "Error: GET https://ghcr.io/token: DENIED: requested access to the resource is denied",
            )
        if reference.startswith(MIRROR_REPOSITORY):
            return 1, "", "Error: GET https://ghcr.io/v2/manifests/x: MANIFEST_UNKNOWN: manifest unknown"
        return 1, "", "Error: GET https://index.docker.io/token: UNAUTHORIZED: authentication required"

    def crane_copy(self, command):
        source, destination = command[3], command[4]
        if destination in self.mirror_tags:
            return 1, "", f"Error: refusing to clobber existing tag {destination}"
        self.mirror_tags[destination] = source.split("@", 1)[1]
        self.package_exists = True
        return 0, "", ""

    def cosign_verify(self, command):
        if command[2] in self.signed:
            return 0, "[]", ""
        return 1, "", "Error: no signatures found"

    def cosign_sign(self, command):
        self.signed.add(command[3])
        return 0, "", ""

    def gh_api(self, command):
        if self.package_exists:
            return 0, "{}", ""
        return 1, "", "gh: Not Found (HTTP 404)"

    def ran(self, *prefix):
        return [command for command in self.commands if command[: len(prefix)] == list(prefix)]


class MirrorImageTest(unittest.TestCase):
    def setUp(self):
        self.registries = FakeRegistries({"alexgshaw/build-pmars:20251031": SOURCE_DIGEST})
        self.sleeps = []
        self.registry = mirror_copy.Registry(
            run=self.registries, sleep=self.sleeps.append, log=lambda message: None, first_backoff_seconds=30
        )

    def mirror(self, task_name="build-pmars"):
        return mirror_copy.mirror_image(self.registry, image(task_name), MIRROR_REPOSITORY, IDENTITY, ISSUER)

    def test_copies_an_absent_image_by_digest_then_verifies_and_signs_it(self):
        entry, copy_outcome, signature_outcome = self.mirror()
        self.assertEqual(
            entry,
            {
                "source": "alexgshaw/build-pmars:20251031",
                "source_digest": SOURCE_DIGEST,
                "pinned": f"{MIRROR_REPOSITORY}@{SOURCE_DIGEST}",
                "mirror_tag": "build-pmars-20251031",
            },
        )
        self.assertEqual((copy_outcome, signature_outcome), ("copied", "signed"))
        self.assertEqual(
            self.registries.ran("crane", "copy"),
            [
                [
                    "crane",
                    "copy",
                    "--no-clobber",
                    f"alexgshaw/build-pmars@{SOURCE_DIGEST}",
                    f"{MIRROR_REPOSITORY}:build-pmars-20251031",
                ]
            ],
        )
        self.assertEqual(
            self.registries.ran("cosign", "sign"), [["cosign", "sign", "--yes", entry["pinned"]]]
        )
        self.assertEqual(
            images_lock.entry_problems("build-pmars", entry, "terminal-bench", "pinned-mirror"), []
        )

    def test_a_rerun_copies_and_signs_nothing_again(self):
        first_entry, _, _ = self.mirror()
        self.registries.commands.clear()
        entry, copy_outcome, signature_outcome = self.mirror()
        self.assertEqual(entry, first_entry)
        self.assertEqual((copy_outcome, signature_outcome), ("already mirrored", "already signed"))
        self.assertEqual(self.registries.ran("crane", "copy"), [])
        self.assertEqual(self.registries.ran("cosign", "sign"), [])

    def test_never_overwrites_a_mirror_tag_that_holds_another_digest(self):
        self.registries.package_exists = True
        self.registries.mirror_tags[f"{MIRROR_REPOSITORY}:build-pmars-20251031"] = OTHER_DIGEST
        with self.assertRaises(mirror_copy.MirrorError) as raised:
            self.mirror()
        self.assertEqual(raised.exception.title, "Mirror tag holds another image")
        self.assertIn(
            f"is {OTHER_DIGEST}, but alexgshaw/build-pmars:20251031 is {SOURCE_DIGEST}", str(raised.exception)
        )
        self.assertEqual(self.registries.ran("crane", "copy"), [])
        self.assertEqual(self.registries.ran("cosign", "sign"), [])

    def test_retries_a_rate_limited_request_with_exponential_backoff(self):
        self.registries.fail("alexgshaw/build-pmars:20251031", RATE_LIMITED, times=3)
        entry, _, _ = self.mirror()
        self.assertEqual(entry["source_digest"], SOURCE_DIGEST)
        self.assertEqual(self.sleeps, [30, 60, 120])

    def test_gives_up_once_every_attempt_is_rate_limited(self):
        self.registries.fail("alexgshaw/build-pmars:20251031", RATE_LIMITED, times=6)
        with self.assertRaises(mirror_copy.MirrorError) as raised:
            self.mirror()
        self.assertEqual(raised.exception.title, "Rate limited")
        self.assertEqual(self.sleeps, [30, 60, 120, 240, 480])
        self.assertEqual(self.registries.ran("crane", "copy"), [])

    def test_does_not_retry_a_failure_that_is_not_transient(self):
        with self.assertRaises(mirror_copy.MirrorError) as raised:
            self.mirror("not-on-docker-hub")
        self.assertEqual(raised.exception.title, "Cannot resolve")
        self.assertEqual(self.sleeps, [])

    def test_a_denied_tag_check_means_absent_only_while_the_package_does_not_exist(self):
        self.mirror()
        self.assertEqual(len(self.registries.ran("gh", "api")), 1)
        self.registries.fail(f"{MIRROR_REPOSITORY}:build-pmars-20251031", "Error: DENIED: denied", times=1)
        with self.assertRaisesRegex(mirror_copy.MirrorError, "crane digest .* failed: Error: DENIED"):
            self.mirror()


class MirrorShardTest(unittest.TestCase):
    def test_mirrors_the_rest_of_the_shard_when_one_image_fails_and_reports_each(self):
        registries = FakeRegistries(
            {
                f"alexgshaw/{name}:20251031": SOURCE_DIGEST
                for name in ("adaptive-rejection-sampler", "build-pmars")
            }
        )
        registry = mirror_copy.Registry(run=registries, sleep=lambda seconds: None, log=lambda message: None)
        plan = {
            "dataset": "terminal-bench",
            "version": "2.0",
            "mirror_repository": MIRROR_REPOSITORY,
            "shards": [
                {"shard": 1, "images": [image("adaptive-rejection-sampler"), image("missing-task")]},
                {"shard": 2, "images": [image("build-pmars")]},
            ],
        }
        lock, outcomes, failures = mirror_copy.mirror_shard(
            registry, plan, 1, IDENTITY, ISSUER, log=lambda message: None
        )
        self.assertEqual(list(lock), ["adaptive-rejection-sampler"])
        self.assertEqual([task for task, _ in failures], ["missing-task"])
        summary = mirror_copy.summary_markdown(plan, 1, outcomes)
        self.assertIn(
            "## Shard 1: terminal-bench@2.0 to `ghcr.io/node-q/hbench-envs/terminal-bench`", summary
        )
        self.assertIn(
            "| adaptive-rejection-sampler | `alexgshaw/adaptive-rejection-sampler:20251031` "
            f"| `{SOURCE_DIGEST}` | copied | signed |",
            summary,
        )
        self.assertIn("| missing-task | `alexgshaw/missing-task:20251031` | - | failed |", summary)
        with self.assertRaisesRegex(mirror_copy.MirrorError, "the plan has no shard 3"):
            mirror_copy.mirror_shard(registry, plan, 3, IDENTITY, ISSUER, log=lambda message: None)


if __name__ == "__main__":
    unittest.main()
