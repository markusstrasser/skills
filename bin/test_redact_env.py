"""redact-env masks credential shapes and passes each line through as it arrives."""

from __future__ import annotations

import select
import subprocess
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "redact-env"


def test_each_line_arrives_before_the_input_ends() -> None:
    # A watcher pipes a live log through this filter; a block-buffered sed held the lines
    # until its buffer filled, so the watcher saw nothing (2026-11-02).
    process = subprocess.Popen(
        [str(TOOL)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
    )
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write("fetch: 22.6 GB committed TOKEN=abc123\n")
        process.stdin.flush()
        ready, _, _ = select.select([process.stdout], [], [], 5)
        assert ready, "no line within 5 s while the input stayed open"
        assert process.stdout.readline() == "fetch: 22.6 GB committed TOKEN=<redacted>\n"
    finally:
        process.kill()
        process.wait()


def test_masks_environment_tokens_and_bare_keys_but_keeps_flag_values() -> None:
    result = subprocess.run(
        [str(TOOL)],
        input="python3 run.py API_KEY=s3cret --label=f2 sk-ant-abcdefgh12345678\n",
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "python3 run.py API_KEY=<redacted> --label=f2 <redacted-key>\n"
