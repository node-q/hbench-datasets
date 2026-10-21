import hashlib
import unittest

import images_lock

DATASET = "terminal-bench"
DECLARED_IMAGE = "alexgshaw/{task}:20251031"
TASK_NAMES = ("adaptive-rejection-sampler", "build-pmars", "chess-best-move")


def digest_of(task_name):
    return "sha256:" + hashlib.sha256(task_name.encode("utf-8")).hexdigest()


def mirror_entry(task_name):
    return {
        "source": f"alexgshaw/{task_name}:20251031",
        "source_digest": digest_of(task_name),
        "pinned": f"ghcr.io/node-q/hbench-envs/{DATASET}@{digest_of(task_name)}",
        "mirror_tag": f"{task_name}-20251031",
    }


def upstream_entry(task_name):
    return {
        "source": f"alexgshaw/{task_name}:20251031",
        "source_digest": digest_of(task_name),
        "pinned": f"alexgshaw/{task_name}@{digest_of(task_name)}",
    }


class MirrorTagTest(unittest.TestCase):
    def test_is_the_task_and_the_upstream_tag(self):
        self.assertEqual(
            images_lock.mirror_tag(
                "adaptive-rejection-sampler", "alexgshaw/adaptive-rejection-sampler:20251031"
            ),
            "adaptive-rejection-sampler-20251031",
        )
        self.assertEqual(images_lock.mirror_tag("web", "localhost:5000/team/web:v1.2"), "web-v1.2")

    def test_refuses_a_source_without_a_tag(self):
        for source in ("alexgshaw/task", "localhost:5000/task", f"alexgshaw/task@sha256:{'0' * 64}"):
            with self.subTest(source=source), self.assertRaises(images_lock.LockError):
                images_lock.mirror_tag("task", source)

    def test_refuses_a_tag_longer_than_128_characters_or_with_other_characters(self):
        with self.assertRaisesRegex(images_lock.LockError, "129 characters, more than an OCI tag's 128"):
            images_lock.mirror_tag("t" * 120, "example/task:20251031")
        self.assertEqual(len(images_lock.mirror_tag("t" * 119, "example/task:20251031")), 128)
        with self.assertRaisesRegex(images_lock.LockError, "is not an OCI tag"):
            images_lock.mirror_tag("-task", "example/task:20251031")

    def test_repository_of_drops_the_tag_or_digest_but_keeps_a_registry_port(self):
        self.assertEqual(images_lock.repository_of("alexgshaw/task:20251031"), "alexgshaw/task")
        self.assertEqual(images_lock.repository_of("localhost:5000/task:1"), "localhost:5000/task")
        self.assertEqual(images_lock.repository_of(f"ghcr.io/a/b@sha256:{'0' * 64}"), "ghcr.io/a/b")
        self.assertEqual(images_lock.repository_of("busybox:1.37"), "busybox")


