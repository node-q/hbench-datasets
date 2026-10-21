"""Generate a dataset version's task directories with its adapter, from its pinned upstream files.

Usage:
  generated_source.py generate [--allow-unfilled-lock] [--write-lock] [--upstream-cache DIRECTORY]
                               datasets/<name>/<version>/source.yaml DESTINATION
  generated_source.py lock-image TAG DIGEST

generate downloads each upstream file into DESTINATION/upstream, or copies it from --upstream-cache,
and checks its sha256; runs the adapter's generate(), which writes DESTINATION/tasks; copies the
environment image's build context into each task's environment/; and checks every task's package
digest against generated.lock.json, or with --write-lock rewrites that file. It then writes
DESTINATION/source.yaml, the descriptor hbench packs the tasks with. A version whose images.lock.json
is not filled yet is refused unless --allow-unfilled-lock is given: its tasks then name no
docker_image, and no descriptor to pack with is written.

lock-image writes the images.lock.json of every generated version whose environment is the built
image TAG, pinning each of its tasks to ghcr.io/node-q/hbench-envs@DIGEST, then rewrites their
generated.lock.json to match.
"""

import argparse
import copy
import importlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import yaml

from environment_images import (
    IMAGES_LOCK_FILENAME,
    EnvironmentImageError,
    built_image,
    dump_images_lock,
    images_lock_entry,
    images_lock_problems,
    load_images_lock,
    pinned_image,
    unfilled_images_lock_message,
)
from generated_checks import GENERATED_LOCK_FILENAME, GeneratedLockError, is_generated, load_generated_lock
from source_descriptor import (
    DESCRIPTOR_FILENAME,
    PUBLISHED_REPOSITORY_URL,
    REPOSITORY_ROOT,
    load_descriptor,
    version_directories,
)

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from adapters.common.generation import GenerationContext
from adapters.common.package_digest import file_sha256, package_digest
from adapters.common.writing import write_task_file

ADAPTER_MODULE_NAME = "adapter"
DOWNLOAD_TIMEOUT_SECONDS = 120
REPORTED_DIFFERENCES = 10


class GeneratedSourceError(RuntimeError):
    pass


def adapter_module(adapter_path):
    module_name = ".".join([*pathlib.PurePosixPath(adapter_path).parts, ADAPTER_MODULE_NAME])
    try:
        return importlib.import_module(module_name)
    except ImportError as error:
        raise GeneratedSourceError(f"cannot import the adapter {module_name}: {error}") from None


def download(url, destination):
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as partial:
        partial_path = pathlib.Path(partial.name)
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                shutil.copyfileobj(response, partial)
        except (OSError, ValueError) as error:
            partial_path.unlink(missing_ok=True)
            raise GeneratedSourceError(f"cannot download {url}: {error}") from None
    partial_path.replace(destination)


def fetched_upstream_files(upstream_files, directory, cache_directory=None):
    directory.mkdir(parents=True)
    paths = {}
    for upstream_file in upstream_files:
        path = directory / upstream_file["name"]
        expected = upstream_file["sha256"]
        cached = cache_directory / expected if cache_directory else None
        if cached and cached.is_file() and file_sha256(cached) == expected:
            shutil.copyfile(cached, path)
        else:
            download(upstream_file["url"], path)
        actual = file_sha256(path)
        if actual != expected:
            raise GeneratedSourceError(
                f"{upstream_file['url']} has sha256 {actual}, but the descriptor pins {expected}"
            )
        if cached and not cached.is_file():
            cache_directory.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, cached)
        paths[upstream_file["name"]] = path
    return paths


def build_context_files(context_directory):
    files = {}
    for path in sorted(context_directory.rglob("*")):
        if path.is_symlink():
            raise GeneratedSourceError(f"{path} is a symbolic link; a build context holds plain files")
        if path.is_file():
            files[path.relative_to(context_directory).as_posix()] = path.read_bytes()
    return files


def add_environment(task_directory, context_files):
    environment_directory = task_directory / "environment"
    if environment_directory.exists():
        raise GeneratedSourceError(f"{task_directory.name}: the adapter wrote environment/, which is the image's")
    for relative_path, content in context_files.items():
        write_task_file(environment_directory / relative_path, content)


