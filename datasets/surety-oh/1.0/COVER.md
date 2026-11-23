## What this is

A test set on rating contract surety bonds in Ohio. Each of its 47 tasks gives the AI one insurer's filed contract surety rate manual and states the facts in the question: the contractor's rate plan tier, the class of work, the contract price and how long the work will take. The AI works out exact values, such as a premium layered across the bands of the rate table, a surcharge for a long contract, a maintenance guarantee or a schedule rating credit held to Ohio's cap. The tasks fall into nine kinds of work, such as layered rates, contract price changes and checks of the manual itself.

This is a draft. No surety underwriter, and nobody at the insurer, has checked the answers.

## Where the text comes from

The AI reads one document: an insurer's Surety Contract Rate Manual, its countrywide contract surety rating plan as revised on 18 May 2026. It comes from a public rate filing in a state insurance department's public filing system and runs to 31 pages. We turned the filed PDF into text with pdftotext and changed nothing, so the page headers, the table layouts and the manual's own errors are as filed. The manual prints no edition or effective date of its own. On 6 November 2026 we checked in the filing system that the filing was in effect and that no later filing replaced it.

The manual names no company, person or contact. We searched every page for personal data and found none, so nothing in it is blacked out. The questions call the insurer [Company A], and nothing in the set names the insurer or its filing. The insurer has not reviewed or endorsed this test set, and we have no tie to it.

## How the answers were worked out

We wrote the questions. Their facts describe no real contractor, and every answer follows from the manual and those facts. Each answer was worked out by hand, step by step. A separate script then read every rate it needed from the cited page of the manual and recomputed all 170 graded fields. Every one matched. Each task grades 2 to 8 fields. Premiums the manual rounds to the dollar must match exactly, rates per $1,000 count within 0.001, and other money within $1 or 0.1%.

## What it does not cover

- Nobody in the trade has reviewed it: no surety underwriter, and nobody at the insurer. Where the manual is silent or unclear the questions stay away from it, but you may still disagree with a reading an answer key takes.
- Contract bonds only. The insurer's separate commercial surety manual is left out, and so are the filing's other attachments and any earlier revision of the plan.
- The tier is always given. No task works it out from a contractor's financial statements.
- Readings the manual leaves open are not asked: the Intermediate surcharge beyond 24 months, maintenance guarantees with more than one chargeable year, which of the manual's two maximum premiums applies, and extra work that crosses a rate layer.
- It is one insurer's countrywide plan, rated for Ohio risks. The text comes out of a PDF, so its lists in several columns are harder to read than on the page.
- It is not underwriting advice. Don't use it to rate real bonds.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source.

The rate manual is not ours, and CC BY 4.0 does not cover it. It is part of a public record filed with the Ohio Department of Insurance, but its text is still the insurer's copyright. We include it unchanged and do not license it to you. Nobody asked the insurer for permission.

## This version

1.0 is the first open version. Its 47 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until surety underwriters have reviewed it.
