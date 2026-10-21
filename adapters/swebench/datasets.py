"""What differs between the SWE-bench datasets this adapter generates: their names, titles and base images.

Verified and Lite start from Epoch AI's public GHCR images, built from the same specifications as
SWE-bench's own.
"""

import dataclasses
from collections.abc import Callable

EPOCH_IMAGE_REPOSITORY = "ghcr.io/epoch-research/swe-bench.eval.x86_64"
UPSTREAM_TAG = "latest"


class DatasetError(ValueError):
    pass


def epoch_image(row):
    return f"{EPOCH_IMAGE_REPOSITORY}.{row['instance_id']}:{UPSTREAM_TAG}"


def python_language(row):
    return "python"


@dataclasses.dataclass(frozen=True)
class Dataset:
    name: str
    title: str
    base_image: Callable[[dict], str]
    language: Callable[[dict], str]


DATASETS = {
    dataset.name: dataset
    for dataset in (
        Dataset("swebench-verified", "SWE-bench Verified", epoch_image, python_language),
        Dataset("swebench-lite", "SWE-bench Lite", epoch_image, python_language),
    )
}


def dataset_named(name):
    try:
        return DATASETS[name]
    except KeyError:
        raise DatasetError(f"{name!r} is not a dataset this adapter generates: {', '.join(sorted(DATASETS))}") from None
