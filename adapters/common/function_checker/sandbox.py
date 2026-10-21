"""Run sandbox_runner.py in check_solution.py's CandidateSandbox and exchange JSON lines with it.

A checker next to this file imports it. runner_request builds a request for one of sandbox_runner.py's
modes, carrying candidate_runner.py's source and check_solution.py's memory limit. run_once runs a
function or expression request and returns its one report; CallsSession keeps a calls request's
runner going, one call at a time. A runner that dies, or writes anything but a JSON object, reports
{"load_error": "no report"}.
"""

import base64
import json
import pathlib
import pickle
import subprocess
import sys

from check_solution import EVALPLUS_MEMORY_LIMIT_BYTES, CandidateSandbox, physical_memory_bytes

TESTS_DIRECTORY = pathlib.Path(__file__).resolve().parent
SANDBOX_RUNNER_PATH = TESTS_DIRECTORY / "sandbox_runner.py"
CANDIDATE_RUNNER_PATH = TESTS_DIRECTORY / "candidate_runner.py"
NO_REPORT = {"load_error": "no report"}


def encoded_bytes(data):
    return base64.b64encode(data).decode("ascii")


def runner_request(mode, **fields):
    return {
        "library": CANDIDATE_RUNNER_PATH.read_text(encoding="utf-8"),
        "mode": mode,
        "memory_limit_bytes": min(EVALPLUS_MEMORY_LIMIT_BYTES, physical_memory_bytes()),
        **fields,
    }


def runner_arguments():
    return [sys.executable, "-s", "-P", "-c", SANDBOX_RUNNER_PATH.read_text(encoding="utf-8")]


def request_line(request):
    return json.dumps(request).encode("utf-8") + b"\n"


def report_of(line):
    try:
        report = json.loads(line)
    except ValueError:
        return dict(NO_REPORT)
    return report if isinstance(report, dict) else dict(NO_REPORT)


def stop(sandbox, process):
    sandbox.stop_every_process(process)
    process.kill()
    process.wait()
    for stream in (process.stdin, process.stdout):
        stream.close()


def run_once(request, time_limit):
    with CandidateSandbox() as sandbox:
        process = sandbox.start(runner_arguments())
        try:
            output, _ = process.communicate(request_line(request), timeout=time_limit)
        except subprocess.TimeoutExpired:
            output = None
        finally:
            stop(sandbox, process)
    if output is None:
        return {"timed_out": True}
    return report_of(output.partition(b"\n")[0])


class CallsSession:
    def __init__(self, request):
        self.request = request

    def __enter__(self):
        self.sandbox = CandidateSandbox().__enter__()
        self.process = self.sandbox.start(runner_arguments())
        self.send(request_line(self.request))
        return self

    def __exit__(self, *exception):
        stop(self.sandbox, self.process)
        self.sandbox.__exit__(*exception)

    def send(self, line):
        try:
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def receive(self):
        return report_of(self.process.stdout.readline())

    def call(self, arguments):
        self.send(encoded_bytes(pickle.dumps(tuple(arguments))).encode("ascii") + b"\n")
        return self.receive()
