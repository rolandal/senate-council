#!/usr/bin/env python3
"""Render a council bundle into the HTML report + markdown transcript.

Fills `report-template.html` from a single bundle dict so the orchestrator never
has to hand-template the output (and every report comes out visually identical).
Built for the Senate (vote bar, faction map, committee briefs) and degrades
cleanly for modes 1-4 (no committees -> Senate-only blocks render empty).

The one hard contract it relies on: the chairman verdict uses `## ` section
headers (The Vote / The Faction Map / Where the Council Agrees / ... / What the
Council Doesn't Know). A dumb substring splitter maps them to placeholders, so
keep that header format rigid.

Bundle schema (keys optional unless noted):
  framed (str, required) · tally {counts, total, confidence_by_stance, leader}
  tallyStr (str) · members [{label, kind, stance, confidence, reason, analysis?}]
  committees [[label,...]] · briefs [{committee, labels, miniTally, text}]
  reviews [str] · verdict (str, required) · factions (str) · anonMap {letter:idx}
  convergence (float) · stanceLabels {letter: label} (overrides default A/B/C names)

  python3 render_report.py --bundle-file b.json --slug sleep-training-senate \
      --raw-title "..." [--out-dir ~/Documents/Local/council-log] [--date YYYY-MM-DD] \
      [--mode Senate] [--tier Tiered] [--native-model "Sonnet 4.6"] \
      [--model-ids "openai/gpt-5.5-pro,google/gemini-3.1-pro-preview,..."]
"""
import argparse
import datetime
import html
import json
import re
from pathlib import Path

KIND_ORDER = {"model": 0, "style": 1, "figure": 2}
# (display label, css-slug) — colors live in the template stylesheet, not inline
KIND_BADGE = {"figure": ("Figure", "figure"), "style": ("Lens", "lens"), "model": ("Model", "model")}
# Fallback A/B/C labels ONLY. What A/B/C actually mean is question-specific —
# every run should pass scenario labels via bundle["stanceLabels"] (e.g.
# {"A": "Relocate", "B": "Stay put"}) naming THIS question's ballot options; those
# override these per render. These defaults are a last resort, not a universal map.
STANCE_LBL = {"A": "Hold course", "B": "Gentle foundations", "C": "Structured", "ABSTAIN": "Abstain"}
VOTE_ORDER = ["A", "B", "C", "ABSTAIN"]

# Only OUR template placeholders get cleared if left unfilled — never a stray
# {{snake_case}} that legitimately appears inside advisor/verdict text.
_KNOWN_PLACEHOLDER = re.compile(
    r"\{\{(?:slug|mode|timestamp|question_raw|question_framed|mode_banner|diversity_scorecard|"
    r"senate_vote|senate_factions|verdict_one_thing|verdict_recommendation|verdict_agrees|"
    r"verdict_clashes|verdict_blindspots|verdict_kill_criteria|verdict_unknowns|committee_briefs|"
    r"advisor_cards|review_cards|anonymization_map|advisor_pack)\}\}")


# ───────────────────────── tiny markdown -> html ─────────────────────────
def md_inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def md_block(text):
    """Convert a markdown block (paragraphs, -, 1. lists) to html."""
    if not text:
        return ""
    lines = text.strip().split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+(.*)", lines[i]):
                items.append(md_inline(re.match(r"^\s*[-*]\s+(.*)", lines[i]).group(1)))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
        elif re.match(r"^\s*\d+[.)]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+(.*)", lines[i]):
                items.append(md_inline(re.match(r"^\s*\d+[.)]\s+(.*)", lines[i]).group(1)))
                i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>")
        else:
            para = [ln]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^\s*([-*]|\d+[.)])\s+", lines[i]):
                para.append(lines[i].rstrip())
                i += 1
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def split_sections(v):
    """Split a `## header` verdict into {lowercased-header: body}."""
    secs, cur, buf = {}, None, []
    for ln in (v or "").split("\n"):
        h = re.match(r"^\s*#{1,3}\s+(.*)", ln)
        if h:
            if cur is not None:
                secs[cur] = "\n".join(buf).strip()
            cur = h.group(1).strip().lower().replace("’", "'")
            buf = []
        else:
            buf.append(ln)
    if cur is not None:
        secs[cur] = "\n".join(buf).strip()
    return secs


def _sec(secs, *keys, default=""):
    # exact header match first (avoids "agree" matching "disagrees"), then substring
    for k in keys:
        if k in secs:
            return secs[k]
    for k in keys:
        for have in secs:
            if k in have:
                return secs[have]
    return default


def _sorted_members(members):
    return sorted(members, key=lambda m: (KIND_ORDER.get(m.get("kind"), 9), m.get("label", "")))


