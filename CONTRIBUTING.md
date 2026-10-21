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
   `NOTICE` names the authors, gives their citation, and says what, if anything, was changed. For a
   generated dataset, see below.
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

## Adding a generated dataset

When the task directories are ours, generated from upstream data whose licence allows it, the
version is a generated one; see [`datasets/humaneval-plus/1.0`](datasets/humaneval-plus/1.0).

1. **Write the adapter**, `adapters/<name>/adapter.py` (with an empty `__init__.py`). It defines:
   - `UPSTREAM_FILES`, the names of the upstream files it reads;
   - `generate(upstream_files, out_dir, context)`, which reads only `upstream_files` (name to local
     path) and writes one directory per task into `out_dir`, returning their names. `context` is an
     `adapters.common.generation.GenerationContext`: the dataset, its version, the canary, and the
     `docker_image` to write into `task.toml`, `None` until the image is built. It writes no
     `environment/`: the generic step adds the image's build context;
   - `verify_tasks(tasks_directory, jobs, names)`, which checks that each task's oracle passes and a
     wrong solution fails, and returns an exit code;
   - optionally `task_problems(task_directory)`, the adapter's own checks of a generated task.

   The output must be deterministic: no timestamps, no randomness, sorted iteration, fixed file
   modes. Each task's `[task].name` is its bare directory name, as in Terminal-Bench, never
   `org/name`: `writing.task_toml` writes it so. `adapters/common` has the helpers: `writing` writes
   task files deterministically,
   `package_digest` is hbench's package digest, and `function_checker` is an EvalPlus-style checker
   for tasks that ask for one Python function (`problem_document`, `function_checker_files` and
   `verify.verify_tasks`). A checker of another shape runs the agent's code through the same
   sandbox with `sandbox_checker_files` and `verify.Checker`, as `adapters/mbpp_plus`,
   `adapters/humanevalfix` and `adapters/cruxeval_input` do. Adapters, and everything they import,
   use only the Python standard library, so that CI can run their checks in the image's base.
2. **Add the image** to [`images/images.yaml`](images/images.yaml), tagged `<dataset>-<version>`,
   with its build context `images/<name>/` and its base. Its Dockerfile starts
   `FROM ghcr.io/node-q/hbench-envs:<base tag>@<base digest>`. A new base goes in
   [`images/bases.yaml`](images/bases.yaml), tagged `base-<name>-<tag>`, with the Docker Hub digest
   it is copied at. Tasks whose environment a built image already gives name that image instead, as
   `humanevalfix@1.0` names `humaneval-plus-1.0`.
3. **Write the descriptor** with `source.kind: generated`, the adapter, each upstream file's name,
   URL and sha256, and the task count, and `environment.policy: built` with the image's tag and
   `images_lock: images.lock.json`. Commit `images.lock.json` as `{}`. `LICENSE` is Apache-2.0, the
   licence of the task directories we write; `NOTICE` carries every upstream licence notice,
   copyright line and citation, and says what the adapter keeps and what it writes. If the upstream
   has no canary string, give the dataset one of ours: a new GUID.
4. **Write the lock and run the checks:**

   ```sh
   python scripts/generated_source.py generate --allow-unfilled-lock --write-lock \
     datasets/<name>/<version>/source.yaml <empty directory>
   python scripts/check_generated_tasks.py --output <empty directory> datasets/<name>/<version>
   python -m adapters.verify <adapter> <empty directory>/<name>/<version>/first/tasks
   ```

   The first writes `generated.lock.json`. CI regenerates the tasks and refuses any that differ from
   it, so a change to the adapter, its shared helpers or the image's build context is committed with
   the lock it produces.
5. **After the pull request is merged**, a maintainer runs the Build images workflow and commits the
   `images.lock.json` and `generated.lock.json` it writes, as the README describes. Only then can the
   version be published.

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
