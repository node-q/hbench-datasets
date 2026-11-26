"""Writes or checks a dataset version's listing.json, what the Actuaria Market Place shows of it.

Usage: python scripts/listing.py [--check] [datasets/<name>/<version> ...]   (default: every version with a
listing.yaml)

listing.yaml and COVER.md are written by hand (schema/listing.v1.json). listing.json is listing.yaml plus what the
dataset itself says: the task count (source.yaml's task_count, which must match the lock's task names), each
repository's task count, the licence id and the registry. --check fails when a listing.json is missing or stale.

A version whose adapter records what each task is (tasks.json, adapters/taskfolders) also gets each kind of work's
task count, the number of graded fields and the difficulty from it; its families are keyed by those kinds.
"""

import collections
import json
import pathlib
import re
import sys

import jsonschema
import yaml

from generated_checks import GENERATED_LOCK_FILENAME
from images_lock import IMAGES_LOCK_FILENAME
from source_descriptor import DATASETS_DIR, DESCRIPTOR_FILENAME

ROOT = DATASETS_DIR.parent
SCHEMA_PATH = ROOT / "schema" / "listing.v1.json"
REGISTRY = "oci://ghcr.io/node-q/hbench-datasets"
LISTING_FILES = ("listing.yaml", "COVER.md", "listing.json")
TASK_FACTS = "tasks.json"
# Read by people choosing a test set, in the Market Place's words (its build refuses these, a price and "!").
BANNED = re.compile(r"\b(agent\w*|benchmark\w*|expert\w*|teams?|cases?)\b", re.I)
MACHINE_ONLY = re.compile(r"node-?q|hbench|ghcr|oci://|licenseref", re.I)
REPOSITORY_TASK = re.compile(r"(?P<owner>[A-Za-z0-9_.-]+?)__(?P<repo>[A-Za-z0-9_.-]+)-\d+")


class ListingError(ValueError):
    pass


def task_names(version_directory):
    for name in (GENERATED_LOCK_FILENAME, IMAGES_LOCK_FILENAME):
        path = version_directory / name
        if path.is_file():
            lock = json.loads(path.read_text(encoding="utf-8"))
            if lock:
                return sorted(lock)
    raise ListingError(f"{version_directory}: no lock names its tasks")


def repository_lines(names):
    counts = collections.Counter()
    for name in names:
        match = REPOSITORY_TASK.fullmatch(name)
        if not match:
            raise ListingError(f"task {name} does not name its repository (owner__repo-<number>)")
        counts[f"{match['owner']}/{match['repo']}"] += 1
    return [{"name": name, "tasks": tasks} for name, tasks in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def copy_problems(text):
    found = sorted({f"the word {m.group(0).lower()!r}" for m in BANNED.finditer(text)})
    found += sorted({f"the name {m.group(0).lower()!r}" for m in MACHINE_ONLY.finditer(text)})
    if "!" in text:
        found.append("an exclamation mark")
    return found


def build_listing(version_directory):
    version_directory = pathlib.Path(version_directory)
    written = yaml.safe_load((version_directory / "listing.yaml").read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(written))
    if errors:
        raise ListingError("\n".join(f"listing.yaml: {e.message}" for e in errors))
    descriptor = yaml.safe_load((version_directory / DESCRIPTOR_FILENAME).read_text(encoding="utf-8"))
    names = task_names(version_directory)
    tasks = descriptor["source"]["task_count"]
    if len(names) != tasks:
        raise ListingError(f"{version_directory}: the lock names {len(names)} tasks, source.yaml says {tasks}")
    cover = (version_directory / "COVER.md").read_text(encoding="utf-8")
    readable = [written["title"], written["summary"], written["description"], written["domain"], cover,
                written["licence"]["name"], written["licence"]["summary"], written["upstream"]["name"],
                written["upstream"]["by"], written.get("trade", "")]
    readable += [f"{f['name']} {f['what']}" for f in written["families"]]
    readable += [f"{g['title']} {g['detail']}" for g in written["you_get"]]
    problems = copy_problems("\n".join(readable))
    # Every "<n> test tasks" a reader sees is the dataset's own count.
    problems += [f"COVER.md says {n} test tasks, the dataset has {tasks}"
                 for n in re.findall(r"\b(\d+) test tasks\b", cover) if int(n) != tasks]
    if problems:
        raise ListingError(f"{version_directory}: " + "; ".join(problems))
    if len(written["families"]) > 1 and not (version_directory / TASK_FACTS).is_file():
        raise ListingError(f"{version_directory}: several kinds of work need {TASK_FACTS} to count their tasks")
    facts = None
    if (version_directory / TASK_FACTS).is_file():
        facts = json.loads((version_directory / TASK_FACTS).read_text(encoding="utf-8"))
        if sorted(facts) != names:
            raise ListingError(f"{version_directory}: {TASK_FACTS} does not describe the lock's tasks")
        kinds = collections.Counter(task["kind"] for task in facts.values())
        if sorted(kinds) != sorted(family["kind"] for family in written["families"]):
            raise ListingError(f"{version_directory}: the families' kinds are not the tasks' ({', '.join(sorted(kinds))})")
    families = [{**family, "tasks": kinds[family["kind"]] if facts else tasks} for family in written["families"]]
    listing = {
        "schema_version": 1,
        "name": descriptor["name"],
        "version": descriptor["version"],
        "type": "test-set",
        "format": written["format"],
        "title": written["title"],
        "summary": written["summary"],
        "description": written["description"],
        "domain": written["domain"],
        "group": written["group"],
        **({"trade": written["trade"]} if "trade" in written else {}),
        "status": written.get("status", "published"),
        "pricing": "free",
        "licence": {"id": descriptor["license"], **written["licence"]},
        "upstream": written["upstream"],
        "tasks": tasks,
        **({"graded_fields": sum(task["fields"] for task in facts.values()),
            "difficulty": {level: sum(task["difficulty"] == level for task in facts.values())
                           for level in ("easy", "medium", "hard")}} if facts else {}),
        "families": families,
        "lines": repository_lines(names) if written.get("lines") == "repository" else [],
        "lines_title": "Projects" if written.get("lines") == "repository" else None,
        "you_get": written["you_get"],
        **({"sample_task": written["sample_task"]} if "sample_task" in written else {}),
        "cover_letter": "COVER.md",
        "registry": {"url": REGISTRY, "name": descriptor["name"], "access": "public"},
    }
    return json.dumps(listing, indent=2, ensure_ascii=False) + "\n"


def listed_versions():
    return sorted(path.parent for path in DATASETS_DIR.glob("*/*/listing.yaml"))


def main(argv):
    check = "--check" in argv
    directories = [pathlib.Path(a) for a in argv if a != "--check"] or listed_versions()
    problems = []
    for directory in directories:
        try:
            text = build_listing(directory)
        except ListingError as error:
            problems.append(str(error))
            continue
        target = directory / "listing.json"
        if check:
            if not target.is_file() or target.read_text(encoding="utf-8") != text:
                problems.append(f"{target} is missing or stale: run python scripts/listing.py {directory}")
        else:
            target.write_text(text, encoding="utf-8")
            print(target)
    if problems:
        sys.exit("\n".join(problems))


if __name__ == "__main__":
    main(sys.argv[1:])