# ───────────────────────── block builders ─────────────────────────
def _vote_block(tally, vote_prose="", stance_lbl=STANCE_LBL):
    if not tally or not tally.get("total"):
        return ""
    c = tally["counts"]
    cb = tally.get("confidence_by_stance", {})
    seg = "".join(
        f'<span class="vote-seg vote--{k}" style="flex:{c.get(k, 0)}" title="{k}: {c.get(k, 0)}"></span>'
        for k in VOTE_ORDER if c.get(k, 0))
    rows = "".join(
        f'<li><span class="vote-dot vote--{k}"></span>'
        f'<span class="vote-key">{k}</span>'
        f'<span class="vote-lbl">{stance_lbl.get(k, k)}</span>'
        f'<span class="vote-tally">{c.get(k, 0)}'
        f'{("<span class=\"conf\">conf " + html.escape(str(cb.get(k))) + "</span>") if cb.get(k) else ""}'
        f'</span></li>'
        for k in VOTE_ORDER)
    lead = tally.get("leader")
    lead = html.escape("/".join(lead) if isinstance(lead, list) else str(lead))
    total = html.escape(str(tally["total"]))
    return (f'<div class="vote-card">'
            f'<div class="vote-head"><h3>The Vote</h3>'
            f'<span class="vote-meta">{total} seats &middot; leader {lead}</span></div>'
            f'<div class="vote-bar">{seg}</div>'
            f'<ul class="vote-legend">{rows}</ul>'
            f'{md_block(vote_prose)}</div>')


def _faction_block(factionmap_txt, factions_raw):
    body = factionmap_txt or factions_raw
    if not body:
        return ""
    return (f'<h2>The Faction Map</h2>\n'
            f'<div class="verdict-section verdict-section--factions">{md_block(body)}</div>')


def _brief_cards(briefs):
    if not briefs:
        return ""
    cards = []
    for b in briefs:
        labs = html.escape(", ".join(b.get("labels", [])))
        cards.append(
            f'<details class="advisor-card"><summary>'
            f'<span class="advisor-name">Committee {b.get("committee", 0) + 1}</span>'
            f'<span class="advisor-headline">{html.escape(b.get("miniTally", ""))} &middot; {labs}</span>'
            f'</summary><div class="advisor-body">{md_block(b.get("text", ""))}</div></details>')
    return '<h2>Committee Briefs</h2><div class="advisor-grid">' + "\n".join(cards) + "</div>"


def _advisor_cards(members, stance_lbl=STANCE_LBL):
    cards = []
    for m in _sorted_members(members):
        knd, slug = KIND_BADGE.get(m.get("kind"), ("?", "x"))
        if m.get("analysis"):
            body = md_block(m["analysis"])
        else:
            body = (f'<p><em>Ballot only.</em> Load-bearing reason: '
                    f'{html.escape(m.get("reason") or "—")}</p>')
        st = html.escape(m.get("stance") or "?")
        conf = m.get("confidence")
        conf_html = f"<small>{html.escape(str(conf))}</small>" if conf else ""
        title = (stance_lbl.get(m.get("stance"), m.get("stance") or "?")
                 + (f", confidence {conf}" if conf else ""))
        headline = html.escape((m.get("reason") or "").strip())
        cards.append(
            f'<details class="advisor-card"><summary>'
            f'<span class="kind kind--{slug}">{knd}</span>'
            f'<span class="advisor-name">{html.escape(m.get("label", "?"))}</span>'
            f'<span class="stance stance--{st}" title="{html.escape(title)}">{st}{conf_html}</span>'
            f'<span class="advisor-headline">{headline}</span>'
            f'</summary><div class="advisor-body">{body}</div></details>')
    return "\n".join(cards)


def _review_cards(reviews):
    out = []
    for i, r in enumerate(reviews or []):
        first = html.escape((r.strip().split("\n")[0])[:90])
        out.append(
            f'<details class="review-card"><summary><span class="advisor-name">Reviewer {i + 1}</span>'
            f'<span class="advisor-headline">{first}…</span></summary>'
            f'<div class="review-body">{md_block(r)}</div></details>')
    return "\n".join(out)


