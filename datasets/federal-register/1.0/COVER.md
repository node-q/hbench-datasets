## What this is

A test set on research in the Federal Register. Each of its 28 tasks gives the AI the same files: the Federal Register's records of every rule and proposed rule that five federal agencies published in 2024 and 2025, and the text of 89 of them. The AI finds the documents that meet stated criteria, follows a rulemaking through its proposal and final rule by its regulation identifier number, docket or citation, counts comment periods and effective dates, matches corrections, extensions, delays and withdrawals to the documents they concern, counts and ranks with the definitions given, reads figures out of rule texts, and checks the records against themselves and against the texts. The tasks fall into nine kinds of work, such as finding documents, rulemaking histories and record checks.

This is a draft. No regulatory analyst and nobody at the Office of the Federal Register or the agencies has checked the answers.

## Where the files come from

The agencies are the Internal Revenue Service, the Agricultural Marketing Service, the Office of Personnel Management, the Social Security Administration and the Pension Benefit Guaranty Corporation. The records of their 386 documents come from the Federal Register's public API, written as one CSV file with the values unchanged. The texts of 89 of them come from the Government Publishing Office's text editions on govinfo.gov. We took both on 15 November 2026 and again on 24 November 2026, and the files came out the same. Under 1 CFR 2.6 anyone may reproduce or republish what appears in the Federal Register. This test set is not approved, endorsed or sponsored by the Office of the Federal Register, the Government Publishing Office or any of the agencies.

No person's personal data is in the files. Five records whose descriptions name a company, a private organisation or a person were left out. From the texts, the contact sections, the signature blocks and the passages that name an official were dropped whole, each marked where it stood, and texts that still named a person were left out. No sentence was edited. The NOTICE lists every cut.

## How the answers were worked out

We wrote the questions. Each states its definitions and asks for exact values. One script computed the answers. A second script, sharing no code with the first, recomputed every graded field from the questions and the files alone and agreed. Three tasks were also solved from scratch by readers who had not seen the answers, with every field right. These checks confirm the reading of each question and the arithmetic, not a regulatory judgement.

## What it does not cover

- The definitions in the questions, such as what counts as a correction or how a comment period is counted, are ours. A reader may define them differently.
- Rules and proposed rules of five agencies over two years only, with no notices, presidential documents or other agencies. Most documents come as records only, and the texts lack the sections dropped for privacy.
- The API's fields are used as the API returns them, because its documentation could not be read. One task shows that a delaying document's effective date in the API is not the date its own text states.
- It asks for no judgement about what a rule means, and for no knowledge from outside the files.
- The records are a snapshot from November 2026. The Federal Register can revise them, and the agencies keep publishing.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The source documents are works of the US government and have no copyright in the United States. Elsewhere their status may differ.

## This version

1.0 is the first open version. Its 28 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until regulatory analysts have reviewed it.
