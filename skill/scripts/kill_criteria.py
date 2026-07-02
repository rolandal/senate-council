#!/usr/bin/env python3
"""Follow-up ledger for chairman verdict Kill Criteria.

Every chairman verdict emits dated, falsifiable Kill Criteria under a
"## Kill Criteria" heading — and nothing ever revisits them once the report
ships. This builds a standing ledger across every run log so those bullets
get checked instead of forgotten.

Two operations:

  Refresh — scan every `*-transcript.md` in a log dir, pull the bullets under
  each transcript's "## Kill Criteria" section, best-effort extract a due
  date from each bullet (an ISO date, or a "by <Month> <D>, <YYYY>" phrase;
  null when neither is present), and write two files into the log dir:
    kill-criteria.json  — [{run_slug, run_date, criterion, due}, ...]
    kill-criteria.md    — human checklist, grouped by run, newest run first

  Check — refresh the ledger, then report OVERDUE (due < --today) and
  UPCOMING (due within 30 days of --today) criteria. Exits 0 unless
  --fail-on-overdue is given and at least one item is overdue, in which case
  it exits 1.

Transcripts without a Kill Criteria section are skipped; a malformed or
unreadable transcript is logged and skipped rather than failing the run.

Resolution: checking a box (`- [x]`) in kill-criteria.md persists across
refreshes (matched by criterion text), marks the entry `resolved` in
kill-criteria.json, and excludes it from OVERDUE/UPCOMING — so a
--fail-on-overdue failure can be cleared by checking off the criterion.

  python3 kill_criteria.py --log-dir ~/Documents/Local/council-log
  python3 kill_criteria.py --log-dir ~/Documents/Local/council-log \\
      --check --today 2026-07-02 [--fail-on-overdue]
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

FILENAME_RE = re.compile(r"^council-(\d{4}-\d{2}-\d{2})-(.+)-transcript\.md$")
HEADER_DATE_RE = re.compile(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})")
TITLE_RE = re.compile(r"^#\s*Council Transcript\s*—\s*(.+?)\s*$", re.MULTILINE)
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December")
MONTH_DATE_RE = re.compile(
    r"\bby\s+(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2}),?\s+(\d{4})\b", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(.*\S)\s*$")
DONE_LINE_RE = re.compile(r"^\s*-\s*\[x\]\s+(.+?)(?:\s+\(due \d{4}-\d{2}-\d{2}\))?\s*$", re.IGNORECASE)
UPCOMING_WINDOW_DAYS = 30


def _extract_due(line):
    """Best-effort due-date extraction: ISO date anywhere, else 'by <Month> <D>, <YYYY>'."""
    m = ISO_DATE_RE.search(line)
    if m:
        return m.group(1)
    m = MONTH_DATE_RE.search(line)
    if m:
        month = MONTH_NAMES.index(m.group(1).title()) + 1
        day, year = int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def _section_bullets(text):
    """Return the bullet lines under a '## Kill Criteria' heading, or [] if absent."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "## kill criteria":
            start = i + 1
            break
    if start is None:
        return []
    bullets = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        m = BULLET_RE.match(line)
        if m:
            bullets.append(m.group(1))
    return bullets


