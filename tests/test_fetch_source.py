import contextlib
import filecmp
import io
import json
import os
import pathlib
import stat
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock

import yaml

import fetch_source
import validate_sources

TASK_NAMES = ("hello-world", "fix-the-build")
SOURCE = "alexgshaw/adaptive-rejection-sampler:20251031"
DIGEST = "sha256:" + "0123456789abcdef" * 4
MIRROR_PIN = f"ghcr.io/node-q/hbench-envs/terminal-bench@{DIGEST}"
UPSTREAM_PIN = f"alexgshaw/adaptive-rejection-sampler@{DIGEST}"
UPSTREAM_TASK_MANIFEST = (
    'version = "1.0"\n'
    "\n"
    "[metadata]\n"
    'author_name = "Example Author"\n'
    'difficulty = "medium"\n'
    'tags = [ "applied-statistics", "simulation",]\n'
    "\n"
    "[verifier]\n"
    "timeout_sec = 900.0\n"
    "\n"
    "[environment]\n"
    "build_timeout_sec = 600.0\n"
    f'docker_image = "{SOURCE}"\n'
    "cpus = 1\n"
    'memory = "2G"\n'
)


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


class UpstreamRepositoryTestCase(unittest.TestCase):
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


class FetchTasksTest(UpstreamRepositoryTestCase):
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

    def test_refuses_to_pack_a_descriptor_that_pins_images_itself(self):
        self.descriptor["environment"] = {"policy": "pinned-by-digest", "images": {}}
        with self.assertRaisesRegex(fetch_source.SourceError, "is not packed yet"):
            self.fetch()


def lock_entry(task_name, policy):
    source = f"example/{task_name}:20251031"
    if policy == "pinned-mirror":
        return {
            "source": source,
            "source_digest": DIGEST,
            "pinned": f"ghcr.io/node-q/hbench-envs/example@{DIGEST}",
            "mirror_tag": f"{task_name}-20251031",
        }
    return {"source": source, "source_digest": DIGEST, "pinned": f"example/{task_name}@{DIGEST}"}


class PinnedTaskManifestTest(unittest.TestCase):
    def test_changes_only_the_docker_image_value(self):
        original = UPSTREAM_TASK_MANIFEST.encode("utf-8")
        for pinned in (MIRROR_PIN, UPSTREAM_PIN):
            with self.subTest(pinned=pinned):
                rewritten = fetch_source.pinned_task_manifest(original, SOURCE, pinned)
                start = original.index(SOURCE.encode("utf-8"))
                self.assertEqual(rewritten[:start], original[:start])
                self.assertEqual(rewritten[start : start + len(pinned)], pinned.encode("utf-8"))
                self.assertEqual(rewritten[start + len(pinned) :], original[start + len(SOURCE) :])
                self.assertEqual(rewritten, original.replace(f'"{SOURCE}"'.encode(), f'"{pinned}"'.encode()))
                self.assertEqual(tomllib.loads(rewritten.decode())["environment"]["docker_image"], pinned)

    def test_keeps_crlf_line_endings_spacing_and_comments(self):
        original = (
            b'version = "1.0"\r\n[environment]\r\n  docker_image   =  "'
            + SOURCE.encode()
            + b'"  # upstream\r\n'
            b"cpus = 1\r\n"
        )
        rewritten = fetch_source.pinned_task_manifest(original, SOURCE, MIRROR_PIN)
        self.assertEqual(
            rewritten,
            b'version = "1.0"\r\n[environment]\r\n  docker_image   =  "'
            + MIRROR_PIN.encode()
            + b'"  # upstream\r\n'
            b"cpus = 1\r\n",
        )

    def test_refuses_a_task_whose_image_is_not_the_lock_s_source(self):
        original = UPSTREAM_TASK_MANIFEST.replace(
            SOURCE, "alexgshaw/adaptive-rejection-sampler:latest"
        ).encode()
        with self.assertRaisesRegex(fetch_source.SourceError, "but images.lock.json pins 'alexgshaw/"):
            fetch_source.pinned_task_manifest(original, SOURCE, MIRROR_PIN)

    def test_refuses_a_docker_image_it_cannot_change_on_one_line_alone(self):
        for original in (
            UPSTREAM_TASK_MANIFEST.replace(f'"{SOURCE}"', f"'{SOURCE}'"),
            UPSTREAM_TASK_MANIFEST.replace("[verifier]\n", f'[verifier]\ndocker_image = "{SOURCE}"\n'),
            f'version = "1.0"\nenvironment = {{ docker_image = "{SOURCE}" }}\n',
        ):
            with (
                self.subTest(original=original),
                self.assertRaisesRegex(fetch_source.SourceError, "on exactly one line"),
            ):
                fetch_source.pinned_task_manifest(original.encode(), SOURCE, MIRROR_PIN)


