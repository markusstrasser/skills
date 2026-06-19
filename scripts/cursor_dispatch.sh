#!/usr/bin/env bash
# cursor_dispatch.sh — hardened repo-coupled Tier-2 dispatch lane for `/improve maintain`.
#
# Routes read-only critique/analysis to cursor-agent (Cursor quota, repo-aware) BEHIND a
# safety wrapper so a missing binary / expired auth / quota stall / timeout NEVER silently
# breaks the maintain loop. On ANY failure it exits with a FALLBACK code and the caller must
# route the same task to the claude Agent lane.
#
# Anchor: agent-infra decisions/2026-06-16-improve-dispatch-route-to-cursor-agent.md (Fix B).
# Verified CLI surface (cursor-agent 2026.06.15): --mode {plan,ask}, ask=read-only;
# NO native --timeout (wrap with shell timeout); -f/--force auto-approves read commands;
# --workspace roots it. Model = Composer ONLY (Cursor's native lane — best price/perf,
# operator directive 2026-06-19). A non-Composer --model (opus/gpt/…) is off-policy AND
# hook-blocked by pretool-cursor-model-guard.py: cursor proxies frontier models at separate
# metered rates. --model accepts composer tiers only (composer-2.5 / composer-2.5-fast).
#
# Usage:
#   cursor_dispatch.sh --prompt "<text>" --out <artifact> [--workspace DIR] [--model M] [--timeout S]
# Exit codes (any non-zero → caller FALLBACK to claude Agent lane):
#   0  success — ANSI-stripped, non-empty analysis written to --out
#   10 cursor-agent binary not found
#   11 cursor-agent not authenticated
#   12 dispatch timed out
#   13 cursor-agent exited non-zero
#   14 output empty after capture
#    2 usage error
set -uo pipefail

MODEL="composer-2.5"                    # Composer ONLY (best price/perf; non-composer is hook-blocked + off-policy)
WORKSPACE="$PWD"
TIMEOUT=600                              # cursor-agent has no native timeout; bound it here
PROMPT=""
OUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt) PROMPT="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --workspace) WORKSPACE="$2"; shift 2;;
    --model) MODEL="$2"; shift 2;;
    --timeout) TIMEOUT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$PROMPT" ] && [ -n "$OUT" ] || { echo "usage: --prompt and --out required" >&2; exit 2; }

# Preflight 1 — binary present (bare runners / Docker may lack it).
command -v cursor-agent >/dev/null 2>&1 || { echo "FALLBACK: cursor-agent not found" >&2; exit 10; }

# Preflight 2 — authenticated. Principal check on isAuthenticated, not just the exit code
# (auth can expire; a headless loop cannot complete browser OAuth).
if ! cursor-agent status --format json 2>/dev/null | grep -q '"isAuthenticated": *true'; then
  echo "FALLBACK: cursor-agent not authenticated" >&2; exit 11
fi

# Bounded run — shell timeout (no native flag); root at --workspace to prevent worktree escape.
raw="$(mktemp)"
trap 'rm -f "$raw"' EXIT
timeout "$TIMEOUT" cursor-agent -p --output-format text --mode ask --force --trust \
  --workspace "$WORKSPACE" --model "$MODEL" "$PROMPT" >"$raw" 2>/dev/null
rc=$?
[ "$rc" -eq 124 ] && { echo "FALLBACK: timed out after ${TIMEOUT}s" >&2; exit 12; }
[ "$rc" -ne 0 ]   && { echo "FALLBACK: cursor-agent exit $rc" >&2; exit 13; }

# Deterministic capture — strip ANSI/control sequences so downstream markdown/manifests aren't corrupted.
sed $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g' "$raw" > "$OUT"
[ -s "$OUT" ] || { echo "FALLBACK: empty output" >&2; exit 14; }

echo "$OUT"
exit 0
