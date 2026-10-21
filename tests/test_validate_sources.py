import contextlib
import io
import pathlib
import shutil
import tempfile
import unittest

from license_expression import get_spdx_licensing

import validate_sources
from source_descriptor import DATASETS_DIR

TERMINAL_BENCH_DIRECTORY = DATASETS_DIR / "terminal-bench" / "2.0"


class VersionDirectoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = validate_sources.schema_validator()
        cls.licensing = get_spdx_licensing()

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.version_directory = pathlib.Path(self.workspace.name) / "datasets" / "terminal-bench" / "2.0"
        shutil.copytree(TERMINAL_BENCH_DIRECTORY, self.version_directory)
        self.descriptor_path = self.version_directory / "source.yaml"

    def problems(self):
        return validate_sources.version_directory_problems(
            self.version_directory, self.validator, self.licensing
        )

    def replace_in_descriptor(self, old, new):
        text = self.descriptor_path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        self.descriptor_path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assertProblem(self, fragment):
        problems = self.problems()
        self.assertTrue(
            any(fragment in problem for problem in problems), f"no problem mentions {fragment!r}: {problems}"
        )

    def test_terminal_bench_descriptor_is_valid(self):
        self.assertEqual(self.problems(), [])

    def test_name_must_match_its_directory(self):
        self.replace_in_descriptor("name: terminal-bench", "name: terminal-bench-two")
        self.assertProblem("does not match its directory 'terminal-bench'")

    def test_version_must_match_its_directory(self):
        self.replace_in_descriptor('version: "2.0"', 'version: "2.0.1"')
        self.assertProblem("does not match its directory '2.0'")

    def test_version_must_be_a_string(self):
        self.replace_in_descriptor('version: "2.0"', "version: 2.0")
        self.assertProblem("version: 2.0 is not of type 'string'")

    def test_licence_and_notice_files_are_required(self):
        (self.version_directory / "NOTICE").unlink()
        (self.version_directory / "LICENSE").write_text("\n", encoding="utf-8")
        self.assertProblem("NOTICE is missing")
        self.assertProblem("LICENSE is empty")

    def test_task_files_are_never_committed(self):
        (self.version_directory / "some-task").mkdir()
        self.assertProblem("some-task does not belong here")

    def test_license_must_be_a_current_spdx_identifier(self):
        for license_id, fragment in (
            ("Apache-2", "is not an SPDX license identifier"),
            ("apache-2.0", "SPDX spells it 'Apache-2.0'"),
            ("GPL-2.0", "SPDX spells it 'GPL-2.0-only'"),
        ):
            with self.subTest(license_id=license_id):
                shutil.copy(TERMINAL_BENCH_DIRECTORY / "source.yaml", self.descriptor_path)
                self.replace_in_descriptor("license: Apache-2.0", f"license: {license_id}")
                self.assertProblem(fragment)

    def test_commit_must_be_a_full_sha(self):
        self.replace_in_descriptor("commit: 69671fbaac6d67a7ef0dfec016cc38a64ef7a77c", "commit: 69671fba")
        self.assertProblem("source/commit: '69671fba' does not match")

    def test_duplicate_keys_are_refused(self):
        self.replace_in_descriptor("license: Apache-2.0", "license: Apache-2.0\nlicense: MIT")
        self.assertProblem("found duplicate key 'license'")

    def test_unknown_keys_are_refused(self):
        self.replace_in_descriptor("license: Apache-2.0", "license: Apache-2.0\nlicence: Apache-2.0")
        self.assertProblem("Additional properties are not allowed ('licence' was unexpected)")

    def test_pinned_images_must_cover_every_task(self):
        self.replace_in_descriptor(
            "  policy: as-declared\n",
            f"  policy: pinned-by-digest\n  images:\n    some-task: docker.io/example/some-task@sha256:{'0' * 64}\n",
        )
        self.assertProblem("environment.images pins 1 images for 89 tasks")

    def test_pinned_policy_requires_images_and_declared_policy_forbids_them(self):
        self.replace_in_descriptor("  policy: as-declared\n", "  policy: pinned-by-digest\n")
        self.assertProblem("'images' is a required property")
        shutil.copy(TERMINAL_BENCH_DIRECTORY / "source.yaml", self.descriptor_path)
        self.replace_in_descriptor(
            "  policy: as-declared\n",
            f"  policy: as-declared\n  images:\n    some-task: docker.io/example/some-task@sha256:{'0' * 64}\n",
        )
        self.assertProblem("environment: ")


class RepositoryTest(unittest.TestCase):
    def main(self, arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = validate_sources.main(arguments)
        return exit_code, output.getvalue()

    def test_every_committed_dataset_version_is_valid(self):
        exit_code, output = self.main([])
        self.assertEqual(exit_code, 0, output)
        self.assertIn("ok  datasets/terminal-bench/2.0", output)

    def test_refuses_a_directory_outside_datasets(self):
        exit_code, output = self.main([str(DATASETS_DIR.parent / "schema")])
        self.assertEqual(exit_code, 1)
        self.assertIn("is not a datasets/<name>/<version> directory", output)


if __name__ == "__main__":
    unittest.main()
