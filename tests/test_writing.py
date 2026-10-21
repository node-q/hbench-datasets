import tomllib
import unittest

from adapters.common.writing import TaskWritingError, task_toml


class TaskTomlTest(unittest.TestCase):
    def test_names_the_task_by_its_bare_directory_name(self):
        manifest = tomllib.loads(
            task_toml("example-0", "An example.", {"metadata": {"category": "python"}, "agent": {"timeout_sec": 60.0}})
        )
        self.assertEqual(manifest["schema_version"], "1.4")
        self.assertEqual(manifest["task"], {"name": "example-0", "description": "An example."})
        self.assertEqual(manifest["metadata"], {"category": "python"})

    def test_refuses_an_org_name_or_a_task_table_of_its_own(self):
        with self.assertRaisesRegex(TaskWritingError, "is not a bare task directory name"):
            task_toml("node-q/example-0", "An example.", {})
        with self.assertRaisesRegex(TaskWritingError, r"\[task\] is written from"):
            task_toml("example-0", "An example.", {"task": {"name": "other"}})

    def test_leaves_out_settings_that_are_none(self):
        manifest = tomllib.loads(task_toml("example-0", "An example.", {"environment": {"docker_image": None, "cpus": 1}}))
        self.assertEqual(manifest["environment"], {"cpus": 1})


if __name__ == "__main__":
    unittest.main()
