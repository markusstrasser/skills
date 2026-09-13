#!/usr/bin/env python3
"""Require a timeout on each guarded CLI invocation, never on argument prose.

The existing app-logs/container-exec policy remains independent of installed CLI
defaults. A downstream head does not bound a quiet producer. Shell syntax and
substitution extraction reuse their existing owners; this module classifies only
the executable and its wrappers. It never executes inspected command text.

Evidence: exec leaks in Codex 019d6d86; help denied in 01a01da9 (2026-08-23);
heredoc prose denied in genomics fe315f9b (2026-09-02); finite search/docs commands
denied in the 2026-09-13 genomics propagation campaign (regression tests).
"""

from __future__ import annotations

import importlib
import json
import math
import re
import shlex
import sys

# Do not copy a shell parser or the guards' historical private heredoc strippers.
_shell = importlib.import_module("pretool-bash-dispatch")
_substitutions = importlib.import_module(
    "pretool-secret-output-guard"
)._command_substitutions

_CONTROL_PREFIXES = {"if", "elif", "while", "until", "then", "else", "do", "{"}
_PYTHON = re.compile(r"python(?:\d+(?:\.\d+)*)?")
_DURATION = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)[smhd]?")
_UV_VALUES = {
    "--project",
    "--directory",
    "--package",
    "--group",
    "--extra",
    "--with",
    "--with-editable",
    "--with-requirements",
    "--python",
    "-p",
    "--env-file",
    "--index",
    "--default-index",
    "--index-url",
    "--extra-index-url",
    "--config-file",
}
_MODAL_VALUES = {
    "--profile",
    "--env",
    "-e",
    "--since",
    "--until",
    "--tail",
    "-n",
    "--search",
    "--function",
    "--function-call",
    "--container",
    "--source",
    "-s",
}


def _basename(word: str) -> str:
    return word.rsplit("/", 1)[-1]


def _after_options(words: list[str], value_options: set[str]) -> list[str]:
    """Return a wrapper's child argv; its own help has no child execution."""
    index = 0
    while index < len(words):
        word = words[index]
        if word == "--":
            return words[index + 1 :]
        if word in {"--help", "-h"} and word not in value_options:
            return []
        if not word.startswith("-"):
            return words[index:]
        index += 2 if word in value_options else 1
    return []


def _option_tokens(words: list[str], value_options: set[str]):
    index = 0
    while index < len(words):
        word = words[index]
        if word == "--":
            break
        yield word
        index += 2 if word in value_options else 1


def _has_help(words: list[str], value_options: set[str]) -> bool:
    return any(
        word in {"--help", "-h"} for word in _option_tokens(words, value_options)
    )


def _stream(words: list[str]) -> bool:
    executable, args = _basename(words[0]), words[1:]
    if executable == "modal":
        if _has_help(args, _MODAL_VALUES):
            return False
        args = _after_options(args, _MODAL_VALUES)
        return args[:2] in (["app", "logs"], ["container", "exec"])
    if executable == "tail":
        value_options = {"-n", "-c", "--lines", "--bytes", "--pid", "--sleep-interval"}
        if _has_help(args, value_options):
            return False
        return any(
            arg in {"-f", "-F", "--follow"} or arg.startswith("--follow=")
            for arg in _option_tokens(args, value_options)
        )
    if executable == "docker" and args[:1] == ["logs"]:
        return not _has_help(args[1:], {"--since", "--until", "--tail"}) and any(
            arg in {"-f", "--follow"}
            for arg in _option_tokens(args[1:], {"--since", "--until", "--tail"})
        )
    return False


