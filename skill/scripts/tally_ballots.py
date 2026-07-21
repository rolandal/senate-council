#!/usr/bin/env python3
"""Parse Council member ballots and compute an exact Senate tally.

A member ends its response with one line:
  BALLOT: stance=<text> | confidence=<1-5> | reason=<one line>

parse_ballot() extracts that line (last one wins, key names case-insensitive).
A missing/unparseable line counts as an ABSTAIN — never raises. tally()
aggregates parsed ballots into exact counts, the confidence spread per stance,
and the leading stance. Stdlib only; usable as a library and from the CLI:

  python3 tally_ballots.py --responses-file responses.json
"""
import argparse
import json
import re
from collections import Counter, defaultdict


def parse_ballot(text):
    """Extract the last BALLOT line. Returns {stance, confidence, reason, ok}."""
    out = {"stance": None, "confidence": None, "reason": None, "ok": False}
    if not text:
        return out
    ballot_line = None
    for line in text.splitlines():
        # tolerate markdown wrapping (e.g. "**BALLOT: ...**", "> `BALLOT: ...`")
        stripped = line.strip().strip("*_`> ").strip()
        if re.match(r"BALLOT\s*:", stripped, re.IGNORECASE):
            ballot_line = stripped  # keep the last match
    if ballot_line is None:
        return out
    body = re.sub(r"^BALLOT\s*:\s*", "", ballot_line, flags=re.IGNORECASE)
    fields = {}
    for part in body.split("|"):
        if "=" in part:
            k, _, v = part.partition("=")
            fields[k.strip().lower()] = v.strip().strip("*_`").strip()
    stance = fields.get("stance", "").strip()
    if not stance:
        return out
    out["stance"] = stance
    out["ok"] = True
    if "confidence" in fields:
        num = re.search(r"\d+", fields["confidence"])
        if num:
            c = int(num.group())
            out["confidence"] = c if 1 <= c <= 5 else None
    if "reason" in fields:
        out["reason"] = fields["reason"].strip() or None
    return out


def _norm(stance):
    return stance.strip().lower()


def canonicalize_stance(stance, options):
    """Map a free-text stance onto one of `options` (e.g. 'Option C — …' -> 'C').

    Without this, a named-option ballot fragments: models tend to write
    'Option C — STRUCTURED…' while figures write 'C', and the exact-string tally
    counts them as different stances. Returns the matching option (as given in
    `options`) or None if no confident match — callers keep the raw stance then,
    so nothing is silently dropped.
    """
    if not stance or not options:
        return None
    t = stance.strip().lower()
    opts = [str(o).strip() for o in options]
    for o in opts:                                            # 1) exact equality
        if t == o.lower():
            return o
    for o in opts:                                            # 2) leading token, opt. "option " prefix
        if re.match(rf"^(option\s+)?{re.escape(o.lower())}\b", t):
            return o
    for o in opts:                                            # 3) standalone token anywhere
        if re.search(rf"\b{re.escape(o.lower())}\b", t):
            return o
    return None


def tally(ballots, options=None):
    """Aggregate parsed ballots -> {counts, abstain, total, leader, confidence_by_stance}.

    Pass `options` (e.g. ["A","B","C"]) for a named-option ballot to canonicalize
    each stance first, so equivalent phrasings count as one stance.
    """
    counts = Counter()
    label = {}                      # normalized -> first-seen surface form
    confs = defaultdict(list)
    abstain = 0
    for b in ballots:
        if not b.get("ok") or not b.get("stance"):
            abstain += 1
            continue
        stance = b["stance"]
        if options:
            canon = canonicalize_stance(stance, options)
            if canon is not None:
                stance = canon
        key = _norm(stance)
        label.setdefault(key, stance.strip())
        counts[key] += 1
        if b.get("confidence") is not None:
            confs[key].append(b["confidence"])
    counts_named = {label[k]: n for k, n in counts.items()}
    conf_named = {label[k]: round(sum(v) / len(v), 2) for k, v in confs.items() if v}
    leader = None
    if counts:
        top = max(counts.values())
        winners = sorted(label[k] for k, n in counts.items() if n == top)
        leader = winners[0] if len(winners) == 1 else winners
    return {
        "counts": counts_named,
        "abstain": abstain,
        "total": len(ballots),
        "leader": leader,
        "confidence_by_stance": conf_named,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses-file", required=True,
                    help="JSON array of objects each with a 'content' string")
    ap.add_argument("--options", default="",
                    help="comma-separated named options (e.g. A,B,C) to canonicalize stances onto")
    args = ap.parse_args()
    data = json.loads(open(args.responses_file).read())
    ballots = [parse_ballot(r.get("content", "")) for r in data]
    options = [o.strip() for o in args.options.split(",") if o.strip()] or None
    print(json.dumps(tally(ballots, options=options), indent=2))


if __name__ == "__main__":
    main()
