#!/usr/bin/env python3
# Gov-ID: hook:bash-background-ampersand
# goal: block a process-backgrounding `&` combined with run_in_background=true — the `&` forks a
#       grandchild the harness CANNOT track, so no completion notification fires (silent poll-required).
# verifier: skills/hooks/test_pretool_bash_background_ampersand.py
# blast_radius: shared
"""PreToolUse(Bash) guard: `&`-backgrounding inside run_in_background=true.

run_in_background already backgrounds the command AND tracks it (fires a <task-notification>
on completion). Adding a shell `&` forks a grandchild the harness does NOT track → the agent
never gets notified and must poll the output file. Always a bug (lived 2026-06-19: a cold-llmx
`... &` inside run_in_background detached it; "completed" fired for the wrapper, not llmx).

Reads the stdin envelope (no CLAUDE_TOOL_* env vars per the hook-input contract).
Exit 2 + stderr = block (message shown to the agent so it retries without the `&`).
Fail-open on any parse error.
"""
import json
import re
import sys


def has_backgrounding_amp(cmd: str) -> bool:
    """True iff cmd contains a process-backgrounding `&` (not &&, redirects, or a quoted &)."""
    s = re.sub(r'"(?:[^"\\]|\\.)*"', "", cmd)   # strip double-quoted segments
    s = re.sub(r"'[^']*'", "", s)               # strip single-quoted segments
    s = s.replace("&&", "")                      # logical-AND, not backgrounding
    s = re.sub(r"\d*>&\d*", "", s)               # 2>&1, >&2, >&
    s = re.sub(r"\d*<&\d*-?", "", s)             # 0<&-, <&
    s = s.replace("&>", "")                      # &> file
    s = s.replace("|&", "")                      # bash pipe-both
    return "&" in s                              # any remaining & backgrounds a process


def main() -> None:
    try:
        env = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # fail open
    if env.get("tool_name") != "Bash":
        sys.exit(0)
    ti = env.get("tool_input") or {}
    if not ti.get("run_in_background"):
        sys.exit(0)  # a manual `&` without run_in_background is the caller's choice; not this bug
    if has_backgrounding_amp(ti.get("command", "") or ""):
        sys.stderr.write(
            "[bg-ampersand-guard] BLOCKED: shell `&` with run_in_background=true.\n"
            "run_in_background ALREADY backgrounds AND tracks the command (you get a completion\n"
            "notification). A `&` forks a grandchild the harness can't track → NO notification,\n"
            "silent poll-required. Remove the trailing `&` (and any `& echo ...`); keep\n"
            "run_in_background=true. For output capture use the tool's own mechanism, not `> file &`.\n"
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
