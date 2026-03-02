#!/usr/bin/env bash
# subagent-source-check-stop.sh — Check researcher output for source citations.
# Stop command hook for researcher agent. Advisory (would-block) until measured.
#
# Promote to blocking only after ≤10% trigger rate over 14 days.

trap 'exit 0' ERR

INPUT=$(cat)

eval "$(echo "$INPUT" | python3 -c '
import sys, json, time, os

try:
    d = json.load(sys.stdin)
    msg = d.get("last_assistant_message", "")
    msg_len = len(msg)
    msg_trunc = msg[:3000].replace("'\''", "'\''\\'\'''\''")
    print(f"MSG='\''{ msg_trunc }'\''")
    print(f"MSG_LEN={ msg_len }")
except Exception:
    print("MSG='\'''\''")
    print("MSG_LEN=0")
' 2>/dev/null)"

# Skip short outputs
[ "${MSG_LEN:-0}" -lt 200 ] && exit 0

# Check for factual claim indicators
HAS_CLAIMS=false
if echo "$MSG" | grep -qE '\$[0-9]|[0-9]+%|[0-9]{4}-[0-9]{2}|billion|million|trillion|according to|study|paper|found that|reported|measured|evidence|benchmark|showed'; then
    HAS_CLAIMS=true
fi

[ "$HAS_CLAIMS" = "false" ] && exit 0

# Check for source tags
HAS_TAGS=false
if echo "$MSG" | grep -qE '\[SOURCE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]|\[Exa\]|\[S2\]|\[PubMed\]'; then
    HAS_TAGS=true
fi

# Log would-block event regardless of outcome
python3 -c '
import json, time, os
entry = json.dumps({
    "event": "researcher_stop_check",
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "has_claims": '"$([ "$HAS_CLAIMS" = "true" ] && echo "true" || echo "false")"',
    "has_tags": '"$([ "$HAS_TAGS" = "true" ] && echo "true" || echo "false")"',
    "would_block": '"$([ "$HAS_CLAIMS" = "true" ] && [ "$HAS_TAGS" = "false" ] && echo "true" || echo "false")"',
    "output_len": '"${MSG_LEN:-0}"'
})
logfile = os.path.expanduser("~/.claude/subagent-log.jsonl")
with open(logfile, "a") as f:
    f.write(entry + "\n")
' 2>/dev/null

# Advisory warning (not blocking)
if [ "$HAS_TAGS" = "false" ]; then
    echo "{\"additionalContext\": \"RESEARCHER CITATION: Output contains factual claims without source tags ([SOURCE:], [DATA], [A2], [Exa], [S2], etc.). Add provenance before incorporating into analysis. This is advisory — will promote to blocking after 14-day measurement if trigger rate ≤10%.\"}"
fi

exit 0
