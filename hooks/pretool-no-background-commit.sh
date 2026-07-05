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
# Classification lives in the sidecar (testable; heredoc stripping is single-sourced
# there via lib_bash_cmd_strip — divergent stripper copies broke 4× in 3 days).
INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLASS=$(printf '%s' "$INPUT" | python3 "$HOOK_DIR/pretool_no_background_commit.py" 2>/dev/null)
if [ "$CLASS" = "BG" ]; then
  echo "BLOCKED: git commit inside run_in_background=true — a hook-blocked commit reports success while nothing lands. Run the commit FOREGROUND (background the slow step, then commit in a separate foreground call)." >&2
  exit 2
fi
if [ "$CLASS" = "PIPE" ]; then
  echo "BLOCKED: git commit piped into tail/head/grep/... masks git's exit code (the pipeline returns the reader's rc), so a hook-blocked commit reads rc=0 while nothing lands. Capture the exit code explicitly instead: 'git commit -F msg > /tmp/c.txt 2>&1; echo COMMIT_RC=\$?; tail /tmp/c.txt' — then verify with 'git log --oneline -1'." >&2
  exit 2
fi
exit 0
