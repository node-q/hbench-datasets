import filecmp
import os
import pathlib
import stat
import subprocess
import tempfile
import unittest

import fetch_source

TASK_NAMES = ("hello-world", "fix-the-build")


def git(repository, *arguments):
    return subprocess.run(
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def write_task(tasks_root, task_name, docker_image):
    task_directory = tasks_root / task_name
    (task_directory / "tests").mkdir(parents=True)
    (task_directory / "task.toml").write_text(
        f'version = "1.0"\n\n[environment]\ndocker_image = "{docker_image}"\n', encoding="utf-8"
    )
    (task_directory / "instruction.md").write_text(f"Solve {task_name}.\n", encoding="utf-8")
    test_script = task_directory / "tests" / "test.sh"
    test_script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    test_script.chmod(0o755)


class FetchTasksTest(unittest.TestCase):
    def setUp(self):
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.upstream = self.workspace / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "--quiet", "--initial-branch=main")
        git(self.upstream, "config", "uploadpack.allowAnySHA1InWant", "true")
        git(self.upstream, "config", "uploadpack.allowFilter", "true")
        tasks_root = self.upstream / "tasks"
        for task_name in TASK_NAMES:
            write_task(tasks_root, task_name, f"example/{task_name}:20251031")
        (tasks_root / "README.md").write_text("Not a task.\n", encoding="utf-8")
        (self.upstream / "LICENSE").write_text("Apache-2.0\n", encoding="utf-8")
        git(self.upstream, "add", ".")
        git(
            self.upstream,
            "-c",
            "user.name=Upstream",
            "-c",
            "user.email=upstream@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            "Add tasks",
        )
        self.commit = git(self.upstream, "rev-parse", "HEAD")
        self.descriptor = {
            "name": "example",
            "version": "1.0",
            "source": {
                "git_url": self.upstream.as_uri(),
                "commit": self.commit,
                "path": "tasks",
                "task_count": len(TASK_NAMES),
            },
            "environment": {"policy": "as-declared", "declared_image": "example/{task}:20251031"},
        }

    def fetch(self):
        return fetch_source.fetch_tasks(self.descriptor, self.workspace / "fetched")

    def test_copies_exactly_the_task_directories_byte_identical(self):
        packed_tasks_directory, task_names = self.fetch()
        self.assertEqual(task_names, sorted(TASK_NAMES))
        self.assertEqual(sorted(os.listdir(packed_tasks_directory)), sorted(TASK_NAMES))
        for task_name in TASK_NAMES:
            comparison = filecmp.dircmp(
                self.upstream / "tasks" / task_name, packed_tasks_directory / task_name
            )
            self.assertEqual(
                (comparison.left_only, comparison.right_only, comparison.diff_files), ([], [], [])
            )
        test_script_mode = (packed_tasks_directory / "hello-world" / "tests" / "test.sh").stat().st_mode
        self.assertTrue(test_script_mode & stat.S_IXUSR)

    def test_fetches_from_the_repository_root(self):
        self.descriptor["source"]["path"] = "."
        self.descriptor["source"]["task_count"] = 1
        with self.assertRaisesRegex(fetch_source.SourceError, "tasks/ has no task.toml"):
            self.fetch()

    def test_refuses_another_number_of_tasks(self):
        self.descriptor["source"]["task_count"] = 3
        with self.assertRaisesRegex(
            fetch_source.SourceError, "found 2 task directories, the descriptor declares 3"
        ):
            self.fetch()

    def test_refuses_tasks_that_declare_another_image(self):
        self.descriptor["environment"]["declared_image"] = "example/{task}:latest"
        with self.assertRaisesRegex(
            fetch_source.SourceError, "hello-world: docker_image is 'example/hello-world:20251031'"
        ):
            self.fetch()

    def test_refuses_an_unknown_commit(self):
        self.descriptor["source"]["commit"] = "0" * 40
        with self.assertRaisesRegex(fetch_source.SourceError, "git fetch"):
            self.fetch()

    def test_refuses_to_pack_pinned_images_until_pinning_is_supported(self):
        self.descriptor["environment"] = {"policy": "pinned-by-digest", "images": {}}
        with self.assertRaisesRegex(fetch_source.SourceError, "is not packed yet"):
            self.fetch()


if __name__ == "__main__":
    unittest.main()
