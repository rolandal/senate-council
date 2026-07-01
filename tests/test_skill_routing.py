# tests/test_skill_routing.py
"""Structural guard: SKILL.md must route to Senate (mode 5)."""
import pathlib

SKILL_MD = pathlib.Path(__file__).resolve().parent.parent / "skill" / "SKILL.md"


def test_senate_trigger_documented():
    text = SKILL_MD.read_text().lower()
    assert "council me senate" in text
    assert "senate express" in text
    assert "senate max" in text


def test_mode_5_section_present():
    assert "## Mode 5: Senate" in SKILL_MD.read_text()


def test_picker_two_step_reaches_senate():
    text = SKILL_MD.read_text()
    assert "Full-house panels" in text   # step-1 option that branches
    assert "2. Senate" in text           # step-2 option
