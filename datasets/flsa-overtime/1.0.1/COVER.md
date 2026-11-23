## What this is

A test set on overtime pay under US federal law. Each of its 30 tasks describes one workweek of an unnamed employee. The AI works out what the Department of Labor's overtime regulation says is owed: the regular rate, the overtime due, a bonus or commission spread back over the weeks it was earned in, or whether a payment counts toward the regular rate at all. The tasks fall into ten kinds of work, such as hourly pay, piecework and a salary for hours that vary.

This is a draft. No payroll specialist, wage and hour lawyer or Department of Labor official has checked the answers.

## Where the text comes from

The AI reads one document: 29 CFR Part 778, the Department of Labor's regulation on overtime pay under the Fair Labor Standards Act, as the eCFR showed it on 12 November 2026. We turned its XML into plain text and changed no words. The eCFR is an editorial compilation, not the official legal edition. This test set is not approved, endorsed or sponsored by the Department of Labor, the Office of the Federal Register or the Government Publishing Office.

## How the answers were worked out

We wrote the scenarios. They describe no real person or employer. Every answer follows from the regulation and the facts in the question. One script computed the answers with rules that reproduce the regulation's own worked examples. A second script, sharing no code with the first, recomputed every answer and agreed. Both come from the same reading of the text, so they catch slips of arithmetic, not a different reading of a rule. Rates are rounded to the cent, as the regulation's examples round them, and amounts are accepted within a small margin.

## What it does not cover

- US federal rules only, from one regulation as it stood on 12 November 2026. Part 778 is the Department's reading of the Act, not the Act itself, and it was last amended in November 2022. State and local law are left out.
- Every task uses the 40-hour week, except one on the daily and weekly standards of section 7(b).
- Part 778 sets no minimum wage, so no task needs one. Questions that need a person's call, such as whether a bonus is discretionary, are given as facts.
- The alternative methods of section 7(g) and the 14-day period of section 7(j) are left out.
- Some rules have no worked example in the text, such as spreading a quarterly bonus or a prize. Those answers rest on the general rule and on how the text handles commissions, which is weaker ground.
- The scenarios are simple on purpose and are not a sample of real payrolls. Two to four tasks for each kind of work show where an AI stands. They can't separate two close results.
- It is not legal advice.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulation's text is a work of the US government and has no copyright in the United States.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until payroll specialists have reviewed it.

1.0.1 has the same 30 tasks as 1.0; only its short description changed.
