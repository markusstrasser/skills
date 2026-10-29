#!/usr/bin/env python3
"""Regression tests for pre-commit-protected-paths.sh's immutable-path rule.

The rule blocks a staged modify, delete, retype or rename of a path matching
PRECOMMIT_PROTECTED_PATHS and allows a new file. On 2026-10-29 a probe showed the rename half
was blind to its source: `git diff --name-only` names a rename by its destination, so renaming
keep.bed to moved.txt passed the guard. The append-only guard closed the same escape on
2026-08-24 (65474a5). Each test stages one change in a throwaway repository and runs the hook.

  uv run --no-project --with pytest python3 -m pytest hooks/test_pre_commit_protected_paths.py -q
"""
import os
import pathlib
import subprocess
import tempfile

HOOK = pathlib.Path(__file__).resolve().parent / "pre-commit-protected-paths.sh"
GUARDS = "PRECOMMIT_PROTECTED_PATHS='\\.bed$'\n"


def run_hook(change) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as t:
        repo = pathlib.Path(t) / "repo"
        config = pathlib.Path(t) / "gitconfig"
        config.write_text("[user]\n\tname = t\n\temail = t@example.invalid\n")
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(config))
        env.pop("GIT_ALLOW_GUARD_BYPASS", None)

        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)

        repo.mkdir()
        git("init", "-q")
        (repo / ".precommit-guards.env").write_text(GUARDS)
        (repo / "keep.bed").write_text("chr1\t1\t2\nchr1\t3\t4\nchr1\t5\t6\n")
        (repo / "notes.txt").write_text("a\nb\nc\nd\n")
        git("add", ".precommit-guards.env", "keep.bed", "notes.txt")
        git("commit", "-qm", "base")
        change(repo, git)
        result = subprocess.run(["bash", str(HOOK)], cwd=repo, env=env, capture_output=True, text=True)
        return result.returncode, result.stderr


def test_renaming_a_protected_file_out_of_the_pattern_is_blocked():
    rc, err = run_hook(lambda repo, git: git("mv", "keep.bed", "moved.txt"))
    assert rc == 1 and "keep.bed" in err, err


def test_renaming_into_a_protected_name_is_blocked():
    rc, err = run_hook(lambda repo, git: git("mv", "notes.txt", "notes.bed"))
    assert rc == 1 and "notes.bed" in err, err


def test_modifying_or_deleting_a_protected_file_is_blocked():
    def modify(repo, git):
        (repo / "keep.bed").write_text("chr1\t1\t9\n")
        git("add", "keep.bed")

    for change in (modify, lambda repo, git: git("rm", "-q", "keep.bed")):
        rc, err = run_hook(change)
        assert rc == 1 and "keep.bed" in err, err


def test_a_new_protected_file_and_an_unprotected_rename_pass():
    def add_and_rename(repo, git):
        (repo / "new.bed").write_text("chr2\t1\t2\n")
        git("add", "new.bed")
        git("mv", "notes.txt", "renamed.txt")

    rc, err = run_hook(add_and_rename)
    assert rc == 0, err
