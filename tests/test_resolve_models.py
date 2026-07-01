"""Tests for resolve_models.py — pure logic + mocked catalog (no network)."""
import sys
import pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import resolve_models as rm  # noqa: E402

# Synthetic OpenRouter catalog: newer 'created' should win; variants excluded.
CATALOG = [
    {"id": "openai/gpt-5.0", "created": 100},
    {"id": "openai/gpt-5.1", "created": 200},                 # newest flagship -> win
    {"id": "openai/gpt-5.1-mini", "created": 300},            # excluded (mini)
    {"id": "google/gemini-3-pro", "created": 150},            # win
    {"id": "google/gemini-2.5-pro", "created": 140},          # fallback if newest is unservable
    {"id": "google/gemini-2.5-flash-lite", "created": 400},   # excluded (flash-lite)
    {"id": "x-ai/grok-4", "created": 120},                    # win
    {"id": "anthropic/claude-sonnet-4.6", "created": 210},    # win
    {"id": "anthropic/claude-3-haiku", "created": 50},
    {"id": "deepseek/deepseek-v4", "created": 180},           # breadth win
    {"id": "mistralai/mistral-large", "created": 90},
]

ALL_OK = lambda mid: True  # offline validator that approves everything


def test_excludes_variants_and_picks_newest():
    # no validator -> pick newest non-variant (offline)
    picks = rm.pick_latest_per_vendor(CATALOG, rm.CORE_VENDORS)
    assert picks["openai"]["model_id"] == "openai/gpt-5.1"      # not the mini, not 5.0
    assert picks["google"]["model_id"] == "google/gemini-3-pro" # not the flash-lite
    assert picks["x-ai"]["model_id"] == "x-ai/grok-4"
    assert picks["anthropic"]["model_id"] == "anthropic/claude-sonnet-4.6"


def test_validator_falls_through_to_next_servable():
    # reject the newest openai flagship -> resolver must fall through to the next-newest
    reject_51 = lambda mid: mid != "openai/gpt-5.1"
    picks = rm.pick_latest_per_vendor(CATALOG, ["openai"], validate=reject_51)
    assert picks["openai"]["model_id"] == "openai/gpt-5.0"      # fell through, skipped the mini

    # reject everything for a vendor -> that vendor is dropped, no crash
    picks = rm.pick_latest_per_vendor(CATALOG, ["openai"], validate=lambda mid: False)
    assert "openai" not in picks


def test_resolve_builds_four_core_plus_one_breadth(monkeypatch):
    monkeypatch.setattr(rm, "fetch_models", lambda: CATALOG)
    data = rm.resolve("2026-06-25", validate=ALL_OK)
    vendors = [s["vendor"] for s in data["seats"]]
    assert vendors[:4] == ["openai", "google", "x-ai", "anthropic"]
    assert len(data["seats"]) == 5  # 4 core + 1 breadth
    assert data["seats"][4]["vendor"] in rm.BREADTH_VENDORS
    assert data["chair"] == {"label": "Claude Opus", "native": True}
    assert data["resolved_at"] == "2026-06-25"


def test_resolve_drops_unservable_and_uses_next(monkeypatch):
    monkeypatch.setattr(rm, "fetch_models", lambda: CATALOG)
    # gemini-3-pro is "unservable" (simulating a 404) -> google seat must fall through
    bad = {"google/gemini-3-pro"}
    data = rm.resolve("2026-06-25", validate=lambda mid: mid not in bad)
    google = next(s for s in data["seats"] if s["vendor"] == "google")
    assert google["model_id"] != "google/gemini-3-pro"


def test_render_roster_has_parseable_json_block(monkeypatch):
    monkeypatch.setattr(rm, "fetch_models", lambda: CATALOG)
    data = rm.resolve("2026-06-25", validate=ALL_OK)
    md = rm.render_roster(data)
    import re, json
    m = re.search(r"```json\s*(\{.*?\})\s*```", md, re.S)
    assert m, "render_roster must emit a ```json block"
    parsed = json.loads(m.group(1))
    assert len(parsed["seats"]) == 5


def test_pretty_label():
    assert rm._pretty_label("openai", "openai/gpt-5.1") == "GPT 5.1"
    assert rm._pretty_label("anthropic", "anthropic/claude-sonnet-4.6").startswith("Claude")
