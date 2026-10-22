import hashlib
import json
import pathlib
import tempfile
import tomllib
import unittest
from unittest import mock

import yaml

import environment_images
import generated_source
from environment_images import images_lock_entry
from humaneval_plus_fixture import CANARY, write_upstream
from images_lock import dump_images_lock
import several_images_fixture

IMAGE_TAG = "humaneval-plus-1.0"
DIGEST = "sha256:" + "b" * 64
TASK_NAMES = ["humaneval-plus-0", "humaneval-plus-2", "humaneval-plus-32"]


class GeneratedSourceTestCase(unittest.TestCase):
    def setUp(self):
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        upstream_path = self.workspace / "upstream" / "HumanEvalPlus.jsonl.gz"
        upstream_path.parent.mkdir()
        self.upstream_sha256 = write_upstream(upstream_path)
        self.version_directory = self.workspace / "datasets" / "humaneval-plus" / "1.0"
        self.version_directory.mkdir(parents=True)
        self.descriptor = {
            "schema_version": 1,
            "name": "humaneval-plus",
            "version": "1.0",
            "title": "HumanEval+ test",
            "description": "A test.",
            "license": "Apache-2.0",
            "upstream": {"url": "https://example.com", "revision": "v0", "creator": "Test", "citation": "Test"},
            "canary": CANARY,
            "source": {
                "kind": "generated",
                "adapter": "adapters/humaneval_plus",
                "upstream_files": [
                    {"name": "HumanEvalPlus.jsonl.gz", "url": upstream_path.as_uri(), "sha256": self.upstream_sha256}
                ],
                "task_count": len(TASK_NAMES),
            },
            "environment": {"policy": "built", "image": IMAGE_TAG, "images_lock": "images.lock.json"},
            "attribution": ["Test."],
        }
        self.write_descriptor()
        self.write_images_lock({})

    def write_descriptor(self):
        (self.version_directory / "source.yaml").write_text(yaml.safe_dump(self.descriptor, sort_keys=False), encoding="utf-8")

    def write_images_lock(self, lock):
        (self.version_directory / "images.lock.json").write_text(dump_images_lock(lock), encoding="utf-8")

    def fill_images_lock(self):
        self.write_images_lock({name: images_lock_entry(IMAGE_TAG, DIGEST) for name in TASK_NAMES})

    def prepare(self, destination_name="generated", **options):
        return generated_source.prepare_for_packing(
            self.version_directory / "source.yaml", self.workspace / destination_name, **options
        )

    def generated_lock(self):
        return json.loads((self.version_directory / "generated.lock.json").read_text(encoding="utf-8"))


class GenerationTest(GeneratedSourceTestCase):
    def test_writes_the_lock_and_then_matches_it(self):
        tasks_directory, task_names, packed_path = self.prepare(allow_unfilled_lock=True, write_lock=True)
        self.assertEqual(task_names, TASK_NAMES)
        self.assertIsNone(packed_path)
        self.assertEqual(sorted(self.generated_lock()), TASK_NAMES)
        self.prepare("again", allow_unfilled_lock=True)
        self.assertEqual(
            (tasks_directory / "humaneval-plus-0" / "environment" / "Dockerfile").read_bytes(),
            (generated_source.REPOSITORY_ROOT / "images" / "humaneval-plus" / "Dockerfile").read_bytes(),
        )

    def test_refuses_tasks_that_differ_from_the_lock(self):
        self.prepare(allow_unfilled_lock=True, write_lock=True)
        lock = self.generated_lock()
        lock["humaneval-plus-2"] = "sha256:" + "0" * 64
        (self.version_directory / "generated.lock.json").write_text(json.dumps(lock), encoding="utf-8")
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "1 tasks differ from generated.lock.json:\n  humaneval-plus-2"):
            self.prepare("again", allow_unfilled_lock=True)

    def test_refuses_an_unfilled_image_lock_unless_allowed(self):
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "run the Build images workflow"):
            self.prepare()

    def test_refuses_an_upstream_file_with_another_digest(self):
        self.descriptor["source"]["upstream_files"][0]["sha256"] = "0" * 64
        self.write_descriptor()
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "but the descriptor pins 0000"):
            self.prepare(allow_unfilled_lock=True)

    def test_refuses_upstream_files_the_adapter_does_not_read(self):
        self.descriptor["source"]["upstream_files"][0]["name"] = "Other.jsonl.gz"
        self.write_descriptor()
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "the adapter reads"):
            self.prepare(allow_unfilled_lock=True)

    def test_refuses_another_number_of_tasks(self):
        self.descriptor["source"]["task_count"] = 4
        self.write_descriptor()
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "wrote 3 tasks, the descriptor declares 4"):
            self.prepare(allow_unfilled_lock=True)

    def test_reuses_an_upstream_cache(self):
        cache = self.workspace / "cache"
        self.prepare(allow_unfilled_lock=True, write_lock=True, upstream_cache=cache)
        self.assertTrue((cache / self.upstream_sha256).is_file())
        (self.workspace / "upstream" / "HumanEvalPlus.jsonl.gz").unlink()
        self.prepare("again", allow_unfilled_lock=True, upstream_cache=cache)


