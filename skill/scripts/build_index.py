#!/usr/bin/env python3
"""Build a searchable index of council-log transcripts.

Council runs pile up as loose `council-YYYY-MM-DD-<slug>-transcript.md` files
in the log dir with no way to find anything short of grepping filenames.
SKILL.md's Stage 1 says to "search prior councils" against nothing structured.
This scans the log dir and writes an index.

For every `*-transcript.md` it extracts: date + slug (from the filename), the
report title (the file's `# ...` heading), mode/tier (from the `## Metadata`
block when present, else the `**Mode:** X (Y)` header line), a one-line
recommendation (the first sentence under `## The Recommendation`, when found),
and whether/how many Kill Criteria exist. Writes two files into `--out-dir`
(default: same as `--log-dir`):

  index.json  — {"entries": [...newest first...], "skipped": [...]}
  index.html  — standalone dark-styled page, inline CSS, no external assets

Malformed or non-matching files are recorded in the "skipped" list and never
fail the run.

  python3 build_index.py
  python3 build_index.py --log-dir ~/Documents/Local/council-log --out-dir /tmp/out
"""
import argparse
import html
import json
import re
from pathlib import Path

FILENAME_RE = re.compile(r"^council-(\d{4}-\d{2}-\d{2})-(.+)-transcript\.md$")
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
METADATA_RE = re.compile(r"^## Metadata\s*\n+```yaml\n(.*?)\n```", re.MULTILINE | re.DOTALL)
HEADER_MODE_RE = re.compile(r"\*\*Mode:\*\*\s*([^(\n]+?)\s*\(([^)\n]+)\)")
BULLET_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(.*\S)\s*$")


def _section_text(text, heading):
    """Return the body text under a '## <heading>' line (up to the next '## '), or None."""
    lines = text.splitlines()
    target = heading.strip().lower()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            start = i + 1
            break
    if start is None:
        return None
    body = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body).strip()


def _first_sentence(section_text):
    """Best-effort first sentence of a section, markdown emphasis stripped."""
    if not section_text:
        return None
    first_para = section_text.strip().split("\n\n", 1)[0]
    clean = re.sub(r"[*_`]", "", first_para)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return None
    m = re.search(r"^(.*?[.!?])(?:\s|$)", clean)
    return (m.group(1) if m else clean).strip()


def _count_bullets(text):
    if not text:
        return 0
    return sum(1 for line in text.splitlines() if BULLET_RE.match(line))


def _parse_metadata(text):
    """Parse the '## Metadata' fenced ```yaml block (its body is actually JSON). None if absent/bad."""
    m = METADATA_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except (ValueError, TypeError):
        return None


