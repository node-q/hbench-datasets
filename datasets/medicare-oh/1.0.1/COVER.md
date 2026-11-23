## What this is

A test set on Ohio's Medicare Advantage and stand-alone Part D plans for contract year 2026, read from public files that CMS publishes. Each of its 52 tasks gives the AI extracts of four CMS files and states the facts in the question. Where a task needs a federal figure the files don't hold, such as the standard Part D deductible or the Part B premium, the question gives it. The AI gives exact answers: a premium component, a count of plans, a list of plan segments or counties, a star rating, an enrollment total, or a finding in the files themselves. The tasks fall into eleven kinds of work, such as premiums and how they are built, special needs plans and star ratings.

This is a draft. No underwriter, nobody at CMS and no plan sponsor has checked the answers.

## Where the data come from

Every file is real public data from the Centers for Medicare & Medicaid Services (CMS), all for contract year 2026, the year in effect when we downloaded them on 6 November 2026. Each is a free download from cms.gov with no login and no data use agreement:

- the Medicare Advantage and Part D landscape file, release of September 2026, cut to its 7,465 Ohio rows;
- Section D of the plan benefit package data for 2026, cut to the 212 rows of the plan segments the Ohio landscape lists;
- the 2026 star ratings summary, as CMS reissued it on 22 July 2026, cut to the 48 contracts in the Ohio landscape and turned from a spreadsheet into CSV, with its title row and empty columns dropped;
- the October 2026 enrollment by contract, plan, state and county, cut to the 33,830 Ohio rows of the same 48 contracts.

The plan sponsors submitted the plan data to CMS. No column was dropped, and no row was written or made up by us or by an AI. We replaced some values. Parent organization, brand, contract and plan names become labels that stay the same throughout ([Parent A], [Brand A], [Organization 01], [Plan 001] and so on). Three program and vendor names inside benefit labels become [Program A] to [Program C]. Contract IDs become made-up IDs, a Z and four digits, which no real contract uses, also inside plan and segment IDs, so rows still join across the files. We keep no list that links a label or an ID to the real one. Line endings differ too, and no file keeps a byte-order mark. Every other value is CMS's, unchanged. Each file is labelled as changed from CMS's data, not as CMS data.

The files hold no personal data. Enrollment is CMS's count by plan and county, and CMS shows every count of 10 or fewer as "*". We keep that: no task asks for or estimates a hidden count, and every enrollment total a task asks for adds up at least 10 listed counts.

## How the answers were worked out

We wrote the questions. They describe no real person. Each answer key was worked out step by step from the rows. A separate script read the shipped files again, answered every question with its own code and matched all 250 graded fields. Each task grades 2 to 8 fields. Money counts as right within a dollar or 0.1%, ratios within 0.005, and counts, flags, choices and lists only when exact.

## What it does not cover

- Nobody in the trade has reviewed it: no underwriter, nobody at CMS and no plan sponsor. You may disagree with a reading an answer key takes.
- One state in one contract year: 48 contracts of 19 parent organizations, and 222 plan segments. Employer group plans appear only in the enrollment data.
- Drug formularies, pharmacy networks, drug prices and every benefit section but Section D are left out, so no task asks about drug coverage, copays or supplemental benefits.
- No task estimates an enrollment count that CMS hides. Enrollment is the October 2026 report, and it changes every month.
- No task uses contract year 2027 data. Plans for 2027 replace these on 1 January 2027.
- It answers questions about the files only. Don't use it to choose or compare coverage.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. CMS's files are not ours, and CC BY 4.0 does not cover them. Their download pages and ReadMe files state no licence terms and no limits on use, and they are works of the US government. The plan sponsors submitted the plan data, and it stays theirs where any copyright applies. CMS and the plan sponsors have not reviewed or endorsed this test set, and we have no tie to them.

## This version

1.0 is the first open version. Its 52 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until underwriters have reviewed it.

1.0.1 has the same 52 tasks as 1.0; only its short description changed.
