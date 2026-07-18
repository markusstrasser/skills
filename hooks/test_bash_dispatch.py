"""Parity tests: pretool-bash-dispatch.py vs the ORIGINAL 28-hook pipeline.

The oracle is the frozen manifest _bash_gates_pre_dispatch_snapshot.json
(captured from ~/.claude/settings.json BEFORE it was edited to point at the
dispatcher) replayed through the ORIGINAL, on-disk hook scripts — honoring
each hook's "if": "Bash(<glob>)" condition exactly as Claude Code would.
Original files are untouched by the consolidation; this test invokes them
directly, so it stays a live oracle even after settings.json is repointed.

Hermetic: every subprocess call passes an isolated HOME (redirects
~/.claude/session-receipts.jsonl, ~/.claude/hook-triggers.jsonl, etc.) and,
for git-touching cases, an isolated non-repo or throwaway-repo cwd — no
writes land in the real ~/.claude or in this repo's own git refs.
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys

import pytest

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
DISPATCHER = os.path.join(HOOKS_DIR, "pretool-bash-dispatch.py")
SNAPSHOT = os.path.join(HOOKS_DIR, "_bash_gates_pre_dispatch_snapshot.json")


def _if_matches(if_pattern, cmd):
    if not if_pattern:
        return True
    if if_pattern.startswith("Bash(") and if_pattern.endswith(")"):
        return fnmatch.fnmatchcase((cmd or "").lstrip(), if_pattern[len("Bash("):-1])
    return True


def run_oracle(envelope: dict, env: dict, cwd: str) -> dict:
    """Replay the ORIGINAL 28-hook pipeline serially, respecting `if` gates."""
    manifest = json.load(open(SNAPSHOT))["hooks"]
    current_ti = dict(envelope.get("tool_input") or {})
    result = {"exit_code": 0, "block_msg": "", "final_command": current_ti.get("command")}
    for h in manifest:
        cmd_str = current_ti.get("command", "") or ""
        if not _if_matches(h.get("if"), cmd_str):
            continue
        payload = dict(envelope)
        payload["tool_input"] = current_ti
        raw = json.dumps(payload)
        parts = h["command"].split(" ", 1)
        argv = ["python3", parts[1]] if parts[0] == "python3" else [h["command"]]
        try:
            proc = subprocess.run(argv, input=raw, capture_output=True, text=True, timeout=30, env=env, cwd=cwd)
        except Exception:
            continue
        if proc.returncode == 2:
            result["exit_code"] = 2
            so = (proc.stdout or "").strip()
            try:
                obj = json.loads(so)
                result["block_msg"] = obj.get("reason", so) if isinstance(obj, dict) and obj.get("decision") == "block" else ((proc.stderr or so).strip())
            except Exception:
                result["block_msg"] = (proc.stderr or so).strip()
            break
        so = (proc.stdout or "").strip()
        if so:
            try:
                obj = json.loads(so)
            except Exception:
                obj = None
            if isinstance(obj, dict):
                if obj.get("decision") == "block":
                    result["exit_code"] = 2
                    result["block_msg"] = obj.get("reason", so)
                    break
                hso = obj.get("hookSpecificOutput") or {}
                if isinstance(hso, dict) and "updatedInput" in hso:
                    current_ti = hso["updatedInput"]
    result["final_command"] = current_ti.get("command")
    return result


def run_dispatcher(envelope: dict, env: dict, cwd: str) -> dict:
    raw = json.dumps(envelope)
    proc = subprocess.run(["python3", DISPATCHER], input=raw, capture_output=True, text=True, timeout=30, env=env, cwd=cwd)
    result = {"exit_code": proc.returncode, "block_msg": "", "final_command": (envelope.get("tool_input") or {}).get("command")}
    if proc.returncode == 2:
        result["block_msg"] = proc.stderr.strip()
        return result
    so = proc.stdout.strip()
    if so:
        try:
            obj = json.loads(so)
        except Exception:
            obj = None
        if isinstance(obj, dict):
            hso = obj.get("hookSpecificOutput") or {}
            if isinstance(hso, dict) and "updatedInput" in hso:
                result["final_command"] = hso["updatedInput"].get("command")
            result["additionalContext"] = obj.get("additionalContext")
    return result


@pytest.fixture
def sandbox(tmp_path):
    """Isolated HOME (kills real ~/.claude writes) + a plain non-git cwd."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    cwd = tmp_path / "work"
    cwd.mkdir()
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.pop("CLAUDE_SESSION_ID", None)
    return {"env": env, "cwd": str(cwd), "home": str(home)}