def generation_context(descriptor, images_lock):
    try:
        docker_image = pinned_image(images_lock)
    except EnvironmentImageError as error:
        raise GeneratedSourceError(str(error)) from None
    return GenerationContext(
        dataset=descriptor["name"],
        version=descriptor["version"],
        canary=descriptor["canary"],
        docker_image=docker_image,
    )


def generate_tasks(descriptor, destination, images_lock, upstream_cache=None):
    source = descriptor["source"]
    adapter = adapter_module(source["adapter"])
    names = sorted(upstream_file["name"] for upstream_file in source["upstream_files"])
    if names != sorted(adapter.UPSTREAM_FILES):
        raise GeneratedSourceError(
            f"the descriptor's upstream files are {names}, the adapter reads {sorted(adapter.UPSTREAM_FILES)}"
        )
    upstream_paths = fetched_upstream_files(source["upstream_files"], destination / "upstream", upstream_cache)
    tasks_directory = destination / "tasks"
    tasks_directory.mkdir()
    task_names = adapter.generate(upstream_paths, tasks_directory, generation_context(descriptor, images_lock))
    written = sorted(entry.name for entry in tasks_directory.iterdir())
    if sorted(task_names) != written:
        raise GeneratedSourceError(f"the adapter reported {len(task_names)} tasks but wrote {len(written)}")
    if len(written) != source["task_count"]:
        raise GeneratedSourceError(f"the adapter wrote {len(written)} tasks, the descriptor declares {source['task_count']}")
    image = built_image(descriptor["environment"]["image"])
    context_files = build_context_files(REPOSITORY_ROOT / image["context"])
    for name in written:
        add_environment(tasks_directory / name, context_files)
    return tasks_directory, written


def package_digests(tasks_directory, task_names):
    return {name: package_digest(tasks_directory / name) for name in sorted(task_names)}


def dump_generated_lock(digests):
    return json.dumps({name: digests[name] for name in sorted(digests)}, indent=2) + "\n"


def lock_differences(locked, generated):
    differences = []
    for name in sorted(set(locked) | set(generated)):
        if name not in generated:
            differences.append(f"{name}: in {GENERATED_LOCK_FILENAME}, not generated")
        elif name not in locked:
            differences.append(f"{name}: generated, not in {GENERATED_LOCK_FILENAME}")
        elif locked[name] != generated[name]:
            differences.append(f"{name}: generated {generated[name]}, {GENERATED_LOCK_FILENAME} has {locked[name]}")
    return differences


def repository_commit():
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise GeneratedSourceError(f"cannot tell this repository's commit: {completed.stderr.strip()}")
    return completed.stdout.strip()


class DescriptorDumper(yaml.SafeDumper):
    pass


