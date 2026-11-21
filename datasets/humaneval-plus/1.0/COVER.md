## What this is

This test set checks whether an AI can write a correct Python function from a short description. It has 164 test tasks.

Each test task gives a function's signature and its description. The AI writes the function.

## Where it comes from

The problems come from HumanEval, by OpenAI. People at OpenAI wrote each problem by hand, with a solution and tests.

HumanEval+ adds many more test inputs to each problem. It is by Jiawei Liu, Chunqiu Steven Xia, Yuyao Wang and Lingming Zhang, of the EvalPlus project. They also fixed several of the original solutions.

This version is made from the HumanEval+ v0.1.10 release.

## How an answer is checked

The AI's function runs on the original inputs and on the extra ones. Its results are compared with those of the reference solution. This is how EvalPlus checks it.

## What it does not cover

- The problems are short and in English. They use only Python and its standard library.
- They are mostly string, list and arithmetic puzzles. They are not real-world software work.
- HumanEval has been public since 2021. Models may have seen its problems and solutions in training.
- Time limits are measured against the reference solution on the machine that runs the check. A slow or busy machine can change a close result.

## Licence

This test set is free under the Apache License 2.0. HumanEval+ is also under the Apache License 2.0. HumanEval is under the MIT License. The notice that comes with the test set carries both.
