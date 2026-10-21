"""Compute hbench's package digest of task directories, as `hbench tasks digest` prints it.

Usage: package_digest.py TASK_DIRECTORY [...]

The digest is sha256 over one "{relative path}\\0{sha256 of the file}\\n" line per package file, sorted
by path, written sha256:<hex>. The package files are task.toml, instruction.md, README.md and
trajectory.json, and every file under environment/, tests/, solution/ and steps/, less hbench's
default ignores. A task with its own .gitignore is refused: its patterns are not reimplemented here.
"""

import fnmatch
import hashlib
import json
import pathlib
import sys

PACKAGE_FILES = ("task.toml", "instruction.md", "README.md", "trajectory.json")
PACKAGE_DIRECTORIES = ("environment", "tests", "solution", "steps")
IGNORED_DIRECTORY_NAMES = ("__pycache__",)
IGNORED_NAME_PATTERNS = ("*.pyc", ".DS_Store", "*.swp", "*.swo", "*~")


class PackageDigestError(ValueError):
    pass


def files_under(directory):
    files = []
    for entry in sorted(directory.iterdir(), key=lambda entry: entry.name):
        if entry.is_dir() and not entry.is_symlink():
            files += files_under(entry)
        elif entry.is_file():
            files.append(entry)
    return files


def is_ignored(relative_path):
    components = relative_path.split("/")
    if any(component in IGNORED_DIRECTORY_NAMES for component in components[:-1]):
        return True
    return any(
        fnmatch.fnmatchcase(component, pattern)
        for component in components
        for pattern in IGNORED_NAME_PATTERNS
    )


def package_files(task_directory):
    task_directory = pathlib.Path(task_directory)
    if (task_directory / ".gitignore").exists():
        raise PackageDigestError(
            f"{task_directory.name} has a .gitignore, whose patterns this digest does not apply"
        )
    files = [task_directory / name for name in PACKAGE_FILES if (task_directory / name).exists()]
    for name in PACKAGE_DIRECTORIES:
        if (task_directory / name).exists():
            files += files_under(task_directory / name)
    relative_paths = (file.relative_to(task_directory).as_posix() for file in files)
    return sorted(path for path in relative_paths if not is_ignored(path))


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def package_digest(task_directory):
    task_directory = pathlib.Path(task_directory)
    digest = hashlib.sha256()
    for relative_path in package_files(task_directory):
        digest.update(f"{relative_path}\0{file_sha256(task_directory / relative_path)}\n".encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def main(arguments):
    if not arguments:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        digests = {pathlib.Path(argument).name: package_digest(argument) for argument in arguments}
    except PackageDigestError as error:
        print(f"package_digest.py: {error}", file=sys.stderr)
        return 1
    print(json.dumps(digests, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
