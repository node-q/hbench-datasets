"""Check dataset descriptors: schema, licence files, SPDX id, name and version against the path, and locks.

Usage: validate_sources.py [--for-publish] [datasets/<name>/<version> ...]

With no arguments, checks every dataset version under datasets/ and the layout of datasets/ itself.
A pinned-mirror, pinned-upstream or built version whose images.lock.json is not filled yet passes
with a warning, unless --for-publish is given. A generated version also needs its adapter's files, a
generated.lock.json of the declared number of tasks, and an images.lock.json that, once filled, pins
exactly those tasks to its one built image.
"""

import argparse
import json
import os
import pathlib
import sys

import jsonschema
import yaml
from license_expression import get_spdx_licensing

from generated_checks import GENERATED_LOCK_FILENAME, generated_problems
from images_lock import (
    IMAGES_LOCK_FILENAME,
    LOCKED_POLICIES,
    LockError,
    load_images_lock,
    lock_problems,
    unfilled_lock_message,
)
from source_descriptor import (
    DATASETS_DIR,
    DESCRIPTOR_FILENAME,
    SCHEMA_PATH,
    load_descriptor,
    version_directories,
)

REQUIRED_LICENCE_FILES = ("LICENSE", "NOTICE")
ALLOWED_VERSION_DIRECTORY_ENTRIES = {
    DESCRIPTOR_FILENAME,
    IMAGES_LOCK_FILENAME,
    GENERATED_LOCK_FILENAME,
    *REQUIRED_LICENCE_FILES,
}


def schema_validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, format_checker=validator_class.FORMAT_CHECKER)


def spdx_id_problems(license_id, licensing):
    info = licensing.validate(license_id, strict=True)
    if info.errors:
        return [f"license {license_id!r} is not an SPDX license identifier: {'; '.join(info.errors)}"]
    if info.normalized_expression != license_id:
        return [
            f"license {license_id!r} is not a current SPDX identifier as written; "
            f"SPDX spells it {info.normalized_expression!r}"
        ]
    return []


