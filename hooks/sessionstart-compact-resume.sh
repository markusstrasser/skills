#!/usr/bin/env bash
# sessionstart-compact-resume.sh — SessionStart(matcher:compact) hook.
# Gov-ID: hook:compact-resume
# goal: after auto-compaction the turn stops and waits for a human "continue"; an unattended /loop stalls
# verifier: null
# blast_radius: shared
#
# Fires only on the post-compaction SessionStart (source="compact"). Injects a
# resume directive so the agent picks the work back up from checkpoint.md WITHOUT
# waiting for the user to type "continue" — closing the one open half of the
# compaction flow (PreCompact already auto-writes checkpoint.md). Pairs with the
# global CLAUDE.md post-compaction rule (read checkpoint, verify claimed commits).
# Advisory: emits context, never blocks.

trap 'exit 0' ERR

if [ "${CODEX_HOOK_COMPAT_SMOKE:-0}" = "1" ] || [ "${CLAUDE_HOOK_SMOKE:-0}" = "1" ]; then
  exit 0
fi

INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"

read -r SOURCE CWD <<<"$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    d = json.load(sys.stdin) or {}
    print(d.get("source",""), d.get("cwd",""))
except Exception:
    print("", "")' 2>/dev/null)"

# Only act on the post-compaction start. The settings matcher should already scope
# this to "compact"; this is a defensive second check so a no-matcher wiring is safe.
[ "$SOURCE" = "compact" ] || exit 0

CKPT=""
[ -n "$CWD" ] && [ -f "$CWD/.claude/checkpoint.md" ] && CKPT=" A fresh .claude/checkpoint.md was written by the PreCompact hook — read it first."

MSG="Context was just auto-compacted mid-session.${CKPT} Resume the work in progress automatically — do NOT wait for the user to say \"continue\". First verify reality against the compaction summary: run \`git log --oneline -10\` and confirm any work the summary claims as done actually landed (compaction summaries hallucinate completed commits). Then continue from the checkpoint's Pending Tasks. If a /loop is active, proceed with the current tick."

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' \
  "$(printf '%s' "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"

exit 0
