# Open Actuaria test sets

node-q writes and checks its own test sets in a private task repository. From 2026-11-23 every one of them except
`next-eo` is published openly here, under CC BY 4.0, and listed free on the Actuaria Market Place.

## The decision

The founder decided this in chat on 2026-11-23 ("Public hết trừ next eo": public, everything except next-eo),
after being told:

1. Every set was licensed for internal use only at the time.
2. Sixteen sets read Ohio insurance rate filings (general liability, commercial property, E&O, farm, medical
   malpractice, pet, personal auto, ratemaking, surety, title, the ACA sets for Florida, Ohio and Texas, Medicare
   for Ohio, Medicare Supplement for Ohio, and the underwriting starter set). The filings are public records, but
   their text is still the filers' copyright.
3. Once published, the answer keys are public too, so the sets stop working as hidden tests. That cannot be undone.

The founder accepted these three risks in chat on 2026-11-23. This page is the record of that acceptance. The
founder did not object to CC BY 4.0 for node-q's own work, proposed in the same chat.

## What the licence covers

- node-q's own work (the tasks, their questions, the answer keys and the checker) is under CC BY 4.0. The
  step-by-step derivations behind the answer keys stay in the private repository and are not published.
- Third-party documents keep their own status, and each version's NOTICE says what it is:
  - Text written by US federal agencies is a work of the US government, with no copyright protection in the
    United States (17 U.S.C. 105). That covers only what the federal government wrote, and only in the United
    States.
  - The Ohio filings are public records. Their text stays the filers', is included unchanged except for the
    redactions each version records, and is not relicensed by node-q.
  - A source with its own terms (ICD-10-CM, NIST OSCAL, FDIC, NOAA, USGS, Treasury, IRS, CDC) is described from
    those terms. A source whose terms forbid redistribution leaves its set out.

The private versions of the sets stay private and unchanged.

## How a set is published

1. In the private repository, `scripts/export_open.py datasets/<name> tasks.tar.xz` writes the current version's
   built tasks as one reproducible file: the same bytes for the same tasks, never a derivation.
2. That file is attached to a release of this repository, `sources-<name>-<version>`, and pinned by sha256 in the
   version's `source.yaml` as its one upstream file.
3. `adapters/taskfolders` writes the tasks from it, unchanged except for their names (without the private
   `hb-int-` prefix), the image they run in (`taskfolders-1.0`, built here from `images/taskfolders`) and the
   canary added to the checker and the answer files. It records each task's kind of work, difficulty and number of
   graded fields in `tasks.json`, which the listing counts from. `scripts/check_generated_tasks.py` checks
   `tasks.json` and runs each task's checker on its oracle (it must pass) and on an empty answer (it must fail).
4. From there a set is built, locked and published like any generated dataset here.
