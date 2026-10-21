# Licensing

Republishing a dataset redistributes it, so every dataset passes a licence check before it gets a
descriptor. Each published dataset carries its LICENSE and NOTICE and keeps its canary strings. A
dataset whose licence does not allow redistribution is not republished; its metadata points at the
upstream revision instead.

| Dataset | Tasks | Underlying data | Task directories today | Status |
| --- | ---: | --- | --- | --- |
| `terminal-bench@2.0` | 89 | Apache-2.0 | [laude-institute/terminal-bench-2], Apache-2.0 | **Configured** in [`datasets/terminal-bench/2.0`](../datasets/terminal-bench/2.0) |
| `humanevalfix@1.0` | 164 | [HumanEvalPack], MIT | A third-party shared task repository with no LICENSE file | Not configured |
| `swebench-verified@1.0` | 500 | [SWE-bench], MIT | A third-party shared task repository with no LICENSE file | Not configured; prebuilt images not mirrored |
| `aider-polyglot@1.0` | 225 | [Exercism] exercises, MIT | A third-party shared task repository with no LICENSE file | Not configured |
| `livecodebench@6.0` | 100 | [LiveCodeBench], licence "cc", unspecified | A third-party shared task repository with no LICENSE file | Not republished |

## Terminal-Bench 2.0

The task directories are in [laude-institute/terminal-bench-2] at commit
`69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`, licensed Apache-2.0 by their authors. The upstream
repository added its LICENSE file in commit `2ef6e27cf5888ec23adcbb72807b36b0508dfd68`
(2025-11-11), after that revision; the commit adds the file and changes nothing else.
[`datasets/terminal-bench/2.0/LICENSE`](../datasets/terminal-bench/2.0/LICENSE) is a copy of it,
and the [NOTICE](../datasets/terminal-bench/2.0/NOTICE) gives the authors and their citation.

Version 2.0 is published byte-identical, so every task keeps
`docker_image = "alexgshaw/<task>:20251031"`, a Docker Hub tag. A later 2.0.x pins each image by
digest. The images are not part of the dataset and are not mirrored.

## Datasets from a third-party shared task repository

Today the task directories of `humanevalfix@1.0`, `swebench-verified@1.0`, `aider-polyglot@1.0`
and `livecodebench@6.0` come from a third-party shared task repository that has no LICENSE file.
The underlying data is MIT for the first three, but the task directories are adaptations (an
instruction, a Docker environment, tests and a solution per task) written by that repository's
contributors, and the data's licence does not cover them. Redistributing them needs one of:

1. **That repository's permission** to redistribute its task directories, recorded in each
   dataset's NOTICE. The datasets would then be published byte-identical, as the versions above.
2. **Our own task directories, generated from the original sources.** Those are different bytes,
   so they are published as new dataset versions, never as the versions above.

Until then, none of them has a descriptor.

### HumanEvalFix

[HumanEvalPack] (from OctoPack, by BigCode) is MIT. Its HumanEvalFix tasks can be generated from it
directly.

### SWE-bench Verified

[SWE-bench] is MIT, in its repository; its Hugging Face dataset cards state no licence. Its
prebuilt task images embed each target repository and its dependencies, GPL-2.0 code among other
licences, so they are not mirrored: a dataset version pins the upstream images by digest.

### Aider Polyglot

The exercises come from [Exercism]'s language tracks, which are MIT. Aider's polyglot-benchmark
repository, which collects them, has no LICENSE file either, so our own task directories would be
built from the Exercism tracks.

### LiveCodeBench

Its dataset's licence is "cc", with no variant or version, and its problems are scraped from
programming contest sites, whose own terms apply. It is not republished. If it is listed, only its
metadata is published, pointing at the upstream revision.

[laude-institute/terminal-bench-2]: https://github.com/laude-institute/terminal-bench-2
[HumanEvalPack]: https://huggingface.co/datasets/bigcode/humanevalpack
[SWE-bench]: https://github.com/SWE-bench/SWE-bench
[Exercism]: https://exercism.org
[LiveCodeBench]: https://huggingface.co/datasets/livecodebench/code_generation_lite
