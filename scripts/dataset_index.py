"""Build the dataset index: every dataset version in datasets/ that the registry serves, with its manifest digest.

Usage: dataset_index.py --namespace ghcr.io/node-q/hbench-datasets [--current current.json] --output index.json
       dataset_index.py --namespace ghcr.io/node-q/hbench-datasets [--current current.json] --verify-only

Resolves <namespace>/<name>:<version> for each datasets/<name>/<version>/source.yaml with `oras resolve`, as an
anonymous client does, and leaves out a version the registry does not serve (not published yet) or serves only to
signed-in clients (a package still private), saying which. It lists a served version only once `cosign verify` passes
on its digest for the identity publish.yml@refs/heads/main: a publish run that pushed a tag but stopped before signing
it leaves a version that is left out, and any other cosign failure stops the build, so that a passing glitch never
drops a dataset from the index.

With --current, the index that is published now: when a version it lists fails verification, nothing is written
and the build fails, naming it, so that a dataset live today is never dropped silently (a version never indexed
that fails is still only left out). --verify-only verifies every served version, prints each result and writes
no index; it fails on the same condition. It also leaves out each version superseded.yaml
replaces with another, once that other is in the index: the registry still serves it by name, but hbench no longer
lists it. The index is the JSON
layer of <namespace>/index:latest, which hbench reads to list the namespace's datasets
(assets/schemas/dataset-index.v1.json in node-q/hbench, schema/dataset-index.v1.json here). Entries are sorted by
name, then version.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

import jsonschema

from source_descriptor import DESCRIPTOR_FILENAME, REPOSITORY_ROOT, load_descriptor, load_superseded, version_directories

INDEX_SCHEMA_PATH = REPOSITORY_ROOT / "schema" / "dataset-index.v1.json"
UNSERVED = re.compile(r"not found|unauthorized|denied|forbidden|manifest unknown|name unknown", re.IGNORECASE)
CERTIFICATE_IDENTITY = "https://github.com/node-q/hbench-datasets/.github/workflows/publish.yml@refs/heads/main"
CERTIFICATE_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
# What cosign says when the digest carries no signature by that identity, as opposed to a network or registry error.
UNSIGNED = re.compile(
    r"no signatures found|no matching signatures|none of the expected identities matched|no matching attestations|"
    r"no bundle found",
    re.IGNORECASE,
)
VERIFY_ATTEMPTS = 3


class DatasetIndexError(Exception):
    pass


def version_key(version):
    return [int(part) if part.isdigit() else part for part in re.split(r"[.-]", version)]


def oras_resolve(reference):
    with tempfile.TemporaryDirectory() as no_credentials:
        environment = dict(os.environ, DOCKER_CONFIG=no_credentials)
        completed = subprocess.run(["oras", "resolve", reference], capture_output=True, text=True, env=environment)
    if completed.returncode == 0:
        return completed.stdout.strip()
    if UNSERVED.search(completed.stderr):
        return None
    raise DatasetIndexError(f"oras resolve {reference}: {completed.stderr.strip()}")


def cosign_verify(reference, attempts=VERIFY_ATTEMPTS, sleep=time.sleep):
    """True when reference (<repository>@<digest>) is signed by publish.yml on main, False when it is not signed so."""
    command = [
        "cosign", "verify",
        "--certificate-identity", CERTIFICATE_IDENTITY,
        "--certificate-oidc-issuer", CERTIFICATE_OIDC_ISSUER,
        reference,
    ]
    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory() as no_credentials:
            environment = dict(os.environ, DOCKER_CONFIG=no_credentials)
            completed = subprocess.run(command, capture_output=True, text=True, env=environment)
        if completed.returncode == 0:
            return True
        if UNSIGNED.search(completed.stderr):
            return False
        if attempt < attempts:
            sleep(5 * attempt)
    raise DatasetIndexError(f"cosign verify {reference}: {completed.stderr.strip()}")


def published_versions(namespace, resolve=None, directories=None, superseded=None, verify=None):
    """The entries to index, the versions the registry does not serve, and those served but not signed by publish.yml."""
    resolve = resolve or oras_resolve
    verify = verify or cosign_verify
    superseded = load_superseded() if superseded is None else superseded
    entries, left_out, unsigned = [], [], []
    for directory in directories if directories is not None else version_directories():
        descriptor = load_descriptor(directory / DESCRIPTOR_FILENAME)
        name, version = descriptor["name"], descriptor["version"]
        digest = resolve(f"{namespace}/{name}:{version}")
        if digest is None:
            left_out.append(f"{name}@{version}")
        elif not verify(f"{namespace}/{name}@{digest}"):
            unsigned.append(f"{name}@{version}")
        else:
            entries.append({"name": name, "version": version, "digest": digest})
    indexed = {dataset_reference(entry) for entry in entries}
    entries = [entry for entry in entries if superseded.get(dataset_reference(entry)) not in indexed]
    entries.sort(key=lambda entry: (entry["name"], version_key(entry["version"])))
    return entries, sorted(left_out), sorted(unsigned)


def dataset_reference(entry):
    return f"{entry['name']}@{entry['version']}"


def build_index(entries):
    index = {"schema_version": 1, "datasets": entries}
    schema = json.loads(INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(index), key=lambda error: list(error.path))
    if errors:
        raise DatasetIndexError("; ".join(f"{'/'.join(map(str, error.path)) or '(top)'}: {error.message}" for error in errors))
    pairs = [(entry["name"], entry["version"]) for entry in entries]
    if len(pairs) != len(set(pairs)):
        raise DatasetIndexError("the index would list a dataset version twice")
    return index


def load_current(path):
    """The name@version of every dataset the index at path lists; an empty set when there is none."""
    if path is None or not path.is_file():
        return set()
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        return {f"{entry['name']}@{entry['version']}" for entry in current["datasets"]}
    except (ValueError, KeyError, TypeError) as error:
        raise DatasetIndexError(f"{path} is not a dataset index: {error}") from error


def dump_index(index):
    return json.dumps(index, indent=2, sort_keys=True) + "\n"


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--current", type=pathlib.Path)
    parser.add_argument("--verify-only", action="store_true")
    options = parser.parse_args(arguments)
    if not options.verify_only and options.output is None:
        parser.error("--output is required unless --verify-only is given")
    try:
        current = load_current(options.current)
        # A verify-only run lists superseded versions too, so that every served version's result is printed.
        superseded = {} if options.verify_only else None
        entries, left_out, unsigned = published_versions(options.namespace.rstrip("/"), superseded=superseded)
        index = build_index(entries)
    except DatasetIndexError as error:
        print(f"dataset_index.py: {error}", file=sys.stderr)
        return 1
    live_unsigned = sorted(dataset for dataset in unsigned if dataset in current)
    if options.verify_only:
        verified = {dataset_reference(entry): entry["digest"] for entry in entries}
        for dataset in sorted(verified):
            print(f"verified {dataset}: {verified[dataset]}")
        for dataset in unsigned:
            live = " (listed in the current index)" if dataset in current else ""
            print(f"not verified {dataset}{live}: not signed by publish.yml on main")
        for dataset in left_out:
            print(f"not served {dataset}")
    if live_unsigned:
        print(
            f"dataset_index.py: refusing to drop {', '.join(live_unsigned)}: listed in the published index but not "
            "signed by publish.yml on main. Nothing was written.",
            file=sys.stderr,
        )
        return 1
    if options.verify_only:
        return 0
    options.output.write_text(dump_index(index), encoding="utf-8")
    for dataset in left_out:
        print(f"left out {dataset}: {options.namespace}/{dataset.replace('@', ':')} is not served to anonymous clients")
    for dataset in unsigned:
        print(
            f"left out {dataset}: {options.namespace}/{dataset.replace('@', ':')} is not signed by publish.yml on main; "
            "delete that package version and publish it again"
        )
    indexed = {dataset_reference(entry) for entry in entries}
    for dataset, successor in sorted(load_superseded().items()):
        if dataset in indexed:
            print(f"kept {dataset}: its successor {successor} is not in the index yet")
        elif successor in indexed:
            print(f"left out {dataset}: superseded by {successor}")
    print(f"indexed {len(entries)} dataset versions in {options.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
