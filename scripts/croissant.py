"""Write a dataset version's Croissant 1.1 JSON-LD from its source.yaml and pushed manifest digest.

Usage: croissant.py --source datasets/<name>/<version>/source.yaml
                    --repository ghcr.io/node-q/hbench-datasets/<name>
                    --digest sha256:<manifest digest>
                    [--date-published YYYY-MM-DD] [--run-url URL] [--output croissant.json]
"""

import argparse
import datetime
import json
import re
import sys

from environment_images import tag_reference
from source_descriptor import PUBLISHED_REPOSITORY_URL, load_descriptor

CROISSANT_SPECIFICATION = "http://mlcommons.org/croissant/1.1"
CROISSANT_RAI_SPECIFICATION = "http://mlcommons.org/croissant/RAI/1.0"
OCI_IMAGE_MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
HBENCH_DATASET_ARTIFACT_TYPE = "application/vnd.hbench.dataset.v1"
DATASET_ARTIFACT_ID = "dataset-artifact"
PUBLISHER = {"@type": "sc:Organization", "name": "node-q", "url": "https://github.com/node-q"}

CROISSANT_CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "sc": "https://schema.org/",
    "cr": "http://mlcommons.org/croissant/",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "dct": "http://purl.org/dc/terms/",
    "prov": "http://www.w3.org/ns/prov#",
    "annotation": "cr:annotation",
    "arrayShape": "cr:arrayShape",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "containedIn": "cr:containedIn",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "excludes": "cr:excludes",
    "extract": "cr:extract",
    "field": "cr:field",
    "fileProperty": "cr:fileProperty",
    "fileObject": "cr:fileObject",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isArray": "cr:isArray",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "readLines": "cr:readLines",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sdVersion": "cr:sdVersion",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
    "unArchive": "cr:unArchive",
    "value": "cr:value",
}

RAI_PROPERTY_BY_DESCRIPTOR_KEY = {
    "data_collection": "rai:dataCollection",
    "data_collection_type": "rai:dataCollectionType",
    "data_use_cases": "rai:dataUseCases",
    "data_limitations": "rai:dataLimitations",
    "data_biases": "rai:dataBiases",
    "personal_sensitive_information": "rai:personalSensitiveInformation",
    "data_social_impact": "rai:dataSocialImpact",
}

MANIFEST_DIGEST_PATTERN = re.compile(r"^sha256:(?P<hex>[0-9a-f]{64})$")
REPOSITORY_PATTERN = re.compile(r"^[a-z0-9.-]+(:[0-9]+)?(/[a-z0-9]+([._-][a-z0-9]+)*)+$")


class CroissantInputError(ValueError):
    pass


def spdx_license_url(license_id):
    return f"https://spdx.org/licenses/{license_id}.html"


def release_maintenance_plan():
    return (
        f"Published from {PUBLISHED_REPOSITORY_URL} by its CI, signed with cosign and attested with SLSA "
        "provenance. A published version never changes: its tag is never moved, and a change of bytes is a "
        "new version."
    )


def canary_use_case(canary):
    return (
        "Evaluation only, not training. The tasks carry the canary string "
        f'"{canary}"; leave any document that contains it out of training corpora.'
    )


def environment_limitations(environment):
    if environment["policy"] == "pinned-by-digest":
        return ["Every task's prebuilt environment image is pinned by digest."]
    if environment["policy"] == "built":
        return [
            f"Every task's environment image is {tag_reference(environment['image'])}, built by node-q from "
            f"images/images.yaml in {PUBLISHED_REPOSITORY_URL} and pinned by digest."
        ]
    limitations = []
    declared_image = environment.get("declared_image")
    if declared_image:
        limitations.append(
            f"Task environments are prebuilt images referenced as upstream declares them ({declared_image}), "
            "by tag rather than by digest."
        )
    if environment.get("planned"):
        limitations.append(environment["planned"])
    return limitations


def rai_properties(descriptor):
    rai = descriptor.get("rai", {})
    properties = {
        RAI_PROPERTY_BY_DESCRIPTOR_KEY[key]: value
        for key, value in rai.items()
        if key in RAI_PROPERTY_BY_DESCRIPTOR_KEY
    }
    if descriptor.get("canary"):
        properties["rai:dataUseCases"] = [
            *properties.get("rai:dataUseCases", []),
            canary_use_case(descriptor["canary"]),
        ]
    limitations = environment_limitations(descriptor["environment"])
    if limitations:
        properties["rai:dataLimitations"] = [*properties.get("rai:dataLimitations", []), *limitations]
    properties["rai:dataReleaseMaintenancePlan"] = release_maintenance_plan()
    return properties


