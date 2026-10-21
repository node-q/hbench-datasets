"""Deterministic writing of task files: UTF-8, LF line endings, fixed modes, no timestamps."""

import json
import pathlib
import re

EXECUTABLE_SUFFIXES = (".sh",)
EXECUTABLE_MODE = 0o755
FILE_MODE = 0o644
DIRECTORY_MODE = 0o755


class TaskWritingError(ValueError):
    pass


def file_mode(path):
    return EXECUTABLE_MODE if pathlib.PurePath(path).suffix in EXECUTABLE_SUFFIXES else FILE_MODE


def write_task_file(path, content):
    path = pathlib.Path(path)
    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    if b"\r" in data and isinstance(content, str):
        raise TaskWritingError(f"{path.name} has carriage returns; task files use LF line endings")
    for directory in reversed(path.parents):
        if not directory.exists():
            directory.mkdir()
            directory.chmod(DIRECTORY_MODE)
    path.write_bytes(data)
    path.chmod(file_mode(path))


def write_task(task_directory, files):
    task_directory = pathlib.Path(task_directory)
    if task_directory.exists():
        raise TaskWritingError(f"{task_directory} exists already")
    task_directory.mkdir(parents=True)
    task_directory.chmod(DIRECTORY_MODE)
    for relative_path in sorted(files):
        if pathlib.PurePosixPath(relative_path).is_absolute() or ".." in pathlib.PurePosixPath(relative_path).parts:
            raise TaskWritingError(f"{relative_path!r} is not a path inside the task")
        write_task_file(task_directory / relative_path, files[relative_path])


def with_canary(text, canary):
    if text.startswith("#!"):
        shebang, _, rest = text.partition("\n")
        return f"{shebang}\n# {canary}\n{rest}"
    return f"# {canary}\n{text}"


def html_canary(canary):
    return f"<!-- {canary} -->\n"


def toml_string(value):
    if not value.isascii() or not value.isprintable():
        raise TaskWritingError(f"{value!r} is not printable ASCII")
    return json.dumps(value)


def toml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return toml_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    raise TaskWritingError(f"{value!r} has no TOML form here")


def task_toml(top_level, tables):
    lines = [f"{key} = {toml_value(value)}" for key, value in top_level.items()]
    for table, entries in tables.items():
        lines += ["", f"[{table}]"]
        lines += [f"{key} = {toml_value(value)}" for key, value in entries.items() if value is not None]
    return "\n".join(lines) + "\n"


def code_fence(code):
    longest_backtick_run = max((len(run) for run in re.findall(r"`+", code)), default=0)
    return "`" * max(3, longest_backtick_run + 1)


def canonical_json(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
