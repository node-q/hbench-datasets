## What this is

This test set checks whether an AI can write Python that does real work with common libraries. It has 1135 test tasks.

Each test task gives the AI a function's signature and a docstring. The docstring says what the function must do and which libraries to use. Between them the test tasks use 139 libraries: Python's own, and others such as pandas, NumPy, Matplotlib, scikit-learn and requests. The AI writes the function.

## Where it comes from

BigCodeBench is by Terry Yue Zhuo and 32 other authors, in the BigCode project. GPT-4 wrote first drafts of the tasks from existing programming problems. People then rewrote the docstrings, added unit tests and checked that each reference solution passes them.

The same authors picked 147 of the harder ones as BigCodeBench-Hard. Those are marked hard here.

This test set leaves out 5 of the 1140 tasks, because their tests cannot tell a right answer from a wrong one here. One needs a screen. Two fetch web pages that now refuse the request. One reference solution hangs on every run. One task's tests never call the function. That leaves 1135.

## How an answer is checked

The task's unit tests run on the AI's function, the way BigCodeBench's own checker runs them. The AI does not see these tests. The test task passes when none of them fails, within about four minutes. The libraries are the versions BigCodeBench chose.

## What it does not cover

- It is 1135 of the 1140 tasks of BigCodeBench. Its score is not directly comparable with one on all 1140.
- The tasks are in English and Python only.
- The tests expect older library versions, such as NumPy 1.21 and pandas 2.0. Code written for a newer version can fail.
- Some tests read the clock, wait, or use the internet. The authors report that about 0.2% of results can change from one run to the next, so two close scores may not really differ.
- Most tasks process data, draw charts or run small system scripts. Few are larger programs.
- BigCodeBench has been public since 2024. Models may have seen its tasks and solutions in training.

## Licence

This test set is free under the Apache License 2.0. BigCodeBench is under the Apache License 2.0 too. The notice that comes with the test set carries BigCodeBench's licence notice.
