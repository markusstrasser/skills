#!/usr/bin/env bash
# pretool-cost-guard.sh — Guard against expensive API calls based on daily spend.
# PreToolUse:Bash hook. Warns at $50/day, blocks at $100/day.
# Reads cumulative spend from ~/.claude/session-receipts.jsonl.

trap 'exit 0' ERR
INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('command',''))
except: sys.exit(0)
" 2>/dev/null)
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
    if r.get('ts','').startswith('$TODAY'): total+=float(r.get('cost_usd',0))
  except: pass
print(f'{total:.2f}')
" 2>/dev/null)
[ -z "$SPEND" ] && exit 0

TRIGGER="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
SPEND_INT=${SPEND%.*}

if [ "$SPEND_INT" -ge 100 ] 2>/dev/null; then
    "$TRIGGER" "cost-guard" "block" "daily_spend=\$$SPEND cmd=$(echo "$CMD" | head -c 80)" 2>/dev/null || true
    cat <<EOF
{"decision":"block","reason":"Daily API spend \$$SPEND exceeds \$100 limit. Defer non-essential API calls."}
EOF
    exit 2
elif [ "$SPEND_INT" -ge 50 ] 2>/dev/null; then
    "$TRIGGER" "cost-guard" "warn" "daily_spend=\$$SPEND cmd=$(echo "$CMD" | head -c 80)" 2>/dev/null || true
    cat <<EOF
{"decision":"allow","additionalContext":"Cost warning: daily spend at \$$SPEND (limit: \$100). Consider batching or deferring API calls."}
EOF
    exit 0
fi

exit 0
