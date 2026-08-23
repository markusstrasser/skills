#!/usr/bin/env python3
"""Both-polarity tests for pretool-streaming-cli-guard.sh.

The guard fronts every Bash call on both harnesses (Claude Code + codex shim). A false
block on `--help` is how it got routed around on 2026-08-23 (codex 01a01da9: two wasted
turns, the block text recommending a `| head` form the guard itself then rejected).
"""
import json
import pathlib
import subprocess
import sys

HOOK = pathlib.Path(__file__).resolve().parent / "pretool-streaming-cli-guard.sh"

# ---------------------------------------------------------------- MUST BLOCK (rc=2)
FIRES = [
    "uv run modal app logs ap-abc123",
    "modal app logs ap-abc123 | head -100",          # head does not bound a quiet stream
    "tail -f run.log",
    "docker logs -f container",
    "modal container exec ta-xyz bash",
]

# ---------------------------------------------------------------- MUST PASS (rc=0)
CLEAN = [
    "uv run modal app logs --help | head -100",      # the 2026-08-23 false positive
    "uv run modal app logs --help",
    "modal app logs -h",
    "timeout 60 uv run modal app logs ap-abc123",
    "gtimeout 120 tail -f run.log",
    "modal app logs ap-abc123 --timeout 30",
    "git log --oneline -5",                          # no streaming verb at all
    "tail -n 50 run.log",                            # tail without -f
]


def run(cmd: str) -> int:
    payload = json.dumps({"tool_input": {"command": cmd}})
    proc = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True)
    return proc.returncode


def main() -> int:
    bad = []
    for cmd in FIRES:
        if run(cmd) != 2:
            bad.append(f"FALSE NEGATIVE (should block): {cmd}")
    for cmd in CLEAN:
        if run(cmd) != 0:
            bad.append(f"FALSE POSITIVE (should pass): {cmd}")
    for line in bad:
        print(line)
    print(f"{len(FIRES) + len(CLEAN) - len(bad)}/{len(FIRES) + len(CLEAN)} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
