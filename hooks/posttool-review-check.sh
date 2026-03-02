#!/usr/bin/env bash
# posttool-review-check.sh — Detect failed cross-model reviews (llmx errors).
# PostToolUse:Bash hook. Checks bash output for model failure patterns.
# Injects additionalContext warning so agent knows review is single-model.
#
# State: /tmp/claude-review-failures-$PPID (failure count per session)
# Fail open: errors → exit 0.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract tool output from hook JSON
OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("tool_result", ""))
except Exception:
    print("")
' 2>/dev/null)

[ -z "$OUTPUT" ] && exit 0

# Check if output contains llmx/model failure patterns
# Match: llmx errors, API failures, model unavailable, 503s, rate limits
if ! echo "$OUTPUT" | grep -qiE 'llmx|model.*(fail|error|unavail|timeout)|503|rate.?limit|gemini.*(error|fail)|gpt.*(error|fail)|APIError|ServiceUnavailable'; then
    exit 0
fi

# Also check that this was actually a review-related command (not random API error)
if ! echo "$OUTPUT" | grep -qiE 'llmx|review|model-review|cross.?model'; then
    exit 0
fi

STATE="/tmp/claude-review-failures-${PPID:-0}"

COUNT=0
[ -f "$STATE" ] && COUNT=$(cat "$STATE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE"

if [ "$COUNT" -ge 2 ]; then
    echo "{\"additionalContext\": \"REVIEW CIRCUIT BREAKER: $COUNT cross-model reviewer failures this session. Reviews are effectively single-model — same-model review is a martingale (no adversarial pressure). Options: (1) retry with different model, (2) explicitly note 'single-model review only' in output, (3) defer review to next session.\"}"
else
    echo "{\"additionalContext\": \"REVIEW WARNING: Cross-model reviewer failed. This review is single-model only — no adversarial pressure. Acknowledge this limitation before proceeding with the review output.\"}"
fi

exit 0
