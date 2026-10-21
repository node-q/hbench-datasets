"""Fetch a dataset version's task directories at their pinned commit, or generate them, ready to pack.

Usage: fetch_source.py [--allow-unfilled-lock] datasets/<name>/<version>/source.yaml DESTINATION

Leaves the git checkout in DESTINATION/checkout, a copy of exactly the task directories in
DESTINATION/tasks, and the descriptor to pack them with in DESTINATION/source.yaml. The copies are
byte-identical, except that a pinned-mirror or pinned-upstream version's task.toml files have the value
of their docker_image line replaced by its pinned reference in images.lock.json.

--allow-unfilled-lock fetches and checks such a version whose images.lock.json is not filled yet,
leaving task.toml as upstream wrote it and writing no descriptor to pack with.

A generated source is not fetched but generated: scripts/generated_source.py writes DESTINATION/tasks
and checks them against generated.lock.json, and, once images.lock.json is filled, writes
DESTINATION/source.yaml.
"""

import argparse
import copy
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib

import yaml

import generated_source
from images_lock import (
    IMAGES_LOCK_FILENAME,
    LOCKED_POLICIES,
    LockError,
    load_images_lock,
    unfilled_lock_message,
)
from source_descriptor import DESCRIPTOR_FILENAME, load_descriptor

TASK_MANIFEST_FILENAME = "task.toml"
PACKED_POLICIES = ("as-declared", *LOCKED_POLICIES)
DOCKER_IMAGE_LINE = re.compile(rb'^[ \t]*docker_image[ \t]*=[ \t]*"(?P<image>[^"\\\r\n]*)"', re.MULTILINE)


class SourceError(RuntimeError):
    pass


