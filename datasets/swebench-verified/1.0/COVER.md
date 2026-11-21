## What this is

This test set checks whether an AI can fix real issues in real Python projects. It has 456 test tasks.

Each test task gives the AI a GitHub issue and the project's code from before the fix. The AI must change the code to resolve the issue.

## Where it comes from

SWE-bench is by Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press and Karthik Narasimhan. They collected merged pull requests from popular Python projects on GitHub. Each pull request resolves an issue and adds tests. They kept those whose tests fail before the pull request and pass after it.

SWE-bench Verified is 500 of its tasks, released by OpenAI with the SWE-bench authors. Professional software developers checked each task. They checked that the issue describes the problem well and that the tests are valid.

This test set keeps only projects under a permissive licence. Matplotlib and pylint are left out. That leaves 456 of the 500.

## How an answer is checked

Each test task is checked as SWE-bench checks it. The project's own tests run in the test task's container after the AI finishes. The test task passes only when every test for the fix passes and every test that passed before still passes.

Each environment is built where the test task runs. It starts from Epoch AI's public image for the task. The project's history after the starting point is removed.

## What it does not cover

- It is 456 of the 500 tasks of SWE-bench Verified. Its score is not directly comparable with one on all 500.
- Django alone is 231 of the 456 test tasks.
- The issues and their fixes have been public on GitHub for years. Models may have seen them in training.
- An AI with internet access can look up the real fix.
- The environments are Epoch AI's images, built in 2024. A few reference fixes may not pass in them.
- The tests run in the same container the AI used. An AI that changes the environment's tools can affect the result.

## Licence

This test set is free under the Apache License 2.0. The SWE-bench repository is under the MIT License. Each issue and fix keeps its project's licence. The notice that comes with the test set lists each project with its licence.
