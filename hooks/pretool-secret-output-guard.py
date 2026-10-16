#!/usr/bin/env python3
# Gov-ID: hook:secret-output-guard
# goal: prevent credential-dump CLIs and environment-exposing process listings from placing live secrets in agent tool output
# verifier: skills/hooks/test_pretool_secret_output_guard.py
# blast_radius: shared
"""Block commands whose output can carry live credentials, before they run.

Two shapes are denied:

* ``b2 account get`` (and the legacy ``b2 get-account-info``) prints live key
  and authorization-token material.
* Process listings that print full argument vectors (``pgrep -fl``,
  ``ps aux``, ``ps -ef``, ``ps -p PID``, ``ps -o args``, ``ps -E``,
  ``pstree``).  On 2026-10-16 a ``pgrep -fl`` liveness check printed a pytest
  worker's environment, API keys included, into an agent transcript.  Probes
  with short and long setproctitle titles did not reproduce the trigger, so
  every full-argument listing is treated as able to expose environment.
  PID-only and ``comm`` forms stay allowed, and so does any command that pipes
  through ``redact-env`` (``~/Projects/skills/bin/redact-env``).

A post-tool redactor is too late: the raw stdout may already have entered the
transcript.  The matcher is shell-aware enough to distinguish a command from
quoted prose while covering compound commands, pipelines, environment/command
prefixes, command substitutions, shell ``-c`` bodies, heredocs (a quoted body
is literal text; an unquoted body is scanned only for its substitutions) and
``python -m b2``.  Hook-input and shell parse errors fail open, consistent
with the shared PreToolUse hook contract.
"""
from __future__ import annotations

import json
import re
import shlex
import sys


BLOCK_MESSAGE = (
    "BLOCKED: `b2 account get` emits live key/token material. Use `b2 bucket list "
    "--json`, `b2 ls --json b2://`, or an allowlist-only account-info helper. Raw "
    "account dumps are forbidden in agent shell output."
)
PROCESS_LISTING_MESSAGE = (
    "BLOCKED: this process listing prints full argument vectors, which exposed another "
    "process's environment (API keys) in agent output on 2026-10-16. Use `pgrep -f PATTERN` "
    "for PIDs, `pgrep -f PATTERN | wc -l` for a count (macOS pgrep has no -c), or "
    "`ps -o pid=,etime=,comm= -p PID`; when you need the arguments, pipe the listing "
    "through `redact-env`, e.g. `pgrep -fl PATTERN | redact-env`."
)

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", re.DOTALL)
_SHELL_SEPARATORS = {";", "&", "&&", "|", "||", "(", ")", "\n"}
_LEADING_KEYWORDS = {"!", "do", "elif", "else", "then", "time"}
_PREFIXES = {"command", "exec", "nohup", "xargs"}
_PYTHON = re.compile(r"^(?:python|python\d+(?:\.\d+)*)$")
_SHELLS = {"bash", "dash", "sh", "zsh"}
_HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_MAX_DEPTH = 8

# Options that consume a value, for macOS and procps; the value never holds flags.
_PGREP_VALUE_OPTIONS = frozenset("FGMNOPUdgstu")
_PS_VALUE_OPTIONS = frozenset("GgMNOoptUu")
# Output fields that print the argument vector (procps, BSD, and AIX `%a`).
_PS_ARGUMENT_FIELDS = frozenset({"args", "cmd", "command", "%a"})


def _basename(token: str) -> str:
    return token.rsplit("/", 1)[-1]


def _segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SHELL_SEPARATORS:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _strip_command_prefixes(segment: list[str]) -> list[str]:
    """Return a simple command with assignments and safe prefixes removed."""
    index = 0
    while index < len(segment) and segment[index] in _LEADING_KEYWORDS:
        index += 1
    while index < len(segment) and _ASSIGNMENT.match(segment[index]):
        index += 1

    while index < len(segment):
        executable = _basename(segment[index])
        if executable == "env":
            index += 1
            while index < len(segment):
                token = segment[index]
                if token == "--":
                    index += 1
                    break
                if token.startswith("-") or _ASSIGNMENT.match(token):
                    index += 1
                    continue
                break
            continue
        if executable in _PREFIXES:
            index += 1
            while index < len(segment) and segment[index].startswith("-"):
                index += 1
            continue
        break
    return segment[index:]


