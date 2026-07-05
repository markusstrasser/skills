#!/usr/bin/env python3
"""pretool_bash_loop_guard.py — detect multiline for/while/until/if blocks (zsh parse errors).

Sidecar for pretool-bash-loop-guard.sh (extracted 2026-07-04 — the inline python-in-bash
needed a quote scanner, and escaping a quote scanner inside a bash double-quoted string is
its own bug class).

Contract (matches the old inline code): read the COMMAND on stdin; exit 0 if a multiline
control structure is present (shell wrapper then blocks), exit 1 if clean.

Heredoc bodies and quoted-string spans are stripped first — both are opaque to the shell
parser, so 'do\\n'/'then\\n' inside them cannot be a control structure. False positives
fixed: heredoc payload (2026-06-10, session e24a68d3); commit-message prose ending a line
on "then" inside -m "..." (2026-07-03, session f4fecc9a). The strippers are single-sourced
in lib_bash_cmd_strip (divergent copies false-blocked/passed 4× in 3 days — see lib header).
"""
import re
import sys

from lib_bash_cmd_strip import strip_heredocs, strip_quoted


def has_multiline_block(cmd: str) -> bool:
    cmd = strip_quoted(strip_heredocs(cmd))
    # 'do\n' or 'then\n' in actual shell code = multiline loop/if (single-line forms pass)
    return bool(re.search(r"\b(do|then)\s*\n", cmd))


if __name__ == "__main__":
    sys.exit(0 if has_multiline_block(sys.stdin.read()) else 1)