def manifest_digest_hex(digest):
    match = MANIFEST_DIGEST_PATTERN.match(digest)
    if not match:
        raise CroissantInputError(f"digest {digest!r} is not sha256:<64 lowercase hex digits>")
    return match.group("hex")


def checked_repository(repository, dataset_name):
    if not REPOSITORY_PATTERN.match(repository):
        raise CroissantInputError(
            f"repository {repository!r} is not <registry>/<path>, without a tag or digest"
        )
    if repository.rsplit("/", 1)[-1] != dataset_name:
        raise CroissantInputError(
            f"repository {repository!r} does not end with the dataset name {dataset_name!r}"
        )
    return repository


def source_label(source):
    if source.get("kind") == "generated":
        urls = ", ".join(upstream_file["url"] for upstream_file in source["upstream_files"])
        return f"the tasks {source['adapter']} generates from {urls}"
    return f"{source['git_url']} at {source['commit']}"


def build_croissant(descriptor, repository, digest, date_published, run_url=None):
    digest_hex = manifest_digest_hex(digest)
    repository = checked_repository(repository, descriptor["name"])
    name = descriptor["name"]
    version = descriptor["version"]
    upstream = descriptor["upstream"]
    croissant = {
        "@context": CROISSANT_CONTEXT,
        "@type": "sc:Dataset",
        "conformsTo": [CROISSANT_SPECIFICATION, CROISSANT_RAI_SPECIFICATION],
        "name": name,
        "alternateName": descriptor["title"],
        "description": descriptor["description"],
        "version": version,
        "license": spdx_license_url(descriptor["license"]),
        "url": f"{PUBLISHED_REPOSITORY_URL}/tree/main/datasets/{name}/{version}",
        "sameAs": upstream["url"],
        "creator": {"@type": "sc:Organization", "name": upstream["creator"]},
        "publisher": PUBLISHER,
        "datePublished": date_published,
        "citeAs": upstream["citation"],
        "prov:wasDerivedFrom": {
            "@type": "prov:Entity",
            "url": upstream["url"],
            "version": upstream["revision"],
        },
    }
    if descriptor.get("keywords"):
        croissant["keywords"] = descriptor["keywords"]
    if run_url:
        croissant["prov:wasGeneratedBy"] = {
            "@type": "prov:Activity",
            "prov:label": f"hbench datasets push of {source_label(descriptor['source'])}",
            "url": run_url,
        }
    croissant.update(rai_properties(descriptor))
    croissant["distribution"] = [
        {
            "@type": "cr:FileObject",
            "@id": DATASET_ARTIFACT_ID,
            "name": f"{name}:{version}",
            "description": "The dataset's OCI artifact: one image manifest, a config blob and one tar+gzip layer per task.",
            "contentUrl": f"oci://{repository}@{digest}",
            "encodingFormat": [OCI_IMAGE_MANIFEST_MEDIA_TYPE, HBENCH_DATASET_ARTIFACT_TYPE],
            "sha256": digest_hex,
        }
    ]
    return croissant


def iso_date(value):
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a date such as 2026-10-22") from None


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Write a dataset version's Croissant 1.1 JSON-LD.")
    parser.add_argument("--source", required=True, help="the dataset version's source.yaml")
    parser.add_argument(
        "--repository", required=True, help="OCI repository, e.g. ghcr.io/node-q/hbench-datasets/<name>"
    )
    parser.add_argument("--digest", required=True, help="the pushed manifest digest, sha256:<hex>")
    parser.add_argument(
        "--date-published",
        type=iso_date,
        default=datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
    )
    parser.add_argument("--run-url", help="URL of the CI run that published the dataset")
    parser.add_argument("--output", help="file to write; standard output if omitted")
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    descriptor = load_descriptor(options.source)
    try:
        croissant = build_croissant(
            descriptor, options.repository, options.digest, options.date_published, options.run_url
        )
    except CroissantInputError as error:
        print(f"croissant.py: {error}", file=sys.stderr)
        return 2
    document = json.dumps(croissant, indent=2, ensure_ascii=False) + "\n"
    if options.output:
        with open(options.output, "w", encoding="utf-8") as output:
            output.write(document)
    else:
        sys.stdout.write(document)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
