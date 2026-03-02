#!/usr/bin/env bash
# subagent-epistemic-gate.sh — Check subagent outputs for provenance on factual claims.
# SubagentStop command hook. Advisory only (exit 0 + additionalContext).
#
# Skips code-focused subagents (Explore, Plan) where provenance tags don't apply.
# Checks last_assistant_message for factual claims (numbers, dates, proper nouns)
# without nearby provenance tags.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract agent_type and last_assistant_message
eval "$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    agent_type = d.get("agent_type", "")
    msg = d.get("last_assistant_message", "")
    # Shell-safe: escape single quotes
    agent_type = agent_type.replace("'\''", "'\''\\'\'''\''")
    msg = msg.replace("'\''", "'\''\\'\'''\''")
    print(f"AGENT_TYPE='\''{ agent_type }'\''")
    print(f"MSG='\''{ msg[:2000] }'\''")  # Cap at 2000 chars
except Exception:
    print("AGENT_TYPE='\'''\''")
    print("MSG='\'''\''")
' 2>/dev/null)"

# Skip code-focused subagents where provenance tags are irrelevant
case "$AGENT_TYPE" in
    Explore|Plan|statusline-setup|claude-code-guide|session-analyst)
        exit 0
        ;;
esac

# Skip short outputs (likely not research-heavy)
if [ ${#MSG} -lt 200 ]; then
    exit 0
fi

# Check for factual claim indicators: dollar amounts, percentages, dates, specific numbers
HAS_CLAIMS=false
if echo "$MSG" | grep -qE '\$[0-9]|[0-9]+%|[0-9]{4}-[0-9]{2}|billion|million|trillion|according to|study|paper|found that|reported|measured'; then
    HAS_CLAIMS=true
fi

[ "$HAS_CLAIMS" = "false" ] && exit 0

# Check for provenance tags
HAS_TAGS=false
if echo "$MSG" | grep -qE '\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]'; then
    HAS_TAGS=true
fi

if [ "$HAS_TAGS" = "false" ]; then
    echo "{\"additionalContext\": \"SUBAGENT PROVENANCE: The $AGENT_TYPE subagent returned factual claims without provenance tags. Before incorporating these claims into your output, verify them or add appropriate tags ([SOURCE:], [SPEC], [TRAINING-DATA], etc.). Unsourced subagent claims compound error across steps.\"}"
fi

exit 0
