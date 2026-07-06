#!/usr/bin/env python3
# Gov-ID: hook:bg-dispatch-footgun
# goal: two recurring background-dispatch footguns that fail silently — (a) `codex exec` via
#       run_in_background hangs forever on "Reading additional input from stdin..." with no
#       `< /dev/null` (4 dead dispatches, ~90 min, heli 2dbe4c62); (b) run_in_background + a
#       relative interpreter path fails MODULE_NOT_FOUND because bg shells reset cwd (3× arc-agi).
# verifier: skills/hooks/test_pretool_bg_dispatch_footgun.py
# blast_radius: shared
"""PreToolUse(Bash) advisory: background-dispatch footguns. WARN only, never blocks.

Fires ONLY when tool_input.run_in_background is true. Two independent checks, either may fire:

  (a) codex-exec-stdin: `codex exec` present AND no `< /dev/null` / `</dev/null` → the process
      blocks on stdin EOF that never comes (silent hang). Also nudges off deprecated `--full-auto`.
  (b) relative-interpreter-path: an interpreter (node / python[3] / `uv run <tool>`) invoked on a
      RELATIVE path with no leading `cd ` → bg shells do not inherit the foreground cwd.

Advisory (hookSpecificOutput.additionalContext); fail-open on any parse error. Reversibility:
delete the hook + registration.
"""
from __future__ import annotations

import json
import re
import sys


def _strip_quotes(cmd: str) -> str:
    s = re.sub(r'"(?:[^"\\]|\\.)*"', "", cmd)
    s = re.sub(r"'[^']*'", "", s)
    return s


def check_codex_exec(cmd: str) -> str | None:
    """Warn if a background `codex exec` does not close stdin with < /dev/null."""
    if not re.search(r"\bcodex\s+exec\b", cmd):
        return None
    if re.search(r"<\s*/dev/null", cmd):
        return None
    extra = ""
    if "--full-auto" in cmd:
        extra = " (also: --full-auto is deprecated -> --sandbox workspace-write.)"
    return (
        "background `codex exec` must close stdin or it hangs forever on 'Reading additional "
        "input from stdin...' (never EOFs; task shows running at ~0 CPU). Append `< /dev/null`, "
        "redirect output to a log file, and never pipe through `| tail` (buffers until EOF, so a "
        "kill swallows all output)." + extra
    )


# interpreter followed by a token that does NOT begin with / ~ $ - (i.e. a relative path/arg)
_REL_INTERP = re.compile(r"\b(?:node|python3?|uv\s+run\s+[^\s]+)\s+([^/~$\s-][^\s]*)")


def check_relative_path(cmd: str) -> str | None:
    """Warn if a background interpreter runs a relative path with no leading `cd`."""
    # A leading `cd ` (anywhere before the interpreter, e.g. `cd /abs && node x.mjs`) is fine.
    if re.search(r"(^|&&|;|\|)\s*cd\s+", cmd):
        return None
    m = _REL_INTERP.search(cmd)
    if not m:
        return None
    target = m.group(1)
    # A bare flag (`-m`, `--foo`) or a subcommand keyword isn't a script path we can judge; but the
    # regex already excludes a leading '-'. Skip obvious non-path tokens (all-word, no dot/slash) —
    # e.g. `uv run pytest` where pytest is a console entry point, not a cwd-relative file.
    if "/" not in target and "." not in target:
        return None
    return (
        f"background shell + relative path `{target}` — background shells reset cwd (they do NOT "
        "inherit the foreground session's directory), so a relative script path fails "
        "MODULE_NOT_FOUND. Prefix `cd <abs> && ...` or use an absolute path."
    )


def main() -> None:
    try:
        env = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # fail open
    if env.get("tool_name") != "Bash":
        sys.exit(0)
    ti = env.get("tool_input") or {}
    if not ti.get("run_in_background"):
        sys.exit(0)
    cmd = ti.get("command", "") or ""
    stripped = _strip_quotes(cmd)
    warnings = [w for w in (check_codex_exec(stripped), check_relative_path(stripped)) if w]
    if not warnings:
        sys.exit(0)
    msg = "[bg-dispatch-footgun] " + "  ".join(warnings)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
