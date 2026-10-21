"""Check and describe the environment images this repository builds: tags of one GHCR package.

Usage:
  environment_images.py check
  environment_images.py bases
  environment_images.py image TAG
  environment_images.py base-of TAG

Every image is a tag of ghcr.io/node-q/hbench-envs: base-<name>-<tag> for a Docker Hub image copied
there with its digest unchanged (images/bases.yaml), and <dataset>-<version> for an image built from a
context in this repository (images/images.yaml). check verifies both lists, and that each built image's
Dockerfile starts FROM its base's copy pinned to the base's digest, so that no build pulls from Docker
Hub. bases prints "<source>@<digest> <target>" for each base. image prints a built image's entry as
JSON. base-of prints the pinned base a built image starts FROM.
"""

import json
import pathlib
import re
import sys

from images_lock import IMAGES_LOCK_FILENAME, MIRROR_NAMESPACE
from source_descriptor import REPOSITORY_ROOT, load_descriptor

ENVIRONMENT_REPOSITORY = MIRROR_NAMESPACE
IMAGES_DIRECTORY = REPOSITORY_ROOT / "images"
BASES_PATH = IMAGES_DIRECTORY / "bases.yaml"
IMAGES_PATH = IMAGES_DIRECTORY / "images.yaml"
SUPPORTED_PLATFORMS = ("linux/amd64", "linux/arm64")
MAXIMUM_TAG_LENGTH = 128
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
DOCKER_HUB_SOURCE_PATTERN = re.compile(
    r"^docker\.io/(?P<path>[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*):(?P<tag>[A-Za-z0-9_][A-Za-z0-9_.-]*)$"
)
BUILT_IMAGE_TAG_PATTERN = re.compile(
    r"^(?!base-)[a-z0-9]+(?:-[a-z0-9]+)*-(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?$"
)
CONTEXT_PATTERN = re.compile(r"^images/[a-z0-9]+(?:-[a-z0-9]+)*$")
FROM_LINE_PATTERN = re.compile(
    r"^FROM\s+(?:--platform=\S+\s+)?(?P<reference>\S+)(?:\s+AS\s+\S+)?$", re.IGNORECASE
)


class EnvironmentImageError(ValueError):
    pass


def tag_reference(tag):
    return f"{ENVIRONMENT_REPOSITORY}:{tag}"


def digest_reference(digest):
    return f"{ENVIRONMENT_REPOSITORY}@{digest}"


def base_tag_for(source):
    match = DOCKER_HUB_SOURCE_PATTERN.match(source)
    if not match:
        raise EnvironmentImageError(f"base source {source!r} is not docker.io/<repository>:<tag>")
    return f"base-{match['path'].rsplit('/', 1)[-1]}-{match['tag']}"


def load_list(path, key):
    document = load_descriptor(path)
    if not isinstance(document, dict) or not isinstance(document.get(key), list):
        raise EnvironmentImageError(f"{path.name} is not a mapping with a {key} list")
    return document[key]


def load_bases(path=BASES_PATH):
    return load_list(path, "bases")


def load_images(path=IMAGES_PATH):
    return load_list(path, "images")


def tag_problems(tag):
    problems = []
    if len(tag) > MAXIMUM_TAG_LENGTH:
        problems.append(f"tag {tag!r} is longer than an OCI tag's {MAXIMUM_TAG_LENGTH} characters")
    if not TAG_PATTERN.match(tag):
        problems.append(f"tag {tag!r} is not an OCI tag")
    return problems


def bases_problems(bases):
    problems = []
    tags = []
    for index, base in enumerate(bases):
        if not isinstance(base, dict) or sorted(base) != ["digest", "source", "tag"]:
            problems.append(f"bases[{index}] is not exactly tag, source and digest")
            continue
        tags.append(base["tag"])
        try:
            expected_tag = base_tag_for(base["source"])
        except EnvironmentImageError as error:
            problems.append(f"bases[{index}]: {error}")
            continue
        if base["tag"] != expected_tag:
            problems.append(f"bases[{index}]: tag is {base['tag']!r}, its source makes it {expected_tag!r}")
        problems += [f"bases[{index}]: {problem}" for problem in tag_problems(base["tag"])]
        if not DIGEST_PATTERN.match(str(base["digest"])):
            problems.append(f"bases[{index}]: digest {base['digest']!r} is not sha256:<64 lowercase hex digits>")
    duplicates = sorted({tag for tag in tags if tags.count(tag) > 1})
    if duplicates:
        problems.append(f"bases list {', '.join(duplicates)} more than once")
    return problems


def dockerfile_from_references(dockerfile_path):
    text = dockerfile_path.read_text(encoding="utf-8").replace("\\\n", " ")
    references = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = FROM_LINE_PATTERN.match(stripped)
        if match:
            references.append(match["reference"])
        elif stripped.upper().startswith("FROM"):
            references.append(stripped)
    return references