class FilledImageLockTest(GeneratedSourceTestCase):
    def setUp(self):
        super().setUp()
        self.prepare("unfilled", allow_unfilled_lock=True, write_lock=True)
        self.fill_images_lock()
        self.prepare("filled", write_lock=True)

    def test_every_task_names_the_pinned_image(self):
        tasks_directory, _, _ = self.prepare()
        for name in TASK_NAMES:
            manifest = tomllib.loads((tasks_directory / name / "task.toml").read_text(encoding="utf-8"))
            self.assertEqual(manifest["environment"]["docker_image"], f"ghcr.io/node-q/hbench-envs@{DIGEST}")

    def test_writes_the_descriptor_hbench_packs_with(self):
        _, _, packed_path = self.prepare()
        packed = yaml.safe_load(packed_path.read_text(encoding="utf-8"))
        self.assertEqual(
            packed["source"],
            {
                "git_url": "https://github.com/node-q/hbench-datasets.git",
                "commit": generated_source.repository_commit(),
                "path": "adapters/humaneval_plus",
                "task_count": 3,
            },
        )
        self.assertEqual(
            packed["environment"],
            {"policy": "pinned-by-digest", "images": {name: f"ghcr.io/node-q/hbench-envs@{DIGEST}" for name in TASK_NAMES}},
        )
        self.assertEqual(packed["canary"], CANARY)
        self.assertEqual(list(packed)[:3], ["schema_version", "name", "version"])

    def test_refuses_an_image_lock_that_misses_a_task(self):
        lock = {name: images_lock_entry(IMAGE_TAG, DIGEST) for name in TASK_NAMES[:2]}
        self.write_images_lock(lock)
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "missing \\['humaneval-plus-32'\\]"):
            self.prepare("short", write_lock=True)

    def test_lock_image_fills_both_locks(self):
        self.write_images_lock({})
        self.prepare("reset", allow_unfilled_lock=True, write_lock=True)
        unfilled_lock = self.generated_lock()
        with mock.patch.object(generated_source, "versions_built_on", return_value=[self.version_directory]):
            generated_source.lock_image(IMAGE_TAG, DIGEST)
        images_lock = json.loads((self.version_directory / "images.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(images_lock, {name: images_lock_entry(IMAGE_TAG, DIGEST) for name in TASK_NAMES})
        self.assertEqual(sorted(self.generated_lock()), TASK_NAMES)
        self.assertNotEqual(self.generated_lock(), unfilled_lock)



class SeveralImagesTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(several_images_fixture.registered_adapter())
        self.workspace = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.upstream_path = self.workspace / "upstream-files" / several_images_fixture.UPSTREAM_FILE_NAME
        self.upstream_path.parent.mkdir()
        self.version_directory = self.workspace / "datasets" / "exercism-polyglot" / "1.0"
        self.version_directory.mkdir(parents=True)
        self.write_upstream()
        self.write_images_lock({})

    def write_upstream(self, **options):
        several_images_fixture.write_upstream(self.upstream_path, **options)
        descriptor = {
            "schema_version": 1,
            "name": "exercism-polyglot",
            "version": "1.0",
            "title": "Several images test",
            "description": "A test.",
            "license": "Apache-2.0",
            "upstream": {"url": "https://example.com", "revision": "v0", "creator": "Test", "citation": "Test"},
            "canary": several_images_fixture.CANARY,
            "source": {
                "kind": "generated",
                "adapter": several_images_fixture.ADAPTER,
                "upstream_files": [
                    {
                        "name": several_images_fixture.UPSTREAM_FILE_NAME,
                        "url": self.upstream_path.as_uri(),
                        "sha256": hashlib.sha256(self.upstream_path.read_bytes()).hexdigest(),
                    }
                ],
                "task_count": len(json.loads(self.upstream_path.read_text(encoding="utf-8"))["tasks"]),
            },
            "environment": {"policy": "built", "task_images": several_images_fixture.TASK_IMAGES, "images_lock": "images.lock.json"},
            "attribution": ["Test."],
        }
        (self.version_directory / "source.yaml").write_text(yaml.safe_dump(descriptor, sort_keys=False), encoding="utf-8")

    def write_images_lock(self, lock):
        (self.version_directory / "images.lock.json").write_text(dump_images_lock(lock), encoding="utf-8")

    def images_lock(self):
        return json.loads((self.version_directory / "images.lock.json").read_text(encoding="utf-8"))

    def prepare(self, destination_name="generated", **options):
        return generated_source.prepare_for_packing(
            self.version_directory / "source.yaml", self.workspace / destination_name, **options
        )

    def docker_images(self, tasks_directory):
        return {
            name: tomllib.loads((tasks_directory / name / "task.toml").read_text(encoding="utf-8"))["environment"]["docker_image"]
            for name in several_images_fixture.TASK_NAMES
        }

    def lock(self, tag, digest):
        with mock.patch.object(generated_source, "versions_built_on", return_value=[self.version_directory]):
            generated_source.lock_image(tag, digest)

    def test_before_any_image_is_built_each_task_names_its_image_by_tag(self):
        tasks_directory, task_names, packed_path = self.prepare(allow_unfilled_lock=True, write_lock=True)
        self.assertEqual(task_names, several_images_fixture.TASK_NAMES)
        self.assertIsNone(packed_path)
        self.assertEqual(
            self.docker_images(tasks_directory),
            {
                "exercism-go-bowling": "ghcr.io/node-q/hbench-envs:exercism-polyglot-go-1.0",
                "exercism-go-react": "ghcr.io/node-q/hbench-envs:exercism-polyglot-go-1.0",
                "exercism-python-bowling": "ghcr.io/node-q/hbench-envs:exercism-polyglot-python-1.0",
            },
        )
        self.assertEqual(
            sorted(path.name for path in (tasks_directory / "exercism-go-bowling" / "environment").iterdir()),
            ["solution.txt"],
        )

    def test_the_adapter_s_environment_must_not_be_a_build_context(self):
        self.write_upstream(extra_environment={"Dockerfile": "FROM scratch\n"})
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "environment/Dockerfile would make hbench build"):
            self.prepare(allow_unfilled_lock=True, write_lock=True)

    def test_every_task_must_match_one_image(self):
        self.write_upstream(tasks=[*several_images_fixture.TASK_NAMES, "exercism-rust-bowling"])
        self.prepare(allow_unfilled_lock=True, write_lock=True)
        with self.assertRaisesRegex(environment_images.EnvironmentImageError, "exercism-rust-bowling matches 0"):
            self.lock("exercism-polyglot-go-1.0", DIGEST)

    def test_lock_image_pins_one_image_s_tasks_and_keeps_the_others(self):
        self.prepare(allow_unfilled_lock=True, write_lock=True)
        self.lock("exercism-polyglot-go-1.0", DIGEST)
        self.assertEqual(sorted(self.images_lock()), ["exercism-go-bowling", "exercism-go-react"])
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "does not pin the tasks on exercism-polyglot-python-1.0 yet"):
            self.prepare("refused")
        tasks_directory, _, packed_path = self.prepare("partly", allow_unfilled_lock=True)
        self.assertIsNone(packed_path)
        self.assertEqual(self.docker_images(tasks_directory)["exercism-go-react"], f"ghcr.io/node-q/hbench-envs@{DIGEST}")
        self.assertEqual(
            self.docker_images(tasks_directory)["exercism-python-bowling"],
            "ghcr.io/node-q/hbench-envs:exercism-polyglot-python-1.0",
        )
        other_digest = "sha256:" + "c" * 64
        self.lock("exercism-polyglot-python-1.0", other_digest)
        tasks_directory, _, packed_path = self.prepare("filled")
        expected = {
            "exercism-go-bowling": f"ghcr.io/node-q/hbench-envs@{DIGEST}",
            "exercism-go-react": f"ghcr.io/node-q/hbench-envs@{DIGEST}",
            "exercism-python-bowling": f"ghcr.io/node-q/hbench-envs@{other_digest}",
        }
        self.assertEqual(self.docker_images(tasks_directory), expected)
        packed = yaml.safe_load(packed_path.read_text(encoding="utf-8"))
        self.assertEqual(packed["environment"], {"policy": "pinned-by-digest", "images": expected})

    def test_a_lock_that_splits_an_image_s_tasks_is_refused(self):
        self.prepare(allow_unfilled_lock=True, write_lock=True)
        self.write_images_lock({"exercism-go-bowling": images_lock_entry("exercism-polyglot-go-1.0", DIGEST)})
        with self.assertRaisesRegex(generated_source.GeneratedSourceError, "locks 1 of the 2 tasks on exercism-polyglot-go-1.0"):
            self.prepare("split", allow_unfilled_lock=True, write_lock=True)


if __name__ == "__main__":
    unittest.main()
