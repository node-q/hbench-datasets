import contextlib
import hashlib
import io
import json
import pathlib
import shutil
import tempfile
import unittest

from license_expression import get_spdx_licensing

import validate_sources
from source_descriptor import DATASETS_DIR, version_directories

TERMINAL_BENCH_DIRECTORY = DATASETS_DIR / "terminal-bench" / "2.0"
PINNED_MIRROR_DIRECTORY = DATASETS_DIR / "terminal-bench" / "2.0.1"
TASK_COUNT = 89


def task_names():
    return [f"task-{index:02d}" for index in range(TASK_COUNT)]


def digest_of(task_name):
    return "sha256:" + hashlib.sha256(task_name.encode("utf-8")).hexdigest()


def filled_lock(policy):
    lock = {}
    for task_name in task_names():
        entry = {"source": f"alexgshaw/{task_name}:20251031", "source_digest": digest_of(task_name)}
        if policy == "pinned-mirror":
            entry["pinned"] = f"ghcr.io/node-q/hbench-envs/terminal-bench@{digest_of(task_name)}"
            entry["mirror_tag"] = f"{task_name}-20251031"
        else:
            entry["pinned"] = f"alexgshaw/{task_name}@{digest_of(task_name)}"
        lock[task_name] = entry
    return lock


