#!/usr/bin/env bash
# subagent-source-check-stop.sh — Enforce researcher output quality.
# Stop command hook for researcher agent.
# - Blocks empty/stub output (exit 2, one retry via stop_hook_active)
# - Blocks substantial output with claims but no source tags (exit 2)
# - stop_hook_active prevents infinite loops.

trap 'exit 0' ERR

INPUT=$(cat)

eval "$(echo "$INPUT" | python3 -c '
import sys, json

try:
    d = json.load(sys.stdin)
    msg = d.get("last_assistant_message", "")
    msg_len = len(msg)
    stop_active = "true" if d.get("stop_hook_active") else "false"
    msg_trunc = msg[:3000].replace("'\''", "'\''\\'\'''\''")
    print(f"MSG='\''{ msg_trunc }'\''")
    print(f"MSG_LEN={ msg_len }")
    print(f"STOP_ACTIVE={ stop_active }")
except Exception:
    print("MSG='\'''\''")
    print("MSG_LEN=0")
    print("STOP_ACTIVE=false")
' 2>/dev/null)"

# Prevent infinite loop — second stop attempt always succeeds
[ "$STOP_ACTIVE" = "true" ] && exit 0

# Block empty output (<200 chars)
if [ "${MSG_LEN:-0}" -lt 200 ]; then
    echo "No research output. Write what you found, even if incomplete. Tag uncertainties with [UNVERIFIED]."
    exit 2
fi

# Detect claims and source tags
HAS_CLAIMS=false
if echo "$MSG" | grep -qE '\$[0-9]|[0-9]+%|[0-9]{4}-[0-9]{2}|billion|million|trillion|according to|study|paper|found that|reported|measured|evidence|benchmark|showed'; then
    HAS_CLAIMS=true
fi

HAS_TAGS=false
if echo "$MSG" | grep -qE '\[SOURCE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]|\[Exa\]|\[S2\]|\[PubMed\]'; then
    HAS_TAGS=true
fi

# Determine blocking decision
BLOCK_REASON=""
if [ "${MSG_LEN:-0}" -lt 500 ] && [ "$HAS_CLAIMS" = "true" ]; then
    BLOCK_REASON="stub_with_claims"
elif [ "${MSG_LEN:-0}" -ge 2000 ] && [ "$HAS_CLAIMS" = "true" ] && [ "$HAS_TAGS" = "false" ]; then
    BLOCK_REASON="unsourced_substantial"
fi

# Log check event
CLAIMS_VAL="$HAS_CLAIMS" TAGS_VAL="$HAS_TAGS" MLEN="${MSG_LEN:-0}" BREASON="$BLOCK_REASON" python3 -c '
import json, time, os
has_claims = os.environ.get("CLAIMS_VAL", "false") == "true"
has_tags = os.environ.get("TAGS_VAL", "false") == "true"
block_reason = os.environ.get("BREASON", "")
entry = json.dumps({
    "event": "researcher_stop_check",
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "has_claims": has_claims,
    "has_tags": has_tags,
    "did_block": bool(block_reason),
    "block_reason": block_reason or None,
    "output_len": int(os.environ.get("MLEN", "0"))
})
logfile = os.path.expanduser("~/.claude/subagent-log.jsonl")
with open(logfile, "a") as f:
    f.write(entry + "\n")
' 2>/dev/null

# Execute blocking
case "$BLOCK_REASON" in
    stub_with_claims)
        echo "Output appears incomplete for research with claims. Write a synthesis with source tags before stopping."
        exit 2
        ;;
    unsourced_substantial)
        echo "Output contains factual claims without source tags. Add [SOURCE:], [DATABASE:], [DATA], [INFERENCE], or [UNVERIFIED] to each major claim before stopping."
        exit 2
        ;;
esac

# Advisory warning for non-blocking cases (claims without tags, 500-2000 chars)
if [ "$HAS_CLAIMS" = "true" ] && [ "$HAS_TAGS" = "false" ]; then
    echo "{\"additionalContext\": \"RESEARCHER CITATION: Output contains factual claims without source tags. Add provenance tags before incorporating into analysis.\"}"
fi

exit 0
