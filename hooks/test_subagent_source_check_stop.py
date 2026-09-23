"""Regression: subagent-source-check-stop.sh must put every block reason on stderr.

On exit 2 Claude Code feeds only stderr back to the blocked agent. A reason printed to stdout
arrives as "No stderr output", so the agent retries blind (two researcher runs, 2026-09-23).
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).with_name("subagent-source-check-stop.sh")


def test_every_block_reason_is_written_to_stderr():
    lines = HOOK.read_text().splitlines()
    blocks = [i for i, line in enumerate(lines) if line.strip() == "exit 2"]
    assert blocks, "hook no longer blocks; update this test"
    for i in blocks:
        prev = lines[i - 1].strip()
        assert prev.startswith("echo") and prev.endswith(">&2"), f"line {i}: {prev}"


def test_empty_output_block_reaches_the_agent():
    # Isolated HOME: the empty-output path exits before the log write and the taxonomy read.
    env = dict(os.environ, HOME=tempfile.mkdtemp())
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"last_assistant_message": "x"}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 2
    assert "No research output" in result.stderr
    assert result.stdout == ""