class VersionDirectoryTestCase(unittest.TestCase):
    committed_directory = TERMINAL_BENCH_DIRECTORY

    @classmethod
    def setUpClass(cls):
        cls.validator = validate_sources.schema_validator()
        cls.licensing = get_spdx_licensing()

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.version_directory = (
            pathlib.Path(self.workspace.name) / "datasets" / "terminal-bench" / self.committed_directory.name
        )
        shutil.copytree(self.committed_directory, self.version_directory)
        self.descriptor_path = self.version_directory / "source.yaml"

    def problems(self, for_publish=False):
        return validate_sources.version_directory_problems(
            self.version_directory, self.validator, self.licensing, for_publish
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


class VersionDirectoryTest(VersionDirectoryTestCase):
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


class PinnedVersionDirectoryTest(VersionDirectoryTestCase):
    committed_directory = PINNED_MIRROR_DIRECTORY

    def setUp(self):
        super().setUp()
        self.lock_path = self.version_directory / "images.lock.json"

    def write_lock(self, lock):
        self.lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    def use_upstream_policy(self):
        self.replace_in_descriptor("  policy: pinned-mirror\n", "  policy: pinned-upstream\n")

    def test_terminal_bench_2_0_1_descriptor_is_valid_with_a_patch_version(self):
        self.assertEqual(self.problems(), [])
        self.replace_in_descriptor('version: "2.0.1"', 'version: "2.0"')
        self.assertProblem("does not match its directory '2.0.1'")

    def test_an_unfilled_lock_passes_but_cannot_be_published(self):
        self.assertEqual(self.lock_path.read_text(encoding="utf-8"), "{}\n")
        self.assertEqual(self.problems(), [])
        problems = self.problems(for_publish=True)
        self.assertEqual(len(problems), 1)
        self.assertIn("images.lock.json is not filled yet, so this version cannot be published", problems[0])
        self.assertIn("run the Mirror images workflow", problems[0])
        self.use_upstream_policy()
        self.assertIn("run the Pin images workflow", self.problems(for_publish=True)[0])

    def test_a_filled_lock_of_the_descriptor_s_policy_passes_and_can_be_published(self):
        self.write_lock(filled_lock("pinned-mirror"))
        self.assertEqual(self.problems(for_publish=True), [])
        self.use_upstream_policy()
        self.assertProblem("a pinned-upstream lock has exactly the strings")
        self.write_lock(filled_lock("pinned-upstream"))
        self.assertEqual(self.problems(for_publish=True), [])

    def test_the_lock_must_cover_every_task(self):
        lock = filled_lock("pinned-mirror")
        del lock["task-00"]
        self.write_lock(lock)
        self.assertProblem("images.lock.json: locks 88 images for 89 tasks")

    def test_every_lock_source_must_be_the_declared_image(self):
        lock = filled_lock("pinned-mirror")
        lock["task-00"]["source"] = "alexgshaw/task-00:latest"
        self.write_lock(lock)
        self.assertProblem(
            "task-00: source is 'alexgshaw/task-00:latest', the descriptor declares 'alexgshaw/task-00:20251031'"
        )

    def test_every_mirror_pin_is_a_digest_reference_under_hbench_envs(self):
        lock = filled_lock("pinned-mirror")
        lock["task-07"]["pinned"] = "docker.io/alexgshaw/task-07@" + lock["task-07"]["source_digest"]
        self.write_lock(lock)
        self.assertProblem("task-07: pinned 'docker.io/alexgshaw/task-07@sha256:")
        self.assertProblem("is not a digest reference under ghcr.io/node-q/hbench-envs/")

    def test_the_lock_must_be_valid_json_without_duplicate_tasks(self):
        self.lock_path.write_text('{"task-00": {}, "task-00": {}}\n', encoding="utf-8")
        self.assertProblem("images.lock.json names 'task-00' twice")
        self.lock_path.write_text("{", encoding="utf-8")
        self.assertProblem("images.lock.json is not valid JSON")

    def test_a_locked_policy_needs_its_lock_file_and_names_it(self):
        self.lock_path.unlink()
        self.assertProblem("images.lock.json is missing: a pinned-mirror version keeps its image lock")
        shutil.copy(PINNED_MIRROR_DIRECTORY / "images.lock.json", self.lock_path)
        self.replace_in_descriptor("  images_lock: images.lock.json\n", "")
        self.assertProblem("'images_lock' is a required property")
        shutil.copy(PINNED_MIRROR_DIRECTORY / "source.yaml", self.descriptor_path)
        self.replace_in_descriptor("  images_lock: images.lock.json\n", "  images_lock: other.lock.json\n")
        self.assertProblem("'images.lock.json' was expected")

    def test_a_lock_belongs_only_to_a_locked_policy(self):
        self.replace_in_descriptor("  policy: pinned-mirror\n", "  policy: as-declared\n")
        self.assertProblem("environment: ")
        self.replace_in_descriptor("  images_lock: images.lock.json\n", "")
        self.assertProblem(
            "images.lock.json belongs only to a version whose environment policy is pinned-mirror"
        )


class RepositoryTest(unittest.TestCase):
    def main(self, arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = validate_sources.main(arguments)
        return exit_code, output.getvalue()

    def test_every_committed_dataset_version_is_valid(self):
        exit_code, output = self.main([])
        self.assertEqual(exit_code, 0, output)
        self.assertIn("ok  datasets/terminal-bench/2.0\n", output)
        self.assertIn("ok  datasets/terminal-bench/2.0.1\n", output)
        self.assertIn("ok  datasets/humaneval-plus/1.0\n", output)
        unfilled_locks = sorted(
            f"datasets/{directory.parent.name}/{directory.name}/images.lock.json"
            for directory in version_directories()
            if (directory / "images.lock.json").is_file()
            and json.loads((directory / "images.lock.json").read_text(encoding="utf-8")) == {}
        )
        warnings = sorted(line for line in output.splitlines() if "is not filled yet" in line)
        self.assertEqual(len(warnings), len(unfilled_locks), output)
        for unfilled_lock, warning in zip(unfilled_locks, warnings):
            self.assertIn(unfilled_lock, warning)

    def test_publishing_refuses_terminal_bench_2_0_1_until_its_images_are_mirrored(self):
        exit_code, output = self.main(["--for-publish", str(PINNED_MIRROR_DIRECTORY)])
        self.assertEqual(exit_code, 1, output)
        self.assertIn("images.lock.json is not filled yet, so this version cannot be published", output)
        exit_code, output = self.main(["--for-publish", str(TERMINAL_BENCH_DIRECTORY)])
        self.assertEqual(exit_code, 0, output)

    def test_refuses_a_directory_outside_datasets(self):
        exit_code, output = self.main([str(DATASETS_DIR.parent / "schema")])
        self.assertEqual(exit_code, 1)
        self.assertIn("is not a datasets/<name>/<version> directory", output)


if __name__ == "__main__":
    unittest.main()
