#!/usr/bin/env python3
"""pretool_bash_backtick_guard.py — catch markdown `inline code` smuggled into a
double-quoted shell argument, where the shell executes it as command substitution and
SILENTLY DELETES the text.

The bug class, in one line: a note/message/evidence field written as prose containing
`some-command` is DATA to the author and CODE to the shell. There is no error — the
backtick span is replaced by the (usually empty) stdout of running it, and the field is
stored with holes. Nothing downstream can detect it, because by the time any tool sees
the string the text is already gone. The PreToolUse hook is the ONLY layer that still
holds the un-expanded command text, which is why this is a hook and not a tool-side check.

Measured recurrence before this guard existed (agentlogs, project arc-agi):
  2026-07-06  dc9fefad  2 hits
  2026-07-17  6f4a8626  "backtick command-substitution silently swallowed two
                         inline-code-quoted CLI names in both my first ..."
  2026-07-17  b0826e4e  same session-pair, Evidence field corrected after the fact
  2026-07-25  56b4ac68  "corrupted by shell backtick expansion (my `just
                         pack-collision-check` triggered command substitution)"
  2026-07-28  c0db7fc1  a loop/phenomena.jsonl note stored with 4 spans deleted
                         (the claude invocation name, --safe-mode, a parent-dir
                         reference, and a backlog row id) — caught only on read-back
Five incidents, four sessions, three weeks. Every one was prose with markdown inline
code. Operator 2026-07-28: "this zsh and backticks shit keeps reappearing ... maybe we
can solve it for good."

SCOPE — deliberately narrow, because a guard with false positives gets routed around.
Fires ONLY when a backtick appears inside a double-quoted span that is the value of a
DATA-BEARING FLAG (--note, -m, --evidence, ...). A backtick in a bare command position
is legacy-but-intentional substitution and is left alone. Single-quoted spans are
literal in every POSIX shell and are never flagged.

Also fires on an ODD backtick count inside such a value: that is an unterminated
substitution, which is a bug under every reading.

Contract (matches the sidecar convention): `offending_flag(cmd)` returns the flag name
that carries a backticked value, or None. The dispatch gate turns non-None into a block.
"""

import re
import sys

# A quoted-delimiter heredoc body is data the shell never expands, so a backtick there is
# literal — exactly the fix this guard recommends. ONE definition, shared with the
# secret-path guard (lib_bash_cmd_strip.py); never re-state it here.
from lib_bash_cmd_strip import strip_quoted_heredocs as _strip_quoted_heredocs

# Flags whose value is prose/data written by an agent, across the CLIs this repo family
# uses: git, gh, the loop tools (phenomena.py, idea_backlog.py), and generic scripts.
DATA_FLAGS = (
    "--note",
    "--notes",
    "-m",
    "--message",
    "--title",
    "--evidence",
    "--source",
    "--reason",
    "--description",
    "--desc",
    "--summary",
    "--body",
    "--caption",
    "--text",
    "--content",
    "--prompt",
    "--comment",
    "--label",
    "--annotation",
)

# Bare key=value data fields (no leading dashes). `just backlog edit --append note="..."` is
# the single most-used form in this repo and the first version of this guard missed it — the
# false-negative that the test suite caught before shipping.
BARE_FIELDS = ("note", "evidence", "source", "reason", "title", "summary", "description")

# A flag token, then its value either as --flag=VALUE or --flag VALUE.
_FLAG_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(f) for f in DATA_FLAGS) + r")(=|\s+)"
    r"|(?<![\w.-])(" + "|".join(BARE_FIELDS) + r")=",
)


def _double_quoted_value_at(cmd: str, start: int) -> str | None:
    """If a double-quoted string starts at/near `start`, return its raw body.

    Returns None when the value is single-quoted (literal — safe), or is not quoted at
    all (a bare token cannot contain an unescaped backtick without the shell having
    already substituted at parse time; nothing useful to say).
    """
    i = start
    while i < len(cmd) and cmd[i] in " \t":
        i += 1
    if i >= len(cmd) or cmd[i] != '"':
        return None
    i += 1
    body = []
    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and i + 1 < len(cmd):
            # An escaped backtick is literal, NOT a substitution — drop it rather than
            # copying it through, or the scan below flags the guard's own escape advice.
            nxt = cmd[i + 1]
            body.append("" if nxt == "`" else nxt)
            i += 2
            continue
        if c == '"':
            return "".join(body)
        body.append(c)
        i += 1
    return "".join(body)  # unterminated — fail toward inspecting it


def offending_flag(cmd: str) -> str | None:
    """-> the data-bearing flag whose double-quoted value contains a live backtick."""
    cmd = _strip_quoted_heredocs(cmd)
    for m in _FLAG_RE.finditer(cmd):
        flag = m.group(1) or (m.group(3) + "=")
        val = _double_quoted_value_at(cmd, m.end())
        if val is None:
            continue
        if "`" in val:
            return flag
    return None


def reason(flag: str) -> str:
    return (
        f"BLOCKED: the value of {flag} is a DOUBLE-QUOTED string containing a backtick, so the\n"
        "shell will run the backticked text as a command and substitute its output — silently\n"
        "DELETING that span from your data. No error is raised and no downstream tool can\n"
        "detect it: by the time the CLI receives the string, the text is already gone.\n"
        "(5 incidents, 4 sessions, 3 weeks — the last corrupted a phenomena note.)\n"
        "\n"
        "Markdown `inline code` in prose is the usual cause. Fixes, in order of preference:\n"
        "  1. Write the text from a FILE:  git commit -F msg.txt   |   --note-file note.md\n"
        "  2. Heredoc with a QUOTED delimiter (no expansion at all):\n"
        "       tool add --note \"$(cat <<'EOF'\n"
        "     ...prose with `inline code`...\n"
        "     EOF\n"
        '     )"\n'
        "  3. SINGLE-quote the value (literal in every POSIX shell) if it contains no\n"
        "     single quotes: --note 'prose with `inline code`'\n"
        "  4. If you genuinely want substitution here, use $(...) so the intent is explicit.\n"
    )


def main() -> int:
    cmd = sys.stdin.read()
    flag = offending_flag(cmd)
    if flag:
        sys.stderr.write(reason(flag))
        return 0  # sidecar convention: exit 0 == offense found, wrapper blocks
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
