import pathlib
import shutil
import tempfile
import unittest

import environment_images
from source_descriptor import REPOSITORY_ROOT

DIGEST = "sha256:" + "c" * 64
OTHER_DIGEST = "sha256:" + "d" * 64


class CatalogueTest(unittest.TestCase):
    def setUp(self):
        self.repository_root = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        shutil.copytree(REPOSITORY_ROOT / "images", self.repository_root / "images")
        self.bases = environment_images.load_bases(self.repository_root / "images" / "bases.yaml")
        self.images = environment_images.load_images(self.repository_root / "images" / "images.yaml")
        self.dockerfile = self.repository_root / "images" / "humaneval-plus" / "Dockerfile"

    def image_problems(self):
        return environment_images.image_problems(self.images, self.bases, self.repository_root)

    def test_the_committed_catalogue_is_valid(self):
        self.assertEqual(environment_images.catalogue_problems(), [])
        self.assertEqual(environment_images.catalogue_problems(self.repository_root), [])

    def test_every_built_image_starts_from_a_pinned_ghcr_copy_of_its_base(self):
        self.assertEqual(
            environment_images.pinned_base_of("humaneval-plus-1.0"),
            "ghcr.io/node-q/hbench-envs:base-python-3.12-slim@" + self.bases[0]["digest"],
        )
        for from_line in (
            "FROM python:3.12-slim",
            "FROM ghcr.io/node-q/hbench-envs:base-python-3.12-slim",
            f"FROM ghcr.io/node-q/hbench-envs:base-python-3.12-slim@{DIGEST}",
        ):
            with self.subTest(from_line=from_line):
                self.dockerfile.write_text(f"{from_line}\nWORKDIR /app\n", encoding="utf-8")
                self.assertTrue(any("expected exactly one FROM" in problem for problem in self.image_problems()))

    def test_a_second_stage_is_refused(self):
        original = self.dockerfile.read_text(encoding="utf-8")
        self.dockerfile.write_text(original + "FROM docker.io/library/debian:12 AS second\n", encoding="utf-8")
        self.assertTrue(any("expected exactly one FROM" in problem for problem in self.image_problems()))

    def test_base_tags_follow_their_source(self):
        self.bases[0]["tag"] = "base-python-3.12"
        problems = environment_images.bases_problems(self.bases)
        self.assertIn("bases[0]: tag is 'base-python-3.12', its source makes it 'base-python-3.12-slim'", problems)
        self.assertEqual(environment_images.base_tag_for("docker.io/library/node:22-bookworm"), "base-node-22-bookworm")

    def test_bases_come_from_docker_hub_pinned_by_digest(self):
        self.bases[0]["source"] = "quay.io/library/python:3.12-slim"
        self.bases.append({"tag": "base-node-22", "source": "docker.io/library/node:22", "digest": "latest"})
        problems = environment_images.bases_problems(self.bases)
        self.assertTrue(any("is not docker.io/<repository>:<tag>" in problem for problem in problems))
        self.assertTrue(any("is not sha256:" in problem for problem in problems))

    def test_built_images_are_tagged_dataset_version_with_known_bases_and_platforms(self):
        self.images[0].update({"tag": "base-humaneval-plus-1.0", "base": "base-python-3.13-slim", "platforms": ["linux/s390x"]})
        problems = " | ".join(self.image_problems())
        self.assertIn("tag is not <dataset>-<version>", problems)
        self.assertIn("is not in bases.yaml", problems)
        self.assertIn("platforms must be some of linux/amd64, linux/arm64", problems)

    def test_an_image_without_its_dockerfile_is_refused(self):
        self.dockerfile.unlink()
        self.assertIn("images[0] (humaneval-plus-1.0): images/humaneval-plus/Dockerfile is missing", self.image_problems())


class BuiltLockTest(unittest.TestCase):
    def test_lock_entries_pin_the_tag_to_its_digest_in_the_shared_package(self):
        self.assertEqual(
            environment_images.images_lock_entry("humaneval-plus-1.0", DIGEST),
            {
                "source": "ghcr.io/node-q/hbench-envs:humaneval-plus-1.0",
                "source_digest": DIGEST,
                "pinned": f"ghcr.io/node-q/hbench-envs@{DIGEST}",
            },
        )
        with self.assertRaises(environment_images.EnvironmentImageError):
            environment_images.images_lock_entry("humaneval-plus-1.0", "latest")

    def test_a_built_lock_pins_exactly_the_tasks_to_one_image(self):
        entry = environment_images.images_lock_entry("humaneval-plus-1.0", DIGEST)
        lock = {"a": entry, "b": entry}
        self.assertEqual(environment_images.built_lock_problems(lock, "humaneval-plus-1.0", ["a", "b"]), [])
        self.assertEqual(environment_images.pinned_image(lock), f"ghcr.io/node-q/hbench-envs@{DIGEST}")
        self.assertIsNone(environment_images.pinned_image({}))
        problems = environment_images.built_lock_problems(lock, "humaneval-plus-1.1", ["a", "c"])
        self.assertIn("does not lock exactly the generated tasks: missing ['c'], unexpected ['b']", problems)
        self.assertTrue(any("but the descriptor's image is" in problem for problem in problems))
        lock["b"] = environment_images.images_lock_entry("humaneval-plus-1.0", OTHER_DIGEST)
        self.assertIn(
            "pins several digests of ghcr.io/node-q/hbench-envs:humaneval-plus-1.0, which has one",
            environment_images.built_lock_problems(lock, "humaneval-plus-1.0", ["a", "b"]),
        )
        with self.assertRaises(environment_images.EnvironmentImageError):
            environment_images.pinned_image(lock)


if __name__ == "__main__":
    unittest.main()
