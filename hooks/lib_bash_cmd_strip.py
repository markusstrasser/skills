#!/usr/bin/env python3
"""lib_bash_cmd_strip.py — THE single definition of bash-command-text preprocessing
for PreToolUse hooks that pattern-match on `tool_input.command`.

Why single-sourced (epistemic principle: a shared invariant has ONE definition):
two hooks (pretool-no-background-commit and the now-retired regex-based
pretool-bash-loop-guard) each carried a private copy of "sanitize the command
string before matching", and the copies diverged 4 times in 3 days — every
divergence was a live false block or silent pass: c1323e8 (heredoc body false-blocked loop-guard), ff79b2d (heredoc body
false-blocked a codex-brief write in no-background-commit), 7af4faa (quoted
prose 'then' at EOL false-blocked a commit), 681a068 (pipe-masked commit passed
silently). A stripper that differs between guards means the same command is
data to one hook and code to another. Consumers IMPORT these functions; never
re-state them. test_lib_bash_cmd_strip.py pins the 4 historical edge cases and
asserts the remaining pattern-matching hook uses these exact function objects.

Semantics (shell-parser-faithful, fail-open):
- Heredoc bodies and quoted spans are DATA — opaque to the shell parser — so
  keywords/commands inside them can never be real invocations.
- Command-position anchoring is NOT here: it is matcher logic that differs by
  design per hook (no-background-commit anchors `git` to command position;
  consumers define their own command-position semantics).
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


def strip_quoted_heredocs(s: str) -> str:
    """Drop bodies of heredocs whose delimiter is QUOTED (<<'EOF' / <<"EOF") — the shell
    performs NO expansion there, so the body is pure data. An UNQUOTED <<EOF still expands
    ($(...), backticks, $VAR) and is deliberately left in place to be scanned. Moved here from
    pretool_bash_backtick_guard (2026-09-04) when the secret-path guard needed the same rule."""
    out, skip_until = [], None
    for ln in s.split("\n"):
        if skip_until is not None:
            if ln.strip() == skip_until:
                skip_until = None
            continue
        m = re.search(r"<<-?\s*(['\"])(\w+)\1", ln)  # quoted delimiter ONLY
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


# <<[-] then a quoted delimiter ('EOF' "EOF" \EOF: literal body) or a bare one. A bare
# delimiter must start with a letter or _, so the shift in $(( x << 2 )) is not a heredoc.
_HEREDOC_OP = re.compile(
    r"<<(-?)[ \t]*(?:'([^'\n]+)'|\"([^\"\n]+)\"|\\([^\s;&|<>()]+)|([A-Za-z_][^\s;&|<>()'\"]*))"
)


def live_mask(s: str) -> str:
    """Blank every character the shell reads as literal data; keep what it parses as code.

    Returns `s` with literal text replaced by spaces (newlines kept), so an offset in the
    result is the same offset in `s`: match on the mask, slice the original. Literal:
    single-quoted and $'...' spans, backslash escapes, comments, and quoted-delimiter
    heredoc bodies. Live: command text, double-quoted text and unquoted heredoc bodies,
    where $( ... ) and backticks expand. $( ... ) restarts quoting even inside double
    quotes, which is what keeps the body of `git commit -m "$(cat <<'EOF' ...)"` literal;
    quote characters inside an unquoted heredoc body are plain text. Fail-open: an
    unterminated quote or heredoc blanks to the end. Unlike strip_quoted, this keeps
    double-quoted text, because a guard on what EXECUTES must still see "$(cmd)".
    """
    n = len(s)
    out = list(s)

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    # Frames: ["cmd", paren_depth, opened_by_dollar_paren] | ["dq"] |
    #         ["hd", delimiter, strip_tabs, literal_body]
    stack: list = [["cmd", 0, False]]
    pending: list = []  # heredocs whose body starts after the next newline token
    i = 0
    while i < n:
        top, c = stack[-1], s[i]
        if top[0] == "hd":
            if s[i - 1] == "\n":  # a body line starts: terminator, literal, or live text
                end = s.find("\n", i)
                end = n if end < 0 else end
                line = s[i:end]
                if (line.lstrip("\t") if top[2] else line) == top[1]:
                    stack.pop()
                    i = end + 1
                    continue
                if top[3]:
                    blank(i, end)
                    i = end + 1
                    continue
            if c == "\\":
                blank(i, i + 2)
                i += 2
            elif s.startswith("$(", i):
                stack.append(["cmd", 0, True])
                i += 2
            else:
                i += 1
            continue
        if c == "\\":
            blank(i, i + 2)
            i += 2
            continue
        if top[0] == "dq":
            if s.startswith("$(", i):
                stack.append(["cmd", 0, True])
                i += 2
                continue
            if c == '"':
                stack.pop()
            i += 1
            continue
        if c == "'" or s.startswith("$'", i):
            j = i + (2 if c == "$" else 1)
            while j < n and s[j] != "'":
                j += 2 if c == "$" and s[j] == "\\" else 1
            blank(i, j + 1)
            i = j + 1
        elif c == '"':
            stack.append(["dq"])
            i += 1
        elif s.startswith("$(", i):
            stack.append(["cmd", 0, True])
            i += 2
        elif c == "(":
            top[1] += 1
            i += 1
        elif c == ")":
            if top[1]:
                top[1] -= 1
            elif top[2]:
                stack.pop()
            i += 1
        elif c == "#" and (i == 0 or s[i - 1] in " \t\n;&|()"):
            end = s.find("\n", i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
        elif s.startswith("<<<", i):
            i += 3
        elif c == "<" and (m := _HEREDOC_OP.match(s, i)):
            delim = m.group(2) or m.group(3) or m.group(4) or m.group(5)
            pending.append((delim, m.group(1) == "-", m.group(5) is None))
            i = m.end()
        elif c == "\n" and pending:
            stack.extend(["hd", d, tabs, lit] for d, tabs, lit in reversed(pending))
            pending = []
            i += 1
        else:
            i += 1
    return "".join(out)
