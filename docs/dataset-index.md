# Dataset index

An OCI registry cannot list its repositories (GHCR serves no catalog), so hbench learns which datasets are under
`ghcr.io/node-q/hbench-datasets` from an index: the manifest tagged `latest` in
`ghcr.io/node-q/hbench-datasets/index`. `hbench datasets list` and the interactive `hbench run` read it:

```bash
hbench datasets list --registry oci://ghcr.io/node-q/hbench-datasets
```

The index is an OCI image manifest with `artifactType` `application/vnd.hbench.dataset-index.v1`, an empty config
and one layer, `index.json`, of media type `application/vnd.hbench.dataset-index.v1+json`. The layer matches
[`schema/dataset-index.v1.json`](../schema/dataset-index.v1.json), a copy of hbench's
`assets/schemas/dataset-index.v1.json`:

```json
{
  "datasets": [
    {"digest": "sha256:7f10df0f…", "name": "terminal-bench", "version": "2.0"},
    {"digest": "sha256:72a08155…", "name": "terminal-bench", "version": "2.0.1"}
  ],
  "schema_version": 1
}
```

hbench opens every listed dataset by its digest, with the checks any dataset passes, so the index only says which
datasets there are; a wrong entry is refused, not run.

## How it is built

The **Index** workflow runs after a publish (Publish run on its own calls it; Release dataset calls it once after its
last set) and by hand:

1. `scripts/dataset_index.py` resolves `<name>:<version>` for each `datasets/<name>/<version>/source.yaml`, as an
   anonymous client does, and lists the versions the registry serves, sorted by name and version. A version not
   published yet, or whose package is still private, is left out and named in the job summary. A served version is
   listed only when `cosign verify --certificate-identity
   https://github.com/node-q/hbench-datasets/.github/workflows/publish.yml@refs/heads/main` passes on its digest; one
   that a failed publish pushed but did not sign is left out and named too. Any other cosign failure, after three
   tries, stops the run, so that the index never drops a dataset because of a network error.
   A version the published `index:latest` lists today that fails verification is never dropped: the run fails,
   naming it, and pushes nothing. Running Index by hand with `verify_only` verifies every served version, prints
   each result in the job summary and pushes no index; it fails on the same condition.
2. When the index lists the same datasets as `index:latest` already does, nothing is pushed.
3. Otherwise it pushes the index with oras, signs its digest with cosign keyless, and checks that an anonymous
   client can pull it.

A new GHCR package starts private. After the first run, make
[`hbench-datasets/index`](https://github.com/orgs/node-q/packages/container/hbench-datasets%2Findex/settings) public,
then run **Index** again.

Check the signature:

```bash
cosign verify ghcr.io/node-q/hbench-datasets/index@sha256:<digest> \
  --certificate-identity-regexp '^https://github.com/node-q/hbench-datasets/.github/workflows/index.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```
