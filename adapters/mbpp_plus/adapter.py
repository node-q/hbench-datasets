"""Write MBPP+ task directories from EvalPlus's MbppPlus.jsonl.gz.

Each problem becomes mbpp-plus-<n>: an instruction to write, in /app/solution.py, the function its
prompt asks for, a task.toml, and check_tagged_solution.py's tests/ and solution/ with the problem's
base and plus inputs and its reference solution (the prompt and canonical solution, as EvalPlus runs
it). The inputs are deserialised as EvalPlus's mbpp_deserialize_inputs does, into tuples, sets and
complex numbers where a problem takes them, and written as tagged values. A problem with no plus
inputs (Mbpp/793) is checked on its base inputs. Five plus inputs of Mbpp/255 are left out
(OMITTED_PLUS_INPUTS): their expected outputs hold 6 to 128 million strings, in tuples of 76 or 77,
too many to pass back from the sandbox as built-in values within the 4 GiB memory limit; the largest
of the others holds 111,384. The generic step adds environment/.
"""

import gzip
import json
import pathlib
import re

from adapters.common.function_checker import (
    SOLUTION_PATH,
    TAGGED_CHECKER_PATH,
    sandbox_checker_files,
    tagged_problem_document,
    tagged_value,
)
from adapters.common.function_checker.verify import Checker
from adapters.common.function_checker.verify import verify_tasks as verify_checker_tasks
from adapters.common.writing import code_fence, html_canary, task_toml, with_canary, write_task

UPSTREAM_FILE_NAME = "MbppPlus.jsonl.gz"
UPSTREAM_FILES = (UPSTREAM_FILE_NAME,)
TASK_NAME_PREFIX = "mbpp-plus-"
SUMMARY_NAME = "mbpp-plus.json"
TASK_ID_PATTERN = re.compile(r"^Mbpp/(?P<number>[1-9][0-9]*)$")
ENTRY_POINT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROBLEM_FIELDS = ("task_id", "prompt", "canonical_solution", "entry_point", "base_input", "plus_input", "atol")
SET_EQUAL_ENTRY_POINTS = (
    "similar_elements",
    "find_char_long",
    "common_in_nested_lists",
    "extract_singly",
    "larg_nnum",
    "intersection_array",
    "find_dissimilar",
    "Diff",
)
NOT_NONE_ENTRY_POINTS = ("check_str", "text_match_three", "text_starta_endb")
ORACLES_BY_ENTRY_POINT = {
    **{entry_point: "set-equal" for entry_point in SET_EQUAL_ENTRY_POINTS},
    **{entry_point: "not-none" for entry_point in NOT_NONE_ENTRY_POINTS},
    "surface_Area": "surface-area",
    "digit_distance_nums": "digit-distance",
}
TUPLES_OF_ARGUMENTS = (2, 116, 132, 143, 222, 261, 273, 394, 399, 421, 424, 429, 470, 560, 579, 596, 616, 630, 726, 740, 744, 809)
TUPLES_IN_LIST_ARGUMENTS = (63, 64, 70, 94, 120, 237, 272, 299, 400, 409, 417, 438, 473, 614, 780)
TUPLES_IN_FIRST_ARGUMENT = (75, 413, 444, 753)
TUPLE_SECOND_ARGUMENT = (106, 750)
TUPLE_FIRST_ARGUMENT = (250, 405, 446, 617, 720, 763, 808)
TUPLES_OF_TUPLE_ARGUMENTS = (259, 401, 445)
NESTED_TUPLE_INPUTS = (580, 615, 791)
OMITTED_PLUS_INPUTS = {"Mbpp/255": (85, 86, 90, 96, 100)}
INSTRUCTION_CODE_PATTERN = re.compile(r"^(?P<fence>`{3,})python\n(?P<code>.*?)^(?P=fence)$", re.MULTILINE | re.DOTALL)
AGENT_TIMEOUT_SECONDS = 600.0
VERIFIER_TIMEOUT_SECONDS = 300.0
BUILD_TIMEOUT_SECONDS = 600.0
CPUS = 1
MEMORY_MB = 4096
STORAGE_MB = 10240
CHECKER = Checker(script=pathlib.Path("tests") / TAGGED_CHECKER_PATH.name)


class AdapterError(ValueError):
    pass


def task_number(task_id):
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        raise AdapterError(f"task_id {task_id!r} is not Mbpp/<n>")
    return int(match["number"])


def task_name(task_id):
    return f"{TASK_NAME_PREFIX}{task_number(task_id)}"


def nested_tuples(value):
    if isinstance(value, list):
        return tuple(nested_tuples(item) for item in value)
    return value


