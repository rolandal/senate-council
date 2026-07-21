# 🏛️ Council

**Pressure-test your hardest decisions against a council that's built to disagree with you.**

![Claude Code skill](https://img.shields.io/badge/Claude_Code-skill-da7756)
![modes](https://img.shields.io/badge/modes-5-00e87a)
![Senate](https://img.shields.io/badge/Senate-~36_seats-00b0ff)
![tests](https://img.shields.io/badge/tests-169_passing-2ea44f)
![license](https://img.shields.io/badge/license-MIT-blue)

**Made by [Roland Ligtenberg](https://github.com/rolandal) &nbsp;·&nbsp; built with his agent [`roland.bot`](http://roland.bot) 🤖**

> Most AI tells you what you want to hear. A Council is engineered to do the opposite — a panel of advisors attacks your decision from every angle, anonymously peer-reviews each other, and a chairman hands down a verdict that can overrule the majority. No yes-men. No "it depends."

A [Claude Code](https://claude.com/claude-code) skill. One trigger — **`council me`** — and a high-stakes call gets the scrutiny you'd get from a room full of brilliant, opinionated people who have zero incentive to flatter you.

---

## Why it exists

LLMs are agreeable by default. Ask one whether your plan is good and it usually finds a way to say yes. That's worse than useless when being wrong is *expensive* — pricing, a pivot, a hire, a launch, *"should I X or Y?"*

Council fixes that with three rules baked into every run:

1. **Every advisor is ordered to disagree** when their lens warrants it. Anti-sycophancy isn't a vibe — it's in the prompt of all ~36 seats.
2. **Peer review is anonymized.** Advisors critique each other as "Response A–F," so ideas win on merit, not on whose name is attached.
3. **The chairman can side with a lone dissenter** against the whole house. Best reasoning wins, not the popular vote — and when the verdict overrules the vote, it says so out loud.

The output isn't a summary of opinions. It's a decision you can act on — plus the dated conditions that would prove it wrong.

---

## Five rosters, one engine

Every mode runs the same pipeline. Only *who sits on the council* changes.

| Say… | Your council is… |
|---|---|
| **`council me models`** | real frontier models — GPT · Gemini · Grok · Claude · DeepSeek — debating live via OpenRouter |
| **`council me figures`** | 23 of history's great minds (Socrates, Feynman, Munger, Taleb, Naval, Jane Jacobs, …) |
| **`council me styles`** | thinking lenses (Contrarian · First-Principles · Expansionist · Outsider · Executor · …) |
| **`council me mixed`** | a hand-picked panel spanning models + figures + lenses |
| **`council me senate`** | **the whole house — ~36 seats** — votes on an ultra-hard call |

Bare triggers — `council this`, `war room this`, `pressure-test this`, `/council`, *"I'm torn between X and Y"* — also work and default to Styles.

---

## The Senate

For the calls that actually keep you up at night. The Senate convenes **every advisor in the house** — all 23 figures, every thinking lens, and the real models — has each cast a structured **ballot**, then compresses the floor through a caucus so the chairman never drowns in 36 raw opinions:

```
~36 advisors  ──ballot──▶  exact tally + confidence spread
     │
     ├─▶ Clerk          names the 2–4 voting factions + the fault line
     ├─▶ 6 Committees    each Whip writes one brief ──▶ anonymized peer review
     │
     └─▶ Chairman ──▶ a 9-section verdict:
            The Vote · The Faction Map · Agrees · Clashes · Blind Spots ·
            The Recommendation · The One Thing To Do First ·
            Kill Criteria · What the Council Doesn't Know
```

You get an **exact vote**, **named factions** with the crux that divides them, and a recommendation that may overrule the tally — with the gap between vote and verdict surfaced as signal:

```
⚖️  The Vote — 36 seats · leader: BOOTSTRAP
   ███████░░░░░░░░░░░░░░░░░░░░░  Raise      14   (conf 3.8)
   ░░░░░░░██████████████████░░░  Bootstrap  19   (conf 4.1)
   ░░░░░░░░░░░░░░░░░░░░░░░░░███  Abstain     3
```

---

## What makes the verdict trustworthy

- **🛡️ The Advocate seat** — whenever you're leaning a certain way, one seat is *required* to make the strongest good-faith case **for your position**. A converging house can't quietly bury your instinct; it gets defended on the merits, or overruled honestly.
- **🔥 Dissent quota** — if the house agrees too fast (>70%), a counterfactual reviewer is seated specifically to argue the consensus is wrong.
- **🚦 Quorum gate** — a verdict is *never* synthesized on a short house. If seats silently drop — even a whole category, like all the model seats — the run hard-stops instead of quietly deciding on partial input.
- **🎭 Mode honesty** — Models mode never fakes a model. No API key → it says so and offers a real alternative; the report banner states the exact tier and model IDs.
- **🎯 Falsifiable by design** — every verdict ends with dated **Kill Criteria** and an honest list of what the council *didn't* know.

---

## What you get

Two artifacts per run, in `~/Documents/Local/council-log/`:

- a **dark-glassmorphism HTML report** — vote bar, faction cards, every advisor's argument, the chairman's verdict — delivered straight to your chat, and
- a **full markdown transcript** with the anonymization map and a machine-readable metadata block.

---

## Quickstart

It's a Claude Code skill — drop it in and talk to it.

```bash
# 1. clone and symlink the skill into Claude Code
git clone https://github.com/rolandal/senate-council
ln -s "$PWD/senate-council/skill" ~/.claude/skills/llm-council

# 2. (optional) enable real-model debates
echo 'sk-or-...' > ~/.claude/.openrouter-key && chmod 600 ~/.claude/.openrouter-key
python3 ~/.claude/skills/llm-council/scripts/resolve_models.py --write --date $(date +%F)
```

Then, in Claude Code:

```
council me senate
> Should we raise our seed round now, or bootstrap another six months?
```

### Modifiers

- `express` — 3 advisors, skip peer review (fast).
- **Senate tiers** — `senate` (default · Sonnet members, Opus reduce), `senate max` (all Opus), `senate express` (skip brief review).
- `fast` — cheaper member models, Opus chairman.
- **Figures** — `swap taleb→musk`, `+naval +graham` (grow ≤8), or a triad (`startup`, `strategy`, `wisdom`, `systems`, `execution`, …).
- `--deploy` — also publish the HTML verdict to a shareable URL.

---

## How the engine works

Modes 1–4 share a four-stage pipeline:

```
Frame ─▶ Convene (∥ advisors) ─▶ Anonymized peer review ─▶ Chairman synthesis ─▶ HTML + transcript
```

The Senate swaps stages 2–4 for the caucus map-reduce shown above. Every member prompt carries the same anti-sycophancy preamble; the chairman is the only seat that sees the whole picture, and it's instructed to pick a side, not hedge. Full internals in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Repo layout

| Path | What |
|---|---|
| `skill/SKILL.md` | the orchestration playbook Claude follows |
| `skill/packs/` | the rosters — `figures/` (23) · `styles/` · `models/` · `mixed/` · `senate/` |
| `skill/scripts/` | pure helpers — OpenRouter dispatch, ballot tally, committee sort, input gate, quorum gate, report renderer |
| `skill/report-template.html` | the dark-glass report scaffold |
| `tests/` | 169 tests — pack contracts, tally/committee/quorum/input-gate logic, renderer, golden snapshot |
| `ARCHITECTURE.md` · `CHANGELOG.md` | how it works · history |

```bash
cd senate-council && .venv/bin/python -m pytest tests/ -q   # 169 passed
```

---

## Credits

Adapted from [Andrej Karpathy's LLM Council](https://github.com/karpathy/llm-council) and the [council-of-high-intelligence](https://github.com/0xNyk/council-of-high-intelligence) figure pack, then rebuilt as a Claude Code skill with structured ballots, a full-house Senate, and an anti-sycophancy spine.

## License

[MIT](LICENSE) © 2026 Roland Ligtenberg. Use it, fork it, build on it.
