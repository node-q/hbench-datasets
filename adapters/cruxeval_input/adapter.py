"""Write CRUXEval input-prediction task directories from CRUXEval's test.jsonl.

Each problem becomes cruxeval-input-<n>, from sample_<n>: CRUXEval-I, whose instruction shows the
problem's code and output and asks for a call of f that returns that output, in /app/answer.txt.
Output prediction is left out: an agent that can run Python computes an output by running f.
tests/ holds check_answer.py, with the code, the output and CRUXEval's 3-second limit; solution/
holds the reference answer, f called on the problem's input. The generic step adds environment/.
"""

import ast
import json
import pathlib
import re

from adapters.common.function_checker import sandbox_checker_files
from adapters.common.function_checker.sandbox_runner import ARGUMENT_BUILTINS
from adapters.common.function_checker.verify import Checker
from adapters.common.function_checker.verify import verify_tasks as verify_checker_tasks
from adapters.common.writing import canonical_json, code_fence, html_canary, task_toml, with_canary, write_task

ADAPTER_DIRECTORY = pathlib.Path(__file__).resolve().parent
CHECKER_PATH = ADAPTER_DIRECTORY / "check_answer.py"
UPSTREAM_FILE_NAME = "test.jsonl"
UPSTREAM_FILES = (UPSTREAM_FILE_NAME,)
TASK_NAME_PREFIX = "cruxeval-input-"
SUMMARY_NAME = "cruxeval-input.json"
ANSWER_PATH = "/app/answer.txt"
ANSWER_NAME = "answer.txt"
ENTRY_POINT = "f"
TASK_ID_PATTERN = re.compile(r"^sample_(?P<number>0|[1-9][0-9]*)$")
PROBLEM_FIELDS = ("id", "code", "input", "output")
CRUXEVAL_TIME_LIMIT_SECONDS = 3
INSTRUCTION_CODE_PATTERN = re.compile(r"^(?P<fence>`{3,})python\n(?P<code>.*?)^(?P=fence)$", re.MULTILINE | re.DOTALL)
AGENT_TIMEOUT_SECONDS = 600.0
VERIFIER_TIMEOUT_SECONDS = 60.0
BUILD_TIMEOUT_SECONDS = 600.0
CPUS = 1
MEMORY_MB = 4096
STORAGE_MB = 10240


class AdapterError(ValueError):
    pass


def task_name(task_id):
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        raise AdapterError(f"id {task_id!r} is not sample_<n>")
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
            try:
                ast.literal_eval(problem["output"])
            except (ValueError, SyntaxError):
                raise AdapterError(f"{problem['id']}: its output is not a Python literal") from None
            name = task_name(problem["id"])
            if name in problems:
                raise AdapterError(f"{problem['id']} appears twice")
            problems[name] = problem
    return problems


def python_block(code):
    code = code.strip("\n") + "\n"
    fence = code_fence(code)
    return f"{fence}python\n{code}{fence}\n"


def reference_answer(problem):
    return f"{ENTRY_POINT}({problem['input']})\n"


def instruction(problem, canary):
    builtins_list = ", ".join(f"`{name}`" for name in ARGUMENT_BUILTINS)
    return (
        html_canary(canary)
        + "\n"
        + f"Find an input for `{ENTRY_POINT}`: a call of `{ENTRY_POINT}` that returns the output below.\n"
        "\n"
        f"{python_block(problem['code'])}"
        "\n"
        "The output:\n"
        "\n"
        f"{python_block(problem['output'])}"
        "\n"
        f"Write `{ANSWER_PATH}`: one call of `{ENTRY_POINT}`, such as `{ENTRY_POINT}(1, 'a')`, whose result "
        "equals this output (`==`).\n"
        "\n"
        "- The call's arguments are Python expressions. They may use the names the code defines, other than "
        f"modules, and these builtins: {builtins_list}. No name or attribute in them may start with `__`, "
        "nor an attribute be one of a frame, generator, coroutine, code object or traceback.\n"
        f"- The call is evaluated, with `{ENTRY_POINT}` from a fresh run of the code, within "
        f"{CRUXEVAL_TIME_LIMIT_SECONDS} seconds.\n"
        f"- Nothing but `{ANSWER_PATH}` is checked. It may span several lines and hold comments.\n"
    )


def problem_document(problem, canary):
    return canonical_json(
        {
            "canary": canary,
            "task_id": problem["id"],
            "entry_point": ENTRY_POINT,
            "code": problem["code"],
            "output": problem["output"],
            "time_limit": CRUXEVAL_TIME_LIMIT_SECONDS,
        }
    )


def task_manifest(name, problem, docker_image):
    return task_toml(
        name,
        f"{problem['id']} from CRUXEval: find an input for which f returns the given output.",
        {
            "metadata": {
                "category": "python",
                "tags": ["cruxeval", "code-reasoning"],
                "upstream_task_id": problem["id"],
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
    files = sandbox_checker_files(
        canary=context.canary, checker_path=CHECKER_PATH, summary_name=SUMMARY_NAME, answer_path=ANSWER_PATH
    )
    files["tests/problem.json"] = problem_document(problem, context.canary)
    files[f"solution/{ANSWER_NAME}"] = with_canary(reference_answer(problem), context.canary)
    files["task.toml"] = task_manifest(name, problem, context.docker_image)
    files["instruction.md"] = instruction(problem, context.canary)
    return files


def generate(upstream_files, out_dir, context):
    problems = load_problems(upstream_files[UPSTREAM_FILE_NAME])
    for name in sorted(problems):
        write_task(pathlib.Path(out_dir) / name, task_files(name, problems[name], context))
    return sorted(problems)


def task_problems(task_directory):
    task_directory = pathlib.Path(task_directory)
    try:
        instruction_text = (task_directory / "instruction.md").read_text(encoding="utf-8")
        problem = json.loads((task_directory / "tests" / "problem.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"cannot read the task: {error}"]
    blocks = [match["code"].strip("\n") for match in INSTRUCTION_CODE_PATTERN.finditer(instruction_text)]
    if blocks != [problem["code"].strip("\n"), problem["output"].strip("\n")]:
        return ["the instruction does not show tests/problem.json's code and output"]
    return []


def wrong_answers(task_directory):
    reference = (task_directory / "solution" / ANSWER_NAME).read_text(encoding="utf-8")
    takes_no_arguments = reference.splitlines()[-1] == f"{ENTRY_POINT}()"
    return ["", f"{ENTRY_POINT}(None)\n" if takes_no_arguments else f"{ENTRY_POINT}()\n"]


CHECKER = Checker(
    script=pathlib.Path("tests") / CHECKER_PATH.name,
    oracle=pathlib.Path("solution") / ANSWER_NAME,
    answer_name=ANSWER_NAME,
    wrong_answers=wrong_answers,
)


def verify_tasks(tasks_directory, jobs=1, names=()):
    return verify_checker_tasks(tasks_directory, jobs=jobs, names=names, checker=CHECKER)
