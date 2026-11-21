import json
import pathlib
import shutil
import tempfile
import unittest

import listing
from source_descriptor import DATASETS_DIR

SWEBENCH_LITE = DATASETS_DIR / "swebench-lite" / "1.0"


class Listing(unittest.TestCase):
    def test_every_listing_json_is_fresh(self):
        self.assertTrue(listing.listed_versions())
        for directory in listing.listed_versions():
            with self.subTest(directory=directory.relative_to(DATASETS_DIR)):
                self.assertEqual(listing.build_listing(directory), (directory / "listing.json").read_text("utf-8"))

    def test_counts_come_from_the_dataset(self):
        built = json.loads(listing.build_listing(SWEBENCH_LITE))
        self.assertEqual(270, built["tasks"])
        self.assertEqual(270, sum(line["tasks"] for line in built["lines"]))
        self.assertEqual({"name": "django/django", "tasks": 114}, built["lines"][0])
        self.assertEqual("Apache-2.0", built["licence"]["id"])
        self.assertEqual("free", built["pricing"])

    def copy(self):
        scratch = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scratch)
        target = scratch / "swebench-lite" / "1.0"
        shutil.copytree(SWEBENCH_LITE, target)
        return target

    def test_banned_words_and_a_wrong_count_are_refused(self):
        for text, expected in (("An agent fixes it.", "'agent'"), ("It has 12 test tasks.", "says 12 test tasks"),
                               ("Wow!", "exclamation"), ("From hbench.", "'hbench'")):
            target = self.copy()
            (target / "COVER.md").write_text(f"## What this is\n\n{text}\n", encoding="utf-8")
            with self.subTest(text=text), self.assertRaisesRegex(listing.ListingError, expected):
                listing.build_listing(target)

    def test_a_stale_listing_json_fails_the_check(self):
        target = self.copy()
        (target / "listing.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            listing.main(["--check", str(target)])


if __name__ == "__main__":
    unittest.main()
