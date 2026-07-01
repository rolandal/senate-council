"""Tests for tally_ballots.py — ballot parsing + exact tally (pure, no network)."""
import sys
import pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tally_ballots as tb  # noqa: E402


def test_parse_full_ballot():
    text = "Some analysis here.\nBALLOT: stance=Option A | confidence=4 | reason=clear upside"
    b = tb.parse_ballot(text)
    assert b["ok"] is True
    assert b["stance"] == "Option A"
    assert b["confidence"] == 4
    assert b["reason"] == "clear upside"


def test_parse_is_case_and_space_tolerant():
    b = tb.parse_ballot("ballot:   stance = Yes |confidence=2|reason = meh ")
    assert b["ok"] is True
    assert b["stance"] == "Yes"
    assert b["confidence"] == 2
    assert b["reason"] == "meh"


def test_last_ballot_wins():
    text = "BALLOT: stance=No | confidence=1 | reason=x\nrethink\nBALLOT: stance=Yes | confidence=5 | reason=y"
    assert tb.parse_ballot(text)["stance"] == "Yes"


def test_missing_ballot_is_abstain():
    b = tb.parse_ballot("I have no idea, lots of words but no ballot line.")
    assert b["ok"] is False
    assert b["stance"] is None


def test_out_of_range_confidence_dropped_stance_kept():
    b = tb.parse_ballot("BALLOT: stance=Yes | confidence=9 | reason=z")
    assert b["ok"] is True
    assert b["stance"] == "Yes"
    assert b["confidence"] is None


def test_tally_counts_and_leader():
    ballots = [
        {"stance": "Yes", "confidence": 4, "ok": True},
        {"stance": "yes", "confidence": 2, "ok": True},   # case-insensitive group
        {"stance": "No", "confidence": 5, "ok": True},
        {"stance": None, "confidence": None, "ok": False},  # abstain
    ]
    t = tb.tally(ballots)
    assert t["counts"] == {"Yes": 2, "No": 1}
    assert t["abstain"] == 1
    assert t["total"] == 4
    assert t["leader"] == "Yes"
    assert t["confidence_by_stance"]["Yes"] == 3.0


def test_tally_tie_returns_sorted_list():
    ballots = [
        {"stance": "A", "confidence": None, "ok": True},
        {"stance": "B", "confidence": None, "ok": True},
    ]
    assert tb.tally(ballots)["leader"] == ["A", "B"]


# ── named-option canonicalization (fixes the fragmented-tally bug) ──

def test_canonicalize_named_option_variants():
    opts = ["A", "B", "C"]
    assert tb.canonicalize_stance("Option C — STRUCTURED TRAINING WHEN AGE-APPROPRIATE", opts) == "C"
    assert tb.canonicalize_stance("Option C", opts) == "C"
    assert tb.canonicalize_stance("C", opts) == "C"
    assert tb.canonicalize_stance("c", opts) == "C"
    assert tb.canonicalize_stance("B - gentle foundations", opts) == "B"


def test_canonicalize_word_options_and_misses():
    assert tb.canonicalize_stance("Yes, clearly", ["YES", "NO"]) == "YES"
    assert tb.canonicalize_stance("no way", ["YES", "NO"]) == "NO"
    assert tb.canonicalize_stance("maybe later", ["A", "B", "C"]) is None  # no confident match
    assert tb.canonicalize_stance("", ["A", "B"]) is None


def test_tally_with_options_merges_fragmented_stances():
    """The live bug: models say 'Option C — …', figures say 'C'. Without options they split."""
    ballots = [
        {"stance": "Option C — STRUCTURED TRAINING WHEN AGE-APPROPRIATE", "confidence": 4, "ok": True},
        {"stance": "Option C", "confidence": 5, "ok": True},
        {"stance": "C", "confidence": 4, "ok": True},
        {"stance": "Option B", "confidence": 3, "ok": True},
    ]
    split = tb.tally(ballots)                      # old behavior: 3 separate C-buckets
    assert len(split["counts"]) == 4
    merged = tb.tally(ballots, options=["A", "B", "C"])
    assert merged["counts"] == {"C": 3, "B": 1}
    assert merged["leader"] == "C"


def test_tally_without_options_unchanged():
    ballots = [{"stance": "Yes", "ok": True}, {"stance": "yes", "ok": True}]
    assert tb.tally(ballots)["counts"] == {"Yes": 2}
