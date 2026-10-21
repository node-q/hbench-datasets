import json
import pathlib
import tempfile
import tomllib
import unittest
from unittest import mock

import yaml

import generated_source
from environment_images import images_lock_entry
from humaneval_plus_fixture import CANARY, write_upstream
from images_lock import dump_images_lock

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


if __name__ == "__main__":
    unittest.main()
