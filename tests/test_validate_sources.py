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
GENERATED_DIRECTORY = DATASETS_DIR / "humaneval-plus" / "1.0"
BUILT_DIGEST = "sha256:" + "e" * 64
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
            pathlib.Path(self.workspace.name)
            / "datasets"
            / self.committed_directory.parent.name
            / self.committed_directory.name
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
        self.write_lock({})
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


class GeneratedVersionDirectoryTest(VersionDirectoryTestCase):
    committed_directory = GENERATED_DIRECTORY

    def generated_lock(self):
        return json.loads((self.version_directory / "generated.lock.json").read_text(encoding="utf-8"))

    def write_json(self, filename, document):
        (self.version_directory / filename).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def fill_images_lock(self, tag="humaneval-plus-1.0", digest=BUILT_DIGEST, task_names=None):
        entry = {
            "source": f"ghcr.io/node-q/hbench-envs:{tag}",
            "source_digest": digest,
            "pinned": f"ghcr.io/node-q/hbench-envs@{digest}",
        }
        self.write_json("images.lock.json", {name: entry for name in task_names or sorted(self.generated_lock())})

    def test_humaneval_plus_is_valid_but_cannot_be_published_before_its_image_is_built(self):
        self.assertEqual(self.problems(), [])
        problems = self.problems(for_publish=True)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("run the Build images workflow and commit the images.lock.json and generated.lock.json", problems[0])

    def test_a_filled_images_lock_can_be_published(self):
        self.fill_images_lock()
        self.assertEqual(self.problems(for_publish=True), [])

    def test_a_filled_images_lock_must_pin_every_generated_task_to_the_descriptor_image(self):
        self.fill_images_lock(task_names=sorted(self.generated_lock())[:-1])
        self.assertProblem("locks 163 images for 164 tasks")
        self.fill_images_lock(tag="humaneval-plus-1.1")
        self.assertProblem("but the descriptor's image is ghcr.io/node-q/hbench-envs:humaneval-plus-1.0")

    def test_generated_lock_must_hold_every_task_digest(self):
        lock = self.generated_lock()
        lock.pop("humaneval-plus-99")
        self.write_json("generated.lock.json", lock)
        self.assertProblem("generated.lock.json locks 163 tasks, the descriptor declares 164")
        (self.version_directory / "generated.lock.json").unlink()
        self.assertProblem("write it with scripts/generated_source.py generate --write-lock")

    def test_generated_lock_digests_are_sha256(self):
        lock = self.generated_lock()
        lock["humaneval-plus-0"] = "md5:0"
        self.write_json("generated.lock.json", lock)
        self.assertProblem("humaneval-plus-0: 'md5:0' is not sha256:<64 lowercase hex digits>")

    def test_the_adapter_and_the_image_must_exist(self):
        self.replace_in_descriptor("adapter: adapters/humaneval_plus", "adapter: adapters/humaneval_minus")
        self.assertProblem("adapter adapters/humaneval_minus has no adapter.py")
        shutil.copy(GENERATED_DIRECTORY / "source.yaml", self.descriptor_path)
        self.replace_in_descriptor("image: humaneval-plus-1.0", "image: humaneval-plus-9.0")
        self.assertProblem("'humaneval-plus-9.0' is not in images/images.yaml")

    def test_upstream_files_are_pinned_by_sha256_over_https(self):
        self.replace_in_descriptor("sha256: 272720b9", "sha256: 272720B9")
        self.assertProblem("source/upstream_files/0/sha256: '272720B9")
        shutil.copy(GENERATED_DIRECTORY / "source.yaml", self.descriptor_path)
        self.replace_in_descriptor("url: https://github.com/evalplus/humanevalplus_release/releases", "url: http://github.com/evalplus/humanevalplus_release/releases")
        self.assertProblem("source/upstream_files/0/url: 'http://github.com/evalplus")

    def test_a_generated_source_needs_the_built_policy_and_a_canary(self):
        self.replace_in_descriptor("  policy: built\n  image: humaneval-plus-1.0\n  images_lock: images.lock.json\n", "  policy: as-declared\n")
        self.assertProblem("environment/policy: 'as-declared' is not one of ['built', 'built-locally']")
        shutil.copy(GENERATED_DIRECTORY / "source.yaml", self.descriptor_path)
        text = self.descriptor_path.read_text(encoding="utf-8")
        canary_start = text.index("canary: >-")
        canary_end = text.index("\nsource:") + 1
        self.descriptor_path.write_text(text[:canary_start] + text[canary_end:], encoding="utf-8")
        self.assertProblem("'canary' is a required property")

    def test_the_built_policy_needs_a_generated_source(self):
        self.replace_in_descriptor(
            "  kind: generated\n  adapter: adapters/humaneval_plus\n",
            "  git_url: https://github.com/evalplus/humanevalplus_release.git\n  commit: " + "a" * 40 + "\n  path: .\n",
        )
        self.assertProblem("source")

    def test_generated_lock_belongs_only_to_a_generated_version(self):
        terminal_bench = pathlib.Path(self.workspace.name) / "datasets" / "terminal-bench" / "2.0"
        shutil.copytree(TERMINAL_BENCH_DIRECTORY, terminal_bench)
        shutil.copy(self.version_directory / "generated.lock.json", terminal_bench)
        problems = validate_sources.version_directory_problems(terminal_bench, self.validator, self.licensing)
        self.assertIn("generated.lock.json belongs only to a version whose source kind is generated", problems)


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

    def test_both_committed_terminal_bench_versions_can_be_published(self):
        for directory in (TERMINAL_BENCH_DIRECTORY, PINNED_MIRROR_DIRECTORY):
            exit_code, output = self.main(["--for-publish", str(directory)])
            self.assertEqual(exit_code, 0, output)

    def test_refuses_a_directory_outside_datasets(self):
        exit_code, output = self.main([str(DATASETS_DIR.parent / "schema")])
        self.assertEqual(exit_code, 1)
        self.assertIn("is not a datasets/<name>/<version> directory", output)


if __name__ == "__main__":
    unittest.main()
