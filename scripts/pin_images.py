"""Pin each task's declared upstream image by its digest and write images.lock.json for a pinned-upstream version.

Usage: pin_images.py datasets/<name>/<version>/source.yaml CHECKOUT_DIRECTORY --output images.lock.json

Fetches the source at its pinned commit into CHECKOUT_DIRECTORY and reads each task's docker_image. Each
tag is resolved with a registry HEAD request for its manifest, through the registry's anonymous token
flow; the digest is the one the registry reports for the index or manifest the tag names. Docker Hub
does not count HEAD requests against its pull limit. Rate-limited and transient failures are retried
with exponential backoff.
"""

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from fetch_source import SourceError, fetch_declared_images
from images_lock import DIGEST_PATTERN, LockError, dump_images_lock, entry_problems, source_tag, upstream_pin
from source_descriptor import load_descriptor

MANIFEST_MEDIA_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)
DOCKER_HUB_HOSTS = ("docker.io", "index.docker.io", "registry-1.docker.io")
DOCKER_HUB_REGISTRY = "registry-1.docker.io"
DOCKER_HUB_OFFICIAL_NAMESPACE = "library"
BEARER_CHALLENGE_PARAMETER = re.compile(r'(\w+)="([^"]*)"')
RETRIED_STATUS_CODES = (429, 500, 502, 503, 504)
DEFAULT_ATTEMPTS = 6
DEFAULT_FIRST_BACKOFF_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 60


class PinError(RuntimeError):
    pass


def registry_location(reference):
    source_tag(reference)
    first_component, _, remainder = reference.partition("/")
    if remainder and ("." in first_component or ":" in first_component or first_component == "localhost"):
        registry, path = first_component, remainder
    else:
        registry, path = DOCKER_HUB_HOSTS[0], reference
    repository, tag = path.rsplit(":", 1)
    if registry in DOCKER_HUB_HOSTS:
        registry = DOCKER_HUB_REGISTRY
        if "/" not in repository:
            repository = f"{DOCKER_HUB_OFFICIAL_NAMESPACE}/{repository}"
    return registry, repository, tag


def bearer_challenge(header):
    if not header or not header.lower().startswith("bearer "):
        return None
    return dict(BEARER_CHALLENGE_PARAMETER.findall(header))


class ManifestResolver:
    def __init__(
        self,
        open_url=urllib.request.urlopen,
        sleep=time.sleep,
        log=print,
        attempts=DEFAULT_ATTEMPTS,
        first_backoff_seconds=DEFAULT_FIRST_BACKOFF_SECONDS,
    ):
        self.open_url = open_url
        self.sleep = sleep
        self.log = log
        self.attempts = attempts
        self.first_backoff_seconds = first_backoff_seconds
        self.tokens = {}

    def anonymous_token(self, challenge):
        if "realm" not in challenge:
            raise PinError(f"the registry's Bearer challenge names no realm: {challenge}")
        query = urllib.parse.urlencode(
            {key: challenge[key] for key in ("service", "scope") if key in challenge}
        )
        token_url = f"{challenge['realm']}?{query}" if query else challenge["realm"]
        try:
            with self.open_url(
                urllib.request.Request(token_url), timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                answer = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError) as error:
            raise PinError(f"no anonymous token from {challenge['realm']}: {error}") from None
        token = answer.get("token") or answer.get("access_token")
        if not token:
            raise PinError(f"{challenge['realm']} gave no token")
        return token

    def head_manifest(self, registry, repository, tag):
        url = f"https://{registry}/v2/{repository}/manifests/{tag}"
        attempt = 1
        token_requested = False
        while True:
            headers = {"Accept": ", ".join(MANIFEST_MEDIA_TYPES)}
            token = self.tokens.get((registry, repository))
            if token:
                headers["Authorization"] = f"Bearer {token}"
            request = urllib.request.Request(url, method="HEAD", headers=headers)
            try:
                with self.open_url(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    return response.headers
            except urllib.error.HTTPError as error:
                challenge = bearer_challenge(error.headers.get("WWW-Authenticate"))
                if error.code == 401 and challenge is not None and not token_requested:
                    self.tokens[(registry, repository)] = self.anonymous_token(challenge)
                    token_requested = True
                    continue
                if error.code == 404:
                    raise PinError(f"{registry}/{repository}:{tag} does not exist") from None
                if error.code not in RETRIED_STATUS_CODES or attempt >= self.attempts:
                    raise PinError(f"HEAD {url} answered {error.code} {error.reason}") from None
                failure = f"{error.code} {error.reason}"
            except urllib.error.URLError as error:
                if attempt >= self.attempts:
                    raise PinError(f"HEAD {url} failed: {error.reason}") from None
                failure = str(error.reason)
            delay = self.first_backoff_seconds * 2 ** (attempt - 1)
            attempt += 1
            self.log(
                f"HEAD {url} failed ({failure}); retrying in {delay} s, attempt {attempt} of {self.attempts}"
            )
            self.sleep(delay)

    def digest(self, reference):
        registry, repository, tag = registry_location(reference)
        headers = self.head_manifest(registry, repository, tag)
        digest = headers.get("Docker-Content-Digest")
        if not digest or not DIGEST_PATTERN.match(digest):
            raise PinError(f"{reference}: the registry reported digest {digest!r}, not a sha256 digest")
        return digest


def pinned_upstream_lock(declared_images, resolver, dataset):
    lock = {}
    problems = []
    for task in sorted(declared_images):
        source = declared_images[task]
        try:
            source_digest = resolver.digest(source)
        except (LockError, PinError) as error:
            problems.append(f"{task}: {error}")
            continue
        lock[task] = {
            "source": source,
            "source_digest": source_digest,
            "pinned": upstream_pin(source, source_digest),
        }
        problems += entry_problems(task, lock[task], dataset, "pinned-upstream")
    if problems:
        raise PinError("cannot pin every task's image:\n  " + "\n  ".join(problems))
    return lock


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Pin a dataset version's upstream images by digest.")
    parser.add_argument("descriptor", type=pathlib.Path)
    parser.add_argument("checkout_directory", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    descriptor = load_descriptor(options.descriptor)
    label = f"{descriptor['name']}@{descriptor['version']}"
    try:
        declared_images = fetch_declared_images(descriptor, options.checkout_directory)
        lock = pinned_upstream_lock(declared_images, ManifestResolver(), descriptor["name"])
    except (SourceError, PinError) as error:
        print(f"pin_images.py: {label}: {error}", file=sys.stderr)
        return 1
    options.output.write_text(dump_images_lock(lock), encoding="utf-8")
    print(f"{label}: {len(lock)} upstream images pinned by digest in {options.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
