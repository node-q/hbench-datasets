"""Run a candidate solution on inputs in this interpreter, as EvalPlus's unsafe_execute does.

check_solution.py passes this file's source with `python -c` and a JSON request on standard input:
source (base64), filename, entry_point, inputs, time_limits and memory_limit_bytes. It writes one
JSON document to the standard output it started with: {"load_error": name} when the solution does
not load, else {"outcomes": [...]}, one per input, each {"returned": tagged value},
{"raised": exception name}, {"timed_out": true} or {"unencodable": exception name}.
"""

import base64
import builtins
import faulthandler
import io
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import types
from decimal import Decimal
from fractions import Fraction

MEMORY_LIMITS = (resource.RLIMIT_AS, resource.RLIMIT_DATA, resource.RLIMIT_STACK)
DISABLED_OS_FUNCTIONS = (
    "kill",
    "system",
    "putenv",
    "remove",
    "removedirs",
    "rmdir",
    "fchdir",
    "setuid",
    "fork",
    "forkpty",
    "killpg",
    "rename",
    "renames",
    "truncate",
    "replace",
    "unlink",
    "fchmod",
    "fchown",
    "chmod",
    "chown",
    "chroot",
    "lchflags",
    "lchmod",
    "lchown",
    "getcwd",
    "chdir",
)
DISABLED_SHUTIL_FUNCTIONS = ("rmtree", "move", "chown")
BLOCKED_MODULES = ("ipdb", "joblib", "resource", "psutil", "tkinter")


class TimeLimitExceeded(Exception):
    pass


class UnreadableStream(io.StringIO):
    def read(self, *arguments, **keywords):
        raise OSError("standard input is not readable")

    def readline(self, *arguments, **keywords):
        raise OSError("standard input is not readable")

    def readlines(self, *arguments, **keywords):
        raise OSError("standard input is not readable")

    def readable(self, *arguments, **keywords):
        return False


def raise_time_limit_exceeded(signal_number, frame):
    raise TimeLimitExceeded()


def silence_standard_streams():
    null_descriptor = os.open(os.devnull, os.O_RDWR)
    for descriptor in (0, 1, 2):
        os.dup2(null_descriptor, descriptor)
    os.close(null_descriptor)
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = sys.stdout
    sys.stdin = UnreadableStream()


def limit_memory(maximum_bytes):
    for limit in MEMORY_LIMITS:
        try:
            resource.setrlimit(limit, (maximum_bytes, maximum_bytes))
        except (OSError, ValueError):
            pass


def disable_destructive_functions():
    faulthandler.disable()
    builtins.exit = None
    builtins.quit = None
    builtins.help = None
    builtins.open = None
    os.environ["OMP_NUM_THREADS"] = "1"
    for name in DISABLED_OS_FUNCTIONS:
        if hasattr(os, name):
            setattr(os, name, None)
    for name in DISABLED_SHUTIL_FUNCTIONS:
        setattr(shutil, name, None)
    subprocess.Popen = None
    for name in BLOCKED_MODULES:
        sys.modules[name] = None


def encoded(value):
    if value is None:
        return ["n"]
    if isinstance(value, bool):
        return ["b", bool.__bool__(value)]
    if isinstance(value, int):
        return ["i", format(int.__int__(value), "x")]
    if isinstance(value, float):
        return ["f", float.hex(float.__float__(value))]
    if isinstance(value, complex):
        number = complex.__complex__(value)
        return ["c", float.hex(number.real), float.hex(number.imag)]
    if isinstance(value, str):
        return ["s", str.__str__(value)]
    if isinstance(value, (bytes, bytearray)):
        return ["y", bytes(memoryview(value)).hex()]
    if isinstance(value, Fraction):
        return ["q", format(value.numerator, "x"), format(value.denominator, "x")]
    if isinstance(value, Decimal):
        return ["D", Decimal.__str__(value)]
    if isinstance(value, tuple):
        return ["t", [encoded(item) for item in tuple.__getitem__(value, slice(None))]]
    if isinstance(value, list):
        return ["l", [encoded(item) for item in list.copy(value)]]
    if isinstance(value, frozenset):
        return ["F", [encoded(item) for item in frozenset.copy(value)]]
    if isinstance(value, set):
        return ["S", [encoded(item) for item in set.copy(value)]]
    if isinstance(value, dict):
        return ["d", [[encoded(key), encoded(item)] for key, item in dict.items(dict.copy(value))]]
    raise TypeError(f"cannot compare a {type(value).__name__}")


def outcome_of_call(function, arguments, time_limit):
    signal.signal(signal.SIGALRM, raise_time_limit_exceeded)
    signal.setitimer(signal.ITIMER_REAL, time_limit)
    try:
        returned = function(*arguments)
    except TimeLimitExceeded:
        return {"timed_out": True}
    except BaseException as error:
        return {"raised": type(error).__name__}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    try:
        return {"returned": encoded(returned)}
    except BaseException as error:
        return {"unencodable": type(error).__name__}


def guarded_outcome_of_call(function, arguments, time_limit):
    try:
        return outcome_of_call(function, arguments, time_limit)
    except TimeLimitExceeded:
        return {"timed_out": True}


def evaluate(request):
    module = types.ModuleType("solution")
    module.__file__ = request["filename"]
    sys.modules["solution"] = module
    try:
        code = compile(base64.b64decode(request["source"]), request["filename"], "exec", dont_inherit=True)
        exec(code, module.__dict__)
        function = module.__dict__[request["entry_point"]]
    except BaseException as error:
        return {"load_error": type(error).__name__}
    return {
        "outcomes": [
            guarded_outcome_of_call(function, arguments, time_limit)
            for arguments, time_limit in zip(request["inputs"], request["time_limits"])
        ]
    }


def main():
    request = json.loads(sys.stdin.buffer.read())
    results = os.fdopen(os.dup(1), "w", encoding="utf-8")
    silence_standard_streams()
    limit_memory(request["memory_limit_bytes"])
    disable_destructive_functions()
    report = evaluate(request)
    results.write(json.dumps(report))
    results.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
