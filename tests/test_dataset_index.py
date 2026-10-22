import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

import dataset_index
from source_descriptor import DATASETS_DIR

NAMESPACE = "ghcr.io/node-q/hbench-datasets"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIRECTORIES = [
    DATASETS_DIR / "terminal-bench" / "2.0.1",
    DATASETS_DIR / "humaneval-plus" / "1.0",
    DATASETS_DIR / "terminal-bench" / "2.0",
    DATASETS_DIR / "bigcodebench" / "1.0",
]


def resolver(served):
    return lambda reference: served.get(reference)


class PublishedVersionsTest(unittest.TestCase):
    def test_served_versions_are_listed_sorted_and_the_rest_left_out(self):
        served = {
            f"{NAMESPACE}/terminal-bench:2.0.1": DIGEST_B,
            f"{NAMESPACE}/terminal-bench:2.0": DIGEST_A,
            f"{NAMESPACE}/humaneval-plus:1.0": DIGEST_C,
        }
        entries, left_out = dataset_index.published_versions(NAMESPACE, resolver(served), DIRECTORIES)
        self.assertEqual(
            entries,
            [
                {"name": "humaneval-plus", "version": "1.0", "digest": DIGEST_C},
                {"name": "terminal-bench", "version": "2.0", "digest": DIGEST_A},
                {"name": "terminal-bench", "version": "2.0.1", "digest": DIGEST_B},
            ],
        )
        self.assertEqual(left_out, ["bigcodebench@1.0"])

    def test_versions_sort_by_number_not_text(self):
        self.assertLess(dataset_index.version_key("2.0.9"), dataset_index.version_key("2.0.10"))


class BuildIndexTest(unittest.TestCase):
    def test_the_index_matches_hbench_s_schema(self):
        index = dataset_index.build_index([{"name": "terminal-bench", "version": "2.0", "digest": DIGEST_A}])
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(json.loads(dataset_index.dump_index(index)), index)

    def test_a_bad_entry_or_a_version_twice_is_refused(self):
        with self.assertRaisesRegex(dataset_index.DatasetIndexError, "digest"):
            dataset_index.build_index([{"name": "terminal-bench", "version": "2.0", "digest": "sha256:12"}])
        with self.assertRaisesRegex(dataset_index.DatasetIndexError, "twice"):
            entry = {"name": "terminal-bench", "version": "2.0", "digest": DIGEST_A}
            dataset_index.build_index([entry, dict(entry)])

    def test_the_schema_is_hbench_s(self):
        schema = json.loads(dataset_index.INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "https://github.com/node-q/hbench/blob/master/assets/schemas/dataset-index.v1.json")


class ResolveTest(unittest.TestCase):
    def completed(self, returncode, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_oras_resolve_reads_the_digest_or_none_when_the_registry_does_not_serve_it(self):
        with mock.patch.object(dataset_index.subprocess, "run", return_value=self.completed(0, DIGEST_A + "\n")) as run:
            self.assertEqual(dataset_index.oras_resolve(f"{NAMESPACE}/terminal-bench:2.0"), DIGEST_A)
        self.assertNotEqual(run.call_args.kwargs["env"].get("DOCKER_CONFIG"), None)
        for stderr in ("Error: ... not found", "Error response from registry: unauthorized: authentication required", "denied"):
            with mock.patch.object(dataset_index.subprocess, "run", return_value=self.completed(1, stderr=stderr)):
                self.assertIsNone(dataset_index.oras_resolve(f"{NAMESPACE}/x:1.0"))

    def test_any_other_failure_stops_the_build(self):
        with mock.patch.object(dataset_index.subprocess, "run", return_value=self.completed(1, stderr="dial tcp: i/o timeout")):
            with self.assertRaisesRegex(dataset_index.DatasetIndexError, "i/o timeout"):
                dataset_index.oras_resolve(f"{NAMESPACE}/x:1.0")


class MainTest(unittest.TestCase):
    def test_writes_the_index_and_names_what_it_left_out(self):
        served = {f"{NAMESPACE}/terminal-bench:2.0": DIGEST_A}
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory, "index.json")
            printed = io.StringIO()
            with (
                mock.patch.object(dataset_index, "oras_resolve", resolver(served)),
                mock.patch.object(dataset_index, "version_directories", lambda: DIRECTORIES),
                contextlib.redirect_stdout(printed),
            ):
                self.assertEqual(dataset_index.main(["--namespace", NAMESPACE + "/", "--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["datasets"], [{"name": "terminal-bench", "version": "2.0", "digest": DIGEST_A}])
        self.assertIn("left out terminal-bench@2.0.1", printed.getvalue())
        self.assertIn("indexed 1 dataset versions", printed.getvalue())


if __name__ == "__main__":
    unittest.main()