def _command_has_unbounded_stream(words: list[str], bounded: bool) -> bool:
    while words:
        while words and words[0] in _CONTROL_PREFIXES:
            words = words[1:]
        # Reuse the existing assignment/command/exec/time prefix semantics, including
        # command -v/-V (query only). Quoting here is data for that classifier only.
        index = _shell._git_noext_command_index(
            [(shlex.quote(word), 0, 0) for word in words]
        )
        if index is None:
            return False
        words = words[index:]
        if not words:
            return False
        executable = _basename(words[0])
        if executable in {"env", "sudo", "nohup"}:
            values = (
                {"-u", "--unset", "-C", "--chdir"}
                if executable == "env"
                else {
                    "-u",
                    "--user",
                    "-g",
                    "--group",
                    "-h",
                    "--host",
                    "-p",
                    "--prompt",
                }
            )
            words = _after_options(words[1:], values)
            continue
        if executable in {"timeout", "gtimeout"}:
            words = _after_options(words[1:], {"-s", "--signal", "-k", "--kill-after"})
            if not words:
                return False
            duration = words[0]
            if _DURATION.fullmatch(duration):
                seconds = float(duration.rstrip("smhd"))
                bounded = bounded or (math.isfinite(seconds) and seconds > 0)
            words = words[1:]
            continue
        if executable == "uv" and words[1:2] == ["run"]:
            words = _after_options(words[2:], _UV_VALUES)
            continue
        if _PYTHON.fullmatch(executable):
            index = 1
            while index < len(words):
                option = words[index]
                if option == "-m":
                    words = words[index + 1 :]
                    break
                if option in {
                    "-c",
                    "--",
                    "-h",
                    "--help",
                    "--help-all",
                    "--help-env",
                    "--help-xoptions",
                    "-V",
                    "--version",
                } or not option.startswith("-"):
                    return False
                index += 2 if option in {"-W", "-X"} else 1
            else:
                return False
            continue
        if executable in {"sh", "bash", "dash", "zsh"}:
            index = 1
            command_string = False
            noexec = False
            while index < len(words):
                option = words[index]
                if option == "--":
                    index += 1
                    break
                if not option.startswith(("-", "+")) or option in {"-", "+"}:
                    break
                if option in {"--help", "--version"}:
                    return False
                if not option.startswith("--"):
                    if "n" in option[1:]:
                        noexec = option.startswith("-")
                    command_string = command_string or "c" in option[1:]
                if option in {"-o", "+o"} and words[index + 1 : index + 2] == [
                    "noexec"
                ]:
                    noexec = option.startswith("-")
                index += 2 if option in {"-o", "-O", "+o", "+O"} else 1
            return (
                command_string
                and not noexec
                and index < len(words)
                and contains_unbounded_stream(words[index], bounded=bounded)
            )
        return not bounded and _stream(words)
    return False


def contains_unbounded_stream(command: str, *, bounded: bool = False) -> bool:
    """Classify executable argv while keeping bounds within their process scope.

    Substitutions in a timeout's arguments run before timeout starts, so they
    inherit only the enclosing shell's bound. A timeout-wrapped shell -c owns
    the bound for every command executed inside that shell.
    """
    try:
        syntax = list(_shell._iter_shell_syntax(command))
        words: list[str] = []
        for kind, raw, _start, _end in syntax:
            if kind in {"word", "redirect"}:
                if any(
                    contains_unbounded_stream(body, bounded=bounded)
                    for body in _substitutions(raw)
                ):
                    return True
            if kind == "word":
                words.append(_shell._shlex_unquote_word(raw) or "")
            elif kind in {"separator", "structure"}:
                if _command_has_unbounded_stream(words, bounded):
                    return True
                words = []
        return _command_has_unbounded_stream(words, bounded)
    except (TypeError, ValueError, RecursionError):
        # Shared hook contract: malformed shell input is handled by syntax preflight.
        return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") not in {None, "Bash"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not contains_unbounded_stream(command):
        return 0
    print("WARN: Streaming command without timeout wrapper.", file=sys.stderr)
    print(
        "  Wrap each streaming invocation with: timeout 60 <stream command>",
        file=sys.stderr,
    )
    print(
        "  (a trailing '| head -N' does not bound a quiet stream — only timeout does)",
        file=sys.stderr,
    )
    print(
        "  Streaming commands without timeout leak exec processes and burn context.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
