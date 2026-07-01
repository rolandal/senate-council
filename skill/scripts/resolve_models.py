#!/usr/bin/env python3
"""Resolve the latest flagship model per lab from OpenRouter's live catalog.

Usage:
  python3 resolve_models.py                 # print resolved roster JSON to stdout
  python3 resolve_models.py --write --date 2026-06-25   # also update packs/models/roster.md

Stdlib only. Reads the OpenRouter key via load_key() (env OPENROUTER_API_KEY or
~/.claude/.openrouter-key). Picks, per target vendor, the model with the newest
`created` timestamp after excluding non-flagship variants (mini/nano/flash-lite/
vision/embed/image/tts/free/etc.) AND verifying each pick is chat-servable.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

MODELS_URL = "https://openrouter.ai/api/v1/models"
KEYFILE = Path.home() / ".claude" / ".openrouter-key"
ROSTER = Path(__file__).resolve().parent.parent / "packs" / "models" / "roster.md"

# Target seats: 4 core labs + one breadth seat (first of the breadth vendors found).
CORE_VENDORS = ["openai", "google", "x-ai", "anthropic"]
BREADTH_VENDORS = ["deepseek", "meta-llama", "mistralai"]

EXCLUDE = re.compile(
    # word-boundaried so 'mini' matches 'gpt-5.1-mini' but NOT 'gemini'
    r"(\bmini\b|\bnano\b|\bflash\b|flash-lite|-lite\b|\blite\b|\bsmall\b|\btiny\b|"
    r"\bbuild\b|\bexp\b|\bbeta\b|\balpha\b|\bdraft\b|chat-latest|\bgemma\b|\bgpt-oss\b|"
    r"\blyria\b|customtools|\bclip\b|"
    r"embed|vision|image|\btts\b|whisper|moderation|guard|\bfree\b|audio|rerank|online|search)",
    re.I,
)
VENDOR_LABEL = {
    "openai": "GPT", "google": "Gemini", "x-ai": "Grok",
    "anthropic": "Claude", "deepseek": "DeepSeek",
    "meta-llama": "Llama", "mistralai": "Mistral",
}


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    if KEYFILE.is_file():
        k = KEYFILE.read_text().strip()
        if k:
            return k
    raise SystemExit(
        "No OpenRouter key. Set OPENROUTER_API_KEY or create ~/.claude/.openrouter-key "
        "(chmod 600). Get a key at https://openrouter.ai/keys"
    )


def fetch_models():
    req = urllib.request.Request(
        MODELS_URL, headers={"Authorization": f"Bearer {load_key()}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["data"]


def _pretty_label(vendor, model_id):
    """Derive a human label like 'GPT-5.1' or 'Claude Sonnet 4.6' from the id."""
    base = VENDOR_LABEL.get(vendor, vendor.title())
    tail = model_id.split("/", 1)[-1]
    # strip vendor word duplicated in slug, tidy separators
    tail = re.sub(r"^(gpt|gemini|grok|claude|deepseek|llama|mistral)[-_]?", "", tail, flags=re.I)
    tail = tail.replace("-", " ").strip()
    return f"{base} {tail}".strip()


CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


def _probe_chat(model_id, key, timeout=25):
    """Return True iff the model actually answers a minimal chat/completions call.
    Drops catalog ids that 404 or return a non-parseable body (e.g. some preview /
    reasoning-only models) so the roster only contains models our dispatcher can use."""
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 16,
    }).encode()
    req = urllib.request.Request(
        CHAT_URL, data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        return bool(data.get("choices"))
    except Exception:
        return False


def is_chat_servable(model_id):
    return _probe_chat(model_id, load_key())


def pick_latest_per_vendor(models, vendors, validate=None):
    """Return {vendor: {model_id, label}} picking the NEWEST non-variant model that is
    chat-servable. `validate(model_id) -> bool` checks servability; if None, validation is
    skipped (pick newest) — unit tests pass None to stay offline."""
    out = {}
    for vendor in vendors:
        cands = [
            m for m in models
            if m.get("id", "").startswith(vendor + "/")
            and not EXCLUDE.search(m["id"])
        ]
        cands.sort(key=lambda m: m.get("created", 0) or 0, reverse=True)  # newest first
        for m in cands:
            if validate is None or validate(m["id"]):
                out[vendor] = {"model_id": m["id"], "label": _pretty_label(vendor, m["id"])}
                break
    return out


def resolve(date, validate=None):
    models = fetch_models()
    if validate is None:
        key = load_key()
        validate = lambda mid: _probe_chat(mid, key)
    core = pick_latest_per_vendor(models, CORE_VENDORS, validate)
    breadth = pick_latest_per_vendor(models, BREADTH_VENDORS, validate)
    seats = []
    for v in CORE_VENDORS:
        if v in core:
            seats.append({"vendor": v, **core[v]})
    # add first available breadth seat
    for v in BREADTH_VENDORS:
        if v in breadth:
            seats.append({"vendor": v, **breadth[v]})
            break
    return {
        "resolved_at": date,
        "seats": seats,
        "chair": {"label": "Claude Opus", "native": True},
    }


def render_roster(data):
    seat_rows = "\n".join(
        f"| {s['label']} | `{s['model_id']}` | {s['vendor']} |" for s in data["seats"]
    )
    return f"""---
pack: models
mode: models
resolved_at: {data['resolved_at']}
description: >
  Mode 1 roster — the latest flagship model per lab, resolved live from the OpenRouter
  catalog by scripts/resolve_models.py. Re-run `python3 scripts/resolve_models.py --write
  --date <YYYY-MM-DD>` to refresh. Chair = Claude Opus (native).
---

# Models Roster (resolved {data['resolved_at']})

| Seat | OpenRouter model id | Lab |
|------|---------------------|-----|
{seat_rows}

**Chairman:** Claude Opus (native `Agent`, not OpenRouter).

```json
{json.dumps(data, indent=2)}
```
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="update packs/models/roster.md")
    ap.add_argument("--date", default="unknown", help="resolution date YYYY-MM-DD (caller supplies)")
    args = ap.parse_args()
    data = resolve(args.date)
    if args.write:
        ROSTER.parent.mkdir(parents=True, exist_ok=True)
        ROSTER.write_text(render_roster(data))
        print(f"Wrote {ROSTER} with {len(data['seats'])} seats:", file=sys.stderr)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
