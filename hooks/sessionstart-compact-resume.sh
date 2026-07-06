#!/usr/bin/env bash
# sessionstart-compact-resume.sh — SessionStart(matcher:compact) hook.
# Gov-ID: hook:compact-resume
# goal: when a turn DOES resume after compaction, it re-orients correctly instead of stalling/re-asking
# verifier: null
# blast_radius: shared
#
# HONEST SCOPE (Fable-5 review 2026-06-12): SessionStart additionalContext is
# injected into the NEXT turn — it does NOT *create* a turn. If the harness stops
# and waits after auto-compaction, something else (the /loop wakeup, or the human)
# must start that turn; this hook only makes that turn re-orient correctly. It does
# NOT by itself close the "type continue" stall — that depends on /loop self-firing,
# which is still unverified (decisions-pending/2026-06-12-loop-resume-after-autocompact.md).
#
# Fires on source="compact" (covers BOTH auto and manual /compact — there's no
# signal to distinguish them). The message is therefore written to be correct in
# both cases: "continue the in-progress work" is right after a manual /compact too.
# Advisory: emits context, never blocks.

trap 'exit 0' ERR

if [ "${CODEX_HOOK_COMPAT_SMOKE:-0}" = "1" ] || [ "${CLAUDE_HOOK_SMOKE:-0}" = "1" ]; then
  exit 0
fi

INPUT="${CLAUDE_TOOL_INPUT:-$(cat)}"

SOURCE=$(printf '%s' "$INPUT" | jq -r '.source // ""' 2>/dev/null || echo "")
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null || echo "")

# Only act on the post-compaction start. The settings matcher should already scope
# this to "compact"; this is a defensive second check so a no-matcher wiring is safe.
[ "$SOURCE" = "compact" ] || exit 0

SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null || echo "")
if [ -n "$SID" ]; then
  date +%s > "/tmp/claude-postcompact-${SID}" 2>/dev/null || true
fi

CKPT=""
if [ -n "$CWD" ] && [ -d "$CWD/.claude" ]; then
  # Point the resume at the CURRENT session's checkpoint — NOT a stale sibling.
  # The PreCompact writer may divert a fresh checkpoint to checkpoint-autogen.md
  # (anti-clobber for a tracked/curated or LIVE-peer checkpoint.md). This hook used
  # to hardcode "a fresh checkpoint.md was written — read it first", which was FALSE
  # after a divert and re-oriented a resume off a dead 2-day-old different-session
  # checkpoint (genomics 2026-07-06). checkpoint_resume single-sources the selection
  # (session-stamp match, else newest) and returns an honest, provenance-aware message.
  HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CKPT=$(python3 "$HOOK_DIR/checkpoint_resume.py" resume-message "$CWD/.claude" "$SID" 2>/dev/null || echo "")
fi

# Compaction loses operator CORRECTIONS while keeping ADR principles — so the same
# wrong instantiation gets re-derived. Re-inject the project's settled-framing headers
# (each is "topic — verdict") so a settled question is looked up, not re-derived.
REFRAMINGS=""
if [ -n "$CWD" ] && [ -f "$CWD/docs/decisions/REFRAMINGS.md" ]; then
  TOPICS=$(awk '/^## /{sub(/^## /,"");printf "%s%s",sep,$0;sep=" · "}' "$CWD/docs/decisions/REFRAMINGS.md" 2>/dev/null || echo "")
  [ -n "$TOPICS" ] && REFRAMINGS=" SETTLED FRAMINGS — do NOT re-derive these from principles; the pinned answer is in docs/decisions/REFRAMINGS.md (consult it + \`agentlogs search\` before asserting any identity/firewall/home/scope framing): ${TOPICS}."
fi

MSG="Context was just compacted.${CKPT} Re-orient and continue the in-progress work from the checkpoint's Pending Tasks — don't re-ask the user what you were doing. First verify reality against the compaction summary: run \`git log --oneline -10\` and confirm any work the summary claims as done actually landed (compaction summaries hallucinate completed commits). If a /loop is active, proceed with the current tick.${REFRAMINGS}"

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' \
  "$(printf '%s' "$MSG" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"

exit 0
