```text
██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
██║  ██║██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
███████║██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
██╔══██║██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
██║  ██║██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

██████╗  █████╗ ████████╗ █████╗ ███████╗███████╗████████╗███████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝
██║  ██║███████║   ██║   ███████║███████╗█████╗     ██║   ███████╗
██║  ██║██╔══██║   ██║   ██╔══██║╚════██║██╔══╝     ██║   ╚════██║
██████╔╝██║  ██║   ██║   ██║  ██║███████║███████╗   ██║   ███████║
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝   ╚══════╝
```

# hbench-datasets

Benchmark datasets for [hbench](https://github.com/node-q/hbench), published as signed OCI artifacts
at `ghcr.io/node-q/hbench-datasets`.

Each dataset version is one OCI image manifest, tagged with the version, with one reproducible layer
per task. hbench pulls it with `--registry oci://ghcr.io/node-q/hbench-datasets` and checks every layer
against the manifest's digest before it unpacks a task. Every version is signed with cosign keyless,
carries SLSA build provenance and Croissant 1.1 metadata, and has a GitHub release with its digest.

- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Datasets](#datasets)
- [Environments](#environments) · [Verifying a dataset](#verifying-a-dataset) · [Offline use and mirrors](#offline-use-and-mirrors) · [Licensing](#licensing)
- [Development](#development)
- [License](#license)
- [Contributors and contact](#contributors-and-contact)

## Installation

Requirements: hbench 0.3.0 or later, and a Docker daemon. Nothing from this repository needs to be
installed: hbench pulls a dataset when a run names it.

Install the latest hbench release:

```bash
curl -fsSL https://raw.githubusercontent.com/node-q/hbench/master/scripts/install.sh | sh
```

`HBENCH_VERSION=vX.Y.Z` pins a release and `HBENCH_INSTALL_DIR` overrides `~/.local/bin` (see
[hbench's README](https://github.com/node-q/hbench)). To check signatures and
provenance, or to copy a dataset without hbench, you also need [cosign](https://github.com/sigstore/cosign),
the [GitHub CLI](https://cli.github.com) or [oras](https://oras.land).

## Usage

```bash
# Run
hbench run -d terminal-bench@2.0.1 --registry oci://ghcr.io/node-q/hbench-datasets -a oracle
hbench run -d humaneval-plus@1.0 --registry oci://ghcr.io/node-q/hbench-datasets --lock-write   # record the digest in ./hbench.lock
hbench run -d humaneval-plus@1.0 --registry oci://ghcr.io/node-q/hbench-datasets --locked       # refuse any other digest

# Download and copy
hbench datasets download humaneval-plus@1.0 --registry oci://ghcr.io/node-q/hbench-datasets -o ./cache
hbench datasets export -d terminal-bench@2.0.1 --registry oci://ghcr.io/node-q/hbench-datasets --oci-layout ./hbench-layout
hbench datasets list --registry oci-layout:./hbench-layout
hbench run -d terminal-bench@2.0.1 --registry oci-layout:./hbench-layout

```

`--registry oci://ghcr.io/node-q/hbench-datasets` names the namespace, and `-d <dataset>@<version>`
picks the repository `<dataset>` in it and the tag `<version>`. A registry can't be listed, so a run
names its dataset; an OCI layout on disk can be listed. In a job config, the dataset sets
`registry: "oci://ghcr.io/node-q/hbench-datasets"` with its `name` and `version`, and may set
`digest: "sha256:..."` to run that manifest whatever the tag says.

`--lock-write` records each dataset's manifest digest in `./hbench.lock`, keyed by `name@version`. A
dataset in `hbench.lock` runs at its locked digest, and `--locked` refuses one that is not in it or
whose tag now resolves to another digest. To check a dataset's signature and provenance, see
[Verifying a dataset](#verifying-a-dataset).

## Examples

Check the setup with the oracle agent, which runs each task's reference solution, on five tasks:

```bash
hbench run -d humaneval-plus@1.0 --registry oci://ghcr.io/node-q/hbench-datasets -a oracle -l 5
```

Run Claude Code on Terminal-Bench 2.0, with every task's image pinned by digest:

```bash
ANTHROPIC_API_KEY=... hbench run -d terminal-bench@2.0.1 --registry oci://ghcr.io/node-q/hbench-datasets \
  -a claude-code -m anthropic/claude-opus-5-5 -n 4
```

Keep a series of runs on the same bytes: record the digests once, commit `hbench.lock`, and run with
`--locked` from then on:

```bash
hbench run -d mbpp-plus@1.0 --registry oci://ghcr.io/node-q/hbench-datasets -a oracle -l 1 --lock-write
hbench run -d mbpp-plus@1.0 --registry oci://ghcr.io/node-q/hbench-datasets -a codex -m openai/gpt-5 --locked
```

Browse the results in hbench's web viewer:

```bash
hbench view jobs
```

## Datasets

| Dataset | Tasks | What it tests | Licence |
|---|---:|---|---|
| `terminal-bench@2.0` | 89 | Work in a terminal: build, debug, configure, train. Images from Docker Hub, by the tags upstream declares | Apache-2.0 |
| `terminal-bench@2.0.1` | 89 | The same tasks, with each image pinned by digest to node-q's mirror on GHCR | Apache-2.0 |
| `humaneval-plus@1.0` | 164 | Write a Python function from its signature and docstring: HumanEval with EvalPlus's extended tests | Apache-2.0 |
| `humanevalfix@1.0` | 164 | Fix a bug written by hand into a HumanEval function (BigCode's HumanEvalPack) | Apache-2.0 |
| `mbpp-plus@1.0` | 378 | Write a Python function from a description and an example: MBPP with EvalPlus's extended tests | Apache-2.0 |
| `cruxeval-input@1.0` | 800 | Given a Python function and an output, find an input that gives it (CRUXEval-I) | Apache-2.0 |

Each version has a [release](https://github.com/node-q/hbench-datasets/releases) named
`<dataset>-<version>`, such as
[`terminal-bench-2.0.1`](https://github.com/node-q/hbench-datasets/releases/tag/terminal-bench-2.0.1):
its reference and manifest digest, task count, licence and upstream commit, how to run and check it,
and its `croissant.json`, `source.yaml`, `LICENSE` and `NOTICE`. A published tag never moves; a fix is
a new version. Each dataset will also be mirrored to a second registry, not chosen yet.

A version is one OCI image manifest at `ghcr.io/node-q/hbench-datasets/<dataset>:<version>`:

- `artifactType: application/vnd.hbench.dataset.v1`;
- a config blob, `application/vnd.hbench.dataset.config.v1+json`, with the dataset's licence,
  upstream, canary and each task's digests;
- one reproducible `tar+gzip` layer per task, which unpacks byte-identical to the task directory
  it was packed from.

hbench's README describes the [format](https://github.com/node-q/hbench#dataset-format) in full.

## Environments

A task runs in the Docker image its `task.toml` names as `docker_image`. With none, or with
`--force-build`, hbench builds the task's `environment/Dockerfile` instead. A version's environment
policy says where its images come from:

| Policy | Images | Versions |
|---|---|---|
| `as-declared` | Upstream's images, by the tags upstream declares. Upstream can move a tag | `terminal-bench@2.0` |
| `pinned-mirror` | Upstream's images, copied unmodified with their digests to `ghcr.io/node-q/hbench-envs/<dataset>`, and named by digest | `terminal-bench@2.0.1` |
| `pinned-upstream` | Upstream's images, named by digest and not copied: for images that are not ours to redistribute or are too large to mirror | none yet |
| `built` | Images this repository builds, tags of `ghcr.io/node-q/hbench-envs`, named by digest. Each starts `FROM` a base image copied to GHCR, so neither a build nor a run needs Docker Hub | `humaneval-plus@1.0`, `humanevalfix@1.0`, `mbpp-plus@1.0` and `cruxeval-input@1.0`, which share `humaneval-plus-1.0` |

A version that pins its images has an `images.lock.json` next to its `source.yaml`, listing each
task's image and digest. [docs/PUBLISHING.md](docs/PUBLISHING.md) describes how the images are
mirrored, pinned and built.

## Verifying a dataset

The signature, made by this repository's publish workflow:

```bash
cosign verify ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/publish.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

The build provenance:

```bash
gh attestation verify oci://ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 --repo node-q/hbench-datasets
```

The Croissant metadata, a referrer of the dataset's manifest:

```bash
oras discover --artifact-type application/ld+json ghcr.io/node-q/hbench-datasets/terminal-bench:2.0
```

A mirrored image, with its digest from the version's `images.lock.json`, is signed by the mirror
workflow. Its digest is upstream's own: `crane digest alexgshaw/<task>:20251031` prints the same one
for as long as upstream keeps the tag where it is.

```bash
cosign verify ghcr.io/node-q/hbench-envs/terminal-bench@sha256:<digest> \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/mirror-images.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

A built image is signed by the build workflow:

```bash
cosign verify ghcr.io/node-q/hbench-envs@sha256:<digest> \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/build-images.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Offline use and mirrors

`hbench datasets export` copies a dataset into an OCI image layout, `<dir>/<dataset>`, and hbench reads
it with `--registry oci-layout:<dir>`:

```bash
hbench datasets export -d terminal-bench@2.0 --registry oci://ghcr.io/node-q/hbench-datasets --oci-layout ./hbench-layout
hbench run -d terminal-bench@2.0 --registry oci-layout:./hbench-layout
```

`oras cp ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 --to-oci-layout ./hbench-layout/terminal-bench:2.0`
writes the same layout without hbench. The tasks' environment images are not part of the layout:
pull or load them before going offline.

To mirror a dataset to another registry:

```bash
oras copy -r ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 <registry>/<namespace>/terminal-bench:2.0
```

`-r` copies the referrers too: the signature, the attestation and the Croissant metadata. Digests do
not change, so the mirror verifies with the same commands, and hbench reads it with
`--registry oci://<registry>/<namespace>`. `hbench.lock` is keyed by `name@version`, not by registry,
so a locked run accepts the mirror only because it serves the same digest.

## Licensing

The tooling in this repository is Apache-2.0 ([`LICENSE`](LICENSE)). Each dataset keeps its own
licence, in its directory and published with it.

- **terminal-bench@2.0** is Apache-2.0.
- **terminal-bench@2.0.1** is the same tasks, Apache-2.0. Its environment images are redistributed
  unmodified from upstream's published images; the software in them carries its own licences.
- **humaneval-plus@1.0** is generated by node-q from HumanEval+ (EvalPlus, Apache-2.0), which
  extends OpenAI's HumanEval (MIT). Its task directories are Apache-2.0, with both notices in its
  NOTICE.
- **humanevalfix@1.0** (from BigCode's HumanEvalPack, MIT), **mbpp-plus@1.0** (from EvalPlus's
  MBPP+, Apache-2.0, derived from Google's MBPP, CC BY 4.0) and **cruxeval-input@1.0** (from Meta's
  CRUXEval, MIT) are generated by node-q. Their task directories are Apache-2.0, with every upstream
  notice in their NOTICE.
- **swebench-verified@1.0 and aider-polyglot@1.0** have MIT data, but their task directories come
  from a third-party shared task repository with no LICENSE file. They need that repository's
  permission, or task directories of our own, which would be new versions.
- **livecodebench@6.0** has an unspecified "cc" licence and problems scraped from contest sites. It
  is not republished.
- **SWE-bench's prebuilt images** embed GPL-2.0 code among other licences. They are pinned upstream
  by digest, not mirrored.

The details are in [`docs/licensing.md`](docs/licensing.md).

## Development

### Repository layout

| Path | What it is |
|---|---|
| `datasets/<name>/<version>/source.yaml` | Where a dataset version's task directories come from (git URL, full commit and path, or the adapter that generates them and the upstream files it reads) and what the published dataset declares: licence, upstream and citation, canary string, environment policy, attribution. |
| `datasets/<name>/<version>/LICENSE`, `NOTICE` | The dataset's own licence and attribution, published with it. |
| `datasets/<name>/<version>/images.lock.json` | For a version that pins its environment images by digest: each task's upstream or built image, its digest, and what its `docker_image` is pinned to. |
| `datasets/<name>/<version>/generated.lock.json` | For a generated version: each task's hbench package digest. |
| `adapters/` | The adapters that generate task directories, and `adapters/common`, what they share. |
| `images/` | The environment images this repository builds (`images.yaml`) and the base images they start from (`bases.yaml`). |
| [`schema/source.v1.json`](schema/source.v1.json) | The JSON Schema for `source.yaml`. |
| `scripts/` | Descriptor validation, fetching a source at its pinned commit, the pushed-manifest check, the Croissant generator, a verified hbench install, and the image mirror and pin scripts. |
| [`docs/licensing.md`](docs/licensing.md) | Which datasets can be republished, and why. |
| [`docs/PUBLISHING.md`](docs/PUBLISHING.md) | For maintainers: mirroring, pinning and building images, and publishing a version. |

No task files are committed. CI fetches each git source at its pinned commit, or generates a
generated source's tasks from its pinned upstream files, and packs them.

### Generated datasets

A dataset version whose source kind is `generated` has task directories this repository writes
itself. Its descriptor names an adapter, `adapters/<name>`, and the upstream files the adapter
reads, each at a fixed URL and pinned by sha256:

```yaml
source:
  kind: generated
  adapter: adapters/humaneval_plus
  upstream_files:
    - name: HumanEvalPlus.jsonl.gz
      url: https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz
      sha256: 272720b90ac375502c8ed23cd791c2a93dfb22a911641a494da74a426c09f101
  task_count: 164
environment:
  policy: built
  image: humaneval-plus-1.0
  images_lock: images.lock.json
```

`scripts/generated_source.py generate` downloads the files, checks their digests, runs the
adapter's `generate()`, and adds each task's `environment/`, the build context of its image. The
output is deterministic, so the tasks are not committed: `generated.lock.json` holds each task's
package digest, as `hbench tasks digest` prints it. CI generates every generated version twice and
fails if a digest differs from the lock, then runs each task's checker on its oracle and on a wrong
solution. `fetch_source.py` generates instead of fetching, so publishing works as for any source.

### Verification

```bash
python -m pip install --require-hashes -r requirements.txt
python scripts/validate_sources.py                  # every source.yaml, its LICENSE, NOTICE and SPDX id
python scripts/environment_images.py check          # the environment images and their bases
python -m unittest discover --start-directory tests --verbose
```

CI (`.github/workflows/validate.yml`) runs these on GitHub-hosted runners with Python 3.12, fetches
every dataset version's task directories at their pinned commits, and generates each generated
version twice and checks every task.

## License

The tooling in this repository is Apache-2.0. See [LICENSE](LICENSE). Each dataset keeps its own
licence (see [Licensing](#licensing)).

## Contributors and contact

hbench-datasets is maintained by [node-q](https://github.com/node-q). See the
[contributors graph](https://github.com/node-q/hbench-datasets/graphs/contributors) for everyone who
has contributed.

Report bugs and request datasets in [GitHub issues](https://github.com/node-q/hbench-datasets/issues).
To propose a dataset, see [CONTRIBUTING.md](CONTRIBUTING.md). To report a problem with a published
dataset, such as a signature that does not verify or a tag that moved, use private reporting as
[SECURITY.md](SECURITY.md) describes.
