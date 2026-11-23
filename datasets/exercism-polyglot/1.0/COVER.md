## What this is

This test set checks whether an AI can solve programming exercises in six languages. It has 210 test tasks, 35 each in C++, Go, Java, JavaScript, Python and Rust.

Each test task gives the AI an exercise as Exercism's course for that language ships it: the instructions, the starting files and the tests. The AI writes the solution.

## Where it comes from

The exercises are Exercism's. Exercism is a not-for-profit site where people learn programming for free. Its volunteers wrote each exercise's description, tests, starting files and example solution. Each test task names the exercise's authors and contributors as Exercism lists them.

The 35 exercises per language were chosen for this test set. The choice starts with the exercises that Aider's polyglot test found hardest, then adds others by difficulty and number of tests. Each has at least 5 tests. Food Chain is left out, because its song's lyrics are under copyright. So are four exercises whose starting files already pass every test.

## How an answer is checked

Every test of the exercise runs on the AI's solution, without internet access, in that language's environment. The test task passes when they all pass. The tests are the ones Exercism ships. Java's tests run without Gradle.

Exercism's own test runners and the solutions people published on exercism.org are not used.

## What it does not cover

- The exercises are short and in English. Each language has only 35, so a score for one language rests on few test tasks.
- The AI can read the tests that check it. Code written only to pass them also passes.
- The exercises and many solutions to them have been public for years. Models may have seen them in training.
- Scores are not comparable with other tests built from Exercism's exercises, such as Aider's, which use a different choice.
- Some tests use threads, timing or randomness. A slow or busy machine can change a close result.
- The exercises are practice puzzles and small data structures more than real-world software.

## Licence

This test set is free under the Apache License 2.0. The exercises are Exercism's, under the MIT License. The C++ exercises include Catch2, under the Boost Software License 1.0. The notice that comes with the test set carries these notices.
