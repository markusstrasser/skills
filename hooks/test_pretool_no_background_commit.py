"""Behavior tests for pretool-no-background-commit.sh.

Covers the 2026-07-04 false-positive class: 'git commit' as heredoc/prose DATA
(a codex brief saying "Do NOT git commit") must not block, while real background
commits — including chained and after-heredoc — must. Run:
  uv run --no-project python3 hooks/test_pretool_no_background_commit.py
"""

import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pretool-no-background-commit.sh")

CASES = [
    # (name, command, run_in_background, expect_block)
    ("real bg commit", "git add x && git commit -m 'y'", True, True),
    ("real bg commit chained", "make build && git commit -m done", True, True),
    ("heredoc mention (2026-07-04 false positive)",
     "cat > brief.md <<'EOF'\nDo NOT git commit anything.\nEOF\ncodex exec --full-auto 'x'", True, False),
    ("prose mention in echo", "echo 'never git commit here' > note.txt", True, False),
    ("fg commit (no bg)", "git commit -m ok", False, False),
    ("bg commit after heredoc", "cat > b.md <<'EOF'\nhello\nEOF\ngit commit -m real", True, True),
    ("pipe mask fg", "git commit -m x 2>&1 | tail -2", False, True),
    ("dry run bg", "git commit --dry-run", True, False),
]


def main() -> None:
    fails = 0
    for name, cmd, bg, expect in CASES:
        payload = json.dumps({"tool_input": {"command": cmd, "run_in_background": bg}})
        r = subprocess.run(["bash", HOOK], input=payload, capture_output=True, text=True)
        blocked = r.returncode == 2
        ok = blocked == expect
        fails += not ok
        print(("✓" if ok else "✗"), name, f"(blocked={blocked}, expected={expect})")
    print("ALL PASS" if not fails else f"{fails} FAILURES")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
