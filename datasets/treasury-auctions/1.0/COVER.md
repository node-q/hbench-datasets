## What this is

A test set on the US Treasury's auctions of bills, notes, bonds, TIPS and floating rate notes. Each of its 27 tasks gives the AI the Treasury's own auction records and the regulation that governs the auctions, and asks for exact figures. Some apply a rule of the regulation to a real auction: a bill's price, an award at the high rate, accrued interest, or a TIPS index ratio and settlement amount. The rest work over the records, such as bid-to-cover ratios, what each class of bidder was awarded, how long the securities issued in a year run, or whether the records agree with each other. The tasks fall into ten kinds of work.

This is a draft. No fixed-income analyst and nobody at the Treasury has checked the answers.

## Where the data come from

The records are the Treasury's published auction results. We fetched them from TreasuryDirect, the public securities service of the Bureau of the Fiscal Service, on 15 November 2026: all 1,245 auctions of securities issued between January 2024 and October 2026, each with 187 fields. We rewrote them from JSON as CSV and changed no field or value. Each task gets one extract, for one type of security or one period.

The auctions issued from 22 October 2026 on use a second layout of the same fields. The extracts keep both layouts as the service returned them, and one task asks about the change.

Every task also gets 31 CFR Part 356, the Uniform Offering Circular, as the eCFR showed it for 6 November 2026. We turned its XML into plain text and changed no words. The eCFR is an editorial compilation of the Code of Federal Regulations, not the official legal edition. This test set is not approved, endorsed or sponsored by the Department of the Treasury, and is not associated with it.

## How the answers were worked out

We wrote the questions. Each names the securities and amounts it is about and states any definition it uses. One script computed the answers. Where the records carry the Treasury's own result of a rule, such as a bill's price, accrued interest or a TIPS index ratio, that script's reading of the rule gives the Treasury's figure on every record. A second script, written in SQL and sharing no code with the first, recomputed every answer from the shipped files. Its first run found one rounding error, in awards at the high rate, and the answers were corrected. The two scripts now agree on every field.

## What it does not cover

- No fixed-income analyst has reviewed the questions or the definitions they give. Where a term means more than one thing in the market, the question says which meaning it uses, and you may still read it differently.
- The regulation shows some formulas only as images, which the text leaves out. So no task asks for a bill's investment rate, a price from a yield or a discount margin, or the interest that builds up on a floating rate note.
- No prices from trading after the auction, no when-issued yields, no buybacks and no amounts maturing on each date.
- The tasks compute numbers. None asks what a bid-to-cover ratio or a tail says about demand.
- The records are as the service returned them on 15 November 2026, and the regulation as of 6 November 2026. Both change, and the answers hold for the files as given.
- CUSIP numbers are kept as the Treasury publishes them. Nobody has reviewed whether using them needs a licence.

## Licence

Our tasks, questions and answer keys are under CC BY 4.0. You may use, change and share them, commercial use included, if you credit the source. The auction records and the regulation are works of the US government and have no copyright in the United States. CUSIP numbers come from a numbering system that a third party owns and licenses.

## This version

1.0 is the first open version. Its 27 tasks are the ones we used privately before, so their answer keys are public now. It stays a draft until fixed-income analysts have reviewed it.
