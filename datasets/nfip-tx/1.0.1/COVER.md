## What this is

A test set on flood insurance in Texas, built on FEMA's public data on the National Flood Insurance Program (NFIP). Each of its 52 tasks gives the AI some of FEMA's files and asks for exact figures, the way a claims analyst would work them out. The AI has to read FEMA's codes with FEMA's dictionary, tell an empty field from a zero, keep building, contents and compliance payments apart, count insured units rather than rows, and spot rows that contradict their own fields. The tasks fall into twelve kinds of work, such as claim payments and repetitive loss. Hurricane Harvey, Hurricane Beryl and the July 2025 Central Texas flood are among the events. Several tasks compare coastal and inland counties. The question then lists the eighteen counties of the Texas coastal zone and calls every other county inland.

This is a draft. No claims analyst, and nobody at FEMA, has checked the answers.

## Where the data come from

Every file is real public data that FEMA publishes through OpenFEMA, its open data service: NFIP claims, NFIP policies, properties with repeated flood losses, the NFIP Community Status Book and residential penetration rates, with FEMA's field dictionary for every column kept. No row was written or made up by us or by an AI. We fetched the files on 6 November 2026. Claims and policies are as FEMA held them on 8 September 2026, the repetitive loss properties on 21 October 2026 and the penetration rates on 3 August 2026, and the community rows were last refreshed on 25 August 2026 (seven of them on 18 September 2026). Texas has 11,612,805 policy rows, too many to fetch whole, so we fetched only the policies of four counties for the years the questions use.

The files are extracts. We kept some rows and dropped whole columns: exact location, ZIP code, city, community names and numbers, map panels, record numbers and exact construction and purchase dates. Every value kept is FEMA's own, unchanged, but the files are not FEMA's data as published. FEMA's data already leave out who the policyholders are, and they name no person or company. Nothing finer than a county and a flood zone is left.

FEMA asks for this notice: "This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s)."

FEMA's name appears because its terms ask for the citation. No FEMA or DHS logo or seal is used.

## How the answers were worked out

We wrote the questions. Each one states its facts, such as a county, a year, a date or a definition, and covers a group of at least ten rows. None asks about a single claim, policy or property, and figures from different files are combined only as county totals.

One script worked out every answer step by step from the rows supplied. A second script loaded the same files into a database and answered every question again in SQL. All 307 graded fields matched, and so did the size of every group. Each task grades 4 to 8 fields. Money counts as right within a dollar or 0.1%, shares and ratios within 0.0005, and counts and codes only when exact.

## What it does not cover

- Nobody in the trade has reviewed it: no claims analyst, and nobody at FEMA. Where FEMA's definitions are unclear, the question gives its own, and you may disagree with it.
- Texas only, and only a few counties and events. Claims come from six counties and three flood events, plus Texas's condominium claims and its claims with a compliance payment. Statewide claims and Harris County's claims are too large to include.
- Claims span the years 1978 to 2026, and older claims are less completely recorded. Policies are only those of four counties (Aransas, Calhoun, Hays and Kerr) effective in 2024 or 2025, rated under Risk Rating 2.0.
- It is a snapshot: claims and policies as FEMA held them in September 2026, repetitive loss properties in October 2026. Claims of recent events may still grow, claims of 2026 events are left out, and the answers hold for the files supplied.
- The list of coastal counties is a definition the questions give.
- No question asks about the program's current rules, puts a value on Community Rating System discounts, or uses the old rating fields, water depth or earned premium. None asks about a group of fewer than ten rows.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. FEMA's data are a work of the US government and have no copyright in the United States. FEMA's terms say nobody may use the files to re-identify, or try to re-identify, any person or property.

## This version

1.0 is the first open version. Its 52 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until claims analysts have reviewed it.

1.0.1 has the same 52 tasks as 1.0; only its short description changed.
