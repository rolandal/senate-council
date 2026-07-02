"""Tests for skill/scripts/detect-providers.sh roster staleness fields.

Runs the shell script via subprocess with DETECT_TODAY pinned so the age/
staleness math is deterministic, then asserts the emitted JSON carries the
new roster_resolved_at / roster_age_days / roster_stale fields alongside the
pre-existing keys.

    .venv/bin/python -m pytest tests/test_detect_providers.py -q
"""
import json
import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skill" / "scripts" / "detect-providers.sh"
ROSTER = REPO_ROOT / "skill" / "packs" / "models" / "roster.md"


def run_detect(today=None, env_overrides=None):
    env = {"HOME": str(REPO_ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    if today:
        env["DETECT_TODAY"] = today
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return json.loads(result.stdout)


def resolved_at_from_roster():
    text = ROSTER.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("resolved_at:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("resolved_at not found in roster.md fixture")


def test_pre_existing_keys_still_present():
    data = run_detect(today="2026-06-30")
    for key in ("openrouter_key", "clis", "claude_models", "tier"):
        assert key in data


def test_roster_not_stale_shortly_after_resolution():
    resolved_at = resolved_at_from_roster()
    # 5 days after resolved_at.
    import datetime
    today = (
        datetime.date.fromisoformat(resolved_at) + datetime.timedelta(days=5)
    ).isoformat()

    data = run_detect(today=today)

    assert data["roster_resolved_at"] == resolved_at
    assert data["roster_age_days"] == 5
    assert data["roster_stale"] is False


def test_roster_stale_after_60_days():
    resolved_at = resolved_at_from_roster()
    import datetime
    today = (
        datetime.date.fromisoformat(resolved_at) + datetime.timedelta(days=60)
    ).isoformat()

    data = run_detect(today=today)

    assert data["roster_resolved_at"] == resolved_at
    assert data["roster_age_days"] == 60
    assert data["roster_stale"] is True


def test_missing_roster_file_yields_nulls_and_not_stale(tmp_path, monkeypatch):
    # Copy the script to an isolated dir with no ../packs/models/roster.md
    # so the script's relative-path resolution finds nothing.
    isolated_scripts = tmp_path / "skill" / "scripts"
    isolated_scripts.mkdir(parents=True)
    script_copy = isolated_scripts / "detect-providers.sh"
    script_copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    script_copy.chmod(0o755)

    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin", "DETECT_TODAY": "2026-06-30"}
    result = subprocess.run(
        ["bash", str(script_copy)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    data = json.loads(result.stdout)

    assert data["roster_resolved_at"] is None
    assert data["roster_age_days"] is None
    assert data["roster_stale"] is False


def test_non_utf8_roster_still_prints_json_with_nulls(tmp_path):
    # A roster that makes the embedded python die (UnicodeDecodeError) must not
    # break the "prints a single JSON object" contract — the || guard maps any
    # python failure to nulls.
    isolated_scripts = tmp_path / "skill" / "scripts"
    isolated_scripts.mkdir(parents=True)
    script_copy = isolated_scripts / "detect-providers.sh"
    script_copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    script_copy.chmod(0o755)
    roster_dir = tmp_path / "skill" / "packs" / "models"
    roster_dir.mkdir(parents=True)
    (roster_dir / "roster.md").write_bytes(b"\xff\xfe not utf-8 \x80\x81")

    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin", "DETECT_TODAY": "2026-06-30"}
    result = subprocess.run(
        ["bash", str(script_copy)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    data = json.loads(result.stdout)

    assert data["roster_resolved_at"] is None
    assert data["roster_age_days"] is None
    assert data["roster_stale"] is False
