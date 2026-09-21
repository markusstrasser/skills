"""Caller identity for hook state: lib_hook_identity.{py,sh} and the hooks that load them.

Incident, 2026-09-21: Claude Code marks a subagent's tool calls with `agent_id` in the hook
ENVELOPE. Hooks here tested CLAUDE_AGENT_ID / CLAUDE_SESSION_ID (never set for hook processes)
or keyed state on $PPID alone (shared by every in-process subagent). Seven sibling readers of
one brief were blocked as one caller; a settings guard and three subagent exemptions never
fired; "once per session" reminders were once per reboot. Every hook test below runs all its
calls from one parent process, which is exactly the sibling situation.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))

import lib_hook_identity  # noqa: E402

SESSION = "adae2b38-fa63-4fd0-b727-08c73975b287"
ENVELOPES = [
    {"session_id": SESSION},  # main loop: no agent_id at all
    {"session_id": SESSION, "agent_id": "a12bfef463b73db2f", "agent_type": "Explore"},
    {"session_id": SESSION, "agent_id": None},
    {"session_id": SESSION, "agent_id": "../../evil/a-1"},
    {"agent_id": 1234567},
    {"agent_id": "x" * 80, "session_id": "s/../../e" + "9" * 90},
    {},
]


def bash_identity(envelope, env=None):
    script = f'. "{HOOKS_DIR}/lib_hook_identity.sh"; hook_identity "$1"; ' \
             'printf "%s\\n%s\\n%s\\n%s" "$HOOK_AGENT_ID" "$HOOK_SESSION_ID" "$HOOK_OWNER" "$PPID"'
    proc = subprocess.run(["bash", "-c", script, "_", json.dumps(envelope)],
                          capture_output=True, text=True, env=env, check=True)
    agent, session, owner, ppid = proc.stdout.split("\n")
    return agent, session, owner, int(ppid)


@pytest.mark.parametrize("envelope", ENVELOPES, ids=[json.dumps(e)[:40] for e in ENVELOPES])
def test_bash_and_python_twins_agree(envelope):
    env = {"PATH": os.environ["PATH"]}  # no inherited session variables
    agent, session, owner, ppid = bash_identity(envelope, env)
    saved = {k: os.environ.pop(k, None) for k in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")}
    try:
        assert agent == lib_hook_identity.agent_id(envelope)
        assert session == lib_hook_identity.session_id(envelope)
        assert owner == lib_hook_identity.owner(envelope, ppid)
    finally:
        os.environ.update({k: v for k, v in saved.items() if v is not None})


def test_main_loop_has_no_agent_and_keeps_the_bare_pid():
    agent, session, owner, ppid = bash_identity({"session_id": SESSION})
    assert (agent, session, owner) == ("", SESSION, str(ppid))


def test_identity_is_filename_safe_and_pid_stays_the_suffix():
    from reap_stale_trackers import PID_SUFFIX

    agent, _, owner, ppid = bash_identity({"agent_id": "../../evil/a-1"})
    assert agent == "evila1" and owner == f"evila1-{ppid}"
    assert int(PID_SUFFIX.search(f"claude-reads-{owner}").group(1)) == ppid


def test_session_falls_back_to_the_variable_hooks_really_inherit():
    env = {"PATH": os.environ["PATH"], "CLAUDE_CODE_SESSION_ID": "from-env"}
    assert bash_identity({}, env)[1] == "from-env"


# --- the hooks that load it -------------------------------------------------


def run_hook(name, envelope, tmp_path, extra_env=None):
    env = dict(os.environ, HOOK_TRIGGER_LOG=str(tmp_path / "triggers.jsonl"))
    env.update(extra_env or {})
    cmd = [sys.executable if name.endswith(".py") else "bash", str(HOOKS_DIR / name)]
    return subprocess.run(cmd, input=json.dumps(envelope), capture_output=True, text=True,
                          env=env, cwd=str(tmp_path))


def as_agent(envelope, agent_id):
    return dict(envelope, agent_id=agent_id, agent_type="researcher", session_id=SESSION)


@pytest.fixture
def own_tmp_trackers():
    """The bash hooks write to the real /tmp under this process's PID; remove what we made."""
    yield
    for path in glob.glob(f"/tmp/claude-*-{os.getpid()}"):
        os.unlink(path)


