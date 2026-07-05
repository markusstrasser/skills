#!/usr/bin/env python3
"""pretool_no_background_commit.py — classify exit-code-masked git commits.

Sidecar for pretool-no-background-commit.sh (extracted 2026-07-05 to single-source
the heredoc stripper in lib_bash_cmd_strip — the private regex copy here and the
loop-guard's scanner diverged 4× in 3 days; see lib header).

Contract: read the PreToolUse JSON envelope on stdin; print "BG" or "PIPE" if the
command is a masked commit (shell wrapper then blocks), print nothing if clean.
"""
import json
import re
import sys

from lib_bash_cmd_strip import strip_heredocs


def classify(envelope: dict) -> str | None:
    ti = envelope.get("tool_input", {})
    cmd = ti.get("command", "")
    # Heredoc bodies are DATA, not commands — strip them before matching. A brief
    # file written via cat <<EOF containing the text "Do NOT git commit" is not a
    # commit (false-positive cascade 2026-07-04: blocked call -> brief never written
    # -> downstream codex ran with an empty prompt).
    cmd = strip_heredocs(cmd)
    # A real git commit INVOCATION: git at a command position (start, after ; && || | & or $( ),
    # not a mention of the words inside prose/echo arguments. Not --dry-run.
    if not re.search(r"(?:^|[;&|]\s*|\$\(\s*)git\b[^|;&\n]*\bcommit\b", cmd, flags=re.M) or "--dry-run" in cmd:
        return None
    if ti.get("run_in_background"):
        return "BG"
    # The commits own pipe into an exit-code-masking reader. Anchored to a LEADING
    # `git ... commit` (the dominant real trap: `git commit -F m | tail`) so that a
    # mere mention of the pattern inside an echo / heredoc / test harness — which
    # starts with echo/cat/etc., not git — is not a false positive. The segment
    # between commit and the pipe allows a single & (so `2>&1 |` is caught) but
    # breaks on ; or && (a later `... | tail` on a *chained* command is not us).
    # Misses X && git commit | tail (non-leading); rarer, and git log still catches it.
    if re.search(r"^\s*git\b[^|;&]*\bcommit\b(?:[^|;&]|&(?!&))*\|\s*(tail|head|grep|sed|awk|cat|tee|less|more|wc)\b", cmd):
        return "PIPE"
    return None


if __name__ == "__main__":
    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    verdict = classify(d)
    if verdict:
        print(verdict)
