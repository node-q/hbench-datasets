import pathlib
import tempfile
import unittest

import check_generated_tasks
import generated_source
from adapters.common.generation import GenerationContext
from adapters.humaneval_plus import adapter
from humaneval_plus_fixture import CANARY, write_upstream
from source_descriptor import REPOSITORY_ROOT

PINNED_IMAGE = "ghcr.io/node-q/hbench-envs@sha256:" + "f" * 64


class TaskLayoutTest(unittest.TestCase):
    def setUp(self):
        workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        upstream_path = workspace / adapter.UPSTREAM_FILE_NAME
        write_upstream(upstream_path)
        tasks_directory = workspace / "tasks"
        tasks_directory.mkdir()
        context = GenerationContext(dataset="humaneval-plus", version="1.0", canary=CANARY, docker_image=PINNED_IMAGE)
        adapter.generate({adapter.UPSTREAM_FILE_NAME: upstream_path}, tasks_directory, context)
        self.context_files = check_generated_tasks.files_of(REPOSITORY_ROOT / "images" / "humaneval-plus")
        self.task_directory = tasks_directory / "humaneval-plus-0"
        generated_source.add_environment(self.task_directory, generated_source.build_context_files(REPOSITORY_ROOT / "images" / "humaneval-plus"))

    def problems(self, docker_image=PINNED_IMAGE):
        return check_generated_tasks.task_layout_problems(
            self.task_directory, CANARY, docker_image, self.context_files, adapter
        )

    def assertProblem(self, fragment, **options):
        problems = self.problems(**options)
        self.assertTrue(any(fragment in problem for problem in problems), f"no problem mentions {fragment!r}: {problems}")

    def test_a_generated_task_is_valid(self):
        self.assertEqual(self.problems(), [])

    def test_docker_image_must_be_the_locked_image(self):
        self.assertProblem("[environment].docker_image is", docker_image=None)

    def test_the_task_is_named_by_its_bare_directory_name(self):
        manifest = self.task_directory / "task.toml"
        text = manifest.read_text(encoding="utf-8")
        manifest.write_text(text.replace('name = "humaneval-plus-0"', 'name = "node-q/humaneval-plus-0"'), encoding="utf-8")
        self.assertProblem("[task].name is 'node-q/humaneval-plus-0', not the task directory's bare name")

    def test_scripts_must_be_executable(self):
        (self.task_directory / "tests" / "test.sh").chmod(0o644)
        self.assertProblem("tests/test.sh is missing or not executable")

    def test_every_verifier_file_carries_the_canary(self):
        (self.task_directory / "tests" / "problem.json").write_text("{}\n", encoding="utf-8")
        self.assertProblem("tests/problem.json does not carry the canary")

    def test_environment_must_be_the_build_context(self):
        (self.task_directory / "environment" / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
        self.assertProblem("environment/ is not the image's build context")

    def test_the_instruction_must_not_hold_the_solution(self):
        instruction = self.task_directory / "instruction.md"
        instruction.write_text(instruction.read_text(encoding="utf-8") + "\n    return a + b\n", encoding="utf-8")
        self.assertProblem("the instruction contains the reference solution")

    def test_stray_files_are_refused(self):
        (self.task_directory / "notes.txt").write_text("x\n", encoding="utf-8")
        self.assertProblem("holds notes.txt")


if __name__ == "__main__":
    unittest.main()
