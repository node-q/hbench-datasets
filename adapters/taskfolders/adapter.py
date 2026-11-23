"""Write the task directories of an open Actuaria test set from its exported tasks, tasks.tar.xz.

The open test sets (docs/open-test-sets.md) are written and checked in node-q's own task repository, which builds
each task's directory and exports them as one reproducible tar.xz (its scripts/export_open.py). That file is
published as an asset of a GitHub release of this repository and pinned by sha256 in the version's source.yaml.

Each exported task keeps its instruction, its documents (environment/, which hbench copies into the image's /app),
its answer key (tests/expected.json), its checker (tests/verify.py), its test.sh and its oracle
(solution/decision.json and solve.sh), byte for byte, except:

- the directory, [task].name and every quoted name in task.toml (its tags) lose the "hb-int-" prefix of node-q's
  own names (hb-int-flsa-overtime-bonus-01 becomes flsa-overtime-bonus-01), and [task].name is the bare directory
  name;
- [environment].docker_image is this repository's image for the task, from images.lock.json;
- tests/verify.py gets the canary as its first line, and tests/expected.json and solution/decision.json a
  "canary" key, so that every file of tests/ and solution/ carries it (the checker reads neither key).

task_facts() reads what a listing counts from the written tasks: each task's kind of work, difficulty and number of
graded fields, which tasks.json next to the descriptor records.
"""

import json
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib

from adapters.common.writing import with_canary, write_task

UPSTREAM_FILE_NAME = "tasks.tar.xz"
UPSTREAM_FILES = (UPSTREAM_FILE_NAME,)
EXPORTED_PREFIX = "hb-int-"
TASK_FILES = ("task.toml", "instruction.md", "tests/test.sh", "tests/verify.py", "tests/expected.json",
              "solution/solve.sh", "solution/decision.json")
NAME_LINE = re.compile(r'^name = "[^"\n]*"$', re.M)
IMAGE_LINE = re.compile(r'^docker_image = "[^"\n]*"$', re.M)
FACTS_NAME = "tasks.json"


class AdapterError(ValueError):
    pass


def task_name(exported):
    return exported.removeprefix(EXPORTED_PREFIX)


def exported_tasks(archive_path):
    """{exported task name: {relative path: bytes}}, refusing anything but plain files and directories."""
    tasks = {}
    with tarfile.open(archive_path, mode="r:xz") as archive:
        for member in archive.getmembers():
            path = pathlib.PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise AdapterError(f"{member.name} is not a path inside the archive")
            if member.isdir():
                continue
            if not member.isfile():
                raise AdapterError(f"{member.name} is not a plain file")
            if len(path.parts) < 2:
                raise AdapterError(f"{member.name} is not inside a task directory")
            tasks.setdefault(path.parts[0], {})[pathlib.PurePosixPath(*path.parts[1:]).as_posix()] = (
                archive.extractfile(member).read()
            )
    return tasks


def with_canary_key(json_bytes, canary):
    document = json.loads(json_bytes.decode("utf-8"))
    if not isinstance(document, dict) or "canary" in document:
        raise AdapterError("an answer file is not a JSON object, or has a canary key already")
    return json.dumps({**document, "canary": canary}, indent=2, ensure_ascii=False) + "\n"


def task_files(name, exported_files, context):
    missing = [path for path in TASK_FILES if path not in exported_files]
    if missing:
        raise AdapterError(f"{name}: the export has no {', '.join(missing)}")
    text = {path: data.decode("utf-8") for path, data in exported_files.items()}
    manifest = text["task.toml"]
    if len(NAME_LINE.findall(manifest)) != 1 or len(IMAGE_LINE.findall(manifest)) != 1:
        raise AdapterError(f"{name}: task.toml does not have exactly one name and one docker_image")
    image = context.docker_image_for(name)
    if image is None:
        raise AdapterError(f"{name}: the version names no image for this task")
    manifest = NAME_LINE.sub(f'name = "{name}"', manifest)
    manifest = IMAGE_LINE.sub(f'docker_image = "{image}"', manifest)
    manifest = manifest.replace(f'"{EXPORTED_PREFIX}', '"')
    if not text["instruction.md"].startswith(f"<!-- {context.canary} -->\n"):
        raise AdapterError(f"{name}: the instruction does not start with the version's canary")
    files = dict(text)
    files["task.toml"] = manifest
    files["tests/verify.py"] = with_canary(text["tests/verify.py"], context.canary)
    files["tests/expected.json"] = with_canary_key(exported_files["tests/expected.json"], context.canary)
    files["solution/decision.json"] = with_canary_key(exported_files["solution/decision.json"], context.canary)
    return files


