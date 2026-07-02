"""Tests for build_index.py — the searchable council-log index.

Two synthetic transcripts modeled closely on tests/fixtures/relocation-senate.expected.transcript.md
(one Senate-style with a `## Metadata` block, one modes-1-4 style without Senate blocks or
metadata, falling back to the `**Mode:**` header line) plus one malformed file, to pin: field
extraction, newest-first sort order, the skip list, and that index.html escapes everything and
links each run to its sibling report HTML.
"""
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_index as bi  # noqa: E402

SENATE_TRANSCRIPT = """# Council Transcript — alpha-senate

**Date:** 2026-06-20 09:00  ·  **Mode:** Senate (Tiered)  ·  **Seats:** 6

## Framed Question

```
CORE DECISION: <& tricky "quoted" markup> should we ship it?
```

## The Vote

A (Ship): 4 | B (Wait): 2. Total: 6 seats. Leader: A (4/6 = 67%).

### Ballots

| Seat | Kind | Vote | Conf | Load-bearing reason |
|---|---|---|---|---|
| Ada Lovelace | figure | A | 4 | Ship now. |

## Chairman Verdict

## The Recommendation

**Ship it (A) — the risk of waiting outweighs the risk of shipping.** More detail
follows in this second sentence that should not be captured.

Second paragraph, also not captured.

## Kill Criteria

1. If churn spikes 20% in week one, reverse course.
2. If support tickets triple, roll back immediately.
3. If the on-call engineer objects, pause the rollout.

## Metadata

```yaml
{
  "schema_version": 1,
  "mode": "senate",
  "tier_strategy": "Tiered",
  "panel": {"figures": 1, "styles": 0, "models": 0, "total": 1},
  "tally": {"counts": {"A": 4, "B": 2}, "abstain": 0, "total": 6, "leader": "A"}
}
```
"""

MODES_TRANSCRIPT = """# Council Transcript — beta-models

**Date:** 2026-06-25 14:30  ·  **Mode:** Models (max)  ·  **Seats:** 3

## Framed Question

```
CORE DECISION: should we adopt the new pricing tier?
```

## The Vote

A (Adopt): 2 | B (Hold): 1. Total: 3 seats. Leader: A (2/3 = 67%).

### Ballots

| Seat | Kind | Vote | Conf | Load-bearing reason |
|---|---|---|---|---|
| GPT 5.5 pro | model | A | 4 | Adopt now. |

## Chairman Verdict

## The Recommendation

**Hold off (B) for one more quarter.** Additional context that trails after the
first sentence is not part of the one-liner.

## Kill Criteria

- If a competitor ships first, revisit immediately.
"""

