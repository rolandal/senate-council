"""End-to-end smoke test — chains the mechanical Senate pipeline on the golden fixture.

The golden test (tests/test_render_golden.py) owns exact bytes for one bundle.
This file owns the CROSS-SCRIPT CONTRACTS between the pipeline stages: does the
seat roster derived from a real bundle satisfy the input gate, the quorum gate,
the tally, committee assignment, anonymization, run-state checkpointing, and the
final render — all wired together the way `council me senate` actually wires
them. It does not pin exact HTML/markdown bytes; it pins shapes and invariants
that must hold no matter how the renderer's markup evolves.

  python3 -m pytest tests/smoke/test_pipeline_chain.py -q
"""
import copy
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import anonymize as an          # noqa: E402
import assign_committees as ac  # noqa: E402
import check_inputs as ci       # noqa: E402
import check_quorum as cq       # noqa: E402
import render_report as rr      # noqa: E402
import run_state as rs          # noqa: E402
import tally_ballots as tb      # noqa: E402

OPTIONS = ["A", "B", "C"]


def _bundle():
    return json.loads((FIX / "relocation-senate.bundle.json").read_text())


def _roster(bundle):
    """[{label, kind}] — the dispatched seat roster, derived from bundle members."""
    return [{"label": m["label"], "kind": m["kind"]} for m in bundle["members"]]


def _prompts(bundle, roster):
    """[{label, prompt}] — synthetic dispatched prompts, each embedding the framed question."""
    framed = bundle["framed"]
    return [{"label": s["label"], "prompt": f"You are {s['label']}.\n\nTHE FRAMED QUESTION:\n{framed}\n\nCast a ballot."}
            for s in roster]


def _ballots(bundle):
    """Member stances/confidences reshaped into the {ok, stance, confidence} shape tally() expects."""
    return [{"ok": True, "stance": m["stance"], "confidence": m.get("confidence")} for m in bundle["members"]]


# ── (1) seat roster ──────────────────────────────────────────────────────
def test_roster_derived_from_bundle_has_all_kinds_and_seats():
    bundle = _bundle()
    roster = _roster(bundle)
    assert len(roster) == len(bundle["members"]) == 36
    assert all(set(s.keys()) == {"label", "kind"} for s in roster)
    assert {s["kind"] for s in roster} == {"model", "style", "figure"}


# ── (2) check_inputs ─────────────────────────────────────────────────────
def test_check_inputs_passes_on_clean_prompts_and_fails_on_corruption():
    bundle = _bundle()
    roster = _roster(bundle)
    prompts = _prompts(bundle, roster)

    result = ci.check_inputs(prompts, framed=bundle["framed"])
    assert result["ok"] is True
    assert result["passed"] == len(prompts) and not result["failures"]

    corrupted = copy.deepcopy(prompts)
    corrupted[0]["prompt"] = f"You are {corrupted[0]['label']}.\n\nTHE FRAMED QUESTION:\nundefined"
    bad = ci.check_inputs(corrupted, framed=bundle["framed"])
    assert bad["ok"] is False
    assert bad["failures"] == [{"label": roster[0]["label"],
                                 "reason": "framed question missing; found unfilled placeholder ('undefined')"}]


# ── (3) check_quorum ─────────────────────────────────────────────────────
def test_check_quorum_passes_full_house_fails_on_whole_kind_drop():
    bundle = _bundle()
    roster = _roster(bundle)

    full = cq.check_quorum(roster, roster)
    assert full["ok"] is True
    assert full["expected"] == full["returned"] == 36
    assert full["dropped_kinds"] == []

    returned_no_models = [s for s in roster if s["kind"] != "model"]
    dropped = cq.check_quorum(roster, returned_no_models)
    assert dropped["ok"] is False
    assert dropped["dropped_kinds"] == ["model"]


