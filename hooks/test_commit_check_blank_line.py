#!/usr/bin/env python3
"""Regression tests for commit-check-parse.py's blank-line-after-subject block.

Git joins every line before the first blank one into the subject. On 2026-09-28 two heredoc
commits (skills c8c2f97, immigration-research f437563) started their body on line 2 and got
run-on subjects; the amend that would have fixed the second was blocked in the shared checkout.
Each test runs the parser in a throwaway repository with HOME pointed at a temporary directory,
so ~/.claude/commit-check-log.jsonl is untouched.

  uv run --no-project --with pytest python3 -m pytest hooks/test_commit_check_blank_line.py -q
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

PARSER = pathlib.Path(__file__).resolve().parent / "commit-check-parse.py"


def parse(command: str) -> str:
    with tempfile.TemporaryDirectory() as t:
        root = pathlib.Path(t)
        (root / "home" / ".claude").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root / "repo")], check=True)
        payload = json.dumps({"tool_input": {"command": command}, "cwd": str(root / "repo")})
        r = subprocess.run([sys.executable, str(PARSER)], input=payload, capture_output=True,
                           text=True, cwd=str(root / "repo"), env=dict(os.environ, HOME=str(root / "home")))
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()


def test_body_on_line_two_is_blocked():
    out = parse("git commit -q -F - -- a.txt <<'EOF'\n[x] Add a — why\nBody on line two.\nEOF")
    assert out.startswith("BLOCK:Line 2"), out


def test_blank_line_after_subject_passes():
    out = parse("git commit -q -F - -- a.txt <<'EOF'\n[x] Add a — why\n\nBody.\nEOF")
    assert not out.startswith("BLOCK"), out


def test_subject_only_passes():
    out = parse("git commit --only -q -F - -- a.txt <<'EOF'\n[x] Add a — why\nEOF")
    assert not out.startswith("BLOCK"), out


def test_an_earlier_heredoc_is_not_read_as_the_message():
    cmd = ("cat > f.md <<'EOF'\nline one\nline two\nEOF\n"
           "git commit -q -F - -- f.md <<'EOF'\n[x] Add f — why\n\nBody.\nEOF")
    assert not parse(cmd).startswith("BLOCK"), cmd


def test_amend_message_is_checked_too():
    out = parse("git commit --amend --only -q -F - <<'EOF'\n[x] Fix — why\nBody.\nEOF")
    assert out.startswith("BLOCK:Line 2"), out
