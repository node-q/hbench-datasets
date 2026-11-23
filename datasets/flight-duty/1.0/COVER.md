## What this is

A test set on pilots' flight and duty limits under US rules. Each of its 30 tasks gives one unnamed pilot's schedule, and the AI checks it the way a crew scheduler would. It picks the right table, row and column, keeps local clock times in different time zones apart, tells a flight duty period from other duty and from rest, counts look-back windows to the minute, and spots which condition of a rule fails. The tasks fall into ten kinds of work.

This is a draft. No crew scheduler, pilot, dispatcher, aviation lawyer or FAA official has checked the answers.

## Where the text comes from

The AI reads one document: 14 CFR Part 117, the FAA's flight and duty limitations and rest requirements for flightcrew members, with Tables A, B and C, as the eCFR showed it on 12 November 2026. We turned the XML into plain text, changed no words and kept every table cell in order. The eCFR is an editorial compilation, not the official legal edition. This test set is not approved or endorsed by the FAA.

## How the answers were worked out

We wrote the scenarios. They describe no real person, airline or flight, and name no airline, airport or person. Every answer follows from the text and the facts in the question. Where the rule leaves room for reading, the question states the reading. Each answer was computed in exact minutes, and a second script, sharing no code with the first, recomputed every answer and agreed. Both come from the same reading of the text, so they catch slips of arithmetic, not a different reading of a rule. The rule gives no worked examples, so beyond its tables the readings could only be checked against its wording.

## What it does not cover

- US rules only, for passenger flights under Part 121, as they stood on 12 November 2026. The eCFR shows no change to the part since at least January 2017, but the rules may change.
- Only the words of Part 117 and the readings the questions state. The FAA's legal interpretations, the rule's preamble and its clarifications were not used and may read a provision differently.
- Calls that need judgement are not asked, such as fitness for duty or whether a circumstance was unforeseen. Where a task needs one, the question says what to assume.
- Fatigue risk management systems, training, emergency and government operations, the limits for a pilot who is not acclimated, and situations the text does not settle are left out.
- The scenarios sit close to the limits on purpose, much closer than ordinary schedules. Two to four tasks for each kind of work show where an AI stands. They can't separate two close results.
- It is not operational or legal advice. Nobody should schedule or fly from these answers.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulation's text is a work of the US government and has no copyright in the United States.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until crew schedulers have reviewed it.
