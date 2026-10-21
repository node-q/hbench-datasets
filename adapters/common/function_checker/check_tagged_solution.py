"""Check a solution to a function-completion problem whose inputs are tagged values, as EvalPlus checks MBPP+.

Usage: check_tagged_solution.py --solution PATH [--summary PATH] [--min-time-limit SECONDS]
                                [--time-limit-factor N] [--unprivileged-id ID]

This is check_solution.py, next to this file, for problems whose inputs JSON cannot hold, such as
tuples, sets and complex numbers. problem.json's input_encoding is "tagged": each input is written as
candidate_runner.py encodes a value, and is decoded here. sandbox_runner.py runs the solution on them.
Expected outputs, time limits and the unprivileged user are check_solution.py's. Besides its oracles,
it knows EvalPlus's special oracles for MBPP+, each of which then compares as the default oracle does:

  set-equal       the output equals the expected one as a set (Mbpp/2, 7, 111, 140, 232, 579, 769)
  not-none        the output, or whether it is not None unless it is a bool, equals whether the
                  expected one is not None (Mbpp/737, 787, 794)
  surface-area    or the output is within atol of EvalPlus's own surface_Area (Mbpp/581)
  digit-distance  or the output equals EvalPlus's own digit_distance_nums (Mbpp/558)

Exits 0 when every input passes and 1 otherwise. --summary writes what was checked, as JSON.
"""

import argparse
import json
import math
import pathlib
import pickle
import sys

import check_solution as function_checker
from sandbox import encoded_bytes, run_once, runner_request

TAGGED_INPUT_ENCODING = "tagged"
NOT_NONE_ORACLE = "not-none"
NOT_NONE_OUTPUT = "not-none"


def surface_area(base_edge, height):
    slant_height = math.sqrt((base_edge / 2) ** 2 + height**2)
    base_area = base_edge**2
    lateral_area = 4 * (base_edge * slant_height) / 2
    return round(base_area + lateral_area)


def digit_distance(first, second):
    first_digits, second_digits = str(first), str(second)
    length = max(len(first_digits), len(second_digits))
    first_digits, second_digits = first_digits.zfill(length), second_digits.zfill(length)
    return sum(abs(int(a) - int(b)) for a, b in zip(first_digits, second_digits))


def compared_as_default(actual, expected, atol, exact):
    if atol == 0 and function_checker.is_floats(expected):
        atol = function_checker.EVALPLUS_FLOAT_ATOL
    if not exact and atol != 0:
        return function_checker.close_enough(actual, expected, atol), atol
    return exact, atol


def set_equal_oracle(arguments, actual, expected, atol):
    try:
        exact = set(actual) == set(expected)
    except Exception:
        return False, atol
    return compared_as_default(actual, expected, atol, exact)


def not_none_oracle(arguments, actual, expected, atol):
    expected_not_none = expected is not None
    return compared_as_default(actual, expected_not_none, atol, function_checker.exactly_equal(actual, expected_not_none))


def surface_area_oracle(arguments, actual, expected, atol):
    exact = function_checker.exactly_equal(actual, expected)
    if not exact:
        try:
            exact = bool(abs(actual - surface_area(*arguments)) <= atol)
        except Exception:
            return False, atol
    return compared_as_default(actual, expected, atol, exact)


def digit_distance_oracle(arguments, actual, expected, atol):
    exact = function_checker.exactly_equal(actual, expected)
    if not exact:
        try:
            exact = function_checker.exactly_equal(actual, digit_distance(*arguments))
        except Exception:
            return False, atol
    return compared_as_default(actual, expected, atol, exact)


ORACLES = {
    **function_checker.ORACLES,
    "set-equal": set_equal_oracle,
    NOT_NONE_ORACLE: not_none_oracle,
    "surface-area": surface_area_oracle,
    "digit-distance": digit_distance_oracle,
}


def judged_inputs(oracle, inputs, expected_outputs, outcomes, atol):
    passes = ORACLES[oracle]
    verdicts = []
    for arguments, expected, outcome in zip(inputs, expected_outputs, outcomes):
        if "returned" not in outcome:
            verdicts.append(function_checker.failure_reason(outcome))
            continue
        try:
            actual = function_checker.decoded(outcome["returned"])
        except (ValueError, TypeError, IndexError, KeyError, RecursionError):
            verdicts.append("returned a value that cannot be compared")
            continue
        passed, atol = passes(arguments, actual, expected, atol)
        verdicts.append(None if passed else function_checker.failure_reason(outcome))
    return verdicts


