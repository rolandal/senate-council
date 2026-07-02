---
name: llm-council
description: Use when facing a high-stakes decision with genuine uncertainty and meaningful tradeoffs — pricing, positioning, hire-vs-build, launch-vs-delay, product scope, pivots, copy critique, or any judgment call where being wrong is expensive. A council of advisors thinks from different angles, anonymously peer-reviews each other, and a chairman synthesizes a verdict. Five modes — council members can be different LLM MODELS, historical FIGURES, thinking STYLES, a MIXED panel, or a full SENATE (the whole ~36-seat house votes on ultra-hard calls). Explicit triggers — "council me", "council this", "/council", "run the council", "war room this", "pressure-test this", "stress-test this", "debate this", "convene the senate", "senate this", "I'm torn between X and Y", "should I X or Y" with real stakes. Do NOT trigger on factual lookups, content creation, summaries, or trivial yes/no decisions with one right answer.
---

# Council

## Overview

A council of advisors thinks about a decision from fundamentally different angles, anonymously peer-reviews each other, then a chairman synthesizes a verdict. Built to fight Claude's default agreeability — every advisor is hard-instructed to disagree with the user when their lens calls for it.

**One engine, four rosters.** A council member is a `{label, model, system_prompt}` tuple. The 4-stage pipeline (Frame → parallel Convene → anonymized A–E peer review → Opus chairman → HTML + transcript) is identical across all modes. Only *who sits on the council* changes:

| Mode | Members are… | How |
|------|--------------|-----|
| **1 · Models** | different real LLM models, named after the model | OpenRouter API calls (`scripts/council_models.py`) |
| **2 · Figures** | historical great minds (Socrates, Feynman, Munger, Naval, Elon…) | native Claude subagents w/ personas (`packs/figures/`) |
| **3 · Styles** | thinking lenses (Contrarian, Outsider…) | native Claude subagents w/ lenses (`packs/styles/`) |
| **4 · Mixed** | a hand-picked panel across all of the above | hybrid dispatch (`packs/mixed/presets.md`) |
| **5 · Senate** | the whole house — all figures + styles + models (~36) | full-house map-reduce (`packs/senate/`) |

Adapted from Andrej Karpathy's LLM Council methodology and the council-of-high-intelligence figure pack.

## When to Use

| Use council for | Skip council for |
|---|---|
| Pricing decisions ($97 vs $497) | Factual lookups ("what's X?") |
| Positioning / messaging angles | Content creation ("write me a tweet") |
| Hire vs build vs delay | Summaries / extractions |
| Product scope or pivot calls | Trivial yes/no with one right answer |
| Launch readiness, copy critique | Anything you've already decided and want validated |

**Rule of thumb:** Council only if being wrong is expensive AND you're willing to change your mind.

## Critical Behaviors (Non-Negotiable)

1. **Spawn members in parallel.** Single message with N parallel tool calls (Agent for figures/styles; one `council_models.py` run for models). Sequential = context bleed = wasted run.
2. **Anonymize for peer review.** Reviewers see Response A–E with randomized mapping. Otherwise they defer to "the Contrarian" / "GPT-5" instead of evaluating on merit.
3. **The chairman can side with one dissenter against a majority.** Best reasoning wins, not popular vote.
4. **Every member prompt explicitly orders them to disagree with the user when their lens warrants it.** This is the anti-sycophancy hardening — without it the skill is just brainstorming. Applies to ALL modes (the persona/model only colors *how* they disagree).
5. **Never substitute the chairman's "I think..."** — the chairman synthesizes the members, not its own view.
6. **Mode honesty.** The report and transcript always state the true mode + tier. Models mode NEVER silently simulates — if no key, it says so and offers a real alternative.
7. **Always seat an Advocate for the user's current leaning** (when one is detectable). One extra seat whose job is the strongest good-faith case FOR the user's instinct — so it gets a brief and a ballot, not just a reviewer footnote. Without it, a converging house can bury the user's own position with no one defending it on the merits. See *The Advocate Seat*.
8. **Embed the question in every member prompt, then VERIFY it arrived.** Build each member's prompt with the framed question as literal text inside it — never rely on a side channel (a workflow `args` object, an env var, an unfilled template variable) that can silently be empty. The failure is invisible: if the question doesn't reach a member, the model does *not* error — it confabulates a plausible answer from whatever breadcrumbs are in the prompt and casts a real-looking ballot, so the run looks fine and is worthless. Post-hoc "does the response look off?" checks can't catch this; confabulation is built to look real. So after assembling the member prompts and **before** dispatching (or at the latest before the reduce), dump them as `[{label, prompt}]` and run `python3 scripts/check_inputs.py --prompts-file <prompts.json> --framed-file <framed.txt>` — it fails loudly listing any seat whose prompt does not contain the framed question. Do not trust a run until this gate passes. (Spot-check is not enough; gate every seat.)

