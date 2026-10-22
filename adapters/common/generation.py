"""What every adapter's generate() is given besides its upstream files."""

import dataclasses
import fnmatch


@dataclasses.dataclass(frozen=True)
class GenerationContext:
    dataset: str
    version: str
    canary: str
    docker_image: str | None
    task_docker_images: tuple[tuple[str, str], ...] = ()

    def docker_image_for(self, task_name):
        for pattern, reference in self.task_docker_images:
            if fnmatch.fnmatchcase(task_name, pattern):
                return reference
        return self.docker_image
