"""Tests for council_models.py — roster parsing + parallel dispatch with mocked POST."""
import sys
import json
import asyncio
import pathlib
import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import council_models as cm  # noqa: E402

ROSTER_JSON = {
    "resolved_at": "2026-06-25",
    "seats": [
        {"vendor": "openai", "label": "GPT-5.1", "model_id": "openai/gpt-5.1"},
        {"vendor": "google", "label": "Gemini 3 Pro", "model_id": "google/gemini-3-pro"},
        {"vendor": "x-ai", "label": "Grok 4", "model_id": "x-ai/grok-4"},
        {"vendor": "anthropic", "label": "Claude", "model_id": "anthropic/claude-sonnet-4.6"},
    ],
    "chair": {"label": "Claude Opus", "native": True},
}


def write_roster(tmp_path):
    p = tmp_path / "roster.md"
    p.write_text("---\npack: models\n---\n\n```json\n" + json.dumps(ROSTER_JSON) + "\n```\n")
    return p


def test_load_roster(tmp_path):
    p = write_roster(tmp_path)
    data = cm.load_roster(p)
    assert len(data["seats"]) == 4
    assert data["seats"][0]["model_id"] == "openai/gpt-5.1"


def test_load_roster_rejects_missing_block(tmp_path):
    p = tmp_path / "bad.md"
    p.write_text("no json here")
    with pytest.raises(SystemExit):
        cm.load_roster(p)


def test_run_council_all_ok(monkeypatch):
    def fake_post(model_id, prompt, key, timeout):
        return f"opinion from {model_id}", None
    monkeypatch.setattr(cm, "_post", fake_post)
    seats = [dict(s, _i=i) for i, s in enumerate(ROSTER_JSON["seats"])]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5))
    assert len(results) == 4
    assert all(r["ok"] for r in results)
    assert results[0]["content"] == "opinion from openai/gpt-5.1"
    assert all(isinstance(r["latency_ms"], int) for r in results)
    assert all(r["attempts"] == 1 for r in results)


def test_run_council_graceful_degradation(monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)

    def flaky_post(model_id, prompt, key, timeout):
        if "grok" in model_id:
            raise TimeoutError("seat timed out")
        return "ok", None
    monkeypatch.setattr(cm, "_post", flaky_post)
    seats = [dict(s, _i=i) for i, s in enumerate(ROSTER_JSON["seats"])]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5))
    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    assert len(ok) == 3 and len(bad) == 1          # one seat failed, run survives
    assert "TimeoutError" in bad[0]["error"]
    assert bad[0]["model_id"] == "x-ai/grok-4"
    assert bad[0]["attempts"] == 2                 # default retries=1 -> 2 total attempts


def test_load_key_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "  sk-or-test  ")
    assert cm.load_key() == "sk-or-test"


def test_build_prompt_appends_ballot():
    assert "BALLOT: stance=" in cm.build_prompt("Q", True)
    assert cm.build_prompt("Q", False) == "Q"


def test_query_model_parses_ballot(monkeypatch):
    def fake_post(model_id, prompt, key, timeout):
        return "my analysis\nBALLOT: stance=Yes | confidence=4 | reason=upside", None
    monkeypatch.setattr(cm, "_post", fake_post)
    seats = [dict(s, _i=i) for i, s in enumerate(ROSTER_JSON["seats"])]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5))
    assert results[0]["ballot"]["stance"] == "Yes"
    assert results[0]["ballot"]["confidence"] == 4
    assert results[0]["ballot"]["ok"] is True


def test_query_model_no_ballot_is_abstain(monkeypatch):
    monkeypatch.setattr(cm, "_post", lambda *a: ("no ballot here", None))
    seats = [dict(s, _i=i) for i, s in enumerate(ROSTER_JSON["seats"][:1])]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5))
    assert results[0]["ballot"]["ok"] is False


def test_usage_captured_when_present(monkeypatch):
    usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    def fake_post(model_id, prompt, key, timeout):
        return f"opinion from {model_id}", usage
    monkeypatch.setattr(cm, "_post", fake_post)
    seats = [dict(s, _i=i) for i, s in enumerate(ROSTER_JSON["seats"])]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5))
    assert all(r["usage"] == usage for r in results)


def test_usage_null_when_absent(monkeypatch):
    def fake_post(model_id, prompt, key, timeout):
        return f"opinion from {model_id}", None
    monkeypatch.setattr(cm, "_post", fake_post)
    seats = [dict(s, _i=i) for i, s in enumerate(ROSTER_JSON["seats"])]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5))
    assert all(r["usage"] is None for r in results)


def test_seat_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def flaky(model_id, prompt, key, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("first attempt failed")
        return "recovered", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    monkeypatch.setattr(cm, "_post", flaky)
    seats = [dict(ROSTER_JSON["seats"][0], _i=0)]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5, retries=1))
    assert results[0]["ok"] is True
    assert results[0]["attempts"] == 2
    assert results[0]["content"] == "recovered"
    assert results[0]["usage"]["total_tokens"] == 15


def test_seat_retries_exhausted(monkeypatch):
    monkeypatch.setattr(cm.time, "sleep", lambda s: None)

    def always_fail(model_id, prompt, key, timeout):
        raise TimeoutError("still failing")
    monkeypatch.setattr(cm, "_post", always_fail)
    seats = [dict(ROSTER_JSON["seats"][0], _i=0)]
    results = asyncio.run(cm.run_council("framed?", seats, "k", 5, retries=2))
    assert results[0]["ok"] is False
    assert results[0]["attempts"] == 3          # 1 initial + 2 retries
    assert "TimeoutError" in results[0]["error"]
    assert results[0]["usage"] is None
