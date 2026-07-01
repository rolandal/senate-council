#!/usr/bin/env python3
"""Dispatch one Council prompt to every model seat in parallel via OpenRouter.

Usage:
  python3 council_models.py --prompt-file framed.txt [--roster ../packs/models/roster.md]
                            [--timeout 90] [--seats 4]

Prints a JSON array, one object per seat:
  [{"seat":0,"label":"GPT-5.1","model_id":"openai/gpt-5.1","ok":true,
    "content":"...","latency_ms":1234,"error":null}, ...]

Stdlib only (urllib + asyncio + threads). Graceful degradation: a failed seat
returns ok=false with an error string and never raises; the caller proceeds as
long as >=3 seats are ok. The key is never printed.
"""
import argparse
import asyncio
import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

from tally_ballots import parse_ballot

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
KEYFILE = Path.home() / ".claude" / ".openrouter-key"
DEFAULT_ROSTER = Path(__file__).resolve().parent.parent / "packs" / "models" / "roster.md"
MIN_OK = 3

BALLOT_INSTRUCTION = (
    "\n\nAfter your analysis, end with EXACTLY one ballot line in this format:\n"
    "BALLOT: stance=<your position> | confidence=<1-5> | reason=<one short line>\n"
    "Put nothing after the ballot line."
)


def build_prompt(prompt, ballot):
    """Append the standard ballot instruction when running a Senate convene."""
    return prompt + BALLOT_INSTRUCTION if ballot else prompt


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


def load_roster(path):
    """Parse the fenced ```json block in roster.md -> dict with 'seats' and 'chair'."""
    text = Path(path).read_text()
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        raise SystemExit(f"No ```json roster block found in {path}. Run resolve_models.py --write first.")
    return json.loads(m.group(1))


def _post(model_id, prompt, key, timeout):
    """Blocking POST to OpenRouter; returns the assistant content string."""
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        CHAT_URL, data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


async def query_model(seat, prompt, key, timeout):
    """Run one seat; never raises. Returns the seat result dict."""
    start = time.time()
    out = {"seat": seat["_i"], "label": seat["label"], "model_id": seat["model_id"],
           "ok": False, "content": "", "latency_ms": 0, "error": None, "ballot": None}
    try:
        content = await asyncio.to_thread(_post, seat["model_id"], prompt, key, timeout)
        out["ok"] = True
        out["content"] = content
        out["ballot"] = parse_ballot(content)
    except Exception as e:  # noqa: BLE001 — graceful degradation is the whole point
        out["error"] = f"{type(e).__name__}: {e}"
    out["latency_ms"] = int((time.time() - start) * 1000)
    return out


async def run_council(prompt, seats, key, timeout):
    tasks = [query_model(s, prompt, key, timeout) for s in seats]
    return await asyncio.gather(*tasks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--roster", default=str(DEFAULT_ROSTER))
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--seats", type=int, default=0, help="limit to first N seats (0 = all)")
    ap.add_argument("--ballot", action="store_true",
                    help="append the Senate ballot instruction to the prompt")
    args = ap.parse_args()

    prompt = Path(args.prompt_file).read_text()
    prompt = build_prompt(prompt, args.ballot)
    roster = load_roster(args.roster)
    seats = roster["seats"]
    if args.seats:
        seats = seats[: args.seats]
    for i, s in enumerate(seats):
        s["_i"] = i

    key = load_key()
    results = asyncio.run(run_council(prompt, seats, key, args.timeout))
    ok = [r for r in results if r["ok"]]
    if len(ok) < MIN_OK:
        # still print results so the caller can show errors, but flag via exit code
        print(json.dumps(results, indent=2))
        raise SystemExit(f"Only {len(ok)}/{len(results)} seats succeeded (need >= {MIN_OK}).")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
