"""Check function-checker tasks: each task's oracle passes and a wrong solution fails.

For each task, verify_tasks copies tests/ to a fresh directory, as hbench uploads it to /tests, and runs
tests/check_solution.py directly: on solution/solution.py, which must pass, and on a solution whose
entry point raises NotImplementedError, which must fail. Adapters of function-completion datasets
call it from their own verify_tasks; python -m adapters.verify runs it. An adapter whose tasks have
another checker, answer file or wrong solutions passes a Checker: the checker's path in the task, the
oracle's, the name the answer is written under in /app, and wrong_answers(task), the texts that must
fail.
"""

import collections.abc
import concurrent.futures
import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib

CHECKER_RELATIVE_PATH = pathlib.Path("tests") / "check_solution.py"
ORACLE_RELATIVE_PATH = pathlib.Path("solution") / "solution.py"
WRONG_SOLUTION_TEMPLATE = "def {entry_point}(*arguments, **keywords):\n    raise NotImplementedError\n"


def raising_solution(task):
    problem = json.loads((task / "tests" / "problem.json").read_text(encoding="utf-8"))
    return [WRONG_SOLUTION_TEMPLATE.format(entry_point=problem["entry_point"])]


@dataclasses.dataclass(frozen=True)
class Checker:
    script: pathlib.Path = CHECKER_RELATIVE_PATH
    oracle: pathlib.Path = ORACLE_RELATIVE_PATH
    answer_name: str = "solution.py"
    wrong_answers: collections.abc.Callable = raising_solution


FUNCTION_CHECKER = Checker()


def task_directories(tasks_directory, names):
    tasks = sorted(path for path in tasks_directory.iterdir() if (path / "task.toml").is_file())
    if not names:
        return tasks
    unknown = sorted(set(names) - {task.name for task in tasks})
    if unknown:
        raise SystemExit(f"no such task: {', '.join(unknown)}")
    return [task for task in tasks if task.name in names]


def verifier_timeout(task):
    with open(task / "task.toml", "rb") as manifest:
        return tomllib.load(manifest)["verifier"]["timeout_sec"]


def run_checker(task, solution_text, checker=FUNCTION_CHECKER):
    with tempfile.TemporaryDirectory(prefix=f"{task.name}-") as workspace:
        workspace = pathlib.Path(workspace)
        shutil.copytree(task / "tests", workspace / "tests")
        solution_path = workspace / "app" / checker.answer_name
        solution_path.parent.mkdir()
        solution_path.write_text(solution_text, encoding="utf-8")
        solution_path.chmod(0o644)
        os.chmod(solution_path.parent, 0o755)
        os.chmod(workspace, 0o755)
        summary_path = workspace / "summary.json"
        started = time.monotonic()
        completed = subprocess.run(
            [
                sys.executable,
                str(workspace / checker.script),
                "--solution",
                str(solution_path),
                "--summary",
                str(summary_path),
            ],
            env={**os.environ, "PYTHONHASHSEED": "0"},
            capture_output=True,
            text=True,
            timeout=verifier_timeout(task),
        )
        elapsed = time.monotonic() - started
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    return completed, summary, elapsed


def phase_counts(summary):
    return "+".join(f"{phase['passed']}/{phase['inputs']}" for phase in summary.get("phases", []))


def verify_task(task, checker=FUNCTION_CHECKER):
    try:
        return checked_task(task, checker)
    except subprocess.TimeoutExpired as error:
        return task.name, [f"the checker ran longer than the verifier's {error.timeout}s"], ""


def oracle_detail(summary, seconds):
    if not summary:
        return ""
    if "phases" in summary:
        return f"oracle passed {phase_counts(summary)} inputs in {seconds:.1f}s"
    return f"oracle passed in {seconds:.1f}s"


def wrong_answers_detail(count):
    return "a wrong solution failed" if count == 1 else f"{count} wrong solutions failed"


def checked_task(task, checker=FUNCTION_CHECKER):
    problems = []
    oracle, oracle_summary, oracle_seconds = run_checker(task, (task / checker.oracle).read_text(encoding="utf-8"), checker)
    if oracle.returncode != 0 or not (oracle_summary and oracle_summary["passed"]):
        problems.append(f"the oracle does not pass (exit {oracle.returncode}): {oracle.stdout.strip()} {oracle.stderr.strip()}")
    wrong_texts = checker.wrong_answers(task)
    for wrong_text in wrong_texts:
        wrong, wrong_summary, _ = run_checker(task, wrong_text, checker)
        if wrong.returncode != 1 or wrong_summary is None or wrong_summary["passed"] or "rejected" in wrong_summary:
            problems.append(f"a wrong solution does not fail (exit {wrong.returncode}): {wrong.stdout.strip()} {wrong.stderr.strip()}")
    detail = f"{oracle_detail(oracle_summary, oracle_seconds)}; {wrong_answers_detail(len(wrong_texts))}"
    return task.name, problems, detail


def verify_tasks(tasks_directory, jobs=1, names=(), checker=FUNCTION_CHECKER):
    tasks = task_directories(pathlib.Path(tasks_directory), names)
    if not tasks:
        print(f"no tasks in {tasks_directory}", file=sys.stderr)
        return 1
    failed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as executor:
        for name, problems, detail in executor.map(lambda task: verify_task(task, checker), tasks):
            if problems:
                failed.append(name)
                for problem in problems:
                    print(f"FAIL {name}: {problem}")
            else:
                print(f"ok   {name}: {detail}")
    print(f"{len(tasks) - len(failed)} of {len(tasks)} tasks: the oracle passes and a wrong solution fails")
    return 1 if failed else 0
