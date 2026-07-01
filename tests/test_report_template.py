"""The report template must carry both the existing and the Senate placeholders."""
import pathlib

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "skill" / "report-template.html"


def test_senate_placeholders_present():
    text = TEMPLATE.read_text()
    for ph in ["{{senate_vote}}", "{{senate_factions}}", "{{committee_briefs}}"]:
        assert ph in text, f"report template missing senate placeholder {ph}"


def test_existing_placeholders_intact():
    text = TEMPLATE.read_text()
    for ph in ["{{mode_banner}}", "{{verdict_recommendation}}", "{{advisor_cards}}"]:
        assert ph in text, f"report template lost placeholder {ph}"
