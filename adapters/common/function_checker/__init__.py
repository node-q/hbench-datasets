"""Tasks that ask for one Python function, checked as EvalPlus checks HumanEval+ and MBPP+.

An adapter gives each task tests/problem.json (problem_document), the reference solution, and the
checker files here; the checker computes the expected outputs from the reference when it runs.

Checkers that run a candidate's code otherwise, such as with tagged inputs (tagged_problem_document
and check_tagged_solution.py) or an adapter's own checker, take sandbox_checker_files: check_solution.py
and candidate_runner.py, whose sandbox and guard they reuse, sandbox.py and sandbox_runner.py, the
checker itself, and a tests/test.sh and solution/solve.sh written for it.
"""

import pathlib

from adapters.common.writing import canonical_json, with_canary

FUNCTION_CHECKER_DIRECTORY = pathlib.Path(__file__).resolve().parent
SOLUTION_PATH = "/app/solution.py"
ORACLES = ("default", "polynomial-root")
TEMPLATE_FILES = {
    "tests/test.sh": "test.sh",
    "tests/check_solution.py": "check_solution.py",
    "tests/candidate_runner.py": "candidate_runner.py",
    "solution/solve.sh": "solve.sh",
}
TAGGED_INPUT_ENCODING = "tagged"
TAGGED_ORACLES = (*ORACLES, "set-equal", "not-none", "surface-area", "digit-distance")
TAGGED_CHECKER_PATH = FUNCTION_CHECKER_DIRECTORY / "check_tagged_solution.py"
SANDBOX_TEMPLATE_FILES = {
    "tests/check_solution.py": "check_solution.py",
    "tests/candidate_runner.py": "candidate_runner.py",
    "tests/sandbox.py": "sandbox.py",
    "tests/sandbox_runner.py": "sandbox_runner.py",
}


class FunctionCheckerError(ValueError):
    pass


def problem_document(*, canary, task_id, entry_point, atol, phases, oracle="default"):
    if oracle not in ORACLES:
        raise FunctionCheckerError(f"{task_id}: unknown oracle {oracle!r}")
    if not phases or any(not phase_inputs for _, phase_inputs in phases):
        raise FunctionCheckerError(f"{task_id}: every phase needs inputs")
    return canonical_json(
        {
            "canary": canary,
            "task_id": task_id,
            "entry_point": entry_point,
            "atol": atol,
            "oracle": oracle,
            "phases": [{"name": name, "inputs": phase_inputs} for name, phase_inputs in phases],
        }
    )


def function_checker_files(*, canary, problem_json, reference_solution):
    files = {
        "tests/problem.json": problem_json,
        "tests/reference_solution.py": with_canary(reference_solution, canary),
        "solution/solution.py": with_canary(reference_solution, canary),
    }
    for relative_path, template_name in TEMPLATE_FILES.items():
        template = (FUNCTION_CHECKER_DIRECTORY / template_name).read_text(encoding="utf-8")
        files[relative_path] = with_canary(template, canary)
    return files


def tagged_value(value):
    if value is None:
        return ["n"]
    if isinstance(value, bool):
        return ["b", value]
    if isinstance(value, int):
        return ["i", format(value, "x")]
    if isinstance(value, float):
        return ["f", float.hex(value)]
    if isinstance(value, complex):
        return ["c", float.hex(value.real), float.hex(value.imag)]
    if isinstance(value, str):
        return ["s", value]
    if isinstance(value, bytes):
        return ["y", value.hex()]
    if isinstance(value, tuple):
        return ["t", [tagged_value(item) for item in value]]
    if isinstance(value, list):
        return ["l", [tagged_value(item) for item in value]]
    if isinstance(value, frozenset):
        return ["F", sorted((tagged_value(item) for item in value), key=canonical_json)]
    if isinstance(value, set):
        return ["S", sorted((tagged_value(item) for item in value), key=canonical_json)]
    if isinstance(value, dict):
        return ["d", [[tagged_value(key), tagged_value(item)] for key, item in value.items()]]
    raise FunctionCheckerError(f"a {type(value).__name__} has no tagged form")


def tagged_problem_document(*, canary, task_id, entry_point, atol, phases, oracle="default"):
    if oracle not in TAGGED_ORACLES:
        raise FunctionCheckerError(f"{task_id}: unknown oracle {oracle!r}")
    if not phases or any(not phase_inputs for _, phase_inputs in phases):
        raise FunctionCheckerError(f"{task_id}: every phase needs inputs")
    return canonical_json(
        {
            "canary": canary,
            "task_id": task_id,
            "entry_point": entry_point,
            "atol": atol,
            "oracle": oracle,
            "input_encoding": TAGGED_INPUT_ENCODING,
            "phases": [{"name": name, "inputs": phase_inputs} for name, phase_inputs in phases],
        }
    )


def checker_test_script(checker_name, answer_path, summary_name):
    return (
        "#!/bin/bash\n"
        "\n"
        'tests_directory="$(dirname "$0")"\n'
        "mkdir -p /logs/verifier\n"
        f'PYTHONHASHSEED=0 python3 "$tests_directory/{checker_name}" \\\n'
        f"  --solution {answer_path} \\\n"
        f"  --summary /logs/verifier/{summary_name}\n"
        "checker_status=$?\n"
        "rm -f /logs/verifier/reward.json\n"
        'if [ "$checker_status" -eq 0 ]; then\n'
        "  echo 1 > /logs/verifier/reward.txt\n"
        "else\n"
        "  echo 0 > /logs/verifier/reward.txt\n"
        "fi\n"
    )


def solve_script(answer_name, answer_path):
    return (
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "\n"
        f"mkdir -p {pathlib.PurePosixPath(answer_path).parent}\n"
        f'cp "$(dirname "$0")/{answer_name}" {answer_path}\n'
    )


def sandbox_checker_files(*, canary, checker_path, summary_name, answer_path=SOLUTION_PATH):
    checker_path = pathlib.Path(checker_path)
    answer_name = pathlib.PurePosixPath(answer_path).name
    files = {
        relative_path: with_canary((FUNCTION_CHECKER_DIRECTORY / template_name).read_text(encoding="utf-8"), canary)
        for relative_path, template_name in SANDBOX_TEMPLATE_FILES.items()
    }
    files[f"tests/{checker_path.name}"] = with_canary(checker_path.read_text(encoding="utf-8"), canary)
    files["tests/test.sh"] = with_canary(checker_test_script(checker_path.name, answer_path, summary_name), canary)
    files["solution/solve.sh"] = with_canary(solve_script(answer_name, answer_path), canary)
    return files
