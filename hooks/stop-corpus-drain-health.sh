#!/usr/bin/env bash
# Stop hook — surface corpus drain health at session end.
#
# Fails OPEN — any error (script missing, audit failure, jq absent) is
# silent. The intent is operator awareness, not a blocker.
#
# Reports:
#   - abandoned_total: outbox rows that crossed retry_count >= 3 and
#     need human triage.
#   - drain_seconds_last: per-repo single-sample drain latency. Surfaces
#     when any repo's last drain took > $DRAIN_SLOW_THRESHOLD_SECS
#     (default 10) — slow drain often precedes a real backlog.
#
# Phase C of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.

set -u

# Fail-open: any error means silence.
trap 'exit 0' ERR

THRESHOLD=${DRAIN_SLOW_THRESHOLD_SECS:-10}
AUDIT="$HOME/Projects/agent-infra/scripts/audit_corpus_sync.py"

[[ -x "$(command -v jq)" ]] || exit 0
[[ -x "$(command -v uv)" ]] || exit 0
[[ -f "$AUDIT" ]] || exit 0

# Time-bounded to keep Stop hooks responsive.
OUT=$(cd "$HOME/Projects/agent-infra" && timeout 20 uv run python3 "$AUDIT" --json 2>/dev/null) || exit 0
[[ -n "$OUT" ]] || exit 0

ABANDONED=$(echo "$OUT" | jq -r '[.summary[].abandoned_count // 0] | add // 0' 2>/dev/null) || ABANDONED=0
SLOW=$(echo "$OUT" | jq -r --argjson t "$THRESHOLD" \
    '[.drain[] | select((.drain_seconds_last // 0) > $t) | "\(.flushed) flushed @ \(.drain_seconds_last)s"] | join(", ")' \
    2>/dev/null) || SLOW=""

WARNINGS=()
if [[ "${ABANDONED:-0}" -gt 0 ]]; then
    WARNINGS+=("$ABANDONED abandoned outbox row(s) need triage (status='abandoned' in pending_corpus_attestations)")
fi
if [[ -n "$SLOW" ]]; then
    WARNINGS+=("slow drain (> ${THRESHOLD}s): $SLOW")
fi

if (( ${#WARNINGS[@]} == 0 )); then
    exit 0
fi

echo "corpus drain health:" >&2
for w in "${WARNINGS[@]}"; do
    echo "  ! $w" >&2
done

exit 0
