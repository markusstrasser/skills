#!/bin/bash
# PostToolUse:Write|Edit — decision/ADR supersession AUTO-BACK-STAMP. GLOBAL.
#
# Closes the forward-only gap at the SOURCE: when a new/edited ADR declares it
# supersedes/retires/reverses-premise of another, append a backward marker to the
# TARGET so supersession ALWAYS self-marks (no more "0003 still reads PROPOSED while
# 0011 reversed it"). The read-gate (posttool-decision-currency.sh) then fires on the
# target even when its own status reads accepted.
#
# FLIP verbs only (the verb ruling): supersedes | retires | reverses[-_ ]premise.
# NOT unifies/merged_from/subsumes/concretizes/extends (consolidation/refinement ≠ kill).
# Append-only (never rewrites the target's status line — a new appended entry, per the
# "mark stale, never delete" principle). Idempotent (keyed on the marker text). Targets
# resolved ONLY within the same decisions dir (never cross-repo). Bash append, so it
# does NOT re-trigger Write-tool hooks (no loop).
#
# Decision: agent-infra/decisions/2026-06-21-decision-currency-whitelist.md (Phase 2)
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

DIR=$(dirname "$FILE")
SELF="${FILE##*/}"; SELF_STEM="${SELF%.md}"
# This ADR's label for the marker: frontmatter id, else filename stem.
SELF_ID=$(awk '
  /^---[[:space:]]*$/ { fm = !fm; next }
  fm && /^id:/ { sub(/^id:[[:space:]]*/, ""); gsub(/["\x27]/,""); print; exit }
' "$FILE" 2>/dev/null || true)
[ -z "$SELF_ID" ] && SELF_ID="$SELF_STEM"

# Collect FLIP-verb supersession targets from BOTH forms:
#  (1) YAML relations:  - type: supersedes|retires|reverses_premise / target: X
#  (2) prose headers:   **Supersedes:** [[X]] / **Retires:** [[X]] / **Reverses-premise:** [[X]]
# (1) YAML relations: a flip `type:` line followed by its `target:`.
yaml_targets=$(awk '
  /^[[:space:]]*-[[:space:]]*type:[[:space:]]*(supersedes|retires|reverses[_-]premise)/ { armed=1; next }
  armed && /target:/ { sub(/.*target:[[:space:]]*/,""); gsub(/["\x27]/,""); print; armed=0; next }
  armed && !/^[[:space:]]/ { armed=0 }
' "$FILE" 2>/dev/null || true)
# (2) Prose flip headers → every [[target]] on the matching line.
prose_lines=$(grep -ioE '\*\*(supersedes|retires|reverses[ _-]premise)[^*]*\*\*[^*]*' "$FILE" 2>/dev/null || true)
prose_targets=$(printf '%s\n' "$prose_lines" | grep -oE '\[\[[^]]+\]\]' 2>/dev/null | tr -d '[]' || true)
targets=$(printf '%s\n%s\n' "$yaml_targets" "$prose_targets" | sed 's/[[:space:]]*$//' | grep -v '^[[:space:]]*$' | sort -u || true)
[ -z "$targets" ] && exit 0

DATE=$(date +%F)
stamped=""
while IFS= read -r tgt; do
  [ -z "$tgt" ] && continue
  # Resolve target within THIS dir: exact stem, else unique prefix glob, else id match.
  tf=""
  if [ -f "$DIR/$tgt.md" ]; then tf="$DIR/$tgt.md"
  else
    matches=$(ls "$DIR/$tgt"*.md 2>/dev/null || true)
    n=$(printf '%s' "$matches" | grep -c . || true)
    if [ "$n" = "1" ]; then tf="$matches"; fi
  fi
  [ -z "$tf" ] && { stamped="$stamped\n  (unresolved target: $tgt)"; continue; }
  [ "$tf" = "$FILE" ] && continue                       # never self-stamp
  # Idempotent: already stamped by THIS adr?
  grep -qF "Superseded-by [[$SELF_ID]]" "$tf" 2>/dev/null && continue
  printf '\n> **⚠ Superseded-by [[%s]] (%s):** a later decision supersedes/reverses this one. This ADR is NOT a current direction — see [[%s]] and REFRAMINGS. (auto-stamped: posttool-decision-backstamp)\n' "$SELF_ID" "$DATE" "$SELF_ID" >> "$tf"
  stamped="$stamped\n  ${tf##*/} ← Superseded-by [[$SELF_ID]]"
done <<< "$targets"

[ -z "$stamped" ] && exit 0
printf '{"additionalContext": "🔗 Auto-back-stamp (supersession self-marks the target):%s"}\n' "$stamped"
exit 0