def schema_problems(descriptor, validator):
    problems = []
    for error in sorted(validator.iter_errors(descriptor), key=lambda error: list(error.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "(top level)"
        problems.append(f"{location}: {error.message}")
    return problems


def path_problems(descriptor, version_directory):
    problems = []
    expected_name = version_directory.parent.name
    expected_version = version_directory.name
    if descriptor.get("name") != expected_name:
        problems.append(f"name {descriptor.get('name')!r} does not match its directory {expected_name!r}")
    if descriptor.get("version") != expected_version:
        problems.append(
            f"version {descriptor.get('version')!r} does not match its directory {expected_version!r}"
        )
    return problems


def licence_file_problems(version_directory):
    problems = []
    for filename in REQUIRED_LICENCE_FILES:
        path = version_directory / filename
        if not path.is_file():
            problems.append(f"{filename} is missing")
        elif not path.read_text(encoding="utf-8").strip():
            problems.append(f"{filename} is empty")
    return problems


def unexpected_entry_problems(version_directory):
    unexpected = sorted(
        entry.name
        for entry in version_directory.iterdir()
        if entry.name not in ALLOWED_VERSION_DIRECTORY_ENTRIES
    )
    return [
        f"{name} does not belong here: a dataset version holds only "
        f"{', '.join(sorted(ALLOWED_VERSION_DIRECTORY_ENTRIES))}, and task files are never committed"
        for name in unexpected
    ]


def environment_problems(descriptor):
    environment = descriptor.get("environment", {})
    images = environment.get("images")
    task_count = descriptor.get("source", {}).get("task_count")
    if isinstance(images, dict) and isinstance(task_count, int) and len(images) != task_count:
        return [f"environment.images pins {len(images)} images for {task_count} tasks"]
    return []


def images_lock_problems(descriptor, version_directory, for_publish):
    lock_path = version_directory / IMAGES_LOCK_FILENAME
    policy = locked_policy(descriptor)
    if policy is None:
        if lock_path.exists():
            return [
                f"{IMAGES_LOCK_FILENAME} belongs only to a version whose environment policy is "
                f"{' or '.join(LOCKED_POLICIES)}"
            ]
        return []
    if not lock_path.is_file():
        return [f"{IMAGES_LOCK_FILENAME} is missing: a {policy} version keeps its image lock next to it"]
    try:
        lock = load_images_lock(lock_path)
    except LockError as error:
        return [str(error)]
    if not lock:
        return [unfilled_lock_message(policy)] if for_publish else []
    name = descriptor.get("name")
    declared_image = descriptor["environment"].get("declared_image")
    source = descriptor.get("source")
    task_count = source.get("task_count") if isinstance(source, dict) else None
    if not (isinstance(name, str) and isinstance(task_count, int)):
        return []
    if not isinstance(declared_image, str):
        declared_image = None
    problems = lock_problems(lock, name, policy, task_count, declared_image)
    return [f"{IMAGES_LOCK_FILENAME}: {problem}" for problem in problems]


def locked_policy(descriptor):
    environment = descriptor.get("environment")
    if isinstance(environment, dict) and environment.get("policy") in LOCKED_POLICIES:
        return environment["policy"]
    return None


def unfilled_lock_warning(valid_version_directory):
    policy = locked_policy(load_descriptor(valid_version_directory / DESCRIPTOR_FILENAME))
    if policy is not None and load_images_lock(valid_version_directory / IMAGES_LOCK_FILENAME) == {}:
        return unfilled_lock_message(policy)
    return None


def version_directory_problems(version_directory, validator, licensing, for_publish=False):
    descriptor_path = version_directory / DESCRIPTOR_FILENAME
    if not descriptor_path.is_file():
        return [f"{DESCRIPTOR_FILENAME} is missing"]
    try:
        descriptor = load_descriptor(descriptor_path)
    except yaml.YAMLError as error:
        return [f"{DESCRIPTOR_FILENAME} is not valid YAML: {error}"]
    problems = licence_file_problems(version_directory) + unexpected_entry_problems(version_directory)
    if not isinstance(descriptor, dict):
        return problems + [f"{DESCRIPTOR_FILENAME} is not a mapping"]
    descriptor_schema_problems = schema_problems(descriptor, validator)
    problems += descriptor_schema_problems
    problems += path_problems(descriptor, version_directory)
    problems += environment_problems(descriptor)
    problems += images_lock_problems(descriptor, version_directory, for_publish)
    if isinstance(descriptor.get("license"), str):
        problems += spdx_id_problems(descriptor["license"], licensing)
    if not descriptor_schema_problems:
        problems += generated_problems(descriptor, version_directory)
    return problems


def datasets_layout_problems():
    problems = []
    for entry in sorted(DATASETS_DIR.iterdir()):
        if not entry.is_dir():
            problems.append((entry, "datasets/ holds only <name>/<version>/ directories"))
            continue
        for version_entry in sorted(entry.iterdir()):
            if not version_entry.is_dir():
                problems.append((version_entry, "datasets/<name>/ holds only <version>/ directories"))
    return problems


def report(problems_by_path, level="error"):
    in_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for path, message in problems_by_path:
        relative_path = os.path.relpath(path)
        if in_github_actions:
            print(f"::{level} file={relative_path}::{message}")
        else:
            print(f"{relative_path}: {message}")


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Check dataset descriptors.")
    parser.add_argument("--for-publish", action="store_true")
    parser.add_argument("version_directories", nargs="*", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    validator = schema_validator()
    licensing = get_spdx_licensing()
    problems_by_path = []
    warnings_by_path = []
    if options.version_directories:
        targets = [path.resolve() for path in options.version_directories]
    else:
        targets = version_directories()
        problems_by_path += datasets_layout_problems()
        if not targets:
            problems_by_path.append((DATASETS_DIR, "no dataset versions found"))
    for version_directory in targets:
        if not version_directory.is_dir() or version_directory.parent.parent != DATASETS_DIR:
            problems_by_path.append((version_directory, "is not a datasets/<name>/<version> directory"))
            continue
        problems = version_directory_problems(version_directory, validator, licensing, options.for_publish)
        descriptor_path = version_directory / DESCRIPTOR_FILENAME
        problems_by_path += [(descriptor_path, message) for message in problems]
        if not problems:
            print(f"ok  {os.path.relpath(version_directory)}")
            warning = unfilled_lock_warning(version_directory)
            if warning:
                warnings_by_path.append((version_directory / IMAGES_LOCK_FILENAME, warning))
    report(warnings_by_path, level="warning")
    report(problems_by_path)
    return 1 if problems_by_path else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
