## What this is

A test set on Florida's individual health plans for plan year 2026, read from public data that CMS publishes. Each of its 44 tasks gives the AI extracts of CMS's public use files and states the facts in the question, such as an age, a rating area or a county. The AI gives exact answers: a monthly rate, a tobacco load, a count, a list of plans or counties, or a finding in the data itself. The tasks fall into ten kinds of work, such as rates by plan, rating area and age band, service areas and cost sharing.

This is a draft. No underwriter, nobody at CMS and no issuer whose plans are in the files has checked the answers.

## Where the data come from

Every file is real public data: extracts of three of the Health Insurance Exchange public use files that the Centers for Medicare & Medicaid Services (CMS) publishes for plan year 2026, the Rate, Plan Attributes and Service Area files, as CMS last updated them on 10 August 2026. We downloaded them on 6 November 2026. The issuers submitted the rates and plan data in them to CMS. The extracts keep Florida's rows: 2,201 rows of the Plan Attributes file and 649 of the Service Area file. Florida has 567,681 rows in the Rate file, too many to ship whole, so a task that needs rates gets only the rate rows it uses. No column was dropped, and no row was written or made up by us or by an AI.

Issuer and brand names are replaced by labels that stay the same throughout, one per brand ([Company A] to [Company W]). Product lines get labels of their own ([Program A] to [Program K]), and so does a health system named in plan and service area names that is not an issuer. Company web addresses are blacked out. Issuer IDs become stand-in numbers, also inside plan IDs, so rows still join across the files. We keep no list that links a label or a stand-in number to the real one. Line endings differ too, and the Plan Attributes file has lost the byte-order mark it starts with. Every other value is CMS's, unchanged. The files hold no personal data, and the finest place they name is a county.

CMS's terms say: "The user may not present or otherwise reference data that have been altered in any way as CMS data." So every file is labelled as changed from CMS's data, and we, not CMS, answer for the changes. CMS asks to be cited as: Centers for Medicare & Medicaid Services. (2025). 2026 Health Insurance Exchange Public Use Files (Rate PUF; Plan Attributes PUF; Service Area PUF) [Data file and code book]. Retrieved from http://www.cms.gov/CCIIO/Resources/Data-Resources/marketplace-puf.html

## How the answers were worked out

We wrote the questions. They describe no real person. Each answer key was worked out step by step from the rows. A separate script read the shipped files again, answered every question with its own code and matched all 250 graded fields. Each task grades 3 to 8 fields. Rates count as right within $1 or 0.1%, loads and ratios within 0.0005, and plan IDs, counts and lists only when exact, so a neighbouring plan with a similar rate can't pass.

## What it does not cover

- Nobody in the trade has reviewed it: no underwriter, nobody at CMS and no issuer. Where the files alone don't settle a question, the tasks leave it out or define it in the question, but you may disagree with a reading an answer key takes.
- One state's individual market in one plan year. One brand files 116 of the 410 individual medical plans.
- No task asks about the second-lowest-cost silver plan, premium tax credits, the age curve, or benefits beyond the Plan Attributes file.
- A household total is the sum of each person's listed rate, as each question defines it. It is not a premium under the federal rules for families.
- CMS updates these files during the year, and the extracts may differ from what HealthCare.gov shows. CMS has since published files for plan year 2027, and this set holds no 2027 data.
- It answers questions about the files only. Don't use it to choose, quote or price coverage.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. CMS's files are not ours, and CC BY 4.0 does not cover them. The issuers submitted the plan data, and it stays theirs where any copyright applies. If you pass the files on, CMS's terms still apply: changed data may not be presented as CMS data. CMS and the issuers have not reviewed or endorsed this test set, and we have no tie to them.

## This version

1.0 is the first open version. Its 44 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until underwriters have reviewed it.