def _has_dump_verb(arguments: list[str]) -> bool:
    if "get-account-info" in arguments:
        return True
    return any(
        arguments[index:index + 2] == ["account", "get"]
        for index in range(len(arguments) - 1)
    )


def _python_b2_arguments(command: list[str]) -> list[str] | None:
    """Return arguments after ``-m b2`` for direct or plain ``uv run`` Python."""
    executable = _basename(command[0]) if command else ""
    if _PYTHON.fullmatch(executable):
        python_index = 0
    elif (
        executable == "uv"
        and len(command) >= 3
        and command[1] == "run"
        and _PYTHON.fullmatch(_basename(command[2]))
    ):
        python_index = 2
    else:
        return None
    for module_index in range(python_index + 1, len(command) - 1):
        if command[module_index] == "-m" and command[module_index + 1] == "b2":
            return command[module_index + 2:]
    return None


def _command_substitutions(command: str) -> list[str]:
    """Extract unquoted/double-quoted ``$(...)`` and backtick bodies.

    Single-quoted text is literal shell prose and is intentionally ignored.
    This is an extractor, not a complete shell parser; nested ``$(...)`` is
    balanced and each returned body is parsed recursively by the main matcher.
    """
    bodies: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(command):
        char = command[index]
        if char == "\\":
            index += 2
            continue
        if char == "'" and quote != '"':
            quote = None if quote == "'" else "'"
            index += 1
            continue
        if char == '"' and quote != "'":
            quote = None if quote == '"' else '"'
            index += 1
            continue
        if quote == "'":
            index += 1
            continue

        if char == "`":
            end = index + 1
            while end < len(command):
                if command[end] == "\\":
                    end += 2
                    continue
                if command[end] == "`":
                    bodies.append(command[index + 1:end])
                    index = end + 1
                    break
                end += 1
            else:
                return bodies
            continue

        if command.startswith("$(", index):
            start = index + 2
            end = start
            depth = 1
            inner_quote: str | None = None
            while end < len(command):
                inner = command[end]
                if inner == "\\":
                    end += 2
                    continue
                if inner == "'" and inner_quote != '"':
                    inner_quote = None if inner_quote == "'" else "'"
                elif inner == '"' and inner_quote != "'":
                    inner_quote = None if inner_quote == '"' else '"'
                elif inner_quote is None:
                    if command.startswith("$(", end):
                        depth += 1
                        end += 1
                    elif inner == ")":
                        depth -= 1
                        if depth == 0:
                            bodies.append(command[start:end])
                            index = end + 1
                            break
                end += 1
            else:
                return bodies
            continue
        index += 1
    return bodies


def _strip_heredoc_bodies(command: str) -> tuple[str, list[str]]:
    """Return the command without heredoc bodies, plus the unquoted bodies.

    A quoted delimiter makes its body literal text.  An unquoted body still
    expands ``$(...)`` and backticks, so callers scan it for substitutions only.
    """
    lines = command.split("\n")
    kept: list[str] = []
    live_bodies: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        index += 1
        for match in _HEREDOC.finditer(line):
            strip_tabs, quote, delimiter = match.group(1) == "-", match.group(2), match.group(3)
            body: list[str] = []
            while index < len(lines):
                candidate = lines[index].lstrip("\t") if strip_tabs else lines[index]
                index += 1
                if candidate == delimiter:
                    break
                body.append(lines[index - 1])
            if not quote:
                live_bodies.append("\n".join(body))
    return "\n".join(kept), live_bodies


def _tokens(command: str) -> list[str] | None:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
        lexer.whitespace_split = True
        lexer.whitespace = " \t\r"
        lexer.commenters = ""
        return list(lexer)
    except (TypeError, ValueError):
        return None


def _is_shell_command_flag(token: str) -> bool:
    return token.startswith("-") and not token.startswith("--") and "c" in token[1:]


