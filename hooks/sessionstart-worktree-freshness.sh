#!/usr/bin/env bash
# SessionStart (global): warn when checkout is materially behind origin/main.
#
# Complements sessionstart-peer-session-warn.sh (concurrent sessions) and
# pretool-worktree-staleness-guard.py (subagent dispatch blind spots). Drift
# pass 2026-06-29: 157-commit stale genomics worktree + 14-commit phenome gap
# had no SessionStart nudge — operator discovered late.
#
# Advisory only, ALWAYS exit 0. Disable: WORKTREE_FRESHNESS_OFF=1
# Threshold: WORKTREE_BEHIND_WARN (default 10 commits behind origin/main).
set -uo pipefail

[ "${WORKTREE_FRESHNESS_OFF:-0}" = "1" ] && exit 0

input="$(cat 2>/dev/null || true)"
cwd="$(printf '%s' "$input" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd","") or "")
except Exception: print("")' 2>/dev/null)"
[ -z "$cwd" ] && cwd="$(pwd -P 2>/dev/null || true)"
[ -z "$cwd" ] && exit 0
cwd="$(cd "$cwd" 2>/dev/null && pwd -P || printf '%s' "$cwd")"

git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1 || exit 0

THRESH="${WORKTREE_BEHIND_WARN:-10}"
msgs=()

if git -C "$cwd" rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
  behind="$(git -C "$cwd" rev-list --count HEAD..origin/main 2>/dev/null || echo 0)"
  if [ "${behind:-0}" -ge "$THRESH" ] 2>/dev/null; then
    branch="$(git -C "$cwd" branch --show-current 2>/dev/null || echo detached)"
    msgs+=("⚠  CHECKOUT STALE — ${behind} commits behind origin/main on branch '${branch}':")
    msgs+=("       ${cwd}")
    msgs+=("   Cross-repo dispatch / worktree isolation may be blind to recent main.")
    msgs+=("   ▶  git -C \"${cwd}\" pull --rebase origin main   (or merge) before heavy work")
  fi
fi

# Linked worktree on a non-main branch with no upstream tracking — surface early.
if git -C "$cwd" worktree list --porcelain >/dev/null 2>&1; then
  wt_branch="$(git -C "$cwd" branch --show-current 2>/dev/null || true)"
  wt_count="$(git -C "$cwd" worktree list 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${wt_count:-0}" -gt 1 ] && [ -n "$wt_branch" ] && [ "$wt_branch" != "main" ]; then
  upstream="$(git -C "$cwd" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)"
    if [ -z "$upstream" ]; then
      msgs+=("⚠  WORKTREE branch '${wt_branch}' has no upstream — push/merge path unclear before dispatch.")
    fi
  fi
fi

if [ "${#msgs[@]}" -gt 0 ]; then
  printf '%s\n' "${msgs[@]}"
  ~/Projects/skills/hooks/hook-trigger-log.sh "worktree-freshness" "warn" "behind=${behind:-0}" 2>/dev/null || true
fi
exit 0
