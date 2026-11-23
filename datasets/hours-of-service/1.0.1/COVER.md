## What this is

A test set on drivers' hours under US federal rules. Each of its 30 tasks gives one unnamed driver's log, and the AI checks it the way a fleet compliance manager would. It tells consecutive hours from accumulated hours and driving from other work, finds the first minute of driving that is not allowed and the limit that forbids it, notices a rest that is ten minutes short, and applies an exception only when every condition is met. The tasks fall into ten kinds of work.

This is a draft. No fleet compliance manager, transport lawyer, enforcement officer or official of the Federal Motor Carrier Safety Administration has checked the answers.

## Where the text comes from

The AI reads one document: subpart A of the Federal Motor Carrier Safety Administration's hours-of-service rules, 49 CFR Part 395, as the eCFR showed it on 12 November 2026. We turned the XML into plain text and changed no words. We left out subpart B, on electronic logging devices. The two log grids drawn in subpart A are not included; the paragraph that describes the sample day in words is. The eCFR is an editorial compilation, not the official legal edition. This test set is not approved, endorsed or sponsored by the Federal Motor Carrier Safety Administration or the Department of Transportation.

## How the answers were worked out

We wrote the scenarios. Each log is part of the question, not a real driver's log, and drivers and carriers are unnamed. Every answer follows from the text and the facts in the question. One script applied the rules to every minute of the log. A second script, sharing no code with the first, worked on whole stretches of time, recomputed every answer and agreed. Both come from the same reading of the text, so they catch slips of arithmetic, not a different reading of a rule. The text gives no worked example of a limit, so the readings could only be checked against its wording.

## What it does not cover

- US federal rules only, for interstate drivers outside Alaska and Hawaii, as they stood on 12 November 2026. The rules may change.
- Only the words of the regulation. The agency's guidance, interpretations and enforcement practice were not used and may differ.
- Each question states how to settle points the text leaves open, such as where a 7 or 8 day period starts. You may disagree with a stated reading.
- Most tasks are on trucks carrying goods, three are on passenger carriers, and every scenario is in one time zone in February 2026. The logs are consistent, but nobody has checked that they look like real operations.
- Points the text does not settle are left out, such as chains of more than two rest periods, with industry exceptions other than short-haul, emergencies, several carriers in one day, and how a log must be kept or corrected.
- Two to four tasks for each kind of work show where an AI stands. They can't separate two close results.
- It is not legal advice. Don't use it to decide whether a real driver may drive.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulation's text is a work of the US government and has no copyright in the United States.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until fleet compliance managers have reviewed it.

1.0.1 has the same 30 tasks as 1.0; only its short description changed.
