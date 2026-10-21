"""Check a solution to a function-completion problem as EvalPlus's evaluator does, phase by phase.

Usage: check_solution.py --solution PATH [--summary PATH] [--min-time-limit SECONDS] [--time-limit-factor N]

problem.json, next to this file, names the function (entry_point), the phases of inputs (for
EvalPlus's datasets, base and then plus), the absolute tolerance (atol) and the oracle. The expected
outputs come from running reference_solution.py on each input here, and each input's time limit is the
larger of --min-time-limit and --time-limit-factor times the reference's time on it. The solution runs
in a fresh interpreter, as an unprivileged user when this runs as root, with this directory closed to
it. A later phase runs only when the earlier ones passed.

The oracles:
  default          the output equals the expected one, or is close to it within atol (1e-6 for float
                   outputs when atol is 0) and rtol 1e-7, as numpy.allclose compares
  polynomial-root  the polynomial with coefficients the first argument is within atol of zero at the
                   output, as EvalPlus checks HumanEval/32 (find_zero), or the default oracle passes

Exits 0 when every input passes and 1 otherwise. --summary writes what was checked, as JSON.
"""

import argparse
import base64
import copy
import json
import math
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from fractions import Fraction

TESTS_DIRECTORY = pathlib.Path(__file__).resolve().parent
PROBLEM_PATH = TESTS_DIRECTORY / "problem.json"
REFERENCE_SOLUTION_PATH = TESTS_DIRECTORY / "reference_solution.py"
CANDIDATE_RUNNER_PATH = TESTS_DIRECTORY / "candidate_runner.py"

EVALPLUS_MIN_TIME_LIMIT_SECONDS = 4.0
EVALPLUS_TIME_LIMIT_FACTOR = 4.0
EVALPLUS_RUN_TIME_CAP_SECONDS = 60.0
EVALPLUS_RUN_GRACE_SECONDS = 3.0
EVALPLUS_MEMORY_LIMIT_BYTES = 4 * 1024**3
EVALPLUS_FLOAT_ATOL = 1e-6
EVALPLUS_RTOL = 1e-7
MAXIMUM_SOLUTION_BYTES = 10 * 1024 * 1024
UNPRIVILEGED_USER_ID = 65534
UNPRIVILEGED_GROUP_ID = 65534
KILL_EVERY_PROCESS_OF_THIS_USER = "import os, signal\nos.kill(-1, signal.SIGKILL)\n"


class SolutionRejected(Exception):
    pass


def running_as_root():
    return os.geteuid() == 0


def physical_memory_bytes():
    try:
        return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError):
        return EVALPLUS_MEMORY_LIMIT_BYTES


def solution_source(solution_path):
    resolved = pathlib.Path(solution_path).resolve()
    if resolved == TESTS_DIRECTORY or TESTS_DIRECTORY in resolved.parents:
        raise SolutionRejected(f"{solution_path} resolves into the verifier's directory")
    if not resolved.is_file():
        raise SolutionRejected(f"{solution_path} is not a file")
    if resolved.stat().st_size > MAXIMUM_SOLUTION_BYTES:
        raise SolutionRejected(f"{solution_path} is larger than {MAXIMUM_SOLUTION_BYTES} bytes")
    return resolved.read_bytes()


def reference_function(entry_point):
    namespace = {}
    exec(compile(REFERENCE_SOLUTION_PATH.read_bytes(), str(REFERENCE_SOLUTION_PATH), "exec"), namespace)
    return namespace[entry_point]


def reference_outputs(function, inputs):
    outputs = []
    durations = []
    for arguments in inputs:
        arguments = copy.deepcopy(arguments)
        started = time.perf_counter()
        outputs.append(function(*arguments))
        durations.append(time.perf_counter() - started)
    return outputs, durations


def decoded(tagged):
    tag = tagged[0]
    if tag == "n":
        return None
    if tag == "b":
        return bool(tagged[1])
    if tag == "i":
        return int(tagged[1], 16)
    if tag == "f":
        return float.fromhex(tagged[1])
    if tag == "c":
        return complex(float.fromhex(tagged[1]), float.fromhex(tagged[2]))
    if tag == "s":
        return str(tagged[1])
    if tag == "y":
        return bytes.fromhex(tagged[1])
    if tag == "q":
        return Fraction(int(tagged[1], 16), int(tagged[2], 16))
    if tag == "D":
        return Decimal(tagged[1])
    if tag == "t":
        return tuple(decoded(item) for item in tagged[1])
    if tag == "l":
        return [decoded(item) for item in tagged[1]]
    if tag == "F":
        return frozenset(decoded(item) for item in tagged[1])
    if tag == "S":
        return {decoded(item) for item in tagged[1]}
    if tag == "d":
        return {decoded(key): decoded(item) for key, item in tagged[1]}
    raise ValueError(f"unknown tag {tag!r}")


