"""Plan the Mirror images workflow: each task's declared image, its mirror tag, and the shards that copy them.

Usage: mirror_plan.py datasets/<name>/<version>/source.yaml CHECKOUT_DIRECTORY
                      [--images-per-shard N] --output mirror-plan.json

Fetches the source at its pinned commit into CHECKOUT_DIRECTORY and reads each task's docker_image,
checked against the descriptor's declared_image when it has one.
"""

import argparse
import json
import math
import pathlib
import sys

from fetch_source import SourceError, fetch_declared_images
from images_lock import LockError, mirror_name, mirror_repository, mirror_tag
from source_descriptor import load_descriptor

DEFAULT_IMAGES_PER_SHARD = 10


class PlanError(ValueError):
    pass


def planned_images(declared_images):
    images = []
    problems = []
    for task_name in sorted(declared_images):
        source = declared_images[task_name]
        try:
            images.append({"task": task_name, "source": source, "mirror_tag": mirror_tag(task_name, source)})
        except LockError as error:
            problems.append(f"{task_name}: {error}")
    if problems:
        raise PlanError("cannot mirror every task's image:\n  " + "\n  ".join(problems))
    return images


def shards(images, images_per_shard):
    if images_per_shard < 1:
        raise PlanError(f"images per shard must be at least 1, not {images_per_shard}")
    if not images:
        raise PlanError("there are no images to mirror")
    shard_count = math.ceil(len(images) / images_per_shard)
    smaller_shard_size, larger_shard_count = divmod(len(images), shard_count)
    planned_shards = []
    start = 0
    for shard_index in range(shard_count):
        size = smaller_shard_size + (1 if shard_index < larger_shard_count else 0)
        planned_shards.append({"shard": shard_index + 1, "images": images[start : start + size]})
        start += size
    return planned_shards


def mirror_plan(descriptor, declared_images, images_per_shard):
    return {
        "dataset": descriptor["name"],
        "version": descriptor["version"],
        "mirror_repository": mirror_repository(mirror_name(descriptor)),
        "shards": shards(planned_images(declared_images), images_per_shard),
    }


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Plan the copy of a dataset version's environment images.")
    parser.add_argument("descriptor", type=pathlib.Path)
    parser.add_argument("checkout_directory", type=pathlib.Path)
    parser.add_argument("--images-per-shard", type=int, default=DEFAULT_IMAGES_PER_SHARD)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    descriptor = load_descriptor(options.descriptor)
    label = f"{descriptor['name']}@{descriptor['version']}"
    try:
        declared_images = fetch_declared_images(descriptor, options.checkout_directory)
        plan = mirror_plan(descriptor, declared_images, options.images_per_shard)
    except (SourceError, PlanError) as error:
        print(f"mirror_plan.py: {label}: {error}", file=sys.stderr)
        return 1
    options.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    image_count = sum(len(shard["images"]) for shard in plan["shards"])
    print(f"{label}: {image_count} images to {plan['mirror_repository']} in {len(plan['shards'])} shards")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
