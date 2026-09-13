"""Streams need a command-local bound; argument data never counts as execution.

2026-09-13 genomics regressions: a finite rg pattern and a quoted Python docs edit
containing ``modal app logs`` were denied. The old whole-string exemptions also
let an unrelated timeout/help argument hide a real stream in another command.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parent / "pretool-streaming-cli-guard.sh"


def _run(command: str) -> subprocess.CompletedProcess[str]:
    envelope = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        ["bash", str(GUARD)], input=envelope, capture_output=True, text=True, timeout=30
    )


@pytest.mark.parametrize(
    "command",
    [
        "uv run python3 -m modal app logs ap-123",
        'uv run python3 -m modal container exec ta-123 -- sh -c "cat /proc/loadavg"',
        "tail -f /var/log/system.log",
        "docker logs -f worker",
        "modal app logs ap-123 | head -5",
        "sh -c 'modal app logs ap-123'",
        "bash -lc 'tail -f /tmp/log'",
        "bash -c -- 'modal app logs ap-123'",
        "sh -c -e 'tail -f /tmp/log'",
        "bash -n +n -c 'modal app logs ap-123'",
        "sudo -h worker modal app logs ap-123",
        'printf "%s" "$(modal app logs ap-123)"',
        "printf '%s' `docker logs -f worker`",
        'timeout 60 printf "%s" "$(modal app logs ap-123)"',
        "timeout 60 true; modal app logs ap-123",
        "modal app logs ap-123; timeout 60 true",
        "true --help && modal app logs ap-123",
        "modal app logs --help; tail -f /tmp/log",
        "modal app logs ap-123 | sed --help",
        "printf '%s' 'timeout 60'; tail -f /tmp/log",
        "printf '%s' '--timeout 60'; modal app logs ap-123",
        "sh -c 'timeout 60 true; modal app logs ap-123'",
        "timeout 0 modal app logs ap-123",
        "env X=1 command /usr/local/bin/modal app logs ap-123",
        "uv run --project /tmp/project python3 -B -m modal app logs ap-123",
        "if tail -f /tmp/log; then true; fi",
        "modal container exec ta-123 -- sh -c 'tail -f /tmp/log --help'",
        "modal app logs ap-123 --search --help",
        "sh -c 'modal app logs ap-123' --help",
        "echo \"$(echo 'prose'; modal app logs ap-123)\"",
        "tail -f /tmp/log -- --help",
    ],
)
def test_unbounded_stream_blocks(command: str) -> None:
    result = _run(command)
    assert result.returncode == 2
    assert "Streaming command without timeout wrapper" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "timeout 60 uv run python3 -m modal app logs ap-123",
        'timeout 60 uv run python3 -m modal container exec ta-123 -- sh -c "cat /proc/loadavg"',
        "uv run python3 -m modal app logs --help",
        "timeout --signal TERM --kill-after 5s 1m modal app logs ap-123",
        "gtimeout -- 30s docker logs -f worker",
        "timeout 60 bash -lc 'modal app logs ap-123; tail -f /tmp/log'",
        "bash -lc 'timeout 60 modal app logs ap-123; true'",
        "printf '%s' \"$(timeout 60 modal app logs ap-123)\"",
        "tail -f /tmp/log --help",
        "docker logs --help",
        "env -u DEBUG timeout 60 uv run --no-sync python3 -m modal app logs ap-123",
    ],
)
def test_bounded_or_static_stream_passes(command: str) -> None:
    assert _run(command).returncode == 0


def test_heredoc_body_mentioning_a_stream_is_not_a_stream() -> None:
    command = (
        "S=/tmp/x; cat > $S/brief.md <<'EOF'\n"
        "# Lane brief\n"
        "the parent had to `modal container exec` into the container and read `ps`\n"
        "run `modal app logs <id>` only with a bound\n"
        "EOF\n"
        "ls $S | head -3"
    )
    result = _run(command)
    assert result.returncode == 0, result.stderr


def test_real_stream_after_a_heredoc_still_blocks() -> None:
    command = "cat > /tmp/note.md <<'EOF'\nplain text\nEOF\nuv run python3 -m modal app logs ap-123"
    assert _run(command).returncode == 2


@pytest.mark.parametrize(
    "command",
    [
        "rg -n 'streaming.cli|streaming guard|heredoc|modal app logs' "
        "/Users/alien/.codex/memories/MEMORY.md",
        "rg -n 'modal app logs' hooks",
        'printf "%s" "modal app logs ap-123"',
        "printf '%s' 'tail -f /tmp/log; modal app logs ap-123'",
        "uv run --no-sync python3 -c 'from pathlib import Path\n"
        'path = Path("notes.md")\n'
        'path.write_text("Use `modal app logs <id>` for runtime evidence.")'
        "'",
        "printf '%s' '$(modal app logs ap-123)'",
        "printf '%s' 'sh -c \"modal app logs ap-123\"'",
        "echo safe # modal app logs ap-123",
        "rg modal app logs README.md",
        "echo safe >'modal app logs'",
        "command -v modal app logs",
        "tail -n 5 /tmp/log",
        "docker logs worker",
        "docker logs -- -f",
        "docker logs --since -f worker",
        "python3 --help -m modal app logs ap-123",
        "uv run python3 -V -m modal app logs ap-123",
        "bash -n -c 'modal app logs ap-123'",
        "bash -o noexec -c 'modal app logs ap-123'",
    ],
)
def test_argument_text_and_finite_commands_pass(command: str) -> None:
    result = _run(command)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "payload", ["not json", "null", "{}", '{"tool_input":{"command":123}}']
)
def test_invalid_hook_input_keeps_fail_open_contract(payload: str) -> None:
    result = subprocess.run(
        ["bash", str(GUARD)], input=payload, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0
    assert result.stderr == ""
