#!/usr/bin/env python3
"""Test pretool-bash-loop-guard — the multiline-control-structure block.

Tests both the sidecar predicate (unit) and the shell wrapper end-to-end (exit 2 = block).
Run: python3 <thisfile>
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SH = HERE / "pretool-bash-loop-guard.sh"

sys.path.insert(0, str(HERE))
from pretool_bash_loop_guard import has_multiline_block  # noqa: E402


def run_sh(command):
    env = {"tool_name": "Bash", "tool_input": {"command": command}}
    r = subprocess.run(["bash", str(SH)], input=json.dumps(env),
                       capture_output=True, text=True, timeout=10)
    return r.returncode


# (command, expected_block, label)
CASES = [
    # BLOCK: genuine multiline control structures
    ("for x in a b; do\n  echo $x\ndone", True, "multiline for"),
    ("while read l; do\n  echo $l\ndone < f", True, "multiline while"),
    ("if [ -f x ]; then\n  echo yes\nfi", True, "multiline if"),
    ('echo "prefix" && for x in a; do\n echo $x\ndone', True, "loop after quoted string"),
    # PASS: single-line forms
    ("for x in a b; do echo $x; done", False, "single-line for"),
    ("if [ -f x ]; then echo yes; fi", False, "single-line if"),
    # PASS: the two known false-positive shapes
    ('git commit -m "goal-confirmation, then\nconfirmed-class fallback"', False,
     "prose 'then' at EOL inside dquotes (2026-07-03 regression)"),
    ("python3 - <<'EOF'\nfor x in y: do_thing()  # do\nthen = 1\nEOF", False,
     "do/then inside heredoc body (2026-06-10 regression)"),
    ("echo 'first do\nthen more'", False, "then at EOL inside squotes"),
    ('echo "escaped \\" quote, then\nstill quoted"', False, "escaped dquote inside dquotes"),
    # PASS: plain commands
    ("git commit -m 'simple message'", False, "plain commit"),
    ("echo done", False, "keyword as word, no newline"),
]


def main():
    failures = 0
    for cmd, expected_block, label in CASES:
        unit = has_multiline_block(cmd)
        rc = run_sh(cmd)
        e2e_block = rc == 2
        ok = unit == expected_block and e2e_block == expected_block
        mark = "✓" if ok else "✗"
        print(f"  {mark} {label} (unit={unit} sh_exit={rc} want_block={expected_block})")
        failures += 0 if ok else 1
    print(f"{len(CASES) - failures}/{len(CASES)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
