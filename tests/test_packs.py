"""Validate Council pack files against the authoring contract.

Dependency-free (hand-parses the simple, controlled frontmatter) so it runs
under any Python 3 without pip installs. Run: pytest tests/test_packs.py -v
"""
import re
import pathlib
import pytest

SKILL = pathlib.Path(__file__).resolve().parent.parent / "skill"
FIG_DIR = SKILL / "packs" / "figures"
STYLES_DIR = SKILL / "packs" / "styles"

REQUIRED_COUNCIL_KEYS = ["figure", "domain", "polarity", "polarity_pairs", "triads", "one_liner", "default_panel"]
REQUIRED_SECTIONS = [
    "## Identity",
    "## Grounding Protocol",
    "## Analytical Method",
    "## What You See That Others Miss",
    "## What You Tend to Miss",
    "## When Deliberating in Council",
]
DEFAULT_PANEL = {"socrates", "feynman", "munger", "taleb", "torvalds"}
# 18 ported + 5 authored = 23
EXPECTED_MIN_FIGURES = 23


def figure_files():
    return sorted(p for p in FIG_DIR.glob("*.md") if p.name != "triads.md")


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, "missing/malformed frontmatter"
    return m.group(1), m.group(2)


def council_block(fm):
    """Return dict of the indented keys under `council:`."""
    out = {}
    in_council = False
    for line in fm.splitlines():
        if re.match(r"^council:\s*$", line):
            in_council = True
            continue
        if in_council:
            m = re.match(r"^\s{2,}([A-Za-z_]+):\s*(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2).strip()
            elif line and not line.startswith(" "):
                break
    return out


def test_figures_exist_and_count():
    files = figure_files()
    assert len(files) >= EXPECTED_MIN_FIGURES, f"only {len(files)} figures; expected >= {EXPECTED_MIN_FIGURES}"


@pytest.mark.parametrize("path", figure_files(), ids=lambda p: p.stem)
def test_figure_frontmatter_and_sections(path):
    fm, body = split_frontmatter(path.read_text())
    assert re.search(r"^name:\s*council-", fm, re.M), f"{path.name}: name must be council-<slug>"
    cb = council_block(fm)
    for key in REQUIRED_COUNCIL_KEYS:
        assert key in cb and cb[key] != "", f"{path.name}: missing council.{key}"
    assert cb["default_panel"] in ("true", "false"), f"{path.name}: default_panel must be true/false"
    for section in REQUIRED_SECTIONS:
        assert section in body, f"{path.name}: missing section '{section}'"


def test_default_panel_is_the_five():
    flagged = set()
    for path in figure_files():
        fm, _ = split_frontmatter(path.read_text())
        if council_block(fm).get("default_panel") == "true":
            flagged.add(path.stem)
    assert flagged == DEFAULT_PANEL, f"default panel mismatch: {flagged} != {DEFAULT_PANEL}"


def test_new_figures_present():
    have = {p.stem for p in figure_files()}
    for slug in ["jacobs", "hopper", "naval", "graham", "musk"]:
        assert slug in have, f"new figure missing: {slug}"


def test_styles_default_has_five_lenses():
    text = (STYLES_DIR / "default.md").read_text()
    for lens in ["Contrarian", "First Principles", "Expansionist", "Outsider", "Executor"]:
        assert lens in text, f"styles/default.md missing lens: {lens}"


def test_advocate_lens_present_and_templated():
    text = (STYLES_DIR / "extras.md").read_text()
    assert "THE ADVOCATE" in text, "extras.md missing the Advocate lens"
    assert "{user_position}" in text, "Advocate lens must be parameterized by the user's leaning"
    assert "{framed_question}" in text
    # must be flagged as outside the standing style union (so it isn't auto-seated)
    assert "not part of the standing union" in text.lower()
    # and must NOT be listed in the extras `members:` frontmatter
    fm, _ = split_frontmatter(text)
    assert "advocate" not in fm.lower(), "Advocate must stay out of the extras members: list"


def test_skill_documents_advocate_seat():
    skill = (SKILL / "SKILL.md").read_text()
    assert "Seat the Advocate" in skill, "SKILL.md missing the Advocate-seat rule"
    assert "Advocate for the user's current leaning" in skill, "SKILL.md missing Advocate non-negotiable"


SENATE_DIR = SKILL / "packs" / "senate"


def test_senate_pack_files_present():
    for fname in ["roster.md", "committees.md", "prompts.md"]:
        assert (SENATE_DIR / fname).is_file(), f"senate pack missing {fname}"


def test_senate_roster_frontmatter():
    fm, _ = split_frontmatter((SENATE_DIR / "roster.md").read_text())
    assert re.search(r"^pack:\s*senate", fm, re.M), "roster.md needs pack: senate"
    assert re.search(r"^mode:\s*senate", fm, re.M), "roster.md needs mode: senate"


def test_senate_prompts_have_required_blocks():
    text = (SENATE_DIR / "prompts.md").read_text()
    for marker in [
        "Ballot Instruction", "BALLOT: stance=", "Clerk Prompt", "Whip Prompt",
        "Extended Chairman", "## The Vote", "## The Faction Map",
    ]:
        assert marker in text, f"senate prompts.md missing: {marker}"
