#!/usr/bin/env bash
# SessionEnd: zero-LLM capture for the recursive learning loop.
# Reads the SessionEnd JSON payload on stdin, extracts deterministic correction
# signals + SHADOW omission-probe firings into ~/.claude/reflect-capture.jsonl.
# Fail-open (always exit 0), shadow (no user/agent surface), self-gates to the
# test bed (intel, agent-infra) inside the Python. See plan 4d40085a.
set +e
REPO="$HOME/Projects/agent-infra"
SCRIPT="$REPO/scripts/reflect_capture.py"
[ -f "$SCRIPT" ] || exit 0
TO=""
command -v timeout  >/dev/null 2>&1 && TO="timeout 10"
command -v gtimeout >/dev/null 2>&1 && TO="gtimeout 10"
cat | $TO python3 "$SCRIPT" >/dev/null 2>&1
exit 0
