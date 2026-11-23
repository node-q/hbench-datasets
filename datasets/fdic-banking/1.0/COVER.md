## What this is

A test set on US banking data. Each of its 30 tasks asks for figures a bank analyst would work out from the FDIC's public yearly totals for insured institutions: return on assets, the net interest margin, loan quality, growth and consolidation over 92 years, state rankings, and checks of the tables against themselves. The tasks fall into ten kinds of work, such as profitability, asset quality and state rankings.

This is a draft. No bank analyst or accountant, and nobody at the FDIC, has checked the answers.

## Where the data come from

Every task reads the Federal Deposit Insurance Corporation's historical yearly totals for FDIC-insured institutions, as the summary endpoint of the FDIC's public BankFind Suite API returned them on 15 November 2026. There is one row for each year between 1934 and 2025, for each state, territory or totals row, and for each charter class: commercial banks since 1934, savings institutions since 1984. The AI also gets the FDIC's own definition of every field. We turned the JSON into CSV and changed no value. We kept the fields the FDIC documents, less two that no task needs, and dropped the ones it does not document. Amounts are in thousands of US dollars, as the definitions say. The data are totals and name no bank.

The FDIC makes no warranty about its data. It has not endorsed or sponsored this test set and is not affiliated with it.

## How the answers were worked out

We wrote the questions. Each states the years, the place, the charter class and the formula of every ratio it asks for. Each answer was worked out step by step with exact arithmetic. A second script, written in SQL and sharing no code with the first, recomputed every answer and agreed.

## What it does not cover

- Each ratio is the formula its question states, and averages are two-point averages of year-end amounts. These need not match the definitions behind the ratios the FDIC publishes, and a reader may prefer others.
- Nothing about a single bank. Regulatory capital ratios, risk-weighted assets, uninsured deposits and the deposit insurance fund are not in the data.
- Only FDIC-insured commercial banks and savings institutions. Credit unions and uninsured institutions are not included. State figures follow where institutions have their head office.
- The source has gaps and breaks. Total equity is zero in the commercial bank rows before 1984, and the national row is a separate series before 1984. The tasks work around these or ask about them.
- The tasks compute numbers. None asks whether a bank is in good health.
- The FDIC revises its figures. The answers are for the data as retrieved on 15 November 2026, with 2025 the last year.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The data and the field definitions are the FDIC's, and CC BY 4.0 does not cover them. The FDIC's website policies state no copyright notice or licence for its own data. Whether the data are free of copyright as a work of the US government has not been confirmed.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until bank analysts have reviewed it.
