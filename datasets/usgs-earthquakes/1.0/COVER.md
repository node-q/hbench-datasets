## What this is

A test set on the US Geological Survey's earthquake catalog. Each of its 30 tasks gives the AI one extract of the catalog and asks for exact figures. The AI has to read numbers written as text, keep event types, magnitude types and review status apart, group events by UTC and by a stated local clock, work out distances and windows in time and space, and apply a stated formula, such as a b-value or a seismic moment, exactly. It also checks records against each other without raising false alarms. The tasks fall into ten kinds of work, such as depth classes, aftershock sequences and data checks.

This is a draft. No seismologist and nobody at the US Geological Survey has checked the answers.

## Where the data come from

Every row is real. The records are events of the ANSS Comprehensive Earthquake Catalog (ComCat), which holds earthquake source parameters contributed by seismic networks. We took them from the US Geological Survey's public web service on 15 November 2026, in four requests: events of magnitude 4.5 and above worldwide for 2024, the same for 2025, and smaller events of 2025 in two boxes in North America. Each task holds one extract of those responses. We left out rows and changed nothing else: all 22 columns are kept, and no value was corrected or rounded.

The records describe seismic events, so no one in them needed to be made anonymous. The only free text is a place description. A scan found no personal data, contact details or company names in it. Some place names are also the names of people or companies.

Credit: U.S. Geological Survey. The US Geological Survey lists this citation for the catalog: U.S. Geological Survey, 2017, Advanced National Seismic System (ANSS) Comprehensive Catalog of Earthquake Events and Products, https://doi.org/10.5066/F7MS3QZH. This test set is not endorsed or approved by the US Geological Survey or any contributing network, and has no tie to them.

## How the answers were worked out

We wrote the questions, and each one states the measures it uses. One script computed every answer from the file supplied, with exact decimals and 50-digit arithmetic. A second script, sharing no code with the first, recomputed all 214 answer fields in SQL and ordinary arithmetic, and every field matched. Each answer was also worked out step by step and checked against the answer key. These checks confirm the arithmetic and the reading of each question. They say nothing about seismological practice.

## What it does not cover

- No seismologist and nobody at the US Geological Survey has reviewed it. Class bounds, windows, completeness magnitudes and the use of the moment formula on other magnitude types are settings of the questions. They are not recommendations from seismology. The aftershock windows are fixed windows and are no substitute for a declustering method.
- Worldwide events are only those of magnitude 4.5 and above. Smaller events cover just two boxes, in the United States, southern Canada and northern Mexico, where networks are dense. One sequence, after the magnitude 8.8 earthquake of July 2025, makes up much of 2025.
- No column definitions from the US Geological Survey are included. Each question defines what it uses.
- Nothing calls for a seismologist's own view or for outside knowledge: whether two close events are one earthquake, whether a sample is complete, an event's tectonic setting or its country. Each task works on one file, with no joins across files.
- It is a snapshot of the catalog as retrieved in November 2026. Events get revised, added and deleted. The answers hold for the files supplied.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The earthquake records are not ours, and CC BY 4.0 does not cover them. Their terms of use are not confirmed. We could not read the US Geological Survey's page on copyrights and credits, and we have not read the terms of the other networks whose events the catalog carries.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until seismologists have reviewed it.