def parse_transcript(path):
    """Parse one transcript file into (run_slug, run_date, [criterion bullets]).

    Falls back to the in-file title/date header when the filename doesn't
    match the `council-YYYY-MM-DD-<slug>-transcript.md` convention. Returns
    None (rather than raising) on any read/parse failure.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    m = FILENAME_RE.match(path.name)
    if m:
        run_date, run_slug = m.group(1), m.group(2)
    else:
        dm = HEADER_DATE_RE.search(text)
        run_date = dm.group(1) if dm else None
        tm = TITLE_RE.search(text)
        run_slug = tm.group(1) if tm else path.stem

    bullets = _section_bullets(text)
    return run_slug, run_date, bullets


def build_ledger(log_dir):
    """Scan `log_dir` for *-transcript.md files and return the ledger entries."""
    entries = []
    for path in sorted(Path(log_dir).glob("*-transcript.md")):
        parsed = parse_transcript(path)
        if not parsed:
            continue
        run_slug, run_date, bullets = parsed
        for bullet in bullets:
            entries.append({
                "run_slug": run_slug,
                "run_date": run_date,
                "criterion": bullet,
                "due": _extract_due(bullet),
            })
    return entries


def _load_done(md_path):
    """Criterion texts already checked off (`- [x]`) in an existing checklist."""
    try:
        text = Path(md_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    done = set()
    for line in text.splitlines():
        m = DONE_LINE_RE.match(line)
        if m:
            done.add(m.group(1))
    return done


def render_checklist(entries, done=None):
    """Render the human checklist markdown, grouped by run, newest run first.

    Criteria whose text is in `done` render as checked (`- [x]`) so human
    check-offs survive a refresh instead of being wiped.
    """
    done = done or set()
    groups = {}
    order = []
    for e in entries:
        key = (e.get("run_date") or "", e.get("run_slug") or "")
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(e)
    order.sort(key=lambda k: k[0], reverse=True)

    lines = ["# Kill Criteria Ledger\n"]
    if not entries:
        lines.append("_No Kill Criteria found in this log dir._\n")
        return "\n".join(lines)

    for run_date, run_slug in order:
        heading = f"## {run_date or '(no date)'} — {run_slug}\n"
        lines.append(heading)
        for e in groups[(run_date, run_slug)]:
            due = f" (due {e['due']})" if e["due"] else ""
            box = "x" if e["criterion"] in done else " "
            lines.append(f"- [{box}] {e['criterion']}{due}")
        lines.append("")
    return "\n".join(lines)


def refresh(log_dir):
    """Build the ledger, write kill-criteria.json/.md into log_dir, return the entries.

    Boxes checked off in an existing kill-criteria.md are preserved and marked
    `resolved` in the entries (and kill-criteria.json).
    """
    entries = build_ledger(log_dir)
    out_dir = Path(log_dir)
    md_path = out_dir / "kill-criteria.md"
    done = _load_done(md_path)
    for e in entries:
        if e["criterion"] in done:
            e["resolved"] = True
    (out_dir / "kill-criteria.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_checklist(entries, done=done), encoding="utf-8")
    return entries


def classify(entries, today):
    """Split entries with a due date into overdue (< today) and upcoming (within 30 days).

    Entries marked `resolved` (checked off in the ledger) are excluded.
    """
    overdue, upcoming = [], []
    horizon = today + datetime.timedelta(days=UPCOMING_WINDOW_DAYS)
    for e in entries:
        if e.get("resolved"):
            continue
        due = e.get("due")
        if not due:
            continue
        try:
            due_date = datetime.date.fromisoformat(due)
        except ValueError:
            continue
        if due_date < today:
            overdue.append(e)
        elif due_date <= horizon:
            upcoming.append(e)
    return overdue, upcoming


def _print_group(title, items):
    print(f"\n{title} ({len(items)}):")
    for e in items:
        print(f"  - [{e['due']}] {e['run_slug']}: {e['criterion']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", required=True, help="directory holding *-transcript.md run logs")
    ap.add_argument("--check", action="store_true",
                     help="after refreshing, print OVERDUE/UPCOMING criteria")
    ap.add_argument("--today", help="ISO date to check against (default: real today; pin this in tests)")
    ap.add_argument("--fail-on-overdue", action="store_true",
                     help="with --check, exit 1 if any criterion is overdue")
    args = ap.parse_args()

    entries = refresh(args.log_dir)
    print(f"Refreshed ledger: {len(entries)} kill criteria across "
          f"{len({e['run_slug'] for e in entries})} run(s) -> {args.log_dir}")

    if not args.check:
        return

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.date.today())
    overdue, upcoming = classify(entries, today)
    _print_group("OVERDUE", overdue)
    _print_group("UPCOMING", upcoming)

    if args.fail_on_overdue and overdue:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