## Stage 0: Mode Selection + Capability Detection (NEW)

**A. Parse the trigger.**
- `council me models` / `/council figures` / `council this styles` / `council me mixed` / `council me senate` → mode is explicit; skip the picker.
- Senate tier flags: `senate` = Tiered (default), `senate max` = all-Opus, `senate express` = Sonnet members + skip brief review. Senate triggers: `council me senate`, `council me 5`, "senate this", "convene the senate", "the whole house/council", "everyone weighs in".
- Bare back-compat triggers (`council this`, `/council`, `war room this`, `pressure-test this`, `stress-test this`, `debate this`, `I'm torn…`) with NO mode word → **default to Styles** (preserves prior behavior).
- `council me` with no mode → **show the picker** (step B).

**B. The picker** — a two-step `AskUserQuestion` flow (each question ≤4 options, the tool's hard limit).

Step 1 — pick the council kind:

```
Pick your council:
  1. Models   — GPT · Gemini · Grok · Claude debate (real frontier models)
  2. Figures  — history's great minds debate (Socrates · Feynman · Munger · …)
  3. Styles   — thinking lenses debate (Contrarian · First-Principles · Outsider · …)
  4. Full-house panels — a panel spanning all of the above (Mixed or Senate)
```

If the user picks **4 · Full-house panels**, ask Step 2:

```
Which full-house panel?
  1. Mixed   — hand-pick a panel across Models / Figures / Styles
  2. Senate  — the whole house (~36 seats) votes on an ultra-hard call
```

(An explicit `council me mixed` / `council me senate` skips both steps and goes straight to that mode.)

**C. Capability detection** (only for Models / Mixed): run `bash scripts/detect-providers.sh` → JSON `{openrouter_key, clis, claude_models, tier, roster_resolved_at, roster_age_days, roster_stale}`.
- `tier == "real"` → proceed with OpenRouter.
- no key → tell the user the exact setup line (`echo 'sk-or-...' > ~/.claude/.openrouter-key && chmod 600 ~/.claude/.openrouter-key`) and offer to run **Figures** or **Styles** instead, OR an explicitly-labeled simulated run only if they confirm. Never silently simulate.
- `roster_stale == true` (roster not re-resolved in the last 30 days) → warn the user and suggest `python3 scripts/resolve_models.py --write --date <today>` before a Models/Mixed/Senate run. Warn, do not block — proceed on the existing roster if they decline.

**D. Roster selection** (mode-specific):
- **Styles:** default pack from `packs/styles/default.md`; add opt-in lenses from `packs/styles/extras.md` via `+systems`/`+inverter`/`+redteam`.
- **Figures:** default panel (Socrates, Feynman, Munger, Taleb, Torvalds) from `packs/figures/`; `swap X→Y` to sub; `+name` to add and grow (cap ~8); triads from `packs/figures/triads.md`.
- **Models:** roster from `packs/models/roster.md` (latest model per lab, resolved live).
- **Mixed:** preset or custom from `packs/mixed/presets.md`.

## Stage 1: Frame the Question

**A. Lazy-load context skills based on question content:**

| If the question mentions... | Load |
|---|---|
| "we already...", "last time...", past decisions | prior councils on this topic — check `council-log/index.json` (built by `scripts/build_index.py`) instead of grepping filenames |
| A new council convenes on a topic that overlaps a prior run | Check `council-log/kill-criteria.json` for overdue criteria on related topics (refreshed by `scripts/kill_criteria.py`) and surface them |

Also Glob workspace for `CLAUDE.md`, `memory/`, `docs/decisions/`, `council-log/`. Read the 2–3 most relevant files. **Time budget: 30 seconds max.**

**Shortcut — embed-direct.** If the orchestrator already has the relevant context loaded, embed a question-relevant subset directly into each member's prompt instead of re-loading. Note the choice in the transcript.

**B. Frame the question neutrally:** Core decision (1 sentence) · Key context (2–4 bullets) · What's at stake (1 sentence). If too vague to frame, ask **up to 3** clarifying questions via `AskUserQuestion`. Hard cap at 3. **Even when the question is framable, spend ONE clarifying question on the single highest-leverage unknown** — the fact that, if resolved, would most change the verdict. (For "we're overwhelmed / can't sustain this" decisions that's usually the resource/operator question: *is anyone else available to share the load?* A council that assumes a sole operator will burn a whole blind-spots section on it.) Save the framed question — it goes into every member + reviewer prompt verbatim.

