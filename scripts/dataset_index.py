"""Build the dataset index: every dataset version in datasets/ that the registry serves, with its manifest digest.

Usage: dataset_index.py --namespace ghcr.io/node-q/hbench-datasets --output index.json

Resolves <namespace>/<name>:<version> for each datasets/<name>/<version>/source.yaml with `oras resolve`, as an
anonymous client does, and leaves out a version the registry does not serve (not published yet) or serves only to
signed-in clients (a package still private), saying which. It also leaves out each version superseded.yaml
replaces with another: the registry still serves it by name, but hbench no longer lists it. The index is the JSON
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

import jsonschema

from source_descriptor import DESCRIPTOR_FILENAME, REPOSITORY_ROOT, load_descriptor, load_superseded, version_directories

INDEX_SCHEMA_PATH = REPOSITORY_ROOT / "schema" / "dataset-index.v1.json"
UNSERVED = re.compile(r"not found|unauthorized|denied|forbidden|manifest unknown|name unknown", re.IGNORECASE)


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


def published_versions(namespace, resolve=None, directories=None, superseded=None):
    resolve = resolve or oras_resolve
    superseded = load_superseded() if superseded is None else superseded
    entries, left_out = [], []
    for directory in directories if directories is not None else version_directories():
        descriptor = load_descriptor(directory / DESCRIPTOR_FILENAME)
        name, version = descriptor["name"], descriptor["version"]
        if f"{name}@{version}" in superseded:
            continue
        digest = resolve(f"{namespace}/{name}:{version}")
        if digest is None:
            left_out.append(f"{name}@{version}")
        else:
            entries.append({"name": name, "version": version, "digest": digest})
    entries.sort(key=lambda entry: (entry["name"], version_key(entry["version"])))
    return entries, sorted(left_out)


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


def dump_index(index):
    return json.dumps(index, indent=2, sort_keys=True) + "\n"


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    options = parser.parse_args(arguments)
    try:
        entries, left_out = published_versions(options.namespace.rstrip("/"))
        index = build_index(entries)
    except DatasetIndexError as error:
        print(f"dataset_index.py: {error}", file=sys.stderr)
        return 1
    options.output.write_text(dump_index(index), encoding="utf-8")
    for dataset in left_out:
        print(f"left out {dataset}: {options.namespace}/{dataset.replace('@', ':')} is not served to anonymous clients")
    for dataset, successor in sorted(load_superseded().items()):
        print(f"left out {dataset}: superseded by {successor}")
    print(f"indexed {len(entries)} dataset versions in {options.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
