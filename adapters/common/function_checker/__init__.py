"""Tasks that ask for one Python function, checked as EvalPlus checks HumanEval+ and MBPP+.

An adapter gives each task tests/problem.json (problem_document), the reference solution, and the
checker files here; the checker computes the expected outputs from the reference when it runs.
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
