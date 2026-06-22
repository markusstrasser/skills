#!/usr/bin/env bash
# pretool-pyunbuffered-inject.sh — PreToolUse(Bash) hook.
# Prepends PYTHONUNBUFFERED=1 to BACKGROUNDED python invocations via the
# `updatedInput` contract. `uv run` does NOT unbuffer stdout, so a backgrounded
# `uv run python3 ...` buffers its output — when you read the live log/task file
# mid-run you see 0 bytes, and a process killed under load looks like a silent
# failure with no traceback. This converts the console-output.md instruction
# ("set PYTHONUNBUFFERED=1 for backgrounded uv run python") into architecture.
#
# Scoped to be near-zero-risk:
#   - ONLY when run_in_background is true (foreground flushes at exit — no need).
#   - ONLY when the command invokes python AND PYTHONUNBUFFERED isn't already set.
#   - prepend-only (env var is ignored by non-python; can't break a command).
#   - handles compound commands (`cd X && uv run python`), pipelines, and
#     subshells by exporting the var shell-wide (`export VAR=1; <cmd>`) rather
#     than an inline `VAR=1 cmd` prefix (which binds only to the first simple
#     command and would mis-target python after `&&`). The export only changes
#     python's flush timing; it can't alter any command's output or behavior.
#
# Contract: exit 0 + {"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{...}}}
# Exit 0 with no output = no change.
#
# Evidence: 2026-06-13 — ~3 backgrounded smoke tests died with 0-byte output
# (buffered + killed under load), masking the real error; the rule existed in
# console-output.md but was instruction-only (skipped on the first attempts).

trap 'exit 0' ERR

INPUT=$(cat)

OUT=$(python3 - "$INPUT" <<'PY'
import sys, json, re

try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

ti = data.get("tool_input", {}) or {}
cmd = ti.get("command", "")
if not cmd:
    sys.exit(0)

# Foreground Bash flushes at exit (you see output then) — buffering only bites a
# live log read mid-run, which only happens when backgrounded.
if not ti.get("run_in_background"):
    sys.exit(0)

# Already unbuffered (env var or python -u) → nothing to do.
if "PYTHONUNBUFFERED" in cmd or re.search(r"\bpython3?\s+-u\b", cmd):
    sys.exit(0)

# Must actually invoke python (covers `python3 ...`, `uv run python3 ...`,
# `uv run --directory X python ...`). False positives (e.g. `echo python`) are
# harmless — the env var is ignored — but the next guard limits them anyway.
if not re.search(r"\bpython3?\b", cmd):
    sys.exit(0)

# `export VAR=1; <cmd>` sets the var shell-wide for the entire command, so it
# applies across compound chains (`cd X && uv run python3 ...`), pipelines, and
# subshells alike — unlike an inline `VAR=1 cmd` prefix, which binds only to the
# first simple command (so python after `&&` would NOT see it). This is the exact
# shape that bit 2026-06-22 (`cd <repo> && uv run python3 <bg audit>` buffered for
# 42 min and read as a wedged run). Each Bash tool call is a fresh shell, so the
# export cannot leak to a later command.
new_cmd = "export PYTHONUNBUFFERED=1; " + cmd
updated = dict(ti)
updated["command"] = new_cmd
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": updated,
    }
}))
PY
)
if [ -n "$OUT" ]; then
    printf '%s\n' "$OUT"
    ~/Projects/skills/hooks/hook-trigger-log.sh "pyunbuffered-inject" "rewrite" "bg python" 2>/dev/null || true
fi
exit 0
