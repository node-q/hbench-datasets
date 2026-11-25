# Open Actuaria test sets

Some of the datasets here are node-q's own test sets, published under the Creative Commons Attribution 4.0
International licence (CC BY 4.0). Each asks an AI for exact answers from real public documents, such as a federal
regulation, and checks every field of the answer against its answer key. They are drafts: nobody in the trade has
reviewed their answers yet, and each version's NOTICE and COVER.md say so.

## What the licence covers

- node-q's work (the tasks, their questions, the answer keys and the checker) is under CC BY 4.0.
- The documents the tasks read are not node-q's, and CC BY 4.0 does not cover them. Each version's NOTICE says
  where they come from and what their status is. Text written by US federal agencies is a work of the US
  government, which has no copyright protection in the United States (17 U.S.C. 105); that covers only what the
  federal government wrote, and only in the United States.

## How a set is published

1. node-q exports a set's tasks as one reproducible file, `tasks.tar.xz`, and attaches it to a release of this
   repository named `sources-<name>-<version>`, marked as source data. The version's `source.yaml` pins it by
   sha256 as its one upstream file.
2. `adapters/taskfolders` writes the tasks from it, unchanged except for their names and tags (without node-q's
   `hb-int-` prefix), the image they run in (`taskfolders-1.0`, built here from `images/taskfolders`, or for the computer-use
   set `desktop-1.0`, from `images/desktop`) and the canary
   added to the checker and the answer files. It records each task's kind of work, difficulty and number of graded
   fields in `tasks.json`, which the listing counts from. `scripts/check_generated_tasks.py` checks `tasks.json`
   and runs each task's checker on its oracle (it must pass) and on an empty answer (it must fail).
3. From there a set is built, locked and published like any generated dataset here.
