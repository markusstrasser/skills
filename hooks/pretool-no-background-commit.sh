#!/bin/bash
# Block the two ways a `git commit` reports success while nothing lands.
#
# Failure class (global CLAUDE.md <git_rules>): a hook-blocked commit's real
# exit code is hidden, so the agent believes it committed when it did not —
# discoverable only by grepping output / git log after the fact.
#   (BG)   commit inside run_in_background=true: the *task* returns exit 0 even
#          when the pre-commit hook blocks (intel, 2026-06-10).
#   (PIPE) commit piped into tail/head/grep/...: the pipeline exit code is the
#          masker's, not git's — a blocked commit reads rc=0 (lost a 6-commit
#          chain 2026-04-26; recurred in genomics 2026-07-03 despite being
#          documented in code-pitfalls.md — a doc wasn't enough, hence this hook).
# Both are the SAME masking class; commits must run foreground with the exit
# code captured explicitly.
#
# Reads the PreToolUse payload on stdin. --dry-run is exempt (it lands nothing).
INPUT=$(cat)
CLASS=$(echo "$INPUT" | python3 -c '
import json, sys, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input", {})
cmd = ti.get("command", "")
# Heredoc bodies are DATA, not commands — strip them before matching. A brief
# file written via cat <<EOF containing the text "Do NOT git commit" is not a
# commit (false-positive cascade 2026-07-04: blocked call -> brief never written
# -> downstream codex ran with an empty prompt).
cmd = re.sub(r"<<-?\s*([\"\x27]?)(\w+)\1[^\n]*\n.*?\n\s*\2(?=\s|$|;)", "<<HEREDOC_STRIPPED", cmd, flags=re.S)
# A real git commit INVOCATION: git at a command position (start, after ; && || | & or $( ),
# not a mention of the words inside prose/echo arguments. Not --dry-run.
if not re.search(r"(?:^|[;&|]\s*|\$\(\s*)git\b[^|;&\n]*\bcommit\b", cmd, flags=re.M) or "--dry-run" in cmd:
    sys.exit(0)
if ti.get("run_in_background"):
    print("BG")
# The commits own pipe into an exit-code-masking reader. Anchored to a LEADING
# `git ... commit` (the dominant real trap: `git commit -F m | tail`) so that a
# mere mention of the pattern inside an echo / heredoc / test harness — which
# starts with echo/cat/etc., not git — is not a false positive. The segment
# between commit and the pipe allows a single & (so `2>&1 |` is caught) but
# breaks on ; or && (a later `... | tail` on a *chained* command is not us).
# Misses X && git commit | tail (non-leading); rarer, and git log still catches it.
elif re.search(r"^\s*git\b[^|;&]*\bcommit\b(?:[^|;&]|&(?!&))*\|\s*(tail|head|grep|sed|awk|cat|tee|less|more|wc)\b", cmd):
    print("PIPE")
' 2>/dev/null)
if [ "$CLASS" = "BG" ]; then
  echo "BLOCKED: git commit inside run_in_background=true — a hook-blocked commit reports success while nothing lands. Run the commit FOREGROUND (background the slow step, then commit in a separate foreground call)." >&2
  exit 2
fi
if [ "$CLASS" = "PIPE" ]; then
  echo "BLOCKED: git commit piped into tail/head/grep/... masks git's exit code (the pipeline returns the reader's rc), so a hook-blocked commit reads rc=0 while nothing lands. Capture the exit code explicitly instead: 'git commit -F msg > /tmp/c.txt 2>&1; echo COMMIT_RC=\$?; tail /tmp/c.txt' — then verify with 'git log --oneline -1'." >&2
  exit 2
fi
exit 0