def deserialized_inputs(task_id, inputs):
    number = task_number(task_id)
    if number in TUPLES_OF_ARGUMENTS:
        return [[tuple(argument) for argument in arguments] for arguments in inputs]
    if number in TUPLES_IN_LIST_ARGUMENTS:
        return [[[tuple(item) for item in argument] for argument in arguments] for arguments in inputs]
    if number in TUPLES_IN_FIRST_ARGUMENT:
        return [[[tuple(item) for item in arguments[0]]] + [arguments[1]] for arguments in inputs]
    if number in TUPLE_SECOND_ARGUMENT:
        return [[arguments[0]] + [tuple(arguments[1])] for arguments in inputs]
    if number == 115:
        return [
            [[set(item) if isinstance(item, list) and len(item) else {} for item in arguments[0]]]
            for arguments in inputs
        ]
    if number == 124:
        return [(float(arguments[0]), complex(arguments[1])) for arguments in inputs]
    if number in TUPLE_FIRST_ARGUMENT:
        return [[tuple(arguments[0])] + [arguments[1]] for arguments in inputs]
    if number in TUPLES_OF_TUPLE_ARGUMENTS:
        tupled = [[[tuple(item) for item in argument] for argument in arguments] for arguments in inputs]
        return [[tuple(argument) for argument in arguments] for arguments in tupled]
    if number == 278:
        tupled = [
            [[tuple(item) if isinstance(item, list) else item for item in arguments[0]]] for arguments in inputs
        ]
        return [[tuple(argument) for argument in arguments] for arguments in tupled]
    if number == 307:
        return [[tuple(arguments[0])] + [arguments[1], arguments[2]] for arguments in inputs]
    if number == 722:
        return [
            [{key: tuple(value) for key, value in arguments[0].items()}] + arguments[1:] for arguments in inputs
        ]
    if number == 252:
        return [[complex(arguments[0])] for arguments in inputs]
    if number in NESTED_TUPLE_INPUTS:
        return [nested_tuples(arguments) for arguments in inputs]
    return inputs


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


def kept_plus_inputs(problem):
    omitted = OMITTED_PLUS_INPUTS.get(problem["task_id"], ())
    if any(index >= len(problem["plus_input"]) for index in omitted):
        raise AdapterError(f"{problem['task_id']} has no plus input {max(omitted)} to leave out")
    return [arguments for index, arguments in enumerate(problem["plus_input"]) if index not in omitted]


def phases(problem):
    phase_inputs = [("base", problem["base_input"]), ("plus", kept_plus_inputs(problem))]
    tagged_phases = []
    for phase_name, inputs in phase_inputs:
        if not inputs:
            continue
        deserialized = deserialized_inputs(problem["task_id"], inputs)
        tagged_phases.append((phase_name, [tagged_value(arguments) for arguments in deserialized]))
    if not tagged_phases or tagged_phases[0][0] != "base":
        raise AdapterError(f"{problem['task_id']} has no base inputs")
    return tagged_phases


def instruction(problem, canary):
    entry_point = problem["entry_point"]
    prompt = problem["prompt"].strip("\n") + "\n"
    fence = code_fence(prompt)
    return (
        html_canary(canary)
        + "\n"
        + f"Write `{SOLUTION_PATH}`: Python code that defines `{entry_point}`, a function that does what "
        "this problem asks.\n"
        "\n"
        f"{fence}python\n"
        f"{prompt}"
        f"{fence}\n"
        "\n"
        f"- The assert shows how `{entry_point}` is called. It is imported from `{SOLUTION_PATH}` and "
        "called on many inputs, including inputs the problem does not show, and each result must be what "
        "the problem asks for. Each call has a time limit.\n"
        "- Use Python 3.12 and its standard library only. Nothing is read from standard input, and nothing "
        "printed is checked.\n"
    )


def task_manifest(name, problem, docker_image):
    return task_toml(
        name,
        f"{problem['task_id']} from MBPP+: write {problem['entry_point']} in Python.",
        {
            "metadata": {
                "category": "python",
                "tags": ["mbpp-plus", "code-generation"],
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


def task_files(name, problem, context):
    reference_solution = with_canary(problem["prompt"] + problem["canonical_solution"], context.canary)
    files = sandbox_checker_files(canary=context.canary, checker_path=TAGGED_CHECKER_PATH, summary_name=SUMMARY_NAME)
    files["tests/problem.json"] = tagged_problem_document(
        canary=context.canary,
        task_id=problem["task_id"],
        entry_point=problem["entry_point"],
        atol=problem["atol"],
        phases=phases(problem),
        oracle=ORACLES_BY_ENTRY_POINT.get(problem["entry_point"], "default"),
    )
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


def task_problems(task_directory):
    task_directory = pathlib.Path(task_directory)
    try:
        instruction_text = (task_directory / "instruction.md").read_text(encoding="utf-8")
        reference = (task_directory / "tests" / "reference_solution.py").read_text(encoding="utf-8")
        problem = json.loads((task_directory / "tests" / "problem.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"cannot read the task: {error}"]
    match = INSTRUCTION_CODE_PATTERN.search(instruction_text)
    prompt = match["code"].strip("\n") if match else None
    reference_code = reference.partition("\n")[2]
    if not prompt or not reference_code.startswith(prompt):
        return ["the instruction's code is not the reference solution's prompt"]
    problems = []
    body = reference_code[len(prompt) :].strip()
    if body and body in instruction_text:
        problems.append("the instruction contains the reference solution")
    entry_point = problem.get("entry_point") if isinstance(problem, dict) else None
    if not isinstance(entry_point, str) or f"`{entry_point}`" not in instruction_text:
        problems.append("tests/problem.json does not name the instruction's entry point")
    return problems


def verify_tasks(tasks_directory, jobs=1, names=()):
    return verify_checker_tasks(tasks_directory, jobs=jobs, names=names, checker=CHECKER)
