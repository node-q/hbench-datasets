import contextlib
import copy
import io
import json
import pathlib
import stat
import tempfile
import tomllib
import unittest

from adapters.common.generation import GenerationContext
from adapters.common.package_digest import package_digest
from adapters.humaneval_plus import adapter
from humaneval_plus_fixture import CANARY, PROBLEMS, write_upstream

PINNED_IMAGE = "ghcr.io/node-q/hbench-envs@sha256:" + "a" * 64
TASK_NAMES = ["humaneval-plus-0", "humaneval-plus-2", "humaneval-plus-32"]


class HumanEvalPlusAdapterTest(unittest.TestCase):
    def setUp(self):
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.upstream_path = self.workspace / adapter.UPSTREAM_FILE_NAME
        write_upstream(self.upstream_path)

    def generate(self, directory_name="tasks", docker_image=None, problems=None):
        if problems is not None:
            write_upstream(self.upstream_path, problems)
        out_dir = self.workspace / directory_name
        out_dir.mkdir()
        context = GenerationContext(dataset="humaneval-plus", version="1.0", canary=CANARY, docker_image=docker_image)
        names = adapter.generate({adapter.UPSTREAM_FILE_NAME: self.upstream_path}, out_dir, context)
        return out_dir, names

    def test_writes_one_task_per_problem_named_after_its_number(self):
        out_dir, names = self.generate()
        self.assertEqual(names, TASK_NAMES)
        self.assertEqual(sorted(path.name for path in out_dir.iterdir()), TASK_NAMES)
        self.assertEqual(
            sorted(path.relative_to(out_dir / "humaneval-plus-0").as_posix() for path in (out_dir / "humaneval-plus-0").rglob("*") if path.is_file()),
            [
                "instruction.md",
                "solution/solution.py",
                "solution/solve.sh",
                "task.toml",
                "tests/candidate_runner.py",
                "tests/check_solution.py",
                "tests/problem.json",
                "tests/reference_solution.py",
                "tests/test.sh",
            ],
        )

    def test_generating_twice_gives_the_same_package_digests(self):
        first, _ = self.generate("first", PINNED_IMAGE)
        second, _ = self.generate("second", PINNED_IMAGE)
        for name in TASK_NAMES:
            self.assertEqual(package_digest(first / name), package_digest(second / name))

    def test_scripts_are_executable_and_other_files_are_not(self):
        out_dir, _ = self.generate()
        for path in (out_dir / "humaneval-plus-0").rglob("*"):
            if path.is_file():
                executable = bool(path.stat().st_mode & stat.S_IXUSR)
                self.assertEqual(executable, path.suffix == ".sh", path)

    def test_the_instruction_shows_the_prompt_and_not_the_solution(self):
        out_dir, _ = self.generate()
        instruction = (out_dir / "humaneval-plus-0" / "instruction.md").read_text(encoding="utf-8")
        self.assertTrue(instruction.startswith(f"<!-- {CANARY} -->\n\n"))
        self.assertIn("```python\n" + PROBLEMS[0]["prompt"] + "```\n", instruction)
        self.assertIn("`/app/solution.py`", instruction)
        self.assertNotIn("return a + b", instruction)
        self.assertEqual(adapter.task_problems(out_dir / "humaneval-plus-0"), [])

    def test_task_toml_names_the_task_and_the_image_once_it_is_built(self):
        out_dir, _ = self.generate(docker_image=PINNED_IMAGE)
        manifest = tomllib.loads((out_dir / "humaneval-plus-2" / "task.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["task"]["name"], "humaneval-plus-2")
        self.assertEqual(manifest["metadata"]["category"], "python")
        self.assertEqual(manifest["metadata"]["upstream_task_id"], "HumanEval/2")
        self.assertEqual(manifest["environment"]["docker_image"], PINNED_IMAGE)
        self.assertGreater(manifest["verifier"]["timeout_sec"], 0)
        unbuilt, _ = self.generate("unbuilt")
        manifest = tomllib.loads((unbuilt / "humaneval-plus-2" / "task.toml").read_text(encoding="utf-8"))
        self.assertNotIn("docker_image", manifest["environment"])

    def test_the_tests_hold_the_inputs_and_the_reference_and_carry_the_canary(self):
        out_dir, _ = self.generate()
        problem = json.loads((out_dir / "humaneval-plus-32" / "tests" / "problem.json").read_text(encoding="utf-8"))
        self.assertEqual(problem["oracle"], "polynomial-root")
        self.assertEqual(problem["atol"], 0.0001)
        self.assertEqual(
            problem["phases"], [{"name": "base", "inputs": [[[1, 2]]]}, {"name": "plus", "inputs": [[[-6, 3]]]}]
        )
        reference = (out_dir / "humaneval-plus-32" / "tests" / "reference_solution.py").read_text(encoding="utf-8")
        self.assertEqual(reference, f"# {CANARY}\n" + PROBLEMS[2]["prompt"] + PROBLEMS[2]["canonical_solution"])
        self.assertEqual(reference, (out_dir / "humaneval-plus-32" / "solution" / "solution.py").read_text(encoding="utf-8"))
        default = json.loads((out_dir / "humaneval-plus-0" / "tests" / "problem.json").read_text(encoding="utf-8"))
        self.assertEqual(default["oracle"], "default")
        for path in (out_dir / "humaneval-plus-0").glob("*/*"):
            if path.parent.name in ("tests", "solution"):
                self.assertIn(CANARY, path.read_text(encoding="utf-8"), path)

    def test_refuses_problems_it_cannot_name_or_read(self):
        missing_field = copy.deepcopy(PROBLEMS)
        del missing_field[1]["plus_input"]
        duplicate = copy.deepcopy(PROBLEMS) + [copy.deepcopy(PROBLEMS[0])]
        unnamed = copy.deepcopy(PROBLEMS)
        unnamed[0]["task_id"] = "HumanEval/007"
        for problems, message in (
            (missing_field, "has no plus_input"),
            (duplicate, "HumanEval/0 appears twice"),
            (unnamed, "is not HumanEval/<n>"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                self.workspace = pathlib.Path(directory)
                self.upstream_path = self.workspace / adapter.UPSTREAM_FILE_NAME
                with self.assertRaisesRegex(adapter.AdapterError, message):
                    self.generate(problems=problems)

    def test_every_oracle_passes_and_every_wrong_solution_fails(self):
        out_dir, _ = self.generate()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = adapter.verify_tasks(out_dir, jobs=3)
        self.assertEqual(exit_code, 0, output.getvalue())
        self.assertIn("3 of 3 tasks: the oracle passes and a wrong solution fails", output.getvalue())


if __name__ == "__main__":
    unittest.main()
