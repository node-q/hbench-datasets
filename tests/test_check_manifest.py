import copy
import unittest

import check_manifest
from source_descriptor import DATASETS_DIR, load_descriptor

TERMINAL_BENCH_SOURCE = DATASETS_DIR / "terminal-bench" / "2.0" / "source.yaml"
PINNED_MIRROR_SOURCE = DATASETS_DIR / "terminal-bench" / "2.0.1" / "source.yaml"
TASK_NAMES = ["adaptive-rejection-sampler", "build-pmars"]


def layer(task_name, digest_character):
    return {
        "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        "digest": f"sha256:{digest_character * 64}",
        "size": 1024,
        "annotations": {
            "org.opencontainers.image.title": task_name,
            "dev.hbench.task.package-digest": f"sha256:{digest_character * 64}",
        },
    }


MATCHING_MANIFEST = {
    "schemaVersion": 2,
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "artifactType": "application/vnd.hbench.dataset.v1",
    "config": {
        "mediaType": "application/vnd.hbench.dataset.config.v1+json",
        "digest": f"sha256:{'c' * 64}",
        "size": 512,
    },
    "layers": [layer(TASK_NAMES[0], "a"), layer(TASK_NAMES[1], "b")],
    "annotations": {
        "org.opencontainers.image.version": "2.0",
        "org.opencontainers.image.licenses": "Apache-2.0",
    },
}


class ManifestCheckTest(unittest.TestCase):
    def setUp(self):
        self.descriptor = load_descriptor(TERMINAL_BENCH_SOURCE)
        self.manifest = copy.deepcopy(MATCHING_MANIFEST)

    def problems(self, task_names=TASK_NAMES):
        return check_manifest.manifest_problems(self.manifest, self.descriptor, task_names)

    def assertProblem(self, fragment, task_names=TASK_NAMES):
        problems = self.problems(task_names)
        self.assertTrue(
            any(fragment in problem for problem in problems), f"no problem mentions {fragment!r}: {problems}"
        )

    def test_a_matching_manifest_passes(self):
        self.assertEqual(self.problems(), [])

    def test_artifact_and_config_types_must_be_hbench_datasets(self):
        self.manifest["artifactType"] = "application/vnd.oci.image.config.v1+json"
        self.manifest["config"]["mediaType"] = "application/vnd.oci.image.config.v1+json"
        self.assertProblem("artifactType is")
        self.assertProblem("config mediaType is")

    def test_every_task_needs_exactly_one_layer(self):
        self.assertProblem("2 layers for 3 tasks", task_names=[*TASK_NAMES, "chess-best-move"])
        self.assertProblem("missing ['chess-best-move']", task_names=[*TASK_NAMES, "chess-best-move"])
        self.manifest["layers"][1]["annotations"]["org.opencontainers.image.title"] = "build-pmars-2"
        self.assertProblem("unexpected ['build-pmars-2']")

    def test_layers_must_be_tar_gzip(self):
        self.manifest["layers"][0]["mediaType"] = "application/vnd.oci.image.layer.v1.tar+zstd"
        self.assertProblem("layers other than application/vnd.oci.image.layer.v1.tar+gzip")

    def test_licence_and_version_annotations_must_match_the_descriptor(self):
        self.manifest["annotations"]["org.opencontainers.image.licenses"] = "MIT"
        del self.manifest["annotations"]["org.opencontainers.image.version"]
        self.assertProblem("org.opencontainers.image.licenses is 'MIT'")
        self.assertProblem("org.opencontainers.image.version is None")

    def test_a_patch_version_matches_its_own_version_annotation(self):
        self.descriptor = load_descriptor(PINNED_MIRROR_SOURCE)
        self.assertProblem("org.opencontainers.image.version is '2.0', expected '2.0.1'")
        self.manifest["annotations"]["org.opencontainers.image.version"] = "2.0.1"
        self.assertEqual(self.problems(), [])


if __name__ == "__main__":
    unittest.main()
