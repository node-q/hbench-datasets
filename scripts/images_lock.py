import json
import pathlib
import re

IMAGES_LOCK_FILENAME = "images.lock.json"
MIRROR_NAMESPACE = "ghcr.io/node-q/hbench-envs"
MAXIMUM_TAG_LENGTH = 128
ENTRY_KEY_ORDER = ("source", "source_digest", "pinned", "mirror_tag")
ENTRY_KEYS_BY_POLICY = {
    "pinned-mirror": ("source", "source_digest", "pinned", "mirror_tag"),
    "pinned-upstream": ("source", "source_digest", "pinned"),
}
LOCKED_POLICIES = tuple(ENTRY_KEYS_BY_POLICY)
LOCK_WORKFLOW_BY_POLICY = {"pinned-mirror": "Mirror images", "pinned-upstream": "Pin images"}

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
TASK_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
MIRROR_REFERENCE_PATTERN = re.compile(
    r"^"
    + re.escape(MIRROR_NAMESPACE)
    + r"/(?P<dataset>[a-z0-9]+(?:-[a-z0-9]+)*)@(?P<digest>sha256:[0-9a-f]{64})$"
)


class LockError(ValueError):
    pass


def mirror_repository(dataset):
    return f"{MIRROR_NAMESPACE}/{dataset}"


def repository_of(reference):
    if "@" in reference:
        return reference.split("@", 1)[0]
    registry_and_path, _, last_component = reference.rpartition("/")
    repository_name = last_component.split(":", 1)[0]
    return f"{registry_and_path}/{repository_name}" if registry_and_path else repository_name


def source_tag(source_reference):
    if "@" in source_reference:
        raise LockError(f"{source_reference!r} is pinned by digest already, so it has no tag to resolve")
    last_component = source_reference.rsplit("/", 1)[-1]
    if ":" not in last_component:
        raise LockError(f"{source_reference!r} names no tag")
    return last_component.rsplit(":", 1)[1]


def tag_problems(tag):
    problems = []
    if len(tag) > MAXIMUM_TAG_LENGTH:
        problems.append(f"tag {tag!r} is {len(tag)} characters, more than an OCI tag's {MAXIMUM_TAG_LENGTH}")
    if not TAG_PATTERN.match(tag):
        problems.append(f"tag {tag!r} is not an OCI tag, [A-Za-z0-9_][A-Za-z0-9_.-]*")
    return problems


def mirror_tag(task, source_reference):
    tag = f"{task}-{source_tag(source_reference)}"
    problems = tag_problems(tag)
    if problems:
        raise LockError("; ".join(problems))
    return tag


def upstream_pin(source_reference, digest):
    return f"{repository_of(source_reference)}@{digest}"


def unfilled_lock_message(policy):
    return (
        f"{IMAGES_LOCK_FILENAME} is not filled yet, so this version cannot be published: run the "
        f"{LOCK_WORKFLOW_BY_POLICY[policy]} workflow and commit the {IMAGES_LOCK_FILENAME} it writes"
    )


def refuse_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise LockError(f"names {key!r} twice")
        seen[key] = value
    return seen


def parse_images_lock(text, origin=IMAGES_LOCK_FILENAME):
    try:
        lock = json.loads(text, object_pairs_hook=refuse_duplicate_keys)
    except json.JSONDecodeError as error:
        raise LockError(f"{origin} is not valid JSON: {error}") from None
    except LockError as error:
        raise LockError(f"{origin} {error}") from None
    if not isinstance(lock, dict):
        raise LockError(f"{origin} is not a JSON object of task name to image")
    return lock


def load_images_lock(path):
    with open(path, encoding="utf-8") as stream:
        return parse_images_lock(stream.read(), origin=pathlib.Path(path).name)


def dump_images_lock(lock):
    ordered = {
        task: {key: lock[task][key] for key in ENTRY_KEY_ORDER if key in lock[task]} for task in sorted(lock)
    }
    return json.dumps(ordered, indent=2) + "\n"


def mirror_entry_problems(task, entry, dataset):
    problems = []
    try:
        expected_tag = mirror_tag(task, entry["source"])
    except LockError as error:
        problems.append(f"{task}: {error}")
    else:
        if entry["mirror_tag"] != expected_tag:
            problems.append(f"{task}: mirror_tag is {entry['mirror_tag']!r}, expected {expected_tag!r}")
    match = MIRROR_REFERENCE_PATTERN.match(entry["pinned"])
    if not match:
        problems.append(
            f"{task}: pinned {entry['pinned']!r} is not a digest reference under {MIRROR_NAMESPACE}/"
        )
    elif match["dataset"] != dataset:
        problems.append(f"{task}: pinned {entry['pinned']!r} is not in {mirror_repository(dataset)}")
    elif match["digest"] != entry["source_digest"]:
        problems.append(
            f"{task}: the mirror's digest {match['digest']} differs from source_digest {entry['source_digest']}, "
            "but a mirror copies its source unchanged"
        )
    return problems


def upstream_entry_problems(task, entry):
    try:
        source_tag(entry["source"])
    except LockError as error:
        return [f"{task}: {error}"]
    expected_pin = upstream_pin(entry["source"], entry["source_digest"])
    if entry["pinned"] != expected_pin:
        return [
            f"{task}: pinned is {entry['pinned']!r}, expected the source pinned by its digest, {expected_pin!r}"
        ]
    return []


def entry_problems(task, entry, dataset, policy, declared_image=None):
    expected_keys = ENTRY_KEYS_BY_POLICY[policy]
    if not TASK_NAME_PATTERN.match(task):
        return [f"{task!r} is not a task directory name"]
    if not isinstance(entry, dict):
        return [f"{task}: is not an object of {', '.join(expected_keys)}"]
    if sorted(entry) != sorted(expected_keys) or not all(
        isinstance(entry[key], str) for key in expected_keys
    ):
        return [f"{task}: has {sorted(entry)}, a {policy} lock has exactly the strings {list(expected_keys)}"]
    problems = []
    declared_source = declared_image.replace("{task}", task) if declared_image is not None else None
    if declared_source is not None and entry["source"] != declared_source:
        problems.append(f"{task}: source is {entry['source']!r}, the descriptor declares {declared_source!r}")
    if not DIGEST_PATTERN.match(entry["source_digest"]):
        return problems + [
            f"{task}: source_digest {entry['source_digest']!r} is not sha256:<64 lowercase hex digits>"
        ]
    if policy == "pinned-mirror":
        return problems + mirror_entry_problems(task, entry, dataset)
    return problems + upstream_entry_problems(task, entry)


def lock_problems(lock, dataset, policy, task_count, declared_image=None):
    problems = []
    if len(lock) != task_count:
        problems.append(f"locks {len(lock)} images for {task_count} tasks")
    if list(lock) != sorted(lock):
        problems.append(
            f"lists its tasks out of order; the {LOCK_WORKFLOW_BY_POLICY[policy]} workflow sorts them"
        )
    for task, entry in lock.items():
        problems += entry_problems(task, entry, dataset, policy, declared_image)
    return problems
