"""Plan a Release dataset run: check each <set>@<version> on this checkout and say what the run would do.

Usage: release_plan.py [--markdown FILE] <set>@<version> [<set>@<version> ...]

The arguments may also be separated by commas, as the workflow's sets input allows. For each set, in order, it
checks that datasets/<set>/<version>/source.yaml exists and passes validate_sources.py --for-publish, and that its
images.lock.json is filled. When a lock is not filled it names the workflow run that fills it (Build images with
each image tag, or Mirror images or Pin images with the dataset and version); that run's locks are committed in a
pull request, so this script never starts it. It also lists the source releases of this repository that the
descriptor's upstream_files download from (such as sources-federal-register-1.0), with each asset's name and the
sha256 pinned for it, so that the workflow can check them against the release.

It prints the plan as JSON on stdout, and with --markdown also writes it as a table for the job summary. It exits 1,
after printing every problem on stderr, when any set cannot be released.
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.parse

from license_expression import get_spdx_licensing

from environment_images import version_image_tags
from generated_checks import GENERATED_LOCK_FILENAME, is_generated, load_generated_lock, unlocked_images
from images_lock import IMAGES_LOCK_FILENAME, LockError, load_images_lock
from source_descriptor import DATASETS_DIR, DESCRIPTOR_FILENAME, PUBLISHED_REPOSITORY_URL, load_descriptor
from validate_sources import locked_policy, schema_validator, version_directory_problems

SET_PATTERN = re.compile(
    r"^(?P<dataset>[a-z0-9]+(?:-[a-z0-9]+)*)@(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?)$"
)
RELEASE_DOWNLOAD_PREFIX = f"{PUBLISHED_REPOSITORY_URL}/releases/download/"
RELEASE_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ASSET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_SETS = 20


class PlanError(Exception):
    pass


def parse_sets(arguments):
    tokens = [token for argument in arguments for token in re.split(r"[\s,]+", argument) if token]
    if not tokens:
        raise PlanError("no sets given: name one or more as <set>@<version>, such as federal-register@1.0")
    if len(tokens) > MAX_SETS:
        raise PlanError(f"{len(tokens)} sets given; one run releases at most {MAX_SETS}")
    sets = []
    for token in tokens:
        match = SET_PATTERN.match(token)
        if not match:
            raise PlanError(f"{token!r} is not <set>@<version>, such as federal-register@1.0")
        pair = (match["dataset"], match["version"])
        if pair in sets:
            raise PlanError(f"{token} is named twice")
        sets.append(pair)
    return sets


def source_releases(descriptor):
    """The releases of this repository that upstream_files download from, as [{tag, assets: [{name, sha256}]}]."""
    releases = {}
    for upstream_file in descriptor.get("source", {}).get("upstream_files", []) or []:
        url = upstream_file.get("url", "")
        if not url.startswith(RELEASE_DOWNLOAD_PREFIX):
            continue
        parts = url[len(RELEASE_DOWNLOAD_PREFIX):].split("/")
        if len(parts) != 2:
            raise PlanError(f"{url} is not {RELEASE_DOWNLOAD_PREFIX}<tag>/<asset>")
        tag, name = (urllib.parse.unquote(part) for part in parts)
        if not (RELEASE_TAG_PATTERN.match(tag) and ASSET_NAME_PATTERN.match(name)):
            raise PlanError(f"{url} names a release tag or asset this workflow does not accept")
        sha256 = upstream_file.get("sha256", "")
        if not SHA256_PATTERN.match(sha256):
            raise PlanError(f"{url} has no sha256 pinned in {DESCRIPTOR_FILENAME}")
        assets = releases.setdefault(tag, [])
        if any(asset["name"] == name for asset in assets):
            raise PlanError(f"{url} is listed twice")
        assets.append({"name": name, "sha256": sha256, "url": url})
    return [{"tag": tag, "assets": assets} for tag, assets in releases.items()]


def lock_instruction(dataset, version, descriptor, version_directory):
    """None when the images lock is filled (or the policy has none), else what to run to fill it."""
    policy = locked_policy(descriptor)
    if policy is None:
        return None
    try:
        lock = load_images_lock(version_directory / IMAGES_LOCK_FILENAME)
    except (LockError, OSError) as error:
        return f"{IMAGES_LOCK_FILENAME} cannot be read: {error}"
    environment = descriptor["environment"]
    if policy == "built":
        if lock and is_generated(descriptor):
            task_names = sorted(load_generated_lock(version_directory / GENERATED_LOCK_FILENAME))
            images = unlocked_images(descriptor, lock, task_names)
        elif lock:
            images = []
        else:
            images = sorted({tag for _, tag in version_image_tags(environment)})
        if not images:
            return None
        runs = ", ".join(f"image={image}" for image in images)
        return (
            f"{IMAGES_LOCK_FILENAME} is not filled for {', '.join(images)}. Run Build images ({runs}), commit the "
            f"{IMAGES_LOCK_FILENAME} and {GENERATED_LOCK_FILENAME} from each run's locks artifact in a pull request, "
            "merge it, then run Release dataset again"
        )
    if lock:
        return None
    workflow = "Mirror images" if policy == "pinned-mirror" else "Pin images"
    return (
        f"{IMAGES_LOCK_FILENAME} is not filled yet. Run {workflow} (dataset={dataset}, version={version}), commit "
        "the lock it writes in a pull request, merge it, then run Release dataset again"
    )


def plan_set(dataset, version, validator, licensing, datasets_directory=DATASETS_DIR):
    version_directory = datasets_directory / dataset / version
    entry = {"dataset": dataset, "version": version, "policy": None, "releases": [], "problems": []}
    if not (version_directory / DESCRIPTOR_FILENAME).is_file():
        entry["problems"].append(
            f"datasets/{dataset}/{version}/{DESCRIPTOR_FILENAME} is not on this commit: merge its pull request first"
        )
        return entry
    descriptor = load_descriptor(version_directory / DESCRIPTOR_FILENAME)
    entry["policy"] = (descriptor.get("environment") or {}).get("policy")
    instruction = None
    try:
        instruction = lock_instruction(dataset, version, descriptor, version_directory)
    except Exception as error:  # A malformed descriptor is reported by the validation below.
        entry["problems"].append(f"cannot read its image locks: {error}")
    if instruction:
        entry["problems"].append(instruction)
    for problem in version_directory_problems(version_directory, validator, licensing, for_publish=True):
        if instruction and IMAGES_LOCK_FILENAME in problem and "not filled" in problem:
            continue
        entry["problems"].append(problem)
    try:
        entry["releases"] = source_releases(descriptor)
    except PlanError as error:
        entry["problems"].append(str(error))
    return entry


def markdown(plan):
    lines = ["| Set | Environment | Source release | Checks |", "|---|---|---|---|"]
    for entry in plan:
        releases = ", ".join(f"`{release['tag']}`" for release in entry["releases"]) or "none (fetched upstream)"
        checks = "; ".join(entry["problems"]) or "ready"
        lines.append(
            f"| `{entry['dataset']}@{entry['version']}` | {entry['policy'] or '-'} | {releases} | "
            f"{checks.replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--markdown", type=pathlib.Path)
    parser.add_argument("sets", nargs="+")
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    try:
        sets = parse_sets(options.sets)
    except PlanError as error:
        print(error, file=sys.stderr)
        return 1
    validator = schema_validator()
    licensing = get_spdx_licensing()
    plan = [plan_set(dataset, version, validator, licensing) for dataset, version in sets]
    json.dump({"sets": plan}, sys.stdout, indent=2)
    print()
    if options.markdown:
        options.markdown.write_text(markdown(plan), encoding="utf-8")
    problems = [f"{entry['dataset']}@{entry['version']}: {problem}" for entry in plan for problem in entry["problems"]]
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
