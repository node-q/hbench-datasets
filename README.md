# hbench-datasets

Benchmark datasets for [hbench](https://github.com/node-q/hbench) (`node-q/hbench`), the CLI that
runs AI agents on benchmark tasks in Docker, published as signed OCI artifacts.

**Nothing is published yet.** The publish workflow is ready, but it refuses to run until a
node-q/hbench release has `hbench datasets push`.

## What's here

| Path | What it is |
| --- | --- |
| `datasets/<name>/<version>/source.yaml` | Where a dataset version's task directories come from (git URL, full commit and path, or the adapter that generates them and the upstream files it reads) and what the published dataset declares: licence, upstream and citation, canary string, environment policy, attribution. |
| `datasets/<name>/<version>/LICENSE`, `NOTICE` | The dataset's own licence and attribution, published with it. |
| `datasets/<name>/<version>/images.lock.json` | For a version that pins its environment images by digest: each task's upstream or built image, its digest, and what its `docker_image` is pinned to. |
| `datasets/<name>/<version>/generated.lock.json` | For a generated version: each task's hbench package digest. |
| `adapters/` | The adapters that generate task directories, and `adapters/common`, what they share. |
| `images/` | The environment images this repository builds (`images.yaml`) and the base images they start from (`bases.yaml`). |
| [`schema/source.v1.json`](schema/source.v1.json) | The JSON Schema for `source.yaml`. |
| `scripts/` | Descriptor validation, fetching a source at its pinned commit, the pushed-manifest check, the Croissant generator, a verified hbench install, and the image mirror and pin scripts. |
| [`docs/licensing.md`](docs/licensing.md) | Which datasets can be republished, and why. |

No task files are committed. CI fetches each git source at its pinned commit, or generates a
generated source's tasks from its pinned upstream files, and packs them.

Each dataset version is one OCI image manifest at
`ghcr.io/node-q/hbench-datasets/<dataset>:<version>`:

- `artifactType: application/vnd.hbench.dataset.v1`;
- a config blob, `application/vnd.hbench.dataset.config.v1+json`;
- one reproducible `tar+gzip` layer per task, which unpacks byte-identical to the upstream task
  directory.

It is signed with cosign keyless (GitHub OIDC), carries SLSA build provenance from GitHub artifact
attestations, and has a Croissant 1.1 JSON-LD file attached for discovery. Tags are never moved: a
new version is a new tag. Each dataset is also mirrored to a second registry, not chosen yet.

| Dataset | Tasks | Licence | Status |
| --- | ---: | --- | --- |
| `terminal-bench@2.0` | 89 | Apache-2.0 | Configured, not published yet |
| `terminal-bench@2.0.1` | 89 | Apache-2.0 | Configured |
| `humaneval-plus@1.0` | 164 | Apache-2.0 | Generated; waits for its image to be built |
| `bigcodebench@1.0` | 1,135 | Apache-2.0 | Generated, with the Hard subset's 147 tasks tagged `hard`; waits for its image to be built |
| `humanevalfix@1.0` | 164 | Apache-2.0 | Generated; waits for its image lock |
| `mbpp-plus@1.0` | 378 | Apache-2.0 | Generated; waits for its image lock |
| `cruxeval-input@1.0` | 800 | Apache-2.0 | Generated; waits for its image lock |
| `exercism-polyglot@1.0` | 210 | Apache-2.0 | Generated, 35 tasks in each of six languages; waits for its six images to be built |
| `swebench-verified@1.0` | 456 | Apache-2.0, with its repositories' licences | Generated; environments built locally |
| `swebench-lite@1.0` | 270 | Apache-2.0, with its repositories' licences | Generated; environments built locally |
| `swebench-multilingual@1.0` | 283 | Apache-2.0, with its repositories' licences | Generated; environments built locally |
| `multi-swe-bench@1.0` | 1594 | Apache-2.0, with its repositories' licences | Generated; environments built locally |

## Running a dataset

This needs an hbench release with the OCI read path (`--registry oci://…`), which is being built.

```sh
hbench run -d terminal-bench@2.0 --registry oci://ghcr.io/node-q/hbench-datasets
```

hbench resolves `terminal-bench:2.0` to its manifest digest and checks every layer against it
before unpacking a task. In `terminal-bench@2.0` the tasks pull their prebuilt environment images
from Docker Hub by tag (`alexgshaw/<task>:20251031`). `terminal-bench@2.0.1` is the same tasks with
each image pinned by digest to its mirror (see [Mirrored environments](#mirrored-environments)).

## Verifying a dataset

The signature, made by this repository's publish workflow:

```sh
cosign verify ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/publish.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

The build provenance:

```sh
gh attestation verify oci://ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 --repo node-q/hbench-datasets
```

The Croissant metadata is a referrer of the dataset's manifest:

```sh
oras discover --artifact-type application/ld+json ghcr.io/node-q/hbench-datasets/terminal-bench:2.0
```

## Mirroring

```sh
oras copy -r ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 <registry>/<namespace>/terminal-bench:2.0
```

`-r` copies the referrers too: the signature, the attestation and the Croissant metadata. Digests do
not change, so the mirror verifies with the same commands, and hbench reads it with
`--registry oci://<registry>/<namespace>`.

## Mirrored environments

A dataset version whose environment policy is `pinned-mirror` runs its tasks' prebuilt images from
node-q's mirror. The **Mirror images** workflow copies each image, registry to registry, unmodified
and with its digest unchanged, to one GHCR package per dataset, `ghcr.io/node-q/hbench-envs/<dataset>`,
tagged `<task>-<upstream tag>` (for example
`ghcr.io/node-q/hbench-envs/terminal-bench:adaptive-rejection-sampler-20251031`). It signs each digest
with cosign keyless and writes `images.lock.json`. Each task's `task.toml` then names its image by
digest, `ghcr.io/node-q/hbench-envs/terminal-bench@sha256:…`, and nothing else in it changes.

To verify a mirrored image, take its digest from the version's `images.lock.json`:

```sh
cosign verify ghcr.io/node-q/hbench-envs/terminal-bench@sha256:<digest> \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/mirror-images.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

The digest is upstream's own: `crane digest alexgshaw/<task>:20251031` prints the same one for as
long as upstream keeps the tag where it is.

A version whose policy is `pinned-upstream` pins upstream's images by digest without copying them,
for images that are not ours to redistribute or are too large to mirror. The **Pin images** workflow
resolves each tag with a registry HEAD request, which Docker Hub does not count as a pull, and writes
`images.lock.json`.

`images.lock.json` maps each task, sorted, to the image upstream declares (`source`), its digest
(`source_digest`) and what `task.toml`'s `docker_image` becomes (`pinned`); a mirrored image also has
its tag in the mirror (`mirror_tag`):

```json
{
  "adaptive-rejection-sampler": {
    "source": "alexgshaw/adaptive-rejection-sampler:20251031",
    "source_digest": "sha256:…",
    "pinned": "ghcr.io/node-q/hbench-envs/terminal-bench@sha256:…",
    "mirror_tag": "adaptive-rejection-sampler-20251031"
  }
}
```

For `pinned-upstream`, `pinned` is `alexgshaw/adaptive-rejection-sampler@sha256:…` and there is no
`mirror_tag`. A version is committed with `{}` as its lock; it validates with a warning, and the
publish workflow refuses it until the lock is filled.

To mirror a dataset's images, a maintainer:

1. optionally adds the repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. Without them,
   the copy pulls from Docker Hub anonymously, in shards on separate runners, and waits and retries
   when it is rate limited;
2. runs **Mirror images** from `main` with the dataset and the version whose tasks declare the images
   (`terminal-bench`, `2.0`). A mirror tag that already holds the source's digest is skipped and one
   that holds another digest is never overwritten, so a failed run is finished by re-running it;
3. after the first run, makes the package public: a new GHCR package starts private, and only its
   [settings page](https://github.com/orgs/node-q/packages/container/hbench-envs%2Fterminal-bench/settings)
   changes that. Publishing a `pinned-mirror` version refuses to run until every mirrored image can
   be pulled anonymously;
4. commits the run's `images.lock.json` artifact to the `pinned-mirror` version's directory
   (`datasets/terminal-bench/2.0.1/`) in a pull request. CI checks it against every task.

## Generated datasets

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

A generated version's environment policy is `built`: every task runs in an image this repository
builds, a tag of the one GHCR package `ghcr.io/node-q/hbench-envs`. `images/bases.yaml` lists base
images, copied from Docker Hub once with their digests unchanged and tagged `base-<name>-<tag>`
(`base-python-3.12-slim`); `images/images.yaml` lists the built images, tagged `<dataset>-<version>`
(`humaneval-plus-1.0`), each with its build context and base. Every built image's Dockerfile starts
`FROM` its base's GHCR copy pinned by digest, so neither a build nor a run needs Docker Hub, and the
task's `environment/Dockerfile`, the same file, is what `--force-build` builds. Versions whose tasks
need the same environment share an image: `humanevalfix@1.0`, `mbpp-plus@1.0` and
`cruxeval-input@1.0` run in `humaneval-plus-1.0`, and `generated_source.py lock-image` writes the
locks of every version built on a tag at once.

To build an image, a maintainer:

1. runs **Build images** from `main` with its tag (`humaneval-plus-1.0`). The workflow copies any base
   not on GHCR yet, builds the image for its platforms, pushes it, refusing an existing tag, and
   signs it with cosign keyless;
2. the first time, makes [`hbench-envs`](https://github.com/orgs/node-q/packages/container/hbench-envs/settings)
   public: a new GHCR package starts private, and it is one package for every built image and base;
3. commits the run's `locks-<tag>` artifact, the `images.lock.json` and `generated.lock.json` of every
   version built on the image, in a pull request.

```sh
cosign verify ghcr.io/node-q/hbench-envs@sha256:<digest> \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/build-images.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

Until then `images.lock.json` is `{}`: the version validates with a warning, its tasks name no
`docker_image`, and the publish workflow refuses it.

## Locally built environments

A generated version whose environment policy is `built-locally` ships no environment image at all:
its tasks name no `docker_image`, and hbench builds each task's `environment/Dockerfile` on the
machine that runs it. The Dockerfile starts `FROM` the task's upstream base image, pinned by digest,
and adds what the adapter needs, such as removing the answer from the image. The adapter declares
each task's base image (`base_images()`), and `images.lock.json` pins it, in the `pinned-upstream`
shape:

```json
{
  "astropy__astropy-12907": {
    "source": "ghcr.io/epoch-research/swe-bench.eval.x86_64.astropy__astropy-12907:latest",
    "source_digest": "sha256:87fda8f3ae644b986737fad17ca1f05cc4ffdf4d9f11acd4ca70bae12674495c",
    "pinned": "ghcr.io/epoch-research/swe-bench.eval.x86_64.astropy__astropy-12907@sha256:87fda8f3ae644b986737fad17ca1f05cc4ffdf4d9f11acd4ca70bae12674495c"
  }
}
```

The **Pin images** workflow (`scripts/pin_images.py`) writes it, resolving each tag with a registry
HEAD request. A base image upstream does not publish is left out of the lock and listed, and the
adapter generates no task for it, so `task_count` is the number of pinned tasks. A new lock changes
the tasks, so it is committed with the `generated.lock.json` it produces. The publish workflow
refuses a version whose base images can no longer be pulled anonymously.

These tasks need Docker to check, so CI checks a sample. The **Sample tasks** workflow runs on every
pull request: for each built-locally version it takes 10 tasks in a fixed order
(`scripts/sample_tasks.py`), one per group of the adapter's choosing first, and on a GitHub-hosted
runner each builds its environment from the pinned base and runs hbench's `oracle` agent, which
must score 1, and `nop`, which must score 0. The job summary gives each task's time and disk. The
**Sweep tasks** workflow, run by hand, does the same for every task of one version, shared between
runners, and reports every task whose oracle or `nop` result is wrong.

### SWE-bench

`swebench-verified@1.0`, `swebench-lite@1.0` and `swebench-multilingual@1.0` are generated by
`adapters/swebench` from SWE-bench's own dataset files, and keep only the instances from repositories
under a permissive licence (see [`docs/licensing.md`](docs/licensing.md#swe-bench-verified-lite-and-multilingual)).
Each task is named by its instance id, which `[metadata].instance_id` repeats, beside the
repository, its licence, the base commit and the pull request.

- **Environment.** Verified and Lite start from Epoch AI's public GHCR images for the instance, built
  from SWE-bench's image specifications, and Multilingual from SWE-bench's own images on Docker Hub,
  each pinned by digest. A layer on top removes
  what would give the answer away: every tag and reference after the base commit, so that
  `git log --all` cannot show the fix, and then the unreachable objects. The build fails unless the
  repository keeps only the base commit's history.
- **Grading.** After the agent, a collect hook in its container (carried in `task.toml`, so the
  agent never sees it) saves the agent's changes, runs the instance's eval script as SWE-bench's
  harness runs it, recording the test command's exit status, and keeps the log in
  `/logs/artifacts/swebench`. The verifier then runs in a separate container from
  `python:3.12-slim`, because many of the images have no Python, and grades the log with SWE-bench's
  own grading code and log parsers, vendored from swebench 5.0.2. The reward is 1 only when every
  `FAIL_TO_PASS` and every `PASS_TO_PASS` test passes. The log stays an artifact of the trial, so a
  trial can be regraded.
- **Oracle.** `solution/solve.sh` applies the instance's reference patch as SWE-bench's harness
  applies a prediction.

### Multi-SWE-bench

`multi-swe-bench@1.0` is generated by `adapters/multi_swe_bench` from Multi-SWE-bench's
per-repository JSONL files, keeping the instances of its repositories under a permissive licence (see
[`docs/licensing.md`](docs/licensing.md#multi-swe-bench)). Its tasks are laid out as the SWE-bench
ones, by the same `adapters/swebench/tasks.py`.

- **Environment.** Each task starts from Multi-SWE-bench's image for the pull request on Docker Hub
  (`mswebench/<org>_m_<repository>:pr-<number>`), pinned by digest. The layer on top removes the
  history after the base commit, as for SWE-bench, and deletes the fix and test patches the images
  keep in `/home`.
- **Grading.** The collect hook resets the files the test patch touches, restores the test patch and
  runs the image's own `test-run.sh`, as Multi-SWE-bench's harness runs a prediction, for up to three
  hours: the harness sets no limit, and ponyc's test run builds LLVM first. The verifier
  grades the log with the repository's `parse_log` and the harness's `Report`, vendored unchanged
  from the harness; its image installs the two packages they need, `dataclasses-json` and `unidiff`,
  from hash-pinned requirements. The reward is 1 only when the report is valid and every test the
  instance expects to pass passes.
- **Upstream files.** They are 1.8 GB, mui's alone 750 MB. CI downloads them; the generated job
  uploads the `generated.lock.json` it computes when it differs from the committed one, so a lock can
  be refreshed without downloading them elsewhere.

## Offline use

hbench's `export` command, which is not in a release yet, writes an OCI image layout to a
directory, and hbench reads it with `--registry oci-layout:<dir>`:

```sh
hbench datasets export --oci-layout ./hbench-layout terminal-bench@2.0 --registry oci://ghcr.io/node-q/hbench-datasets
hbench run -d terminal-bench@2.0 --registry oci-layout:./hbench-layout
```

`oras copy -r --to-oci-layout ghcr.io/node-q/hbench-datasets/terminal-bench:2.0 ./hbench-layout:2.0`
writes the same layout today. The tasks' environment images are not part of the layout: pull or
load them before going offline.

## Licensing

The tooling in this repository is Apache-2.0 ([`LICENSE`](LICENSE)). Each dataset keeps its own
licence, in its directory and published with it.

- **terminal-bench@2.0** is Apache-2.0 and configured.
- **terminal-bench@2.0.1** is the same tasks, Apache-2.0. Its environment images are redistributed
  unmodified from upstream's published images; the software in them carries its own licences.
- **humaneval-plus@1.0** is generated by node-q from HumanEval+ (EvalPlus, Apache-2.0), which
  extends OpenAI's HumanEval (MIT). Its task directories are Apache-2.0, with both notices in its
  NOTICE.
- **bigcodebench@1.0** is generated by node-q from BigCodeBench (BigCode, Apache-2.0). Its task
  directories are Apache-2.0; BigCodeBench-Hard, whose card states no licence, contributes only the
  IDs of the 147 tasks tagged `hard`.
- **humanevalfix@1.0** (from BigCode's HumanEvalPack, MIT), **mbpp-plus@1.0** (from EvalPlus's
  MBPP+, Apache-2.0, derived from Google's MBPP, CC BY 4.0) and **cruxeval-input@1.0** (from Meta's
  CRUXEval, MIT) are generated by node-q. Their task directories are Apache-2.0, with every upstream
  notice in their NOTICE.
- **exercism-polyglot@1.0** is generated by node-q from Exercism's MIT-licensed problem
  specifications and C++, Go, Java, JavaScript, Python and Rust tracks. Its task directories are
  Apache-2.0, with Exercism's notices and Catch2's licence in its NOTICE.
- **swebench-verified@1.0, swebench-lite@1.0 and swebench-multilingual@1.0** are generated by node-q
  from SWE-bench's data, and **multi-swe-bench@1.0** from Multi-SWE-bench's (CC0, its harness
  Apache-2.0), keeping only instances from permissively licensed repositories. node-q's files are
  Apache-2.0; the issue texts and patches keep their repositories' licences, which each NOTICE
  lists. No environment image is redistributed.
- **aider-polyglot@1.0** has MIT data, but its task directories come from a third-party shared
  task repository with no LICENSE file. It needs that repository's permission, or task
  directories of our own, which would be a new version.
- **livecodebench@6.0** has an unspecified "cc" licence and problems scraped from contest sites. It
  is not republished.
- **SWE-bench's prebuilt images** embed GPL-2.0 code among other licences. They are not mirrored:
  the SWE-bench tasks build their environments locally from upstream images pinned by digest.

The details are in [`docs/licensing.md`](docs/licensing.md).

## Publishing

A maintainer runs the **Publish** workflow from `main` with the dataset, the version and the
node-q/hbench release to pack with. It runs on GitHub-hosted runners and:

1. refuses to run unless that hbench release has `hbench datasets push`, installing it only after
   checking `SHA256SUMS` and its build provenance;
2. refuses to overwrite a tag that already exists;
3. fetches the source at its pinned commit, or generates it, and checks its task count and images
   against the descriptor; for a version that pins its images, refuses an `images.lock.json` that is
   not filled yet, or mirrored or built images that cannot be pulled anonymously, and pins each
   task's `docker_image` from the lock;
4. packs and pushes with `hbench datasets push`, then checks the pushed manifest;
5. signs the manifest digest with cosign, attests it with `actions/attest`, and attaches the
   Croissant file;
6. writes the digest to the job summary;
7. once an anonymous pull of the new digest works, creates the GitHub release
   `<dataset>-<version>` (for example `terminal-bench-2.0`): the reference and digest, how to run
   and verify it, and its `croissant.json`, `source.yaml`, `LICENSE` and `NOTICE` attached.

A new GHCR package starts private. After the first publish of a dataset, make its package public
in the package's settings, then re-run the release job.

To propose a dataset, see [CONTRIBUTING.md](CONTRIBUTING.md). To report a problem with a published
dataset, see [SECURITY.md](SECURITY.md).
