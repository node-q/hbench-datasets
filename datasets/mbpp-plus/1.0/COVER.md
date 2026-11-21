## What this is

This test set checks whether an AI can write a correct Python function from a short description. It has 378 test tasks.

Each test task gives a description of a function and an example of its use. The AI writes the function.

## Where it comes from

The problems come from MBPP, by Jacob Austin and others at Google Research. Crowd workers wrote the problems, their solutions and their tests. The authors then checked a part of them by hand.

MBPP+ is by Jiawei Liu, Chunqiu Steven Xia, Yuyao Wang and Lingming Zhang, of the EvalPlus project. They chose and revised 378 of the checked problems. They added many more test inputs to each one.

This version is made from the MBPP+ v0.2.0 release. Five of the extra inputs of one problem, Mbpp/255, are left out.

## How an answer is checked

The AI's function runs on the original inputs and on the extra ones. Its results are compared with those of the reference solution. This is how EvalPlus checks it.

## What it does not cover

- The problems are short and in English. They use only Python and its standard library.
- They are entry-level string, list and arithmetic exercises. They are not real-world software work.
- MBPP has been public since 2021. Models may have seen its problems and solutions in training.
- Time limits are measured against the reference solution on the machine that runs the check. A slow or busy machine can change a close result.

## Licence

This test set is free under the Apache License 2.0. MBPP+ is also under the Apache License 2.0. MBPP is under the Creative Commons Attribution 4.0 International licence. The notice that comes with the test set carries both, with the changes made.
