## What this is

A test set on Medicare supplement rates and refunds in Ohio, worked from the documents insurers file. Each of its 45 tasks gives the AI the text of one insurer's rate filing and another insurer's refund calculation, and states the facts in the question, such as an applicant's age, county, plan and way of paying. The AI works out exact values: a monthly rate, a discount, the step in rate at a birthday, a line of the rate increase exhibit, or whether a refund is due. Some tasks ask it to find the errors in the filings. The tasks fall into ten kinds of work, such as rating areas, implied relativities and the NAIC refund calculation.

This is a draft. No underwriter or actuary, and nobody at either insurer, has checked the answers.

## Where the text comes from

The AI reads three documents from two public filings by two insurers in Ohio's public filing system:

- one insurer's page of monthly rates for its modernized Medicare supplement plans, by plan, attained age, sex and area, with its areas by county (3 pages). It reads "Effective July 1, 2026", with rates "effective July 1, 2026 or later pending implementation".
- the actuarial memorandum of the same filing, dated 23 March 2026, with Exhibits I to VIII (52 pages).
- the other insurer's Medicare supplement refund calculation forms and the worksheets behind them for calendar year 2025, for Plans F, High Deductible F, G and N (9 pages).

On 6 November 2026 we checked in the filing system that both filings were filed and that no later filing replaced them. We turned the filed PDFs into text with pdftotext. The insurers made them in a spreadsheet, and some headings print over others, so the text shows them mixed together, as anyone reading the PDF's text would see them. Several tasks test reading through this. Otherwise the text is as filed, errors included, apart from these changes:

- Personal data is blacked out: the names of the actuaries and a telephone number.
- The two insurers, one more company the memorandum names and the state insurance department are replaced by labels that stay the same throughout: [Company A], [Company B], [Company C] and [State Agency A].
- The refund forms' company address and company codes are blacked out.
- The first insurer's policy form numbers become neutral codes, FORM-001 to FORM-017.

No figure a task uses was changed, and we keep no list that links a label or code to the real one. Neither insurer has reviewed or endorsed this test set, and we have no tie to them.

## How the answers were worked out

We wrote the questions. Their facts describe no real person, and every answer follows from the filed text and those facts. Each answer key was worked out from the text, with the cells and exhibit lines it needs typed by hand. A separate script then read every rate cell, the county lists, the memorandum's figures and exhibits and every line of the refund forms from the documents, recomputed all 208 graded answers and compared them with the keys. It also checked that no money answer falls within the margin of a cell one slip away, such as the next age, the other sex, another area or another plan.

## What it does not cover

- Nobody in the trade has reviewed it: no underwriter or actuary, and nobody at either insurer. Where the filings are silent or unclear, such as how the discounts stack, the questions stay away from them, but you may still disagree with a reading an answer key takes.
- One insurer's modernized plans and another insurer's refund forms, in one state, Ohio. Individual Medicare supplement only.
- The rates are the filed page for July 1, 2026. No task uses the rates in force before it or asks when a member's new rate starts. The refund calculation covers calendar year 2025 only, and its de minimis test is left out because it needs the premium in force, which the filing doesn't give.
- The headings printed over each other make the text harder to read than the page.
- It is not underwriting or actuarial advice. Don't use it to rate or refund real policies.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source.

The filed documents are not ours, and CC BY 4.0 does not cover them. They are public records filed with the Ohio Department of Insurance, but their text is still the insurers' copyright. We include them unchanged apart from the changes listed above, and we do not license them to you. For this open version, the credentials and job titles of people whose names were already withheld are removed as well. The refund forms and worksheets follow forms of an NAIC model regulation, which the NAIC publishes under its own copyright. Nobody asked the insurers or the NAIC for permission. The NAIC has not reviewed or endorsed this test set either.

## This version

1.0 is the first open version. Its 45 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until underwriters and actuaries have reviewed it.
