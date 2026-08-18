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
    if (
        not re.search(r"(?:^|[;&|]\s*|\$\(\s*)git\b[^|;&\n]*\bcommit\b", cmd, flags=re.M)
        or "--dry-run" in cmd
    ):
        return None
    if ti.get("run_in_background"):
        return "BG"
    # The commit's own pipe into an exit-code-masking reader. Anchored to git at a
    # COMMAND POSITION — start of string, or after ; && || or a newline — not to a
    # leading git. The previous leading-only anchor called the non-leading case
    # "rarer"; it is in fact the dominant one, because `cd <repo>; git commit ... |
    # tail` is what any agent working with absolute paths writes. That miss let a
    # 342-file commit report success on tail's rc=0 while the gate had rejected it
    # (genomics, 2026-08-18).
    #
    # Command position (not bare `|`) is what keeps the 2026-07-04 prose/heredoc
    # false positives dead: in `echo 'git commit -m x | tail'` the git is preceded
    # by a quote, so it never sits at a command position. Heredocs are stripped
    # above. The segment between commit and the pipe allows a single & (so `2>&1 |`
    # is caught) but breaks on ; or && (a later `... | tail` on a *chained*
    # command is not this commit's pipe).
    if re.search(
        r"(?:^|[;\n]|&&|\|\|)\s*git\b[^|;&]*\bcommit\b(?:[^|;&]|&(?!&))*"
        r"\|\s*(tail|head|grep|sed|awk|cat|tee|less|more|wc)\b",
        cmd,
    ):
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
