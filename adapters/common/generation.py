"""What every adapter's generate() is given besides its upstream files."""

import dataclasses


@dataclasses.dataclass(frozen=True)
class GenerationContext:
    dataset: str
    version: str
    canary: str
    docker_image: str | None