def _scorecard(members, tally, conv):
    c = (tally or {}).get("counts", {})
    nf = sum(1 for m in members if m.get("kind") == "figure")
    ns = sum(1 for m in members if m.get("kind") == "style")
    nm = sum(1 for m in members if m.get("kind") == "model")
    lead = (tally or {}).get("leader")
    lead = html.escape("/".join(lead) if isinstance(lead, list) else str(lead or "—"))
    total = html.escape(str((tally or {}).get("total", len(members))))
    return (
        '<div class="scorecard">'
        f'<div class="metric"><div class="v">{total}</div><div class="k">Seats voting</div></div>'
        f'<div class="metric"><div class="v">{nf}·{ns}·{nm}</div><div class="k">Figures · Lenses · Models</div></div>'
        f'<div class="metric"><div class="v">{c.get("A", 0)}·{c.get("B", 0)}·{c.get("C", 0)}</div><div class="k">Vote A · B · C</div></div>'
        f'<div class="metric"><div class="v">{lead}</div><div class="k">Leading option</div></div>'
        f'<div class="metric"><div class="v">{int(round((conv or 0) * 100))}%</div><div class="k">Top-option share</div></div>'
        '</div>')


def _banner(mode, tier, members, native_model, model_ids):
    nf = sum(1 for m in members if m.get("kind") == "figure")
    ns = sum(1 for m in members if m.get("kind") == "style")
    nm = sum(1 for m in members if m.get("kind") == "model")
    ids = model_ids or [m["label"] for m in members if m.get("kind") == "model"]
    ids_code = f'<code>{html.escape(" · ".join(ids))}</code>' if ids else ""
    if mode.lower() == "senate":
        return (f'<div class="mode-banner"><strong>SENATE &middot; {html.escape(tier)}</strong>'
                f'<span>{len(members)} seats: {nf} figures + {ns} lenses '
                f'(native, {html.escape(native_model)}) + {nm} real model seats</span>'
                f'{ids_code}'
                f'<span>Clerk / Whips / Reviewers / Chairman on Opus, max effort</span></div>')
    return (f'<div class="mode-banner"><strong>{html.escape(mode)}</strong>'
            f'<span>{len(members)} advisors</span>{ids_code}</div>')


# ───────────────────────── public API ─────────────────────────
def build_report(bundle, *, template, slug, date, raw_title,
                 mode="Senate", tier="Tiered", native_model="Sonnet 4.6", model_ids=None,
                 timestamp=None):
    """Return {'html': ..., 'transcript': ...} for the given bundle."""
    members = bundle.get("members", [])
    tally = bundle.get("tally", {})
    committees = bundle.get("committees") or []
    briefs = bundle.get("briefs") or []
    reviews = bundle.get("reviews") or []
    verdict = bundle.get("verdict", "")
    factions_raw = bundle.get("factions", "")
    framed = bundle.get("framed", "")
    anon = bundle.get("anonMap", {})
    conv = bundle.get("convergence", 0)
    ts = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    stance_lbl = {**STANCE_LBL, **(bundle.get("stanceLabels") or {})}

    S = split_sections(verdict)
    senate_vote = _vote_block(tally, _sec(S, "the vote"), stance_lbl) if committees else ""
    senate_factions = _faction_block(_sec(S, "faction map"), factions_raw) if committees else ""
    committee_briefs = _brief_cards(briefs)

    one_thing = re.sub(r"\s+", " ", _sec(S, "one thing")).strip()
    anon_str = ", ".join(f"{k}=Committee {v + 1}" for k, v in sorted(anon.items()))

    repl = {
        "{{slug}}": slug, "{{mode}}": mode, "{{timestamp}}": ts,
        "{{question_raw}}": html.escape(raw_title),
        "{{question_framed}}": html.escape(framed),
        "{{mode_banner}}": _banner(mode, tier, members, native_model, model_ids),
        "{{diversity_scorecard}}": _scorecard(members, tally, conv),
        "{{senate_vote}}": senate_vote,
        "{{senate_factions}}": senate_factions,
        "{{verdict_one_thing}}": md_inline(one_thing) or "See the recommendation.",
        "{{verdict_recommendation}}": md_block(_sec(S, "recommendation")),
        "{{verdict_agrees}}": md_block(_sec(S, "where the council agrees")),
        "{{verdict_clashes}}": md_block(_sec(S, "where the council clashes")),
        "{{verdict_blindspots}}": md_block(_sec(S, "blind spot")),
        "{{verdict_kill_criteria}}": md_block(_sec(S, "kill criteria")),
        "{{verdict_unknowns}}": md_block(_sec(S, "council doesn't know", "doesn't know", "does not know")),
        "{{committee_briefs}}": committee_briefs,
        "{{advisor_cards}}": _advisor_cards(members, stance_lbl),
        "{{review_cards}}": _review_cards(reviews),
        "{{anonymization_map}}": html.escape(anon_str),
        # legacy template-comment placeholders (kept fillable for safety)
        "{{advisor_pack}}": mode,
    }
    # strip the leading template instruction comment, then fill
    out = re.sub(r"^\s*<!--.*?-->\s*", "", template, count=1, flags=re.S)
    for k, v in repl.items():
        out = out.replace(k, v)
    out = _KNOWN_PLACEHOLDER.sub("", out)  # clear only OUR leftover placeholders, never injected {{...}}

    transcript = _build_transcript(bundle, slug=slug, date=date, ts=ts, mode=mode, tier=tier,
                                    members=members, committees=committees, briefs=briefs,
                                    reviews=reviews, verdict=verdict, factions_raw=factions_raw,
                                    framed=framed, tally=tally, anon=anon, conv=conv, model_ids=model_ids)
    return {"html": out, "transcript": transcript}


