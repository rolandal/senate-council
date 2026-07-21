"""Regression tests: render_report accepts the pipeline shape {label, kind, content}.

Guards the bug where a bundle built from the pipeline's native seat shape (the
same objects tally_ballots/anonymize/check_quorum consume) rendered every
advisor card as "Ballot only. Load-bearing reason: —", and tally_ballots
counted a markdown-wrapped ballot line (**BALLOT: ...**) as ABSTAIN.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from render_report import (_canon_stance, _normalize_brief,  # noqa: E402
                           _normalize_member, _normalize_review)
from tally_ballots import parse_ballot  # noqa: E402

CONTENT = """### Analysis
The draft names your number first. Delete that clause.

BALLOT: stance=Option B | confidence=4 | reason=self-anchoring gives away the range"""


def test_member_content_is_parsed_into_analysis_and_ballot():
    m = _normalize_member({"label": "Feynman", "kind": "figure", "content": CONTENT})
    assert m["analysis"].startswith("### Analysis")
    assert "BALLOT" not in m["analysis"]
    assert m["stance"] == "B"
    assert m["confidence"] == 4
    assert m["reason"] == "self-anchoring gives away the range"


def test_markdown_wrapped_ballot_parses():
    m = _normalize_member({"label": "DeepSeek", "kind": "model",
                           "content": "Argument.\n**BALLOT: stance=C | confidence=5 | reason=don't name first**"})
    assert m["stance"] == "C"
    assert m["reason"] == "don't name first"


def test_preparsed_member_passes_through():
    pre = {"label": "X", "kind": "style", "analysis": "done", "stance": "A"}
    assert _normalize_member(pre) == pre


def test_canon_stance():
    assert _canon_stance("Option B") == "B"
    assert _canon_stance("c") == "C"
    assert _canon_stance("ABSTAIN (no view)") == "ABSTAIN"
    assert _canon_stance("bundle both projects") == "bundle both projects"


def test_brief_label_shape_derives_index_labels_minitally():
    members = [
        _normalize_member({"label": "Feynman", "kind": "figure", "content": CONTENT}),
        _normalize_member({"label": "DeepSeek", "kind": "model",
                           "content": "Arg.\n**BALLOT: stance=C | confidence=5 | reason=r**"}),
    ]
    b = _normalize_brief({"label": "Committee 1", "text": "brief text"},
                         [["Feynman", "DeepSeek"]], members)
    assert b["committee"] == 0
    assert b["labels"] == ["Feynman", "DeepSeek"]
    assert "1 B" in b["miniTally"] and "1 C" in b["miniTally"]


def test_review_dict_shape_accepted():
    assert _normalize_review({"label": "Reviewer 1", "content": "body"}) == "Reviewer 1\nbody"
    assert _normalize_review("plain string") == "plain string"


def test_tally_parse_ballot_tolerates_markdown_wrappers():
    b = parse_ballot("Argument.\n**BALLOT: stance=C | confidence=5 | reason=Don't name the first number**")
    assert b["ok"] and b["stance"] == "C" and b["confidence"] == 5
    plain = parse_ballot("BALLOT: stance=Option B | confidence=4 | reason=fix the clause")
    assert plain["ok"] and plain["stance"] == "Option B"
