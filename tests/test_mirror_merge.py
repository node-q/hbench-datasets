import contextlib
import hashlib
import io
import json
import pathlib
import tempfile
import unittest

import images_lock
import mirror_merge
import mirror_plan

TASK_NAMES = [f"task-{index:02d}" for index in range(23)]


def digest_of(task_name):
    return "sha256:" + hashlib.sha256(task_name.encode("utf-8")).hexdigest()


def plan():
    declared_images = {task_name: f"alexgshaw/{task_name}:20251031" for task_name in TASK_NAMES}
    return mirror_plan.mirror_plan({"name": "terminal-bench", "version": "2.0"}, declared_images, 10)


def shard_lock(shard):
    return {
        image["task"]: {
            "source": image["source"],
            "source_digest": digest_of(image["task"]),
            "pinned": f"ghcr.io/node-q/hbench-envs/terminal-bench@{digest_of(image['task'])}",
            "mirror_tag": image["mirror_tag"],
        }
        for image in shard["images"]
    }


class MergedLockTest(unittest.TestCase):
    def setUp(self):
        self.plan = plan()
        self.shard_locks = [(f"shard-{shard['shard']}", shard_lock(shard)) for shard in self.plan["shards"]]

    def test_merges_every_shard_into_one_sorted_lock(self):
        lock = mirror_merge.merged_lock(self.plan, list(reversed(self.shard_locks)))
        self.assertEqual(list(lock), TASK_NAMES)
        self.assertEqual(
            images_lock.lock_problems(lock, "terminal-bench", "pinned-mirror", len(TASK_NAMES)), []
        )

    def test_refuses_a_missing_shard(self):
        with self.assertRaisesRegex(
            images_lock.LockError,
            "no shard locked task-08, task-09, .*, task-15: re-run the shards that failed",
        ):
            mirror_merge.merged_lock(self.plan, [self.shard_locks[0], self.shard_locks[2]])

    def test_refuses_a_task_locked_twice(self):
        duplicate = ("shard-copy", {"task-00": self.shard_locks[0][1]["task-00"]})
        with self.assertRaisesRegex(images_lock.LockError, "task-00: locked by more than one shard"):
            mirror_merge.merged_lock(self.plan, [*self.shard_locks, duplicate])

    def test_refuses_an_entry_the_plan_does_not_hold(self):
        self.shard_locks[0][1]["task-00"]["mirror_tag"] = "task-00-latest"
        self.shard_locks[1][1]["not-planned"] = self.shard_locks[1][1].pop("task-10")
        with self.assertRaises(images_lock.LockError) as raised:
            mirror_merge.merged_lock(self.plan, self.shard_locks)
        message = str(raised.exception)
        self.assertIn("task-00: mirror_tag is 'task-00-latest', expected 'task-00-20251031'", message)
        self.assertIn("not-planned: is not in the plan", message)
        self.assertIn("no shard locked task-10", message)

    def test_refuses_a_mirror_whose_digest_is_not_the_source_s(self):
        self.shard_locks[2][1]["task-20"]["pinned"] = (
            f"ghcr.io/node-q/hbench-envs/terminal-bench@sha256:{'0' * 64}"
        )
        with self.assertRaisesRegex(
            images_lock.LockError, "task-20: the mirror's digest .* differs from source_digest"
        ):
            mirror_merge.merged_lock(self.plan, self.shard_locks)

    def test_command_line_writes_images_lock_json(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory)
            plan_path = workspace / "mirror-plan.json"
            plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
            shard_paths = []
            for name, lock in self.shard_locks:
                shard_path = workspace / f"images-lock-{name}.json"
                shard_path.write_text(images_lock.dump_images_lock(lock), encoding="utf-8")
                shard_paths.append(str(shard_path))
            output = workspace / "images.lock.json"
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = mirror_merge.main(
                    ["--plan", str(plan_path), "--output", str(output), *shard_paths]
                )
            self.assertEqual(exit_code, 0)
            written = output.read_text(encoding="utf-8")
        self.assertEqual(
            written, images_lock.dump_images_lock(mirror_merge.merged_lock(self.plan, self.shard_locks))
        )
        self.assertEqual(list(json.loads(written)), TASK_NAMES)


if __name__ == "__main__":
    unittest.main()