def parse_transcript(path):
    """Parse one transcript file into an index entry dict. Raises ValueError on any parse failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"unreadable: {e}")

    m = FILENAME_RE.match(path.name)
    if not m:
        raise ValueError("filename does not match council-YYYY-MM-DD-<slug>-transcript.md")
    date, slug = m.group(1), m.group(2)

    tm = TITLE_RE.search(text)
    if not tm:
        raise ValueError("no '# ' title heading found")
    title = tm.group(1).strip()

    meta = _parse_metadata(text)
    mode = meta.get("mode") if meta else None
    tier = meta.get("tier_strategy") if meta else None
    if mode is None or tier is None:
        hm = HEADER_MODE_RE.search(text)
        if hm:
            mode = mode or hm.group(1).strip().lower()
            tier = tier or hm.group(2).strip()

    recommendation = _first_sentence(_section_text(text, "## The Recommendation"))

    kill_text = _section_text(text, "## Kill Criteria")
    has_kill_criteria = kill_text is not None
    kill_criteria_count = _count_bullets(kill_text)

    return {
        "file": path.name,
        "date": date,
        "slug": slug,
        "title": title,
        "mode": mode,
        "tier": tier,
        "recommendation": recommendation,
        "has_kill_criteria": has_kill_criteria,
        "kill_criteria_count": kill_criteria_count,
        "report_html": re.sub(r"-transcript\.md$", ".html", path.name),
    }


def build_index(log_dir):
    """Scan log_dir for *-transcript.md files. Returns (entries newest-first, skipped)."""
    entries, skipped = [], []
    for path in sorted(Path(log_dir).glob("*-transcript.md")):
        try:
            entries.append(parse_transcript(path))
        except ValueError as e:
            skipped.append({"file": path.name, "reason": str(e)})
    entries.sort(key=lambda e: (e["date"], e["file"]), reverse=True)
    return entries, skipped


def render_html(entries):
    """Render a standalone dark-styled index page. Inline CSS only, no external assets."""
    items = []
    for e in entries:
        title = html.escape(e["title"] or e["slug"])
        date = html.escape(e["date"] or "")
        mode_label = e["mode"] or "—"
        if e["tier"]:
            mode_label = f"{mode_label} ({e['tier']})"
        mode_label = html.escape(mode_label)
        rec = html.escape(e["recommendation"] or "—")
        href = html.escape(e["report_html"])
        kill_badge = (f'<span class="badge badge-kill">{e["kill_criteria_count"]} kill criteria</span>'
                      if e["has_kill_criteria"] else "")
        items.append(f'''      <li class="run">
        <div class="run-head">
          <a class="run-title" href="{href}">{title}</a>
          <span class="run-date">{date}</span>
        </div>
        <div class="run-meta"><span class="badge">{mode_label}</span>{kill_badge}</div>
        <p class="run-rec">{rec}</p>
      </li>''')
    body = "\n".join(items) if items else '      <li class="empty">No council runs found.</li>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Council Log Index</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{
    margin: 0; padding: 2.5rem 1.5rem;
    background: #0b0d10; color: #e6e8eb;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  h1 {{ font-size: 1.4rem; margin: 0 0 1.5rem; color: #fafafa; }}
  ul {{ list-style: none; margin: 0; padding: 0; max-width: 780px; }}
  li.run {{
    border: 1px solid #23262b; border-radius: 10px;
    padding: 1rem 1.25rem; margin-bottom: 0.9rem; background: #14171b;
  }}
  .run-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }}
  .run-title {{ color: #7dd3fc; text-decoration: none; font-weight: 600; }}
  .run-title:hover {{ text-decoration: underline; }}
  .run-date {{ color: #8b929c; font-size: 0.85rem; white-space: nowrap; }}
  .run-meta {{ margin: 0.4rem 0; }}
  .badge {{
    display: inline-block; font-size: 0.75rem; padding: 0.15rem 0.5rem;
    border-radius: 999px; background: #23262b; color: #c7cbd1; margin-right: 0.4rem;
  }}
  .badge-kill {{ background: #3a2323; color: #f5b0b0; }}
  .run-rec {{ margin: 0.4rem 0 0; color: #cdd2d8; font-size: 0.92rem; }}
  li.empty {{ color: #8b929c; }}
</style>
</head>
<body>
<h1>Council Log Index — {len(entries)} run(s)</h1>
<ul>
{body}
</ul>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", default=str(Path.home() / "Documents" / "Local" / "council-log"),
                     help="directory holding *-transcript.md run logs")
    ap.add_argument("--out-dir", default=None, help="where to write index.json/index.html (default: --log-dir)")
    args = ap.parse_args()

    log_dir = Path(args.log_dir)
    out_dir = Path(args.out_dir) if args.out_dir else log_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    entries, skipped = build_index(log_dir)
    (out_dir / "index.json").write_text(json.dumps({"entries": entries, "skipped": skipped}, indent=2) + "\n",
                                         encoding="utf-8")
    (out_dir / "index.html").write_text(render_html(entries), encoding="utf-8")

    print(f"Indexed {len(entries)} transcript(s), skipped {len(skipped)} -> {out_dir}")
    if skipped:
        for s in skipped:
            print(f"  skipped {s['file']}: {s['reason']}")


if __name__ == "__main__":
    main()