@pytest.fixture
def git_sandbox(sandbox):
    """A throwaway git repo cwd — for gates that read `git diff --cached` etc."""
    subprocess.run(["git", "init", "-q"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=sandbox["cwd"], env=sandbox["env"], check=True)
    return sandbox


def _both(envelope, sb):
    envelope = dict(envelope)
    envelope.setdefault("cwd", sb["cwd"])
    oracle = run_oracle(envelope, sb["env"], sb["cwd"])
    disp = run_dispatcher(envelope, sb["env"], sb["cwd"])
    return oracle, disp


# ---------------------------------------------------------------------------

def test_benign_git_status_passes_both(git_sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    oracle, disp = _both(envelope, git_sandbox)
    assert oracle["exit_code"] == 0
    assert disp["exit_code"] == 0
    assert oracle["final_command"] == disp["final_command"] == "git status"


def test_git_add_dash_A_blocks_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git add -A"}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 2
    assert disp["exit_code"] == 2
    assert "git add -A" in oracle["block_msg"] or "git add -A" in disp["block_msg"]
    assert "banned" in disp["block_msg"]


def test_backgrounded_git_commit_blocks_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git commit -m test", "run_in_background": True}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 2
    assert disp["exit_code"] == 2
    assert "run_in_background" in oracle["block_msg"] or "FOREGROUND" in disp["block_msg"]


def test_git_diff_injects_no_ext_diff_both(git_sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git diff HEAD~1"}}
    oracle, disp = _both(envelope, git_sandbox)
    assert oracle["exit_code"] == 0
    assert disp["exit_code"] == 0
    assert "--no-ext-diff" in oracle["final_command"]
    assert "--no-ext-diff" in disp["final_command"]
    assert oracle["final_command"] == disp["final_command"]


def test_backgrounded_python_gets_pythonunbuffered_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "cd /tmp && python3 script.py", "run_in_background": True}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 0
    assert disp["exit_code"] == 0
    assert "PYTHONUNBUFFERED=1" in oracle["final_command"]
    assert "PYTHONUNBUFFERED=1" in disp["final_command"]
    assert oracle["final_command"] == disp["final_command"]


def test_bare_python_rewrites_to_uv_run_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "python3 foo.py"}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 0
    assert disp["exit_code"] == 0
    assert oracle["final_command"] == disp["final_command"] == "uv run python3 foo.py"


def test_uvx_python_blocks_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "uvx python3 -c 'import duckdb'"}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 2
    assert disp["exit_code"] == 2
    assert "isolated interpreter" in oracle["block_msg"] or "isolated interpreter" in disp["block_msg"]


def test_cat_missing_file_blocks_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "echo \"$(cat /tmp/definitely-missing-file-xyz-parity-test.txt)\""}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 2
    assert disp["exit_code"] == 2
    assert "missing" in oracle["block_msg"].lower()
    assert "missing" in disp["block_msg"].lower()


def test_cursor_agent_foreign_model_blocks_both(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "cursor-agent --model gpt-5.5 'review this'"}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 2
    assert disp["exit_code"] == 2
    assert "Composer" in oracle["block_msg"] or "Composer" in disp["block_msg"]


def test_destructive_git_ref_never_hard_blocks_both(git_sandbox):
    """pretool-destructive-git-ref.sh is ADVISORY-FIRST by design (never
    exits 2 on its own — only a hard git failure would). Verifies parity on
    that documented never-blocks invariant using a non-existent ref (which
    git itself will reject harmlessly) so no real destructive op runs."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD~1"}}
    oracle, disp = _both(envelope, git_sandbox)
    assert oracle["exit_code"] == 0
    assert disp["exit_code"] == 0


def test_malformed_stdin_fails_open(sandbox):
    proc = subprocess.run(["python3", DISPATCHER], input="not json {{{", capture_output=True, text=True,
                           timeout=30, env=sandbox["env"], cwd=sandbox["cwd"])
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_non_bash_tool_is_noop(sandbox):
    envelope = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}
    proc = subprocess.run(["python3", DISPATCHER], input=json.dumps(envelope), capture_output=True, text=True,
                           timeout=30, env=sandbox["env"], cwd=sandbox["cwd"])
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_duckdb_double_quote_advisory_matches(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": 'duckdb -c "SELECT * FROM t WHERE col = \\"value\\""'}}
    oracle, disp = _both(envelope, sandbox)
    assert oracle["exit_code"] == 0
    assert disp["exit_code"] == 0


# ---------------------------------------------------------------------------
# Post-consolidation additions (2026-07-18) — new gates, no pre-consolidation
# oracle to parity-test against, so these call run_dispatcher() directly.
# ---------------------------------------------------------------------------

def _fake_peer_bin(tmp_path, count):
    p = tmp_path / f"fake_peer_{count}.sh"
    p.write_text(f"#!/bin/sh\necho {count}\n")
    p.chmod(0o755)
    return str(p)


def test_git_stash_bare_blocks_when_peer_present(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 2
    assert "peer Claude session" in disp["block_msg"]


def test_git_stash_push_pathlimited_allowed_even_with_peer(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash push -- file.txt"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def test_git_stash_list_readonly_never_blocked(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash list"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0


def test_git_stash_no_peer_is_advisory_not_block(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 0)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp.get("additionalContext") and "no peer detected" in disp["additionalContext"]


def test_git_stash_compound_command_still_caught(sandbox, tmp_path):
    """Native port (if=None) catches `cd x && git stash`, unlike a hypothetical
    if="Bash(git*)" gate which would never see a non-git-prefixed compound
    command — this is the coverage the native-vs-subprocess-kept design choice
    buys over cloning git-add-all-guard.sh's if="Bash(git*)" verbatim."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": "cd /tmp && git stash"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 2


