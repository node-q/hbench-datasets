"""Write HumanEvalFix task directories from HumanEvalPack's Python data, humanevalpack.jsonl.

Each problem becomes humanevalfix-<n>, HumanEvalFixTests as OctoPack defines it: the instruction shows
the problem's code with its bug (declaration and buggy_solution) and its tests, and asks for the fixed
code in /app/solution.py. tests/ holds check_fix.py, with the tests, the harness's Python imports less
numpy (which no problem uses) and its 10-second limit, and the reference solution (declaration and
canonical_solution), whose helper functions some tests call; solution/ holds the reference solution.
task.toml records the bug's type and symptom. The generic step adds environment/.
"""

import json
import pathlib
import re

from adapters.common.function_checker import SOLUTION_PATH, sandbox_checker_files
from adapters.common.function_checker.verify import WRONG_SOLUTION_TEMPLATE, Checker
from adapters.common.function_checker.verify import verify_tasks as verify_checker_tasks
from adapters.common.writing import canonical_json, code_fence, html_canary, task_toml, with_canary, write_task

ADAPTER_DIRECTORY = pathlib.Path(__file__).resolve().parent
CHECKER_PATH = ADAPTER_DIRECTORY / "check_fix.py"
UPSTREAM_FILE_NAME = "humanevalpack.jsonl"
UPSTREAM_FILES = (UPSTREAM_FILE_NAME,)
TASK_NAME_PREFIX = "humanevalfix-"
SUMMARY_NAME = "humanevalfix.json"
TASK_ID_PATTERN = re.compile(r"^Python/(?P<number>0|[1-9][0-9]*)$")
ENTRY_POINT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROBLEM_FIELDS = (
    "task_id",
    "declaration",
    "canonical_solution",
    "buggy_solution",
    "bug_type",
    "failure_symptoms",
    "entry_point",
    "test",
)
HARNESS_IMPORTS = (
    "import math",
    "import re",
    "import sys",
    "import copy",
    "import datetime",
    "import itertools",
    "import collections",
    "import heapq",
    "import statistics",
    "import functools",
    "import hashlib",
    "import string",
    "from typing import *",
    "from collections import *",
)
HARNESS_TIME_LIMIT_SECONDS = 10
INSTRUCTION_CODE_PATTERN = re.compile(r"^(?P<fence>`{3,})python\n(?P<code>.*?)^(?P=fence)$", re.MULTILINE | re.DOTALL)
AGENT_TIMEOUT_SECONDS = 600.0
VERIFIER_TIMEOUT_SECONDS = 120.0
BUILD_TIMEOUT_SECONDS = 600.0
CPUS = 1
MEMORY_MB = 4096
STORAGE_MB = 10240


class AdapterError(ValueError):
    pass


def task_name(task_id):
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        raise AdapterError(f"task_id {task_id!r} is not Python/<n>")
    return f"{TASK_NAME_PREFIX}{match['number']}"


