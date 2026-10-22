"""Checks of a generated dataset version that need no download: its adapter, its locks and its image.

validate_sources.py checks images.lock.json as it checks any lock; these add what is particular to a
generated version: generated.lock.json, and an images.lock.json that pins exactly its generated tasks
to its one built image or, for a version on several images (environment.task_images), the tasks of
each image it pins to that image, an image's tasks all together, or, for the built-locally policy,
each to its own base image.
"""

import json
import pathlib
import re

from environment_images import (
    EnvironmentImageError,
    built_image,
    built_lock_problems,
    task_image_tags,
    task_images_lock_problems,
    unlocked_image_tags,
    unmatched_task_image_patterns,
    version_image_tags,
)
from images_lock import (
    IMAGES_LOCK_FILENAME,
    LockError,
    load_images_lock,
    lock_problems,
    refuse_duplicate_keys,
    unfilled_lock_message,
)
from source_descriptor import REPOSITORY_ROOT

GENERATED_KIND = "generated"
BUILT_LOCALLY_POLICY = "built-locally"
GENERATED_LOCK_FILENAME = "generated.lock.json"
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
    except (OSError, ValueError, LockError) as error:
        raise GeneratedLockError(f"{GENERATED_LOCK_FILENAME}: {error}") from None
    if not isinstance(lock, dict):
        raise GeneratedLockError(f"{GENERATED_LOCK_FILENAME} is not a JSON object of task name to package digest")
    return lock


def dump_generated_lock(digests):
    return json.dumps({name: digests[name] for name in sorted(digests)}, indent=2) + "\n"


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


def on_several_images(descriptor):
    return "task_images" in descriptor["environment"]


def built_lock_problems_of(descriptor, lock, task_names):
    environment = descriptor["environment"]
    if not on_several_images(descriptor):
        return built_lock_problems(lock, environment["image"], task_names)
    try:
        tags_by_task = task_image_tags(environment, task_names)
    except EnvironmentImageError as error:
        return [str(error)]
    return task_images_lock_problems(lock, tags_by_task)


def version_lock_problems(descriptor, lock, task_names):
    task_count = len(lock) if on_several_images(descriptor) else len(task_names)
    return lock_problems(lock, descriptor["name"], "built", task_count) + built_lock_problems_of(
        descriptor, lock, task_names
    )


def unlocked_images(descriptor, lock, task_names):
    if not on_several_images(descriptor):
        return [] if lock else [descriptor["environment"]["image"]]
    try:
        return unlocked_image_tags(lock, task_image_tags(descriptor["environment"], task_names))
    except EnvironmentImageError:
        return sorted(descriptor["environment"]["task_images"].values())


def partially_locked_message(unlocked):
    return (
        f"{unfilled_lock_message('built')}; it does not pin the tasks on {', '.join(unlocked)} yet, so run "
        "the workflow for each of them"
    )


def built_image_problems(descriptor, version_directory, task_names, for_publish=False):
    environment = descriptor["environment"]
    problems = []
    for _, tag in version_image_tags(environment):
        try:
            built_image(tag)
        except EnvironmentImageError as error:
            problems.append(str(error))
    if on_several_images(descriptor):
        problems += [
            f"environment.task_images's glob {pattern} matches no task in {GENERATED_LOCK_FILENAME}"
            for pattern in unmatched_task_image_patterns(environment, task_names)
        ]
    if problems:
        return problems
    try:
        lock = load_images_lock(version_directory / IMAGES_LOCK_FILENAME)
    except (OSError, LockError):
        return []
    if not lock:
        return []
    problems = [f"{IMAGES_LOCK_FILENAME}: {problem}" for problem in built_lock_problems_of(descriptor, lock, task_names)]
    unlocked = unlocked_images(descriptor, lock, task_names)
    if for_publish and unlocked and not problems:
        problems.append(partially_locked_message(unlocked))
    return problems


def locked_tasks_problems(lock, task_names):
    missing = sorted(set(task_names) - set(lock))
    unexpected = sorted(set(lock) - set(task_names))
    if missing or unexpected:
        return [f"does not lock exactly the generated tasks: missing {missing[:10]}, unexpected {unexpected[:10]}"]
    return []


def base_images_problems(version_directory, task_names):
    try:
        lock = load_images_lock(version_directory / IMAGES_LOCK_FILENAME)
    except (OSError, LockError):
        return []
    return [f"{IMAGES_LOCK_FILENAME}: {problem}" for problem in locked_tasks_problems(lock, task_names)] if lock else []


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
        return problems + [f"{error}; write it with scripts/generated_source.py generate --write-lock"]
    problems += generated_lock_problems(generated_lock, source["task_count"])
    if descriptor["environment"]["policy"] == BUILT_LOCALLY_POLICY:
        return problems + base_images_problems(version_directory, sorted(generated_lock))
    return problems + built_image_problems(descriptor, version_directory, sorted(generated_lock), for_publish)
