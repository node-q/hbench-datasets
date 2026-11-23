## What this is

A test set on general liability ratemaking, built on one real rate filing made in Ohio. Each of its 27 tasks gives the AI the filed documents as text and asks it to redo part of the insurer's rate indication exactly, the way an actuary reviewing the filing would. The tasks fall into nine kinds of work, such as development factors, ultimate losses, trend and Ohio's loss cost multiplier. Some ask where the exhibits disagree with each other or with their own notes.

This is a draft. No actuary has checked the answers, and neither has the insurer.

## Where the text comes from

The AI reads three documents of one general liability rate filing, taken from a public filing system: the insurer's countrywide rate indication with its ten exhibits, its Ohio adoption form with the loss cost multiplier calculation, and its Ohio manual exception page. The filing was confirmed as filed and in effect, with nothing replacing it, on 6 November 2026. We also add a short index page of our own that lists the documents and the indication's pages.

We turned the filed PDFs into text and changed nothing but names and identifiers. The insurer reads [Company A], and its address, company code and a document code in a page footer are replaced by markers. The one person named, on the adoption form, is removed along with a phone number. No key back to the real names is kept. The filing names no policyholder or claimant.

The indication prints development factors from ISO, and its notes cite an ISO circular. Those figures may be ISO's copyright.

## How the answers were worked out

We wrote the questions. Every answer follows from the filing's printed numbers and the formulas it states. A script read the triangles and exhibits, computed every answer and checked that each value the filing prints is marked right and each tempting wrong value is marked wrong. Each answer was then written out step by step against the printed cells and notes. No second script or person has recomputed them yet. Where the filing picks a value itself, such as a tail factor or a trend, a task asks for the value it picked or the arithmetic behind it, never for a choice of its own. The disagreements the review tasks ask about were each checked number by number. They are what the documents contain, and they say nothing about whether the insurer's rates are right.

## What it does not cover

- No actuary has reviewed it, no second solver has checked it, and the insurer has not reviewed or endorsed it.
- It is one filing from one insurer: small commercial risks, mostly construction, at one evaluation date (30 September 2025), with one state's multiplier. Every task uses the same eighteen pages, so a result shows care with this indication and says little about other filings.
- A few printed figures can't be reproduced from the filing alone, and no task asks for them.
- Ratios the filing prints in whole percent count as right within half a percentage point.
- The documents are plain text from PDFs. Wide tables run past a page, and empty cells are blank space, as in the filed pages.

## Licence

Our tasks, questions, answer keys and index page are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source.

The filed documents are not ours, and CC BY 4.0 does not cover them. They are public records filed with the Ohio Department of Insurance, but their text is still the filer's copyright, and we don't license it to you. The ISO development factors in the indication may also be ISO's copyright. Nobody asked the insurer or ISO for permission. We include the documents unchanged apart from the names and identifiers we replaced. For this open version, the credentials and job titles of people whose names were already withheld are removed as well. The insurer's name is replaced, but it may still be identifiable from the documents.

## This version

1.0 is the first open version. Its 27 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until actuaries have reviewed it.
