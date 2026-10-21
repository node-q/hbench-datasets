"""Merge the Mirror images workflow's shard locks into one images.lock.json, checked against the plan.

Usage: mirror_merge.py --plan mirror-plan.json --output images.lock.json SHARD_LOCK...
"""

import argparse
import json
import pathlib
import sys

from images_lock import LockError, dump_images_lock, entry_problems, load_images_lock


def merged_lock(plan, shard_locks):
    planned_images = {image["task"]: image for shard in plan["shards"] for image in shard["images"]}
    lock = {}
    problems = []
    for origin, shard_lock in shard_locks:
        for task, entry in shard_lock.items():
            if task in lock:
                problems.append(f"{task}: locked by more than one shard, the second time in {origin}")
                continue
            lock[task] = entry
    for task, entry in lock.items():
        planned_image = planned_images.get(task)
        if planned_image is None:
            problems.append(f"{task}: is not in the plan")
            continue
        problems += entry_problems(task, entry, plan["dataset"], "pinned-mirror")
        if isinstance(entry, dict):
            for key in ("source", "mirror_tag"):
                if entry.get(key) != planned_image[key]:
                    problems.append(
                        f"{task}: {key} is {entry.get(key)!r}, the plan has {planned_image[key]!r}"
                    )
    missing = sorted(set(planned_images) - set(lock))
    if missing:
        problems.append(f"no shard locked {', '.join(missing)}: re-run the shards that failed")
    if problems:
        raise LockError("the shard locks do not make up the plan:\n  " + "\n  ".join(problems))
    return {task: lock[task] for task in sorted(lock)}


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Merge shard locks into images.lock.json.")
    parser.add_argument("--plan", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("shard_locks", nargs="+", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    try:
        plan = json.loads(options.plan.read_text(encoding="utf-8"))
        shard_locks = [(path.name, load_images_lock(path)) for path in options.shard_locks]
        lock = merged_lock(plan, shard_locks)
    except LockError as error:
        print(f"mirror_merge.py: {error}", file=sys.stderr)
        return 1
    options.output.write_text(dump_images_lock(lock), encoding="utf-8")
    print(f"{plan['dataset']}: {len(lock)} images locked in {options.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