def test_region_dup_read_counts_each_sibling_separately(tmp_path, own_tmp_trackers):
    read = {"tool_name": "Read", "tool_input": {"file_path": f"{tmp_path}/BRIEF.md"}}
    siblings = [run_hook("posttool-dup-read.sh", as_agent(read, f"sib{n}"), tmp_path) for n in range(7)]
    assert [(p.returncode, p.stdout) for p in siblings] == [(0, "")] * 7
    one = [run_hook("posttool-dup-read.sh", as_agent(read, "loner"), tmp_path) for _ in range(6)]
    assert [p.returncode for p in one] == [0, 0, 0, 0, 0, 2]


def test_search_burst_counts_each_sibling_separately(tmp_path, own_tmp_trackers):
    search = {"tool_name": "WebSearch", "tool_input": {"query": "q"}}
    for n in range(3):
        for _ in range(9):
            proc = run_hook("pretool-search-burst.sh", as_agent(search, f"sib{n}"), tmp_path)
            assert (proc.returncode, proc.stderr) == (0, "")
    tenth = run_hook("pretool-search-burst.sh", as_agent(search, "sib0"), tmp_path)
    assert tenth.returncode == 0 and "10 search queries" in tenth.stderr


def test_bash_poll_counts_each_sibling_separately(tmp_path, own_tmp_trackers):
    target = tmp_path / "background_job_output.log"
    target.write_text("x")
    poll = {"tool_name": "Bash", "tool_input": {"command": f"wc -l {target}"}}
    for n in range(2):
        for _ in range(9):  # 18 polls in one process: a shared tracker blocks at 15
            proc = run_hook("posttool-bash-poll.sh", as_agent(poll, f"sib{n}"), tmp_path)
            assert (proc.returncode, proc.stdout) == (0, "")


def test_bash_failure_loop_counts_each_sibling_separately(tmp_path, own_tmp_trackers):
    failure = {"tool_name": "Bash", "tool_input": {"command": "false"},
               "exit_code": 1, "stderr": "error: boom"}
    for n in range(2):
        for _ in range(4):  # 8 failures in one process: a shared counter trips at 5
            proc = run_hook("posttool-bash-failure-loop.sh", as_agent(failure, f"sib{n}"), tmp_path)
            assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("hook,envelope,marker", [
    ("posttool-bgrun-watcher-nudge.sh",
     {"tool_name": "Bash", "tool_input": {"command": "bgrun lane7 -- python3 train.py"}},
     "WATCHER-PAIRING"),
    ("pretool-modal-run-detach-nudge.sh",
     {"tool_name": "Bash", "tool_input": {"command": "modal run train.py"}},
     "detach"),
])
def test_parent_only_nudges_skip_subagents(hook, envelope, marker, tmp_path):
    parent = run_hook(hook, dict(envelope, session_id=SESSION), tmp_path)
    assert marker in parent.stdout + parent.stderr
    child = run_hook(hook, as_agent(envelope, "a12bfef463b73db2f"), tmp_path)
    assert (child.returncode, child.stdout, child.stderr) == (0, "", "")


def test_no_wired_hook_reads_the_variables_claude_code_never_sets():
    """CLAUDE_AGENT_ID and CLAUDE_SESSION_ID do not exist in a hook's environment. Allowed:
    the identity libs (fallback order), the settings guard's belt-and-braces check, scripts
    that run inside the Bash tool's shell, and the un-wired parity oracles."""
    allowed = {
        "lib_hook_identity.py", "lib_hook_identity.sh",
        "pretool-subagent-settings-guard.py",
        "prepare-commit-msg-session-id.sh", "agent-zsh-safe.sh",  # Bash-tool shell, has the var
        "pretool-skill-log.sh", "posttool-skill-log.sh",  # read CLAUDE_CODE_SESSION_ID first
        "pretool-companion-remind.sh", "pretool-cost-awareness.sh",  # un-wired oracles
        "pretool-bash-dispatch.py",  # falls back to the PID, which is the scope it wants
    }
    offenders = []
    for path in sorted(HOOKS_DIR.glob("*")):
        if path.suffix not in {".py", ".sh"} or path.name in allowed or path.name.startswith("test_"):
            continue
        text = path.read_text(errors="replace")
        for token in ("CLAUDE_AGENT_ID", "CLAUDE_SESSION_ID"):
            if any(token in line and not line.lstrip().startswith("#") and "CLAUDE_CODE_" + token[7:] not in line
                   for line in text.splitlines()):
                offenders.append(f"{path.name}: {token}")
    assert offenders == [], offenders
