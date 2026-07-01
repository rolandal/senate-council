# Council (llm-council skill)

A 5-mode AI decision council for high-stakes calls. Trigger: **`council me`**.

## Modes

| Say | You get |
|-----|---------|
| `council me` | a picker → choose Models / Figures / Styles / Mixed / Senate |
| `council me models` | real frontier models (GPT · Gemini · Grok · Claude) debate via OpenRouter |
| `council me figures` | history's great minds debate (default: Socrates · Feynman · Munger · Taleb · Torvalds) |
| `council me styles` | thinking lenses debate (Contrarian · First-Principles · Expansionist · Outsider · Executor) |
| `council me mixed` | a hand-picked panel across all three (preset or custom) |
| `council me senate` | the whole house (~36 seats) votes on an ultra-hard call → exact tally + factions + verdict |

Legacy triggers (`council this`, `war room this`, `pressure-test this`, `/council`, …) still work and default to **Styles**.

## Modifiers

- `express` — 3 members, skip peer review (fast).
- Senate tiers: `senate` (default), `senate max` (all Opus), `senate express` (Sonnet members, skip brief review).
- `fast` — cheaper models for members, Opus chairman.
- Figures: `swap taleb→musk`, `+naval +graham` (grow ≤8), or a triad (`decision`, `startup`, `strategy`, `ai-strategy`, `design`, `first-principles`, `wisdom`, `systems`, `execution`, `economics`).
- `--deploy` — also publish the HTML verdict to Vercel.

## Models mode setup (one time)

```bash
echo 'sk-or-...' > ~/.claude/.openrouter-key && chmod 600 ~/.claude/.openrouter-key
python3 ~/.claude/skills/llm-council/scripts/resolve_models.py --write --date $(date +%F)
```
The skill reads the key from that file (or `OPENROUTER_API_KEY`). It **never** simulates models silently — the report banner states the real tier and exact model IDs.

## Output

Two files in `~/Documents/Local/council-log/`: a dark-glass HTML report (delivered in chat) and a full markdown transcript. See `../ARCHITECTURE.md` for internals.

## Tests

```bash
cd senate-council && .venv/bin/python -m pytest tests/ -q
```
