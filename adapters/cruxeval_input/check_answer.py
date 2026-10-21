"""Check an answer to a CRUXEval input-prediction problem: a call of f that returns the expected output.

Usage: check_answer.py --solution PATH [--summary PATH]

problem.json, next to this file, holds the problem's code, which defines the function (entry_point,
f), the expected output, a Python literal, and the time limit in seconds. The answer, the file at
PATH, must be one Python expression, a call of f. Its arguments may use the names the code defines,
other than modules, and the builtins sandbox_runner.py lists in ARGUMENT_BUILTINS; no name or
attribute in it may start with "__", nor an attribute be one of a frame, generator, coroutine, code
object or traceback. sandbox.py evaluates it in a fresh interpreter, as an unprivileged user when this
runs as root, with this directory closed to it: the arguments among the code's names, then f, from a
fresh run of the code, on them. The answer passes when f's result, passed back as built-in values,
equals the expected output within the time limit, as CRUXEval checks `assert output == answer`.

Exits 0 when the answer passes and 1 otherwise. --summary writes what was checked, as JSON.
"""

import argparse
import ast
import json
import pathlib
import sys

import check_solution as function_checker
from sandbox import run_once, runner_request

TESTS_DIRECTORY = pathlib.Path(__file__).resolve().parent
PROBLEM_PATH = TESTS_DIRECTORY / "problem.json"
FORBIDDEN_NAME_PREFIX = "__"
FORBIDDEN_ATTRIBUTE_PREFIXES = ("__", "f_", "gi_", "cr_", "ag_", "co_", "tb_")
RUN_GRACE_SECONDS = 3.0


class AnswerRefused(Exception):
    pass


def identifiers(node):
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.arg):
        return [node.arg]
    if isinstance(node, ast.keyword) and node.arg is not None:
        return [node.arg]
    return []


def checked_answer(text, entry_point):
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        raise AnswerRefused("is not one Python expression") from None
    call = tree.body
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == entry_point):
        raise AnswerRefused(f"is not a call of {entry_point}")
    for node in ast.walk(tree):
        if any(name.startswith(FORBIDDEN_NAME_PREFIX) for name in identifiers(node)):
            raise AnswerRefused(f"uses a name that starts with {FORBIDDEN_NAME_PREFIX!r}")
        if isinstance(node, ast.Attribute) and node.attr.startswith(FORBIDDEN_ATTRIBUTE_PREFIXES):
            raise AnswerRefused(f"uses the attribute {node.attr!r}")
    return text


def answer_text(solution_path):
    source = function_checker.solution_source(solution_path)
    try:
        return source.decode("utf-8")
    except UnicodeDecodeError:
        raise AnswerRefused("is not UTF-8 text") from None


def result_failure(outcome, expected):
    if "timed_out" in outcome:
        return "timed out"
    if "raised" in outcome:
        return f"raised {outcome['raised']}"
    if "unencodable" in outcome:
        return f"returned a value that cannot be compared ({outcome['unencodable']})"
    if "returned" not in outcome:
        return f"stopped without a result ({outcome.get('load_error', 'no report')})"
    try:
        equal = function_checker.decoded(outcome["returned"]) == expected
    except (ValueError, TypeError, IndexError, KeyError, RecursionError):
        return "returned a value that cannot be compared"
    return None if equal else "returned another value than the expected output"


def check_answer(solution_path):
    problem = json.loads(PROBLEM_PATH.read_text(encoding="utf-8"))
    summary = {"task_id": problem["task_id"], "passed": False}
    if function_checker.running_as_root():
        summary["verifier_directory_closed"] = function_checker.closed_to_others(TESTS_DIRECTORY)
    try:
        answer = checked_answer(answer_text(solution_path), problem["entry_point"])
    except function_checker.SolutionRejected as error:
        summary["rejected"] = str(error)
        return summary
    except AnswerRefused as error:
        summary["failure"] = f"the answer {error}"
        return summary
    request = runner_request(
        "expression",
        code=problem["code"],
        answer=answer,
        filename=str(solution_path),
        entry_point=problem["entry_point"],
        time_limit=problem["time_limit"],
    )
    outcome = run_once(request, problem["time_limit"] + RUN_GRACE_SECONDS)
    failure = result_failure(outcome, ast.literal_eval(problem["output"]))
    if failure:
        summary["failure"] = f"the call {failure}"
        return summary
    summary["passed"] = True
    return summary


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Check an answer to a CRUXEval input-prediction problem.")
    parser.add_argument("--solution", required=True, type=pathlib.Path)
    parser.add_argument("--summary", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    summary = check_answer(options.solution)
    document = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if options.summary:
        options.summary.write_text(document, encoding="utf-8")
    sys.stdout.write(document)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
