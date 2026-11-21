## What this is

This test set checks whether an AI can reason about what code does. It has 800 test tasks.

Each test task shows a short Python function and an output. The AI must find an input that makes the function return that output.

## Where it comes from

It is the input prediction part of CRUXEval. CRUXEval is by Alex Gu, Baptiste Rozière, Hugh Leather, Armando Solar-Lezama, Gabriel Synnaeve and Sida I. Wang, at Meta.

Meta's Code Llama 34B model wrote the functions and their inputs. The authors ran each function to get its output. They kept problems that a good programmer should solve in about a minute. They then picked 800 of them at random.

The output prediction part of CRUXEval is left out. An AI that can run Python could answer it by running the function.

## How an answer is checked

The AI's call runs against the function. It passes when the result equals the given output within 3 seconds. This is how CRUXEval checks it.

## What it does not cover

- All the functions are short. They use only Python and its standard library.
- One model wrote all the functions. They are more like puzzles than real-world code.
- The AI can run Python, so it can try inputs until one works. Its score is not comparable with CRUXEval scores of models that answer without running code.
- CRUXEval has been public since 2024. Models may have seen its problems in training.

## Licence

This test set is free under the Apache License 2.0. CRUXEval itself is under the MIT License, copyright 2023 Meta. The notice that comes with the test set carries both.
