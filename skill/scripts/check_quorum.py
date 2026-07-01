#!/usr/bin/env python3
"""Verify the collected Senate responses match the dispatched roster.

Guards the reduce stage against silently synthesizing a verdict on the wrong
house. Catches two failure modes a raw quorum ratio misses:

  - WHOLE-KIND DROPS — e.g. all model seats lost. That is only 5/36 = 14% of the
    house, so a naive ">=75% returned" still passes, yet the entire cross-model
    diversity (the whole point of the Senate) is gone. (This actually happened:
    model seats passed via a workflow `args` object arrived empty and the reduce
    ran on 31 of 36 seats.)
  - NAMED-SEAT DROPS — any specific seat that was dispatched but never returned.

Pure core (`check_quorum`) for unit tests; a CLI that prints a JSON report and
EXITS NON-ZERO when the bar isn't met, so a bash/workflow gate hard-fails instead
of proceeding to synthesize.

  python3 check_quorum.py --roster-file seats.json --responses-file responses.json
                          [--quorum 0.75] [--strict]

Both files are JSON arrays of seats; each seat needs at least {label, kind}.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

EXIT_QUORUM_FAIL = 2


def _by_kind(seats):
    return dict(Counter(s.get("kind", "?") for s in seats))


def check_quorum(expected, returned, quorum=0.75, strict=False):
    """Compare dispatched roster vs collected responses.

    expected / returned: lists of seats, each a dict with {label, kind}.
    Returns a report dict; `ok` is the gate. Default rule: pass only if the
    returned share meets `quorum` AND no expected kind is entirely missing.
    `strict=True` instead demands every dispatched seat returned.
    """
    exp_labels = [s.get("label") for s in expected if s.get("label")]
    exp_label_set = set(exp_labels)
    exp_counts = Counter(exp_labels)
    ret_counts = Counter(s.get("label") for s in returned if s.get("label"))

    # Count by multiset intersection so a single physical response can't satisfy
    # multiple expected seats sharing a label (a dispatch dup must NOT pass the gate).
    returned_total = sum(min(n, ret_counts.get(lbl, 0)) for lbl, n in exp_counts.items())
    missing = []
    for lbl, n in exp_counts.items():
        missing += [lbl] * max(0, n - ret_counts.get(lbl, 0))  # per-occurrence shortfall
    extra = sorted(set(ret_counts) - exp_label_set)

    exp_total = len(exp_labels)
    ratio = (returned_total / exp_total) if exp_total else 1.0

    exp_kinds = _by_kind(expected)
    ret_kinds = _by_kind([s for s in returned if s.get("label") in exp_label_set])
    dropped_kinds = sorted(k for k, n in exp_kinds.items() if n > 0 and ret_kinds.get(k, 0) == 0)

    if strict:
        ok = not missing
    else:
        ok = (ratio >= quorum) and (not dropped_kinds)

    return {
        "ok": ok,
        "expected": exp_total,
        "returned": returned_total,
        "quorum_ratio": round(ratio, 4),
        "quorum_required": quorum,
        "strict": strict,
        "missing": missing,
        "extra": extra,
        "dropped_kinds": dropped_kinds,
        "expected_by_kind": exp_kinds,
        "returned_by_kind": ret_kinds,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster-file", required=True,
                    help="JSON array of dispatched seats, each {label, kind}")
    ap.add_argument("--responses-file", required=True,
                    help="JSON array of returned responses, each {label, kind}")
    ap.add_argument("--quorum", type=float, default=0.75)
    ap.add_argument("--strict", action="store_true",
                    help="require every dispatched seat to return (no missing)")
    args = ap.parse_args()

    try:
        expected = json.loads(Path(args.roster_file).read_text())
        returned = json.loads(Path(args.responses_file).read_text())
    except (OSError, ValueError) as e:
        sys.stderr.write(f"QUORUM GATE could not read inputs: {e}\nDo NOT reduce.\n")
        raise SystemExit(EXIT_QUORUM_FAIL)
    report = check_quorum(expected, returned, quorum=args.quorum, strict=args.strict)
    print(json.dumps(report, indent=2))

    if not report["ok"]:
        kinds = ", ".join(report["dropped_kinds"]) or "—"
        sys.stderr.write(
            f"\nQUORUM FAIL: {report['returned']}/{report['expected']} seats returned "
            f"(ratio {report['quorum_ratio']}, need {report['quorum_required']}); "
            f"dropped kinds: {kinds}; missing {len(report['missing'])} seat(s). "
            f"Do NOT reduce — fix dispatch and re-collect before the clerk/whips run.\n")
        raise SystemExit(EXIT_QUORUM_FAIL)


if __name__ == "__main__":
    main()
