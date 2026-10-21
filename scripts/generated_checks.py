"""Checks of a generated dataset version that need no download: its adapter, its locks and its image."""

import json
import pathlib
import re

from environment_images import (
    IMAGES_LOCK_FILENAME,
    EnvironmentImageError,
    built_image,
    images_lock_problems,
    load_images_lock,
    refuse_duplicate_keys,
    unfilled_images_lock_message,
)
from source_descriptor import REPOSITORY_ROOT

GENERATED_KIND = "generated"
BUILT_POLICY = "built"
GENERATED_LOCK_FILENAME = "generated.lock.json"
GENERATED_VERSION_ENTRIES = (GENERATED_LOCK_FILENAME, IMAGES_LOCK_FILENAME)
ADAPTER_FILES = ("__init__.py", "adapter.py")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TASK_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")


class GeneratedLockError(ValueError):
    pass


def is_generated(descriptor):
    source = descriptor.get("source")
    return isinstance(source, dict) and source.get("kind") == GENERATED_KIND


def load_generated_lock(path):
    try:
        lock = json.loads(pathlib.Path(path).read_text(encoding="utf-8"), object_pairs_hook=refuse_duplicate_keys)
    except (OSError, ValueError) as error:
        raise GeneratedLockError(f"{GENERATED_LOCK_FILENAME}: {error}") from None
    if not isinstance(lock, dict):
        raise GeneratedLockError(f"{GENERATED_LOCK_FILENAME} is not a JSON object of task name to package digest")
    return lock


def generated_lock_problems(lock, task_count):
    problems = []
    if len(lock) != task_count:
        problems.append(f"{GENERATED_LOCK_FILENAME} locks {len(lock)} tasks, the descriptor declares {task_count}")
    if list(lock) != sorted(lock):
        problems.append(f"{GENERATED_LOCK_FILENAME} lists its tasks out of order")
    for name, digest in lock.items():
        if not TASK_NAME_PATTERN.match(name):
            problems.append(f"{GENERATED_LOCK_FILENAME}: {name!r} is not a task directory name")
        if not isinstance(digest, str) or not DIGEST_PATTERN.match(digest):
            problems.append(f"{GENERATED_LOCK_FILENAME}: {name}: {digest!r} is not sha256:<64 lowercase hex digits>")
    return problems


def adapter_problems(adapter):
    adapter_directory = REPOSITORY_ROOT / adapter
    return [
        f"adapter {adapter} has no {filename}"
        for filename in ADAPTER_FILES
        if not (adapter_directory / filename).is_file()
    ]


def upstream_file_problems(upstream_files):
    names = [upstream_file["name"] for upstream_file in upstream_files]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    return [f"source.upstream_files names {name} more than once" for name in duplicates]


def images_lock_state(descriptor, version_directory, task_names):
    tag = descriptor["environment"]["image"]
    try:
        built_image(tag)
        lock = load_images_lock(version_directory / IMAGES_LOCK_FILENAME)
    except OSError:
        return [f"{IMAGES_LOCK_FILENAME} is missing: a built version keeps its image lock next to it, {{}} until built"], None
    except EnvironmentImageError as error:
        return [str(error)], None
    if not lock:
        return [], unfilled_images_lock_message(tag)
    return [f"{IMAGES_LOCK_FILENAME}: {problem}" for problem in images_lock_problems(lock, tag, task_names)], None


def generated_problems(descriptor, version_directory, for_publish=False):
    generated_lock_path = version_directory / GENERATED_LOCK_FILENAME
    if not is_generated(descriptor):
        if generated_lock_path.exists():
            return [f"{GENERATED_LOCK_FILENAME} belongs only to a version whose source kind is generated"]
        return []
    source = descriptor["source"]
    problems = adapter_problems(source["adapter"]) + upstream_file_problems(source["upstream_files"])
    try:
        generated_lock = load_generated_lock(generated_lock_path)
    except GeneratedLockError as error:
        return problems + [f"{error}; generate it with scripts/generated_source.py generate --write-lock"]
    problems += generated_lock_problems(generated_lock, source["task_count"])
    lock_problems, unfilled = images_lock_state(descriptor, version_directory, sorted(generated_lock))
    problems += lock_problems
    if unfilled and for_publish:
        problems.append(unfilled)
    return problems


def generated_warnings(descriptor, version_directory):
    if not is_generated(descriptor):
        return []
    try:
        task_names = sorted(load_generated_lock(version_directory / GENERATED_LOCK_FILENAME))
    except GeneratedLockError:
        return []
    _, unfilled = images_lock_state(descriptor, version_directory, task_names)
    return [unfilled] if unfilled else []
