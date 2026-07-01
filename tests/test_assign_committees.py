"""Tests for assign_committees.py — balanced, diverse committee sort (pure)."""
import sys
import pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import assign_committees as ac  # noqa: E402


def make_roster():
    seats = []
    seats += [{"label": f"model{i}", "kind": "model"} for i in range(5)]
    seats += [{"label": f"style{i}", "kind": "style"} for i in range(8)]
    seats += [{"label": f"fig{i}", "kind": "figure"} for i in range(23)]
    return seats  # 36 total


def test_committee_count_is_ceil():
    committees = ac.assign_committees(make_roster(), size=6)
    assert len(committees) == 6  # ceil(36/6)


def test_every_seat_placed_once():
    roster = make_roster()
    committees = ac.assign_committees(roster, size=6)
    placed = [s["label"] for c in committees for s in c]
    assert sorted(placed) == sorted(s["label"] for s in roster)
    assert len(placed) == len(set(placed)) == 36


def test_sizes_balanced():
    committees = ac.assign_committees(make_roster(), size=6)
    sizes = [len(c) for c in committees]
    assert max(sizes) - min(sizes) <= 1


def test_models_in_distinct_committees():
    committees = ac.assign_committees(make_roster(), size=6)
    model_committees = [i for i, c in enumerate(committees)
                        for s in c if s["kind"] == "model"]
    assert len(model_committees) == len(set(model_committees)) == 5


def test_styles_spread_no_clumping():
    committees = ac.assign_committees(make_roster(), size=6)
    per = [sum(1 for s in c if s["kind"] == "style") for c in committees]
    assert max(per) <= 2  # 8 styles over 6 committees -> at most 2 each


def test_deterministic():
    roster = make_roster()
    a = [[s["label"] for s in c] for c in ac.assign_committees(roster, 6)]
    b = [[s["label"] for s in c] for c in ac.assign_committees(roster, 6)]
    assert a == b


def test_uneven_native_only_panel():
    seats = ([{"label": f"s{i}", "kind": "style"} for i in range(8)]
             + [{"label": f"f{i}", "kind": "figure"} for i in range(23)])  # 31
    committees = ac.assign_committees(seats, size=6)
    assert len(committees) == 6  # ceil(31/6)
    sizes = sorted(len(c) for c in committees)
    assert sizes == [5, 5, 5, 5, 5, 6]


def test_empty_roster():
    assert ac.assign_committees([], size=6) == []
