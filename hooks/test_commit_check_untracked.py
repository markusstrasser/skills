#!/usr/bin/env python3
"""Regression tests for commit-check-parse.py's untracked-pathspec warning.

`git commit -- <dir>` takes tracked files only, so new files in a directory that already holds a
tracked one are left out without a message. On 2026-09-25 immigration-research 7ec7144 named a lane
directory whose results, inventory and two tests were all new; none landed (fixed in ed1b623).
The parser now warns before such a commit. Each test builds a throwaway repository and points HOME at
a temporary directory, so ~/.claude/commit-check-log.jsonl is untouched.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

PARSER = pathlib.Path(__file__).resolve().parent / "commit-check-parse.py"
MESSAGE = " <<'EOF'\n[x] Add the lane — cited\n\nBody line.\nEOF"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


def lane_repo(root: pathlib.Path) -> pathlib.Path:
    repo = root / "repo"
    (repo / "lane" / "derived").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / ".gitignore").write_text("_cache/\n")
    (repo / "lane" / "BRIEF.md").write_text("brief\n")
    git(repo, "add", ".gitignore", "lane/BRIEF.md")
    git(repo, "commit", "-q", "-m", "init")
    (repo / "lane" / "RESULT.md").write_text("result\n")
    (repo / "lane" / "derived" / "out.csv").write_text("a\n")
    (repo / "lane" / "_cache").mkdir()
    (repo / "lane" / "_cache" / "raw.csv").write_text("ignored\n")
    return repo


def parse(command: str, cwd: pathlib.Path, home: pathlib.Path) -> str:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    r = subprocess.run([sys.executable, str(PARSER)], input=payload, capture_output=True, text=True,
                       cwd=str(cwd), env=dict(os.environ, HOME=str(home)))
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def setup(t: str):
    root = pathlib.Path(t)
    (root / "home" / ".claude").mkdir(parents=True)
    return lane_repo(root), root, root / "home"


def test_cd_pathspec_commit_names_the_untracked_files():
    with tempfile.TemporaryDirectory() as t:
        repo, root, home = setup(t)
        out = parse(f"cd {repo} && git commit -q -F - -- lane" + MESSAGE, root, home)
        assert out.startswith("WARN:"), out
        assert "2 untracked file(s)" in out
        assert "lane/RESULT.md" in out and "lane/derived/out.csv" in out
        assert "raw.csv" not in out  # ignored files are not flagged


def test_dash_c_commit_with_a_variable_pathspec():
    with tempfile.TemporaryDirectory() as t:
        repo, root, home = setup(t)
        out = parse(f'P="lane"; git -C {repo} commit -q -F - -- $P/derived' + MESSAGE, root, home)
        assert out.startswith("WARN:1 untracked file(s)"), out
        assert "lane/derived/out.csv" in out


def test_staged_files_are_not_flagged():
    with tempfile.TemporaryDirectory() as t:
        repo, root, home = setup(t)
        git(repo, "add", "lane/RESULT.md", "lane/derived/out.csv")
        out = parse(f"cd {repo} && git commit -q -F - -- lane" + MESSAGE, root, home)
        assert "untracked" not in out, out


def test_commit_without_pathspecs_is_not_checked():
    with tempfile.TemporaryDirectory() as t:
        repo, root, home = setup(t)
        out = parse(f"cd {repo} && git commit -q -F -" + MESSAGE, root, home)
        assert "untracked" not in out, out
        assert parse(f"git -C {repo} status", root, home) == "SKIP"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"✓ {name}")
