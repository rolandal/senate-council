"""Tests for anonymize.py — mechanized A-Z anonymization for peer review.

Pins the properties peer review depends on: deterministic given a seed, a full
bijective map back to originals, exact content preservation, and no leakage of
identifying keys (label, model_id, ...) into the anonymized entries.
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pytest

import anonymize as an  # noqa: E402


def _responses(n):
    return [
        {"label": f"member-{i}", "content": f"content body {i}", "model_id": f"model-{i}", "ballot": "A"}
        for i in range(n)
    ]


def test_determinism_given_seed():
    responses = _responses(6)
    r1 = an.anonymize(responses, seed=42)
    r2 = an.anonymize(responses, seed=42)
    assert r1 == r2


def test_map_is_bijection_covering_all_labels():
    responses = _responses(10)
    result = an.anonymize(responses, seed=7)
    original_labels = {r["label"] for r in responses}
    mapped_labels = set(result["map"].values())
    assert mapped_labels == original_labels
    # bijection: as many anon keys as originals, all unique
    assert len(result["map"]) == len(responses)
    assert len(set(result["map"].keys())) == len(responses)


def test_contents_preserved_exactly():
    responses = _responses(5)
    result = an.anonymize(responses, seed=3)
    original_contents = {r["content"] for r in responses}
    anon_contents = {e["content"] for e in result["anonymized"]}
    assert anon_contents == original_contents


def test_no_identifying_keys_leak():
    responses = _responses(8)
    result = an.anonymize(responses, seed=1)
    for entry in result["anonymized"]:
        assert set(entry.keys()) == {"anon", "content"}
        assert "label" not in entry
        assert "model_id" not in entry
        assert "ballot" not in entry


def test_brief_shaped_input_errors_instead_of_silent_blanks():
    """Bundle-shaped briefs ({committee, labels, miniTally, text}) must fail loudly —
    never emit empty content with an all-null map (SKILL.md Stage 3c requires the
    {label, content} reshape first)."""
    briefs = [{"committee": i, "labels": ["x", "y"], "miniTally": "3A, 3B", "text": f"brief {i}"}
              for i in range(6)]
    with pytest.raises(ValueError):
        an.anonymize(briefs, seed=7)


def test_missing_label_or_empty_content_errors():
    with pytest.raises(ValueError):
        an.anonymize([{"content": "body but no label"}], seed=1)
    with pytest.raises(ValueError):
        an.anonymize([{"label": "member-0", "content": ""}], seed=1)


def test_27_responses_errors():
    responses = _responses(27)
    with pytest.raises(ValueError):
        an.anonymize(responses, seed=1)


def test_empty_input_errors():
    with pytest.raises(ValueError):
        an.anonymize([], seed=1)


def test_seed_echoed_in_output():
    result = an.anonymize(_responses(3), seed=99)
    assert result["seed"] == 99


def test_cli_empty_array_exits(tmp_path):
    responses_file = tmp_path / "empty.json"
    responses_file.write_text("[]")
    sys.argv = ["anonymize.py", "--responses-file", str(responses_file)]
    with pytest.raises(SystemExit):
        an.main()


def test_cli_27_responses_exits(tmp_path):
    import json
    responses_file = tmp_path / "resp.json"
    responses_file.write_text(json.dumps(_responses(27)))
    sys.argv = ["anonymize.py", "--responses-file", str(responses_file)]
    with pytest.raises(SystemExit):
        an.main()


def test_cli_seed_omitted_generates_and_echoes(tmp_path, capsys):
    import json
    responses_file = tmp_path / "resp.json"
    responses_file.write_text(json.dumps(_responses(4)))
    sys.argv = ["anonymize.py", "--responses-file", str(responses_file)]
    an.main()
    out = json.loads(capsys.readouterr().out)
    assert isinstance(out["seed"], int)


def test_cli_prefix_applied(tmp_path, capsys):
    import json
    responses_file = tmp_path / "resp.json"
    responses_file.write_text(json.dumps(_responses(3)))
    sys.argv = ["anonymize.py", "--responses-file", str(responses_file), "--seed", "1", "--prefix", "Seat"]
    an.main()
    out = json.loads(capsys.readouterr().out)
    assert all(e["anon"].startswith("Seat ") for e in out["anonymized"])
