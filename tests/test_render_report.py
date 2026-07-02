"""Tests for render_report.py — fills report-template.html from a council bundle.

Pure-ish: build_report(bundle, ...) returns {html, transcript} strings so we can
assert structure without touching the filesystem.
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
TEMPLATE = (ROOT / "skill" / "report-template.html").read_text()
sys.path.insert(0, str(SCRIPTS))

import render_report as rr  # noqa: E402


def bundle():
    return {
        "framed": "CORE DECISION: test.\nBALLOT SPEC — A/B/C.",
        "tally": {"counts": {"A": 0, "B": 2, "C": 1, "ABSTAIN": 0}, "abstain": 0,
                  "total": 3, "confidence_by_stance": {"A": None, "B": 4.0, "C": 4.0}, "leader": "B"},
        "tallyStr": "A: 0 | B: 2 | C: 1 | ABSTAIN: 0. Leader: B.",
        "members": [
            {"label": "GPT 5.5 pro", "kind": "model", "stance": "C", "confidence": 4,
             "reason": "overload", "analysis": "**Hard truth.** Some *analysis*.\n\n- a\n- b"},
            {"label": "Lao Tzu", "kind": "figure", "stance": "B", "confidence": 3,
             "reason": "force nothing", "analysis": "Wu wei applies here."},
            {"label": "The Contrarian", "kind": "style", "stance": "B", "confidence": 4,
             "reason": "status quo failed", "analysis": "You avoid the real question."},
        ],
        "committees": [["GPT 5.5 pro", "Lao Tzu"], ["The Contrarian"]],
        "briefs": [
            {"committee": 0, "labels": ["GPT 5.5 pro", "Lao Tzu"], "miniTally": "1xC, 1xB",
             "text": "1. **Strongest case:** mixed.\n2. Split.\n3. Mini-tally: 1C 1B."},
            {"committee": 1, "labels": ["The Contrarian"], "miniTally": "1xB", "text": "Brief two."},
        ],
        "reviews": ["1. Strongest is Response A.\n2. Blind spot: marriage.\n3. All missed: the partner."],
        "verdict": ("## The Vote\nLeans B.\n\n## The Faction Map\n**Empiricists** back data.\n\n"
                    "## Where the Council Agrees\nDon't train a newborn.\n\n## Where the Council Clashes\n"
                    "A vs C.\n\n## Blind Spots the Council Caught\nThe partner.\n\n## The Recommendation\n"
                    "Do **B**.\n\n## The One Thing to Do First\nFix the routine tonight.\n\n## Kill Criteria\n"
                    "- If no change by month 4, escalate.\n\n## What the Council Doesn't Know\nIs there a co-parent?"),
        "factions": "**Empiricists**: trust trials.",
        "anonMap": {"A": 1, "B": 0},
        "convergence": 0.67,
    }


def render():
    return rr.build_report(bundle(), template=TEMPLATE, slug="test-senate",
                           date="2026-06-26", raw_title="Did we decide right?",
                           mode="Senate", tier="Tiered",
                           model_ids=["openai/gpt-5.5-pro"])


def test_no_unfilled_placeholders():
    out = render()
    assert "{{" not in out["html"] and "}}" not in out["html"]


def test_recommendation_and_hero_present():
    html = render()["html"]
    assert "Do <strong>B</strong>" in html         # markdown bold rendered
    assert "Fix the routine tonight" in html        # the one-thing hero


def test_every_member_and_review_rendered():
    html = render()["html"]
    for m in bundle()["members"]:
        assert m["label"] in html
    assert "Reviewer 1" in html


def test_committee_briefs_rendered():
    html = render()["html"]
    assert "Committee 1" in html and "Committee 2" in html


def test_vote_bar_present_for_senate():
    html = render()["html"]
    assert "The Vote" in html and "title=" in html   # at least one vote-bar segment


def test_transcript_has_verdict_and_ballots():
    out = render()
    assert "Chairman Verdict" in out["transcript"]
    assert "GPT 5.5 pro" in out["transcript"]
    assert "Load-bearing reason" in out["transcript"] or "reason" in out["transcript"].lower()


def test_anon_map_accepts_anonymize_string_values():
    """bundle.anonMap may be anonymize.py's map verbatim ({"Response A": "Committee 3"});
    string values must render as-is instead of crashing on `v + 1`."""
    b = bundle()
    b["anonMap"] = {"Response A": "Committee 2", "Response B": "Committee 1"}
    out = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                          raw_title="Q?", mode="Senate", tier="Tiered")
    assert "Response A=Committee 2" in out["html"]
    assert "Response B=Committee 1" in out["html"]


def test_injected_placeholder_survives():
    """A {{snake_case}} token inside advisor/verdict text must NOT be eaten by the cleanup pass."""
    b = bundle()
    b["verdict"] = b["verdict"].replace("Do **B**.", "Do **B** with the {{my_var}} token.")
    html = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                           raw_title="Q?", mode="Senate", tier="Tiered")["html"]
    assert "{{my_var}}" in html


def test_leader_and_total_escaped():
    b = bundle()
    b["tally"]["leader"] = "<script>x</script>"
    html = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                           raw_title="Q?", mode="Senate", tier="Tiered")["html"]
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_sec_no_substring_collision_on_disagrees():
    """The 'agrees' panel must not pick up a 'Where the Council Disagrees' section."""
    b = bundle()
    b["verdict"] = ("## Where the Council Disagrees\nDecoy disagreement.\n\n"
                    "## The Recommendation\nDo B.\n\n## The One Thing to Do First\nGo.")
    html = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                           raw_title="Q?", mode="Senate", tier="Tiered")["html"]
    assert "Decoy disagreement." not in html


def test_run_stats_full_line_renders():
    b = bundle()
    b["runStats"] = {"seats": 36, "durationSec": 252, "tokens": 41203, "modelSpend": "$1.23"}
    html = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                           raw_title="Q?", mode="Senate", tier="Tiered")["html"]
    assert "run-stats" in html
    assert "36 seats" in html
    assert "4m 12s" in html
    assert "41,203 tokens" in html
    assert "~$1.23 model spend" in html


def test_run_stats_partial_line_renders_only_given_parts():
    b = bundle()
    b["runStats"] = {"seats": 36, "duration": "4m 12s"}
    html = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                           raw_title="Q?", mode="Senate", tier="Tiered")["html"]
    assert "run-stats" in html
    assert "36 seats" in html
    assert "4m 12s" in html
    assert "tokens" not in html
    assert "model spend" not in html


def test_no_run_stats_key_renders_no_stats_artifacts():
    b = bundle()
    assert "runStats" not in b
    html = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                           raw_title="Q?", mode="Senate", tier="Tiered")["html"]
    assert "run-stats" not in html


def test_degrades_without_senate_blocks():
    """A modes-1-4 bundle (no committees/briefs, 7-section verdict) still renders."""
    b = bundle()
    b["committees"] = []
    b["briefs"] = []
    b["verdict"] = "## The Recommendation\nDo B.\n\n## The One Thing to Do First\nStart now."
    out = rr.build_report(b, template=TEMPLATE, slug="x", date="2026-06-26",
                          raw_title="Q?", mode="Styles", tier="n/a")
    assert "{{" not in out["html"]
    assert "Do B" in out["html"]
