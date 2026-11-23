## What this is

A test set on rating one insurer's farmowners program in Ohio. Each of its 86 tasks gives the AI the manual the insurer filed and states the facts in the question, such as a dwelling's county, its coverage form and its amount of insurance. The AI gives exact values: a county's zone, a dwelling or outbuilding premium, a credit, a farm liability charge, a deductible, or the stale pages and slips in the manual. The tasks fall into ten kinds of work, such as dwelling rating, farm liability and package rules.

This is a draft. No underwriter has checked the answers, and neither has the insurer.

## Where the text comes from

The AI reads two documents from one public rate filing for Ohio: the program's farm property and liability manual, effective 1 May 2026, and the filing's one-page actuarial memorandum. The memorandum cites three exhibits that are not in it. The manual's last page, an ISO rating plan, is left out. The filing was confirmed as filed and in effect, with nothing replacing it, on 6 November 2026.

We turned the filed PDFs into text and changed nothing but names and codes. Seven pages of the manual are scans, so their text is the PDF's own OCR, slips included. Every dwelling, outbuilding and blanket figure on those pages was checked against the manual's typed tables, and every scanned figure a task uses was read on the page itself.

The insurer reads [Company A]. Its programs, a data vendor and two state agencies read [Program A] to [Program E], [Vendor A], [State Agency A] and [State Agency B]. The insurer's form, endorsement and notice numbers are replaced by neutral codes (FORM-001 and on). Ohio county names are kept, because they set the zones. No key back to the real names is kept. A search of every page found no personal data.

## How the answers were worked out

We wrote the questions. They describe no real farm, and no application or submission was made up: the only documents are the insurer's own. Each answer was worked out step by step by hand from the manual. A separate script then read every table it needed from the text on its own and recomputed every answer, and all of them matched. The manual doesn't say whether a premium is rounded once or after each factor, so every premium with several steps was picked so that each way of rounding gives the same dollar. Each task grades 2 to 8 fields, 442 in all. Rounded premiums must match exactly, and rates per $100 count as right within 0.0005.

## What it does not cover

- Nobody in the trade has reviewed it: no underwriter, and not the insurer. Where the manual is silent or unclear, the tasks leave the question out, but you may still disagree with how an answer key reads the text.
- It is one insurer's farm program in Ohio, for small family farms and rural dwellings.
- Mobile home and earthquake premiums are not rated. Their only rate page is out of date, and it appears only in tasks that check the manual.
- Coverages rated from other manuals or from a vendor's cost indices are left out. Fire protection classes are given in the question.
- Values the manual leaves open are not asked, such as blanket farm property above the table's top amount, or acreage that falls exactly on the edge of a band.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source.

The filed manual and memorandum are not ours, and CC BY 4.0 does not cover them. They are public records filed with the Ohio Department of Insurance, but their text is still the filer's copyright, and we don't license it to you. Nobody asked the insurer for permission. We include them unchanged apart from the names and codes we replaced.

## This version

1.0 is the first open version. Its 86 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until underwriters have reviewed it.