class LockProblemsTest(unittest.TestCase):
    def problems(self, lock, policy, task_count=len(TASK_NAMES)):
        return images_lock.lock_problems(lock, DATASET, policy, task_count, DECLARED_IMAGE)

    def assertProblem(self, lock, policy, fragment, task_count=len(TASK_NAMES)):
        problems = self.problems(lock, policy, task_count)
        self.assertTrue(
            any(fragment in problem for problem in problems), f"no problem mentions {fragment!r}: {problems}"
        )

    def test_a_complete_lock_of_either_policy_passes(self):
        self.assertEqual(
            self.problems({task: mirror_entry(task) for task in TASK_NAMES}, "pinned-mirror"), []
        )
        self.assertEqual(
            self.problems({task: upstream_entry(task) for task in TASK_NAMES}, "pinned-upstream"), []
        )

    def test_the_lock_must_cover_every_task_in_order(self):
        lock = {task: mirror_entry(task) for task in TASK_NAMES}
        self.assertProblem(lock, "pinned-mirror", "locks 3 images for 89 tasks", task_count=89)
        reversed_lock = {task: mirror_entry(task) for task in reversed(TASK_NAMES)}
        self.assertProblem(reversed_lock, "pinned-mirror", "out of order")

    def test_each_policy_has_its_own_keys(self):
        self.assertProblem(
            {task: upstream_entry(task) for task in TASK_NAMES}, "pinned-mirror", "has exactly the strings"
        )
        self.assertProblem(
            {task: mirror_entry(task) for task in TASK_NAMES}, "pinned-upstream", "has exactly the strings"
        )

    def test_the_source_must_be_the_declared_image(self):
        lock = {task: mirror_entry(task) for task in TASK_NAMES}
        lock["build-pmars"]["source"] = "alexgshaw/build-pmars:latest"
        self.assertProblem(lock, "pinned-mirror", "build-pmars: source is 'alexgshaw/build-pmars:latest'")

    def test_the_source_digest_must_be_sha256(self):
        lock = {task: upstream_entry(task) for task in TASK_NAMES}
        lock["build-pmars"]["source_digest"] = "sha256:abc"
        self.assertProblem(lock, "pinned-upstream", "source_digest 'sha256:abc' is not sha256:")

    def test_a_mirror_pin_is_a_digest_reference_in_the_dataset_s_package(self):
        cases = {
            "ghcr.io/node-q/hbench-envs/terminal-bench:build-pmars-20251031": "is not a digest reference under",
            f"ghcr.io/someone-else/terminal-bench@{digest_of('build-pmars')}": "is not a digest reference under",
            f"ghcr.io/node-q/hbench-envs/swebench@{digest_of('build-pmars')}": "is not in ghcr.io/node-q/hbench-envs/",
            f"ghcr.io/node-q/hbench-envs/terminal-bench@sha256:{'f' * 64}": "differs from source_digest",
        }
        for pinned, fragment in cases.items():
            with self.subTest(pinned=pinned):
                lock = {task: mirror_entry(task) for task in TASK_NAMES}
                lock["build-pmars"]["pinned"] = pinned
                self.assertProblem(lock, "pinned-mirror", fragment)

    def test_a_mirror_tag_is_the_task_and_upstream_tag(self):
        lock = {task: mirror_entry(task) for task in TASK_NAMES}
        lock["build-pmars"]["mirror_tag"] = "build-pmars"
        self.assertProblem(
            lock, "pinned-mirror", "mirror_tag is 'build-pmars', expected 'build-pmars-20251031'"
        )

    def test_an_upstream_pin_is_the_source_repository_at_its_digest(self):
        for pinned in (
            f"ghcr.io/node-q/hbench-envs/terminal-bench@{digest_of('build-pmars')}",
            f"alexgshaw/build-pmars@sha256:{'f' * 64}",
            "alexgshaw/build-pmars:20251031",
        ):
            with self.subTest(pinned=pinned):
                lock = {task: upstream_entry(task) for task in TASK_NAMES}
                lock["build-pmars"]["pinned"] = pinned
                self.assertProblem(lock, "pinned-upstream", "expected the source pinned by its digest")


class LockFileTest(unittest.TestCase):
    def test_refuses_duplicate_tasks_and_anything_but_an_object(self):
        with self.assertRaisesRegex(images_lock.LockError, "names 'build-pmars' twice"):
            images_lock.parse_images_lock('{"build-pmars": {}, "build-pmars": {}}')
        with self.assertRaisesRegex(images_lock.LockError, "is not a JSON object"):
            images_lock.parse_images_lock("[]")
        with self.assertRaisesRegex(images_lock.LockError, "is not valid JSON"):
            images_lock.parse_images_lock("{")

    def test_dumps_tasks_sorted_and_keys_in_a_fixed_order(self):
        lock = {task: dict(reversed(list(mirror_entry(task).items()))) for task in reversed(TASK_NAMES)}
        dumped = images_lock.dump_images_lock(lock)
        self.assertEqual(list(images_lock.parse_images_lock(dumped)), sorted(TASK_NAMES))
        self.assertEqual(
            list(images_lock.parse_images_lock(dumped)["build-pmars"]),
            ["source", "source_digest", "pinned", "mirror_tag"],
        )
        self.assertTrue(dumped.endswith("}\n"))
        self.assertEqual(images_lock.dump_images_lock({}), "{}\n")


if __name__ == "__main__":
    unittest.main()
