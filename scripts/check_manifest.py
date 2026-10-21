"""Check a pushed dataset manifest against its descriptor and the task directories it was packed from.

Usage: check_manifest.py MANIFEST_JSON datasets/<name>/<version>/source.yaml TASKS_DIRECTORY
"""

import json
import pathlib
import sys

from source_descriptor import load_descriptor

OCI_IMAGE_MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
HBENCH_DATASET_ARTIFACT_TYPE = "application/vnd.hbench.dataset.v1"
HBENCH_DATASET_CONFIG_MEDIA_TYPE = "application/vnd.hbench.dataset.config.v1+json"
TASK_LAYER_MEDIA_TYPE = "application/vnd.oci.image.layer.v1.tar+gzip"
TITLE_ANNOTATION = "org.opencontainers.image.title"
LICENSES_ANNOTATION = "org.opencontainers.image.licenses"
VERSION_ANNOTATION = "org.opencontainers.image.version"


def manifest_problems(manifest, descriptor, task_names):
    problems = []
    if manifest.get("mediaType") != OCI_IMAGE_MANIFEST_MEDIA_TYPE:
        problems.append(
            f"mediaType is {manifest.get('mediaType')!r}, expected {OCI_IMAGE_MANIFEST_MEDIA_TYPE!r}"
        )
    if manifest.get("artifactType") != HBENCH_DATASET_ARTIFACT_TYPE:
        problems.append(
            f"artifactType is {manifest.get('artifactType')!r}, expected {HBENCH_DATASET_ARTIFACT_TYPE!r}"
        )
    config_media_type = manifest.get("config", {}).get("mediaType")
    if config_media_type != HBENCH_DATASET_CONFIG_MEDIA_TYPE:
        problems.append(
            f"config mediaType is {config_media_type!r}, expected {HBENCH_DATASET_CONFIG_MEDIA_TYPE!r}"
        )
    layers = manifest.get("layers", [])
    if len(layers) != len(task_names):
        problems.append(f"{len(layers)} layers for {len(task_names)} tasks")
    other_media_types = sorted(
        {layer.get("mediaType") for layer in layers} - {TASK_LAYER_MEDIA_TYPE}, key=str
    )
    if other_media_types:
        problems.append(f"layers other than {TASK_LAYER_MEDIA_TYPE}: {other_media_types}")
    layer_titles = [layer.get("annotations", {}).get(TITLE_ANNOTATION) for layer in layers]
    if sorted(layer_titles, key=str) != sorted(task_names):
        missing = sorted(set(task_names) - set(layer_titles))
        unexpected = sorted(set(layer_titles) - set(task_names), key=str)
        problems.append(
            f"layer titles differ from the task directories: missing {missing}, unexpected {unexpected}"
        )
    annotations = manifest.get("annotations", {})
    if annotations.get(LICENSES_ANNOTATION) != descriptor["license"]:
        problems.append(
            f"{LICENSES_ANNOTATION} is {annotations.get(LICENSES_ANNOTATION)!r}, expected {descriptor['license']!r}"
        )
    if annotations.get(VERSION_ANNOTATION) != descriptor["version"]:
        problems.append(
            f"{VERSION_ANNOTATION} is {annotations.get(VERSION_ANNOTATION)!r}, expected {descriptor['version']!r}"
        )
    return problems


def main(arguments):
    if len(arguments) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    manifest_path, descriptor_path, tasks_directory = (pathlib.Path(argument) for argument in arguments)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    descriptor = load_descriptor(descriptor_path)
    task_names = sorted(entry.name for entry in tasks_directory.iterdir() if entry.is_dir())
    problems = manifest_problems(manifest, descriptor, task_names)
    for problem in problems:
        print(f"check_manifest.py: {problem}", file=sys.stderr)
    if not problems:
        print(
            f"{descriptor['name']}@{descriptor['version']}: manifest matches the descriptor and {len(task_names)} tasks"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
