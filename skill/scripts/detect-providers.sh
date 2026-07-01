#!/usr/bin/env bash
# Council capability detection (Models / Mixed modes).
# Prints a single JSON object to stdout. Never prints the key itself.
set -euo pipefail

KEYFILE="${HOME}/.claude/.openrouter-key"
key_present=false
if [ -n "${OPENROUTER_API_KEY:-}" ] || { [ -f "$KEYFILE" ] && [ -s "$KEYFILE" ]; }; then
  key_present=true
fi

have() { command -v "$1" >/dev/null 2>&1 && printf true || printf false; }
claude=$(have claude); codex=$(have codex); gemini=$(have gemini); ollama=$(have ollama)

if [ "$key_present" = true ]; then tier=real; else tier=claude-only; fi

cat <<JSON
{"openrouter_key": ${key_present}, "clis": {"claude": ${claude}, "codex": ${codex}, "gemini": ${gemini}, "ollama": ${ollama}}, "claude_models": ["opus", "sonnet", "haiku", "fable"], "tier": "${tier}"}
JSON
