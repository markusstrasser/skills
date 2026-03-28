#!/usr/bin/env bash
# subagent-epistemic-gate.sh — Check subagent outputs for provenance on factual claims.
# SubagentStop command hook. Advisory only (exit 0 + additionalContext).
#
# Skips code-focused subagents (Explore, Plan) where provenance tags don't apply.
# Checks last_assistant_message for factual claims (numbers, dates, proper nouns)
# without nearby provenance tags.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract agent_type, last_assistant_message, and log completion
eval "$(echo "$INPUT" | python3 -c '
import sys, json, time, os
try:
    d = json.load(sys.stdin)
    agent_type = d.get("agent_type", "")
    agent_id = d.get("agent_id", "")
    session_id = d.get("session_id", "")
    transcript_path = d.get("agent_transcript_path", "")
    msg = d.get("last_assistant_message", "")

    # Compute full length before truncation (R:P4/P12)
    msg_len = len(msg)

    # Log subagent completion to same JSONL as start events
    try:
        entry = json.dumps({
            "event": "subagent_stop",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "agent_type": agent_type,
            "agent_id": agent_id,
            "session_id": session_id,
            "output_len": msg_len,
            "transcript_path": transcript_path
        })
        logfile = os.path.expanduser("~/.claude/subagent-log.jsonl")
        with open(logfile, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass

    # Shell-safe: escape single quotes, truncate for shell use
    agent_type = agent_type.replace("'\''", "'\''\\'\'''\''")
    msg_trunc = msg[:2000].replace("'\''", "'\''\\'\'''\''")
    print(f"AGENT_TYPE='\''{ agent_type }'\''")
    print(f"MSG='\''{ msg_trunc }'\''")
    print(f"MSG_LEN={ msg_len }")
except Exception:
    print("AGENT_TYPE='\'''\''")
    print("MSG='\'''\''")
    print("MSG_LEN=0")
' 2>/dev/null)"

# Skip code-focused subagents where provenance tags are irrelevant
case "$AGENT_TYPE" in
    Explore|Plan|statusline-setup|claude-code-guide|session-analyst)
        exit 0
        ;;
esac

# Short/empty output warning — subagent may have exhausted turns without synthesizing
if [ "$MSG_LEN" -lt 200 ] && [ "$MSG_LEN" -gt 0 ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "epistemic-gate" "warn" "$AGENT_TYPE: short output (${MSG_LEN} chars)" 2>/dev/null || true
    echo "{\"additionalContext\": \"SUBAGENT EMPTY: ${AGENT_TYPE} returned only ${MSG_LEN} chars. This agent likely exhausted turns without synthesizing. Check if it wrote to a file (the data may still be useful). If not, dispatch a recovery agent to read the transcript and extract findings. Do NOT ignore this — empty agents waste tokens AND lose discovered information.\"}"
    exit 0
fi
if [ "$MSG_LEN" -eq 0 ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "epistemic-gate" "warn" "$AGENT_TYPE: zero output" 2>/dev/null || true
    echo "{\"additionalContext\": \"SUBAGENT ZERO OUTPUT: ${AGENT_TYPE} returned nothing. The agent may have crashed or exhausted all turns on tool calls. Check the transcript for recoverable findings.\"}"
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
    ~/Projects/skills/hooks/hook-trigger-log.sh "epistemic-gate" "warn" "$AGENT_TYPE: claims without tags" 2>/dev/null || true
    echo "{\"additionalContext\": \"SUBAGENT PROVENANCE: The $AGENT_TYPE subagent returned factual claims without provenance tags. Before incorporating these claims into your output, verify them or add appropriate tags ([SOURCE:], [SPEC], [TRAINING-DATA], etc.). Unsourced subagent claims compound error across steps.\"}"
fi

# Result-size check — uses MSG_LEN (full length, computed before truncation)
if [ "${MSG_LEN:-0}" -gt 2000 ]; then
    KB=$(( MSG_LEN / 1024 ))
    echo "{\"additionalContext\": \"SUBAGENT SIZE: ${AGENT_TYPE} returned ${KB}KB. Large results defeat context isolation — ask subagents to return conclusions, not raw data.\"}"
fi

exit 0
