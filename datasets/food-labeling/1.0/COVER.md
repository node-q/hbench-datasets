## What this is

A test set on US nutrition labeling. Each of its 30 tasks describes an unnamed food through its lab values, product category, serving and package. The AI applies the Food and Drug Administration's labeling rules the way a regulatory specialist would: it rounds each nutrient by its own range and step, picks the right Daily Value, works out serving sizes from reference amounts, chooses the label format, and tests a nutrient content claim against its exact limits. The tasks fall into ten kinds of work, such as declared values, calories and compliance tolerance.

This is a draft. No regulatory specialist and nobody at the Food and Drug Administration has checked the answers.

## Where the text comes from

The AI reads eight sections of 21 CFR Part 101, the Food and Drug Administration's food labeling regulations: nutrition labeling (101.9), reference amounts customarily consumed (101.12), and the nutrient content claims of 101.13, 101.54, 101.56, 101.60, 101.61 and 101.62. The text is as the eCFR showed it for 12 November 2026. We turned its XML into plain text and changed no words. The 14 pictures of sample labels are not reproduced, and one paragraph of 101.9 on publications incorporated by reference is left out; no task needs either. The eCFR is an editorial compilation, not the official legal edition. This test set is not approved or endorsed by, or associated with, the Food and Drug Administration.

## How the answers were worked out

We wrote the scenarios. The foods are made up, and their lab values are facts in the question, not measurements of real products. Every answer follows from the text and those facts. Each answer was worked out step by step in exact fractions from the lines of the regulation. A second script, sharing no code with the first, recomputed every graded field from the questions and the text and agreed on all of them. Both come from the same reading of the text, so they catch slips of arithmetic, not a different reading of a rule.

## What it does not cover

- It is not regulatory or legal advice. FDA guidance outside the text was not used.
- US federal rules only, for packaged foods of the general food supply, as the text stood on 12 November 2026. Section 101.9 was last amended in May 2023 and section 101.13 in April 2025, and the rules may change.
- Numeric rules only. Where the regulation leaves a choice to the manufacturer, the question makes it. A claim is tested on actual amounts and on its numbers alone, with every other condition taken as met. A regulatory specialist may think a different choice more usual.
- Where the regulation does not decide, such as an exact tie in rounding, cholesterol between 2 and 5 mg or the amounts of vitamins and minerals in mcg or mg, no task asks.
- Left out: "more", "fortified" and "added" claims, health claims and the "healthy" claim, protein's percent Daily Value, meal and main dish products, dietary supplements and foods for infants.
- Questions that need someone to weigh the facts, such as whether a reference food is appropriate, are not asked.
- Each kind of work has only two to four questions, enough to show where an AI stands. They can't separate two close results.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulations' text is a work of the US government and has no copyright in the United States. Elsewhere its status may differ.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until regulatory specialists have reviewed it.
