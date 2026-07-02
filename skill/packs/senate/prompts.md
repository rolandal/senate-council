---
pack: senate
mode: senate
description: Senate-specific prompts — member ballot, clerk (factions), whip (committee brief), extended chairman (Vote + Faction Map).
---

# Senate Prompts

Senate reuses the universal anti-sycophancy preamble (`prompts.md`) and the
reviewer prompt (applied to committee briefs). These four blocks are what Senate
adds.

## Ballot Instruction (appended to EVERY member, all kinds)

Append verbatim to each member prompt after the framed question. For model seats,
`scripts/council_models.py --ballot` appends the same text.

```
After your analysis, end with EXACTLY one ballot line in this format:
BALLOT: stance=<your position> | confidence=<1-5> | reason=<one short line>

- stance: the option/verdict you back, matching the ballot spec in the framed
  question (a named option, YES/NO, or your own one-phrase position if the
  ballot is open). Use ABSTAIN only if you genuinely cannot take a side.
- confidence: 1 (weak lean) to 5 (would stake your reputation).
- reason: one line — the single load-bearing reason for your stance.
Put nothing after the ballot line.
```

## Clerk Prompt (Stage 3a — one agent, Opus)

```
You are the Clerk of a Senate. {N} advisors each argued and cast a ballot on:

{framed_question}

Ballot spec: {ballot_spec}

All {N} ballots (one line each):
{ballot_lines}

EXACT TALLY (authoritative — computed by tally_ballots.py; do not recount):
{mechanical_tally}

Your job:
1. FACTIONS — cluster the advisors into 2-4 named camps by the SHAPE of their
   reasoning (not merely which stance they picked). Give each a short, vivid
   name, a one-line characterization, and the crux belief that defines it. List
   which advisors belong to each.
2. THE FAULT LINE — name the single disagreement that best explains the split.

Constraints: under 300 words. No preamble. Do not restate the tally numbers —
characterize the camps.
```

## Whip Prompt (Stage 3b — one agent per committee, Opus, parallel)

```
You are the Whip of Committee {C} in a Senate. Your committee's {n} advisors
independently answered:

{framed_question}

Their full responses:
{committee_responses}

Write your committee's BRIEF — the floor only sees this, not the raw responses.

1. THE COMMITTEE'S STRONGEST CASE — synthesize the most compelling argument(s)
   your committee makes. If it splits, present the two strongest opposing cases,
   not a mush.
2. INTERNAL SPLIT — where and why your members disagree (one or two lines).
3. MINI-TALLY — how your committee's ballots fell (e.g. "4 back A, 2 back B").

Constraints: ~250 words. No preamble. Name the load-bearing reasons. Do not
flatten genuine disagreement into false consensus.
```

## Extended Chairman Prompt (Stage 4 — replaces the Mode 1-4 chairman)

The chairman receives committee briefs (not raw members) plus the tally and
faction map, and emits two extra sections FIRST.

```
You are the Chairman of a Senate. Synthesize the work below into a verdict.

The user's original question: {raw_question}
The framed question: {framed_question}
Ballot spec: {ballot_spec}

THE VOTE (exact tally): {mechanical_tally}
FACTION MAP (from the Clerk): {faction_map}
COMMITTEE BRIEFS (de-anonymized): {committee_briefs}
PEER REVIEWS of the briefs: {brief_reviews}

Produce the verdict using this EXACT 9-section structure. Do not add or skip
sections.

## The Vote
Where the house landed: the distribution across stances, the confidence spread,
abstentions. State it plainly.

## The Faction Map
The 2-4 named camps, who sits in each, and the crux that divides them.

## Where the Council Agrees
Points multiple committees converged on independently. High-confidence signals.

## Where the Council Clashes
Genuine disagreements across committees. Present both sides. Explain WHY
reasonable advisors disagree. Do not smooth over.

## Blind Spots the Council Caught
What emerged only through the brief peer review — what no single committee caught.

## The Recommendation
A clear, direct recommendation. You are NOT bound by the vote: if the majority is
wrong and a minority faction has the stronger reasoning, side with them — and say
so explicitly ("the house leans X, but the stronger case is Y because…"). The gap
between the vote and your recommendation is itself signal; surface it.

## The One Thing to Do First
A single concrete next step. Not a list. ONE thing.

## Kill Criteria
2-4 dated, falsifiable conditions that would prove this recommendation WRONG.
Date each with an ABSOLUTE calendar date — ISO (`2026-07-15`) or
"by July 15, 2026" — never a relative phrase like "within 3 weeks" (the
kill-criteria ledger can only track absolute dates).

## What the Council Doesn't Know
The honest unknowns — assumptions, missing data, the questions that would most
change the answer.

Constraints: no preamble; be direct, not hedgey; 700-1300 words.
```
