"""Copy one shard of a mirror plan with crane, registry to registry; verify and sign each image; write its lock.

Usage: mirror_copy.py --plan mirror-plan.json --shard N --output images-lock-shard-N.json
                      --certificate-identity-regexp REGEXP --certificate-oidc-issuer URL
                      [--summary FILE]

A mirror tag that already holds the source's digest is left as it is; one that holds another digest is
never overwritten. Rate-limited and transient registry failures are retried with exponential backoff.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse

from images_lock import DIGEST_PATTERN, dump_images_lock, repository_of

RATE_LIMITED_PATTERN = re.compile(r"toomanyrequests|too many requests|\b429\b", re.IGNORECASE)
TRANSIENT_FAILURE_PATTERN = re.compile(
    r"\b50[234]\b|connection reset by peer|unexpected EOF|i/o timeout|TLS handshake timeout", re.IGNORECASE
)
NOT_FOUND_PATTERN = re.compile(r"MANIFEST_UNKNOWN|NAME_UNKNOWN|\b404 Not Found\b")
DENIED_PATTERN = re.compile(r"\bDENIED\b|\bUNAUTHORIZED\b|\b40[13]\b", re.IGNORECASE)
DEFAULT_ATTEMPTS = 6
DEFAULT_FIRST_BACKOFF_SECONDS = 30
LOGGED_FAILURE_LINES = 20


class MirrorError(RuntimeError):
    def __init__(self, title, message):
        super().__init__(message)
        self.title = title


def error_lines(output):
    lines = [line for line in output.splitlines() if line.startswith("Error:")]
    return "\n".join(lines) if lines else output


def last_line(output):
    lines = [line for line in output.strip().splitlines() if line.strip()]
    return lines[-1] if lines else "no output"


class Registry:
    def __init__(
        self,
        run=subprocess.run,
        sleep=time.sleep,
        log=print,
        attempts=DEFAULT_ATTEMPTS,
        first_backoff_seconds=DEFAULT_FIRST_BACKOFF_SECONDS,
    ):
        self.run = run
        self.sleep = sleep
        self.log = log
        self.attempts = attempts
        self.first_backoff_seconds = first_backoff_seconds
        self.packages_known_to_exist = set()

    def run_with_retries(self, command):
        attempt = 1
        while True:
            completed = self.run(command, capture_output=True, text=True)
            if completed.returncode == 0:
                return completed
            failure = error_lines(completed.stderr + completed.stdout)
            retryable = RATE_LIMITED_PATTERN.search(failure) or TRANSIENT_FAILURE_PATTERN.search(failure)
            if not retryable or attempt >= self.attempts:
                failure_lines = (completed.stderr + completed.stdout).strip().splitlines()
                self.log("\n".join([f"{' '.join(command)} failed:", *failure_lines[-LOGGED_FAILURE_LINES:]]))
                return completed
            delay = self.first_backoff_seconds * 2 ** (attempt - 1)
            attempt += 1
            self.log(
                f"{' '.join(command[:2])} failed ({last_line(failure)}); "
                f"retrying in {delay} s, attempt {attempt} of {self.attempts}"
            )
            self.sleep(delay)

    def digest(self, reference, absent_while_package_missing=False):
        completed = self.run_with_retries(["crane", "digest", reference])
        if completed.returncode == 0:
            digest = completed.stdout.strip()
            if not DIGEST_PATTERN.match(digest):
                raise MirrorError(
                    "Bad digest", f"crane digest {reference} printed {digest!r}, not a sha256 digest"
                )
            return digest
        failure = error_lines(completed.stderr)
        if RATE_LIMITED_PATTERN.search(failure):
            raise MirrorError(
                "Rate limited",
                f"{reference} is still rate limited after {self.attempts} attempts: {last_line(failure)}. "
                "Re-run the failed shards later; Docker Hub allows more pulls with DOCKERHUB_USERNAME and "
                "DOCKERHUB_TOKEN set.",
            )
        if NOT_FOUND_PATTERN.search(failure):
            return None
        if (
            absent_while_package_missing
            and DENIED_PATTERN.search(failure)
            and not self.package_exists(repository_of(reference))
        ):
            return None
        raise MirrorError("Cannot resolve", f"crane digest {reference} failed: {last_line(failure)}")

    def mirror_digest(self, reference):
        return self.digest(reference, absent_while_package_missing=True)

    def package_exists(self, repository):
        if repository in self.packages_known_to_exist:
            return True
        _, organization, package = repository.split("/", 2)
        completed = self.run(
            ["gh", "api", f"orgs/{organization}/packages/container/{urllib.parse.quote(package, safe='')}"],
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            self.packages_known_to_exist.add(repository)
            return True
        if "HTTP 404" in completed.stderr:
            return False
        raise MirrorError(
            "Package check failed",
            f"could not tell whether {repository} exists: {last_line(completed.stderr)}",
        )

    def copy(self, source, destination):
        completed = self.run_with_retries(["crane", "copy", "--no-clobber", source, destination])
        if completed.returncode != 0:
            failure = last_line(error_lines(completed.stderr))
            raise MirrorError("Copy failed", f"crane copy {source} {destination} failed: {failure}")
        self.packages_known_to_exist.add(repository_of(destination))

    def signed(self, reference, certificate_identity_regexp, certificate_oidc_issuer):
        completed = self.run_with_retries(
            [
                "cosign",
                "verify",
                reference,
                "--certificate-identity-regexp",
                certificate_identity_regexp,
                "--certificate-oidc-issuer",
                certificate_oidc_issuer,
            ]
        )
        return completed.returncode == 0

    def sign(self, reference):
        completed = self.run_with_retries(["cosign", "sign", "--yes", reference])
        if completed.returncode != 0:
            raise MirrorError(
                "Signing failed", f"cosign sign {reference} failed: {last_line(completed.stderr)}"
            )


def mirror_image(registry, image, mirror_repository, certificate_identity_regexp, certificate_oidc_issuer):
    source = image["source"]
    mirror_tag_reference = f"{mirror_repository}:{image['mirror_tag']}"
    source_digest = registry.digest(source)
    if source_digest is None:
        raise MirrorError("No source image", f"{source} does not exist")
    existing_digest = registry.mirror_digest(mirror_tag_reference)
    if existing_digest is None:
        registry.copy(f"{repository_of(source)}@{source_digest}", mirror_tag_reference)
        copy_outcome = "copied"
    elif existing_digest == source_digest:
        copy_outcome = "already mirrored"
    else:
        raise MirrorError(
            "Mirror tag holds another image",
            f"{mirror_tag_reference} is {existing_digest}, but {source} is {source_digest}. Mirror tags are never "
            "moved: nothing was copied for this task.",
        )
    mirrored_digest = registry.digest(mirror_tag_reference)
    if mirrored_digest != source_digest:
        raise MirrorError(
            "Digest changed",
            f"{mirror_tag_reference} is {mirrored_digest} after the copy, but {source} is {source_digest}",
        )
    pinned = f"{mirror_repository}@{source_digest}"
    if registry.signed(pinned, certificate_identity_regexp, certificate_oidc_issuer):
        signature_outcome = "already signed"
    else:
        registry.sign(pinned)
        if not registry.signed(pinned, certificate_identity_regexp, certificate_oidc_issuer):
            raise MirrorError(
                "Signature does not verify", f"{pinned} was signed, but its signature does not verify"
            )
        signature_outcome = "signed"
    entry = {
        "source": source,
        "source_digest": source_digest,
        "pinned": pinned,
        "mirror_tag": image["mirror_tag"],
    }
    return entry, copy_outcome, signature_outcome


def mirror_shard(
    registry, plan, shard_number, certificate_identity_regexp, certificate_oidc_issuer, log=print
):
    matching_shards = [shard for shard in plan["shards"] if shard["shard"] == shard_number]
    if len(matching_shards) != 1:
        raise MirrorError("No such shard", f"the plan has no shard {shard_number}")
    lock = {}
    outcomes = []
    failures = []
    for image in matching_shards[0]["images"]:
        log(f"{image['task']}: {image['source']} to {plan['mirror_repository']}:{image['mirror_tag']}")
        try:
            entry, copy_outcome, signature_outcome = mirror_image(
                registry,
                image,
                plan["mirror_repository"],
                certificate_identity_regexp,
                certificate_oidc_issuer,
            )
        except MirrorError as error:
            failures.append((image["task"], error))
            outcomes.append((image, None, "failed", str(error)))
            continue
        lock[image["task"]] = entry
        outcomes.append((image, entry["source_digest"], copy_outcome, signature_outcome))
    return lock, outcomes, failures


def summary_markdown(plan, shard_number, outcomes):
    lines = [
        f"## Shard {shard_number}: {plan['dataset']}@{plan['version']} to `{plan['mirror_repository']}`",
        "",
        "| Task | Source | Digest | Copy | Signature |",
        "| --- | --- | --- | --- | --- |",
    ]
    for image, digest, copy_outcome, signature_outcome in outcomes:
        lines.append(
            f"| {image['task']} | `{image['source']}` | {f'`{digest}`' if digest else '-'} | {copy_outcome} "
            f"| {signature_outcome.replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def report_failure(task, error):
    message = f"{task}: {error}"
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::error title={error.title}::{message}")
    else:
        print(f"mirror_copy.py: {message}", file=sys.stderr)


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Copy, verify and sign one shard of a mirror plan.")
    parser.add_argument("--plan", type=pathlib.Path, required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--certificate-identity-regexp", required=True)
    parser.add_argument("--certificate-oidc-issuer", required=True)
    parser.add_argument("--summary", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    plan = json.loads(options.plan.read_text(encoding="utf-8"))

    def log(message):
        print(message, flush=True)

    registry = Registry(log=log)
    try:
        lock, outcomes, failures = mirror_shard(
            registry,
            plan,
            options.shard,
            options.certificate_identity_regexp,
            options.certificate_oidc_issuer,
            log=log,
        )
    except MirrorError as error:
        report_failure(f"shard {options.shard}", error)
        return 1
    if options.summary:
        with open(options.summary, "a", encoding="utf-8") as summary:
            summary.write(summary_markdown(plan, options.shard, outcomes))
    for task, error in failures:
        report_failure(task, error)
    if failures:
        return 1
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(dump_images_lock(lock), encoding="utf-8")
    print(f"shard {options.shard}: {len(lock)} images mirrored, verified and signed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
