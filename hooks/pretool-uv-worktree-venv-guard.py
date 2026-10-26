#!/usr/bin/env python3
# Gov-ID: hook:uv-worktree-venv-guard
# goal: stop `uv run` building a second ~700 MB .venv inside a linked git worktree
# verifier: test_pretool_uv_worktree_venv_guard.py
# blast_radius: shared (PreToolUse Bash; fires only when `uv run` resolves into a linked worktree)
"""pretool-uv-worktree-venv-guard.py — a linked worktree of a virtual project shares main's venv.

`uv run` creates `<project>/.venv` when the project has none. In a linked worktree that is a
second ~700 MB environment: genomics lanes and their parent built four in 24 hours
(2026-10-26/27), one inside a peer session's suite worktree. When the project is virtual (uv
installs no package for it, so nothing in the venv points back at main's source) and the
worktree's pyproject.toml and uv.lock equal the main checkout's, the main .venv is the right
environment: the gate prefixes each such `uv run` with `env UV_PROJECT_ENVIRONMENT=<main>/.venv
UV_NO_SYNC=1` (env, so `exec`, `nohup` or `timeout` before it still work) and says so. A packaged project, a worktree whose dependency files differ, or one
that already has its own .venv passes untouched: there a separate environment is correct.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from pathlib import Path

_UV_RUN = re.compile(r"\buv\s+run\b")
_NO_PROJECT_ENV = re.compile(r"--(?:no-project|isolated|script)\b")
_WORD = r"('[^']*'|\"[^\"]*\"|[^\s;&|()<>]+)"
_ASSIGN = re.compile(r"(?:^|(?<=[\s;&|(]))([A-Za-z_][A-Za-z0-9_]*)=" + _WORD)
_CD = re.compile(r"(?:^|(?<=[\s;&|(]))cd\s+" + _WORD)
_DIR_FLAG = re.compile(r"--(?:directory|project)(?:=|\s+)" + _WORD)
_SEGMENT_END = re.compile(r"&&|\|\||[;|\n]")
_HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_VAR = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


def _masked(cmd: str) -> list[bool]:
    """True at every offset inside quotes or a heredoc body, where no command starts."""
    mask = [False] * len(cmd)
    quote = ""
    for index, char in enumerate(cmd):
        if quote:
            mask[index] = True
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
            mask[index] = True
    for match in _HEREDOC.finditer(cmd):
        if mask[match.start()]:
            continue
        body_start = cmd.find("\n", match.end())
        if body_start < 0:
            continue
        cursor = body_start + 1
        while cursor < len(cmd):
            line_end = cmd.find("\n", cursor)
            line_end = len(cmd) if line_end < 0 else line_end
            line = cmd[cursor:line_end]
            if (line.lstrip("\t") if match.group(1) else line) == match.group(3):
                break
            cursor = line_end + 1
        for index in range(body_start, min(cursor, len(cmd))):
            mask[index] = True
    return mask


def _resolve(word: str, base: Path | None, names: dict[str, str]) -> Path | None:
    text = word[1:-1] if word[:1] in "'\"" and word[-1:] == word[:1] else word
    if word[:1] != "'":
        text = _VAR.sub(lambda m: names.get(m.group(1) or m.group(2), m.group(0)), text)
    if "$" in text or "`" in text or text == "-":
        return None
    if text == "~" or text.startswith("~/"):
        text = os.path.expanduser(text)
    path = Path(text)
    if not path.is_absolute():
        if base is None:
            return None
        path = base / path
    return path.resolve()


def _linked_worktree_project(start: Path) -> tuple[Path, Path] | None:
    """(project root inside a linked worktree, its counterpart in the main checkout)."""
    project = None
    for directory in [start, *start.parents]:
        if project is None and (directory / "pyproject.toml").is_file():
            project = directory
        dot_git = directory / ".git"
        if dot_git.is_dir():
            return None
        if dot_git.is_file():
            text = dot_git.read_text(errors="replace").strip()
            if project is None or not text.startswith("gitdir:"):
                return None
            gitdir = (directory / text.split(":", 1)[1].strip()).resolve()
            if gitdir.parent.name != "worktrees":
                return None  # a submodule, not a linked worktree
            commondir = gitdir / "commondir"
            common = (
                (gitdir / commondir.read_text().strip()).resolve()
                if commondir.is_file()
                else gitdir.parent.parent
            )
            return project, common.parent / project.relative_to(directory)
    return None


def _is_package(project: Path) -> bool:
    try:
        data = tomllib.loads((project / "pyproject.toml").read_text())
    except Exception:
        return True  # unreadable: assume uv installs it, so never share
    declared = (data.get("tool") or {}).get("uv", {}).get("package")
    return bool(declared) if declared is not None else "build-system" in data


def _same_bytes(left: Path, right: Path) -> bool:
    if left.exists() != right.exists():
        return False
    return not left.exists() or left.read_bytes() == right.read_bytes()


def shared_env(project: Path, main_project: Path) -> Path | None:
    """The main checkout's venv when this worktree project can safely use it."""
    shared = main_project / ".venv"
    if (project / ".venv").exists() or not shared.is_dir() or _is_package(project):
        return None
    if not all(_same_bytes(project / n, main_project / n) for n in ("pyproject.toml", "uv.lock")):
        return None
    return shared


