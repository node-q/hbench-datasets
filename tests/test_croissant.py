import contextlib
import copy
import io
import json
import pathlib
import tempfile
import unittest

import croissant
from source_descriptor import DATASETS_DIR, load_descriptor

TERMINAL_BENCH_SOURCE = DATASETS_DIR / "terminal-bench" / "2.0" / "source.yaml"
PINNED_MIRROR_SOURCE = DATASETS_DIR / "terminal-bench" / "2.0.1" / "source.yaml"
GENERATED_SOURCE = DATASETS_DIR / "humaneval-plus" / "1.0" / "source.yaml"
REPOSITORY = "ghcr.io/node-q/hbench-datasets/terminal-bench"
DIGEST_HEX = "0123456789abcdef" * 4
DIGEST = f"sha256:{DIGEST_HEX}"
DATE_PUBLISHED = "2026-10-22"
RUN_URL = "https://github.com/node-q/hbench-datasets/actions/runs/1"
CROISSANT_REQUIRED_PROPERTIES = (
    "@context",
    "@type",
    "conformsTo",
    "description",
    "license",
    "name",
    "url",
    "creator",
    "datePublished",
    "distribution",
)


def terminal_bench_croissant(**overrides):
    arguments = {
        "descriptor": load_descriptor(TERMINAL_BENCH_SOURCE),
        "repository": REPOSITORY,
        "digest": DIGEST,
        "date_published": DATE_PUBLISHED,
        "run_url": RUN_URL,
    }
    arguments.update(overrides)
    return croissant.build_croissant(**arguments)


class TerminalBenchCroissantTest(unittest.TestCase):
    def setUp(self):
        self.descriptor = load_descriptor(TERMINAL_BENCH_SOURCE)
        self.document = terminal_bench_croissant()

    def test_declares_every_property_croissant_requires(self):
        for property_name in CROISSANT_REQUIRED_PROPERTIES:
            with self.subTest(property_name=property_name):
                self.assertIn(property_name, self.document)
        self.assertEqual(self.document["@type"], "sc:Dataset")
        self.assertEqual(
            self.document["conformsTo"],
            ["http://mlcommons.org/croissant/1.1", "http://mlcommons.org/croissant/RAI/1.0"],
        )

    def test_context_declares_every_prefix_the_document_uses(self):
        context = self.document["@context"]
        serialized = json.dumps({key: value for key, value in self.document.items() if key != "@context"})
        for prefix in ("sc", "cr", "rai", "prov"):
            with self.subTest(prefix=prefix):
                self.assertIn(f'"{prefix}:', serialized)
                self.assertIn(prefix, context)
        self.assertEqual(context["conformsTo"], "dct:conformsTo")
        self.assertEqual(context["citeAs"], "cr:citeAs")

    def test_describes_the_dataset_from_its_descriptor(self):
        self.assertEqual(self.document["name"], "terminal-bench")
        self.assertEqual(self.document["alternateName"], "Terminal-Bench 2.0")
        self.assertEqual(self.document["version"], "2.0")
        self.assertEqual(self.document["description"], self.descriptor["description"])
        self.assertEqual(self.document["license"], "https://spdx.org/licenses/Apache-2.0.html")
        self.assertEqual(self.document["citeAs"], self.descriptor["upstream"]["citation"])
        self.assertEqual(
            self.document["creator"], {"@type": "sc:Organization", "name": "The Terminal-Bench Team"}
        )
        self.assertEqual(self.document["datePublished"], DATE_PUBLISHED)
        self.assertEqual(
            self.document["url"],
            "https://github.com/node-q/hbench-datasets/tree/main/datasets/terminal-bench/2.0",
        )

    def test_names_the_upstream_revision_it_was_derived_from(self):
        self.assertEqual(
            self.document["prov:wasDerivedFrom"],
            {
                "@type": "prov:Entity",
                "url": "https://github.com/laude-institute/terminal-bench-2",
                "version": "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c",
            },
        )
        self.assertEqual(self.document["prov:wasGeneratedBy"]["url"], RUN_URL)

    def test_distribution_is_the_pushed_manifest(self):
        (artifact,) = self.document["distribution"]
        self.assertEqual(artifact["@type"], "cr:FileObject")
        self.assertEqual(artifact["contentUrl"], f"oci://{REPOSITORY}@{DIGEST}")
        self.assertEqual(artifact["sha256"], DIGEST_HEX)
        self.assertEqual(
            artifact["encodingFormat"],
            ["application/vnd.oci.image.manifest.v1+json", "application/vnd.hbench.dataset.v1"],
        )

    def test_responsible_ai_fields_carry_the_descriptor_canary_and_environment(self):
        use_cases = self.document["rai:dataUseCases"]
        self.assertEqual(use_cases[0], self.descriptor["rai"]["data_use_cases"][0])
        self.assertIn(self.descriptor["canary"], use_cases[-1])
        limitations = self.document["rai:dataLimitations"]
        self.assertTrue(any("alexgshaw/{task}:20251031" in limitation for limitation in limitations))
        self.assertIn(self.descriptor["environment"]["planned"], limitations)
        self.assertEqual(self.document["rai:dataCollection"], self.descriptor["rai"]["data_collection"])
        self.assertEqual(self.document["rai:dataCollectionType"], ["Manual Human Curator"])
        self.assertTrue(self.document["rai:personalSensitiveInformation"])
        self.assertIn("its tag is never moved", self.document["rai:dataReleaseMaintenancePlan"])

    def test_omits_the_generating_run_when_none_is_given(self):
        self.assertNotIn("prov:wasGeneratedBy", terminal_bench_croissant(run_url=None))

    def test_pinned_images_are_stated_as_pinned(self):
        descriptor = load_descriptor(TERMINAL_BENCH_SOURCE)
        descriptor["environment"] = {
            "policy": "pinned-by-digest",
            "images": {"some-task": f"docker.io/example/some-task@{DIGEST}"},
        }
        document = terminal_bench_croissant(descriptor=descriptor)
        self.assertIn(
            "Every task's prebuilt environment image is pinned by digest.", document["rai:dataLimitations"]
        )
        self.assertFalse(any("by tag" in limitation for limitation in document["rai:dataLimitations"]))

    def test_mirrored_images_are_stated_as_pinned_to_the_mirror(self):
        document = terminal_bench_croissant(descriptor=load_descriptor(PINNED_MIRROR_SOURCE))
        self.assertEqual(document["version"], "2.0.1")
        self.assertIn(
            "Every task's prebuilt environment image is pinned by digest to ghcr.io/node-q/hbench-envs/terminal-bench, "
            "an unmodified mirror of the images upstream declares (alexgshaw/{task}:20251031).",
            document["rai:dataLimitations"],
        )
        self.assertFalse(any("by tag" in limitation for limitation in document["rai:dataLimitations"]))
        self.assertEqual(
            document["url"],
            "https://github.com/node-q/hbench-datasets/tree/main/datasets/terminal-bench/2.0.1",
        )

    def test_upstream_images_are_stated_as_pinned_upstream(self):
        descriptor = load_descriptor(PINNED_MIRROR_SOURCE)
        descriptor["environment"]["policy"] = "pinned-upstream"
        document = terminal_bench_croissant(descriptor=descriptor)
        self.assertIn(
            "Every task's prebuilt environment image is the one upstream declares (alexgshaw/{task}:20251031), "
            "pinned by its digest.",
            document["rai:dataLimitations"],
        )


