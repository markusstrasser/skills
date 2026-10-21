"""Resolve ``$NAME`` references a command assigned literally earlier in itself.

Path guards (worktree-cd, worktree-location) read ``cd $S`` / ``git worktree add $W``
as an unreadable target and block. The common shape is ``S=/private/tmp/x; cd "$S"``,
where the value is right there in the command: 73 of 245 worktree-cd blocks in the
week to 2026-10-21 were that shape with a non-worktree literal. Expanding it lets the
guard judge the real path.

Guards must not be talked into allowing a cd the shell would really make, so a name
resolves only when the command binds it exactly once, by a plain top-level statement
(``NAME=value`` at the start of a ``;``-separated statement, followed by ``;``/``&&``
or the end) with a value free of quotes, ``$`` and shell metacharacters. Anything
else stays unresolved and the guard still blocks: subshell or ``{ }`` scopes, prefix
assignments (``W=x cmd``), conditional ones (``a || W=x``), ``for``/``read``/
``printf -v``/``declare``/``unset``/``+=``, and ``NAME=`` text inside quotes
(2026-10-21 review: each of those had turned a block into a pass).
"""
from __future__ import annotations

import re
import shlex

_REF_RE = re.compile(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)")
_PLAIN_ASSIGN_RE = re.compile(r"^([A-Za-z_]\w*)=(.*)$", re.S)
_PUNCT = ";&|()<>"
_UNSAFE_VALUE = set("\"'`$\\()<>;&|{}\n")
_BINDERS = r"for|read|unset|local|declare|typeset|readonly|eval|mapfile|readarray|getopts"


def _plain_top_level(cmd: str) -> dict[str, str]:
    """name -> value for each plain top-level ``NAME=value`` statement."""
    lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=_PUNCT)
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return {}
    found: dict[str, str] = {}
    depth, prev = 0, ";"
    for i, tok in enumerate(toks):
        if set(tok) <= set(_PUNCT):
            depth += tok.count("(") - tok.count(")")
            prev = tok
            continue
        if tok == "export" and prev == ";":
            continue  # `export NAME=value` binds like a plain statement
        m = _PLAIN_ASSIGN_RE.match(tok)
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if (m and depth == 0 and prev == ";" and nxt in (None, ";", "&&")
                and not (set(m.group(2)) & _UNSAFE_VALUE)):
            found[m.group(1)] = m.group(2)
        depth += (tok == "{") - (tok == "}")
        prev = ""
    return found


def expand_literal_vars(cmd: str) -> str:
    """Return ``cmd`` with each ``$NAME``/``${NAME}`` after a safe single binding
    replaced by its literal value. Unresolvable references stay as written."""
    if "$" not in cmd or "=" not in cmd:
        return cmd
    values = _plain_top_level(cmd)
    starts: dict[str, int] = {}
    for name in values:
        n = re.escape(name)
        binds = list(re.finditer(rf"(?<![\w$]){n}\+?=", cmd))
        if len(binds) != 1:
            continue
        if re.search(rf"\b(?:{_BINDERS})\b[^;&|\n]*?(?<![\w$]){n}\b|\bprintf\s+-v\s*{n}\b", cmd):
            continue
        starts[name] = binds[0].start()
    if not starts:
        return cmd

    def sub(m: re.Match[str]) -> str:
        name = m.group(1) or m.group(2)
        if name in starts and starts[name] < m.start():
            return values[name]
        return m.group(0)

    return _REF_RE.sub(sub, cmd)
