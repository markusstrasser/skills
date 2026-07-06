"""Behavior test for commit-check-parse.py Native-First advisory scope.

The advisory must fire on a newly-added capability script (scripts/*.py) with no
Native-First: trailer, and must NOT fire on newly-added test scripts — matching
the native_first grader's population (evals/graders/governance/native_first.py),
which excludes tests/, test_*, *_test.py, conftest.py. Run:
  uv run --no-project python3 hooks/test_commit_check_native_first.py
"""

import json
import os
import subprocess
import sys
import tempfile

PARSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit-check-parse.py")


def _run(repo, staged_paths, msg):
    """Stage new files in a temp git repo, run the parse hook, return stdout."""
    # Fresh index each case — unstage everything, then stage this case's paths.
    subprocess.run(
        ["git", "-C", repo, "rm", "-rf", "--cached", "--ignore-unmatch", "."],
        capture_output=True,
    )
    for p in staged_paths:
        full = os.path.join(repo, p)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("# new\n")
        subprocess.run(["git", "-C", repo, "add", p], check=True)
    payload = json.dumps({"tool_input": {"command": f'git commit -m "{msg}"'}})
    r = subprocess.run(
        ["python3", PARSE], input=payload, capture_output=True, text=True, cwd=repo
    )
    return r.stdout


CASES = [
    # (name, staged_paths, commit_msg, expect_fire)
    ("capability script fires", ["scripts/worktree_gc.py"],
     "[hooks] Add worktree gc — why", True),
    ("test_ prefix excluded", ["scripts/test_worktree_gc.py"],
     "[hooks] Add test — why", False),
    ("tests/ dir excluded", ["scripts/tests/test_x.py"],
     "[hooks] Add test — why", False),
    ("_test suffix excluded", ["scripts/worktree_gc_test.py"],
     "[hooks] Add test — why", False),
    ("conftest excluded", ["scripts/conftest.py"],
     "[hooks] Add fixture — why", False),
    ("trailer present suppresses", ["scripts/foo.py"],
     "[hooks] Add foo — why\n\nNative-First: no just recipe fits", False),
    ("non-scripts .py ignored", ["src/mod.py"],
     "[hooks] Add mod — why", False),
]


def main():
    fails = 0
    with tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
        subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
        for name, paths, msg, expect in CASES:
            out = _run(repo, paths, msg)
            fired = "add Native-First: trailer" in out
            ok = fired == expect
            fails += not ok
            print(("✓" if ok else "✗"), name, f"(fired={fired}, expected={expect})")
    print("ALL PASS" if not fails else f"{fails} FAILURES")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
