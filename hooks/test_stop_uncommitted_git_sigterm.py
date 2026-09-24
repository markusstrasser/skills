"""stop-uncommitted-warn.sh must stop a timed-out git with SIGTERM, not SIGKILL.

subprocess.run(timeout=) SIGKILLs the child. Git cannot catch SIGKILL, so a git that
holds .git/index.lock when the timeout fires leaves the lock behind, and every later
git write in the repo fails (heli 2026-09-24: a 0-byte index.lock with no holder
blocked git for ~10 minutes under a CPU saturated by a Blender render). On SIGTERM git
deletes its own lock files. The hook routes every git call through `_git_run`.

The positive control reproduces the leak with plain subprocess.run, so a pass here
cannot come from a setup in which git never held the lock.

Run: uv run python3 -m pytest hooks/test_stop_uncommitted_git_sigterm.py -q
"""

from __future__ import annotations

import ast
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent / "stop-uncommitted-warn.sh"
TERMINATOR = "' 2>/dev/null)"


def _embedded_body() -> str:
    text = HOOK.read_text()
    start = text.index("python3 -c '") + len("python3 -c '")
    end = text.index("'", start)
    # A stray single quote in the body ends the bash string early; bash -n can still
    # pass while the hook is dead. The body must end at the intended terminator.
    assert text[end : end + len(TERMINATOR)] == TERMINATOR, text[end - 80 : end + 20]
    return text[start:end]


def _load_git_run(cwd: Path):
    tree = ast.parse(_embedded_body())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_git_run")
    ns = {"subprocess": subprocess, "cwd": str(cwd)}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(HOOK), "exec"), ns)
    return ns["_git_run"]


def test_embedded_program_compiles():
    compile(_embedded_body(), f"{HOOK.name}:embedded", "exec")


def test_no_git_call_bypasses_the_helper():
    tree = ast.parse(_embedded_body())
    bare = [
        ast.unparse(node)[:80]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) in ("subprocess.run", "subprocess.call", "subprocess.check_call",
                                       "subprocess.check_output", "subprocess.Popen")
        and node.args
        and ast.unparse(node.args[0]).lstrip("[(").startswith(("'git'", '"git"'))
    ]
    assert bare == []


@pytest.fixture
def slow_partial_commit(tmp_path: Path):
    """A repo whose pre-commit hook sleeps while `git commit --only` holds index.lock."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = dict(os.environ, HOME=str(tmp_path), GIT_CONFIG_NOSYSTEM="1")

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    git("config", "core.hooksPath", str(repo / ".git" / "hooks"))
    (repo / "a.txt").write_text("base\n")
    git("add", "a.txt")
    git("commit", "-q", "-m", "init")
    pidfile = tmp_path / "hook.pid"
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho $$ > {pidfile}\nexec sleep 30\n")
    hook.chmod(0o755)
    (repo / "a.txt").write_text("changed\n")
    yield repo, env, pidfile
    try:
        os.kill(int(pidfile.read_text().strip()), signal.SIGKILL)
    except (OSError, ValueError):
        pass


def _commit_argv():
    return ["git", "commit", "--only", "-m", "x", "--", "a.txt"]


def test_positive_control_sigkill_leaves_the_lock(slow_partial_commit):
    repo, env, _ = slow_partial_commit
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(_commit_argv(), cwd=repo, env=env, capture_output=True, timeout=1)
    assert (repo / ".git" / "index.lock").exists()


def test_git_run_timeout_terminates_and_git_removes_its_lock(slow_partial_commit, monkeypatch):
    repo, env, _ = slow_partial_commit
    for key in ("HOME", "GIT_CONFIG_NOSYSTEM"):
        monkeypatch.setenv(key, env[key])
    git_run = _load_git_run(repo)
    t0 = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        git_run(_commit_argv(), timeout=1)
    elapsed = time.monotonic() - t0
    assert not (repo / ".git" / "index.lock").exists()
    assert not list((repo / ".git").glob("next-index-*.lock"))
    # 1 s timeout + at most the 2 s grace, even though the orphaned hook keeps the
    # output pipes open; generous margin for a loaded machine.
    assert elapsed < 8, elapsed


def test_git_run_matches_subprocess_run_on_success_and_check(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git_run = _load_git_run(tmp_path)
    ok = git_run(["git", "--version"], timeout=10)
    assert ok.returncode == 0 and ok.stdout.startswith("git version")
    raw = git_run(["git", "--version"], timeout=10, text=False)
    assert isinstance(raw.stdout, bytes)
    with pytest.raises(subprocess.CalledProcessError):
        git_run(["git", "rev-parse", "--verify", "no-such-ref"], timeout=10, check=True)
    assert git_run(["git", "rev-parse", "--verify", "no-such-ref"], timeout=10).returncode != 0
