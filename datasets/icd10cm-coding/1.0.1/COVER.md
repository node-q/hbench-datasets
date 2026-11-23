## What this is

A test set on ICD-10-CM, the US diagnosis code set, read exactly as the US government publishes it. Each of its 30 tasks gives the AI lines of the published files and asks for exact answers: which codes are valid for submission and which are headers, how many valid codes sit under a header, which codes one release added, removed or reworded, or where two of the publisher's files disagree. The tasks fall into ten kinds of work, such as code lookup, the hierarchy and release changes. No task asks the AI to pick a code for a clinical record.

This is a draft. No certified coder or clinician, and nobody at NCHS or CMS, has checked the answers.

## Where the data come from

Every line the AI reads comes from the ICD-10-CM files of the National Center for Health Statistics (NCHS), part of the Centers for Disease Control and Prevention (CDC), as NCHS and the Centers for Medicare & Medicaid Services (CMS) publish them. They are available on the agencies' websites at no charge. We used the order files, codes files and addenda of two releases, 1 October 2025 (FY2026) and 1 October 2024 (FY2025), the publisher's two descriptions of the file layouts, and tables taken from the FY2026 tabular list. We fetched them on 15 November 2026.

Each task gets runs of consecutive lines of the files. Every line is the published line, character for character. Only the line endings differ. One file covers the whole code set and keeps only each line's code and flag, so that it stays under 1 MB. The tables hold the tabular list's text unchanged, accented letters included. The two layout descriptions are one-page PDFs, turned into plain text with the wording unchanged. The publisher doesn't describe the layout of the addenda, so the positions the tasks give for them were read off the files and checked on every change line.

ICD-10-CM is the United States' clinical modification of ICD-10, which the World Health Organization owns and publishes. Using these files here does not mean that CDC, CMS, the Department of Health and Human Services, the US Government or the World Health Organization endorses us or this test set. It is not an official ICD-10-CM product.

The descriptions name no private person or company. They do hold surnames as medical terms, such as Charcot or Kaposi, in the names of conditions. Those are kept as published.

## How the answers were worked out

We wrote the questions. Each one states its facts, such as a code, a range or a text to match, and defines the structural words it uses: parent, under, block, pair and placeholder. One script computed every answer from the task's own files, checking each line against the published bytes. A second script, sharing no code with the first, loaded the same files into a database and recomputed all 181 graded fields. Every one matched. To make sure the second script could catch a wrong answer, each expected value was then changed in small ways, and it rejected every change.

Each task grades 5 to 8 fields. Codes are written as the order file writes them, without the decimal point. Counts and codes count as right only when exact, and a list of codes only when it has exactly the expected members.

## What it does not cover

- No certified coder or clinician has reviewed it. Each question defines its structural words, and a coder may use some of them differently.
- It is not coding from a clinical record. No task picks a code for a clinical statement, puts codes in order, or applies the official coding guidelines, Excludes notes or instructional notes. The AI is not given them.
- The alphabetic index, the neoplasm and drug tables and the list of codes exempt from present-on-admission reporting are left out.
- Each task works on extracts: single chapters, blocks and categories, mostly ones with changes between the releases, 7th characters or laterality. They are not a sample of the whole code set.
- The two releases are no longer in force. The release of October 2025 was replaced on 1 April 2026, and FY2027 followed on 1 October 2026. The answers hold for the files supplied.
- No published statement says that ICD-10-CM is in the public domain, and we have not confirmed with its publishers the terms on which it may be reused.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. ICD-10-CM itself is not covered. Its files carry no copyright notice and no terms of use. CDC's general terms call most of the content on its websites public domain, but they also warn that a US government work may still be protected by copyright outside the United States, and ICD-10-CM is based on ICD-10, which the World Health Organization owns. We found no terms from CDC, CMS or the World Health Organization that allow or forbid passing the files on. So we don't claim that the code set is in the public domain, and we don't license it. The notice sets out what each publisher says.

## This version

1.0.1 has the same 30 tasks as 1.0. The only change is in the credit to the agencies in each task, which now names Actuaria.io as the publisher. It stays a draft until medical coders have reviewed it.
