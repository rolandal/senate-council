#!/usr/bin/env python3
"""Mechanized anonymization for peer review — Critical Behavior 2 of SKILL.md.

Peer review requires each member to critique the OTHER responses without knowing
whose they are (no self-preference, no deference-to-model-prestige). Doing this by
prose instruction leaves the anonymization step to the orchestrating agent's
judgment — an unverified trust-the-agent step that could leak a label, a model_id,
or an ordering tell. This script mechanizes it: shuffle deterministically, strip
every identifying key, hand back only {anon, content} pairs plus the map needed to
de-anonymize after review.

  python3 anonymize.py --responses-file responses.json
  python3 anonymize.py --responses-file responses.json --seed 42 --prefix "Seat"
  python3 anonymize.py --responses-file responses.json --out anon.json

Input: JSON array of member-response objects, each with at least {label, content}
(other keys — model_id, ballot, kind, etc. — are ignored and stripped). A dict
entry missing a non-empty label or content raises ValueError — silently emitting
blank responses or a null map would defeat both peer review and de-anonymization
(Senate briefs keep their text under `text`; reshape them to {label, content}
first — see SKILL.md Stage 3c). Output is a JSON object {anonymized, map, seed} —
printed to stdout or written to --out. Stdlib only; --seed omitted means one is
generated (via os.urandom) and echoed back so the run is still reproducible after
the fact.
"""
import argparse
import json
import os
import random
import string
import sys

MAX_RESPONSES = 26


def make_seed():
    """Generate a seed from OS randomness, small enough to echo back cleanly."""
    return int.from_bytes(os.urandom(8), "big")


def anonymize(responses, seed, prefix="Response"):
    """Shuffle responses deterministically and strip identifying keys.

    Returns {"anonymized": [...], "map": {...}, "seed": seed}.
    """
    if not responses:
        raise ValueError("no responses to anonymize (empty input)")
    if len(responses) > MAX_RESPONSES:
        raise ValueError(f"{len(responses)} responses exceeds the {MAX_RESPONSES}-label limit (A-Z)")
    for i, resp in enumerate(responses):
        if not isinstance(resp, dict):
            continue
        if not resp.get("label"):
            raise ValueError(
                f"response {i} has no 'label' — input must be [{{label, content}}] objects "
                "(reshape Senate briefs to {label, content} first; see SKILL.md Stage 3c)")
        if not resp.get("content"):
            raise ValueError(
                f"response {i} ({resp['label']!r}) has no non-empty 'content' — input must be "
                "[{label, content}] objects (briefs carry their text under 'text'; "
                "reshape to {label, content} before anonymizing)")

    order = list(responses)
    random.Random(seed).shuffle(order)

    anonymized = []
    label_map = {}
    for letter, resp in zip(string.ascii_uppercase, order):
        anon_label = f"{prefix} {letter}"
        original_label = resp.get("label") if isinstance(resp, dict) else None
        content = resp.get("content", "") if isinstance(resp, dict) else str(resp)
        anonymized.append({"anon": anon_label, "content": content})
        label_map[anon_label] = original_label

    return {"anonymized": anonymized, "map": label_map, "seed": seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses-file", required=True,
                    help="JSON array of member-response objects, each with at least {label, content}")
    ap.add_argument("--seed", type=int, default=None,
                    help="seed for deterministic shuffling (omit to generate one; it is echoed in the output)")
    ap.add_argument("--prefix", default="Response", help="label prefix (default: 'Response' -> 'Response A')")
    ap.add_argument("--out", help="write JSON output here instead of stdout")
    args = ap.parse_args()

    responses = json.loads(open(args.responses_file).read())
    if not isinstance(responses, list):
        raise SystemExit("--responses-file must contain a JSON array of response objects")

    seed = args.seed if args.seed is not None else make_seed()
    try:
        result = anonymize(responses, seed, prefix=args.prefix)
    except ValueError as exc:
        raise SystemExit(str(exc))

    output = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
