## What this is

A test set on NIST SP 800-53 Rev. 5, the US federal catalog of security and privacy controls, and the baselines that go with it. Each of its 30 tasks gives the AI tables of the catalog and asks for exact answers, the way a compliance analyst works with it: how many controls a family has, where a withdrawn control went, what the HIGH baseline adds over MODERATE, or a system's control set after tailoring. The tasks fall into ten kinds of work, such as withdrawn controls, baseline comparison, parameters and assessment procedures.

This is a draft. No security compliance analyst, auditor or anyone at NIST has checked the answers.

## Where the data come from

Nothing in the data is invented. The AI reads the National Institute of Standards and Technology's own machine-readable (OSCAL) release of SP 800-53 Rev. 5, with the assessment procedures of SP 800-53A and the LOW, MODERATE, HIGH and privacy baselines of SP 800-53B. It is catalog version 5.2.0, last modified on 22 October 2026, as NIST's public repository usnistgov/oscal-content held it on 15 November 2026.

We rewrote NIST's JSON files as six tables: controls, links, parameters, baselines, statements and guidance, and assessment procedures. Every value and all the wording stayed as NIST wrote it. A script rebuilds NIST's controls and baselines from the tables and finds them equal. Each task gets the controls table and every other table its question needs, whole. The catalog's list of reference documents is left out. This test set is not NIST's product, and NIST has not endorsed it.

## How the answers were worked out

We wrote the questions. Each one states its facts, such as a system's impact level or the controls it marks not applicable, and defines the words it uses, such as base control, enhancement, active and withdrawn. Each answer was worked out step by step from the tables, citing the rows and columns it rests on. A second script, written in SQL and sharing no code with the first, recomputed all 195 answer fields and agreed with every one. That shows two separate readings of each question agree. It does not show the questions are the right ones.

## What it does not cover

- No security compliance analyst or auditor has reviewed it yet.
- The tailoring tasks apply simple rules that the question states, such as an enhancement needing its base control. They are not NIST's tailoring guidance, which asks for a person's view of the system.
- Nothing that needs an opinion or outside knowledge: whether a control suits a system, how to set a parameter, or what a control means. The tasks count, compare and cross-check.
- The reference documents the controls cite are not given to the AI, and no question searches the control text for words.
- One catalog and its baselines only. SP 800-53 Rev. 4, other frameworks and other countries are left out.
- The questions define their own words, and a reader may define some of them differently.
- The data are a snapshot of catalog version 5.2.0. NIST revises the catalog, and the answers hold for the tables as given.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. NIST's release is a work of the US government and has no copyright in the United States. NIST has also dedicated it to the public domain worldwide under CC0 1.0.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until security compliance analysts have reviewed it.
