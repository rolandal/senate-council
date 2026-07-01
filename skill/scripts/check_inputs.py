#!/usr/bin/env python3
"""Pre-dispatch integrity gate — confirm every member actually RECEIVED the question.

The Council's most dangerous failure is silent. If the framed question never
reaches a member — a side channel that arrived empty, an unfilled template
variable, a mis-wired orchestrator — the model does NOT error. It confabulates a
plausible answer from whatever breadcrumbs are in the prompt, casts a real-looking
ballot, and the whole run looks fine. (This happened: 31 seats once deliberated on
`THE FRAMED QUESTION:\\nundefined`; 29 produced on-topic-looking analyses by
inferring the scenario from names dropped elsewhere in the prompt. Only 2 said
"undefined" out loud.)

Post-hoc content checks CANNOT catch this — confabulation is built to look real.
The only robust guard is to verify the INPUT that was actually delivered. So this
script checks the dispatched PROMPTS, not the responses: every member prompt must
contain the framed question (matched on a whitespace-normalized fingerprint). Any
prompt that doesn't — or that still carries an unfilled placeholder — fails the
gate loudly, before the reduce/synthesis stage trusts a single ballot.

Run it right after building member prompts and before (or alongside) the quorum
gate. The orchestrator already holds every prompt it dispatches; dump them as
[{label, prompt}] and point this at them.

  python3 check_inputs.py --prompts-file prompts.json --framed-file framed.txt
  python3 check_inputs.py --prompts-file prompts.json --fingerprint "CORE DECISION: ..."

Exits non-zero (and lists offenders) if any prompt failed. Stdlib only.
"""
import argparse
import json
import re
import sys

# Unfilled-template / empty-channel tells: if a prompt still contains one of these
# where the question should be, the input never arrived.
PLACEHOLDER_MARKERS = ("undefined", "{{framed", "{framed_question}", "{{question",
                       "none\n", "null\n", "[object object]")


def _norm(s):
    """Lowercase + collapse all whitespace, so formatting differences don't matter."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def fingerprint(framed, n=80):
    """A distinctive normalized slice of the framed question to look for in prompts."""
    return _norm(framed)[:n]


def check_prompt(prompt, fp):
    """Return (ok, reason). A prompt is ok iff it carries the framed-question fingerprint."""
    np = _norm(prompt)
    if not np:
        return False, "empty prompt"
    if fp and fp in np:
        return True, "ok"
    for marker in PLACEHOLDER_MARKERS:
        if marker in np:
            return False, f"framed question missing; found unfilled placeholder ({marker.strip()!r})"
    return False, "framed question fingerprint not found in prompt"


def check_inputs(prompts, framed=None, fp=None):
    fp = fp if fp is not None else fingerprint(framed or "")
    if not fp:
        raise ValueError("need a non-empty framed question or fingerprint to check against")
    failures = []
    for i, p in enumerate(prompts):
        label = p.get("label", f"seat-{i}") if isinstance(p, dict) else f"seat-{i}"
        text = p.get("prompt", "") if isinstance(p, dict) else str(p)
        ok, reason = check_prompt(text, fp)
        if not ok:
            failures.append({"label": label, "reason": reason})
    return {
        "ok": not failures,
        "checked": len(prompts),
        "passed": len(prompts) - len(failures),
        "fingerprint": fp,
        "failures": failures,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts-file", required=True,
                    help="JSON array of dispatched prompts, each {label, prompt} (or a bare string)")
    ap.add_argument("--framed-file", help="file holding the framed question (fingerprint is derived from it)")
    ap.add_argument("--fingerprint", help="explicit fingerprint to require in every prompt (overrides --framed-file)")
    args = ap.parse_args()
    prompts = json.loads(open(args.prompts_file).read())
    framed = open(args.framed_file).read() if args.framed_file else None
    result = check_inputs(prompts, framed=framed, fp=args.fingerprint)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        print(f"\nINPUT GATE FAILED: {len(result['failures'])} of {result['checked']} seats did NOT receive "
              f"the framed question. Do NOT trust this run — fix dispatch and re-convene.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