def represent_string(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


DescriptorDumper.add_representer(str, represent_string)


def dump_descriptor(descriptor):
    return yaml.dump(descriptor, Dumper=DescriptorDumper, sort_keys=False, allow_unicode=True, width=100)


def packed_descriptor(descriptor, images_lock, task_names, commit):
    packed = {}
    for key, value in descriptor.items():
        if key == "source":
            packed[key] = {
                "git_url": f"{PUBLISHED_REPOSITORY_URL}.git",
                "commit": commit,
                "path": value["adapter"],
                "task_count": value["task_count"],
            }
        elif key == "environment":
            packed[key] = {
                "policy": "pinned-by-digest",
                "images": {name: images_lock[name]["pinned"] for name in sorted(task_names)},
            }
        else:
            packed[key] = copy.deepcopy(value)
    return packed


def prepare_for_packing(descriptor_path, destination, allow_unfilled_lock=False, write_lock=False, upstream_cache=None):
    descriptor_path = pathlib.Path(descriptor_path)
    version_directory = descriptor_path.parent
    descriptor = load_descriptor(descriptor_path)
    tag = descriptor["environment"]["image"]
    try:
        images_lock = load_images_lock(version_directory / IMAGES_LOCK_FILENAME)
    except (OSError, EnvironmentImageError) as error:
        raise GeneratedSourceError(str(error)) from None
    if not images_lock and not allow_unfilled_lock:
        raise GeneratedSourceError(unfilled_images_lock_message(tag))
    destination.mkdir(parents=True)
    tasks_directory, task_names = generate_tasks(descriptor, destination, images_lock, upstream_cache)
    digests = package_digests(tasks_directory, task_names)
    lock_path = version_directory / GENERATED_LOCK_FILENAME
    if write_lock:
        lock_path.write_text(dump_generated_lock(digests), encoding="utf-8")
    else:
        locked = load_generated_lock(lock_path) if lock_path.is_file() else {}
        differences = lock_differences(locked, digests)
        if differences:
            shown = "\n  ".join(differences[:REPORTED_DIFFERENCES])
            more = len(differences) - REPORTED_DIFFERENCES
            raise GeneratedSourceError(
                f"{len(differences)} tasks differ from {GENERATED_LOCK_FILENAME}:\n  {shown}"
                + (f"\n  and {more} more" if more > 0 else "")
            )
    if images_lock:
        problems = images_lock_problems(images_lock, tag, task_names)
        if problems:
            raise GeneratedSourceError(f"{IMAGES_LOCK_FILENAME}: " + "; ".join(problems))
        packed_path = destination / DESCRIPTOR_FILENAME
        packed = packed_descriptor(descriptor, images_lock, task_names, repository_commit())
        packed_path.write_text(dump_descriptor(packed), encoding="utf-8")
        return tasks_directory, task_names, packed_path
    return tasks_directory, task_names, None


def versions_built_on(tag):
    versions = []
    for version_directory in version_directories():
        descriptor = load_descriptor(version_directory / DESCRIPTOR_FILENAME)
        if is_generated(descriptor) and descriptor["environment"].get("image") == tag:
            versions.append(version_directory)
    return versions


def lock_image(tag, digest, upstream_cache=None):
    versions = versions_built_on(tag)
    if not versions:
        raise GeneratedSourceError(f"no generated dataset version runs in {tag}")
    entry = images_lock_entry(tag, digest)
    for version_directory in versions:
        task_names = sorted(load_generated_lock(version_directory / GENERATED_LOCK_FILENAME))
        lock = {name: dict(entry) for name in task_names}
        (version_directory / IMAGES_LOCK_FILENAME).write_text(dump_images_lock(lock), encoding="utf-8")
        with tempfile.TemporaryDirectory() as workspace:
            prepare_for_packing(
                version_directory / DESCRIPTOR_FILENAME,
                pathlib.Path(workspace) / "generated",
                write_lock=True,
                upstream_cache=upstream_cache,
            )
    return versions


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Generate a dataset version's task directories.")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--allow-unfilled-lock", action="store_true")
    generate.add_argument("--write-lock", action="store_true")
    generate.add_argument("--upstream-cache", type=pathlib.Path)
    generate.add_argument("descriptor", type=pathlib.Path)
    generate.add_argument("destination", type=pathlib.Path)
    lock = commands.add_parser("lock-image")
    lock.add_argument("--upstream-cache", type=pathlib.Path)
    lock.add_argument("tag")
    lock.add_argument("digest")
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    try:
        if options.command == "lock-image":
            for version_directory in lock_image(options.tag, options.digest, options.upstream_cache):
                print(f"locked {version_directory.relative_to(REPOSITORY_ROOT)} to {options.tag}@{options.digest}")
            return 0
        if options.destination.exists():
            print(f"generated_source.py: {options.destination} already exists", file=sys.stderr)
            return 2
        tasks_directory, task_names, packed_path = prepare_for_packing(
            options.descriptor,
            options.destination,
            allow_unfilled_lock=options.allow_unfilled_lock,
            write_lock=options.write_lock,
            upstream_cache=options.upstream_cache,
        )
    except (GeneratedSourceError, GeneratedLockError, EnvironmentImageError) as error:
        print(f"generated_source.py: {error}", file=sys.stderr)
        return 1
    checked = "wrote" if options.write_lock else "matching"
    print(f"{len(task_names)} tasks in {tasks_directory}, {checked} {GENERATED_LOCK_FILENAME}")
    if packed_path:
        print(f"pack with {packed_path}")
    else:
        print(f"{IMAGES_LOCK_FILENAME} is not filled yet: the tasks name no docker_image, and nothing is ready to pack")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
