import contextlib
import io
import unittest

import release_notes
from source_descriptor import DATASETS_DIR, load_descriptor

TERMINAL_BENCH_SOURCE = DATASETS_DIR / "terminal-bench" / "2.0" / "source.yaml"
REPOSITORY = "ghcr.io/node-q/hbench-datasets/terminal-bench"
DIGEST = "sha256:" + "0123456789abcdef" * 4
HBENCH_VERSION = "v0.3.0"
RUN_URL = "https://github.com/node-q/hbench-datasets/actions/runs/1"


class ReleaseNotesTest(unittest.TestCase):
    def setUp(self):
        self.descriptor = load_descriptor(TERMINAL_BENCH_SOURCE)

    def notes(self):
        return release_notes.release_notes(self.descriptor, REPOSITORY, DIGEST, HBENCH_VERSION, RUN_URL)

    def test_tag_and_title_name_the_dataset_version(self):
        self.assertEqual(release_notes.release_tag(self.descriptor), "terminal-bench-2.0")
        self.assertEqual(
            release_notes.release_title(self.descriptor), "Terminal-Bench 2.0 (terminal-bench@2.0)"
        )

    def test_notes_carry_the_reference_digest_and_licence(self):
        notes = self.notes()
        self.assertIn(f"`{REPOSITORY}:2.0`", notes)
        self.assertIn(f"`{DIGEST}`", notes)
        self.assertIn("Apache-2.0", notes)
        self.assertIn("- Tasks: 89", notes)

    def test_notes_show_how_to_run_and_verify_by_digest(self):
        notes = self.notes()
        self.assertIn("hbench run -d terminal-bench@2.0 --registry oci://ghcr.io/node-q/hbench-datasets", notes)
        self.assertIn(f"cosign verify {REPOSITORY}@{DIGEST}", notes)
        self.assertIn(f"gh attestation verify oci://{REPOSITORY}@{DIGEST}", notes)

    def test_notes_keep_the_citation_and_attribution(self):
        notes = self.notes()
        self.assertIn("```bibtex", notes)
        self.assertIn("@misc{tbench_2025", notes)
        self.assertIn("## Attribution", notes)

    def test_command_line_prints_the_requested_field(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            release_notes.main(
                [
                    "--source",
                    str(TERMINAL_BENCH_SOURCE),
                    "--repository",
                    REPOSITORY,
                    "--digest",
                    DIGEST,
                    "--hbench-version",
                    HBENCH_VERSION,
                    "--run-url",
                    RUN_URL,
                    "--field",
                    "tag",
                ]
            )
        self.assertEqual(output.getvalue(), "terminal-bench-2.0\n")


if __name__ == "__main__":
    unittest.main()
