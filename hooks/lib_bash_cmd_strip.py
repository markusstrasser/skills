#!/usr/bin/env python3
"""lib_bash_cmd_strip.py — THE single definition of bash-command-text preprocessing
for PreToolUse hooks that pattern-match on `tool_input.command`.

Why single-sourced (epistemic principle: a shared invariant has ONE definition):
two hooks (pretool-no-background-commit, pretool-bash-loop-guard) each carried a
private copy of "sanitize the command string before matching", and the copies
diverged 4 times in 3 days — every divergence was a live false block or silent
pass: c1323e8 (heredoc body false-blocked loop-guard), ff79b2d (heredoc body
false-blocked a codex-brief write in no-background-commit), 7af4faa (quoted
prose 'then' at EOL false-blocked a commit), 681a068 (pipe-masked commit passed
silently). A stripper that differs between guards means the same command is
data to one hook and code to another. Consumers IMPORT these functions; never
re-state them. test_lib_bash_cmd_strip.py pins the 4 historical edge cases and
asserts both hook sidecars use these exact function objects.

Semantics (shell-parser-faithful, fail-open):
- Heredoc bodies and quoted spans are DATA — opaque to the shell parser — so
  keywords/commands inside them can never be real invocations.
- Command-position anchoring is NOT here: it is matcher logic that differs by
  design per hook (no-background-commit anchors `git` to command position;
  loop-guard has no notion of command position).
"""
import re


def strip_heredocs(s: str) -> str:
    """Drop heredoc BODY lines (opener line kept, body + terminator line dropped).
    An unterminated heredoc strips to end-of-string — fail-open, matching shell
    reality (the shell would sit waiting for the terminator anyway)."""
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
