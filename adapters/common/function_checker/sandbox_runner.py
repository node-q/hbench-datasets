"""Run a candidate's code for a checker in this interpreter, guarded as candidate_runner.py guards it.

sandbox.py passes this file's source with `python -c` and writes a JSON request line to standard
input: library, candidate_runner.py's source, which this loads as a module; mode; memory_limit_bytes;
and the mode's fields. This silences the standard streams, limits memory and disables destructive
functions as candidate_runner.py does, then runs the mode, writing JSON lines to the standard output
it started with. The modes:

  function    source (base64), filename, prelude, entry_point, inputs (base64 pickle) and
              time_limits: one line, {"load_error": name} or {"outcomes": [...]}, as
              candidate_runner.py reports them. With output "not-none", each result is reduced to
              whether it is not None, unless it is a bool, as EvalPlus checks such MBPP+ problems.
  calls       source, filename, prelude, entry_point and time_limit: one line, {"loaded": true} or
              {"load_error": name}, then, for each further request line, a base64 pickle of a tuple
              of arguments, the outcome of calling entry_point with them.
  expression  code, answer, filename, entry_point and time_limit: one line, the outcome of the
              answer, a call of entry_point. Its arguments are evaluated among code's names that are
              not modules and ARGUMENT_BUILTINS only; entry_point is then called on them from a fresh
              run of code, with builtins of its own.

The prelude runs in the solution's namespace before its source, as a harness prepends its imports.
"""

import ast
import base64
import builtins
import json
import os
import pickle
import sys
import types

NOT_NONE_OUTPUT = "not-none"
ARGUMENTS_CAPTURE_NAME = "__arguments__"
ARGUMENT_BUILTINS = (
    "abs",
    "all",
    "any",
    "ascii",
    "bin",
    "bool",
    "bytearray",
    "bytes",
    "chr",
    "complex",
    "dict",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "format",
    "frozenset",
    "hash",
    "hex",
    "int",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "list",
    "map",
    "max",
    "min",
    "next",
    "oct",
    "ord",
    "pow",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
)


def library_module(source):
    library = types.ModuleType("candidate_runner")
    exec(compile(source, "candidate_runner.py", "exec", dont_inherit=True), library.__dict__)
    return library


def send(results, document):
    results.write(json.dumps(document) + "\n")
    results.flush()


def loaded_function(request):
    module = types.ModuleType("solution")
    module.__file__ = request["filename"]
    sys.modules["solution"] = module
    exec(compile(request["prelude"], "<prelude>", "exec", dont_inherit=True), module.__dict__)
    source = base64.b64decode(request["source"])
    exec(compile(source, request["filename"], "exec", dont_inherit=True), module.__dict__)
    return module.__dict__[request["entry_point"]]


def reduced_to_not_none(function):
    def reduced(*arguments):
        returned = function(*arguments)
        return returned if isinstance(returned, bool) else returned is not None

    return reduced


def run_function(library, request, requests, results):
    inputs = pickle.loads(base64.b64decode(request["inputs"]))
    try:
        function = loaded_function(request)
    except BaseException as error:
        send(results, {"load_error": type(error).__name__})
        return
    if request.get("output") == NOT_NONE_OUTPUT:
        function = reduced_to_not_none(function)
    outcomes = [
        library.guarded_outcome_of_call(function, arguments, time_limit)
        for arguments, time_limit in zip(inputs, request["time_limits"])
    ]
    send(results, {"outcomes": outcomes})


def serve_calls(library, request, requests, results):
    try:
        function = loaded_function(request)
    except BaseException as error:
        send(results, {"load_error": type(error).__name__})
        return
    send(results, {"loaded": True})
    for line in requests:
        arguments = pickle.loads(base64.b64decode(line))
        send(results, library.guarded_outcome_of_call(function, arguments, request["time_limit"]))


def captured_arguments(*arguments, **keywords):
    return arguments, keywords


def argument_namespace(definitions):
    namespace = {
        name: value
        for name, value in definitions.items()
        if not name.startswith("__") and not isinstance(value, types.ModuleType)
    }
    namespace["__builtins__"] = {name: getattr(builtins, name) for name in ARGUMENT_BUILTINS}
    namespace[ARGUMENTS_CAPTURE_NAME] = captured_arguments
    return namespace


def answer_result(code, capture, entry_point):
    definitions = {}
    exec(code, definitions)
    arguments, keywords = eval(capture, argument_namespace(definitions))
    namespace = {"__builtins__": dict(vars(builtins))}
    exec(code, namespace)
    return namespace[entry_point](*arguments, **keywords)


def evaluate_answer(library, request, requests, results):
    answer = ast.parse(request["answer"], mode="eval")
    answer.body.func = ast.Name(id=ARGUMENTS_CAPTURE_NAME, ctx=ast.Load())
    capture = compile(ast.fix_missing_locations(answer), request["filename"], "eval", dont_inherit=True)
    code = compile(request["code"], "<code>", "exec", dont_inherit=True)
    outcome = library.guarded_outcome_of_call(
        lambda: answer_result(code, capture, request["entry_point"]), (), request["time_limit"]
    )
    send(results, outcome)


MODES = {"function": run_function, "calls": serve_calls, "expression": evaluate_answer}


def main():
    requests = os.fdopen(os.dup(0), "rb")
    request = json.loads(requests.readline())
    results = os.fdopen(os.dup(1), "w", encoding="utf-8")
    library = library_module(request["library"])
    mode = MODES[request["mode"]]
    library.silence_standard_streams()
    library.limit_memory(request["memory_limit_bytes"])
    library.disable_destructive_functions()
    mode(library, request, requests, results)
    os._exit(0)


if __name__ == "__main__":
    main()
