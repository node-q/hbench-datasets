"""Which upstream repositories' instances a dataset keeps: only those under a permissive licence.

repo-licences.json records, for each repository, what GitHub's licence API reports (spdx_id, the licence
file and its copyright lines) and, where GitHub asserts no licence, a review of the licence file itself
(review.spdx_id and review.reason). A repository is kept when the licence it is used under, the review's
if there is one, else GitHub's, is in PERMISSIVE_LICENCES. Everything else is dropped: copyleft licences,
MPL included, source-available licences, and repositories whose licence is unknown or missing.
"""

import json
import pathlib

LICENCES_PATH = pathlib.Path(__file__).resolve().parent / "repo-licences.json"
PERMISSIVE_LICENCES = frozenset(
    {
        "0BSD",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "BSL-1.0",
        "ISC",
        "MIT",
        "MIT-0",
        "PSF-2.0",
        "Unlicense",
        "UPL-1.0",
        "Zlib",
    }
)
UNASSERTED_LICENCES = (None, "NOASSERTION", "OTHER")


class LicenceError(ValueError):
    pass


def load_licences(path=LICENCES_PATH):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def licence_entry(licences, repository):
    if repository in licences:
        return licences[repository]
    for name, entry in licences.items():
        if name.lower() == repository.lower():
            return entry
    raise LicenceError(f"{repository} is not in repo-licences.json; look it up with scripts/repo_licences.py")


def used_licence(entry):
    review = entry.get("review")
    if review:
        return review["spdx_id"]
    return entry["spdx_id"]


def drop_reason(entry):
    licence = used_licence(entry)
    if licence in PERMISSIVE_LICENCES:
        return None
    if entry.get("review"):
        return f"{licence}: {entry['review']['reason']}"
    if licence in UNASSERTED_LICENCES:
        return "GitHub detects no licence" if licence is None else "GitHub cannot identify its licence"
    return f"{licence} is not a permissive licence"


def is_permissive(licences, repository):
    return drop_reason(licence_entry(licences, repository)) is None


def repository_licence(licences, repository):
    entry = licence_entry(licences, repository)
    if drop_reason(entry) is not None:
        raise LicenceError(f"{repository} is not under a permissive licence: {drop_reason(entry)}")
    return used_licence(entry)
