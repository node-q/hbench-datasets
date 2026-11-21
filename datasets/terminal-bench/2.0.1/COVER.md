## What this is

This test set checks whether an AI can do valuable work in a computer terminal. It has 89 test tasks.

The work ranges from assembling proteins for synthesis to debugging async code and fixing security holes. Each test task has an instruction, an environment in a container, tests that check the result and a reference solution.

## Where it comes from

Contributors to the Terminal-Bench project wrote the test tasks. Each test task names its author. Each one received several hours of checking by people and by models. The checks make sure that it can be solved, that it is realistic and that it is clearly described.

Version 2.0.1 has the same test tasks as Terminal-Bench 2.0. The only change is how each environment is fetched. Each one is pinned to an exact, unchanged copy of the original image.

## How an answer is checked

Each test task's own tests run after the AI finishes. They check the state the AI left the environment in.

## What it does not cover

- All the test tasks are in English.
- Of the test tasks, 26 are software engineering. The rest cover systems administration, security, scientific computing, data science and a few smaller areas.
- A score is a pass rate over a small set.
- A run downloads each environment, so it needs internet access.

## Licence

This test set is free under the Apache License 2.0, as is Terminal-Bench 2.0. The notice that comes with the test set carries the credit.
