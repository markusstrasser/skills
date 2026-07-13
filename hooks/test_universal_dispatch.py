"""Parity tests for pretool-universal-dispatch.py against the two originals it replaces:
tool-tracker.sh and pretool-companion-remind.sh.

Hermetic: every test runs with an isolated $TMPDIR/$HOME so state files never touch
real /tmp or ~/.claude. Run: uv run pytest hooks/test_universal_dispatch.py -q
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
DISPATCH = HOOKS_DIR / "pretool-universal-dispatch.py"
ORIGINAL_TRACKER = Path("/Users/alien/.claude/hooks/tool-tracker.sh")
ORIGINAL_COMPANION = HOOKS_DIR / "pretool-companion-remind.sh"


def run_dispatch(envelope, env_extra=None, tmp_dir=None, home_dir=None, state_dir=None):
    env = os.environ.copy()
    if tmp_dir:
        env["TMPDIR"] = str(tmp_dir)
    if home_dir:
        env["HOME"] = str(home_dir)
    if state_dir:
        env["CLAUDE_HOOK_STATE_DIR"] = str(state_dir)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(DISPATCH)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_dir) if tmp_dir else None,
    )
    return proc


def run_original_tracker(envelope, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["bash", str(ORIGINAL_TRACKER)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc


def isolated_tmp(tmp_path):
    """Create a fake /tmp under tmp_path and point our helpers at it via a fixed PPID dir."""
    fake_tmp = tmp_path / "tmp"
    fake_tmp.mkdir()
    return fake_tmp


def _isolated(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    state = tmp_path / "state"
    state.mkdir()
    return home, state


def test_fresh_read_exits_zero_and_writes_tab_file(tmp_path):
    home, state = _isolated(tmp_path)
    envelope = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/some/fresh_file.py"}}
    proc = run_dispatch(envelope, home_dir=home, state_dir=state)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""
    tab_files = list(state.glob("claude-tab-tool-*"))
    assert len(tab_files) == 1
    assert tab_files[0].read_text() == "Read fresh_file.py"


def test_repeated_read_sequence_matches_oracle(tmp_path):
    """Verified against the real tool-tracker.sh oracle (5 sequential calls,
    same PPID, same file, no offset): call1 silent; calls2-3 recency-window
    'DUPLICATE READ ... 1 tool calls ago' (TOTAL_READS counts PRIOR entries
    only, so it lags the call index by one); call4 'REPEATED READ (3x)';
    call5 BLOCKED (TOTAL_READS=4) with exit 2. TOTAL_READS is computed from
    entries written by PRIOR calls, so blocking needs 5 calls, not 4."""
    home, state = _isolated(tmp_path)
    envelope = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/dup_target_test_file.py"}}
    codes = []
    outs = []
    for _ in range(5):
        proc = run_dispatch(envelope, home_dir=home, state_dir=state)
        codes.append(proc.returncode)
        outs.append(proc.stdout.strip())

    assert codes == [0, 0, 0, 0, 2], (codes, outs)
    assert outs[0] == ""
    assert "DUPLICATE READ" in json.loads(outs[1])["additionalContext"]
    assert "1 tool calls ago" in json.loads(outs[1])["additionalContext"]
    assert "DUPLICATE READ" in json.loads(outs[2])["additionalContext"]
    assert "REPEATED READ (3x)" in json.loads(outs[3])["additionalContext"]
    blocked = json.loads(outs[4])["additionalContext"]
    assert "BLOCKED" in blocked and "4x" in blocked


def test_llmx_bash_command_reminds_once_then_dedups(tmp_path):
    home, state = _isolated(tmp_path)
    session = "test-session-llmx"
    envelope = {"tool_name": "Bash", "tool_input": {"command": "llmx chat -m gpt-5.6 'hi'"}}
    p1 = run_dispatch(envelope, env_extra={"CLAUDE_SESSION_ID": session}, home_dir=home, state_dir=state)
    p2 = run_dispatch(envelope, env_extra={"CLAUDE_SESSION_ID": session}, home_dir=home, state_dir=state)
    assert p1.returncode == 0 and p2.returncode == 0
    assert "[companion]" in p1.stderr and "llmx-guide" in p1.stderr
    assert p2.stderr.strip() == ""  # deduped second call


def test_benign_bash_no_block_no_remind(tmp_path):
    home, state = _isolated(tmp_path)
    envelope = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
    proc = run_dispatch(envelope, env_extra={"CLAUDE_SESSION_ID": "test-benign"}, home_dir=home, state_dir=state)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


def test_agent_tool_action_naming_matches_tab_convention(tmp_path):
    home, state = _isolated(tmp_path)
    envelope = {"tool_name": "Agent", "tool_input": {"description": "audit the repo for bugs"}}
    proc = run_dispatch(envelope, home_dir=home, state_dir=state)
    assert proc.returncode == 0
    tab_files = list(state.glob("claude-tab-tool-*"))
    assert tab_files[0].read_text() == "Agent: audit the repo for b"


def test_write_clears_prior_read_dedup_entries(tmp_path):
    home, state = _isolated(tmp_path)
    fpath = "/tmp/write_clears_target.py"
    read_env = {"tool_name": "Read", "tool_input": {"file_path": fpath}}
    write_env = {"tool_name": "Write", "tool_input": {"file_path": fpath, "content": "x = 1"}}
    run_dispatch(read_env, home_dir=home, state_dir=state)
    run_dispatch(read_env, home_dir=home, state_dir=state)
    p = run_dispatch(write_env, home_dir=home, state_dir=state)
    assert p.returncode == 0
    # after a write, reads reset — three more reads should not immediately block
    codes = [run_dispatch(read_env, home_dir=home, state_dir=state).returncode for _ in range(3)]
    assert codes == [0, 0, 0], codes


def test_mcp_search_tool_triggers_research_reminder_at_third_call(tmp_path):
    home, state = _isolated(tmp_path)
    session = "test-session-search-burst"
    envelope = {
        "tool_name": "mcp__exa__web_search_exa",
        "tool_input": {"query": "arxiv paper on causal inference"},
    }
    stderrs = []
    for _ in range(3):
        p = run_dispatch(envelope, env_extra={"CLAUDE_SESSION_ID": session}, home_dir=home, state_dir=state)
        stderrs.append(p.stderr)
    assert "research" in stderrs[2] and "[companion]" in stderrs[2]
    assert "research" not in stderrs[0]
    assert "research" not in stderrs[1]
    # s2-for-papers should also fire (query matches "paper|arxiv"); the printed
    # message text, not the internal skill slug, is what lands in stderr.
    assert any("Paper/venue name detected" in s for s in stderrs)


def test_matches_original_tracker_for_fresh_read():
    """Direct comparison against the bash original. The original hardcodes
    /tmp/claude-*-$PPID with no override, so this test unavoidably touches
    real /tmp (keyed to this pytest process's own PID) — cleaned up in
    `finally` regardless of outcome."""
    own_pid = os.getpid()
    tab_file = f"/tmp/claude-tab-tool-{own_pid}"
    non_agent_file = f"/tmp/claude-non-agent-{own_pid}"
    reads_file = f"/tmp/claude-reads-{own_pid}"
    count_file = f"/tmp/claude-toolcount-{own_pid}"
    # Distinct file paths for each side — both must independently see a FRESH
    # (first-ever) read under the shared PPID's reads_file, not a dup of the
    # other side's just-recorded entry.
    orig_envelope = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/parity_compare_orig.py"}}
    dispatched_envelope = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/parity_compare_dispatched.py"}}
    try:
        orig = run_original_tracker(orig_envelope)
        assert orig.returncode == 0, orig.stderr
        orig_tab_content = Path(tab_file).read_text()

        dispatched = run_dispatch(dispatched_envelope, state_dir="/tmp")  # same real-/tmp path
        assert dispatched.returncode == 0, dispatched.stderr
        dispatched_tab_content = Path(tab_file).read_text()

        # Original uses `echo` (trailing \n); dispatcher uses write() (no \n) —
        # trailing whitespace is not part of the tab-title contract (consumers
        # display it, no downstream parser depends on exact byte-for-byte).
        assert orig_tab_content.rstrip("\n") == "Read parity_compare_orig.py"
        assert dispatched_tab_content.rstrip("\n") == "Read parity_compare_dispatched.py"
        assert orig.stdout.strip() == dispatched.stdout.strip() == ""
    finally:
        for f in (tab_file, non_agent_file, reads_file, count_file):
            try:
                os.remove(f)
            except OSError:
                pass


def test_settings_json_is_valid_and_wires_dispatcher():
    settings_path = Path("/Users/alien/.claude/settings.json")
    data = json.loads(settings_path.read_text())
    catchall_blocks = [
        blk for blk in data.get("hooks", {}).get("PreToolUse", [])
        if "matcher" not in blk
    ]
    assert len(catchall_blocks) == 1, catchall_blocks
    commands = [h["command"] for h in catchall_blocks[0]["hooks"]]
    assert any("pretool-universal-dispatch.py" in c for c in commands)
    assert not any("tool-tracker.sh" in c for c in commands)
    assert not any("pretool-companion-remind.sh" in c for c in commands)
