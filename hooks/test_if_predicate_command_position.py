"""The gate predicate must see git at any COMMAND POSITION, not only string start.

`_if_matches` fnmatched `Bash(git*)` against the whole lstripped command, so every
git-predicated gate fired on `git add -A` and was silently skipped on
`cd /repo; git add -A`. That is not an edge case: `cd <repo>; git ...` is what any
agent using absolute paths writes, so the `git add -A` ban, the destructive-ref
guard, the multiagent-commit guard and the masked-commit guard were all bypassable
by the default phrasing. Demonstrated live 2026-08-18 (genomics):

    git add -A --dry-run            -> BLOCKED
    cd /repo; git add -A --dry-run  -> ran unblocked

The DATA cases matter as much as the command cases: widening the predicate without
stripping heredocs and quotes re-opens the 2026-07-04 false-positive class, where a
brief containing "git commit" blocked the write that would have created it. That
regression fired during this change and is pinned below.

Run: uv run --no-project python3 hooks/test_if_predicate_command_position.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS))

_spec = importlib.util.spec_from_file_location("dispatch", HOOKS / "pretool-bash-dispatch.py")
assert _spec and _spec.loader
_dispatch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dispatch)

GIT = "Bash(git*)"
GIT_COMMIT = "Bash(git commit*)"
_ADD_ALL = "git add" + " -A"  # split so this file's own source is not a live example
_COMMIT = "git commit" + " -m x"

CASES: list[tuple[str, str, str, bool]] = [
    # (name, command, predicate, expect_match)
    ("leading git still matches", _ADD_ALL, GIT, True),
    ("after cd;", f"cd /r; {_ADD_ALL}", GIT, True),
    ("after &&", f"cd /r && {_ADD_ALL}", GIT, True),
    ("after newline", f"cd /r\n{_ADD_ALL}", GIT, True),
    ("after ||", f"false || {_ADD_ALL}", GIT, True),
    ("two-word predicate after cd;", f"cd /r; {_COMMIT}", GIT_COMMIT, True),
    ("non-git command", "ls -la", GIT, False),
    ("cd without git", "cd /r; ls", GIT, False),
    # DATA, not commands — these must never satisfy the predicate.
    ("quoted single", f"echo '{_ADD_ALL}' > n.txt", GIT, False),
    ("quoted double", f'echo "{_ADD_ALL}" > n.txt', GIT, False),
    ("heredoc body", f"cat > b.md <<'EOF'\n{_ADD_ALL}\nEOF", GIT, False),
    ("heredoc body multiline", f"cat > b.md <<'EOF'\nplease do not\n{_COMMIT}\nEOF", GIT, False),
]


def main() -> int:
    failures = 0
    for name, command, predicate, expected in CASES:
        got = _dispatch._if_matches(predicate, command)
        ok = got is expected
        failures += not ok
        print(("PASS" if ok else "FAIL"), f"{name:32s} got={got} want={expected}")
    print("ALL PASS" if not failures else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
