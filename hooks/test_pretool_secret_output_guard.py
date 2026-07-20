#!/usr/bin/env python3
"""Retrodiction and contract tests for the B2 secret-output guard."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest


HOOKS_DIR = Path(__file__).resolve().parent
HOOK = HOOKS_DIR / "pretool-secret-output-guard.py"
DISPATCHER = HOOKS_DIR / "pretool-bash-dispatch.py"
CODEX_SHIM = Path("/Users/alien/Projects/agent-infra/scripts/codex_hook_shim.py")
INCIDENT_COMMAND = "/opt/homebrew/bin/b2 version && /opt/homebrew/bin/b2 account get"


def _payload(command: str, *, tool_name: str = "Bash") -> str:
    return json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})


def _run(script: Path, command: str, *, tool_name: str = "Bash", env=None):
    return subprocess.run(
        [sys.executable, str(script)],
        input=_payload(command, tool_name=tool_name),
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )


@pytest.mark.parametrize(
    "command",
    [
        INCIDENT_COMMAND,
        "b2 account get",
        "env X=1 b2 account get",
        "/usr/bin/env X=1 /opt/homebrew/bin/b2 account get",
        "command b2 account get",
        "b2 account get | jq .accountId",
        "echo safe\nb2 account get",
        'echo "$(b2 account get)"',
        "echo `b2 get-account-info`",
        "b2 get-account-info",
        "python -m b2 account get",
        "/usr/bin/python3 -m b2 get-account-info",
        "uv run python3 -m b2 account get",
        "sh -c 'b2 account get'",
    ],
)
def test_standalone_blocks_secret_output_shapes(command: str) -> None:
    result = _run(HOOK, command)
    assert result.returncode == 2
    assert "live key/token material" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "command",
    [
        "b2 bucket list --json",
        "b2 ls --json b2://",
        "b2 version",
        "echo account and get are unrelated words",
        "echo 'b2 account get is forbidden prose'",
        "echo 'python -m b2 account get is also prose'",
        "echo 'multiline prose:\nb2 account get'",
        "printf '%s' 'x; b2 get-account-info'",
    ],
)
def test_standalone_allows_safe_shapes(command: str) -> None:
    result = _run(HOOK, command)
    assert result.returncode == 0
    assert result.stderr == ""


def test_non_bash_tool_is_ignored() -> None:
    assert _run(HOOK, INCIDENT_COMMAND, tool_name="Write").returncode == 0


def test_dispatcher_runs_guard_first_and_blocks_incident(tmp_path: Path) -> None:
    source = DISPATCHER.read_text(encoding="utf-8")
    manifest = source.split("MANIFEST: list[dict] = [", 1)[1]
    first_entry = manifest.split("},", 1)[0]
    assert "secret-output-guard" in first_entry

    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    result = _run(DISPATCHER, INCIDENT_COMMAND, env=env)
    assert result.returncode == 2
    assert "live key/token material" in result.stderr


def test_dispatcher_allows_safe_b2_probe(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    result = _run(DISPATCHER, "b2 bucket list --json", env=env)
    assert result.returncode == 0
    assert "live key/token material" not in result.stderr


def test_codex_shim_preserves_exit2_and_nonempty_stderr(tmp_path: Path) -> None:
    env = {"CODEX_HOOK_EVENT": "PreToolUse", "HOME": str(tmp_path), "PATH": os.environ["PATH"]}
    inner_command = f"{shlex.quote(sys.executable)} {shlex.quote(str(HOOK))}"
    result = subprocess.run(
        [sys.executable, str(CODEX_SHIM), inner_command],
        input=_payload(INCIDENT_COMMAND),
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    assert result.returncode == 2
    assert result.stderr.strip()
    assert "live key/token material" in result.stderr
    assert result.stdout == ""