def _simple_commands(command: str, depth: int = 0) -> list[list[str]]:
    """Return every simple command the shell would run, prefixes removed."""
    if depth > _MAX_DEPTH or not command or not command.strip():
        return []
    text, live_bodies = _strip_heredoc_bodies(command)
    commands: list[list[str]] = []
    for source in (text, *live_bodies):
        for body in _command_substitutions(source):
            commands.extend(_simple_commands(body, depth + 1))
    tokens = _tokens(text)
    if tokens is None:
        return commands
    for segment in _segments(tokens):
        simple = _strip_command_prefixes(segment)
        if not simple:
            continue
        commands.append(simple)
        # Shell wrappers can hide a command in one quoted token.
        if _basename(simple[0]) in _SHELLS:
            for index, token in enumerate(simple[1:], start=1):
                if _is_shell_command_flag(token) and index + 1 < len(simple):
                    commands.extend(_simple_commands(simple[index + 1], depth + 1))
                    break
    return commands


def _is_b2_dump(command: list[str]) -> bool:
    if _basename(command[0]) == "b2":
        return _has_dump_verb(command[1:])
    python_arguments = _python_b2_arguments(command)
    return python_arguments is not None and _has_dump_verb(python_arguments)


def contains_secret_b2_dump(command: str) -> bool:
    return any(_is_b2_dump(simple) for simple in _simple_commands(command))


def _short_options(
    arguments: list[str], value_options: frozenset[str], *, bsd_first: bool = False
) -> tuple[set[str], dict[str, list[str]], list[str]]:
    """Parse getopt-style clusters into flags, option values and long options."""
    flags: set[str] = set()
    values: dict[str, list[str]] = {}
    long_options: list[str] = []
    index = 0
    while index < len(arguments):
        token = arguments[index]
        index += 1
        if token.startswith("--"):
            long_options.append(token)
            continue
        if token.startswith("-") and len(token) > 1:
            cluster = token[1:]
        elif bsd_first and index == 1 and token.isalpha():
            cluster = token
        else:
            continue
        for position, letter in enumerate(cluster):
            if letter in value_options:
                value = cluster[position + 1:]
                if not value and index < len(arguments):
                    value = arguments[index]
                    index += 1
                values.setdefault(letter, []).append(value)
                break
            flags.add(letter)
    return flags, values, long_options


def _pgrep_lists_arguments(arguments: list[str]) -> bool:
    flags, _values, long_options = _short_options(arguments, _PGREP_VALUE_OPTIONS)
    if "--list-full" in long_options:
        return True
    lists = "l" in flags or "--list-name" in long_options
    full = "f" in flags or "--full" in long_options
    return lists and full


def _ps_lists_arguments(arguments: list[str]) -> bool:
    # A dash-less first word is a BSD cluster (`ps aux`, `ps eww`); `e` there prints
    # the environment on procps.
    if arguments and not arguments[0].startswith("-") and arguments[0].isalpha():
        if "e" in arguments[0] or "E" in arguments[0]:
            return True
    flags, values, long_options = _short_options(arguments, _PS_VALUE_OPTIONS, bsd_first=True)
    if "E" in flags or "O" in values:
        # -E prints the environment; -O extends a default display that ends in the command.
        return True
    formats = list(values.get("o", []))
    formats += [option.split("=", 1)[1] for option in long_options if option.startswith("--format=")]
    if not formats:
        # Every default ps display ends in the full command column.
        return True
    fields = [
        field.split("=", 1)[0].strip().lower()
        for value in formats
        for field in re.split(r"[,\s]+", value)
        if field.strip()
    ]
    return any(field in _PS_ARGUMENT_FIELDS for field in fields)


def _lists_process_arguments(command: list[str]) -> bool:
    executable = _basename(command[0])
    if executable == "pgrep":
        return _pgrep_lists_arguments(command[1:])
    if executable == "ps":
        return _ps_lists_arguments(command[1:])
    return executable == "pstree"


def contains_process_argument_listing(command: str) -> bool:
    commands = _simple_commands(command)
    if any(_basename(simple[0]) == "redact-env" for simple in commands):
        return False
    return any(_lists_process_arguments(simple) for simple in commands)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") not in (None, "Bash"):
        return 0
    tool_input = payload.get("tool_input") or payload
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if contains_secret_b2_dump(command):
        print(BLOCK_MESSAGE, file=sys.stderr)
        return 2
    if contains_process_argument_listing(command):
        print(PROCESS_LISTING_MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
