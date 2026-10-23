import os
import pathlib
import subprocess
import tempfile
import unittest

from adapters.swebench import verification

OPENED_AT = "2022-01-13T18:51:58Z"


def commit(repository, message, date):
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_COMMITTER_DATE": date,
    }
    subprocess.run(
        ["git", "-C", str(repository), "commit", "--quiet", "--allow-empty", "-m", message],
        check=True,
        env=environment,
    )


def probe(repository, pull_request_number, opened_at):
    completed = subprocess.run(
        ["bash", "-c", verification.HISTORY_PROBE, "probe", str(repository), pull_request_number, opened_at],
        check=True,
        capture_output=True,
        text=True,
    )
    return dict(zip(verification.HISTORY_FIELDS, (int(value) for value in completed.stdout.split())))


class HistoryProbeTest(unittest.TestCase):
    def setUp(self):
        self.repository = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        subprocess.run(["git", "-C", str(self.repository), "init", "--quiet", "--initial-branch=main"], check=True)
        commit(self.repository, "Fixed #15315 -- Added the widget argument to modelform_factory.", "2011-08-23T04:08:24Z")

    def test_a_ticket_older_than_the_pull_request_does_not_name_it(self):
        counts = probe(self.repository, "15315", OPENED_AT)
        self.assertEqual(counts["naming_pull_request"], 0)
        self.assertEqual(verification.history_problems(counts), [])

    def test_a_message_since_the_pull_request_was_opened_names_it(self):
        commit(self.repository, "Fixed #33412 -- Fixed the widget's attrs (#15315).", "2022-01-20T09:00:00Z")
        self.assertEqual(probe(self.repository, "15315", OPENED_AT)["naming_pull_request"], 1)

    def test_without_an_opening_date_every_message_counts(self):
        self.assertEqual(probe(self.repository, "15315", "")["naming_pull_request"], 1)


if __name__ == "__main__":
    unittest.main()
