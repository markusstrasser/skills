#!/usr/bin/env python3
"""Syntax preflight for multiline zsh control structures.

The historical hook treated every ``do``/``then`` followed by a newline as a
parse error. That sequence is the normal multiline spelling in zsh, so the
guard blocked valid commands and never established that parsing would fail.

Keep the cheap lexical check only as an admission filter, then ask zsh itself
with ``-n`` (parse without execution). Contract for the shell wrapper remains:
stdin is the command; exit 0 only for a confirmed syntax error, exit 1 for a
valid command or when zsh is unavailable (fail open).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys


_MULTILINE_CONTROL = re.compile(r"\b(do|then)\s*\n")


def syntax_error(command: str) -> str | None:
    """Return zsh's parse error for a multiline control block, else ``None``.

    ``zsh -n`` reads and parses the command but does not execute it. Restricting
    the subprocess to the old hook's candidate shape avoids paying for a zsh
    process on ordinary shell calls and avoids expanding this guard's scope.
    """

    if not _MULTILINE_CONTROL.search(command):
        return None
    zsh = shutil.which("zsh")
    if zsh is None:
        return None
    result = subprocess.run(
        [zsh, "-n", "-c", command],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode == 0:
        return None
    return result.stderr.strip() or f"zsh syntax check exited {result.returncode}"


def has_multiline_block(command: str) -> bool:
    """Compatibility predicate: true only for a confirmed syntax error."""

    return syntax_error(command) is not None


if __name__ == "__main__":
    error = syntax_error(sys.stdin.read())
    if error is None:
        raise SystemExit(1)
    print(error)
    raise SystemExit(0)