def run_candidate(source, solution_path, problem, inputs, time_limits, unprivileged_id):
    request = runner_request(
        "function",
        source=encoded_bytes(source),
        filename=str(solution_path),
        prelude="",
        entry_point=problem["entry_point"],
        inputs=encoded_bytes(pickle.dumps(inputs)),
        time_limits=time_limits,
        output=NOT_NONE_OUTPUT if problem["oracle"] == NOT_NONE_ORACLE else None,
    )
    run_time_limit = (
        min(function_checker.EVALPLUS_RUN_TIME_CAP_SECONDS, sum(time_limits))
        + function_checker.EVALPLUS_RUN_GRACE_SECONDS
    )
    report = run_once(request, run_time_limit, unprivileged_id)
    if "timed_out" in report or "load_error" in report:
        return report
    outcomes = report.get("outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != len(inputs):
        return {"load_error": "no report"}
    if not all(isinstance(outcome, dict) for outcome in outcomes):
        return {"load_error": "no report"}
    return report


def check_phase(problem, function, source, solution_path, inputs, settings):
    expected_outputs, durations = function_checker.reference_outputs(function, inputs)
    time_limits = [max(settings.min_time_limit, settings.time_limit_factor * duration) for duration in durations]
    report = run_candidate(source, solution_path, problem, inputs, time_limits, settings.unprivileged_id)
    if "timed_out" in report:
        return {"status": "timeout", "inputs": len(inputs), "passed": 0}
    if "load_error" in report:
        return {"status": "fail", "inputs": len(inputs), "passed": 0, "load_error": str(report["load_error"])}
    verdicts = judged_inputs(problem["oracle"], inputs, expected_outputs, report["outcomes"], problem["atol"])
    return function_checker.phase_summary(inputs, verdicts)


def check_tagged_solution(solution_path, settings):
    problem = json.loads(function_checker.PROBLEM_PATH.read_text(encoding="utf-8"))
    summary = {"task_id": problem["task_id"], "passed": False}
    if function_checker.running_as_root():
        summary["verifier_directory_closed"] = function_checker.closed_to_others(function_checker.TESTS_DIRECTORY)
    try:
        source = function_checker.solution_source(solution_path)
    except function_checker.SolutionRejected as error:
        summary["rejected"] = str(error)
        return summary
    if problem["oracle"] not in ORACLES:
        raise ValueError(f"problem.json names an unknown oracle, {problem['oracle']!r}")
    if problem["input_encoding"] != TAGGED_INPUT_ENCODING:
        raise ValueError(f"problem.json's inputs are not tagged, but {problem['input_encoding']!r}")
    function = function_checker.reference_function(problem["entry_point"])
    summary["phases"] = []
    for phase in problem["phases"]:
        inputs = [function_checker.decoded(tagged) for tagged in phase["inputs"]]
        phase_result = check_phase(problem, function, source, solution_path, inputs, settings)
        summary["phases"].append({"name": phase["name"], **phase_result})
        if phase_result["status"] != "pass":
            return summary
    summary["passed"] = True
    return summary


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Check a solution to a function-completion problem with tagged inputs.")
    parser.add_argument("--solution", required=True, type=pathlib.Path)
    parser.add_argument("--summary", type=pathlib.Path)
    parser.add_argument("--min-time-limit", type=float, default=function_checker.EVALPLUS_MIN_TIME_LIMIT_SECONDS)
    parser.add_argument("--time-limit-factor", type=float, default=function_checker.EVALPLUS_TIME_LIMIT_FACTOR)
    parser.add_argument("--unprivileged-id", type=function_checker.unprivileged_id, default=function_checker.NOBODY_ID)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    settings = function_checker.CheckSettings(options.min_time_limit, options.time_limit_factor, options.unprivileged_id)
    summary = check_tagged_solution(options.solution, settings)
    document = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if options.summary:
        options.summary.write_text(document, encoding="utf-8")
    sys.stdout.write(document)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
