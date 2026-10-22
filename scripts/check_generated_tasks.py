"""Generate each generated dataset version twice, and check its package digests and its tasks' layout.

Usage: check_generated_tasks.py --output DIRECTORY [--upstream-cache DIRECTORY] [--hbench BINARY]
                                [datasets/<name>/<version> ...]
       check_generated_tasks.py --list [--policy POLICY]

Generates every generated dataset version (each one under datasets/ when none is given) into
OUTPUT/<name>/<version>/first and OUTPUT/<name>/<version>/second, with its images.lock.json as
committed. It fails if the two generations' package digests differ, if they differ from
generated.lock.json, or if a task is not a valid hbench task: task.toml must parse, name the task
and give its category and timeouts, its [task].name being the bare directory name; its docker_image
must be the locked image (none while images.lock.json is not filled); instruction.md must start with
the canary; environment/ must be exactly the image's build context, or for a built-locally version a
Dockerfile whose only FROM is the task's base image as images.lock.json pins it; tests/test.sh and
solution/solve.sh must be executable; every file in tests/ and solution/ must carry the canary; and
the adapter's own task_problems() must find nothing. With --hbench, hbench itself must accept every
task (hbench tasks check) and print the same package digests (hbench tasks digest).

In a version on several images (environment.task_images), each task's docker_image must be its
image, pinned from images.lock.json or by tag until the lock pins it, and environment/ must hold the
files the adapter wrote for hbench to copy into the image, with no Dockerfile or docker-compose.yaml.

--list prints "<name> <version> <adapter> <image>" for each generated version on one image or none,
the adapter being its directory name under adapters/ and the image "-" for a version with no built
image; --policy lists only the versions whose environment policy it names.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tomllib

import generated_source
from environment_images import built_image, dockerfile_from_references
from generated_checks import BUILT_LOCALLY_POLICY, is_generated, on_several_images
from images_lock import IMAGES_LOCK_FILENAME, load_images_lock
from source_descriptor import DESCRIPTOR_FILENAME, REPOSITORY_ROOT, load_descriptor, version_directories

TASK_ENTRIES = {"task.toml", "instruction.md", "environment", "tests", "solution"}
EXECUTABLE_SCRIPTS = ("tests/test.sh", "solution/solve.sh")
VERIFIER_ONLY_DIRECTORIES = ("tests", "solution")
GENERATIONS = ("first", "second")


def generated_versions(arguments):
    directories = [pathlib.Path(argument).resolve() for argument in arguments] or version_directories()
    versions = []
    for directory in directories:
        descriptor = load_descriptor(directory / DESCRIPTOR_FILENAME)
        if is_generated(descriptor):
            versions.append((directory, descriptor))
    return versions


def manifest_problems(task_directory, docker_image):
    try:
        with open(task_directory / "task.toml", "rb") as stream:
            manifest = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"task.toml does not parse: {error}"]
    problems = []
    name = manifest.get("task", {}).get("name")
    if name != task_directory.name:
        problems.append(f"[task].name is {name!r}, not the task directory's bare name {task_directory.name!r}")
    if not isinstance(manifest.get("metadata", {}).get("category"), str):
        problems.append("[metadata].category is missing")
    for section in ("agent", "verifier"):
        timeout = manifest.get(section, {}).get("timeout_sec")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            problems.append(f"[{section}].timeout_sec is not a positive number")
    declared_image = manifest.get("environment", {}).get("docker_image")
    if declared_image != docker_image:
        problems.append(f"[environment].docker_image is {declared_image!r}, the image lock pins {docker_image!r}")
    return problems


def files_of(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def base_image_problems(environment_directory, pinned_base_image):
    dockerfile = environment_directory / "Dockerfile"
    if not dockerfile.is_file():
        return ["environment/Dockerfile is missing"]
    references = dockerfile_from_references(dockerfile)
    if references != [pinned_base_image]:
        return [f"environment/Dockerfile starts FROM {references}, images.lock.json pins {pinned_base_image}"]
    return []


def task_layout_problems(task_directory, canary, docker_image, context_files, adapter, pinned_base_image=None):
    problems = []
    unexpected = sorted({entry.name for entry in task_directory.iterdir()} - TASK_ENTRIES)
    if unexpected:
        problems.append(f"holds {', '.join(unexpected)}, which a generated task does not")
    problems += manifest_problems(task_directory, docker_image)
    instruction_path = task_directory / "instruction.md"
    instruction = instruction_path.read_text(encoding="utf-8") if instruction_path.is_file() else ""
    if not instruction.startswith(f"<!-- {canary} -->\n") or not instruction.partition("\n")[2].strip():
        problems.append("instruction.md does not start with the canary and an instruction")
    environment_directory = task_directory / "environment"
    if pinned_base_image is not None:
        problems += base_image_problems(environment_directory, pinned_base_image)
    elif context_files is None:
        problems += [problem.partition(": ")[2] for problem in generated_source.adapter_environment_problems(task_directory)]
    elif environment_directory.is_dir():
        if files_of(environment_directory) != context_files:
            problems.append("environment/ is not the image's build context")
    else:
        problems.append("environment/ is missing")
    for relative_path in EXECUTABLE_SCRIPTS:
        path = task_directory / relative_path
        if not path.is_file() or not os.access(path, os.X_OK):
            problems.append(f"{relative_path} is missing or not executable")
    canary_bytes = canary.encode("utf-8")
    for directory in VERIFIER_ONLY_DIRECTORIES:
        if (task_directory / directory).is_dir():
            for relative_path, content in files_of(task_directory / directory).items():
                if canary_bytes not in content:
                    problems.append(f"{directory}/{relative_path} does not carry the canary")
    if hasattr(adapter, "task_problems"):
        problems += adapter.task_problems(task_directory)
    return problems


def hbench_problems(hbench, tasks_directory, digests):
    checked = subprocess.run([hbench, "tasks", "check", "--path", str(tasks_directory)], capture_output=True, text=True)
    refused = [line for line in checked.stdout.splitlines() if line.strip() and not line.startswith("ok ")]
    if checked.returncode != 0 or refused:
        return [f"hbench tasks check refuses tasks: {' '.join(refused[:5]) or checked.stderr.strip()}"]
    printed = subprocess.run(
        [hbench, "tasks", "digest", "--path", str(tasks_directory)], capture_output=True, text=True, check=True
    )
    hbench_digests = {task["name"]: task["digest"] for task in json.loads(printed.stdout)}
    if hbench_digests != digests:
        differing = sorted(name for name in set(digests) | set(hbench_digests) if digests.get(name) != hbench_digests.get(name))
        return [f"hbench tasks digest differs in {len(differing)} tasks, such as {differing[:5]}"]
    return []


def check_version(version_directory, descriptor, output, upstream_cache, hbench=None):
    label = f"{descriptor['name']}@{descriptor['version']}"
    destination = output / descriptor["name"] / descriptor["version"]
    digests = []
    for generation in GENERATIONS:
        tasks_directory, task_names, _ = generated_source.prepare_for_packing(
            version_directory / DESCRIPTOR_FILENAME,
            destination / generation,
            allow_unfilled_lock=True,
            upstream_cache=upstream_cache,
        )
        digests.append(generated_source.package_digests(tasks_directory, task_names))
    if digests[0] != digests[1]:
        differing = sorted(name for name in digests[0] if digests[0].get(name) != digests[1].get(name))
        return [f"{label}: two generations differ in {len(differing)} tasks, such as {differing[:5]}"]
    adapter = generated_source.adapter_module(descriptor["source"]["adapter"])
    context = generated_source.generation_context(descriptor, load_images_lock(version_directory / IMAGES_LOCK_FILENAME))
    context_files = None
    if descriptor["environment"]["policy"] != BUILT_LOCALLY_POLICY and not on_several_images(descriptor):
        context_files = files_of(REPOSITORY_ROOT / built_image(descriptor["environment"]["image"])["context"])
    tasks_directory = destination / GENERATIONS[0] / "tasks"
    problems = []
    for task_name in sorted(digests[0]):
        problems += [
            f"{label}: {task_name}: {problem}"
            for problem in task_layout_problems(
                tasks_directory / task_name,
                descriptor["canary"],
                context.docker_image_for(task_name),
                context_files,
                adapter,
                context.base_images.get(task_name),
            )
        ]
    if hbench and not problems:
        problems += [f"{label}: {problem}" for problem in hbench_problems(hbench, tasks_directory, digests[0])]
    if not problems:
        checked_by = ", and hbench accepts them with the same digests" if hbench else ""
        print(f"ok  {label}: {len(digests[0])} tasks, generated twice with the same digests as generated.lock.json{checked_by}")
    return problems


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Generate each generated dataset version twice and check it.")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--policy")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--upstream-cache", type=pathlib.Path)
    parser.add_argument("--hbench")
    parser.add_argument("version_directories", nargs="*")
    options = parser.parse_args(arguments)
    if not options.list and options.output is None:
        parser.error("--output is needed unless --list is given")
    return options


def main(arguments):
    options = parse_arguments(arguments)
    versions = generated_versions(options.version_directories)
    if options.list:
        for _, descriptor in versions:
            if on_several_images(descriptor):
                continue
            if options.policy and descriptor["environment"]["policy"] != options.policy:
                continue
            adapter = pathlib.PurePosixPath(descriptor["source"]["adapter"]).name
            print(f"{descriptor['name']} {descriptor['version']} {adapter} {descriptor['environment'].get('image', '-')}")
        return 0
    problems = []
    for version_directory, descriptor in versions:
        try:
            problems += check_version(
                version_directory, descriptor, options.output, options.upstream_cache, options.hbench
            )
        except (generated_source.GeneratedSourceError, generated_source.GeneratedLockError) as error:
            problems.append(f"{descriptor['name']}@{descriptor['version']}: {error}")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
