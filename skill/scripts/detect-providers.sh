#!/usr/bin/env bash
# Council capability detection (Models / Mixed modes).
# Prints a single JSON object to stdout. Never prints the key itself.
#
# Roster staleness: resolved_at is parsed out of skill/packs/models/roster.md
# (relative to this script's location, not the cwd) and compared against
# "today" to flag a roster that hasn't been re-resolved in >30 days. Override
# "today" for deterministic tests with DETECT_TODAY=YYYY-MM-DD.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROSTER_FILE="${SCRIPT_DIR}/../packs/models/roster.md"

KEYFILE="${HOME}/.claude/.openrouter-key"
key_present=false
if [ -n "${OPENROUTER_API_KEY:-}" ] || { [ -f "$KEYFILE" ] && [ -s "$KEYFILE" ]; }; then
  key_present=true
fi

have() { command -v "$1" >/dev/null 2>&1 && printf true || printf false; }
claude=$(have claude); codex=$(have codex); gemini=$(have gemini); ollama=$(have ollama)

if [ "$key_present" = true ]; then tier=real; else tier=claude-only; fi

# Parse roster resolved_at + compute age/staleness via embedded python3 (a hard
# dependency of this skill). Emits a single-line JSON fragment with just these
# three keys, which we splice into the final object below. Never crashes: a
# missing/unparsable roster yields nulls and roster_stale=false, and the || guard
# below maps ANY python failure (e.g. a non-UTF-8 roster) to the same nulls so a
# single JSON object is always printed.
roster_fields=$(ROSTER_FILE="$ROSTER_FILE" DETECT_TODAY="${DETECT_TODAY:-}" python3 <<'PYEOF'
import datetime
import json
import os
import re

roster_file = os.environ["ROSTER_FILE"]
today_override = os.environ.get("DETECT_TODAY", "").strip()

resolved_at = None
try:
    with open(roster_file, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r'"?resolved_at"?\s*[:=]\s*"?(\d{4}-\d{2}-\d{2})"?', text)
    if m:
        resolved_at = m.group(1)
except OSError:
    resolved_at = None

age_days = None
stale = False
if resolved_at:
    try:
        resolved_date = datetime.date.fromisoformat(resolved_at)
        today = (datetime.date.fromisoformat(today_override)
                 if today_override else datetime.date.today())
        age_days = (today - resolved_date).days
        stale = age_days > 30
    except ValueError:
        resolved_at, age_days, stale = None, None, False

print(json.dumps({
    "roster_resolved_at": resolved_at,
    "roster_age_days": age_days,
    "roster_stale": stale,
})[1:-1])
PYEOF
) || roster_fields='"roster_resolved_at": null, "roster_age_days": null, "roster_stale": false'

cat <<JSON
{"openrouter_key": ${key_present}, "clis": {"claude": ${claude}, "codex": ${codex}, "gemini": ${gemini}, "ollama": ${ollama}}, "claude_models": ["opus", "sonnet", "haiku", "fable"], "tier": "${tier}", ${roster_fields}}
JSON