def run_git(arguments, repository_directory):
    completed = subprocess.run(
        ["git", "-C", str(repository_directory), *arguments], capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise SourceError(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def checkout_commit(git_url, commit, path, checkout_directory):
    checkout_directory.mkdir(parents=True)
    run_git(["init", "--quiet"], checkout_directory)
    run_git(["remote", "add", "origin", git_url], checkout_directory)
    if path != ".":
        run_git(["sparse-checkout", "set", "--no-cone", f"/{path}/"], checkout_directory)
    run_git(
        ["fetch", "--quiet", "--depth", "1", "--no-tags", "--filter=blob:none", "origin", commit],
        checkout_directory,
    )
    run_git(["-c", "advice.detachedHead=false", "checkout", "--quiet", "FETCH_HEAD"], checkout_directory)
    checked_out_commit = run_git(["rev-parse", "HEAD"], checkout_directory)
    if checked_out_commit != commit:
        raise SourceError(f"checked out {checked_out_commit}, expected {commit}")
    tasks_root = checkout_directory / path
    if not tasks_root.is_dir():
        raise SourceError(f"{path} is not a directory at {commit}")
    return tasks_root


def task_directories(tasks_root):
    tasks = []
    for entry in sorted(tasks_root.iterdir()):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        if not (entry / TASK_MANIFEST_FILENAME).is_file():
            raise SourceError(f"{entry.name}/ has no {TASK_MANIFEST_FILENAME}, so it is not a task directory")
        tasks.append(entry)
    return tasks


def declared_docker_image(task):
    with open(task / TASK_MANIFEST_FILENAME, "rb") as manifest:
        return tomllib.load(manifest).get("environment", {}).get("docker_image")


def declared_image_problems(tasks, declared_image):
    problems = []
    for task in tasks:
        docker_image = declared_docker_image(task)
        expected_image = declared_image.replace("{task}", task.name)
        if docker_image != expected_image:
            problems.append(
                f"{task.name}: docker_image is {docker_image!r}, the descriptor declares {expected_image!r}"
            )
    return problems


def pinned_task_manifest(manifest_bytes, source, pinned):
    try:
        manifest = tomllib.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SourceError(f"{TASK_MANIFEST_FILENAME} does not parse: {error}") from None
    docker_image = manifest.get("environment", {}).get("docker_image")
    if docker_image != source:
        raise SourceError(f"docker_image is {docker_image!r}, but {IMAGES_LOCK_FILENAME} pins {source!r}")
    docker_image_lines = list(DOCKER_IMAGE_LINE.finditer(manifest_bytes))
    if len(docker_image_lines) != 1 or docker_image_lines[0]["image"] != source.encode("utf-8"):
        raise SourceError(
            f'{TASK_MANIFEST_FILENAME} does not set docker_image = "{source}" on exactly one line, '
            "so that line cannot be pinned alone"
        )
    start, end = docker_image_lines[0].span("image")
    pinned_bytes = manifest_bytes[:start] + pinned.encode("utf-8") + manifest_bytes[end:]
    expected_manifest = copy.deepcopy(manifest)
    expected_manifest["environment"]["docker_image"] = pinned
    if tomllib.loads(pinned_bytes.decode("utf-8")) != expected_manifest:
        raise SourceError(
            f"pinning docker_image would change more of {TASK_MANIFEST_FILENAME} than that value"
        )
    return pinned_bytes


def pin_task_images(tasks_directory, task_names, images_lock):
    missing = sorted(set(task_names) - set(images_lock))
    unexpected = sorted(set(images_lock) - set(task_names))
    if missing or unexpected:
        raise SourceError(
            f"{IMAGES_LOCK_FILENAME} does not lock exactly the task directories: "
            f"missing {missing}, unexpected {unexpected}"
        )
    pinned_manifests = {}
    problems = []
    for task_name in task_names:
        manifest_path = tasks_directory / task_name / TASK_MANIFEST_FILENAME
        if manifest_path.is_symlink():
            problems.append(f"{task_name}: {TASK_MANIFEST_FILENAME} is a symbolic link")
            continue
        entry = images_lock[task_name]
        try:
            pinned_manifests[manifest_path] = pinned_task_manifest(
                manifest_path.read_bytes(), entry["source"], entry["pinned"]
            )
        except SourceError as error:
            problems.append(f"{task_name}: {error}")
    if problems:
        raise SourceError("cannot pin every task's image:\n  " + "\n  ".join(problems))
    for manifest_path, pinned_bytes in pinned_manifests.items():
        manifest_path.write_bytes(pinned_bytes)


def is_locked(descriptor):
    return descriptor["environment"]["policy"] in LOCKED_POLICIES


def unfilled_lock(descriptor, images_lock):
    return is_locked(descriptor) and not images_lock


def fetch_tasks(descriptor, destination, images_lock=None, allow_unfilled_lock=False):
    source = descriptor["source"]
    environment = descriptor["environment"]
    if environment["policy"] not in PACKED_POLICIES:
        raise SourceError(
            f"environment policy {environment['policy']!r} is not packed yet: only "
            f"{' and '.join(repr(policy) for policy in PACKED_POLICIES)} sources are"
        )
    if unfilled_lock(descriptor, images_lock) and not allow_unfilled_lock:
        raise SourceError(unfilled_lock_message(environment["policy"]))
    tasks = checked_task_directories(descriptor, destination / "checkout")
    packed_tasks_directory = destination / "tasks"
    packed_tasks_directory.mkdir()
    for task in tasks:
        shutil.copytree(task, packed_tasks_directory / task.name, symlinks=True)
    task_names = [task.name for task in tasks]
    if is_locked(descriptor) and images_lock:
        pin_task_images(packed_tasks_directory, task_names, images_lock)
    return packed_tasks_directory, task_names


def checked_task_directories(descriptor, checkout_directory):
    source = descriptor["source"]
    tasks_root = checkout_commit(source["git_url"], source["commit"], source["path"], checkout_directory)
    tasks = task_directories(tasks_root)
    if len(tasks) != source["task_count"]:
        raise SourceError(
            f"found {len(tasks)} task directories, the descriptor declares {source['task_count']}"
        )
    declared_image = descriptor["environment"].get("declared_image")
    if declared_image:
        problems = declared_image_problems(tasks, declared_image)
        if problems:
            raise SourceError("tasks do not declare the descriptor's image:\n  " + "\n  ".join(problems))
    return tasks


def fetch_declared_images(descriptor, checkout_directory):
    declared_images = {}
    undeclared = []
    for task in checked_task_directories(descriptor, checkout_directory):
        docker_image = declared_docker_image(task)
        if isinstance(docker_image, str) and docker_image:
            declared_images[task.name] = docker_image
        else:
            undeclared.append(task.name)
    if undeclared:
        raise SourceError(f"these tasks declare no [environment].docker_image: {', '.join(undeclared)}")
    return declared_images


def packed_descriptor(descriptor, images_lock):
    if not is_locked(descriptor):
        return descriptor
    packed = copy.deepcopy(descriptor)
    packed["environment"] = {
        "policy": "pinned-by-digest",
        "images": {task: images_lock[task]["pinned"] for task in sorted(images_lock)},
    }
    return packed


def write_packed_descriptor(descriptor_path, descriptor, images_lock, destination):
    packed_descriptor_path = destination / DESCRIPTOR_FILENAME
    if is_locked(descriptor):
        packed_descriptor_path.write_text(
            yaml.safe_dump(packed_descriptor(descriptor, images_lock), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    else:
        shutil.copyfile(descriptor_path, packed_descriptor_path)
    return packed_descriptor_path


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(
        description="Fetch a dataset version's task directories at their pinned commit, ready to pack."
    )
    parser.add_argument("--allow-unfilled-lock", action="store_true")
    parser.add_argument("descriptor", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    return parser.parse_args(arguments)


def generate(descriptor_path, destination, allow_unfilled_lock):
    try:
        tasks_directory, task_names, packed_path = generated_source.prepare_for_packing(
            descriptor_path, destination, allow_unfilled_lock=allow_unfilled_lock
        )
    except (
        generated_source.GeneratedSourceError,
        generated_source.GeneratedLockError,
        generated_source.EnvironmentImageError,
    ) as error:
        raise SourceError(str(error)) from None
    return tasks_directory, task_names, packed_path


def main_for_generated(options, descriptor, label):
    try:
        tasks_directory, task_names, packed_path = generate(
            options.descriptor, options.destination, options.allow_unfilled_lock
        )
    except SourceError as error:
        print(f"fetch_source.py: {label}: {error}", file=sys.stderr)
        return 1
    print(f"{label}: {len(task_names)} tasks generated by {descriptor['source']['adapter']} in {tasks_directory}")
    if packed_path is None:
        print(f"{label}: {IMAGES_LOCK_FILENAME} is not filled yet, so the tasks name no docker_image and nothing is ready to pack")
    else:
        print(f"{label}: pack with {packed_path}")
    return 0


def main(arguments):
    options = parse_arguments(arguments)
    if options.destination.exists():
        print(f"fetch_source.py: {options.destination} already exists", file=sys.stderr)
        return 2
    descriptor = load_descriptor(options.descriptor)
    label = f"{descriptor['name']}@{descriptor['version']}"
    if generated_source.is_generated(descriptor):
        return main_for_generated(options, descriptor, label)
    try:
        images_lock = None
        if is_locked(descriptor):
            try:
                images_lock = load_images_lock(options.descriptor.parent / IMAGES_LOCK_FILENAME)
            except (OSError, LockError) as error:
                raise SourceError(str(error)) from None
        packed_tasks_directory, task_names = fetch_tasks(
            descriptor, options.destination, images_lock, options.allow_unfilled_lock
        )
    except SourceError as error:
        print(f"fetch_source.py: {label}: {error}", file=sys.stderr)
        return 1
    print(
        f"{label}: {len(task_names)} tasks from "
        f"{descriptor['source']['git_url']} at {descriptor['source']['commit']} in {packed_tasks_directory}"
    )
    if unfilled_lock(descriptor, images_lock):
        print(
            f"{label}: {IMAGES_LOCK_FILENAME} is not filled yet, so task.toml keeps upstream's docker_image "
            "and nothing is ready to pack"
        )
        return 0
    packed_descriptor_path = write_packed_descriptor(
        options.descriptor, descriptor, images_lock, options.destination
    )
    print(f"{label}: pack with {packed_descriptor_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