def _ballot_table(members):
    rows = ["| Seat | Kind | Vote | Conf | Load-bearing reason |", "|---|---|---|---|---|"]
    for m in _sorted_members(members):
        rows.append(f'| {m.get("label", "?")} | {m.get("kind", "?")} | {m.get("stance", "?")} '
                    f'| {m.get("confidence") or "–"} | {(m.get("reason") or "").replace("|", "/")} |')
    return "\n".join(rows)


def _build_transcript(bundle, *, slug, date, ts, mode, tier, members, committees, briefs,
                      reviews, verdict, factions_raw, framed, tally, anon, conv, model_ids):
    nf = sum(1 for m in members if m.get("kind") == "figure")
    ns = sum(1 for m in members if m.get("kind") == "style")
    nm = sum(1 for m in members if m.get("kind") == "model")
    t = [f"# Council Transcript — {slug}\n",
         f"**Date:** {ts}  ·  **Mode:** {mode} ({tier})  ·  **Seats:** {len(members)}\n",
         f"## Framed Question\n\n```\n{framed}\n```\n",
         f"## The Vote\n\n{bundle.get('tallyStr', '')}\n\n### Ballots\n\n{_ballot_table(members)}\n"]
    if committees:
        t.append("## Committees\n\n" + "\n".join(
            f"- **Committee {i + 1}:** {', '.join(c)}" for i, c in enumerate(committees)) + "\n")
    if factions_raw:
        t.append(f"## Clerk — Factions\n\n{factions_raw}\n")
    for b in briefs:
        t.append(f"## Committee {b.get('committee', 0) + 1} Brief — {b.get('miniTally', '')}\n\n"
                 f"_Members: {', '.join(b.get('labels', []))}_\n\n{b.get('text', '')}\n")
    for i, r in enumerate(reviews):
        t.append(f"## Brief Peer Review {i + 1}\n\n{r}\n")
    t.append(f"## Chairman Verdict\n\n{verdict}\n")
    if any(m.get("analysis") for m in members):
        t.append("## Full Advisor Responses\n")
        for m in _sorted_members(members):
            if m.get("analysis"):
                t.append(f"### {m.get('label')} ({m.get('kind')}) — Option {m.get('stance')} "
                         f"(conf {m.get('confidence') or '–'})\n\n{m['analysis']}\n\n"
                         f"_Reason: {m.get('reason') or '—'}_\n")
    meta = {
        "schema_version": 1, "mode": mode.lower(), "tier_strategy": tier,
        "panel": {"figures": nf, "styles": ns, "models": nm, "total": len(members)},
        "model_seats": model_ids or [m["label"] for m in members if m.get("kind") == "model"],
        "tally": tally, "committee_map": committees, "anonymization_map": anon, "convergence": conv,
    }
    t.append("## Metadata\n\n```yaml\n" + json.dumps(meta, indent=2) + "\n```\n")
    return "\n".join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-file", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--raw-title", required=True, help="the user's question, for the report H1")
    ap.add_argument("--template", default=str(Path(__file__).resolve().parent.parent / "report-template.html"))
    ap.add_argument("--out-dir", default=str(Path.home() / "Documents" / "Local" / "council-log"))
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--mode", default="Senate")
    ap.add_argument("--tier", default="Tiered")
    ap.add_argument("--native-model", default="Sonnet 4.6")
    ap.add_argument("--model-ids", default="", help="comma-separated OpenRouter model ids for the banner")
    args = ap.parse_args()

    bundle = json.loads(Path(args.bundle_file).read_text())
    model_ids = [s.strip() for s in args.model_ids.split(",") if s.strip()] or None
    out = build_report(bundle, template=Path(args.template).read_text(), slug=args.slug,
                       date=args.date, raw_title=args.raw_title, mode=args.mode, tier=args.tier,
                       native_model=args.native_model, model_ids=model_ids)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"council-{args.date}-{args.slug}.html"
    trans_path = out_dir / f"council-{args.date}-{args.slug}-transcript.md"
    html_path.write_text(out["html"])
    trans_path.write_text(out["transcript"])
    print(f"HTML: {html_path}")
    print(f"TRANSCRIPT: {trans_path}")


if __name__ == "__main__":
    main()
