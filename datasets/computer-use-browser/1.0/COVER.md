## What this is

A test set for AIs that use a computer the way a person does. Each of its 30 tasks puts one to three real IRS documents on a Linux desktop with the Chromium browser. The AI opens a PDF or a web page, finds the right page of a long table, follows the document's own bookmarks, zooms into small print, and carries what it reads through a table or worksheet exactly. The tasks fall into ten kinds of work, such as tax table lookups, payroll withholding, worksheets and searching long web pages.

It suits AIs that see only the screen and use the mouse and keyboard, and AIs that can also run commands. An AI that can't write files gives its answer as its final message, and the task's check reads it from there.

This is a draft. No tax preparer, payroll specialist or anyone at the IRS has checked the answers.

## Where the documents come from

The tasks read nine documents of the Internal Revenue Service, byte for byte as irs.gov served them on 24 November 2026: Publication 1040 with the 2025 tax and earned income credit tables, the 2024 tax tables, the 2025 Instructions for Form 1040, Publication 15-T for 2026 and for 2025, Schedule 1 (Form 1040) for 2025, Publication 501 for 2025, and the web editions of Publications 501 and 15-T. IRS.gov says content made by federal employees in the course of their duties is not subject to copyright, and asks for credit, which we give. This test set is not approved, endorsed or sponsored by, or associated with, the IRS or the Department of the Treasury.

The documents ship unchanged, so nothing in them was cut. We read every one for personal data and found none: the phone numbers are those of agencies and organisations, and the names in worked examples, such as Lee, Sam or the Smiths, and the sample check made out by Stella and Bailey Keys, are fictitious examples printed by the IRS. The NOTICE lists what we found, and the parts of the documents, such as some cover artwork, that may not be US government works.

## How the answers were worked out

We wrote the questions. Each states the facts of an exercise for an unnamed taxpayer or employee. One script read every answer from the documents and checked that each quoted passage is on the page it cites. A second script, sharing no code with the first, read the documents another way and agreed on every graded field. Every amount of the two years' wage bracket withholding tables was also recomputed with the same publication's percentage method, without a difference.

## What it does not cover

- It is not tax advice. It covers US federal income tax and withholding only, in the editions named above. Later editions and the law may differ.
- The two web pages ship without the site's styling, so they look plainer than on irs.gov. With network access, the browser also loads the site's Google Tag Manager and AddToAny scripts for them. You can run the tasks with the network off: every document is a local file.
- The questions test reading and carrying values exactly, not judgement about a real return. The exercises are simple on purpose.
- Two to four tasks for each kind of work show where an AI stands. They are not enough to rank two close results.

## What you need to run it

An AI set up to work a desktop through screenshots, mouse and keyboard, and Docker with at least 2 CPUs and 4 GB of memory for each task, on a 64-bit Intel or AMD machine. The tasks run in our desktop image: Debian with a virtual screen, the XFCE desktop and Chromium.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The source documents are works of the US government and have no copyright in the United States. Elsewhere their status may differ.

## This version

1.0 is the first open version. Its 30 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until tax preparers and payroll specialists have reviewed it.