class GeneratedCroissantTest(unittest.TestCase):
    def test_a_generated_dataset_names_its_adapter_upstream_files_and_built_image(self):
        descriptor = load_descriptor(GENERATED_SOURCE)
        document = croissant.build_croissant(
            descriptor, "ghcr.io/node-q/hbench-datasets/humaneval-plus", DIGEST, DATE_PUBLISHED, RUN_URL
        )
        self.assertEqual(
            document["prov:wasGeneratedBy"]["prov:label"],
            "hbench datasets push of the tasks adapters/humaneval_plus generates from "
            "https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz",
        )
        self.assertIn(
            "Every task's environment image is ghcr.io/node-q/hbench-envs:humaneval-plus-1.0, built by node-q from "
            "images/images.yaml in https://github.com/node-q/hbench-datasets and pinned by digest.",
            document["rai:dataLimitations"],
        )
        self.assertEqual(document["license"], "https://spdx.org/licenses/Apache-2.0.html")


class CroissantInputTest(unittest.TestCase):
    def test_rejects_a_digest_that_is_not_sha256(self):
        for digest in (DIGEST_HEX, "sha256:abc", f"sha512:{DIGEST_HEX}", DIGEST.upper()):
            with self.subTest(digest=digest), self.assertRaises(croissant.CroissantInputError):
                terminal_bench_croissant(digest=digest)

    def test_rejects_a_repository_with_a_tag_or_another_name(self):
        for repository in (
            f"{REPOSITORY}:2.0",
            f"{REPOSITORY}@{DIGEST}",
            "ghcr.io/node-q/hbench-datasets/other",
            "terminal-bench",
        ):
            with self.subTest(repository=repository), self.assertRaises(croissant.CroissantInputError):
                terminal_bench_croissant(repository=repository)

    def test_does_not_modify_the_descriptor(self):
        descriptor = load_descriptor(TERMINAL_BENCH_SOURCE)
        original = copy.deepcopy(descriptor)
        terminal_bench_croissant(descriptor=descriptor)
        self.assertEqual(descriptor, original)


class CroissantCommandTest(unittest.TestCase):
    def test_writes_the_json_ld_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "croissant.json"
            exit_code = croissant.main(
                [
                    "--source",
                    str(TERMINAL_BENCH_SOURCE),
                    "--repository",
                    REPOSITORY,
                    "--digest",
                    DIGEST,
                    "--date-published",
                    DATE_PUBLISHED,
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(exit_code, 0)
            document = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(document, terminal_bench_croissant(run_url=None))

    def test_refuses_a_bad_date_or_digest(self):
        arguments = ["--source", str(TERMINAL_BENCH_SOURCE), "--repository", REPOSITORY]
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                croissant.main([*arguments, "--digest", DIGEST, "--date-published", "22/10/2026"])
            exit_code = croissant.main([*arguments, "--digest", "sha256:0"])
        self.assertEqual(exit_code, 2)
        self.assertIn("'22/10/2026' is not a date", errors.getvalue())
        self.assertIn("'sha256:0' is not sha256:", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
