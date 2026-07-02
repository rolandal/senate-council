"""Tests for run_state.py — resumable run checkpoints.

Pins the round-trip: init creates a manifest, save copies artifacts and advances
"next" per the canonical stage order (even when stages are saved out of order),
unknown stages are rejected, init is idempotent/non-destructive, and status
reports complete=true once every canonical stage has been saved.
"""
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_state as rs  # noqa: E402


def test_init_creates_manifest_with_next_frame(tmp_path):
    result = rs.init_run("relocation-senate", run_root=str(tmp_path), date="2026-06-26")
    run_dir = pathlib.Path(result["run_dir"])
    assert run_dir == tmp_path / "2026-06-26-relocation-senate"
    assert run_dir.is_dir()
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest == {"slug": "relocation-senate", "date": "2026-06-26", "stages": {}}
    assert result["next"] == "frame"
    assert result["complete"] is False


def test_init_is_idempotent_and_non_destructive(tmp_path):
    first = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    run_dir = first["run_dir"]
    # simulate progress already recorded
    artifact = tmp_path / "frame.json"
    artifact.write_text('{"question": "stay or go"}')
    rs.save_stage(run_dir, "frame", str(artifact), now="2026-06-26T10:00:00+00:00")

    second = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    assert second["run_dir"] == run_dir
    # the previously-saved stage must survive re-init
    assert "frame" in second["stages"]
    assert second["next"] == "prompts"


def test_save_two_stages_out_of_order_advances_next_by_canonical_order(tmp_path):
    init = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    run_dir = init["run_dir"]

    convene_file = tmp_path / "responses.json"
    convene_file.write_text('{"responses": []}')
    frame_file = tmp_path / "frame.json"
    frame_file.write_text('{"question": "stay or go"}')

    # save a LATER stage first
    result = rs.save_stage(run_dir, "convene", str(convene_file), now="2026-06-26T11:00:00+00:00")
    assert "convene" in result["stages"]
    # next should still be the first missing canonical stage, not "gate_quorum"
    assert result["next"] == "frame"

    artifacts_dir = pathlib.Path(run_dir) / "artifacts"
    assert (artifacts_dir / "convene-responses.json").exists()
    assert result["stages"]["convene"] == {
        "saved_at": "2026-06-26T11:00:00+00:00",
        "artifact": "artifacts/convene-responses.json",
    }

    # now save the earlier stage
    result2 = rs.save_stage(run_dir, "frame", str(frame_file), now="2026-06-26T10:00:00+00:00")
    assert result2["next"] == "prompts"
    assert set(result2["stages"]) == {"frame", "convene"}


def test_unknown_stage_raises_system_exit(tmp_path):
    init = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    bogus_file = tmp_path / "x.json"
    bogus_file.write_text("{}")
    try:
        rs.save_stage(init["run_dir"], "not_a_real_stage", str(bogus_file))
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert "not_a_real_stage" in str(e)
        for stage in rs.STAGES:
            assert stage in str(e)


def test_status_complete_true_when_all_stages_saved(tmp_path):
    init = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    run_dir = init["run_dir"]
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}")
    for i, stage in enumerate(rs.STAGES):
        rs.save_stage(run_dir, stage, str(artifact), now=f"2026-06-26T{10 + i:02d}:00:00+00:00")

    status = rs.get_status(run_dir)
    assert status["complete"] is True
    assert status["next"] is None
    assert set(status["stages"]) == set(rs.STAGES)


def test_corrupt_manifest_exits_with_guidance_not_traceback(tmp_path):
    init = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    (pathlib.Path(init["run_dir"]) / "manifest.json").write_text('{"slug": "senate", ')
    try:
        rs.get_status(init["run_dir"])
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert "corrupt manifest" in str(e)
        assert "artifacts" in str(e)


def test_cli_status_prints_json(tmp_path, capsys):
    init = rs.init_run("senate", run_root=str(tmp_path), date="2026-06-26")
    sys.argv = ["run_state.py", "status", "--run-dir", init["run_dir"]]
    rs.main()
    out = json.loads(capsys.readouterr().out)
    assert out["next"] == "frame"
    assert out["slug"] == "senate"
