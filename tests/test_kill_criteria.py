"""Tests for kill_criteria.py — follow-up ledger for chairman verdict Kill Criteria.

Every verdict emits dated, falsifiable Kill Criteria under a "## Kill Criteria"
heading and nothing ever revisits them. These tests pin: the parser (against the
real bullet format from the golden fixture), the ledger + checklist outputs, and
the overdue/upcoming classification with a pinned --today.
"""
import json
import subprocess
import sys
import pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import kill_criteria as kc  # noqa: E402

ISO_TRANSCRIPT = """# Council Transcript — sleep-training-senate

**Date:** 2026-06-01 09:00  ·  **Mode:** Senate (Tiered)  ·  **Seats:** 12

## The Vote

A: 5 | B: 7

## Kill Criteria

These would prove this recommendation wrong:

1. **By 2026-07-15:** if the pediatrician flags a medical cause, the verdict flips.
2. **Within a week:** if the child's daytime mood degrades, escalate immediately (no date).

## What the Council Doesn't Know

- Some unknown.
"""

MONTH_NAME_TRANSCRIPT = """# Council Transcript — relocation-senate

**Date:** 2026-06-26 12:00  ·  **Mode:** Senate (Tiered)  ·  **Seats:** 36

## Kill Criteria

These would prove this recommendation (negotiate-first, default-Stay) **wrong**:

1. **By the end of the Question-One conversation:** if Priya expresses a clear desire to relocate, the case flips toward A.
2. **By July 20, 2026:** if the employer grants a written delayed start, then C succeeds outright.

## What the Council Doesn't Know

- Priya's actual preference.
"""

NO_SECTION_TRANSCRIPT = """# Council Transcript — no-kill-section

**Date:** 2026-05-01 08:00  ·  **Mode:** Models  ·  **Seats:** 5

## The Vote

A: 3 | B: 2

## What the Council Doesn't Know

- Nothing notable.
"""


def write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# parser / pure functions
# ---------------------------------------------------------------------------

def test_parse_transcript_iso_dates(tmp_path):
    p = write(tmp_path, "council-2026-06-01-sleep-training-senate-transcript.md", ISO_TRANSCRIPT)
    run_slug, run_date, bullets = kc.parse_transcript(p)
    assert run_slug == "sleep-training-senate"
    assert run_date == "2026-06-01"
    assert len(bullets) == 2
    assert "pediatrician" in bullets[0]


def test_extract_due_iso_anywhere_in_line():
    assert kc._extract_due("**By 2026-07-15:** if X happens") == "2026-07-15"


def test_extract_due_month_name_style():
    assert kc._extract_due("**By July 20, 2026:** if Y happens") == "2026-07-20"


def test_extract_due_none_when_undated():
    assert kc._extract_due("**Within a week:** escalate immediately") is None


def test_no_kill_criteria_section_yields_no_bullets(tmp_path):
    p = write(tmp_path, "council-2026-05-01-no-kill-section-transcript.md", NO_SECTION_TRANSCRIPT)
    run_slug, run_date, bullets = kc.parse_transcript(p)
    assert bullets == []
    assert run_slug == "no-kill-section"
    assert run_date == "2026-05-01"


def test_malformed_file_never_fatal(tmp_path):
    """A transcript that is missing OR malformed (non-UTF-8) must be skipped, not raise."""
    missing = tmp_path / "council-2026-01-01-ghost-transcript.md"
    assert kc.parse_transcript(missing) is None

    bad = tmp_path / "council-2026-01-01-badbytes-transcript.md"
    bad.write_bytes(b"\xff\xfe garbage \x80\x81")
    assert kc.parse_transcript(bad) is None
    assert kc.build_ledger(tmp_path) == []  # skipped; the ledger run survives


# ---------------------------------------------------------------------------
# build_ledger / refresh (writes into log dir)
# ---------------------------------------------------------------------------

def _seed_log_dir(tmp_path):
    write(tmp_path, "council-2026-06-01-sleep-training-senate-transcript.md", ISO_TRANSCRIPT)
    write(tmp_path, "council-2026-06-26-relocation-senate-transcript.md", MONTH_NAME_TRANSCRIPT)
    write(tmp_path, "council-2026-05-01-no-kill-section-transcript.md", NO_SECTION_TRANSCRIPT)
    return tmp_path


def test_build_ledger_skips_section_less_run_and_extracts_dates(tmp_path):
    _seed_log_dir(tmp_path)
    entries = kc.build_ledger(tmp_path)
    slugs = {e["run_slug"] for e in entries}
    assert slugs == {"sleep-training-senate", "relocation-senate"}
    assert len(entries) == 4  # 2 bullets per dated run

    due_by_criterion = {e["criterion"]: e["due"] for e in entries}
    iso_line = next(c for c in due_by_criterion if "pediatrician" in c)
    assert due_by_criterion[iso_line] == "2026-07-15"
    undated_line = next(c for c in due_by_criterion if "daytime mood" in c)
    assert due_by_criterion[undated_line] is None
    month_line = next(c for c in due_by_criterion if "written delayed start" in c)
    assert due_by_criterion[month_line] == "2026-07-20"


