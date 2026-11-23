## What this is

A test set on health privacy under US federal law. Each of its 29 tasks describes an incident or a request at an unnamed health care provider, health plan or business associate. The AI applies the HIPAA regulations the way a privacy officer would: it decides whether an incident is a breach, finds whose knowledge starts the clock, tells "more than 500" from "500 or more", gives the latest date for each notice, meets the time limits for requests, and reads the right row of the penalty table. The tasks fall into ten kinds of work.

This is a draft. No privacy officer, lawyer or official of the Department of Health and Human Services has checked the answers.

## Where the text comes from

The AI reads ten parts of the Department of Health and Human Services' regulations in Title 45 of the Code of Federal Regulations: the breach notification rule (Part 164, Subpart D), the definitions in 160.103, 164.103 and 164.501, the rights of access, amendment and accounting (164.524, 164.526 and 164.528), the administrative requirements in 164.530, the civil money penalty rules (Part 160, Subpart D) and the yearly adjusted penalty amounts (Part 102). The text is as the eCFR showed it on 12 November 2026. We turned the XML into plain text and changed no words. The eCFR is an editorial compilation, not the official legal edition. This test set is not approved or endorsed by the Department of Health and Human Services or any other agency.

## How the answers were worked out

We wrote the scenarios. They name no organisation or person and describe no real incident. Every answer follows from the text and the facts in the question. Each answer was worked out step by step from the rule it rests on. A second script, sharing no code with the first, recomputed every answer from the questions and the text and agreed. Both come from the same reading of the text, so they catch slips of arithmetic, not a different reading of a rule. The regulations give no worked examples, so the readings could only be checked against their wording.

## What it does not cover

- US federal rules only, as they stood on 12 November 2026. The penalty amounts change every year, and the rules are amended from time to time. State breach notification laws are left out.
- The regulations don't say how to count days and years. Each question states one way, and counted another way several answers move by a day.
- Calls the text leaves open are not asked, such as the risk assessment of whether information was compromised, or whether a fee was reasonable. Where a task needs one, the question gives the outcome.
- Rules that are not in the text it reads, such as permitted uses and disclosures or the Security Rule, are left out. Where a task depends on one, the question states the fact.
- The scenarios are short and clean, told in the regulations' own terms, which real incidents are not. Two or three tasks for each kind of work show where an AI stands. They can't separate two close results.
- It is not legal advice.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The regulations' text is a work of the US government and has no copyright in the United States.

## This version

1.0 is the first open version. Its 29 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until privacy officers have reviewed it.

1.0.1 has the same 29 tasks as 1.0; only its short description changed.
