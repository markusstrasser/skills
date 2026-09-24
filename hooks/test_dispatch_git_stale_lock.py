"""Regression: pretool-bash-dispatch.py runs pretool-git-stale-lock.sh for git commands.

Incident (heli, 2026-09-24): a 0-byte .git/index.lock left at 20:05:05 with no holder
and no git process blocked every git write until it was removed by hand ~10 minutes
later. The stale-lock guard existed but only genomics wired it; the dispatcher now runs
it for every repo, only when the command names git, in the envelope's directory.

Each case also carries a positive control, so a guard that never runs (missing lsof,
wrong cwd, bad exec bit) cannot pass a "lock stays" assertion by accident.

Run: uv run python3 -m pytest hooks/test_dispatch_git_stale_lock.py -q
"""

from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent
DISPATCHER = HOOKS_DIR / "pretool-bash-dispatch.py"
_NS = runpy.run_path(str(DISPATCHER))

pytestmark = pytest.mark.skipif(shutil.which("lsof") is None, reason="the guard needs lsof")


@pytest.fixture
def sb(tmp_path: Path) -> dict:
    """Throwaway repo, isolated HOME and receipts, and a separate non-git process cwd."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"  # the dispatcher's own cwd: NOT the repo
    elsewhere.mkdir()
    receipts = tmp_path / "receipts" / "removed.jsonl"
    env = dict(os.environ, HOME=str(home), GIT_STALE_LOCK_RECEIPTS=str(receipts))
    env.pop("CLAUDE_SESSION_ID", None)
    env.pop("GIT_STALE_LOCK_MIN_AGE_SECONDS", None)
    subprocess.run(["git", "init", "-q", str(repo)], env=env, check=True)
    lock = repo / ".git" / "index.lock"
    return {"repo": repo, "env": env, "elsewhere": elsewhere, "receipts": receipts, "lock": lock}


def _stale_lock(lock: Path, age_s: int = 120) -> None:
    lock.write_bytes(b"")
    past = time.time() - age_s
    os.utime(lock, (past, past))


def _dispatch(sb: dict, command: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    envelope = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd or sb["repo"]),
    }
    return subprocess.run(
        [sys.executable, str(DISPATCHER)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        timeout=60,
        env=sb["env"],
        cwd=sb["elsewhere"],
    )


def test_git_command_removes_stale_lock_from_envelope_cwd(sb):
    _stale_lock(sb["lock"])
    proc = _dispatch(sb, f"cd {sb['repo']} && git status")
    assert proc.returncode == 0, proc.stderr
    assert not sb["lock"].exists()
    assert "git-stale-lock" not in proc.stdout  # the guard's note is never model-visible
    rows = [json.loads(line) for line in sb["receipts"].read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["lock"] == str(sb["lock"].resolve())  # absolute: names its repo
    assert rows[0]["holders"] == "none"


def test_envelope_cwd_in_a_subdirectory_still_finds_the_repo(sb):
    _stale_lock(sb["lock"])
    proc = _dispatch(sb, "git log --oneline -1", cwd=sb["repo"] / "sub")
    assert proc.returncode == 0, proc.stderr
    assert not sb["lock"].exists()


def test_non_git_command_leaves_the_lock(sb):
    _stale_lock(sb["lock"])
    proc = _dispatch(sb, "ls")
    assert proc.returncode == 0, proc.stderr
    assert sb["lock"].exists()
    assert not sb["receipts"].exists()
    # Positive control: the same setup does clear on a git command.
    assert _dispatch(sb, "git status").returncode == 0
    assert not sb["lock"].exists()


@pytest.mark.parametrize("command", ["echo legit", "open https://github.com/x/y", "ls digits"])
def test_git_as_part_of_a_word_does_not_trigger(sb, command):
    _stale_lock(sb["lock"])
    assert _dispatch(sb, command).returncode == 0
    assert sb["lock"].exists()


def test_lock_held_by_a_live_process_stays(sb):
    _stale_lock(sb["lock"])
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys, time\n"
            "f = open(sys.argv[1], 'a')\n"
            "print('ready', flush=True)\n"
            "time.sleep(120)\n",
            str(sb["lock"]),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "ready"
        proc = _dispatch(sb, f"cd {sb['repo']} && git status")
        assert proc.returncode == 0, proc.stderr
        assert sb["lock"].exists()
        assert not sb["receipts"].exists()
    finally:
        holder.kill()
        holder.wait()
    # Positive control: once the holder is gone the same lock is cleared.
    assert _dispatch(sb, "git status").returncode == 0
    assert not sb["lock"].exists()


def _commit_in_hook_phase(sb: dict) -> subprocess.Popen:
    """Start `git commit -a` whose pre-commit hook sleeps; return once index.lock exists.

    In a hook phase git keeps index.lock on disk but CLOSED (lsof finds no holder) and
    renames it only after the hooks return. Measured 2026-09-24, git 2.54.
    """
    repo, env = sb["repo"], sb["env"]
    for args in (["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(repo), *args], env=env, check=True)
    (repo / "a.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(repo), "add", "--", "a.txt"], env=env, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "init"], env=env, check=True)
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexec sleep 6 >/dev/null 2>&1\n")
    hook.chmod(0o755)
    (repo / "a.txt").write_text("changed\n")
    proc = subprocess.Popen(
        ["git", "-C", str(repo), "commit", "-a", "-m", "live"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not sb["lock"].exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert sb["lock"].exists(), "commit never took index.lock"
    assert subprocess.run(["lsof", "-t", "--", str(sb["lock"])], capture_output=True).stdout == b""
    return proc


def test_live_commit_in_a_hook_phase_keeps_its_closed_lock(sb):
    """The lock has no holder and passes the age floor, but its git is alive."""
    commit = _commit_in_hook_phase(sb)
    sb["env"]["GIT_STALE_LOCK_MIN_AGE_SECONDS"] = "0"  # the floor must not be what saves it
    try:
        proc = _dispatch(sb, "git status")
        assert proc.returncode == 0, proc.stderr
        assert sb["lock"].exists()
        assert not sb["receipts"].exists()
    finally:
        out, _ = commit.communicate(timeout=30)
    assert commit.returncode == 0, out  # the deletion made this fail: "unable to write new index file"


def test_lock_orphaned_mid_hook_is_removed(sb):
    """Positive control for the busy check: kill the committing git, keep its hook."""
    commit = _commit_in_hook_phase(sb)
    commit.kill()
    commit.wait()
    assert sb["lock"].exists()  # SIGKILL: git could not clean up
    sb["env"]["GIT_STALE_LOCK_MIN_AGE_SECONDS"] = "0"
    assert _dispatch(sb, "git status").returncode == 0
    assert not sb["lock"].exists()


@pytest.fixture
def in_process(sb, monkeypatch):
    """Call the gate function directly, with the sandbox env and a non-git cwd."""
    monkeypatch.setenv("HOME", sb["env"]["HOME"])
    monkeypatch.setenv("GIT_STALE_LOCK_RECEIPTS", sb["env"]["GIT_STALE_LOCK_RECEIPTS"])
    monkeypatch.chdir(sb["elsewhere"])
    return _NS["gate_git_stale_lock"]


def test_gate_never_emits_a_verdict(sb, in_process):
    """Gate-level contract: pass with no output, also when it removed a lock."""
    _stale_lock(sb["lock"])
    raw = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(sb["repo"])}
    )
    assert tuple(in_process(raw)) == (0, "", "")
    assert not sb["lock"].exists()


@pytest.mark.parametrize("cwd", ["/nonexistent/dir/for/stale-lock-test", None])
def test_missing_or_absent_cwd_fails_open(sb, in_process, cwd):
    _stale_lock(sb["lock"])
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    if cwd:
        envelope["cwd"] = cwd
    assert tuple(in_process(json.dumps(envelope))) == (0, "", "")
    assert sb["lock"].exists()  # neither case points at the repo
    assert not sb["receipts"].exists()


def test_gate_runs_second_right_after_secret_output_guard():
    names = [gate["name"] for gate in _NS["MANIFEST"]]
    assert names[:2] == ["secret-output-guard", "git-stale-lock"]
