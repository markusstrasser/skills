#!/usr/bin/env python3
"""Test pretool-bash-background-ampersand.py — the `&`+run_in_background guard.

Exit 2 = block (the bug); exit 0 = pass. Run: uv run python3 <thisfile> (or python3).
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "pretool-bash-background-ampersand.py"


def run(tool_name, command, run_in_background):
    env = {"tool_name": tool_name,
           "tool_input": {"command": command, "run_in_background": run_in_background}}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(env),
                       capture_output=True, text=True, timeout=10)
    return r.returncode


# (tool_name, command, run_in_background, expected_exit, label)
CASES = [
    # BLOCK: backgrounding & with run_in_background
    ("Bash", "llmx chat -m gpt-5.5 -o out.md 'x' &", True, 2, "trailing &"),
    ("Bash", "foo & echo done", True, 2, "& then echo"),
    ("Bash", "sleep 5 &", True, 2, "sleep &"),
    ("Bash", "a & b & c", True, 2, "multiple &"),
    # PASS: operators/redirects that contain & but do not background
    ("Bash", "foo && bar", True, 0, "&& logical-and"),
    ("Bash", "foo 2>&1", True, 0, "2>&1 redirect"),
    ("Bash", "foo > log 2>&1", True, 0, "redirect both"),
    ("Bash", "foo &> log", True, 0, "&> redirect"),
    ("Bash", "foo |& bar", True, 0, "|& pipe-both"),
    ("Bash", 'echo "a & b"', True, 0, "& inside dquotes"),
    ("Bash", "echo 'x & y'", True, 0, "& inside squotes"),
    ("Bash", "curl 'http://x?a=1&b=2'", True, 0, "& in quoted URL"),
    ("Bash", "foo | bar", True, 0, "pipe only"),
    ("Bash", "foo", True, 0, "plain cmd"),
    # PASS: not the bug — manual & without run_in_background is the caller's choice
    ("Bash", "foo &", False, 0, "& but bg=false"),
    # PASS: non-Bash tool
    ("Write", "foo &", True, 0, "non-Bash tool"),
]


def main():
    fails = []
    for tool, cmd, bg, expected, label in CASES:
        got = run(tool, cmd, bg)
        ok = got == expected
        print(f"  {'ok ' if ok else 'FAIL'}: {label:24} expected {expected} got {got}")
        if not ok:
            fails.append(label)
    if fails:
        print(f"\nFAILED: {fails}")
        sys.exit(1)
    print(f"\nall {len(CASES)} cases pass")
    sys.exit(0)


if __name__ == "__main__":
    main()
