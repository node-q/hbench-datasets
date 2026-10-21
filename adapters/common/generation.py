"""What every adapter's generate() is given besides its upstream files.

base_images is for a version whose environment policy is built-locally: each task's upstream base
image pinned by digest, from images.lock.json, which its environment/Dockerfile starts FROM.
"""

import dataclasses
import types


def no_base_images():
    return types.MappingProxyType({})


@dataclasses.dataclass(frozen=True)
class GenerationContext:
    dataset: str
    version: str
    canary: str
    docker_image: str | None
    base_images: types.MappingProxyType = dataclasses.field(default_factory=no_base_images)
