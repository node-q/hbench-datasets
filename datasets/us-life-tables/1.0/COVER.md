## What this is

A test set on the work an actuary does with a life table. Each of its 30 tasks gives the AI all 36 published United States life tables for 2023 and 2024, and the AI has to choose the right one before it works anything out. The answers are probabilities of survival and death, expectations of life, values at fractional ages and for two lives, insurance and annuity values, net premiums and reserves. Other tasks rebuild one column of a table from another, compare tables, or check a table against itself. The tasks fall into ten kinds of work.

This is a draft. No actuary, demographer or anyone at the National Center for Health Statistics has checked the questions, the conventions they state or the answers.

## Where the data come from

The AI reads the complete period life tables that the National Center for Health Statistics published with two National Vital Statistics Reports: United States Life Tables, 2024 and United States Life Tables, 2023. There are 18 tables a year: the total population, males and females, and the same three for the Hispanic population and for the non-Hispanic American Indian and Alaska Native, Asian, Black and White populations. Each follows 100,000 births of a made-up group through one year's death rates, so the tables name no person.

We downloaded the 36 spreadsheets on the agency's file server on 15 November 2026 and wrote each one out as a plain CSV file. No value and no wording changed. The title and notes above and below each table are quoted in every question instead of sitting in the file. We compared all 21,816 figures the reports print with the stored values, rounded to the printed precision, and every one agreed.

Source: Centers for Disease Control and Prevention, National Center for Health Statistics, National Vital Statistics System. Arias E, Xu JQ, Tejada-Vera B. United States life tables, 2024. Natl Vital Stat Rep. 2026 Aug;75(5):1–64. Arias E, Xu JQ, Kochanek K. United States life tables, 2023. Natl Vital Stat Rep. 2025 Jul 15;74(6):1–63. The life tables are available on the agency's website for no charge. This use of the material does not imply endorsement by CDC, ATSDR, HHS or the United States Government.

## How the answers were worked out

We wrote the questions. Each one states its facts, formulas and conventions, including the interest rate and how to treat ages 100 and over, so that only one answer follows. Every answer was worked out step by step. One script computed the answer keys with exact fractions from the files. A second script, sharing no code with the first, recomputed all 141 checked fields in ordinary floating point and agreed with every one. Dollar amounts are accepted within a dollar or 0.1%, and probabilities and factors within a small stated margin.

## What it does not cover

- Where actuaries use more than one convention, such as for the last age group, fractional ages or when payments fall, the question picks one. A practitioner may prefer another.
- These are period life tables of the whole population. They are not tables of insured lives, they have no select period and they don't project future mortality. The insurance and annuity values are exercises on population mortality, not prices.
- United States mortality in 2023 and 2024 only. The reports' text and their other tables are left out.
- The files are the tables as the agency's server held them on 15 November 2026. The National Center for Health Statistics may revise a table, and the answers are for the files included.
- The stored values carry about seven significant digits, so the columns of a table agree with each other only roughly. Tasks that compare columns do it at the printed precision or with a stated threshold.
- The tables by Hispanic origin and race rest on death rates the agency adjusted for errors on death certificates, as the tables' notes say. The tasks take the tables as published.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The life tables are a work of the US government. A work of the US government has no copyright protection in the United States (17 U.S.C. 105). That covers only what the federal government wrote, and only in the United States. The reports say their material is in the public domain and ask to be cited, and the agency asks for the credit and the statements given above.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until actuaries have reviewed it.
