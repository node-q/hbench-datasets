"""Write a taskfolders version's tasks.json: each task's kind of work, difficulty and number of graded fields.

Usage: python -m adapters.taskfolders.facts [--upstream-cache DIRECTORY] datasets/<name>/<version>

It generates the version's tasks (scripts/generated_source.py) into a temporary directory and reads them. The
listing (scripts/listing.py) counts from tasks.json; scripts/check_generated_tasks.py checks it.
"""

import argparse
import json
import pathlib
import sys
import tempfile

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import generated_source  # noqa: E402

from adapters.taskfolders.adapter import FACTS_NAME, facts_text, task_facts  # noqa: E402


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--upstream-cache", type=pathlib.Path)
    parser.add_argument("version_directory", type=pathlib.Path)
    options = parser.parse_args(arguments)
    with tempfile.TemporaryDirectory() as scratch:
        tasks_directory, _, _ = generated_source.prepare_for_packing(
            options.version_directory / "source.yaml", pathlib.Path(scratch) / "generated",
            allow_unfilled_lock=True, upstream_cache=options.upstream_cache,
        )
        facts = task_facts(tasks_directory)
    (options.version_directory / FACTS_NAME).write_text(facts_text(facts), encoding="utf-8")
    print(f"wrote {options.version_directory / FACTS_NAME}: {len(facts)} tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