def is_floats(value):
    if isinstance(value, float):
        return True
    if isinstance(value, (list, tuple)) and value:
        return all(isinstance(item, float) for item in value)
    return False


def as_float64(value):
    if isinstance(value, complex):
        return value
    if isinstance(value, (bool, int, float, Fraction, Decimal)):
        return float(value)
    raise TypeError(f"{type(value).__name__} is not a number")


def numbers_close(actual, expected, rtol, atol):
    actual, expected = as_float64(actual), as_float64(expected)
    if any(math.isinf(abs(number)) for number in (actual, expected)):
        return actual == expected
    if any(number != number for number in (actual, expected)):
        return False
    return abs(actual - expected) <= atol + rtol * abs(expected)


def broadcast_pairs(actual, expected):
    actual_items = list(actual) if isinstance(actual, (list, tuple)) else [actual]
    expected_items = list(expected) if isinstance(expected, (list, tuple)) else [expected]
    if len(actual_items) == len(expected_items):
        return list(zip(actual_items, expected_items))
    if len(actual_items) == 1:
        return [(actual_items[0], item) for item in expected_items]
    if len(expected_items) == 1:
        return [(item, expected_items[0]) for item in actual_items]
    raise ValueError("shapes do not broadcast")


def all_close(actual, expected, rtol, atol):
    if isinstance(actual, (list, tuple)) or isinstance(expected, (list, tuple)):
        return all(all_close(a, e, rtol, atol) for a, e in broadcast_pairs(actual, expected))
    return numbers_close(actual, expected, rtol, atol)


def close_enough(actual, expected, atol):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, (list, tuple)) and len(actual) != len(expected):
        return False
    try:
        return all_close(actual, expected, EVALPLUS_RTOL, atol)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False


def polynomial_value(coefficients, x):
    return sum(coefficient * math.pow(x, power) for power, coefficient in enumerate(coefficients))


def polynomial_root_passes(arguments, actual, atol):
    try:
        return abs(polynomial_value(*arguments, actual)) <= atol
    except Exception:
        return False


def exactly_equal(actual, expected):
    try:
        return bool(actual == expected)
    except Exception:
        return False


def failure_reason(outcome):
    if "timed_out" in outcome:
        return "timed out"
    if "raised" in outcome:
        return f"raised {outcome['raised']}"
    if "unencodable" in outcome:
        return f"returned a value that cannot be compared ({outcome['unencodable']})"
    return "returned a wrong value"


def default_oracle(arguments, actual, expected, atol):
    exact = exactly_equal(actual, expected)
    if atol == 0 and is_floats(expected):
        atol = EVALPLUS_FLOAT_ATOL
    if not exact and atol != 0:
        return close_enough(actual, expected, atol), atol
    return exact, atol


def polynomial_root_oracle(arguments, actual, expected, atol):
    if polynomial_root_passes(arguments, actual, atol):
        return True, atol
    return default_oracle(arguments, actual, expected, atol)


ORACLES = {"default": default_oracle, "polynomial-root": polynomial_root_oracle}


def judged_inputs(oracle, inputs, expected_outputs, outcomes, atol):
    passes = ORACLES[oracle]
    verdicts = []
    for arguments, expected, outcome in zip(inputs, expected_outputs, outcomes):
        if "returned" not in outcome:
            verdicts.append(failure_reason(outcome))
            continue
        try:
            actual = decoded(outcome["returned"])
        except (ValueError, TypeError, IndexError, KeyError, RecursionError):
            verdicts.append("returned a value that cannot be compared")
            continue
        passed, atol = passes(arguments, actual, expected, atol)
        verdicts.append(None if passed else failure_reason(outcome))
    return verdicts


