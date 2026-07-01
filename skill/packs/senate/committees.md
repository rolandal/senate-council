---
pack: senate
mode: senate
description: How the Senate sorts ~36 members into balanced, diverse committees.
---

# Senate Committees — the caucus sort

Run by `scripts/assign_committees.py` (pure, deterministic). Members are grouped
by kind (model → style → figure) then round-robin assigned to
`ceil(N / size_target)` committees (size_target = 6 → 6 committees for ~36).

Why this order: the scarce, high-signal kinds spread first. With ≤ 6 model
seats, every model lands in a **distinct** committee; the 8 styles spread at most
two per committee; figures fill the rest. No committee is an echo chamber, and
sizes differ by at most one.

Each committee elects a **whip** (one Opus agent) that compresses its ~6
members' full arguments into a single ~250-word committee brief plus the
committee's mini-tally. The chairman then sees 6 briefs, never 36 raw responses.
