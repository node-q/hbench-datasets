import pathlib

import yaml

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASETS_DIR = REPOSITORY_ROOT / "datasets"
SCHEMA_PATH = REPOSITORY_ROOT / "schema" / "source.v1.json"
DESCRIPTOR_FILENAME = "source.yaml"
PUBLISHED_REPOSITORY_URL = "https://github.com/node-q/hbench-datasets"


class UniqueKeySafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen_keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen_keys:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            seen_keys.add(key)
        return super().construct_mapping(node, deep=deep)


def load_descriptor(path):
    with open(path, encoding="utf-8") as stream:
        return yaml.load(stream, Loader=UniqueKeySafeLoader)


def version_directories():
    return sorted(path for path in DATASETS_DIR.glob("*/*") if path.is_dir())
