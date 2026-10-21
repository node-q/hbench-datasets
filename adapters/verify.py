"""Check an adapter's generated tasks with its own verify_tasks: each oracle passes, a wrong solution fails.

Usage: python -m adapters.verify ADAPTER TASKS_DIRECTORY [--jobs N] [--task NAME ...] [--summary FILE]

ADAPTER is the adapter's directory under adapters/, such as humaneval_plus. Adapters and what they
import use only the Python standard library, so this runs in a task's environment image or its base.
--summary, for an adapter whose verify_tasks takes summary_path, writes what it checked as JSON.
"""

import argparse
import importlib
import pathlib
import sys


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Check an adapter's generated tasks.")
    parser.add_argument("adapter")
    parser.add_argument("tasks_directory", type=pathlib.Path)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--task", action="append", default=[])
    parser.add_argument("--summary", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    adapter = importlib.import_module(f"adapters.{options.adapter}.adapter")
    summary = {"summary_path": options.summary} if options.summary else {}
    return adapter.verify_tasks(options.tasks_directory, jobs=options.jobs, names=options.task, **summary)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
