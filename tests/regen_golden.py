"""Regenerate the relocation-senate golden fixture's expected output files.

Run this ONLY after an intentional change to render_report.py or
report-template.html. It re-renders the committed bundle through build_report()
with the same PINNED parameters the test uses, and overwrites:
  - tests/fixtures/relocation-senate.expected.html
  - tests/fixtures/relocation-senate.expected.transcript.md

    python3 tests/regen_golden.py

Then re-run `python3 -m pytest tests/test_render_golden.py` to confirm green.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_render_golden import _render, FIX  # noqa: E402


def main():
    out = _render()
    (FIX / "relocation-senate.expected.html").write_text(out["html"])
    (FIX / "relocation-senate.expected.transcript.md").write_text(out["transcript"])
    print(f"Wrote {FIX / 'relocation-senate.expected.html'}")
    print(f"Wrote {FIX / 'relocation-senate.expected.transcript.md'}")


if __name__ == "__main__":
    main()