def _read_trigger_log(sandbox):
    log_path = os.path.join(sandbox["home"], ".claude", "hook-triggers.jsonl")
    if not os.path.isfile(log_path):
        return []
    rows = []
    with open(log_path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", "replace").strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_git_stash_list_readonly_with_peer_logs_exposure_clean(sandbox, tmp_path):
    """T3 (rescue-class-surface-closure-loop): a safe stash form with a peer
    present is the eligible-and-clean denominator row — the guard's
    precondition (stash-shaped, peer present) matched but nothing fired."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash list"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    rows = _read_trigger_log(sandbox)
    exposures = [r for r in rows if r.get("hook") == "git-stash-guard" and r.get("action") == "exposure-clean"]
    assert len(exposures) == 1
    assert exposures[0].get("cmd_tok") == "git"
    assert len(exposures[0].get("cmd_fp", "")) == 8
    assert "cmd" not in exposures[0]  # raw command never persisted


def test_git_stash_push_pathlimited_with_peer_logs_exposure_clean(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash push -- file.txt"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 2)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    rows = _read_trigger_log(sandbox)
    exposures = [r for r in rows if r.get("hook") == "git-stash-guard" and r.get("action") == "exposure-clean"]
    assert len(exposures) == 1
    assert "peers=2" in exposures[0].get("detail", "")


def test_git_stash_safe_no_peer_logs_nothing(sandbox, tmp_path):
    """No peer -> the guard's precondition never applied (same scoping as the
    advisory branch) -> no exposure row, not even a false 'clean' one."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash list"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 0)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    rows = _read_trigger_log(sandbox)
    assert not [r for r in rows if r.get("hook") == "git-stash-guard"]


def test_git_stash_block_row_carries_cmd_fingerprint(sandbox, tmp_path):
    """T1 enrichment applied to the pre-existing block path: the block row
    now also carries cmd_tok/cmd_fp, never the raw command."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": "git stash"}}
    env = dict(sandbox["env"])
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 2
    rows = _read_trigger_log(sandbox)
    blocks = [r for r in rows if r.get("hook") == "git-stash-guard" and r.get("action") == "block"]
    assert len(blocks) == 1
    assert blocks[0].get("cmd_tok") == "git"
    assert len(blocks[0].get("cmd_fp", "")) == 8
    assert "cmd" not in blocks[0]


def test_pkill_unanchored_advises(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "pkill -f forkDC"}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp.get("additionalContext") and "unanchored" in disp["additionalContext"]


def test_pkill_anchored_by_path_silent(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "pkill -f /usr/bin/foo"}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def test_pkill_anchored_by_dash_x_silent(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "pkill -x -f process_name"}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def test_pkill_bare_name_no_dash_f_not_flagged(sandbox):
    """Not the -f substring-danger case the rule targets — bare `pkill name`
    matches by process name only, a different (less risky) mode."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": "pkill forkDCH"}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def _fake_pgrep_bin(tmp_path, n_lines):
    p = tmp_path / f"fake_pgrep_{n_lines}.sh"
    body = "\n".join(f"echo '{1000+i} line{i}'" for i in range(n_lines))
    p.write_text(f"#!/bin/sh\n{body}\n")
    p.chmod(0o755)
    return str(p)


def test_opus_concurrency_advises_at_three_or_more(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "llmx chat -m claude-opus-4-8 -e max hi"}}
    env = dict(sandbox["env"])
    env["OPUS_LOAD_PGREP_BIN"] = _fake_pgrep_bin(tmp_path, 3)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp.get("additionalContext") and "concurrent opus-family streams" in disp["additionalContext"]


def test_opus_concurrency_silent_below_three(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "llmx chat -m claude-opus-4-8 -e max hi"}}
    env = dict(sandbox["env"])
    env["OPUS_LOAD_PGREP_BIN"] = _fake_pgrep_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def test_opus_concurrency_ignores_non_opus_models(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "llmx chat -m gpt-5.6 -e max hi"}}
    env = dict(sandbox["env"])
    env["OPUS_LOAD_PGREP_BIN"] = _fake_pgrep_bin(tmp_path, 5)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def test_settings_json_is_valid_after_edit():
    """Guards the deliverable's final step (this test only meaningful after
    settings.json has been repointed at the dispatcher; harmless no-op check
    of current validity otherwise)."""
    with open(os.path.expanduser("~/.claude/settings.json")) as f:
        json.load(f)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
