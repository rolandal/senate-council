#!/usr/bin/env python3
"""Dispatch one Council prompt to every model seat in parallel via OpenRouter.

Usage:
  python3 council_models.py --prompt-file framed.txt [--roster ../packs/models/roster.md]
                            [--timeout 90] [--seats 4] [--retries 1]

Prints a JSON array, one object per seat:
  [{"seat":0,"label":"GPT-5.1","model_id":"openai/gpt-5.1","ok":true,
    "content":"...","latency_ms":1234,"error":null,"attempts":1,
    "usage":{"prompt_tokens":123,"completion_tokens":45,"total_tokens":168}}, ...]

Stdlib only (urllib + asyncio + threads). Graceful degradation: a failed seat
returns ok=false with the error string from its LAST attempt and never raises;
the caller proceeds as long as >=3 seats are ok. --retries sets the number of
EXTRA attempts per seat after a failure (default 1 = try twice total), with a
1.5*attempt second backoff between attempts. Every seat result also carries
"attempts" (int) and "usage" (the OpenRouter usage dict, or null). The key is
never printed.
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
    """Blocking POST to OpenRouter; returns (content, usage_dict_or_None)."""
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
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage")
    return content, usage


def _call_with_retries(model_id, prompt, key, timeout, retries):
    """Blocking. Calls _post up to (retries + 1) times with 1.5*attempt backoff
    between attempts. Returns (content, usage, attempts, error) — error is None
    on success, else the string form of the LAST exception seen.
    """
    attempts = 0
    last_err = None
    max_attempts = max(1, retries + 1)
    while attempts < max_attempts:
        attempts += 1
        try:
            content, usage = _post(model_id, prompt, key, timeout)
            return content, usage, attempts, None
        except Exception as e:  # noqa: BLE001 — graceful degradation is the whole point
            last_err = f"{type(e).__name__}: {e}"
            if attempts < max_attempts:
                time.sleep(1.5 * attempts)
    return None, None, attempts, last_err


async def query_model(seat, prompt, key, timeout, retries=1):
    """Run one seat; never raises. Returns the seat result dict."""
    start = time.time()
    out = {"seat": seat["_i"], "label": seat["label"], "model_id": seat["model_id"],
           "ok": False, "content": "", "latency_ms": 0, "error": None, "ballot": None,
           "attempts": 0, "usage": None}
    try:
        content, usage, attempts, err = await asyncio.to_thread(
            _call_with_retries, seat["model_id"], prompt, key, timeout, retries,
        )
        out["attempts"] = attempts
        if err is None:
            out["ok"] = True
            out["content"] = content
            out["usage"] = usage
            out["ballot"] = parse_ballot(content)
        else:
            out["error"] = err
    except Exception as e:  # noqa: BLE001 — graceful degradation is the whole point
        out["error"] = f"{type(e).__name__}: {e}"
    out["latency_ms"] = int((time.time() - start) * 1000)
    return out


async def run_council(prompt, seats, key, timeout, retries=1):
    tasks = [query_model(s, prompt, key, timeout, retries) for s in seats]
    return await asyncio.gather(*tasks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--roster", default=str(DEFAULT_ROSTER))
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--seats", type=int, default=0, help="limit to first N seats (0 = all)")
    ap.add_argument("--retries", type=int, default=1,
                    help="extra attempts per seat after a failure (default 1 = try twice total)")
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
    results = asyncio.run(run_council(prompt, seats, key, args.timeout, args.retries))
    ok = [r for r in results if r["ok"]]
    if len(ok) < MIN_OK:
        # still print results so the caller can show errors, but flag via exit code
        print(json.dumps(results, indent=2))
        raise SystemExit(f"Only {len(ok)}/{len(results)} seats succeeded (need >= {MIN_OK}).")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
