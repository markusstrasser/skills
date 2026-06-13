#!/usr/bin/env bash
# pretool-governance-edit-notice.sh — ADVISORY notice on edits to human-owned governance text.
#
# Gov-ID: hook:governance-edit-notice
# goal: surface the human-owned-governance protection at EDIT time WITHOUT hard-blocking.
#   Replaces the deleted ~/.claude/hooks/pretool-shared-infra-guard.sh, whose HARD block forced an
#   agent to delete the global guard to comply with a human-directed GOALS edit (2026-06-13 incident,
#   3x-repeated instruction). Policy (agent-infra invariants #1, relaxed 2026-06-13): human-DIRECTED
#   reversible governance edits are allowed — explicit OR confidently inferred from the user's
#   messages; only an AUTONOMOUS self-edit with no human message to infer from is barred (the p-hack
#   hole). So this WARNS and lets the edit proceed; the daily governance downstream-watch (/improve
#   maintain) + git reversibility are the safety net. Lives in skills/hooks (git-tracked) so it can
#   never be silently lost like its predecessor.
# verifier: null
# blast_radius: shared
#
# Fail-open: any error → exit 0 (never block an edit on a hook bug). Reads the stdin envelope per
# the hook input contract (NO CLAUDE_TOOL_* env vars). Dependency-free (sed), no python/jq.

input="$(cat 2>/dev/null || true)"
path="$(printf '%s' "$input" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

case "$path" in
  */GOALS.md|*/agent-infra/CLAUDE.md)
    {
      echo "[governance-notice] '$path' is human-owned governance text."
      echo "  Policy (agent-infra invariants #1): human-DIRECTED reversible edits are allowed —"
      echo "  explicit OR confidently inferred from the user's messages. An autonomous self-edit with"
      echo "  no human message to infer from is BARRED (the p-hack hole). This is ADVISORY, not a block:"
      echo "  proceeding. The edit is visible to the daily governance downstream-watch + git history."
    } >&2
    ;;
esac
exit 0
