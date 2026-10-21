import unittest

import mirror_plan

TERMINAL_BENCH_TASK_COUNT = 89


def declared_images(count):
    return {f"task-{index:02d}": f"alexgshaw/task-{index:02d}:20251031" for index in range(count)}


class ShardPlanTest(unittest.TestCase):
    def test_splits_terminal_bench_into_nine_shards_of_about_ten(self):
        images = mirror_plan.planned_images(declared_images(TERMINAL_BENCH_TASK_COUNT))
        shards = mirror_plan.shards(images, 10)
        self.assertEqual([shard["shard"] for shard in shards], list(range(1, 10)))
        self.assertEqual([len(shard["images"]) for shard in shards], [10, 10, 10, 10, 10, 10, 10, 10, 9])
        self.assertEqual([image for shard in shards for image in shard["images"]], images)

    def test_shard_sizes_differ_by_at_most_one(self):
        for image_count, images_per_shard in ((1, 10), (10, 10), (11, 10), (21, 10), (89, 7), (5, 1)):
            with self.subTest(image_count=image_count, images_per_shard=images_per_shard):
                images = mirror_plan.planned_images(declared_images(image_count))
                sizes = [len(shard["images"]) for shard in mirror_plan.shards(images, images_per_shard)]
                self.assertEqual(sum(sizes), image_count)
                self.assertLessEqual(max(sizes), images_per_shard)
                self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_refuses_no_images_or_empty_shards(self):
        with self.assertRaisesRegex(mirror_plan.PlanError, "no images"):
            mirror_plan.shards([], 10)
        with self.assertRaisesRegex(mirror_plan.PlanError, "at least 1"):
            mirror_plan.shards(mirror_plan.planned_images(declared_images(3)), 0)

    def test_each_image_gets_its_task_and_upstream_tag_as_its_mirror_tag(self):
        (image,) = mirror_plan.planned_images({"build-pmars": "alexgshaw/build-pmars:20251031"})
        self.assertEqual(
            image,
            {
                "task": "build-pmars",
                "source": "alexgshaw/build-pmars:20251031",
                "mirror_tag": "build-pmars-20251031",
            },
        )

    def test_refuses_images_it_cannot_tag(self):
        with self.assertRaisesRegex(mirror_plan.PlanError, "is 129 characters, more than an OCI tag's 128"):
            mirror_plan.planned_images({"t" * 120: "example/task:20251031"})
        with self.assertRaisesRegex(mirror_plan.PlanError, "untagged: 'alexgshaw/untagged' names no tag"):
            mirror_plan.planned_images({"untagged": "alexgshaw/untagged", "tagged": "alexgshaw/tagged:1"})

    def test_the_plan_names_the_dataset_s_mirror_repository(self):
        descriptor = {"name": "terminal-bench", "version": "2.0"}
        plan = mirror_plan.mirror_plan(descriptor, declared_images(TERMINAL_BENCH_TASK_COUNT), 10)
        self.assertEqual(plan["mirror_repository"], "ghcr.io/node-q/hbench-envs/terminal-bench")
        self.assertEqual((plan["dataset"], plan["version"]), ("terminal-bench", "2.0"))
        self.assertEqual(len(plan["shards"]), 9)


if __name__ == "__main__":
    unittest.main()
