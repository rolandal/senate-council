# Changelog

## v1.3 — 2026-06-26 · Input-integrity gate + golden fixture

Lessons from a second Senate run (a fictional, repo-safe relocation dilemma built
as a regression fixture). The headline: a member can vote on a question it never
received, and the run still looks perfect.

- **`scripts/check_inputs.py`** — input-integrity gate run right after convene,
  before quorum. Verifies every member prompt actually contained the framed
  question; exits non-zero listing any seat whose prompt does not. Closes the most
  dangerous failure mode: when the question doesn't reach a member (an empty side
  channel, an unfilled template variable), the model does **not** error — it
  confabulates a plausible answer from breadcrumbs in the prompt and casts a
  real-looking ballot. Observed live: 31 seats once deliberated on
  `THE FRAMED QUESTION:\nundefined`; 29 produced on-topic-looking analyses, only 2
  said "undefined" out loud. **No response-level check can catch this** —
  confabulation is built to look real — so the gate checks the *input* delivered,
  not the output. SKILL.md adds this as Critical Behavior 8 and a mandatory Senate
  step.
- **`scripts/render_report.py`** — vote labels are now data-driven via
  `bundle["stanceLabels"]` (e.g. `{A: "Relocate", B: "Stay put"}`). A/B/C mean
  nothing on their own; what they stand for is defined by *each question's* ballot
  options. Decouples the renderer from any one scenario; backward compatible.
- **Golden render fixture** (`tests/fixtures/relocation-senate.*`) — a full,
  repo-safe 36-seat Senate captured as a byte-for-byte snapshot of `build_report()`
  (HTML + transcript), locking the renderer/template against silent regressions.
  Also the canonical example. `tests/regen_golden.py` regenerates it after an
  intentional renderer change.
- Report footer + README now carry a build credit (*built with `roland.bot`*).
- Tests: 89 → 98 (golden snapshot + input-gate coverage).

## v1.2 — 2026-06-26 · Senate hardening (first live run)

Lessons from the first live Senate run (a 36-seat personal decision).

- **`scripts/check_quorum.py`** — roster-integrity gate run before the reduce.
  Fails (exits non-zero) on a quorum shortfall **or any whole-kind drop**. Closes
  the bug where all 5 model seats were silently lost and the verdict was
  synthesized on 31/36 seats — a naive ≥75% quorum (86%) would have passed it.
- **`scripts/render_report.py`** — fills `report-template.html` from a run bundle
  and writes both the HTML and the transcript, so the output is never
  hand-templated. Senate-aware (vote bar, faction map, committee briefs); degrades
  cleanly to modes 1-4. Reproduces the first live report byte-for-byte.
- **`tally_ballots.py --options A,B,C`** — canonicalizes named-option stances so
  `"Option C — …"`, `"Option C"`, and `"C"` count as one stance. Fixes a latent
  fragmented-tally bug in the native flow (the live run dodged it only because its
  members used a forced enum).
- SKILL.md: mandatory quorum gate in the Senate flow; tally step now passes
  `--options` for named ballots; Output points at the renderer; framing stage now
  spends one clarifying question on the highest-leverage unknown (the live run
  burned a whole blind-spots section on an un-asked sole-caregiver assumption).
- **The Advocate seat** — a mandatory extra seat (when the user has a detectable
  leaning) whose job is the strongest good-faith case FOR the user's current
  position, so a converging house can't bury it with only a reviewer footnote in
  dissent. Voice = whichever is stronger: a fitting figure or the new
  position-agnostic **Advocate lens** (`packs/styles/extras.md`, parameterized by
  `{user_position}`; excluded from the standing style union). New Critical
  Behavior 7 + Stage 1C; Senate roster counts it like any seat (≈37 with it).
- +21 tests (8 quorum, 7 render, 4 tally canonicalization, 2 advocate) → 89 green.

## v1.1 — 2026-06-25 · Mode 5 Senate

The whole-house mode for ultra-hard calls. Convenes the union of every pack
(~36 seats: all figures + styles + real models); each member casts a structured
ballot, and a caucus+clerk map-reduce produces an exact vote tally, named
factions, and a chairman synthesis (9-section verdict — adds The Vote + The
Faction Map). New pure scripts `tally_ballots.py` (ballot parse + tally) and
`assign_committees.py` (balanced diverse committee sort); new `packs/senate/`
pack; runtime tier flag (`senate` / `senate max` / `senate express`). Prior tests
stay green; Senate adds parse/tally/committee/pack/template/router tests.

## v1.0 — 2026-06-25

First release of the 4-mode Council, wrapping the existing `llm-council` skill.

- **Engine:** one member-agnostic pipeline (Frame → parallel Convene → anonymized A–E
  peer review → Opus chairman → HTML + transcript), four interchangeable rosters.
- **Mode 1 · Models:** real OpenRouter dispatch, latest flagship per lab resolved live;
  capability detection + honesty banner (never silently simulates).
- **Mode 2 · Figures:** 23-figure bench — 18 ported from council-of-high-intelligence +
  5 new (Jane Jacobs, Grace Hopper, Naval Ravikant, Paul Graham, Elon Musk); triads index.
- **Mode 3 · Styles:** the original skill, preserved as the regression anchor;
  opt-in extras (Systems Thinker, Inverter, Red Team).
- **Mode 4 · Mixed:** first-class; presets (Heavyweight / Red Team / Founder's Room) +
  custom builder; hybrid dispatch.
- **Cross-cutting:** "name-the-flaw-to-update" anti-conformity reviewer rule; dissent
  quota (counterfactual reviewer when >70% converge); per-member timeout + graceful
  degradation; report mode/honesty banner + epistemic diversity scorecard; chairman
  Kill Criteria + What-the-Council-Doesn't-Know sections; transcript metadata block.
- **Safety:** live skill snapshotted to `~/.claude/.skill-backups/llm-council-20260625/`;
  skill symlinked from this repo (single source of truth).
- **Tests:** 36 passing (pack validation + both scripts with mocked HTTP).

Backup of the pre-refactor skill: `~/.claude/.skill-backups/llm-council-20260625/`.