# ── (4) tally_ballots ────────────────────────────────────────────────────
def test_tally_ballots_reproduces_bundle_tally_counts():
    bundle = _bundle()
    ballots = _ballots(bundle)
    result = tb.tally(ballots, options=OPTIONS)
    assert result["counts"] == bundle["tally"]["counts"]
    assert result["total"] == bundle["tally"]["total"]
    assert result["abstain"] == bundle["tally"]["abstain"]
    assert result["leader"] == bundle["tally"]["leader"]
    assert result["confidence_by_stance"] == bundle["tally"]["confidence_by_stance"]


# ── (5) assign_committees ────────────────────────────────────────────────
def test_assign_committees_places_every_seat_once_with_kind_diversity():
    bundle = _bundle()
    roster = _roster(bundle)
    committees = ac.assign_committees(roster, size=6)

    assert len(committees) == 6
    all_labels = [s["label"] for c in committees for s in c]
    assert sorted(all_labels) == sorted(s["label"] for s in roster)   # every seat placed exactly once
    assert len(all_labels) == len(set(all_labels))                    # ...and only once

    multi_kind_committees = sum(1 for c in committees if len({s["kind"] for s in c}) > 1)
    assert multi_kind_committees > 1  # kind-diversity spread across committees, not one clump


# ── (6) anonymize ────────────────────────────────────────────────────────
def test_anonymize_is_deterministic_bijective_and_leaks_no_labels():
    bundle = _bundle()
    briefs = bundle["briefs"][:6]
    responses = [{"label": f"Committee {b['committee'] + 1}", "content": b["text"], "kind": "committee"}
                 for b in briefs]

    r1 = an.anonymize(responses, seed=1234)
    r2 = an.anonymize(responses, seed=1234)
    assert r1 == r2  # deterministic given a fixed seed

    original_labels = {r["label"] for r in responses}
    assert set(r1["map"].values()) == original_labels        # bijection covers every original
    assert len(r1["map"]) == len(responses)
    for entry in r1["anonymized"]:
        assert set(entry.keys()) == {"anon", "content"}       # no label/kind leakage
        assert entry["anon"] not in original_labels
        assert not any(lbl in entry["anon"] for lbl in original_labels)


# ── (7) run_state ────────────────────────────────────────────────────────
def test_run_state_status_next_advances_across_saved_stages(tmp_path):
    bundle = _bundle()
    init = rs.init_run("relocation-senate", run_root=str(tmp_path), date="2026-06-26")
    run_dir = init["run_dir"]
    assert init["next"] == "frame"

    frame_file = tmp_path / "frame.json"
    frame_file.write_text(json.dumps({"framed": bundle["framed"]}))
    after_frame = rs.save_stage(run_dir, "frame", str(frame_file), now="2026-06-26T10:00:00+00:00")
    assert after_frame["next"] == "prompts"

    prompts_file = tmp_path / "prompts.json"
    prompts_file.write_text(json.dumps(_prompts(bundle, _roster(bundle))))
    after_prompts = rs.save_stage(run_dir, "prompts", str(prompts_file), now="2026-06-26T10:05:00+00:00")
    assert after_prompts["next"] == "gate_inputs"

    status = rs.get_status(run_dir)
    assert status["next"] == "gate_inputs"
    assert set(status["stages"]) == {"frame", "prompts"}
    assert status["complete"] is False


# ── (8) build_report ─────────────────────────────────────────────────────
def test_build_report_html_contains_tally_leader_count_and_title():
    bundle = _bundle()
    template = (ROOT / "skill" / "report-template.html").read_text()
    raw_title = "Daniel & Priya: take the career-defining cross-country move, or stay?"

    out = rr.build_report(bundle, template=template, slug="relocation-senate", date="2026-06-26",
                          raw_title=raw_title, timestamp="2026-06-26 12:00")

    leader = bundle["tally"]["leader"]
    leader_count = bundle["tally"]["counts"][leader]
    assert f">{leader_count}<" in out["html"]
    assert html.escape(raw_title) in out["html"]
    assert "<title>Council Verdict — relocation-senate</title>" in out["html"]
