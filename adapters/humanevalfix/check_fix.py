"""Check a HumanEvalFix solution as HumanEvalFix's harness does: the problem's tests must pass.

Usage: check_fix.py --solution PATH [--summary PATH]

problem.json, next to this file, names the function (entry_point) and holds the imports the harness
puts before the solution (prelude), the tests (test, which defines check and ends by calling it on
the function) and their time limit in seconds. The tests run here, after the prelude and
reference_solution.py, whose other functions, such as poly, they may call. The function they check is
the solution's: sandbox.py runs the solution, after the prelude, in a fresh interpreter, as an
unprivileged user when this runs as root, with this directory closed to it, and passes each call's
arguments to it and its result back as built-in values. The solution passes when loading it and
running the tests raise nothing within the time limit.

Exits 0 when the solution passes and 1 otherwise. --summary writes what was checked, as JSON.
"""

import argparse
import json
import pathlib
import signal
import sys
import traceback

import check_solution as function_checker
from sandbox import CallsSession, encoded_bytes, runner_request

TESTS_DIRECTORY = pathlib.Path(__file__).resolve().parent
PROBLEM_PATH = TESTS_DIRECTORY / "problem.json"
REFERENCE_SOLUTION_PATH = TESTS_DIRECTORY / "reference_solution.py"
TESTS_FILENAME = "tests"


class TimeLimitExceeded(Exception):
    pass


class CandidateFailed(Exception):
    pass


def raise_time_limit_exceeded(signal_number, frame):
    raise TimeLimitExceeded()


def outcome_reason(outcome):
    if "timed_out" in outcome:
        return "timed out"
    if "raised" in outcome:
        return f"raised {outcome['raised']}"
    if "unencodable" in outcome:
        return f"returned a value that cannot be compared ({outcome['unencodable']})"
    return "stopped without a result"


def candidate_function(session, entry_point):
    def candidate(*arguments):
        outcome = session.call(arguments)
        if "returned" not in outcome:
            raise CandidateFailed(f"{entry_point} {outcome_reason(outcome)}")
        try:
            return function_checker.decoded(outcome["returned"])
        except (ValueError, TypeError, IndexError, KeyError, RecursionError):
            raise CandidateFailed(f"{entry_point} returned a value that cannot be compared") from None

    candidate.__name__ = entry_point
    return candidate


def reference_namespace(problem):
    namespace = {"__name__": "__main__"}
    exec(compile(problem["prelude"], "<prelude>", "exec"), namespace)
    exec(compile(REFERENCE_SOLUTION_PATH.read_bytes(), str(REFERENCE_SOLUTION_PATH), "exec"), namespace)
    return namespace


def failing_test_line(error):
    lines = [frame.lineno for frame in traceback.extract_tb(error.__traceback__) if frame.filename == TESTS_FILENAME]
    return f" (line {lines[-1]} of the tests)" if lines else ""


def tests_failure(problem, session, namespace):
    loaded = session.receive()
    if "loaded" not in loaded:
        return f"the solution does not load ({loaded.get('load_error', 'no report')})"
    namespace[problem["entry_point"]] = candidate_function(session, problem["entry_point"])
    try:
        exec(compile(problem["test"], TESTS_FILENAME, "exec"), namespace)
    except CandidateFailed as error:
        return f"{error}{failing_test_line(error)}"
    except AssertionError as error:
        return f"a test failed{failing_test_line(error)}"
    except TimeLimitExceeded:
        raise
    except Exception as error:
        return f"the tests raised {type(error).__name__}{failing_test_line(error)}"
    return None


def timed_tests_failure(problem, session, namespace):
    signal.signal(signal.SIGALRM, raise_time_limit_exceeded)
    signal.setitimer(signal.ITIMER_REAL, problem["time_limit"])
    try:
        return tests_failure(problem, session, namespace)
    except TimeLimitExceeded:
        return f"the solution and its tests ran longer than {problem['time_limit']} seconds"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def check_fix(solution_path):
    problem = json.loads(PROBLEM_PATH.read_text(encoding="utf-8"))
    summary = {"task_id": problem["task_id"], "passed": False}
    if function_checker.running_as_root():
        summary["verifier_directory_closed"] = function_checker.closed_to_others(TESTS_DIRECTORY)
    try:
        source = function_checker.solution_source(solution_path)
    except function_checker.SolutionRejected as error:
        summary["rejected"] = str(error)
        return summary
    namespace = reference_namespace(problem)
    request = runner_request(
        "calls",
        source=encoded_bytes(source),
        filename=str(solution_path),
        prelude=problem["prelude"],
        entry_point=problem["entry_point"],
        time_limit=problem["time_limit"],
    )
    with CallsSession(request) as session:
        failure = timed_tests_failure(problem, session, namespace)
    if failure:
        summary["failure"] = failure
        return summary
    summary["passed"] = True
    return summary


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Check a HumanEvalFix solution.")
    parser.add_argument("--solution", required=True, type=pathlib.Path)
    parser.add_argument("--summary", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    summary = check_fix(options.solution)
    document = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if options.summary:
        options.summary.write_text(document, encoding="utf-8")
    sys.stdout.write(document)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