class CandidateSandbox:
    def __init__(self):
        self.unprivileged = running_as_root()

    def __enter__(self):
        self.working_directory = tempfile.mkdtemp(prefix="humaneval-plus-")
        if self.unprivileged:
            os.chown(self.working_directory, UNPRIVILEGED_USER_ID, UNPRIVILEGED_GROUP_ID)
        return self

    def __exit__(self, *exception):
        shutil.rmtree(self.working_directory, ignore_errors=True)

    def user_arguments(self):
        if not self.unprivileged:
            return {}
        return {"user": UNPRIVILEGED_USER_ID, "group": UNPRIVILEGED_GROUP_ID, "extra_groups": []}

    def environment(self):
        return {
            "PATH": os.environ.get("PATH", os.defpath),
            "PYTHONHASHSEED": "0",
            "LANG": "C.UTF-8",
            "HOME": self.working_directory,
            "TMPDIR": self.working_directory,
        }

    def start(self, arguments):
        return subprocess.Popen(
            arguments,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=self.working_directory,
            env=self.environment(),
            start_new_session=True,
            **self.user_arguments(),
        )

    def stop_every_process(self, process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        if self.unprivileged:
            subprocess.run(
                [sys.executable, "-s", "-P", "-c", KILL_EVERY_PROCESS_OF_THIS_USER],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={},
                timeout=30,
                check=False,
                **self.user_arguments(),
            )


def run_candidate(source, solution_path, entry_point, inputs, time_limits):
    request = json.dumps(
        {
            "source": base64.b64encode(source).decode("ascii"),
            "filename": str(solution_path),
            "entry_point": entry_point,
            "inputs": inputs,
            "time_limits": time_limits,
            "memory_limit_bytes": min(EVALPLUS_MEMORY_LIMIT_BYTES, physical_memory_bytes()),
        }
    ).encode("utf-8")
    run_time_limit = min(EVALPLUS_RUN_TIME_CAP_SECONDS, sum(time_limits)) + EVALPLUS_RUN_GRACE_SECONDS
    runner_arguments = [sys.executable, "-s", "-P", "-c", CANDIDATE_RUNNER_PATH.read_text(encoding="utf-8")]
    with CandidateSandbox() as sandbox:
        process = sandbox.start(runner_arguments)
        try:
            output, _ = process.communicate(request, timeout=run_time_limit)
        except subprocess.TimeoutExpired:
            output = None
        finally:
            sandbox.stop_every_process(process)
            process.kill()
            process.wait()
            for stream in (process.stdin, process.stdout):
                stream.close()
    if output is None:
        return {"timed_out": True}
    try:
        report = json.loads(output)
    except ValueError:
        return {"load_error": "no report"}
    if not isinstance(report, dict):
        return {"load_error": "no report"}
    if not isinstance(report.get("outcomes"), list) or len(report["outcomes"]) != len(inputs):
        return {"load_error": str(report.get("load_error", "no report"))}
    if not all(isinstance(outcome, dict) for outcome in report["outcomes"]):
        return {"load_error": "no report"}
    return report


def phase_summary(inputs, verdicts):
    failures = [(index, verdict) for index, verdict in enumerate(verdicts) if verdict is not None]
    summary = {
        "status": "fail" if failures else "pass",
        "inputs": len(inputs),
        "passed": len(inputs) - len(failures),
    }
    if failures:
        summary["first_failure"] = {"input": failures[0][0], "reason": failures[0][1]}
    return summary


def check_phase(problem, function, source, solution_path, inputs, time_limit_settings):
    min_time_limit, time_limit_factor = time_limit_settings
    expected_outputs, durations = reference_outputs(function, inputs)
    time_limits = [max(min_time_limit, time_limit_factor * duration) for duration in durations]
    report = run_candidate(source, solution_path, problem["entry_point"], inputs, time_limits)
    if "timed_out" in report:
        return {"status": "timeout", "inputs": len(inputs), "passed": 0}
    if "load_error" in report:
        return {"status": "fail", "inputs": len(inputs), "passed": 0, "load_error": report["load_error"]}
    verdicts = judged_inputs(problem["oracle"], inputs, expected_outputs, report["outcomes"], problem["atol"])
    return phase_summary(inputs, verdicts)


def closed_to_others(directory):
    try:
        os.chmod(directory, 0o700)
    except OSError:
        return False
    return True


def check_solution(solution_path, time_limit_settings):
    problem = json.loads(PROBLEM_PATH.read_text(encoding="utf-8"))
    summary = {"task_id": problem["task_id"], "passed": False}
    if running_as_root():
        summary["verifier_directory_closed"] = closed_to_others(TESTS_DIRECTORY)
    try:
        source = solution_source(solution_path)
    except SolutionRejected as error:
        summary["rejected"] = str(error)
        return summary
    if problem["oracle"] not in ORACLES:
        raise ValueError(f"problem.json names an unknown oracle, {problem['oracle']!r}")
    function = reference_function(problem["entry_point"])
    summary["phases"] = []
    for phase in problem["phases"]:
        phase_result = check_phase(problem, function, source, solution_path, phase["inputs"], time_limit_settings)
        summary["phases"].append({"name": phase["name"], **phase_result})
        if phase_result["status"] != "pass":
            return summary
    summary["passed"] = True
    return summary


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Check a solution to a function-completion problem.")
    parser.add_argument("--solution", required=True, type=pathlib.Path)
    parser.add_argument("--summary", type=pathlib.Path)
    parser.add_argument("--min-time-limit", type=float, default=EVALPLUS_MIN_TIME_LIMIT_SECONDS)
    parser.add_argument("--time-limit-factor", type=float, default=EVALPLUS_TIME_LIMIT_FACTOR)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    summary = check_solution(options.solution, (options.min_time_limit, options.time_limit_factor))
    document = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if options.summary:
        options.summary.write_text(document, encoding="utf-8")
    sys.stdout.write(document)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