def rewrite(cmd: str, cwd: str) -> tuple[str, list[str]] | None:
    """The command with each worktree-bound `uv run` prefixed, plus the venvs used; None if unchanged."""
    if "uv" not in cmd or "UV_PROJECT_ENVIRONMENT" in cmd or not _UV_RUN.search(cmd):
        return None
    mask = _masked(cmd)
    events: list[tuple[int, str, re.Match]] = []
    for kind, pattern in (("assign", _ASSIGN), ("cd", _CD), ("uv", _UV_RUN)):
        events.extend((m.start(), kind, m) for m in pattern.finditer(cmd) if not mask[m.start()])
    names: dict[str, str] = {}
    here: Path | None = Path(cwd).resolve() if cwd else None
    inserts: list[tuple[int, Path]] = []
    for start, kind, match in sorted(events, key=lambda event: event[0]):
        if kind == "assign":
            value = match.group(2)
            names[match.group(1)] = value[1:-1] if value[:1] in "'\"" else value
        elif kind == "cd":
            here = _resolve(match.group(1), here, names)
        elif here is not None:
            end = _SEGMENT_END.search(cmd, match.end())
            segment = cmd[match.end() : end.start() if end else len(cmd)]
            if _NO_PROJECT_ENV.search(segment):
                continue
            flag = _DIR_FLAG.search(segment)
            target = _resolve(flag.group(1), here, names) if flag else here
            located = _linked_worktree_project(target) if target is not None else None
            shared = shared_env(*located) if located else None
            if shared is not None:
                inserts.append((start, shared))
    if not inserts:
        return None
    out = cmd
    for start, shared in sorted(inserts, reverse=True):
        out = f"{out[:start]}env UV_PROJECT_ENVIRONMENT={shared} UV_NO_SYNC=1 {out[start:]}"
    return out, sorted({str(shared) for _, shared in inserts})


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    tool_input = payload.get("tool_input") or {}
    try:
        result = rewrite(tool_input.get("command", "") or "", payload.get("cwd") or "")
    except Exception:
        return 0
    if result is None:
        return 0
    command, envs = result
    note = (
        "uv-worktree-venv-guard: `uv run` here would build a separate ~700 MB .venv inside a "
        f"linked worktree, so it now runs with UV_PROJECT_ENVIRONMENT={', '.join(envs)} "
        "UV_NO_SYNC=1 (same pyproject.toml and uv.lock as the main checkout). Pass "
        "UV_PROJECT_ENVIRONMENT yourself, or `uv sync` in the worktree, to choose otherwise."
    )
    updated = dict(tool_input)
    updated["command"] = command
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "updatedInput": updated, "additionalContext": note}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