MALFORMED_TRANSCRIPT = """This file matches the *-transcript.md glob but has no title heading
and no other structure at all — it should be skipped, not crash the run.
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_parses_senate_style_transcript_with_metadata_block(tmp_path):
    p = _write(tmp_path, "council-2026-06-20-alpha-senate-transcript.md", SENATE_TRANSCRIPT)
    entry = bi.parse_transcript(p)
    assert entry["date"] == "2026-06-20"
    assert entry["slug"] == "alpha-senate"
    assert entry["title"] == "Council Transcript — alpha-senate"
    assert entry["mode"] == "senate"
    assert entry["tier"] == "Tiered"
    assert entry["recommendation"] == ('Ship it (A) — the risk of waiting outweighs the risk of '
                                        'shipping.')
    assert entry["has_kill_criteria"] is True
    assert entry["kill_criteria_count"] == 3
    assert entry["report_html"] == "council-2026-06-20-alpha-senate.html"


def test_parses_modes_style_transcript_without_metadata_block(tmp_path):
    p = _write(tmp_path, "council-2026-06-25-beta-models-transcript.md", MODES_TRANSCRIPT)
    entry = bi.parse_transcript(p)
    assert entry["date"] == "2026-06-25"
    assert entry["slug"] == "beta-models"
    assert entry["title"] == "Council Transcript — beta-models"
    # No `## Metadata` block here: mode/tier must fall back to the header line.
    assert entry["mode"] == "models"
    assert entry["tier"] == "max"
    assert entry["recommendation"] == "Hold off (B) for one more quarter."
    assert entry["has_kill_criteria"] is True
    assert entry["kill_criteria_count"] == 1
    assert entry["report_html"] == "council-2026-06-25-beta-models.html"


def test_malformed_file_raises_value_error(tmp_path):
    p = _write(tmp_path, "council-2020-01-01-broken-transcript.md", MALFORMED_TRANSCRIPT)
    import pytest
    with pytest.raises(ValueError):
        bi.parse_transcript(p)


def test_non_matching_filename_raises_value_error(tmp_path):
    p = _write(tmp_path, "notes.md", SENATE_TRANSCRIPT)
    import pytest
    with pytest.raises(ValueError):
        bi.parse_transcript(p)


def test_build_index_sorts_newest_first_and_records_skipped(tmp_path):
    _write(tmp_path, "council-2026-06-20-alpha-senate-transcript.md", SENATE_TRANSCRIPT)
    _write(tmp_path, "council-2026-06-25-beta-models-transcript.md", MODES_TRANSCRIPT)
    _write(tmp_path, "council-2020-01-01-broken-transcript.md", MALFORMED_TRANSCRIPT)

    entries, skipped = bi.build_index(tmp_path)

    assert [e["slug"] for e in entries] == ["beta-models", "alpha-senate"]
    assert len(skipped) == 1
    assert skipped[0]["file"] == "council-2020-01-01-broken-transcript.md"
    assert "reason" in skipped[0] and skipped[0]["reason"]


def test_build_index_empty_dir_is_not_fatal(tmp_path):
    entries, skipped = bi.build_index(tmp_path / "does-not-exist")
    assert entries == [] and skipped == []


def test_main_writes_index_json_and_html(tmp_path):
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    _write(log_dir, "council-2026-06-20-alpha-senate-transcript.md", SENATE_TRANSCRIPT)
    _write(log_dir, "council-2026-06-25-beta-models-transcript.md", MODES_TRANSCRIPT)
    _write(log_dir, "council-2020-01-01-broken-transcript.md", MALFORMED_TRANSCRIPT)
    out_dir = tmp_path / "out"

    old_argv = sys.argv
    sys.argv = ["build_index.py", "--log-dir", str(log_dir), "--out-dir", str(out_dir)]
    try:
        bi.main()
    finally:
        sys.argv = old_argv

    index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
    assert [e["slug"] for e in index["entries"]] == ["beta-models", "alpha-senate"]
    assert len(index["skipped"]) == 1

    page = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "<html" in page and "<style>" in page
    # No external assets: no <link> stylesheets or remote script/img sources.
    assert "http://" not in page and "https://" not in page
    # Titles link to the sibling report HTML.
    assert 'href="council-2026-06-20-alpha-senate.html"' in page
    assert 'href="council-2026-06-25-beta-models.html"' in page
    assert "Council Transcript — alpha-senate" in page
    assert "Council Transcript — beta-models" in page


DANGEROUS_TRANSCRIPT = """# Council Transcript — <script>alert(1)</script> & "quotes"

**Date:** 2026-06-27 10:00  ·  **Mode:** Senate (Tiered)  ·  **Seats:** 2

## Framed Question

```
CORE DECISION: irrelevant
```

## The Vote

A (X): 1 | B (Y): 1. Total: 2 seats. Leader: A (1/2 = 50%).

### Ballots

| Seat | Kind | Vote | Conf | Load-bearing reason |
|---|---|---|---|---|
| X | figure | A | 4 | n/a |

## Chairman Verdict

## The Recommendation

**Do <b>not</b> trust "raw" input & always escape it.** Trailing detail.

## Kill Criteria

1. If escaping ever regresses, fail the build.
"""


def test_index_html_escapes_dangerous_title_and_recommendation(tmp_path):
    """A title/recommendation carrying raw '<script>', '&', and '\"' markup must render as
    inert escaped text in index.html, never as live HTML."""
    p = _write(tmp_path, "council-2026-06-27-danger-transcript.md", DANGEROUS_TRANSCRIPT)
    entry = bi.parse_transcript(p)
    assert entry["title"] == 'Council Transcript — <script>alert(1)</script> & "quotes"'
    page = bi.render_html([entry])
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "&amp;" in page
    assert "&quot;quotes&quot;" in page
    # The recommendation's embedded <b> tag must also come through escaped, not as live markup.
    assert 'Do <b>not</b> trust' not in page
    assert "Do &lt;b&gt;not&lt;/b&gt; trust" in page
