"""Behaviour matrix for the protected-data guards (data, append-only, archive).

They fail CLOSED since 2026-10-21 (constitution P10): an internal error exits 2. These
cases pin the normal flow so the stricter trap can't start blocking legitimate calls.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent


def run(hook: str, payload: dict | str, env: dict[str, str] | None = None) -> int:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run(
        ["bash", str(HOOKS / hook)],
        input=body,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        timeout=30,
    )
    return proc.returncode


def write(path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit(path: str, old: str, new: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": old, "new_string": new}}


def bash(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


@pytest.mark.parametrize(
    "payload,want",
    [
        (write("/r/datasets/a.csv", "x"), 2),
        (write("/r/out/t.parquet", "x"), 2),
        (write("/r/src/app.py", "x"), 0),
        (bash("ls datasets/"), 0),
        ("not json at all", 0),
    ],
)
def test_data_guard(payload, want):
    assert run("pretool-data-guard.sh", payload) == want


@pytest.fixture
def log(tmp_path: Path) -> Path:
    p = tmp_path / "improvement-log.md"
    p.write_text("a\nb\nc\n")
    return p


def test_append_only_matrix(log: Path, tmp_path: Path):
    env = {"APPENDONLY_PATHS": r"improvement-log\.md"}
    hook = "pretool-append-only-guard.sh"
    assert run(hook, write(str(log), "a\nb\nc\nd\n"), env) == 0  # grow
    assert run(hook, write(str(log), "a\n"), env) == 2  # shrink
    assert run(hook, write(str(tmp_path / "new" / "improvement-log.md"), "a\n"), env) == 0  # new file
    assert run(hook, edit(str(log), "c", "c\nd"), env) == 0  # append
    assert run(hook, edit(str(log), "a\nb\nc", "a"), env) == 2  # shrink
    assert run(hook, write(str(tmp_path / "other.md"), ""), env) == 0  # unprotected path
    assert run(hook, bash("cat improvement-log.md"), env) == 0
    assert run(hook, write(str(log), "a\n"), {}) == 0  # guard not configured


def test_append_only_unparseable_input_blocks(log: Path):
    env = {"APPENDONLY_PATHS": r"improvement-log\.md"}
    broken = '{"tool_name": "Edit", "tool_input": {"file_path": "%s", "old_string": ' % log
    assert run("pretool-append-only-guard.sh", broken, env) == 2


@pytest.mark.parametrize(
    "cmd,want",
    [
        ("git mv research/memo.md archive/memo.md", 2),
        ("git mv research/memo.md archive/ # ARCHIVAL-REVIEWED", 0),
        ("git mv src/a.py src/b.py", 0),
        ("ls archive/", 0),
    ],
)
def test_archive_guard(cmd, want):
    assert run("pretool-archive-guard.sh", bash(cmd), {"ARCHIVE_PROTECTED": "research/"}) == want
