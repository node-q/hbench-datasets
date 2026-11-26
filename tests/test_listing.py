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

    def test_the_group_is_one_of_the_six_and_required(self):
        """hbench-studio#390: the Market Place and Essentials file a set under its listing's own group."""
        self.assertEqual("coding", json.loads(listing.build_listing(SWEBENCH_LITE))["group"])
        for text, expected in (("group: coding\n", "'group' is a required property"),
                               ("group: coding\n", "is not one of")):
            target = self.copy()
            written = (target / "listing.yaml").read_text(encoding="utf-8")
            self.assertIn(text, written)
            changed = written.replace(text, "" if "required" in expected else "group: other\n")
            (target / "listing.yaml").write_text(changed, encoding="utf-8")
            with self.subTest(expected=expected), self.assertRaisesRegex(Exception, expected):
                listing.build_listing(target)

    def test_a_stale_listing_json_fails_the_check(self):
        target = self.copy()
        (target / "listing.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            listing.main(["--check", str(target)])


if __name__ == "__main__":
    unittest.main()


FLSA_OVERTIME = DATASETS_DIR / "flsa-overtime" / "1.0.1"


class TaskFacts(unittest.TestCase):
    """A version whose tasks.json records each task (adapters/taskfolders): its kinds of work, graded fields,
    difficulty and draft status come from the dataset."""

    def copy(self):
        scratch = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scratch)
        target = scratch / "flsa-overtime" / "1.0.1"
        shutil.copytree(FLSA_OVERTIME, target)
        return target

    def test_counts_come_from_tasks_json(self):
        built = json.loads(listing.build_listing(FLSA_OVERTIME))
        facts = json.loads((FLSA_OVERTIME / "tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(facts), sum(family["tasks"] for family in built["families"]))
        self.assertEqual(sum(task["fields"] for task in facts.values()), built["graded_fields"])
        self.assertEqual(len(facts), sum(built["difficulty"].values()))
        self.assertEqual(("draft", "payroll specialists", "field-graded"), (built["status"], built["trade"], built["format"]))
        self.assertEqual("CC-BY-4.0", built["licence"]["id"])

    def test_tasks_json_must_describe_the_lock_and_the_families(self):
        target = self.copy()
        facts = json.loads((target / "tasks.json").read_text(encoding="utf-8"))
        first = sorted(facts)[0]
        (target / "tasks.json").write_text(json.dumps({**facts, first: {**facts[first], "kind": "other"}}), encoding="utf-8")
        with self.assertRaisesRegex(listing.ListingError, "kinds"):
            listing.build_listing(target)
        facts.pop(first)
        (target / "tasks.json").write_text(json.dumps(facts), encoding="utf-8")
        with self.assertRaisesRegex(listing.ListingError, "lock"):
            listing.build_listing(target)
        (target / "tasks.json").unlink()
        with self.assertRaisesRegex(listing.ListingError, "several kinds"):
            listing.build_listing(target)