class PinnedFetchTest(UpstreamRepositoryTestCase):
    def lock(self, policy):
        return {task_name: lock_entry(task_name, policy) for task_name in sorted(TASK_NAMES)}

    def use_policy(self, policy):
        self.descriptor["environment"] = {
            "policy": policy,
            "declared_image": "example/{task}:20251031",
            "images_lock": "images.lock.json",
        }

    def test_pins_only_the_docker_image_line_of_each_task(self):
        for policy in ("pinned-mirror", "pinned-upstream"):
            with self.subTest(policy=policy):
                self.use_policy(policy)
                images_lock = self.lock(policy)
                destination = self.workspace / policy
                packed_tasks_directory, _ = fetch_source.fetch_tasks(
                    self.descriptor, destination, images_lock
                )
                for task_name in TASK_NAMES:
                    upstream_task = self.upstream / "tasks" / task_name
                    packed_task = packed_tasks_directory / task_name
                    comparison = filecmp.dircmp(upstream_task, packed_task)
                    self.assertEqual((comparison.left_only, comparison.right_only), ([], []))
                    self.assertEqual(comparison.diff_files, ["task.toml"])
                    upstream_lines = (upstream_task / "task.toml").read_bytes().splitlines(keepends=True)
                    packed_lines = (packed_task / "task.toml").read_bytes().splitlines(keepends=True)
                    changed = [pair for pair in zip(upstream_lines, packed_lines) if pair[0] != pair[1]]
                    self.assertEqual(len(upstream_lines), len(packed_lines))
                    self.assertEqual(
                        changed,
                        [
                            (
                                f'docker_image = "example/{task_name}:20251031"\n'.encode(),
                                f'docker_image = "{images_lock[task_name]["pinned"]}"\n'.encode(),
                            )
                        ],
                    )

    def test_refuses_a_lock_that_misses_a_task_or_names_another(self):
        self.use_policy("pinned-mirror")
        images_lock = self.lock("pinned-mirror")
        images_lock["not-a-task"] = images_lock.pop("hello-world")
        with self.assertRaisesRegex(
            fetch_source.SourceError, r"missing \['hello-world'\], unexpected \['not-a-task'\]"
        ):
            fetch_source.fetch_tasks(self.descriptor, self.workspace / "fetched", images_lock)

    def test_refuses_a_lock_whose_source_is_not_the_task_s_image(self):
        self.use_policy("pinned-upstream")
        self.descriptor["environment"].pop("declared_image")
        images_lock = self.lock("pinned-upstream")
        images_lock["hello-world"]["source"] = "example/hello-world:latest"
        with self.assertRaisesRegex(
            fetch_source.SourceError, "hello-world: docker_image is 'example/hello-world:20251031', but"
        ):
            fetch_source.fetch_tasks(self.descriptor, self.workspace / "fetched", images_lock)

    def test_refuses_an_unfilled_lock_unless_allowed(self):
        self.use_policy("pinned-mirror")
        with self.assertRaisesRegex(
            fetch_source.SourceError, "is not filled yet, .* run the Mirror images workflow"
        ):
            fetch_source.fetch_tasks(self.descriptor, self.workspace / "refused", {})
        packed_tasks_directory, _ = fetch_source.fetch_tasks(
            self.descriptor, self.workspace / "allowed", {}, allow_unfilled_lock=True
        )
        comparison = filecmp.dircmp(
            self.upstream / "tasks" / "hello-world", packed_tasks_directory / "hello-world"
        )
        self.assertEqual(comparison.diff_files, [])

    def test_the_packed_descriptor_pins_the_lock_s_images_and_matches_the_schema(self):
        for policy in ("pinned-mirror", "pinned-upstream"):
            with self.subTest(policy=policy):
                self.use_policy(policy)
                images_lock = self.lock(policy)
                packed = fetch_source.packed_descriptor(self.descriptor, images_lock)
                self.assertEqual(
                    packed["environment"],
                    {
                        "policy": "pinned-by-digest",
                        "images": {task: entry["pinned"] for task, entry in images_lock.items()},
                    },
                )
                self.assertEqual(self.descriptor["environment"]["policy"], policy)

    def test_main_writes_the_descriptor_to_pack_with(self):
        repository_descriptor = validate_sources.load_descriptor(
            validate_sources.DATASETS_DIR / "terminal-bench" / "2.0.1" / "source.yaml"
        )
        repository_descriptor["source"] = self.descriptor["source"]
        repository_descriptor["environment"]["declared_image"] = "example/{task}:20251031"
        repository_descriptor["name"] = "example"
        version_directory = self.workspace / "datasets" / "example" / "1.0"
        version_directory.mkdir(parents=True)
        descriptor_path = version_directory / "source.yaml"
        descriptor_path.write_text(yaml.safe_dump(repository_descriptor, sort_keys=False), encoding="utf-8")
        (version_directory / "images.lock.json").write_text(
            json.dumps(self.lock("pinned-mirror")), encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = fetch_source.main([str(descriptor_path), str(self.workspace / "fetched")])
        self.assertEqual(exit_code, 0)
        packed = yaml.safe_load((self.workspace / "fetched" / "source.yaml").read_text(encoding="utf-8"))
        self.assertEqual(packed["environment"]["policy"], "pinned-by-digest")
        self.assertEqual(
            {key: packed[key] for key in packed if key != "environment"},
            {key: repository_descriptor[key] for key in repository_descriptor if key != "environment"},
        )
        packed["source"]["git_url"] = "https://example.com/upstream.git"
        self.assertEqual(validate_sources.schema_problems(packed, validate_sources.schema_validator()), [])


class GeneratedFetchTest(unittest.TestCase):
    def setUp(self):
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.descriptor_path = validate_sources.DATASETS_DIR / "humaneval-plus" / "1.0" / "source.yaml"

    def run_main(self, *arguments):
        output = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            exit_code = fetch_source.main([*arguments, str(self.descriptor_path), str(self.workspace / "fetched")])
        return exit_code, output.getvalue() + errors.getvalue()

    def test_a_generated_source_is_generated_rather_than_fetched(self):
        tasks_directory = self.workspace / "fetched" / "tasks"
        prepared = (tasks_directory, ["humaneval-plus-0"], None)
        with mock.patch.object(fetch_source.generated_source, "prepare_for_packing", return_value=prepared) as prepare:
            exit_code, output = self.run_main("--allow-unfilled-lock")
        self.assertEqual(exit_code, 0, output)
        prepare.assert_called_once_with(self.descriptor_path, self.workspace / "fetched", allow_unfilled_lock=True)
        self.assertIn("1 tasks generated by adapters/humaneval_plus", output)
        self.assertIn("nothing is ready to pack", output)

    def test_a_generation_error_fails_the_fetch(self):
        error = fetch_source.generated_source.GeneratedSourceError("images.lock.json is not filled yet")
        with mock.patch.object(fetch_source.generated_source, "prepare_for_packing", side_effect=error):
            exit_code, output = self.run_main()
        self.assertEqual(exit_code, 1)
        self.assertIn("humaneval-plus@1.0: images.lock.json is not filled yet", output)


if __name__ == "__main__":
    unittest.main()
