#!/bin/bash
# Block `git commit` inside run_in_background=true Bash calls.
#
# Failure class (global CLAUDE.md <git_rules>, violated again 2026-06-10 in
# intel): a commit chained after a slow command auto-backgrounds; a pre-commit
# hook block returns exit 0 from the *task* (the notification reads success)
# while nothing landed — discoverable only by grepping the output file. Same
# class as piping commits through tail/head. Commits must run foreground.
#
# Reads the PreToolUse payload on stdin; blocks only when BOTH
# run_in_background:true AND a git-commit invocation appear.
INPUT=$(cat)
PARSED=$(echo "$INPUT" | python3 -c '
import json, sys, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input", {})
if not ti.get("run_in_background"):
    sys.exit(0)
cmd = ti.get("command", "")
# git commit / git -C <path> commit — ignore mentions inside quoted strings is
# overkill; false positives are acceptable (the fix is to foreground the call).
if re.search(r"\bgit\b[^|;&]*\bcommit\b", cmd):
    print("HIT")
' 2>/dev/null)
if [ "$PARSED" = "HIT" ]; then
  echo "BLOCKED: git commit inside run_in_background=true — a hook-blocked commit reports success while nothing lands. Run the commit FOREGROUND (background the slow step, then commit in a separate foreground call)." >&2
  exit 2
fi
exit 0
