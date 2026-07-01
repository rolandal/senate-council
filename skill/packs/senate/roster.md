---
pack: senate
mode: senate
description: >
  Mode 5 (Senate) — the whole house. The roster is the UNION of every pack: all
  figures + all styles + all real models (~36 seats). Every member casts a
  structured ballot and argues; a caucus+clerk map-reduce compresses the floor
  into a tally, named factions, and a chairman verdict.
size_target: 6
quorum: 0.75
---

# Senate Roster — the whole house

## Assembly rule

The Senate seats are the **union** of:

- **Figures** — every file in `packs/figures/*.md` (excluding `triads.md`). ~23 seats, `kind: figure`.
- **Styles** — every lens in `packs/styles/default.md` + `packs/styles/extras.md`,
  **excluding The Advocate** (it is not part of the standing union). ~8 seats,
  `kind: style`.
- **Models** — every seat in `packs/models/roster.md`. ~5 seats, `kind: model`.

Each seat is `{label, kind, source}`. Total ≈ 36.

Plus **one Advocate seat** (`kind: style` or `figure`) whenever the user has a
detectable leaning — see SKILL.md → Stage 1C / Critical Behavior 7. It is an extra
seat (≈37 with it), carries a ballot, and is included in the quorum gate and
committee assignment like any member.

## Tier strategy (runtime flag)

| Invocation | Members (convene) | Clerk · Whips · Reviewers · Chairman | Model seats |
|---|---|---|---|
| `senate` (default, Tiered) | native = Sonnet | Opus, max effort | real |
| `senate max` | Opus, max effort | Opus, max effort | real |
| `senate express` | native = Sonnet | Opus (skip brief review) | real |

The model seats are always real frontier models. **No OpenRouter key** → run a
**native Senate** (figures + styles only, ~31 seats); the honesty banner states
the reduced panel.

## Quorum & degradation

Proceed when ≥ 75% of members return (~28 of 36). Below quorum, surface it and
ask before proceeding. An unparseable ballot counts as ABSTAIN; the member's
argument is still used by its committee whip.