def test_refresh_writes_json_and_md(tmp_path):
    _seed_log_dir(tmp_path)
    entries = kc.refresh(tmp_path)

    json_path = tmp_path / "kill-criteria.json"
    md_path = tmp_path / "kill-criteria.md"
    assert json_path.exists() and md_path.exists()

    on_disk = json.loads(json_path.read_text(encoding="utf-8"))
    assert on_disk == entries

    md = md_path.read_text(encoding="utf-8")
    # Newest run (2026-06-26) appears before the older one (2026-06-01).
    assert md.index("relocation-senate") < md.index("sleep-training-senate")
    assert "- [ ]" in md
    assert "(due 2026-07-15)" in md


def test_refresh_preserves_checked_boxes_and_resolves_entries(tmp_path):
    """A `- [x]` check-off must survive refresh, mark the entry resolved, and drop it from classify."""
    import datetime
    _seed_log_dir(tmp_path)
    kc.refresh(tmp_path)

    md_path = tmp_path / "kill-criteria.md"
    md = md_path.read_text(encoding="utf-8")
    target = next(l for l in md.splitlines() if "pediatrician" in l)
    md_path.write_text(md.replace(target, target.replace("- [ ]", "- [x]", 1)), encoding="utf-8")

    entries = kc.refresh(tmp_path)
    md2 = md_path.read_text(encoding="utf-8")
    assert any(l.startswith("- [x]") and "pediatrician" in l for l in md2.splitlines())
    resolved = [e for e in entries if e.get("resolved")]
    assert len(resolved) == 1 and "pediatrician" in resolved[0]["criterion"]

    # Resolved items no longer count as overdue (so --fail-on-overdue can be cleared).
    overdue, _ = kc.classify(entries, datetime.date(2026, 8, 1))
    assert all("pediatrician" not in e["criterion"] for e in overdue)


def test_refresh_on_empty_dir_produces_empty_ledger(tmp_path):
    entries = kc.refresh(tmp_path)
    assert entries == []
    md = (tmp_path / "kill-criteria.md").read_text(encoding="utf-8")
    assert "No Kill Criteria" in md


# ---------------------------------------------------------------------------
# classify (overdue / upcoming)
# ---------------------------------------------------------------------------

def test_classify_overdue_and_upcoming():
    import datetime
    entries = [
        {"run_slug": "a", "run_date": "2026-01-01", "criterion": "past", "due": "2026-06-01"},
        {"run_slug": "b", "run_date": "2026-01-01", "criterion": "soon", "due": "2026-07-10"},
        {"run_slug": "c", "run_date": "2026-01-01", "criterion": "far", "due": "2026-12-01"},
        {"run_slug": "d", "run_date": "2026-01-01", "criterion": "undated", "due": None},
    ]
    today = datetime.date(2026, 7, 2)
    overdue, upcoming = kc.classify(entries, today)
    assert [e["criterion"] for e in overdue] == ["past"]
    assert [e["criterion"] for e in upcoming] == ["soon"]


# ---------------------------------------------------------------------------
# CLI end-to-end (subprocess) — refresh, --check, --fail-on-overdue exit codes
# ---------------------------------------------------------------------------

def run_cli(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "kill_criteria.py")] + args,
        capture_output=True, text=True,
    )


def test_cli_refresh_creates_ledger_files(tmp_path):
    _seed_log_dir(tmp_path)
    result = run_cli(["--log-dir", str(tmp_path)])
    assert result.returncode == 0
    assert (tmp_path / "kill-criteria.json").exists()
    assert (tmp_path / "kill-criteria.md").exists()


def test_cli_check_pinned_today_classifies_upcoming_not_overdue(tmp_path):
    _seed_log_dir(tmp_path)
    result = run_cli(["--log-dir", str(tmp_path), "--check", "--today", "2026-07-02"])
    assert result.returncode == 0
    # Relative to 2026-07-02 both dated criteria (07-15, 07-20) are upcoming, none overdue.
    assert "OVERDUE (0)" in result.stdout
    assert "UPCOMING (2)" in result.stdout
    assert "2026-07-15" in result.stdout


def test_cli_fail_on_overdue_exits_nonzero_when_overdue_present(tmp_path):
    _seed_log_dir(tmp_path)
    # Relative to 2026-08-01, the 2026-07-15 and 2026-07-20 due dates are overdue.
    result = run_cli(["--log-dir", str(tmp_path), "--check", "--today", "2026-08-01",
                       "--fail-on-overdue"])
    assert result.returncode == 1
    assert "OVERDUE" in result.stdout


def test_cli_fail_on_overdue_exits_zero_when_nothing_overdue(tmp_path):
    _seed_log_dir(tmp_path)
    result = run_cli(["--log-dir", str(tmp_path), "--check", "--today", "2026-01-01",
                       "--fail-on-overdue"])
    assert result.returncode == 0
