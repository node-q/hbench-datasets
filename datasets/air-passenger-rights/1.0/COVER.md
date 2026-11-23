## What this is

A test set on the rights of air passengers under US federal rules. Each of its 30 tasks describes one passenger's problem with an unnamed airline. The AI works out what the Department of Transportation's rules say the airline owes: whether a passenger bumped from a flight is owed compensation and how much, whether a schedule change counts as significant, what must be refunded and by which date, when a delayed bag's fee comes back, and what a tarmac delay or a travel credit requires. The tasks fall into ten kinds of work, such as refund deadlines, baggage liability and tarmac delays.

This is a draft. No customer support specialist, no lawyer and nobody at the Department of Transportation has checked the answers.

## Where the text comes from

The AI reads five parts of Title 14 of the Code of Federal Regulations, the Department of Transportation's consumer protection rules for air passengers: Part 250 on oversold flights, Part 254 on domestic baggage liability, Part 259 on enhanced protections for passengers, Part 260 on refunds of fares and extra fees, and Part 262 on travel credits when a serious communicable disease keeps someone from flying. The text is as the eCFR showed it for 12 November 2026. We turned its XML into plain text and changed no words. The eCFR is an editorial compilation, not the official legal edition. This test set is not approved or endorsed by, or associated with, the Department of Transportation, the Office of the Federal Register or the Government Publishing Office.

## How the answers were worked out

We wrote the scenarios. Each one gives a fare, flight times, dates and what was paid and how, and names no airline, airport operator or person. Every answer follows from the rules and the facts in the question. Each answer was worked out step by step from the rules. A second script, sharing no code with the first, recomputed every graded field from the questions and the text and agreed on all of them. Both come from the same reading of the text, so they catch slips of arithmetic, not a different reading of a rule.

## What it does not cover

- US federal rules only, as the text stood on 12 November 2026. The five parts were last amended between June 2024 and July 2026, and they may change again. It is not legal advice.
- The answers apply the words of the rules alone. Statutes, treaties, the Department's guidance, enforcement practice and airlines' contracts of carriage are left out.
- In every scenario one airline sold the ticket and flew every flight. Tickets sold by someone else, trips on several airlines and partly used tickets are left out.
- Also left out: the inflation adjustments of the dollar limits, the refund owed for a seat in a cheaper class, the 24-hour hold or cancellation rule, complaint response times and flight status notices.
- Rules that leave the call to a person, such as what counts as adequate food or comparable transport, are not asked about.
- The questions state conventions the text does not spell out, such as how periods of days and years are counted and which Federal holidays fall in a period. Another reader may count differently.
- The scenarios are cut down to the facts the rules need and are not a sample of real complaints. Each kind of work has only three, enough to show where an AI stands. They can't separate two close results.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulations' text is a work of the US government and has no copyright in the United States. Elsewhere its status may differ.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until customer support specialists have reviewed it.
