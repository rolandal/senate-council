# Council — Architecture

How the skill works, inside and out. The runnable skill lives at
`~/.claude/skills/llm-council/` (symlink it to this repo's `skill/`, so the repo stays
the single source of truth).

## The one idea

A **council member is a tuple**: `{ label, model, system_prompt }`. The entire skill is
one deliberation engine that runs that tuple through four stages. The four *modes* differ
only in **how the tuple is filled** — nothing else in the pipeline changes.

```
              ┌─────────────── one engine ───────────────┐
 mode picks → │ Frame → Convene (∥) → Peer-review (∥) → Chairman → Report │
              └───────────────────────────────────────────┘
 Models : vary model (real OpenRouter), identical neutral prompt
 Figures: vary system_prompt (persona),  model = Claude/Opus
 Styles : vary system_prompt (lens),     model = Claude/Opus   ← original skill
 Mixed  : both vary, per seat (hybrid dispatch)
 Senate : the whole house (~36 seats); a caucus+clerk map-reduce adds an
          intermediate layer (committees → floor) so the chairman never sees
          more than ~6 briefs. Output = exact vote tally + named factions + verdict.
```

## Stages

0. **Mode select + capability detect** (`SKILL.md` Stage 0). Parse `council me [mode]`;
   if no mode, show the 4-option `AskUserQuestion` picker. For Models/Mixed, run
   `scripts/detect-providers.sh` → `{openrouter_key, clis, claude_models, tier}`.
1. **Frame** — lazy-load context (prior councils), produce a
   neutral framing used verbatim by every member. ≤3 clarifying questions, 30s budget.
2. **Convene (parallel)** — N members answer the framed question simultaneously.
   - Figures/Styles → parallel `Agent` subagents, prompt = `universal_preamble + member_body`.
   - Models → `python3 scripts/council_models.py --prompt-file <f>` (one OpenRouter call
     per seat, concurrent, per-seat timeout, graceful degradation; ≥3 ok to proceed).
   - Mixed → model seats via the script, figure/style seats via subagents, merged.
3. **Anonymous peer review (parallel)** — responses relabeled Response A–E (randomized
   map kept private); reviewers judge on content only. Reviewer prompt carries the
   *name-the-flaw-to-update* anti-conformity directive. If >70% converge, a
   **counterfactual reviewer** is injected (dissent quota). Skipped in express mode.
4. **Chairman synthesis** (`model: opus`) — receives de-anonymized members + reviews,
   emits the 7-section verdict: Agrees · Clashes · Blind Spots · Recommendation ·
   One Thing First · **Kill Criteria** · **What the Council Doesn't Know**.

Output: `~/Documents/Local/council-log/council-YYYY-MM-DD-<slug>.html` (dark-glass report
with mode/honesty banner + epistemic diversity scorecard) and `…-transcript.md` (full
transcript + anonymization map + a `schema_version:1` metadata block).

## File map (`skill/`)

| Path | Role |
|------|------|
| `SKILL.md` | the orchestrator: triggers, Stage 0 router, all 4 stages, model strategy |
| `prompts.md` | shared universal preamble · reviewer (+ anti-conformity, dissent quota) · counterfactual reviewer · 7-section chairman |
| `packs/styles/{default,extras}.md` | Mode 3 lenses |
| `packs/figures/<slug>.md` + `triads.md` | Mode 2: 23-figure bench + triads/polarity index |
| `packs/models/roster.md` | Mode 1: latest model per lab (resolved live) |
| `packs/mixed/presets.md` | Mode 4: presets + custom builder |
| `packs/senate/{roster,committees,prompts}.md` | Mode 5: union roster, committee sort, ballot/clerk/whip/chairman prompts |
| `scripts/assign_committees.py` | Mode 5: pure balanced-committee sort |
| `scripts/tally_ballots.py` | Mode 5: pure ballot parse + exact tally |
| `scripts/check_inputs.py` | Mode 5: input-integrity gate after convene — verifies every member prompt contained the framed question; fails (exits non-zero) on the silent-confabulation failure where a seat votes on an empty/undefined question |
| `scripts/check_quorum.py` | Mode 5: roster-integrity gate before reduce — fails on quorum shortfall **or** whole-kind drop (exits non-zero) |
| `scripts/render_report.py` | all modes: fill `report-template.html` from a bundle → HTML + transcript |
| `scripts/detect-providers.sh` | capability detection → JSON tier |
| `scripts/resolve_models.py` | OpenRouter `/models` → newest flagship per lab → roster.md |
| `scripts/council_models.py` | parallel OpenRouter dispatch → JSON results |
| `report-template.html` | dark-glass HTML scaffold w/ `{{placeholders}}` |

## Modes in detail

- **Models** — `resolve_models.py` pins the newest GA model per lab (openai/google/x-ai/
  anthropic + one breadth lab) from the live OpenRouter catalog; chair = Claude Opus.
  Real cross-vendor answers make the anonymized peer review genuinely meaningful. Key:
  env `OPENROUTER_API_KEY` or `~/.claude/.openrouter-key` (chmod 600). **Never silently
  simulates** — the banner states the real tier + exact model IDs.
- **Figures** — 23 bench personas (18 ported from council-of-high-intelligence + Jacobs,
  Hopper, Naval, Graham, Musk). Default panel: Socrates · Feynman · Munger · Taleb ·
  Torvalds. Sub (`swap X→Y`), add (`+name`, grow ≤8), or a zero-config triad.
- **Styles** — original 5 lenses (Contrarian, First-Principles, Expansionist, Outsider,
  Executor); opt-in extras (Systems Thinker,
  Inverter, Red Team). This is the regression anchor: output shape unchanged from the
  pre-refactor skill.
- **Mixed** — hand-pick across all packs; 3 presets or a custom multiSelect builder;
  hybrid dispatch; banner lists each seat's true backing.

## Resilience & honesty invariants

- Per-member timeout + graceful degradation (≥3 results to proceed) + chairman fallback.
- Universal anti-sycophancy preamble on every member, every mode.
- Anonymized A–E peer review retained across all modes.
- Keys never printed or committed; a pre-commit grep guards against leaking secrets.

## Testing

`tests/` (pytest, run via `.venv`): `test_packs.py` validates every figure's frontmatter
+ sections + the default panel; `test_resolve_models.py` and `test_council_models.py`
cover the scripts with mocked HTTP (no network, no key). 36 tests.

## Provenance

Adapted from Andrej Karpathy's LLM Council (the multi-model method + anonymized
cross-review) and 0xNyk/council-of-high-intelligence (the figure-pack format). Built on
Roland's pre-existing `llm-council` thinking-styles skill, which became Mode 3.