def load_problems(upstream_path):
    problems = {}
    with open(upstream_path, encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            problem = json.loads(line)
            missing = [field for field in PROBLEM_FIELDS if field not in problem]
            if missing:
                raise AdapterError(f"line {line_number} has no {', '.join(missing)}")
            if not ENTRY_POINT_PATTERN.match(problem["entry_point"]):
                raise AdapterError(f"{problem['task_id']}: entry_point {problem['entry_point']!r} is not a name")
            if not problem["test"].rstrip().endswith(f"check({problem['entry_point']})"):
                raise AdapterError(f"{problem['task_id']}: the tests do not end by checking {problem['entry_point']}")
            name = task_name(problem["task_id"])
            if name in problems:
                raise AdapterError(f"{problem['task_id']} appears twice")
            problems[name] = problem
    return problems


def buggy_code(problem):
    return problem["declaration"] + problem["buggy_solution"]


def python_block(code):
    code = code.strip("\n") + "\n"
    fence = code_fence(code)
    return f"{fence}python\n{code}{fence}\n"


def instruction(problem, canary):
    entry_point = problem["entry_point"]
    return (
        html_canary(canary)
        + "\n"
        + f"Fix bugs in `{entry_point}`.\n"
        "\n"
        f"{python_block(buggy_code(problem))}"
        "\n"
        f"The code must pass these tests, which check `{entry_point}`:\n"
        "\n"
        f"{python_block(problem['test'])}"
        "\n"
        f"Write `{SOLUTION_PATH}`: the code above, with the bugs in `{entry_point}` fixed.\n"
        "\n"
        "- Keep the code's imports and the other functions it defines.\n"
        f"- The tests are run on `{entry_point}` from `{SOLUTION_PATH}`, as they are shown, within "
        f"{HARNESS_TIME_LIMIT_SECONDS} seconds in all.\n"
        "- Use Python 3.12 and its standard library only. Nothing is read from standard input, and nothing "
        "printed is checked.\n"
    )


def problem_document(problem, canary):
    return canonical_json(
        {
            "canary": canary,
            "task_id": problem["task_id"],
            "entry_point": problem["entry_point"],
            "prelude": "\n".join(HARNESS_IMPORTS) + "\n",
            "test": problem["test"],
            "time_limit": HARNESS_TIME_LIMIT_SECONDS,
        }
    )


def task_manifest(name, problem, docker_image):
    return task_toml(
        name,
        f"{problem['task_id']} from HumanEvalFix: fix the bug in {problem['entry_point']}, in Python.",
        {
            "metadata": {
                "category": "python",
                "tags": ["humanevalfix", "bug-fixing"],
                "upstream_task_id": problem["task_id"],
                "bug_type": problem["bug_type"],
                "failure_symptoms": problem["failure_symptoms"],
            },
            "agent": {"timeout_sec": AGENT_TIMEOUT_SECONDS},
            "verifier": {"timeout_sec": VERIFIER_TIMEOUT_SECONDS},
            "environment": {
                "build_timeout_sec": BUILD_TIMEOUT_SECONDS,
                "docker_image": docker_image,
                "cpus": CPUS,
                "memory_mb": MEMORY_MB,
                "storage_mb": STORAGE_MB,
            },
        },
    )


def task_files(name, problem, context):
    reference_solution = with_canary(problem["declaration"] + problem["canonical_solution"], context.canary)
    files = sandbox_checker_files(canary=context.canary, checker_path=CHECKER_PATH, summary_name=SUMMARY_NAME)
    files["tests/problem.json"] = problem_document(problem, context.canary)
    files["tests/reference_solution.py"] = reference_solution
    files["solution/solution.py"] = reference_solution
    files["task.toml"] = task_manifest(name, problem, context.docker_image)
    files["instruction.md"] = instruction(problem, context.canary)
    return files


def generate(upstream_files, out_dir, context):
    problems = load_problems(upstream_files[UPSTREAM_FILE_NAME])
    for name in sorted(problems):
        write_task(pathlib.Path(out_dir) / name, task_files(name, problems[name], context))
    return sorted(problems)


def instruction_code_blocks(instruction_text):
    return [match["code"] for match in INSTRUCTION_CODE_PATTERN.finditer(instruction_text)]


def task_problems(task_directory):
    task_directory = pathlib.Path(task_directory)
    try:
        instruction_text = (task_directory / "instruction.md").read_text(encoding="utf-8")
        reference = (task_directory / "tests" / "reference_solution.py").read_text(encoding="utf-8")
        problem = json.loads((task_directory / "tests" / "problem.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"cannot read the task: {error}"]
    blocks = instruction_code_blocks(instruction_text)
    if len(blocks) != 2:
        return ["the instruction does not show the code and its tests"]
    code, tests = blocks
    reference_code = reference.partition("\n")[2]
    problems = []
    if tests.strip("\n") != problem["test"].strip("\n"):
        problems.append("the instruction's tests are not tests/problem.json's")
    if code.strip("\n") == reference_code.strip("\n"):
        problems.append("the instruction shows the reference solution, not the buggy code")
    if f"Fix bugs in `{problem['entry_point']}`." not in instruction_text:
        problems.append("the instruction does not name tests/problem.json's entry point")
    return problems


def wrong_solutions(task_directory):
    problem = json.loads((task_directory / "tests" / "problem.json").read_text(encoding="utf-8"))
    code = instruction_code_blocks((task_directory / "instruction.md").read_text(encoding="utf-8"))[0]
    return [code, WRONG_SOLUTION_TEMPLATE.format(entry_point=problem["entry_point"])]


CHECKER = Checker(script=pathlib.Path("tests") / CHECKER_PATH.name, wrong_answers=wrong_solutions)


def verify_tasks(tasks_directory, jobs=1, names=()):
    return verify_checker_tasks(tasks_directory, jobs=jobs, names=names, checker=CHECKER)
