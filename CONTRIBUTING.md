# Contributing

## Proposing a dataset

1. **Check the licence first.** Republishing a dataset redistributes it. Before writing anything,
   find out:
   - whether its licence allows redistribution, and whether it covers the task directories
     themselves (instructions, environments, tests, solutions), not only the underlying data;
   - what any prebuilt environment images embed, since mirroring an image redistributes everything
     in it;
   - whether the upstream has a canary string.

   Add the dataset to the table in [`docs/licensing.md`](docs/licensing.md) with what you found. A
   dataset whose licence does not allow redistribution is not republished.
2. **Write the descriptor**, `datasets/<name>/<version>/source.yaml`, against
   [`schema/source.v1.json`](schema/source.v1.json). See
   [`datasets/terminal-bench/2.0/source.yaml`](datasets/terminal-bench/2.0/source.yaml). Pin the
   source by full commit SHA, give the exact task count, and say how the environment images are
   referenced: `as-declared`, `pinned-mirror` (copied to `ghcr.io/node-q/hbench-envs/<name>` by the
   Mirror images workflow) or `pinned-upstream` (pinned by digest by the Pin images workflow). A
   version that pins its images also commits `images.lock.json`, `{}` until that workflow has run;
   see [`datasets/terminal-bench/2.0.1`](datasets/terminal-bench/2.0.1). Do not commit any task
   files: CI fetches them.
3. **Add `LICENSE` and `NOTICE`** next to it. `LICENSE` is the upstream licence text, verbatim.
   `NOTICE` names the authors, gives their citation, and says what, if anything, was changed.
4. **Run the checks:**

   ```sh
   python3 -m venv .venv && . .venv/bin/activate
   pip install --require-hashes -r requirements.txt
   python scripts/validate_sources.py
   PYTHONPATH=scripts python -m unittest discover -s tests
   ```

   `python scripts/fetch_source.py datasets/<name>/<version>/source.yaml <empty directory>` fetches
   the source at its pinned commit and checks its task count and images, as CI does. It downloads
   every task directory.
5. **Open a pull request.** CI validates the descriptor and fetches the source. After it is merged,
   a maintainer publishes it.

## Versions are immutable

- A published tag is never moved. A version is published once the publish workflow has finished:
  pushed, signed, attested and with its Croissant file attached.
- A change of bytes is a new version, in a new directory: a task fixed upstream, a new upstream
  commit, or images pinned by digest. A change that keeps upstream's version and changes only how it
  is packaged bumps the last component, as 2.0 to 2.0.1. The old version's directory stays.
- A publish run that fails after pushing leaves a tag that is not signed. A maintainer deletes that
  package version before running the workflow again.

## Changing the tooling

- Actions are pinned by full commit SHA, with the version in a comment. Workflows run on
  GitHub-hosted runners only.
- Python packages are pinned with hashes in `requirements.txt`, generated from `requirements.in`:

  ```sh
  uv pip compile requirements.in --universal --generate-hashes --python-version 3.12 -o requirements.txt
  ```
