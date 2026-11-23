## What this is

A test set on US storm records, the kind of hazard data a catastrophe modeller prepares. Each of its 30 tasks gives the AI rows of NOAA's Storm Events Database for 2024 or 2025 and asks for exact figures. The AI has to tell events apart from episodes and county rows apart from forecast zone rows. It reads damage written with K, M and B suffixes and keeps an empty cell apart from zero. It reads a magnitude whose unit depends on the event type, handles times and time zones as the question states them, joins two files without counting a row twice, and checks records against each other without raising false alarms. The tasks fall into ten kinds of work, such as damage amounts, tornado paths and counts compared year over year.

This is a draft. No catastrophe modeller, meteorologist or actuary, and nobody at NOAA, has checked the answers.

## Where the data come from

Every task works on real public data, and none of it is made up. The rows come from the Storm Events Database files that NOAA's National Centers for Environmental Information (NCEI) publish for 2024 and 2025, as the National Weather Service entered them. We took the files from NCEI on 15 November 2026. Each task's files are extracts. We kept the rows for one state, one event type or a list of event types, dropped a few columns and rewrote the CSV quoting. Every other value is exactly what NCEI's file holds. The extracts cover five states (Florida, Georgia, Missouri, New York and Texas), tornado segments in every state, and the tropical events of 2024.

We dropped the forecasters' free-text notes, which can name people, businesses and addresses, and the point coordinates. The files that describe individual deaths are not used, and deaths and injuries are only summed over groups of at least ten events. Public place names stay in. Some places are named after people or businesses, such as airports, mills and ranches.

NCEI asks that you cite the database when you use it as a source. It also says: "Customers should be cautious as the NWS does not guarantee the accuracy or validity of the information." This test set is not approved, endorsed or sponsored by, or associated with, NOAA, NCEI or the National Weather Service.

## How the answers were worked out

We wrote the questions. Each one states its definitions in full, and the meaning of each column follows NCEI's own description of the file format. We read that description, a PDF, only through a rough pull of its text, so it isn't included and isn't quoted.

One script computed every answer with exact arithmetic, in whole dollars and fractions. Each answer was also worked out step by step, citing the rows and columns it rests on, and checked against the key. A second script, sharing no code with the first, loaded the files into SQL and recomputed all 217 graded fields, and every one matched. Two scripts agreeing shows the arithmetic holds. It doesn't show that a definition is the one a practitioner would pick. Counts and dollar sums must be exact. Shares and indexes are accepted within 0.0005, and averages within a small margin.

## What it does not cover

- Nobody in the trade has reviewed it: no catastrophe modeller, meteorologist or actuary, and nobody at NOAA. Each question states its own definitions, and a practitioner may prefer others.
- US data for 2024 and 2025 only: five states, tornado segments in every state, and one year's tropical events.
- The answers describe what the files record. Damage amounts are forecasters' estimates and many cells are empty. Reporting depends on the local forecast office and on who reports, so populated areas report more events.
- Every task counts tornado segments. The files have no key that ties the segments of one tornado together, so no task counts whole tornadoes.
- There is no exposure, insured loss, inflation adjustment or return period. No task asks whether a row is wrong or what a year says about the climate.
- It is a dated snapshot of the files as NOAA served them on 15 November 2026. NOAA rewrites the files as records are corrected. The answers hold for the files supplied.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The storm records are not ours, and CC BY 4.0 does not cover them. NOAA is an agency of the US government, and a work of the US government has no copyright protection in the United States. That covers only what the federal government wrote, and only in the United States. NCEI states no licence for the database and asks that you cite it.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until catastrophe modellers have reviewed it.
