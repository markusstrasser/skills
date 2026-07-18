"""Tests for pretool-multiagent-commit-guard.sh — the multi-agent shared-
checkout commit guard, extended 2026-07-18 with a T3 exposure-clean probe
(guard-forcerate-study / rescue-class-surface-closure-loop, arc-agi
loop/backlog.jsonl rows 906/909: "git commit --only when peers exist =
eligible-and-clean for the commit guard").

Hermetic: isolated HOME (kills real ~/.claude writes) + throwaway git repos.
Peer count is faked via PEER_SESSION_COUNT_BIN, same convention as
test_bash_dispatch.py's git-stash tests.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent
SCRIPT = HOOKS_DIR / "pretool-multiagent-commit-guard.sh"


def run_guard(cmd: str, env: dict, cwd: str) -> subprocess.CompletedProcess:
    envelope = {"tool_input": {"command": cmd}, "cwd": cwd}
    return subprocess.run(
        ["bash", str(SCRIPT)], input=json.dumps(envelope),
        capture_output=True, text=True, env=env, cwd=cwd, timeout=30,
    )


def _fake_peer_bin(tmp_path, count):
    p = tmp_path / f"fake_peer_{count}.sh"
    p.write_text(f"#!/bin/sh\necho {count}\n")
    p.chmod(0o755)
    return str(p)


def _read_trigger_log(home):
    log_path = Path(home) / ".claude" / "hook-triggers.jsonl"
    if not log_path.is_file():
        return []
    rows = []
    with open(log_path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", "replace").strip()
            if line:
                rows.append(json.loads(line))
    return rows


@pytest.fixture
def sandbox(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    cwd = tmp_path / "work"
    cwd.mkdir()
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.pop("CLAUDE_SESSION_ID", None)
    return {"env": env, "cwd": str(cwd), "home": str(home), "tmp_path": tmp_path}


@pytest.fixture
def git_sandbox(sandbox):
    subprocess.run(["git", "init", "-q"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    (Path(sandbox["cwd"]) / "file.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "file.py"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    return sandbox


def test_bare_commit_blocks_with_peer_and_carries_fingerprint(git_sandbox):
    (Path(git_sandbox["cwd"]) / "file.py").write_text("x = 2\n")
    subprocess.run(["git", "add", "file.py"], cwd=git_sandbox["cwd"], env=git_sandbox["env"], check=True)
    env = dict(git_sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(git_sandbox["tmp_path"], 1)
    proc = run_guard("git commit -m 'bare'", env, git_sandbox["cwd"])
    assert proc.returncode == 2
    out = json.loads(proc.stdout)
    assert out["decision"] == "block"
    rows = _read_trigger_log(git_sandbox["home"])
    blocks = [r for r in rows if r.get("hook") == "multiagent-commit" and r.get("action") == "block"]
    assert len(blocks) == 1
    assert blocks[0].get("cmd_tok") == "git"
    assert len(blocks[0].get("cmd_fp", "")) == 8
    assert "cmd" not in blocks[0]


def test_commit_only_with_peer_logs_exposure_clean(git_sandbox):
    (Path(git_sandbox["cwd"]) / "file.py").write_text("x = 2\n")
    env = dict(git_sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(git_sandbox["tmp_path"], 1)
    proc = run_guard("git commit --only file.py -m 'scoped'", env, git_sandbox["cwd"])
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    rows = _read_trigger_log(git_sandbox["home"])
    exposures = [r for r in rows if r.get("hook") == "multiagent-commit" and r.get("action") == "exposure-clean"]
    assert len(exposures) == 1
    assert exposures[0].get("cmd_tok") == "git"
    assert len(exposures[0].get("cmd_fp", "")) == 8
    assert "peers=1" in exposures[0].get("detail", "")


def test_commit_only_no_peer_logs_nothing(git_sandbox):
    """No peer -> the guard's precondition never applied -> no exposure row."""
    (Path(git_sandbox["cwd"]) / "file.py").write_text("x = 2\n")
    env = dict(git_sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(git_sandbox["tmp_path"], 0)
    proc = run_guard("git commit --only file.py -m 'scoped'", env, git_sandbox["cwd"])
    assert proc.returncode == 0
    rows = _read_trigger_log(git_sandbox["home"])
    assert not [r for r in rows if r.get("hook") == "multiagent-commit"]


def test_commit_only_in_worktree_logs_nothing(git_sandbox, tmp_path):
    """A linked worktree means the guard's whole precondition (shared/main
    checkout) doesn't apply — no exposure row, same as the block path already
    treats a worktree as structurally safe."""
    wt_dir = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "wt-branch", str(wt_dir)],
        cwd=git_sandbox["cwd"], env=git_sandbox["env"], check=True,
    )
    (wt_dir / "file.py").write_text("x = 3\n")
    env = dict(git_sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(git_sandbox["tmp_path"], 1)
    proc = run_guard("git commit --only file.py -m 'scoped'", env, str(wt_dir))
    assert proc.returncode == 0
    rows = _read_trigger_log(git_sandbox["home"])
    assert not [r for r in rows if r.get("hook") == "multiagent-commit"]


def test_merge_head_present_allow_merge_carries_fingerprint(git_sandbox):
    """Pre-existing allow-merge logging now also carries a fingerprint (T1),
    still never blocks (unchanged behavior)."""
    env = dict(git_sandbox["env"])
    # Fabricate a MERGE_HEAD without an actual merge conflict, matching how
    # the guard's own check reads it (rev-parse --verify MERGE_HEAD).
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"], cwd=git_sandbox["cwd"], env=env,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_sandbox["cwd"], env=env,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    (Path(git_sandbox["cwd"]) / git_dir / "MERGE_HEAD").write_text(head_sha + "\n")
    proc = run_guard("git commit -m 'merge commit'", env, git_sandbox["cwd"])
    assert proc.returncode == 0
    rows = _read_trigger_log(git_sandbox["home"])
    allows = [r for r in rows if r.get("hook") == "multiagent-commit" and r.get("action") == "allow-merge"]
    assert len(allows) == 1
    assert allows[0].get("cmd_tok") == "git"
    assert len(allows[0].get("cmd_fp", "")) == 8


def test_git_status_safe_logs_nothing(git_sandbox):
    env = dict(git_sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(git_sandbox["tmp_path"], 1)
    proc = run_guard("git status", env, git_sandbox["cwd"])
    assert proc.returncode == 0
    rows = _read_trigger_log(git_sandbox["home"])
    assert not [r for r in rows if r.get("hook") == "multiagent-commit"]


def test_git_add_dash_A_still_blocks_unchanged(git_sandbox):
    """Sanity: the pre-existing dangerous-add block path is untouched by the
    T3 exposure-probe restructure."""
    env = dict(git_sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(git_sandbox["tmp_path"], 1)
    proc = run_guard("git add -A", env, git_sandbox["cwd"])
    assert proc.returncode == 2
