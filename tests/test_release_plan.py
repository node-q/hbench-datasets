import pathlib
import shutil
import tempfile
import unittest

from license_expression import get_spdx_licensing

import release_plan
import validate_sources
from source_descriptor import DATASETS_DIR


class ParseSetsTest(unittest.TestCase):
    def test_spaces_and_commas_separate_sets_in_order(self):
        self.assertEqual(
            release_plan.parse_sets(["federal-register@1.0, computer-use-browser@1.0", "aca-fl@1.0.1"]),
            [("federal-register", "1.0"), ("computer-use-browser", "1.0"), ("aca-fl", "1.0.1")],
        )

    def test_refuses_malformed_names(self):
        for token in ["federal-register", "Federal@1.0", "a@1", "a@01.0", "../a@1.0", "a@1.0;echo", "a@1.0@2.0"]:
            with self.subTest(token=token), self.assertRaises(release_plan.PlanError):
                release_plan.parse_sets([token])

    def test_refuses_no_sets_and_duplicates(self):
        with self.assertRaises(release_plan.PlanError):
            release_plan.parse_sets([" , "])
        with self.assertRaisesRegex(release_plan.PlanError, "named twice"):
            release_plan.parse_sets(["a@1.0 a@1.0"])

    def test_refuses_too_many_sets(self):
        with self.assertRaisesRegex(release_plan.PlanError, "at most"):
            release_plan.parse_sets([" ".join(f"a{index}@1.0" for index in range(release_plan.MAX_SETS + 1))])


class SourceReleasesTest(unittest.TestCase):
    def descriptor(self, *urls, sha256="a" * 64):
        return {"source": {"upstream_files": [{"name": "x", "url": url, "sha256": sha256} for url in urls]}}

    def test_lists_only_this_repository_releases(self):
        releases = release_plan.source_releases(
            self.descriptor(
                "https://github.com/node-q/hbench-datasets/releases/download/sources-a-1.0/tasks.tar.xz",
                "https://example.org/upstream.parquet",
            )
        )
        self.assertEqual([release["tag"] for release in releases], ["sources-a-1.0"])
        self.assertEqual(releases[0]["assets"][0]["name"], "tasks.tar.xz")
        self.assertEqual(releases[0]["assets"][0]["sha256"], "a" * 64)

    def test_refuses_a_release_url_without_a_pinned_sha256(self):
        with self.assertRaisesRegex(release_plan.PlanError, "no sha256"):
            release_plan.source_releases(
                self.descriptor(
                    "https://github.com/node-q/hbench-datasets/releases/download/sources-a-1.0/tasks.tar.xz",
                    sha256="",
                )
            )

    def test_refuses_an_odd_release_path(self):
        with self.assertRaises(release_plan.PlanError):
            release_plan.source_releases(
                self.descriptor("https://github.com/node-q/hbench-datasets/releases/download/sources-a-1.0/x/y")
            )


class PlanSetTest(unittest.TestCase):
    committed_directory = DATASETS_DIR / "federal-register" / "1.0"

    @classmethod
    def setUpClass(cls):
        cls.validator = validate_sources.schema_validator()
        cls.licensing = get_spdx_licensing()

    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.datasets_directory = pathlib.Path(workspace.name) / "datasets"
        self.version_directory = self.datasets_directory / "federal-register" / "1.0"
        shutil.copytree(self.committed_directory, self.version_directory)

    def plan(self, dataset="federal-register", version="1.0"):
        return release_plan.plan_set(dataset, version, self.validator, self.licensing, self.datasets_directory)

    def test_a_committed_set_is_ready_with_its_source_release(self):
        entry = self.plan()
        self.assertEqual(entry["problems"], [])
        self.assertEqual([release["tag"] for release in entry["releases"]], ["sources-federal-register-1.0"])

    def test_a_missing_descriptor_says_to_merge_first(self):
        entry = self.plan(version="9.9")
        self.assertEqual(len(entry["problems"]), 1)
        self.assertIn("merge its pull request first", entry["problems"][0])

    def test_an_empty_lock_names_the_build_images_run(self):
        (self.version_directory / "images.lock.json").write_text("{}\n", encoding="utf-8")
        entry = self.plan()
        self.assertEqual(len(entry["problems"]), 1, entry["problems"])
        self.assertIn("Run Build images (image=taskfolders-1.0)", entry["problems"][0])
        self.assertIn("pull request", entry["problems"][0])


if __name__ == "__main__":
    unittest.main()
