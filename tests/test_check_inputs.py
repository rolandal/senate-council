"""Tests for check_inputs.py — the pre-dispatch input-integrity gate.

The gate's whole job is to catch the silent failure where a member never received
the framed question and confabulated. These tests pin that: a clean run passes, and
the exact historical failure (`THE FRAMED QUESTION:\\nundefined`) is rejected.
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_inputs as ci  # noqa: E402

FRAMED = ("CORE DECISION: Should Daniel & Priya take a career-defining cross-country "
          "job offer that uproots their child's school and Priya's local business, or stay?\n"
          "BALLOT SPEC — A RELOCATE / B STAY / C NEGOTIATE.")


def _prompt_with_question(persona):
    return f"{persona}\n\nTHE FRAMED QUESTION:\n{FRAMED}\n\nCast a ballot A/B/C."


def test_clean_run_passes():
    prompts = [{"label": f"seat-{i}", "prompt": _prompt_with_question(f"You are advisor {i}.")}
               for i in range(5)]
    result = ci.check_inputs(prompts, framed=FRAMED)
    assert result["ok"] is True
    assert result["passed"] == 5 and not result["failures"]


def test_rejects_the_undefined_regression():
    """The exact bug: the framed question arrived as the literal string 'undefined'."""
    prompts = [
        {"label": "Ada Lovelace", "prompt": "You are Ada.\n\nTHE FRAMED QUESTION:\nundefined\n\nCast a ballot."},
        {"label": "The Outsider", "prompt": "You are the Outsider.\n\nTHE FRAMED QUESTION:\nundefined\n\nBallot."},
    ]
    result = ci.check_inputs(prompts, framed=FRAMED)
    assert result["ok"] is False
    assert {f["label"] for f in result["failures"]} == {"Ada Lovelace", "The Outsider"}
    assert all("placeholder" in f["reason"] or "not found" in f["reason"] for f in result["failures"])


def test_flags_only_the_broken_seat_in_a_mixed_run():
    prompts = [
        {"label": "good-1", "prompt": _prompt_with_question("You are advisor 1.")},
        {"label": "broken", "prompt": "You are advisor 2.\n\nTHE FRAMED QUESTION:\nundefined"},
        {"label": "good-2", "prompt": _prompt_with_question("You are advisor 3.")},
    ]
    result = ci.check_inputs(prompts, framed=FRAMED)
    assert result["ok"] is False
    assert [f["label"] for f in result["failures"]] == ["broken"]
    assert result["passed"] == 2


def test_empty_prompt_fails():
    result = ci.check_inputs([{"label": "x", "prompt": ""}], framed=FRAMED)
    assert result["ok"] is False
    assert result["failures"][0]["reason"] == "empty prompt"


def test_whitespace_reformatting_still_matches():
    """A prompt that re-wraps/indents the question must still pass (fingerprint is normalized)."""
    reflowed = "  CORE   DECISION:   Should Daniel & Priya take a career-defining\ncross-country job offer..."
    result = ci.check_inputs([{"label": "x", "prompt": reflowed}], framed=FRAMED)
    assert result["ok"] is True


def test_requires_a_fingerprint():
    import pytest
    with pytest.raises(ValueError):
        ci.check_inputs([{"label": "x", "prompt": "anything"}], framed="")
