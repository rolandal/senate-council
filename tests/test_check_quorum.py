"""Tests for check_quorum.py — roster-integrity gate before the Senate reduce (pure).

The motivating bug: all 5 model seats were silently dropped, so the reduce ran on
31 of 36 seats. A naive >=75% quorum does NOT catch this (31/36 = 86%), but losing
an entire *kind* is a categorical failure. These tests pin both guards.
"""
import sys
import pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_quorum as cq  # noqa: E402


def roster():
    seats = [{"label": f"model{i}", "kind": "model"} for i in range(5)]
    seats += [{"label": f"style{i}", "kind": "style"} for i in range(8)]
    seats += [{"label": f"fig{i}", "kind": "figure"} for i in range(23)]
    return seats  # 36


def test_full_house_passes():
    r = cq.check_quorum(roster(), roster())
    assert r["ok"] is True
    assert r["expected"] == 36 and r["returned"] == 36
    assert r["missing"] == [] and r["dropped_kinds"] == []


def test_whole_kind_drop_fails_even_above_quorum():
    """The actual bug: all model seats gone. 31/36 = 86% >= 75%, but a kind is empty."""
    returned = [s for s in roster() if s["kind"] != "model"]  # 31 seats
    r = cq.check_quorum(roster(), returned)
    assert r["quorum_ratio"] >= 0.75          # would pass a naive quorum
    assert r["ok"] is False                   # but the guard fails it
    assert r["dropped_kinds"] == ["model"]
    assert len(r["missing"]) == 5


def test_partial_native_loss_within_quorum_passes():
    """Losing a few figures (no whole kind gone, still >=75%) is acceptable degradation."""
    returned = [s for s in roster() if s["label"] not in {"fig0", "fig1", "fig2", "fig3"}]  # 32
    r = cq.check_quorum(roster(), returned)
    assert r["ok"] is True
    assert r["dropped_kinds"] == []
    assert sorted(r["missing"]) == ["fig0", "fig1", "fig2", "fig3"]


def test_below_quorum_fails():
    returned = roster()[:20]  # 20/36 = 55%
    r = cq.check_quorum(roster(), returned)
    assert r["ok"] is False
    assert r["quorum_ratio"] < 0.75


def test_strict_requires_every_seat():
    returned = roster()[:35]  # one missing
    assert cq.check_quorum(roster(), returned, strict=True)["ok"] is False
    assert cq.check_quorum(roster(), roster(), strict=True)["ok"] is True


def test_extra_seats_reported_not_fatal():
    returned = roster() + [{"label": "ghost", "kind": "figure"}]
    r = cq.check_quorum(roster(), returned)
    assert r["ok"] is True
    assert r["extra"] == ["ghost"]


def test_by_kind_breakdown():
    returned = [s for s in roster() if s["kind"] != "model"]
    r = cq.check_quorum(roster(), returned)
    assert r["expected_by_kind"] == {"model": 5, "style": 8, "figure": 23}
    assert r["returned_by_kind"].get("model", 0) == 0


def test_empty_expected_is_vacuously_ok():
    r = cq.check_quorum([], [])
    assert r["ok"] is True
    assert r["quorum_ratio"] == 1.0


def test_duplicate_label_not_double_counted():
    """A single physical response must not satisfy multiple expected seats sharing a label."""
    exp = [{"label": "dup", "kind": "figure"}] * 4 + [{"label": f"u{i}", "kind": "figure"} for i in range(4)]
    ret = [{"label": "dup", "kind": "figure"}] + [{"label": f"u{i}", "kind": "figure"} for i in range(3)]
    r = cq.check_quorum(exp, ret)
    assert r["expected"] == 8
    assert r["returned"] == 4            # not 7 — 'dup' returned once covers one seat, not four
    assert r["missing"].count("dup") == 3
    assert r["ok"] is False              # 4/8 = 50% < quorum
