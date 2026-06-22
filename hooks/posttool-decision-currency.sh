#!/bin/bash
# PostToolUse:Read — decision/ADR currency WHITELIST (advisory injection). GLOBAL.
#
# THE GENERAL PREVENTION: fires whenever an agent reads ANY decision/ADR that is
# NOT current — warning it not to execute that decision as ratified without
# confirming it's the CURRENT decision on the spine. Whitelist semantics: only
# known-current statuses are silent.
#
# Non-current = status ∉ {accepted,active,current,implemented,done,ratified}
#   OR the body carries an appended supersession marker (the producer-stamp's
#   `Superseded-by`/`Superseded-in-effect` blockquote) even if status reads accepted
#   — closes the accepted-then-superseded gap while honoring append-only (we never
#   rewrite the status line; supersession is a new appended entry).
#
# Keys on EXISTING signals (YAML `status:` / prose `**Status:**` / appended marker)
# — NO edge-graph, NO parser-migration; works on frontmatter-less ADRs (substrate).
# Advisory only (additionalContext, never exit 2): a hard block / fail-closed is the
# PROMOTION target after measuring, not the launch posture.
#
# Once per (session,file). Decision:
# agent-infra/decisions/2026-06-21-decision-currency-whitelist.md
set -euo pipefail
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)
[ -z "$FILE" ] && exit 0
case "$FILE" in
  */decisions/*.md|*/docs/decisions/*.md) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0
case "${FILE##*/}" in .template.md|README.md|index.md|REFRAMINGS.md|deferred-and-open.md|glossary.md) exit 0 ;; esac

STATUS=$(awk '
  /^---[[:space:]]*$/ { fm = !fm; next }
  fm && tolower($0) ~ /^status:/ { sub(/^[Ss]tatus:[[:space:]]*/, ""); print tolower($0); exit }
' "$FILE" 2>/dev/null || true)
if [ -z "$STATUS" ]; then
  STATUS=$(grep -m1 -oiE '\*\*status:\*\*[[:space:]]*[a-z-]+' "$FILE" 2>/dev/null \
    | sed -E 's/.*\*\*[Ss]tatus:\*\*[[:space:]]*//' | tr '[:upper:]' '[:lower:]' || true)
fi
STATUS=$(printf '%s' "$STATUS" | tr -d '`*. ' | tr -cd '[:alnum:]-')

# Appended supersession marker (producer-stamp blockquote) → non-current even if accepted.
MARKED=""
grep -qiE 'superseded[ -](by|in-effect)' "$FILE" 2>/dev/null && MARKED="superseded"

REASON=""
if [ -n "$MARKED" ]; then
  REASON="superseded"
else
  [ -z "$STATUS" ] && exit 0
  case "$STATUS" in
    accepted|active|current|implemented|done|ratified) exit 0 ;;
  esac
  REASON="$STATUS"
fi

TRACKER="/tmp/claude-decision-currency-${PPID}"
grep -qxF "$FILE" "$TRACKER" 2>/dev/null && exit 0
printf '%s\n' "$FILE" >> "$TRACKER"

base="${FILE##*/}"
printf '{"additionalContext": "⚠ Decision currency: %s is %s (not accepted/current). Read/discuss freely, but do NOT execute its plan as a ratified decision without confirming it is the CURRENT decision on this spine — check for a superseding ADR or a REFRAMINGS entry. (agent-infra/decisions/2026-06-21-decision-currency-whitelist.md)"}\n' "$base" "$REASON"
exit 0
