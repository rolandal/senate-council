"""Golden render test — locks build_report() output against a real Senate bundle.

The fixture is a full, repo-safe Senate run (the fictional "relocation dilemma":
Daniel & Priya deciding whether to take a cross-country job). The bundle was
captured once from a live `council me senate` run; this test then re-renders it
through build_report() with PINNED, non-time-varying parameters and asserts the
HTML + transcript byte-for-byte match the committed expected files.

This is a regression guard on the renderer/template, not the council logic: it
catches any unintended change to how a bundle becomes a report. Regenerate the
expected files (after an *intentional* renderer change) with:

    python3 tests/regen_golden.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
TEMPLATE = (ROOT / "skill" / "report-template.html").read_text()
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import render_report as rr  # noqa: E402

# Pinned render parameters — the generator (regen_golden.py) MUST use this exact
# dict, or the snapshot will flake. timestamp is the key pin: build_report()
# defaults it to datetime.now(), which would make every render differ.
PINNED = dict(
    slug="relocation-senate",
    date="2026-06-26",
    raw_title="Daniel & Priya: take the career-defining cross-country move, or stay?",
    mode="Senate",
    tier="Tiered",
    native_model="Sonnet 4.6",
    model_ids=[
        "openai/gpt-5.5-pro",
        "google/gemini-3.1-pro-preview",
        "x-ai/grok-4.3",
        "anthropic/claude-opus-4.8-fast",
        "deepseek/deepseek-v4-pro",
    ],
    timestamp="2026-06-26 12:00",
)


def _bundle():
    return json.loads((FIX / "relocation-senate.bundle.json").read_text())


def _render():
    return rr.build_report(_bundle(), template=TEMPLATE, **PINNED)


def test_golden_html_matches():
    expected = (FIX / "relocation-senate.expected.html").read_text()
    assert _render()["html"] == expected, (
        "Rendered HTML drifted from the golden fixture. If this change was "
        "intentional, regenerate with `python3 tests/regen_golden.py`."
    )


def test_golden_transcript_matches():
    expected = (FIX / "relocation-senate.expected.transcript.md").read_text()
    assert _render()["transcript"] == expected, (
        "Rendered transcript drifted from the golden fixture. If intentional, "
        "regenerate with `python3 tests/regen_golden.py`."
    )


def test_golden_bundle_is_wellformed():
    """Guards the fixture itself: a real 36-seat Senate bundle, all 3 kinds present."""
    b = _bundle()
    assert b["tally"]["total"] == 36
    kinds = {m["kind"] for m in b["members"]}
    assert kinds == {"model", "style", "figure"}
    assert len(b["members"]) == 36
    assert len(b["committees"]) == 6
    assert b["verdict"].lstrip().startswith("## The Vote")
