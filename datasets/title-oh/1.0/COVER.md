## What this is

A test set on rating title insurance in Ohio. Each of its 56 tasks gives the AI the schedule of rates that a title insurance rating organization filed, and states the facts in the question, such as the kind of policy, the amount of insurance or the age of a prior policy. The AI works out exact values: an owner's or loan premium by band, the minimum that applies, a reissue, refinance or simultaneous issue rate, an endorsement premium, or a figure in the actuarial memorandum. Some tasks ask it to find the errors in the filed pages. The tasks fall into eleven kinds of work, such as premiums by band, endorsements and the memorandum.

This is a draft. No title underwriter, and nobody at the rating organization, has checked the answers.

## Where the text comes from

The AI reads fifteen documents from two public rate filings in a state insurance department's public filing system. The first filing holds the 107-page schedule of rates, effective for orders received on or after 1 January 2026, seven of its rate pages, the January 2026 revision of the simultaneous issue rule and the actuarial memorandum as revised after the regulator's objections. The second, later filing adds the rate pages of three endorsements and three manual pages. On 6 November 2026 we checked in the filing system that both filings were in effect and that no later filing replaced them.

We turned the filed PDFs into text with pdftotext. Three manual pages are scans, so their text comes from OCR, checked against the scans, with the misread words put right and nothing else changed. Two scanned pages of the memorandum have no text and no task uses them. Otherwise the text is as filed, errors included, apart from these changes:

- Personal data is blacked out: the name and credentials of the memorandum's signer, and the names of two public officials on the regulator's letterhead.
- Names are replaced by labels that stay the same throughout. The rating organization is [Company A] and the state regulator [State Agency A]. Its 31 member insurers, two data vendors and three filing numbers get labels of their own.
- Addresses, phone and fax numbers, web addresses and a vendor's job code are replaced by markers.
- The rating organization's own form numbers become neutral codes, FORM-001 to FORM-126, and a code in one page footer is blacked out.

We keep no list that links a label or code to the real name. The rating organization has not reviewed or endorsed this test set, and we have no tie to it.

## How the answers were worked out

We wrote the questions. Their facts describe no real insured, and every answer follows from the filed text and those facts. Each answer key was worked out from the text. A separate script then read every rate, minimum and printed figure from the files and recomputed all 228 graded fields. It agreed with every key. Each task grades 3 to 7 fields. Amounts of insurance and counts must match exactly, and premiums count as right within $1 or 0.1%.

## What it does not cover

- Nobody in the trade has reviewed it: no title underwriter, and nobody at the rating organization. Where the filings are silent or unclear the questions stay away from them, but you may still disagree with a reading an answer key takes.
- One rating organization's schedule in one state, Ohio, and mostly residential owner's and loan policies.
- Rules whose wording leaves the answer open are not rated. Among them are several endorsements whose filed pages carry the page numbers of other manual pages.
- The rates in force before this filing, the text of ALTA's forms, the Ohio Revised Code and the charges the insurer may set at its discretion are not used.
- It is not underwriting advice. Don't use it to rate real policies.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source.

The filed documents are not ours, and CC BY 4.0 does not cover them. They are public records filed with the Ohio Department of Insurance, but their text is still the rating organization's copyright. We include them unchanged apart from the changes listed above, and we do not license them to you. For this open version, the credentials and job titles of people whose names were already withheld are removed as well. Nobody asked the rating organization for permission. Its name is replaced, but it may still be identifiable from the documents. None of the text of ALTA's policy or endorsement forms is included.

## This version

1.0 is the first open version. Its 56 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until title underwriters have reviewed it.
