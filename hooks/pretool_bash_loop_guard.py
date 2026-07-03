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
on "then" inside -m "..." (2026-07-03, session f4fecc9a).
"""
import re
import sys


def strip_heredocs(s: str) -> str:
    out, skip_until = [], None
    for ln in s.split("\n"):
        if skip_until is not None:
            if ln.strip() == skip_until:
                skip_until = None
            continue
        m = re.search(r"<<-?\s*(['\"]?)(\w+)\1", ln)
        out.append(ln)
        if m:
            skip_until = m.group(2)
    return "\n".join(out)


def strip_quoted(s: str) -> str:
    """Drop single/double-quoted spans (incl. their newlines). Backslash escapes are
    respected outside quotes and inside double quotes; single-quoted text is literal.
    An unterminated quote strips to end-of-string — fail-open, matching shell reality
    (the command would be a parse error anyway)."""
    out, i, n, q = [], 0, len(s), None
    while i < n:
        c = s[i]
        if q is None:
            if c == "\\" and i + 1 < n:
                out.append(c)
                out.append(s[i + 1])
                i += 2
                continue
            if c in ('"', "'"):
                q = c
            else:
                out.append(c)
        elif q == '"':
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == '"':
                q = None
        else:  # inside '...'
            if c == "'":
                q = None
        i += 1
    return "".join(out)


def has_multiline_block(cmd: str) -> bool:
    cmd = strip_quoted(strip_heredocs(cmd))
    # 'do\n' or 'then\n' in actual shell code = multiline loop/if (single-line forms pass)
    return bool(re.search(r"\b(do|then)\s*\n", cmd))


if __name__ == "__main__":
    sys.exit(0 if has_multiline_block(sys.stdin.read()) else 1)
