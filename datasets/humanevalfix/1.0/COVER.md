## What this is

This test set checks whether an AI can find and fix a bug in Python code. It has 164 test tasks.

Each test task shows a function with one bug in it. It also shows the tests the function must pass. The AI returns the fixed code.

## Where it comes from

The problems come from HumanEval, by OpenAI. People at OpenAI wrote each problem by hand, with a solution and tests.

HumanEvalFix is part of HumanEvalPack, by BigCode. Its authors wrote a bug by hand into each solution, so that the tests fail. They are Niklas Muennighoff, Qian Liu, Armel Zebaze, Qinkai Zheng, Binyuan Hui, Terry Yue Zhuo, Swayam Singh, Xiangru Tang, Leandro von Werra and Shayne Longpre.

This version uses the Python problems of HumanEvalPack.

## How an answer is checked

The problem's tests run on the AI's code. It passes when they all pass within 10 seconds. This is how the HumanEvalFix harness runs them.

## What it does not cover

- The problems are short and in English. They use only Python and its standard library.
- The AI sees the tests that check it. Code that only returns the tested values also passes.
- Each bug is one that an author chose to write. The bugs are not taken from real-world software.
- HumanEval and HumanEvalPack are public. Models may have seen their problems, bugs and solutions in training.

## Licence

This test set is free under the Apache License 2.0. HumanEvalPack is under the MIT License, copyright 2023 Muennighoff. HumanEval is under the MIT License. The notice that comes with the test set carries both.
