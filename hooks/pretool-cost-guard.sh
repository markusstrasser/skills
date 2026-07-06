#!/usr/bin/env bash
# pretool-cost-guard.sh — Guard against expensive *discretionary API* calls.
# PreToolUse:Bash hook. Warns at $10/day, blocks at $25/day — aligned to the
# constitutional daily cap (agent-infra invariants.md; doctor warn $10/fail $25).
# This is the FOREGROUND-Bash surface guard; the surface-agnostic hard block on
# metered llmx spend lives in llmx spend_guard (fires for bg workers too). Keep
# both — this catches non-llmx metered Bash (modal run, raw curl/openai/anthropic).
# Reads cumulative spend from ~/.claude/session-receipts.jsonl, EXCLUDING
# Claude Code session-telemetry rows (subscription session cost is NOT metered
# API spend — those rows carry `transcript_lines`/`harness_hash` and their
# estimated cost_usd is large and irrelevant to this guard; counting them
# misfired the block at ~$1.9K/day of pure session cost — 2026-06-09).

trap 'exit 0' ERR
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '(if has("tool_input") then (.tool_input // {}) else . end) | .command // ""' 2>/dev/null || true)
[ -z "$CMD" ] && exit 0
echo "$CMD" | grep -qE 'llmx|modal run|curl.*api|python.*openai|python.*anthropic' || exit 0

RECEIPTS="$HOME/.claude/session-receipts.jsonl"
[ -f "$RECEIPTS" ] || exit 0
TODAY=$(date +%Y-%m-%d)
SPEND=$(python3 -c "
import json
total=0.0
for l in open('$RECEIPTS'):
  try:
    r=json.loads(l)
    if not r.get('ts','').startswith('$TODAY'): continue
    # Skip Claude Code session-telemetry receipts (subscription, not API spend).
    if 'transcript_lines' in r or 'harness_hash' in r: continue
    total+=float(r.get('cost_usd',0))
  except: pass
print(f'{total:.2f}')
" 2>/dev/null)
[ -z "$SPEND" ] && exit 0

TRIGGER="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
SPEND_INT=${SPEND%.*}

if [ "$SPEND_INT" -ge 25 ] 2>/dev/null; then
    "$TRIGGER" "cost-guard" "block" "daily_spend=\$$SPEND cmd=$(echo "$CMD" | head -c 80)" 2>/dev/null || true
    cat <<EOF
{"decision":"block","reason":"Daily API spend \$$SPEND exceeds the \$25 constitutional cap. Defer non-essential API calls, or set LLMX_SPEND_OVERRIDE=1 for an intended llmx job / get human approval."}
EOF
    exit 2
elif [ "$SPEND_INT" -ge 10 ] 2>/dev/null; then
    "$TRIGGER" "cost-guard" "warn" "daily_spend=\$$SPEND cmd=$(echo "$CMD" | head -c 80)" 2>/dev/null || true
    cat <<EOF
{"decision":"allow","additionalContext":"Cost warning: daily spend at \$$SPEND (warn at \$10, block at \$25). Consider batching or deferring."}
EOF
    exit 0
fi

exit 0