def generate(upstream_files, out_dir, context):
    exported = exported_tasks(upstream_files[UPSTREAM_FILE_NAME])
    names = {}
    for exported_name in sorted(exported):
        name = task_name(exported_name)
        if name in names:
            raise AdapterError(f"{exported_name} and {names[name]} would both be {name}")
        names[name] = exported_name
        write_task(pathlib.Path(out_dir) / name, task_files(name, exported[exported_name], context))
    return sorted(names)


def task_problems(task_directory):
    task_directory = pathlib.Path(task_directory)
    try:
        expected = json.loads((task_directory / "tests" / "expected.json").read_text(encoding="utf-8"))
        decision = json.loads((task_directory / "solution" / "decision.json").read_text(encoding="utf-8"))
        instruction = (task_directory / "instruction.md").read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        return [f"cannot read the task: {error}"]
    problems = []
    paths = [field.get("path") for field in expected.get("fields", [])]
    if not paths:
        problems.append("tests/expected.json has no fields")
    if any(re.match(r"[A-Za-z0-9_]*", path).group(0) not in decision for path in paths if isinstance(path, str)):
        problems.append("solution/decision.json does not answer every field")
    if "/app/output/decision.json" not in instruction:
        problems.append("the instruction does not ask for /app/output/decision.json")
    if not any((task_directory / "environment").rglob("*")):
        problems.append("environment/ holds no document")
    return problems


def reward(task_directory, decision_path):
    with tempfile.TemporaryDirectory() as output:
        subprocess.run(
            [sys.executable, str(task_directory / "tests" / "verify.py"), str(task_directory / "tests" / "expected.json"),
             str(decision_path), output],
            check=True, stdout=subprocess.DEVNULL,
        )
        return json.loads((pathlib.Path(output) / "reward.json").read_text(encoding="utf-8"))["reward"]


def verify_tasks(tasks_directory, jobs=1, names=()):
    """Each task's checker gives its oracle 1 and an empty answer 0. Returns 0 when all do, else 1."""
    tasks_directory = pathlib.Path(tasks_directory)
    failures = []
    with tempfile.TemporaryDirectory() as scratch:
        empty = pathlib.Path(scratch) / "decision.json"
        empty.write_text("{}\n", encoding="utf-8")
        for task in sorted(p for p in tasks_directory.iterdir() if p.is_dir() and (not names or p.name in names)):
            oracle = reward(task, task / "solution" / "decision.json")
            wrong = reward(task, empty)
            if (oracle, wrong) != (1, 0):
                failures.append(f"{task.name}: the oracle scores {oracle} and an empty answer {wrong}")
    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


def task_facts(tasks_directory):
    """{task: {kind, difficulty, fields}} from the written tasks, for tasks.json and the listing."""
    facts = {}
    for task in sorted(p for p in pathlib.Path(tasks_directory).iterdir() if p.is_dir()):
        manifest = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
        expected = json.loads((task / "tests" / "expected.json").read_text(encoding="utf-8"))
        facts[task.name] = {
            "kind": manifest["metadata"]["task_type"],
            "difficulty": manifest["metadata"]["difficulty"],
            "fields": len(expected["fields"]),
        }
    return facts


def version_problems(version_directory, tasks_directory):
    """tasks.json must be what the tasks say, and each task's checker must give its oracle 1 and an empty answer 0."""
    problems = []
    path = pathlib.Path(version_directory) / FACTS_NAME
    facts = task_facts(tasks_directory)
    if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != facts:
        problems.append(f"{FACTS_NAME} is missing or differs from the tasks: run python -m adapters.taskfolders.facts "
                        f"{pathlib.Path(version_directory).as_posix()}")
    if verify_tasks(tasks_directory) != 0:
        problems.append("a task's checker does not give its oracle 1 and an empty answer 0")
    return problems


def facts_text(facts):
    return json.dumps(facts, indent=2, sort_keys=True) + "\n"
