## What this is

This test set checks whether an AI can fix real issues in real projects in seven languages. It has 1594 test tasks.

The projects are in C, C++, Go, Java, JavaScript, TypeScript and Rust. Each test task gives the AI a GitHub issue and the project's code from before the fix. The AI must change the code to resolve the issue.

## Where it comes from

Multi-SWE-bench is by Daoguang Zan and 18 other authors, at ByteDance Seed. They collected merged pull requests that resolve an issue in a popular project and add tests. They ran each project's tests before and after the fix, and kept the tasks where the fix makes tests pass. Reviewers who know each language then checked them.

This test set keeps only projects under a permissive licence. Logstash is left out, because part of its code is under the Elastic License. That leaves 1594 of the 1632 tasks.

## How an answer is checked

Each test task is checked as Multi-SWE-bench checks it. The project's own test script runs with the AI's changes and the task's tests. The test task passes only when the run completes and every test that should pass after the fix passes.

Each environment is built where the test task runs. It starts from Multi-SWE-bench's image for the task on Docker Hub, fixed to one exact build. The project's history after the starting point is removed, and so are the copies of the fix and its tests that the image keeps.

## What it does not cover

- It is 1594 of the 1632 tasks of Multi-SWE-bench. Its score is not directly comparable with one on all 1632.
- Three projects make up over half of the test tasks: cli/cli (397), sveltejs/svelte (272) and mui/material-ui (174).
- Most issue text is in English.
- The issues and their fixes are public on GitHub. Models may have seen them in training.
- An AI with internet access can look up the real fix.
- Each test task has its own image, often near a gigabyte. A run downloads them from Docker Hub, so running many test tasks takes a lot of disk space and time.
- If those images are removed from Docker Hub, this version can no longer run.
- The tests run in the same container the AI used. An AI that changes the environment's tools can affect the result.

## Licence

The task files written for this test set are under the Apache License 2.0. Multi-SWE-bench's data is under CC0, as its dataset card states, subject to any rights ByteDance holds in it. The parts of Multi-SWE-bench's code that grade each task are under the Apache License 2.0. Each issue and fix keeps its project's licence. The notice that comes with the test set quotes the dataset card and lists each project with its licence.
