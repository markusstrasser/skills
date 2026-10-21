"""Resolve ``$NAME`` references a command assigned literally earlier in itself.

Path guards (worktree-cd, worktree-location) read ``cd $S`` / ``git worktree add $W``
as an unreadable target and block. The common shape is ``S=/private/tmp/x; cd "$S"``,
where the value is right there in the command: 73 of 245 worktree-cd blocks in the
week to 2026-10-21 were that shape with a non-worktree literal. Expanding it lets the
guard judge the real path; a value it cannot read (``$(…)``, another ``$VAR``) stays
unresolved, so the guard still blocks it.
"""
from __future__ import annotations

import re

_ASSIGN_RE = re.compile(r"(?:^|(?<=[\s;&|(]))([A-Za-z_]\w*)=(\"[^\"]*\"|'[^']*'|[^\s;&|()]*)")
_REF_RE = re.compile(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)")


def _literal(value: str) -> str | None:
    if value[:1] == "'" and value[-1:] == "'" and len(value) >= 2:
        return value[1:-1]
    if value[:1] == '"' and value[-1:] == '"' and len(value) >= 2:
        value = value[1:-1]
    if "$" in value or "`" in value or "\\" in value:
        return None
    return value


def expand_literal_vars(cmd: str) -> str:
    """Return ``cmd`` with each ``$NAME``/``${NAME}`` replaced by the literal value of the
    nearest earlier ``NAME=value`` in the same command. Unresolvable references stay."""
    assigns = [(m.start(), m.group(1), _literal(m.group(2))) for m in _ASSIGN_RE.finditer(cmd)]
    if not assigns:
        return cmd

    def sub(m: re.Match[str]) -> str:
        name = m.group(1) or m.group(2)
        value = None
        for pos, n, v in assigns:
            if pos >= m.start():
                break
            if n == name:
                value = v
        return m.group(0) if value is None else value

    return _REF_RE.sub(sub, cmd)
