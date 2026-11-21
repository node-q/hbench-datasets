## What this is

This test set checks whether an AI can fix real issues in real projects, beyond Python. It has 283 test tasks.

The projects are in C, C++, Go, Java, JavaScript, TypeScript, PHP, Ruby and Rust. Each test task gives the AI a GitHub issue and the project's code from before the fix. The AI must change the code to resolve the issue.

## Where it comes from

SWE-bench Multilingual is by the authors of SWE-bench. It was introduced with SWE-smith. They collected merged pull requests from popular projects in nine languages. Each pull request resolves an issue and adds tests. They kept those whose tests fail before the pull request and pass after it.

This test set keeps only projects under a permissive licence. Terraform and redis are left out. That leaves 283 of the 300 tasks.

## How an answer is checked

Each test task is checked as SWE-bench checks it. The project's own tests run in the test task's container after the AI finishes. The test task passes only when every test for the fix passes and every test that passed before still passes.

Each environment is built where the test task runs. It starts from SWE-bench's image for the task on Docker Hub. The project's history after the starting point is removed.

## What it does not cover

- It is 283 of the 300 tasks of SWE-bench Multilingual. Its score is not directly comparable with one on all 300.
- It covers 39 projects, with a few test tasks each.
- Most issue text is in English.
- The issues and their fixes are public on GitHub. Models may have seen them in training.
- An AI with internet access can look up the real fix.
- A run pulls SWE-bench's images from Docker Hub. If those images are removed, this version can no longer run.
- The tests run in the same container the AI used. An AI that changes the environment's tools can affect the result.

## Licence

This test set is free under the Apache License 2.0. SWE-bench Multilingual is under the MIT License. Each issue and fix keeps its project's licence. The notice that comes with the test set lists each project with its licence.