**C. Seat the Advocate (mandatory when the user has a leaning).** If the user is
leaning toward a position ("I think I should X", "I'm inclined to X", "we decided
X and want to keep it", a stated current course), add **one extra seat** to the
roster whose fixed job is to make the strongest good-faith case FOR that position.
This is in *addition* to the normal roster — it does not replace a seat, it casts
its own ballot, and it can lose the vote; the point is that the user's instinct is
argued on the merits by someone, not left to a post-hoc reviewer.

- **Voice = whichever is stronger.** Realize the Advocate as either (a) a **figure**
  from the bench whose worldview is a natural, vivid champion of *this specific*
  position (e.g. restraint / "don't force it" → Lao Tzu or Watts; precaution /
  "don't risk the irreversible" → Taleb; "don't break what works" → Munger;
  bottom-up / lived experience → Jane Jacobs), given the Advocate job below; or
  (b) the position-agnostic **Advocate lens** (`packs/styles/extras.md`) when no
  figure is a clean fit. Pick the one that argues the position more compellingly.
- **It is one seat.** Label it clearly ("The Advocate" or "The Advocate (Lao Tzu)")
  so the tally, committee assignment, and quorum gate treat it as a single member
  (`kind: style` or `kind: figure`).
- **It does NOT soften the others.** Every other seat still attacks freely
  (Behavior 4). The Advocate is the counterweight that guarantees representation,
  not a thumb on the scale.
- If the user has **no** detectable leaning (genuinely torn / open), skip it and
  note that no Advocate was seated.

## Stage 2: Convene the Council (parallel)

Spawn all members in a **single message**. Each returns 150–300 words (300–500 at max effort).

- **Styles / Figures:** parallel `Agent` calls (`subagent_type: general-purpose`, model per Model Strategy). Build each prompt as `universal_preamble + member_body` with `{framed_question}` substituted.
- **Models:** write the framed question to a temp file and run `python3 scripts/council_models.py --prompt-file <file>` — it dispatches every seat to OpenRouter in parallel and returns a JSON array of responses.
- **Mixed:** model seats via `council_models.py`, figure/style seats via parallel `Agent` calls — merge into one response set before Stage 3.

The universal anti-sycophancy preamble (in `packs/styles/default.md` and `prompts.md`) is prepended to EVERY member, all modes.

**Input gate before trusting any response (MANDATORY, all modes).** After
assembling the member prompts and before dispatch, dump them as
`[{label, prompt}]` and run
`python3 scripts/check_inputs.py --prompts-file <prompts.json> --framed-file <framed.txt>`.
This is Critical Behavior 8 — it is not Senate-only; a Models/Figures/Styles/Mixed
run can confabulate on an empty question exactly the same way. Do not trust a run
until this gate passes.

## Stage 3: Anonymous Peer Review (parallel)

1. Collect all member responses.
2. Anonymize mechanically — never by hand. Write member responses to a temp file
   as a `[{label, content}]` JSON array (the script errors on entries missing a
   non-empty `label`/`content`) and run
   `python3 scripts/anonymize.py --responses-file <f> --seed <n>`; it
   shuffles deterministically, strips every identifying key, and returns
   `{anonymized, map, seed}`. Put the returned `map` verbatim into the bundle's
   `anonMap` (`render_report.py` accepts it as-is, or `{letter: committee-index}`
   ints) — it surfaces in the transcript metadata and the report's anonymization
   line, never in the reviewers' inputs. This replaces the old prose "shuffle
   them yourself" instruction.
3. Spawn reviewers in a **single message** (parallel `Agent` calls). Each answers: strongest response + why, biggest blind spot + what, what all missed. Reviewer prompt in `prompts.md` (includes the "name the flaw to update" anti-conformity directive and the dissent-quota rule).
4. **Dissent quota:** if >70% of members converge, inject one counterfactual reviewer ("assume the consensus is wrong — why?").

Skip this entire stage in **express mode**.

## Stage 4: Chairman Synthesis (1 agent)

One agent (model: `opus`) receives the framed question, all member responses **de-anonymized** (labeled), and all peer reviews. Output structure (template in `prompts.md`):
1. Where the Council Agrees
2. Where the Council Clashes
3. Blind Spots the Council Caught
4. The Recommendation (real answer, not "it depends" — may side with a lone dissenter)
5. The One Thing to Do First (single concrete next step)
6. **Kill Criteria** (dated with absolute calendar dates — ISO or "by <Month> <D>, <YYYY>", never relative phrases — falsifiable; what would prove this wrong)
7. **What the Council Doesn't Know** (the honest unknowns)

## Mode 5: Senate (full-house map-reduce)

The whole house on one ultra-hard call: ~36 cross-mode members → exact vote
tally + named factions + chairman synthesis. Senate overrides Stages 2-4 with a
two-level caucus+clerk reduce so the chairman never sees more than ~6 briefs.

**Roster** (`packs/senate/roster.md`): the union of every pack — all 23 figures
(`kind: figure`) + all 8 style lenses (`kind: style`) + all ~5 model seats (`kind: model`). No OpenRouter key → native
Senate (~31 seats), honesty banner states it. Capability detection reuses
`scripts/detect-providers.sh`.

**Tier strategy** (`packs/senate/roster.md`): `senate` (default Tiered: native
members on Sonnet, reduce layer Opus-max), `senate max` (all Opus-max),
`senate express` (Sonnet members, **skip Stage 3c**). Model seats always real.

**Stage 1 — Frame + ballot spec.** Frame as usual, and define a **ballot spec**:
named options (Option A/B/C), a YES/NO proposition, or `open` (members self-
declare; the clerk clusters). The ballot spec goes into every member prompt.

**Stage 2 — Convene with ballots (∥, batched).** Spawn all members in waves of
~12. Each prompt = universal preamble + member body + framed question + the
Ballot Instruction (`packs/senate/prompts.md`). Each member ends with
`BALLOT: stance=… | confidence=… | reason=…`. Dispatch: model seats via
`python3 scripts/council_models.py --prompt-file <f> --ballot` (ballots surface
in its JSON); figure/style seats via parallel `Agent` subagents.

**Input gate before trusting any ballot (MANDATORY — see Critical Behavior 8).**
The moment you've built the member prompts, dump them as `[{label, prompt}]` and
run `python3 scripts/check_inputs.py --prompts-file <prompts.json> --framed-file <framed.txt>`.
It **exits non-zero** if any seat's prompt does not contain the framed question —
the silent-confabulation failure that no response-level check can catch. This gate
runs *before* quorum: a house that voted on an empty question passes quorum (all
seats "returned") while being entirely worthless. If it fails, fix dispatch and
re-convene.

**Quorum gate before reducing (MANDATORY).** Assemble the dispatched roster and
the collected responses (each a seat with `{label, kind}`), then run
`python3 scripts/check_quorum.py --roster-file <seats.json> --responses-file <all_responses.json>`.
It **exits non-zero** if the returned share is below quorum (0.75) **or any whole
*kind* dropped** — the second guard is the trap a raw quorum misses: losing all 5
model seats is only 14% of a 36-seat house (86% still "passes"), yet it guts the
cross-model diversity that is the whole point of the Senate. Do NOT run the
clerk/whips until this gate passes; if it fails, fix dispatch and re-collect.
After any change to how seats are dispatched, sanity-check `tally.total` equals
the expected seat count before synthesizing. (`--strict` requires every seat.)

**Stage 3a — Clerk (1 agent, Opus).** Mechanically tally first:
`python3 scripts/tally_ballots.py --responses-file <all_responses.json>` →
exact counts + leader + confidence spread. **For a named-option ballot, pass
`--options A,B,C`** so `"Option C — …"`, `"Option C"`, and `"C"` canonicalize to
one stance (without it the vote fragments into separate buckets). Then the Clerk prompt
(`packs/senate/prompts.md`) names 2-4 factions from the ballot lines + tally.

**Stage 3b — Whips (∥, Opus).** Sort members into committees:
`python3 scripts/assign_committees.py --roster-file <seats.json> --size 6` → 6
balanced, diverse committees. One whip per committee writes a ~250-word brief +
mini-tally (Whip prompt).

**Stage 3c — Brief peer review (∥).** Relabel the 6 briefs mechanically — first
reshape each brief to `{label, content}` (e.g.
`{"label": "Committee 3", "content": <the brief's text>}`; the bundle's `briefs[]`
carry their prose under `text`, which anonymize.py rejects), write them as a JSON
array to `<briefs.json>`, then
`python3 scripts/anonymize.py --responses-file <briefs.json> --seed <n> --prefix "Response"`
— giving Response A–F (map kept out of the reviewers' inputs; put it in the
bundle's `anonMap` verbatim) — and run the existing
reviewer prompt. Inject the
counterfactual reviewer if briefs converge >70%. **Skipped in `senate express`.**

**Stage 4 — Chairman (1 agent, Opus).** The Extended Chairman prompt
(`packs/senate/prompts.md`) receives the framed question, the mechanical tally,
the faction map, the 6 committee briefs (de-anonymized), and the brief reviews —
never the 36 raw responses. It emits the 9-section verdict (the 7 standard
sections plus **The Vote** and **The Faction Map** first); the recommendation may
overrule the vote and must flag when it does.

**Output.** Fill the Senate-only template placeholders (`report-template.html`):
`{{senate_vote}}` (tally/distribution), `{{senate_factions}}` (faction cards),
`{{committee_briefs}}` (the 6 briefs, expandable). The transcript adds committee
assignments, clerk output, the 6 briefs, and a metadata block with `mode: senate`,
`tier_strategy`, `committee_map`, `tally`, `factions`, `anonymization_map`.

## Output

Two files per session, written to `~/Documents/Local/council-log/`:

```
council-YYYY-MM-DD-<slug>.html             # visual report (branding-pages dark style)
council-YYYY-MM-DD-<slug>-transcript.md    # full transcript + anonymization map + metadata block
```

**Render with the committed script — do NOT hand-template.** Write the run to a
bundle JSON (keys: `framed`, `tally`, `tallyStr`, `members[]`, `committees[]`,
`briefs[]`, `reviews[]`, `verdict`, `factions`, `anonMap`, `convergence`,
`stanceLabels`, and optionally `runStats`) and run:

> **`runStats` is optional** — `{seats, durationSec, tokens, modelSpend}`. When
> present and non-empty it renders one compact cost/latency line (e.g. "36 seats
> · 4m 12s · 41,203 tokens · ~$1.23 model spend") inside the honesty banner, in
> both the HTML and the transcript. Omit it and output is unchanged.

> **`stanceLabels` is question-specific — always set it.** The vote bar shows
> stance keys `A`/`B`/`C`, but what they *mean* is defined entirely by the ballot
> options of *this* question. Pass `stanceLabels` (e.g.
> `{"A": "Relocate", "B": "Stay put", "C": "Negotiate a middle path"}`) naming
> *this run's* options, or the legend falls back to generic defaults that won't
> match your question. There are no universal A/B/C labels.

```
python3 scripts/render_report.py --bundle-file <bundle.json> --slug <slug> \
  --raw-title "<the user's question>" [--mode Senate --tier <Tiered|max|express>] \
  [--native-model "Sonnet 4.6"] [--model-ids "openai/...,google/...,..."]
```

It fills `report-template.html` (vote bar, faction map, committee briefs, advisor
+ review cards, diversity scorecard, honesty banner), strips the template's
instruction comment, and writes both the HTML and the transcript (with the YAML
metadata block) to `--out-dir` (default `~/Documents/Local/council-log/`). It is
Senate-aware and **degrades cleanly for modes 1-4** (no committees → the
Senate-only blocks render empty; a 7-section verdict still maps). The one
contract it depends on: the chairman verdict uses rigid `## ` section headers.

After writing both files, run `python3 scripts/build_index.py` to refresh the
council-log index (`index.json` + `index.html`), then
`python3 scripts/kill_criteria.py --log-dir ~/Documents/Local/council-log` to
refresh the Kill Criteria ledger (`kill-criteria.json` + `.md`) with this run's
new criteria. Boxes checked off (`- [x]`) in `kill-criteria.md` survive the
refresh and drop out of the overdue/upcoming report — check a box to resolve a
criterion.

Then deliver the HTML via `SendUserFile` (`status: "proactive"`); optionally also `open` it.

### Run State & Resume

Recommended for every Senate run (any mode may use it). A full run walks a fixed
pipeline and a mid-run crash otherwise discards everything collected so far:

- At frame time: `python3 scripts/run_state.py init --slug <slug>` — creates a
  checkpoint dir with an empty manifest.
- After each stage completes: `python3 scripts/run_state.py save --run-dir <d> --stage <name> --file <f>`
  (stage names: `frame, prompts, gate_inputs, convene, gate_quorum, tally, committees, briefs, reviews, verdict, render`)
  — copies that stage's artifact into the checkpoint dir.
- On interruption/resume: `python3 scripts/run_state.py status --run-dir <d>`
  reports which stages are saved and the first missing stage to resume from.

### Optional Vercel Deploy
If invoked with `--deploy` or "share the verdict": copy the HTML into a Vercel project's `public/council/<slug>/index.html`, run `vercel --prod` from that project, and report the resulting `https://<your-project>.vercel.app/council/<slug>/` URL.

## Express Mode

`/council express` or "quick council" / "express council": 3 members only, **skip Stage 3 peer review**, chairman synthesizes directly. Works in any mode.

## Model Strategy

**Default: Opus on all agents at max effort.** Council questions are by definition high-stakes. Quality is the constraint, not cost.

| Phase | Default model | Why |
|---|---|---|
| Members (figures/styles) | opus | Each lens deserves depth |
| Members (models mode) | real models per `packs/models/roster.md` | the whole point is genuine model diversity |
| Reviewers | opus | "what did all miss" rewards reasoning power |
| Chairman | opus | synthesis is the hardest step |

In each prompt include: *"Think deeply, take the depth you need, this is a high-stakes decision."*

**Cost-optimized opt-in** (`/council fast` or "use sonnet for advisors"): drop figure/style members + reviewers to sonnet, keep chairman on opus. ~10× cheaper, ~80% quality. **Only when explicitly requested** — quality is the default.

## Red Flags — Stop and Reconsider

| Symptom | What it means | Fix |
|---|---|---|
| Council invoked on "what's the capital of X" | Trivial | Just answer it |
| "I'm definitely doing X, council this" | They want validation | Surface this back — council won't validate |
| All members agree from the start | Anti-sycophancy softened or question not contested | Re-run with stricter prompts; dissent quota should also fire |
| Chairman writes "it depends" | Synthesis failed | Re-run chairman with explicit "pick a side" |
| Council asks >3 clarifying questions | Framing failed | Best-guess frame and proceed |
| Models mode ran simulated without saying so | Honesty violation | NEVER allowed — banner must state the real tier |

## Files in This Skill

- `prompts.md` — shared universal preamble, reviewer prompt (with anti-conformity + dissent quota), chairman prompt (7-section verdict).
- `packs/styles/{default,extras}.md` — Mode 3 thinking-style lenses.
- `packs/figures/*.md` + `triads.md` — Mode 2 historical-figure bench (23 members).
- `packs/models/roster.md` — Mode 1 model roster (latest per lab, live-resolved).
- `packs/mixed/presets.md` — Mode 4 presets + custom builder.
- `scripts/detect-providers.sh` — capability detection → JSON.
- `scripts/resolve_models.py` — query OpenRouter, pin latest model per lab → roster.md.
- `scripts/council_models.py` — parallel OpenRouter dispatch → JSON.
- `scripts/tally_ballots.py` — parse member ballots → exact Senate tally.
- `scripts/assign_committees.py` — sort the roster into balanced, kind-diverse committees.
- `scripts/check_inputs.py` — input-integrity gate: verifies every member prompt actually contained the framed question (catches silent confabulation when the question doesn't reach a seat).
- `scripts/check_quorum.py` — roster-integrity gate before the reduce (fails on quorum shortfall **or** whole-kind drop).
- `scripts/anonymize.py` — mechanized A–Z anonymization for peer review (shuffle, strip identifying keys, return the map).
- `scripts/render_report.py` — fill `report-template.html` from a bundle → HTML + transcript (don't hand-template).
- `scripts/build_index.py` — scans `council-log/` and writes `index.json` + `index.html`, a searchable log of prior runs.
- `scripts/kill_criteria.py` — ledger of every chairman verdict's Kill Criteria across runs; flags overdue/upcoming.
- `scripts/run_state.py` — resumable run checkpoints (init/save/status) so an interrupted run resumes instead of restarting.
- `report-template.html` — dark glassmorphism HTML scaffold with placeholders.
