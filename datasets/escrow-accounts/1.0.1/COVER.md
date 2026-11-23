## What this is

A test set on mortgage escrow accounts under US federal rules. Each of its 30 tasks states the facts of one unnamed borrower's escrow account, such as the bills it will pay, a balance and a date. The AI works out what Regulation X requires: the monthly escrow payment and its cushion, a surplus, shortage or deficiency and what the servicer must or may do about it, and the last day for an escrow statement, for answering a notice of error or a request for information, or for a notice before force-placed insurance. The tasks fall into ten kinds of work, such as the escrow analysis, surpluses and force-placed insurance.

This is a draft. No mortgage servicer, compliance practitioner or lawyer, and nobody at the Consumer Financial Protection Bureau, has checked the answers.

## Where the text comes from

The AI reads one document: Regulation X, the Consumer Financial Protection Bureau's rules under the Real Estate Settlement Procedures Act (12 CFR Part 1024), as the eCFR showed it for 12 November 2026. It gets section 1024.17 on escrow accounts, sections 1024.30, 1024.31 and 1024.34 to 1024.37, and appendix E, which sets out the arithmetic of an escrow analysis. We turned the XML into plain text and changed no words. The rest of Part 1024 is left out, with the definitions of section 1024.2 and the Bureau's official interpretations. The eCFR is an editorial compilation of the Code of Federal Regulations, not an official legal edition of it. This test set is not approved or endorsed by, or associated with, the Bureau.

## How the answers were worked out

We wrote the scenarios. They describe no real borrower, loan or servicer. Where the regulation leaves a detail open, such as how days are counted or which balance is the target at an annual analysis, the question states the convention it follows. One script computed every answer in exact cents, with an escrow analysis that reproduces every worked table of appendix E. A second script, sharing no code with the first, recomputed every answer and agreed. Both come from the same reading of the regulation, so they catch slips of arithmetic and counting, not a different reading. Amounts are accepted within a dollar or 0.1 percent, and must be exact where one cent decides the answer.

## What it does not cover

- It is not legal advice. A practitioner may read a convention the questions state differently.
- The Bureau's official interpretations (Supplement I) and the definitions of section 1024.2 are not given to the AI. Loss mitigation, servicing transfer notices and settlement costs are left out.
- Every amount divides evenly to the cent, because the regulation gives no rounding rule. Real escrow accounts need one.
- Biweekly payments, estimates that move with a price index and the terms of loan documents are left out. State law appears only as a fact a question states.
- The escrow items are property taxes and hazard and flood insurance, with dates between 2026 and 2028.
- The answers are for the regulation as it stood on 12 November 2026. It may be amended after that date.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulation's text is a work of the US government and has no copyright in the United States. Elsewhere its status may differ.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until mortgage servicers have reviewed it.

1.0.1 has the same 30 tasks as 1.0; only its short description changed.
