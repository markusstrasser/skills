#!/usr/bin/env python3
# Gov-ID: hook:secret-output-guard
# goal: prevent credential-dump CLIs from placing live secrets in agent tool output
# verifier: skills/hooks/test_pretool_secret_output_guard.py
# blast_radius: shared
"""Block B2 account-dump commands before they can emit credentials.

`b2 account get` (and the legacy `b2 get-account-info`) prints live key and
authorization-token material.  A post-tool redactor is too late: the raw
stdout may already have entered the transcript.  This hook therefore matches
only executable shell invocations and denies them before process creation.

The matcher is deliberately shell-aware enough to distinguish a command from
quoted prose while covering compound commands, pipelines, environment/command
prefixes, command substitutions, and ``python -m b2``.  Hook-input and shell
parse errors fail open, consistent with the shared PreToolUse hook contract.
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

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", re.DOTALL)
_SHELL_SEPARATORS = {";", "&", "&&", "|", "||", "(", ")", "\n"}
_LEADING_KEYWORDS = {"!", "do", "elif", "else", "then", "time"}
_PREFIXES = {"command", "exec", "nohup"}
_PYTHON = re.compile(r"^(?:python|python\d+(?:\.\d+)*)$")


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


def _segment_has_secret_invocation(segment: list[str]) -> bool:
    command = _strip_command_prefixes(segment)
    if not command:
        return False

    executable = _basename(command[0])
    if executable == "b2":
        return _has_dump_verb(command[1:])

    python_arguments = _python_b2_arguments(command)
    if python_arguments is not None and _has_dump_verb(python_arguments):
        return True

    # Shell wrappers can hide the same executable command in one quoted token.
    if executable in {"bash", "dash", "sh", "zsh"}:
        for index, token in enumerate(command[1:], start=1):
            if token == "-c" and index + 1 < len(command):
                return contains_secret_b2_dump(command[index + 1])
    return False


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


def contains_secret_b2_dump(command: str) -> bool:
    if not command or not command.strip():
        return False

    for body in _command_substitutions(command):
        if contains_secret_b2_dump(body):
            return True

    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
        lexer.whitespace_split = True
        lexer.whitespace = " \t\r"
        lexer.commenters = ""
        tokens = list(lexer)
    except (TypeError, ValueError):
        return False
    return any(_segment_has_secret_invocation(segment) for segment in _segments(tokens))


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
