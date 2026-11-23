## What this is

A test set on flood insurance in Louisiana, built on FEMA's public data on the National Flood Insurance Program (NFIP). Each of its 54 tasks gives the AI some of FEMA's files and asks for exact figures, the way a claims analyst would work them out. The AI has to read FEMA's codes with FEMA's dictionary, tell an empty field from a zero, keep building, contents and compliance payments apart, count insured units rather than rows, and spot rows that contradict their own fields. The tasks fall into fifteen kinds of work, such as claim payments and repetitive loss. The tasks lean on what is Louisiana's own: named storms such as Katrina, Rita, Ida and Francine, the levee-protected A99 zone and the coastal V zones, tidal overflow as a cause of loss, compliance claims after Katrina, tens of thousands of properties with repeated losses, and communities sanctioned for not taking part in the program.

This is a draft. No claims analyst, and nobody at FEMA, has checked the answers.

## Where the data come from

Every file is real public data that FEMA publishes through OpenFEMA, its open data service: NFIP claims, NFIP policies, properties with repeated flood losses, the NFIP Community Status Book and residential penetration rates, with FEMA's field dictionary for every column kept. No row was written or made up by us or by an AI. We fetched the files on 6 November 2026. Claims and policies are as FEMA held them on 8 September 2026, the repetitive loss properties on 21 October 2026 and the penetration rates on 3 August 2026, and the community rows were last refreshed on 25 August 2026 (two of them on 18 September 2026). Policies are only those effective in 2024 and 2025, 833,277 Louisiana rows.

The files are extracts. We kept some rows and dropped whole columns: exact location, ZIP code, city, community names and numbers, map panels, record numbers and exact construction and purchase dates. Every value kept is FEMA's own, unchanged, but the files are not FEMA's data as published. FEMA's data already leave out who the policyholders are, and they name no person or company. Nothing finer than a parish and a flood zone is left.

FEMA asks for this notice: "This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s)."

FEMA's name appears because its terms ask for the citation. No FEMA or DHS logo or seal is used.

## How the answers were worked out

We wrote the questions. Each one states its facts, such as a parish, a year, a date or a definition, and covers a group of at least ten rows. None asks about a single claim, policy or property, and figures from different files are combined only as parish or state totals.

One script worked out every answer step by step from the rows supplied. A second script loaded the same files into a database and answered every question again in SQL. All 302 graded fields matched, and so did the size of every group. Each task grades 2 to 8 fields. Money counts as right within $1 or 0.1%, shares and ratios within 0.0005, and counts and codes only when exact.

## What it does not cover

- Nobody in the trade has reviewed it: no claims analyst, and nobody at FEMA. Where FEMA's definitions are unclear, the question gives its own, and you may disagree with it.
- Louisiana only, and only a few parishes. Claims span the years 1978 to 2026, most of them from Hurricane Katrina in 2005, and older claims are less completely recorded.
- Policies are only those effective in 2024 and 2025, rated under Risk Rating 2.0, for five parishes. Every policy task says which year it uses.
- It is a snapshot: claims and policies as FEMA held them in September 2026, repetitive loss properties in October 2026. Recent claims may still grow, claims of 2026 are left out, and the answers hold for the files supplied.
- No question asks about the program's current rules, puts a value on Community Rating System discounts, or uses the old rating fields, water depth or earned premium. None asks about a group of fewer than ten rows.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. FEMA's data are a work of the US government and have no copyright in the United States. FEMA's terms say nobody may use the files to re-identify, or try to re-identify, any person or property.

## This version

1.0 is the first open version. Its 54 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until claims analysts have reviewed it.
