"""Write HumanEval+ task directories from EvalPlus's HumanEvalPlus.jsonl.gz.

Each problem becomes humaneval-plus-<n>: an instruction to implement its prompt in /app/solution.py, a
task.toml, and the function checker's tests/ and solution/ with the problem's base and plus inputs and
its reference solution (the prompt and canonical solution, as EvalPlus runs it). The generic step adds
environment/, the image's build context.
"""

import gzip
import json
import pathlib
import re

from adapters.common.function_checker import (
    SOLUTION_PATH,
    function_checker_files,
    problem_document,
)
from adapters.common.function_checker.verify import verify_tasks as verify_function_checker_tasks
from adapters.common.writing import code_fence, html_canary, task_toml, write_task

UPSTREAM_FILE_NAME = "HumanEvalPlus.jsonl.gz"
UPSTREAM_FILES = (UPSTREAM_FILE_NAME,)
TASK_NAME_PREFIX = "humaneval-plus-"
TASK_ID_PATTERN = re.compile(r"^HumanEval/(?P<number>0|[1-9][0-9]*)$")
ENTRY_POINT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROBLEM_FIELDS = ("task_id", "prompt", "canonical_solution", "entry_point", "base_input", "plus_input", "atol")
POLYNOMIAL_ROOT_ENTRY_POINTS = ("find_zero",)
INSTRUCTION_CODE_PATTERN = re.compile(r"^(?P<fence>`{3,})python\n(?P<code>.*?)^(?P=fence)$", re.MULTILINE | re.DOTALL)
AGENT_TIMEOUT_SECONDS = 600.0
VERIFIER_TIMEOUT_SECONDS = 300.0
BUILD_TIMEOUT_SECONDS = 600.0
CPUS = 1
MEMORY_MB = 4096
STORAGE_MB = 10240


class AdapterError(ValueError):
    pass


def task_name(task_id):
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        raise AdapterError(f"task_id {task_id!r} is not HumanEval/<n>")
    return f"{TASK_NAME_PREFIX}{match['number']}"


def load_problems(upstream_path):
    problems = {}
    with gzip.open(upstream_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            problem = json.loads(line)
            missing = [field for field in PROBLEM_FIELDS if field not in problem]
            if missing:
                raise AdapterError(f"line {line_number} has no {', '.join(missing)}")
            if not ENTRY_POINT_PATTERN.match(problem["entry_point"]):
                raise AdapterError(f"{problem['task_id']}: entry_point {problem['entry_point']!r} is not a name")
            name = task_name(problem["task_id"])
            if name in problems:
                raise AdapterError(f"{problem['task_id']} appears twice")
            problems[name] = problem
    return problems


def instruction(problem, canary):
    entry_point = problem["entry_point"]
    prompt = problem["prompt"].strip("\n") + "\n"
    fence = code_fence(prompt)
    return (
        html_canary(canary)
        + "\n"
        + f"Write `{SOLUTION_PATH}`: the Python code below, with the body of `{entry_point}` implemented to do "
        "what its docstring describes.\n"
        "\n"
        f"{fence}python\n"
        f"{prompt}"
        f"{fence}\n"
        "\n"
        "- Keep the code's imports and any other functions it defines: your implementation may use them.\n"
        f"- `{entry_point}` is imported from `{SOLUTION_PATH}` and called on many inputs, including inputs the "
        "docstring does not show, and each result must be what the docstring specifies. Each call has a time "
        "limit.\n"
        "- Use Python 3.12 and its standard library only. Nothing is read from standard input, and nothing "
        "printed is checked.\n"
    )


def task_manifest(name, problem, docker_image):
    return task_toml(
        name,
        f"{problem['task_id']} from HumanEval+: implement {problem['entry_point']} in Python.",
        {
            "metadata": {
                "category": "python",
                "tags": ["humaneval-plus", "code-generation"],
                "upstream_task_id": problem["task_id"],
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


def oracle(problem):
    return "polynomial-root" if problem["entry_point"] in POLYNOMIAL_ROOT_ENTRY_POINTS else "default"


def task_files(name, problem, context):
    problem_json = problem_document(
        canary=context.canary,
        task_id=problem["task_id"],
        entry_point=problem["entry_point"],
        atol=problem["atol"],
        phases=[("base", problem["base_input"]), ("plus", problem["plus_input"])],
        oracle=oracle(problem),
    )
    files = function_checker_files(
        canary=context.canary,
        problem_json=problem_json,
        reference_solution=problem["prompt"] + problem["canonical_solution"],
    )
    files["task.toml"] = task_manifest(name, problem, context.docker_image)
    files["instruction.md"] = instruction(problem, context.canary)
    return files


def generate(upstream_files, out_dir, context):
    problems = load_problems(upstream_files[UPSTREAM_FILE_NAME])
    for name in sorted(problems):
        write_task(pathlib.Path(out_dir) / name, task_files(name, problems[name], context))
    return sorted(problems)


def instruction_code(instruction_text):
    match = INSTRUCTION_CODE_PATTERN.search(instruction_text)
    return match["code"].strip("\n") if match else None


def task_problems(task_directory):
    task_directory = pathlib.Path(task_directory)
    try:
        instruction_text = (task_directory / "instruction.md").read_text(encoding="utf-8")
        reference = (task_directory / "tests" / "reference_solution.py").read_text(encoding="utf-8")
        problem = json.loads((task_directory / "tests" / "problem.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"cannot read the task: {error}"]
    prompt = instruction_code(instruction_text)
    reference_code = reference.partition("\n")[2]
    if not prompt or prompt not in reference_code:
        return ["the instruction's code is not the reference solution's prompt"]
    problems = []
    body = reference_code[reference_code.index(prompt) + len(prompt) :].strip()
    if body and body in instruction_text:
        problems.append("the instruction contains the reference solution")
    entry_point = problem.get("entry_point") if isinstance(problem, dict) else None
    if not isinstance(entry_point, str) or f"`{entry_point}`" not in instruction_text:
        problems.append("tests/problem.json does not name the instruction's entry point")
    return problems


def verify_tasks(tasks_directory, jobs=1, names=()):
    return verify_function_checker_tasks(tasks_directory, jobs=jobs, names=names)
