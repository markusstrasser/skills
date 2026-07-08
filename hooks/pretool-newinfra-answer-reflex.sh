#!/bin/sh
# pretool-newinfra-answer-reflex.sh — ADVISORY (never blocks): nudge the answer-reflex
# before an agent builds a NEW standalone infra script inline.
#
# WHY (arc-agi 2026-07-08): built loop/arxiv_watch.py — a full duplicate of
# frontier_scout.scout_arxiv — without running `just answer` / checking existing recipes.
# Same class as the action_census rebuild-endorsement. The inventory-before-dispatch hook
# fires on AGENT dispatch but NOT on inline Write, so the answer-reflex's enforcement had a
# scope hole for interactive/inline builds. This closes it. Registered in arc-agi ONLY.
#
# Fail-safe by construction: any error -> exit 0; only fires on genuinely-new infra scripts
# (loop/scripts/experiments, not tests, not tmp, not an overwrite of an existing file);
# once per 30 min so it can't nag inside one build session. It can NEVER block a Write.
trap 'exit 0' ERR
INPUT=$(cat)
FP=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || echo "")
[ -z "$FP" ] && exit 0

# scope: NEW standalone infra scripts only
case "$FP" in
  */loop/*.py|*/loop/*.sh|*/scripts/*.py|*/scripts/*.sh|*/experiments/*.py|*/experiments/*.sh) : ;;
  *) exit 0 ;;
esac
case "$FP" in *test_*|*_test.*|*/tests/*|*/tmp/*|*conftest*) exit 0 ;; esac
[ -e "$FP" ] && exit 0   # overwrite/Edit of an existing file = not a fresh build

# throttle: once per 30 min
MARK="${CLAUDE_JOB_DIR:-/tmp}/tmp/.answer_reflex_nudge"
NOW=$(date +%s); LAST=$(stat -f %m "$MARK" 2>/dev/null || echo 0)
[ $((NOW - LAST)) -lt 1800 ] && exit 0
mkdir -p "$(dirname "$MARK")" 2>/dev/null || true
: > "$MARK" 2>/dev/null || true

BASE=$(basename "$FP")
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"ANSWER-REFLEX (advisory — new infra script %s): before building, run `just answer \\"<mechanism concept>\\"` and grep existing `just` recipes + loop/ + scripts/ — the mechanism may already exist (2026-07-08: arxiv_watch.py duplicated frontier_scout.scout_arxiv; action_census rebuild-endorsement). Cite what you checked, or note why genuinely net-new."}}\n' "$BASE"
exit 0
