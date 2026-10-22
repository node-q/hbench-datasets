# Publishing

For maintainers: how a dataset version's environment images are mirrored, pinned or built, and how
the version is published. Every step runs in this repository's workflows, from `main`, on
GitHub-hosted runners. Contributors propose versions as [CONTRIBUTING.md](../CONTRIBUTING.md)
describes.

- [Mirroring images](#mirroring-images)
- [Pinning upstream images](#pinning-upstream-images)
- [Building images](#building-images)
- [images.lock.json](#imageslockjson)
- [Publishing a version](#publishing-a-version)

## Mirroring images

A version whose environment policy is `pinned-mirror` runs its tasks' prebuilt images from node-q's
mirror. The **Mirror images** workflow copies each image, registry to registry, unmodified and with
its digest unchanged, to one GHCR package per dataset, `ghcr.io/node-q/hbench-envs/<dataset>`, tagged
`<task>-<upstream tag>` (for example
`ghcr.io/node-q/hbench-envs/terminal-bench:adaptive-rejection-sampler-20251031`). It signs each digest
with cosign keyless and writes `images.lock.json`. Each task's `task.toml` then names its image by
digest, `ghcr.io/node-q/hbench-envs/terminal-bench@sha256:…`, and nothing else in it changes.

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

## Pinning upstream images

A version whose policy is `pinned-upstream` pins upstream's images by digest without copying them,
for images that are not ours to redistribute or are too large to mirror. The **Pin images** workflow
resolves each tag with a registry HEAD request, which Docker Hub does not count as a pull, and writes
`images.lock.json`. Commit it to the version's directory in a pull request, as for a mirror.

## Building images

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

Until then `images.lock.json` is `{}`: the version validates with a warning, its tasks name no
`docker_image`, and the publish workflow refuses it.

## images.lock.json

`images.lock.json` maps each task, sorted, to the image upstream declares or the tag this repository
built (`source`), its digest (`source_digest`) and what `task.toml`'s `docker_image` becomes
(`pinned`); a mirrored image also has its tag in the mirror (`mirror_tag`):

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

## Publishing a version

A maintainer runs the **Publish** workflow from `main` with the dataset, the version and the
node-q/hbench release to pack with. It:

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

A new GHCR package starts private. After the first publish of a dataset, make its package public in
the package's settings
(`https://github.com/orgs/node-q/packages/container/hbench-datasets%2F<dataset>/settings`), then
re-run the release job.
