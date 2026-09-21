"""Tests for pretool-subagent-settings-guard.py."""

import json
import subprocess
import sys
from pathlib import Path

GUARD = str(Path(__file__).parent / "pretool-subagent-settings-guard.py")


def run(envelope, agent_id: str | None = "a12bfef463b73db2f", raw=None, env_agent_id=None):
    """A subagent's call is marked the way Claude Code marks it: agent_id/agent_type in the
    envelope (probed 2026-09-21). The hook environment never carries CLAUDE_AGENT_ID; these
    tests set only that variable until then, so they passed while the live guard was dead."""
    env = {"PATH": "/usr/bin:/bin"}
    if env_agent_id is not None:
        env["CLAUDE_AGENT_ID"] = env_agent_id
    if agent_id is not None and isinstance(envelope, dict):
        envelope = dict(envelope, agent_id=agent_id, agent_type="general-purpose")
    data = raw if raw is not None else json.dumps(envelope)
    return subprocess.run(
        [sys.executable, GUARD], input=data, capture_output=True, text=True, env=env
    )


def _env(fpath, tool="Write"):
    return {"tool_name": tool, "tool_input": {"file_path": fpath, "content": "{}"}}


def test_subagent_blocked_on_global_settings():
    p = run(_env("/Users/alien/.claude/settings.json"))
    assert p.returncode == 2
    assert "BLOCKED" in p.stderr and "parent applies the wiring" in p.stderr


def test_subagent_blocked_on_repo_settings_and_local():
    assert run(_env("/Users/x/Projects/intel/.claude/settings.json", "Edit")).returncode == 2
    assert run(_env("/Users/x/proj/.claude/settings.local.json")).returncode == 2


def test_main_session_never_blocked():
    p = run(_env("/Users/alien/.claude/settings.json"), agent_id=None)
    assert p.returncode == 0


def test_environment_marker_alone_still_blocks():
    p = run(_env("/Users/alien/.claude/settings.json"), agent_id=None, env_agent_id="a1b2c3")
    assert p.returncode == 2


def test_subagent_free_on_non_settings_paths():
    for fp in (
        "/Users/x/proj/.claude/hooks/pretool-foo.py",
        "/Users/x/proj/.claude/settings.json.bak",
        "/Users/x/proj/hooks/_gates_snapshot.json",
        "/Users/x/proj/settings.json",  # not under .claude/
    ):
        assert run(_env(fp)).returncode == 0, fp


def test_fail_open_on_garbage():
    assert run(None, raw="{{{").returncode == 0
    assert run(None, raw="").returncode == 0
    assert run({"tool_name": "Write"}).returncode == 0  # no tool_input
