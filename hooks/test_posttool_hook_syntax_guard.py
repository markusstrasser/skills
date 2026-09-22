#!/usr/bin/env python3
"""Test posttool-hook-syntax-guard.sh.

Pins the 2026-09-22 fix: the guard used to hand the whole PostToolUse envelope to python
through an environment variable, so an Edit of a large file that merely mentions "hooks/"
blew past ARG_MAX and python3 died with "Argument list too long" (23 of 23 logged runs,
2026-09-15..22). Only the edited path travels now: a parse error in a real hook script
still blocks (exit 2), a clean one passes, and a multi-megabyte envelope no longer matters.

Run: python3 <thisfile>
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent / "posttool-hook-syntax-guard.sh"
CHECKS = []


def check(label, ok):
    CHECKS.append((label, ok))
    print(f"  {'✓' if ok else '✗'} {label}")


def run(file_path, pad_bytes=0):
    envelope = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "a", "new_string": "b"},
        "tool_response": {"filePath": file_path, "originalFile": "x" * pad_bytes},
    }
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(envelope), capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        hooks = Path(td) / "hooks"
        hooks.mkdir()
        good = hooks / "good.sh"
        good.write_text("#!/usr/bin/env bash\necho ok\n")
        bad = hooks / "bad.sh"
        bad.write_text("#!/usr/bin/env bash\necho 'unterminated\n")
        badpy = hooks / "bad.py"
        badpy.write_text("def f(:\n    pass\n")
        other = Path(td) / "notes.md"
        other.write_text("see hooks/x.sh\n")

        r = run(str(good))
        check("clean hook passes silently", r.returncode == 0 and not r.stderr.strip())
        r = run(str(bad))
        check("broken shell hook blocks with exit 2", r.returncode == 2 and "BLOCKED (hook-syntax)" in r.stderr)
        r = run(str(badpy))
        check("broken python hook blocks with exit 2", r.returncode == 2 and "BLOCKED (hook-syntax)" in r.stderr)
        big = 3 * 1024 * 1024
        r = run(str(good), pad_bytes=big)
        check("3 MB envelope no longer kills python (was: Argument list too long)",
              r.returncode == 0 and "Argument list too long" not in r.stderr)
        r = run(str(bad), pad_bytes=big)
        check("broken hook still blocks under a 3 MB envelope", r.returncode == 2)
        r = run(str(other))
        check("non-hook path is ignored", r.returncode == 0 and not r.stdout and not r.stderr.strip())
    failed = [l for l, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
