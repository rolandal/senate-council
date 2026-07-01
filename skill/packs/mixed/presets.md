---
pack: mixed
mode: mixed
description: >
  Mode 4 (Mixed) — hand-pick a panel across models + figures + styles, the one configuration
  the pure modes can't express. Model seats dispatch via scripts/council_models.py; figure/style
  seats via native Agent subagents; all merge into one response set before the anonymized A–E
  peer review. The honesty banner lists each seat's true backing.
---

# Mixed — Presets & Custom Builder

## Builder flow (two taps)

1. **Preset or custom?** (`AskUserQuestion`) → pick a preset below, or "Custom".
2. **Custom** → second `AskUserQuestion` (`multiSelect: true`) over a curated shortlist
   spanning all packs; include one model seat by default if a key exists. Cap the panel at ~7.

Each seat is `{label, kind, source}` where `kind ∈ {model, figure, style}`:
- `model` → dispatched via `council_models.py` (real OpenRouter model)
- `figure` → native `Agent` subagent loading `packs/figures/<slug>.md`
- `style`  → native `Agent` subagent loading the lens from `packs/styles/*`

## Preset 1 — Heavyweight (default)

A strong, general high-stakes panel: one real frontier model + two sharp human minds + two structural lenses.

| Seat | Kind | Source |
|------|------|--------|
| Top frontier model | model | first seat in `packs/models/roster.md` |
| Charlie Munger | figure | `packs/figures/munger.md` |
| Richard Feynman | figure | `packs/figures/feynman.md` |
| The Contrarian | style | `packs/styles/default.md` |
| The Executor | style | `packs/styles/default.md` |

## Preset 2 — Red Team

Adversarial pressure for competitive / security / trust / launch decisions.

| Seat | Kind | Source |
|------|------|--------|
| Grok (or top model) | model | a roster seat (prefer the bluntest available) |
| Machiavelli | figure | `packs/figures/machiavelli.md` |
| Sun Tzu | figure | `packs/figures/sun-tzu.md` |
| The Red Team | style | `packs/styles/extras.md` |
| The Contrarian | style | `packs/styles/default.md` |

## Preset 3 — Founder's Room

0→1 / growth / founder calls: leverage, makers, velocity, first-principles, plus a real model.

| Seat | Kind | Source |
|------|------|--------|
| Naval Ravikant | figure | `packs/figures/naval.md` |
| Paul Graham | figure | `packs/figures/graham.md` |
| Elon Musk | figure | `packs/figures/musk.md` |
| The First Principles Thinker | style | `packs/styles/default.md` |
| Top frontier model | model | first seat in `packs/models/roster.md` |

## Custom shortlist (curated, for the multiSelect builder)

- **Models:** the resolved roster seats (GPT / Gemini / Grok / Claude / breadth).
- **Figures:** socrates · feynman · munger · taleb · torvalds · naval · graham · musk · machiavelli · sun-tzu · meadows · kahneman (offer the full 23 bench on request).
- **Styles:** contrarian · first-principles · expansionist · outsider · executor · systems-thinker · inverter · red-team.

If the panel has 0 model seats and a key exists, suggest adding one for genuine cross-substrate diversity. If no key, all-figure/all-style is fine — note it in the banner.
