"""Look up the licence of every GitHub repository a generated dataset's instances come from.

Usage: repo_licences.py --output repo-licences.json [--upstream-cache DIRECTORY]
                        datasets/<name>/<version>/source.yaml [...]

Fetches each version's upstream files, asks its adapter's upstream_repositories() for the repositories
its instances come from, and asks GitHub's licence API (GET /repos/<owner>/<repo>/license) for each: the
SPDX id GitHub detects, the licence file's URL and blob, and the copyright lines in it. For a repository
under Apache-2.0 it also reads the NOTICE file at the repository's root, if there is one. Entries of other
repositories already in --output are kept, so several datasets can share one file, and so is the review
of a repository whose licence file was read by hand. GITHUB_TOKEN, if set, authenticates the requests,
which are made one at a time.
"""

import argparse
import base64
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

import generated_source
from source_descriptor import load_descriptor

GITHUB_API = "https://api.github.com"
NOTICE_FILE_NAMES = ("NOTICE", "NOTICE.txt", "NOTICE.md")
APACHE_LICENCE = "Apache-2.0"
COPYRIGHT_LINE = re.compile(r"\bcopyright\s*(?:\(c\)|©)|^\s*copyright\s+(?:\d{4}|by\s)", re.IGNORECASE)
TEMPLATE_COPYRIGHT_LINE = re.compile(r"\[(?:yyyy|year)\]|\{yyyy\}|<year>|\[name of copyright owner\]", re.IGNORECASE)
REQUEST_TIMEOUT_SECONDS = 60
SECONDS_BETWEEN_REQUESTS = 0.5
ENTRY_KEY_ORDER = (
    "spdx_id",
    "name",
    "license_file",
    "api_url",
    "blob_sha",
    "copyright",
    "notice_file",
    "notice",
    "review",
)


class LicenceLookupError(RuntimeError):
    pass


def github_get(path, token=None, open_url=urllib.request.urlopen, sleep=time.sleep):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    sleep(SECONDS_BETWEEN_REQUESTS)
    request = urllib.request.Request(f"{GITHUB_API}{path}", headers=headers)
    try:
        with open_url(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise LicenceLookupError(f"GET {path} answered {error.code} {error.reason}") from None
    except urllib.error.URLError as error:
        raise LicenceLookupError(f"GET {path} failed: {error.reason}") from None


def decoded_content(answer):
    return base64.b64decode(answer.get("content", "")).decode("utf-8", errors="replace")


def copyright_lines(text):
    lines = []
    for line in text.splitlines():
        if COPYRIGHT_LINE.search(line) and not TEMPLATE_COPYRIGHT_LINE.search(line):
            stripped = " ".join(line.split())
            if stripped not in lines:
                lines.append(stripped)
    return lines


def notice_of(repository, token, get):
    for name in NOTICE_FILE_NAMES:
        answer = get(f"/repos/{repository}/contents/{name}", token)
        if isinstance(answer, dict) and answer.get("type") == "file":
            return answer["html_url"], decoded_content(answer).replace("\r\n", "\n").strip() + "\n"
    return None, None


def repository_licence(repository, token=None, get=github_get):
    api_url = f"{GITHUB_API}/repos/{repository}/license"
    answer = get(f"/repos/{repository}/license", token)
    if answer is None:
        return {
            "spdx_id": None,
            "name": None,
            "license_file": None,
            "api_url": api_url,
            "blob_sha": None,
            "copyright": [],
            "notice_file": None,
            "notice": None,
        }
    licence = answer.get("license") or {}
    spdx_id = licence.get("spdx_id")
    notice_file, notice = notice_of(repository, token, get) if spdx_id == APACHE_LICENCE else (None, None)
    return {
        "spdx_id": spdx_id,
        "name": licence.get("name"),
        "license_file": answer.get("html_url"),
        "api_url": api_url,
        "blob_sha": answer.get("sha"),
        "copyright": copyright_lines(decoded_content(answer)),
        "notice_file": notice_file,
        "notice": notice,
    }


def with_review_kept(looked_up, previous):
    if previous and previous.get("review"):
        return {**looked_up, "review": previous["review"]}
    return looked_up


def dump_licences(licences):
    ordered = {
        repository: {key: licences[repository][key] for key in ENTRY_KEY_ORDER if key in licences[repository]}
        for repository in sorted(licences, key=str.lower)
    }
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def load_licences(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def repositories_of(descriptor_path, upstream_cache):
    descriptor = load_descriptor(descriptor_path)
    source = descriptor["source"]
    adapter = generated_source.adapter_module(source["adapter"])
    with tempfile.TemporaryDirectory() as workspace:
        paths = generated_source.fetched_upstream_files(
            source["upstream_files"], pathlib.Path(workspace) / "upstream", upstream_cache
        )
        return set(adapter.upstream_repositories(paths, descriptor["name"]))


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description="Look up the licences of the repositories a dataset's instances come from.")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--upstream-cache", type=pathlib.Path)
    parser.add_argument("descriptors", nargs="+", type=pathlib.Path)
    return parser.parse_args(arguments)


def main(arguments):
    options = parse_arguments(arguments)
    token = os.environ.get("GITHUB_TOKEN")
    try:
        repositories = set()
        for descriptor_path in options.descriptors:
            repositories |= repositories_of(descriptor_path, options.upstream_cache)
        licences = load_licences(options.output)
        for repository in sorted(repositories, key=str.lower):
            licences[repository] = with_review_kept(repository_licence(repository, token), licences.get(repository))
            print(f"{repository}: {licences[repository]['spdx_id']}")
    except (LicenceLookupError, generated_source.GeneratedSourceError) as error:
        print(f"repo_licences.py: {error}", file=sys.stderr)
        return 1
    options.output.write_text(dump_licences(licences), encoding="utf-8")
    print(f"{len(repositories)} repositories looked up, {len(licences)} in {options.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
