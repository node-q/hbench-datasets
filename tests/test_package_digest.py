import pathlib
import tempfile
import unittest

from adapters.common.package_digest import PackageDigestError, package_digest, package_files

HBENCH_TASKS_DIGEST_OF_SAMPLE_TASK = "sha256:2634b7b75312006a16b0da9b6ce409d10fd4d9ae97b5d8530efb9ea104f5663e"
SAMPLE_TASK_FILES = {
    "task.toml": 'schema_version = "1.4"\n',
    "instruction.md": "Do it.\n",
    "environment/Dockerfile": "FROM scratch\n",
    "tests/test.sh": "#!/bin/bash\n",
    "tests/__pycache__/a.pyc": "x",
    "tests/nested/b.pyc": "y",
    "tests/nested/notes.txt~": "z",
    "tests/nested/.DS_Store": "k",
    "tests/nested/data.json": "data\n",
    "solution/solve.sh": "echo\n",
    "steps/one/instruction.md": "step\n",
    "notes.md": "not packaged\n",
}


class PackageDigestTest(unittest.TestCase):
    def setUp(self):
        self.task_directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory())) / "sample-task"
        for relative_path, text in SAMPLE_TASK_FILES.items():
            path = self.task_directory / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        (self.task_directory / "solution" / "linked-dir").symlink_to("../tests")
        (self.task_directory / "solution" / "linked-file.json").symlink_to("../tests/nested/data.json")

    def test_matches_what_hbench_tasks_digest_prints(self):
        self.assertEqual(package_digest(self.task_directory), HBENCH_TASKS_DIGEST_OF_SAMPLE_TASK)

    def test_packages_the_task_files_without_hbench_default_ignores_or_symlinked_directories(self):
        self.assertEqual(
            package_files(self.task_directory),
            [
                "environment/Dockerfile",
                "instruction.md",
                "solution/linked-file.json",
                "solution/solve.sh",
                "steps/one/instruction.md",
                "task.toml",
                "tests/nested/data.json",
                "tests/test.sh",
            ],
        )

    def test_any_packaged_byte_changes_the_digest_and_other_files_do_not(self):
        (self.task_directory / "notes.md").write_text("changed\n", encoding="utf-8")
        self.assertEqual(package_digest(self.task_directory), HBENCH_TASKS_DIGEST_OF_SAMPLE_TASK)
        (self.task_directory / "tests" / "test.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        self.assertNotEqual(package_digest(self.task_directory), HBENCH_TASKS_DIGEST_OF_SAMPLE_TASK)

    def test_refuses_a_task_with_its_own_gitignore(self):
        (self.task_directory / ".gitignore").write_text("*.json\n", encoding="utf-8")
        with self.assertRaisesRegex(PackageDigestError, "has a .gitignore"):
            package_digest(self.task_directory)


if __name__ == "__main__":
    unittest.main()
