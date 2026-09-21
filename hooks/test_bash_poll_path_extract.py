#!/usr/bin/env python3
"""Test posttool-bash-poll.sh path extraction.

Pins the 2026-09-18 extractor fix: a RELATIVE path (`ls infra/x/y.csv`) must not
yield the suffix token `/x/y.csv`, which collapsed every distinct command under one
tree onto one counter ("Polled /immigration-fiscal 91x", immigration-research,
four false blocks in one session). Absolute-path polling must still block at 15.

Run: python3 <thisfile>
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "posttool-bash-poll.sh"
CHECKS = []


def check(label, ok):
    CHECKS.append((label, ok))
    print(f"  {'✓' if ok else '✗'} {label}")


def run(cmd, scope):
    # The tracker is scoped by the envelope's agent_id (lib_hook_identity.sh), then this PID.
    envelope = {"tool_input": {"command": cmd}, "agent_id": scope}
    return subprocess.run([str(HOOK)], input=json.dumps(envelope), capture_output=True, text=True)


def main():
    scope = "testpoll"
    tracker = Path(f"/tmp/claude-bash-poll-tracker-{scope}-{os.getpid()}")
    tracker.unlink(missing_ok=True)
    try:
        # Sixteen distinct relative-path commands: no shared token, never blocked.
        codes = [run(f"ls infra/immigration-fiscal/lane_{i}/derived/estimates.csv | head -3", scope).returncode
                 for i in range(16)]
        check("16 distinct relative paths never block", all(c == 0 for c in codes))
        check("relative paths leave the tracker empty", not tracker.exists() or tracker.read_text().strip() == "")
        # Genuine poll of one absolute file still blocks on the 15th call.
        target = "/tmp/some-long-background-output-file.log"
        codes = [run(f"tail -5 {target}", scope).returncode for _ in range(15)]
        check("absolute-path poll blocks at 15", codes[-1] == 2 and all(c == 0 for c in codes[:9]))
        # A quoted absolute path is extracted without the quote.
        run(f'cat "{target}"', scope)
        lines = tracker.read_text().split()
        check("quoted absolute path extracted cleanly", lines[-1] == target)
        # A redirect target is a write, not a poll.
        code = run(f"cat >> {target} <<'EOF'\nx\nEOF", scope).returncode
        check("redirect target not counted", code == 0)
    finally:
        tracker.unlink(missing_ok=True)
    failed = [l for l, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
