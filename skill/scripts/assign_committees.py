#!/usr/bin/env python3
"""Sort the Senate roster into balanced, diverse committees.

Seats are grouped by kind (model -> style -> figure) then round-robin assigned,
so the scarce, high-value kinds (real models, then styles) spread across
distinct committees instead of clumping. Pure and deterministic: same roster in
-> same committees out. No agent, no network.

  python3 assign_committees.py --roster-file roster.json [--size 6]
"""
import argparse
import json
import math

KIND_ORDER = {"model": 0, "style": 1, "figure": 2}


def assign_committees(seats, size=6):
    """Return ceil(len(seats)/size) committees: balanced, kind-spread, deterministic."""
    n = len(seats)
    if n == 0:
        return []
    k = math.ceil(n / size)
    ordered = sorted(
        enumerate(seats),
        key=lambda t: (KIND_ORDER.get(t[1].get("kind"), 99), t[0]),
    )
    committees = [[] for _ in range(k)]
    for pos, (_orig_i, seat) in enumerate(ordered):
        committees[pos % k].append(seat)
    return committees


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster-file", required=True,
                    help="JSON array of seats, each {label, kind, ...}")
    ap.add_argument("--size", type=int, default=6)
    args = ap.parse_args()
    seats = json.loads(open(args.roster_file).read())
    committees = assign_committees(seats, args.size)
    print(json.dumps([[s.get("label") for s in c] for c in committees], indent=2))


if __name__ == "__main__":
    main()
