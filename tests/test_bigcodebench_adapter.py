import contextlib
import copy
import io
import json
import pathlib
import stat
import tempfile
import tomllib
import unittest

from adapters.bigcodebench import adapter
from adapters.common.generation import GenerationContext
from adapters.common.package_digest import package_digest
from bigcodebench_fixture import CANARY, PROBLEMS, write_upstream

PINNED_IMAGE = "ghcr.io/node-q/hbench-envs@sha256:" + "b" * 64
TASK_NAMES = ["bigcodebench-0", "bigcodebench-12", "bigcodebench-7"]


class BigCodeBenchAdapterTest(unittest.TestCase):
    def setUp(self):
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))

    def generate(self, directory_name="tasks", docker_image=None, excluded_task_ids=(), **upstream):
        upstream_directory = self.workspace / f"{directory_name}-upstream"
        upstream_directory.mkdir()
        upstream_files = write_upstream(upstream_directory, **upstream)
        out_dir = self.workspace / directory_name
        out_dir.mkdir()
        context = GenerationContext(dataset="bigcodebench", version="1.0", canary=CANARY, docker_image=docker_image)
        return out_dir, adapter.generate(upstream_files, out_dir, context, excluded_task_ids=excluded_task_ids)

    def manifest(self, out_dir, name):
        return tomllib.loads((out_dir / name / "task.toml").read_text(encoding="utf-8"))

    def test_writes_one_task_per_problem_named_after_its_number(self):
        out_dir, names = self.generate()
        self.assertEqual(names, TASK_NAMES)
        self.assertEqual(sorted(path.name for path in out_dir.iterdir()), TASK_NAMES)
        self.assertEqual(
            sorted(path.relative_to(out_dir / "bigcodebench-7").as_posix() for path in (out_dir / "bigcodebench-7").rglob("*") if path.is_file()),
            [
                "instruction.md",
                "solution/solution.py",
                "solution/solve.sh",
                "task.toml",
                "tests/check_solution.py",
                "tests/problem.json",
                "tests/test.sh",
                "tests/unittest_runner.py",
            ],
        )

    def test_leaves_out_the_excluded_tasks_and_refuses_unknown_ones(self):
        out_dir, names = self.generate(excluded_task_ids=("BigCodeBench/7",))
        self.assertEqual(names, ["bigcodebench-0", "bigcodebench-12"])
        self.assertEqual(sorted(path.name for path in out_dir.iterdir()), names)
        with self.assertRaisesRegex(adapter.AdapterError, "the excluded tasks bigcodebench-99 are not in the full split"):
            self.generate("unknown", excluded_task_ids=("BigCodeBench/99",))
        self.assertTrue(all(adapter.task_name(task_id) for task_id in adapter.EXCLUDED_TASKS))

    def test_generating_twice_gives_the_same_package_digests(self):
        first, _ = self.generate("first", PINNED_IMAGE)
        second, _ = self.generate("second", PINNED_IMAGE)
        for name in TASK_NAMES:
            self.assertEqual(package_digest(first / name), package_digest(second / name))

    def test_scripts_are_executable_and_other_files_are_not(self):
        out_dir, _ = self.generate()
        for path in (out_dir / "bigcodebench-0").rglob("*"):
            if path.is_file():
                self.assertEqual(bool(path.stat().st_mode & stat.S_IXUSR), path.suffix == ".sh", path)

    def test_the_instruction_shows_the_complete_prompt_and_not_the_solution(self):
        out_dir, _ = self.generate()
        instruction = (out_dir / "bigcodebench-7" / "instruction.md").read_text(encoding="utf-8")
        self.assertTrue(instruction.startswith(f"<!-- {CANARY} -->\n\n"))
        self.assertIn("```python\n" + PROBLEMS[1]["complete_prompt"] + "```\n", instruction)
        self.assertIn("`/app/solution.py`", instruction)
        self.assertIn("240 seconds", instruction)
        self.assertNotIn("most_common(1)", instruction)
        self.assertEqual(adapter.task_problems(out_dir / "bigcodebench-7"), [])

    def test_task_toml_has_a_bare_name_the_hard_tag_and_the_image_once_it_is_built(self):
        out_dir, _ = self.generate(docker_image=PINNED_IMAGE)
        hard = self.manifest(out_dir, "bigcodebench-7")
        self.assertEqual(hard["task"]["name"], "bigcodebench-7")
        self.assertEqual(hard["metadata"]["tags"], ["bigcodebench", "code-generation", "hard"])
        self.assertEqual(hard["metadata"]["upstream_task_id"], "BigCodeBench/7")
        self.assertEqual(hard["metadata"]["libraries"], ["collections"])
        self.assertEqual(hard["environment"]["docker_image"], PINNED_IMAGE)
        self.assertEqual(hard["verifier"]["timeout_sec"], 360.0)
        full_only = self.manifest(out_dir, "bigcodebench-0")
        self.assertEqual(full_only["metadata"]["tags"], ["bigcodebench", "code-generation"])
        unbuilt, _ = self.generate("unbuilt")
        self.assertNotIn("docker_image", self.manifest(unbuilt, "bigcodebench-0")["environment"])

    def test_the_tests_hold_the_unit_tests_and_the_solution_is_upstreams_ground_truth(self):
        out_dir, _ = self.generate()
        problem = json.loads((out_dir / "bigcodebench-7" / "tests" / "problem.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {key: problem[key] for key in ("task_id", "entry_point", "code_prompt", "test")},
            {key: PROBLEMS[1][key] for key in ("task_id", "entry_point", "code_prompt", "test")},
        )
        solution = (out_dir / "bigcodebench-7" / "solution" / "solution.py").read_text(encoding="utf-8")
        self.assertEqual(solution, f"# {CANARY}\n" + PROBLEMS[1]["complete_prompt"] + "\n" + PROBLEMS[1]["canonical_solution"])
        for path in (out_dir / "bigcodebench-7").glob("*/*"):
            self.assertIn(CANARY, path.read_text(encoding="utf-8"), path)

    def test_refuses_problems_it_cannot_name_or_read(self):
        missing_field = copy.deepcopy(PROBLEMS)
        missing_field[1]["test"] = None
        duplicate = copy.deepcopy(PROBLEMS) + [copy.deepcopy(PROBLEMS[0])]
        unnamed = copy.deepcopy(PROBLEMS)
        unnamed[0]["task_id"] = "BigCodeBench/007"
        unlisted_libraries = copy.deepcopy(PROBLEMS)
        unlisted_libraries[2]["libs"] = "time"
        other_definition = copy.deepcopy(PROBLEMS)
        other_definition[0]["code_prompt"] = "def other(numbers):\n"
        changed_hard_row = [dict(PROBLEMS[1], test=PROBLEMS[1]["test"] + "\n")]
        unknown_hard_row = [dict(PROBLEMS[1], task_id="BigCodeBench/99")]
        for upstream, message in (
            ({"problems": missing_field}, "has no test"),
            ({"problems": duplicate}, "BigCodeBench/0 appears twice"),
            ({"problems": unnamed}, "is not BigCodeBench/<n>"),
            ({"problems": unlisted_libraries}, "is not a list of module names"),
            ({"problems": other_definition}, "the code_prompt does not end by defining task_func"),
            ({"hard_problems": changed_hard_row}, "the Hard split's test differ"),
            ({"hard_problems": unknown_hard_row}, "is in the Hard split but not in the full split"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(adapter.AdapterError, message):
                self.generate(f"refused-{len(list(self.workspace.iterdir()))}", **upstream)

    def test_every_oracle_passes_and_every_wrong_solution_fails(self):
        out_dir, _ = self.generate()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = adapter.verify_tasks(out_dir, jobs=3)
        self.assertEqual(exit_code, 0, output.getvalue())
        self.assertIn("3 of 3 tasks: the oracle passes and a wrong solution fails", output.getvalue())


if __name__ == "__main__":
    unittest.main()