def image_problems(images, bases, repository_root=REPOSITORY_ROOT):
    problems = []
    bases_by_tag = {base["tag"]: base for base in bases if isinstance(base, dict) and "tag" in base}
    tags = []
    for index, image in enumerate(images):
        label = f"images[{index}]"
        if not isinstance(image, dict) or sorted(image) != ["base", "context", "platforms", "tag"]:
            problems.append(f"{label} is not exactly tag, context, base and platforms")
            continue
        tags.append(image["tag"])
        label = f"images[{index}] ({image['tag']})"
        if not BUILT_IMAGE_TAG_PATTERN.match(str(image["tag"])):
            problems.append(f"{label}: tag is not <dataset>-<version>")
        problems += [f"{label}: {problem}" for problem in tag_problems(str(image["tag"]))]
        platforms = image["platforms"]
        if not isinstance(platforms, list) or not platforms or not set(platforms) <= set(SUPPORTED_PLATFORMS):
            problems.append(f"{label}: platforms must be some of {', '.join(SUPPORTED_PLATFORMS)}")
        base = bases_by_tag.get(image["base"])
        if base is None:
            problems.append(f"{label}: base {image['base']!r} is not in bases.yaml")
        if not CONTEXT_PATTERN.match(str(image["context"])):
            problems.append(f"{label}: context {image['context']!r} is not images/<name>")
            continue
        dockerfile = repository_root / image["context"] / "Dockerfile"
        if not dockerfile.is_file():
            problems.append(f"{label}: {image['context']}/Dockerfile is missing")
            continue
        references = dockerfile_from_references(dockerfile)
        if base is not None:
            pinned_base = f"{tag_reference(base['tag'])}@{base['digest']}"
            if references != [pinned_base]:
                problems.append(
                    f"{label}: {image['context']}/Dockerfile starts FROM {references}, "
                    f"expected exactly one FROM {pinned_base}"
                )
    duplicates = sorted({tag for tag in tags if tags.count(tag) > 1})
    if duplicates:
        problems.append(f"images list {', '.join(duplicates)} more than once")
    return problems


def catalogue_problems(repository_root=REPOSITORY_ROOT):
    images_directory = repository_root / "images"
    try:
        bases = load_bases(images_directory / "bases.yaml")
        images = load_images(images_directory / "images.yaml")
    except (OSError, ValueError) as error:
        return [str(error)]
    return bases_problems(bases) + image_problems(images, bases, repository_root)


def built_image(tag, images=None):
    for image in load_images() if images is None else images:
        if image.get("tag") == tag:
            return image
    raise EnvironmentImageError(f"{tag!r} is not in images/images.yaml")


def pinned_base_of(tag):
    image = built_image(tag)
    base = next(base for base in load_bases() if base["tag"] == image["base"])
    return f"{tag_reference(base['tag'])}@{base['digest']}"


def images_lock_entry(tag, digest):
    if not DIGEST_PATTERN.match(digest):
        raise EnvironmentImageError(f"digest {digest!r} is not sha256:<64 lowercase hex digits>")
    return {"source": tag_reference(tag), "source_digest": digest, "pinned": digest_reference(digest)}


def pinned_image(lock):
    pinned = {entry["pinned"] for entry in lock.values()}
    if len(pinned) > 1:
        raise EnvironmentImageError(f"{IMAGES_LOCK_FILENAME} pins several images: {sorted(pinned)}")
    return next(iter(pinned), None)


def built_lock_problems(lock, tag, task_names):
    problems = []
    missing = sorted(set(task_names) - set(lock))
    unexpected = sorted(set(lock) - set(task_names))
    if missing or unexpected:
        problems.append(f"does not lock exactly the generated tasks: missing {missing}, unexpected {unexpected}")
    sources = sorted({entry.get("source") for entry in lock.values() if isinstance(entry, dict)})
    if sources and sources != [tag_reference(tag)]:
        problems.append(f"locks {sources}, but the descriptor's image is {tag_reference(tag)}")
    if len({entry.get("source_digest") for entry in lock.values() if isinstance(entry, dict)}) > 1:
        problems.append(f"pins several digests of {tag_reference(tag)}, which has one")
    return problems


def main(arguments):
    command, *rest = arguments or [""]
    try:
        if command == "check" and not rest:
            problems = catalogue_problems()
            for problem in problems:
                print(f"images: {problem}", file=sys.stderr)
            if not problems:
                print(f"ok  images: {len(load_bases())} bases, {len(load_images())} built images")
            return 1 if problems else 0
        if command == "bases" and not rest:
            for base in load_bases():
                print(f"{base['source']}@{base['digest']} {tag_reference(base['tag'])}")
            return 0
        if command == "image" and len(rest) == 1:
            print(json.dumps(built_image(rest[0]), sort_keys=True))
            return 0
        if command == "base-of" and len(rest) == 1:
            print(pinned_base_of(rest[0]))
            return 0
    except EnvironmentImageError as error:
        print(f"environment_images.py: {error}", file=sys.stderr)
        return 1
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
