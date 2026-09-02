"""pretool-streaming-cli-guard.sh — streams need a timeout; heredoc text is not a stream."""

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
