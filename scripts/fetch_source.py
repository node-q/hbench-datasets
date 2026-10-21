"""Fetch a dataset version's task directories at their pinned commit, ready to pack.

Usage: fetch_source.py datasets/<name>/<version>/source.yaml DESTINATION

Leaves the git checkout in DESTINATION/checkout and a copy of exactly the task directories,
byte-identical, in DESTINATION/tasks.
"""

import pathlib
import shutil
import subprocess
import sys
import tomllib

from source_descriptor import load_descriptor

TASK_MANIFEST_FILENAME = "task.toml"


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


def declared_image_problems(tasks, declared_image):
    problems = []
    for task in tasks:
        with open(task / TASK_MANIFEST_FILENAME, "rb") as manifest:
            docker_image = tomllib.load(manifest).get("environment", {}).get("docker_image")
        expected_image = declared_image.replace("{task}", task.name)
        if docker_image != expected_image:
            problems.append(
                f"{task.name}: docker_image is {docker_image!r}, the descriptor declares {expected_image!r}"
            )
    return problems


def fetch_tasks(descriptor, destination):
    source = descriptor["source"]
    environment = descriptor["environment"]
    if environment["policy"] != "as-declared":
        raise SourceError(
            f"environment policy {environment['policy']!r} is not packed yet: only 'as-declared' sources are"
        )
    tasks_root = checkout_commit(
        source["git_url"], source["commit"], source["path"], destination / "checkout"
    )
    tasks = task_directories(tasks_root)
    if len(tasks) != source["task_count"]:
        raise SourceError(
            f"found {len(tasks)} task directories, the descriptor declares {source['task_count']}"
        )
    if environment.get("declared_image"):
        problems = declared_image_problems(tasks, environment["declared_image"])
        if problems:
            raise SourceError("tasks do not declare the descriptor's image:\n  " + "\n  ".join(problems))
    packed_tasks_directory = destination / "tasks"
    packed_tasks_directory.mkdir()
    for task in tasks:
        shutil.copytree(task, packed_tasks_directory / task.name, symlinks=True)
    return packed_tasks_directory, [task.name for task in tasks]


def main(arguments):
    if len(arguments) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    descriptor_path, destination = pathlib.Path(arguments[0]), pathlib.Path(arguments[1])
    if destination.exists():
        print(f"fetch_source.py: {destination} already exists", file=sys.stderr)
        return 2
    descriptor = load_descriptor(descriptor_path)
    try:
        packed_tasks_directory, task_names = fetch_tasks(descriptor, destination)
    except SourceError as error:
        print(f"fetch_source.py: {descriptor['name']}@{descriptor['version']}: {error}", file=sys.stderr)
        return 1
    print(
        f"{descriptor['name']}@{descriptor['version']}: {len(task_names)} tasks from "
        f"{descriptor['source']['git_url']} at {descriptor['source']['commit']} in {packed_tasks_directory}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
