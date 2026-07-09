#!/usr/bin/env bash
# pretool-genomics-mcp-routing.sh — advisory routing for Modal/JSON shell workflows
# in genomics. The genomics MCP was retired 2026-06-20 (stale-reader hazard);
# prefer fresh CLI / just recipes.

trap 'exit 0' ERR

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -n "$CMD" ] || exit 0

SESSION_ID=""
for SID_PATH in ".claude/current-session-id" "$HOME/.claude/current-session-id"; do
    if [ -f "$SID_PATH" ]; then
        SESSION_ID=$(tr -d "[:space:]" < "$SID_PATH" 2>/dev/null)
        [ -n "$SESSION_ID" ] && break
    fi
done

TRACKER="/tmp/claude-genomics-mcp-routing-${SESSION_ID:-$PPID}.txt"

seen() {
    local key="$1"
    [ -f "$TRACKER" ] && grep -qxF "$key" "$TRACKER" 2>/dev/null
}

remember() {
    local key="$1"
    touch "$TRACKER"
    grep -qxF "$key" "$TRACKER" 2>/dev/null || printf '%s\n' "$key" >> "$TRACKER"
}

MESSAGES=()
TRIGGERED=()

if echo "$CMD" | grep -qE '(^|[[:space:]])modal[[:space:]]+app[[:space:]]+logs([[:space:]]|$)' && ! seen "modal-logs"; then
    remember "modal-logs"
    MESSAGES+=('Prefer a bounded fresh read: `modal app logs <id> 2>&1 | tail -n 80` (or `uv run python3 scripts/watch_active_apps.py`) — do not hang on an unbounded tail. Genomics MCP retired 2026-06-20.')
    TRIGGERED+=("modal-logs")
fi

if echo "$CMD" | grep -qE '(^|[[:space:]])modal[[:space:]]+volume[[:space:]]+(ls|get|list|cat)([[:space:]]|$)' && ! seen "modal-volume"; then
    remember "modal-volume"
    MESSAGES+=('Volume inspect via fresh CLI (`modal volume ls/get`) is fine; for sample status prefer `just sample-state` / `just sample-doctor` / `just sample-remediation` over ad-hoc volume crawls.')
    TRIGGERED+=("modal-volume")
fi

if echo "$CMD" | grep -q '\.json' && echo "$CMD" | grep -qE '(^|[[:space:]])(jq|cat|sed|head|tail|python|python3)([[:space:]]|$)' && ! seen "json-query"; then
    remember "json-query"
    MESSAGES+=('For pipeline JSON, prefer `just sample-state` / remediation surfaces or a short `jq` against the Modal-backed path — not a long shell parse of a local mirror.')
    TRIGGERED+=("json-query")
fi

# Stale-local-mirror trap: reading a LOCAL results-tree JSON (data/.../results/.../*.json)
# via shell parsing. That tree is authority rank #4 — it diverges from the Modal volume
# across reruns. A 2-month-stale local review_packets.json once produced a false
# "all DL scores null" finding (2026-06-08, feedback_stale_local_review_packets_false_null).
if echo "$CMD" | grep -qE 'data/[^[:space:]"'"'"']*results/[^[:space:]"'"'"']*\.json' \
    && echo "$CMD" | grep -qE '(^|[[:space:]])(jq|cat|sed|head|tail|python|python3)([[:space:]]|$)' \
    && ! seen "local-results-mirror"; then
    remember "local-results-mirror"
    MESSAGES+=('Reading a LOCAL `data/.../results/.../*.json` mirror (authority rank #4) — it DIVERGES from the Modal volume across reruns; a 2-month-stale local review_packets.json caused a false "all DL scores null" finding (2026-06-08). Verify against Modal volume truth (`modal volume get` / `just sample-state`) before treating values as authoritative.')
    TRIGGERED+=("local-results-mirror")
fi

[ "${#MESSAGES[@]}" -gt 0 ] || exit 0

~/Projects/skills/hooks/hook-trigger-log.sh "genomics-mcp-routing" "remind" "$(IFS=,; echo "${TRIGGERED[*]}")" 2>/dev/null || true

CONTEXT=$(printf '%s\n' "${MESSAGES[@]}" | python3 -c '
import json, sys
lines = [line.strip() for line in sys.stdin if line.strip()]
text = "Genomics routing (fresh CLI — genomics MCP retired):\n- " + "\n- ".join(lines)
print(json.dumps(text))
')

printf '{"additionalContext":%s}\n' "$CONTEXT"

exit 0
