# hbench-datasets

Benchmark datasets for [hbench](https://github.com/node-q/hbench) (`node-q/hbench`), the CLI that
runs AI agents on benchmark tasks in Docker, published as signed OCI artifacts.

**Nothing is published yet.** The publish workflow is ready, but it refuses to run until a
node-q/hbench release has `hbench datasets push`.

## What's here

| Path | What it is |
| --- | --- |
| `datasets/<name>/<version>/source.yaml` | Where a dataset version's task directories come from (git URL, full commit, path) and what the published dataset declares: licence, upstream and citation, canary string, environment policy, attribution. |
| `datasets/<name>/<version>/LICENSE`, `NOTICE` | The dataset's own licence and attribution, published with it. |
| [`schema/source.v1.json`](schema/source.v1.json) | The JSON Schema for `source.yaml`. |
| `scripts/` | Descriptor validation, fetching a source at its pinned commit, the pushed-manifest check, the Croissant generator, and a verified hbench install. |
| [`docs/licensing.md`](docs/licensing.md) | Which datasets can be republished, and why. |

No task files are committed. CI fetches each source at its pinned commit and packs it.

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

## Running a dataset

This needs an hbench release with the OCI read path (`--registry oci://…`), which is being built.

```sh
hbench run -d terminal-bench@2.0 --registry oci://ghcr.io/node-q/hbench-datasets
```

hbench resolves `terminal-bench:2.0` to its manifest digest and checks every layer against it
before unpacking a task. Terminal-Bench 2.0's tasks still pull their prebuilt environment images
from Docker Hub, by tag (`alexgshaw/<task>:20251031`); a later 2.0.x pins them by digest.

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
- **humanevalfix@1.0, swebench-verified@1.0 and aider-polyglot@1.0** have MIT data, but their task
  directories come from a third-party shared task repository with no LICENSE file. They need that
  repository's permission, or task directories of our own, which would be new versions.
- **livecodebench@6.0** has an unspecified "cc" licence and problems scraped from contest sites. It
  is not republished.
- **SWE-bench's prebuilt images** embed GPL-2.0 code among other licences. They are pinned upstream
  by digest, not mirrored.

The details are in [`docs/licensing.md`](docs/licensing.md).

## Publishing

A maintainer runs the **Publish** workflow from `main` with the dataset, the version and the
node-q/hbench release to pack with. It runs on GitHub-hosted runners and:

1. refuses to run unless that hbench release has `hbench datasets push`, installing it only after
   checking `SHA256SUMS` and its build provenance;
2. refuses to overwrite a tag that already exists;
3. fetches the source at its pinned commit and checks its task count and images against the
   descriptor;
4. packs and pushes with `hbench datasets push`, then checks the pushed manifest;
5. signs the manifest digest with cosign, attests it with `actions/attest`, and attaches the
   Croissant file;
6. writes the digest to the job summary.

To propose a dataset, see [CONTRIBUTING.md](CONTRIBUTING.md). To report a problem with a published
dataset, see [SECURITY.md](SECURITY.md).
