#!/usr/bin/env python3
"""Both-polarity, integration and drift tests for the secret-path guard.

The guard replaced two settings.json `Read()` deny rules on 2026-09-04. Those rules made the
auto-mode permission classifier stop for a human whenever a Bash read path could not be
resolved; the incident command below is therefore a MUST-NOT-FIRE control here — it never
touched a secret, it was only unresolvable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
import lib_bash_cmd_strip  # noqa: E402
import pretool_bash_backtick_guard  # noqa: E402
from pretool_secret_path_guard import offending_secret_path, reason  # noqa: E402

DISPATCHER = HOOKS_DIR / "pretool-bash-dispatch.py"
READ_GUARD = HOOKS_DIR / "pretool-secret-path-read-guard.py"
SETTINGS = Path.home() / ".claude" / "settings.json"

INCIDENT_COMMAND = (
    "cd /Users/alien/Projects/genomics; grep -n -B3 -A3 'config_consumer_map' justfile | head -30"
)

FIRES = [
    ("cat ~/.config/secrets/b2.env", ".config/secrets"),
    ("sops -d $HOME/.config/sops/age/keys.txt", ".config/sops/age"),
    ("cat /Users/alien/.config/secrets/x.json | jq .", ".config/secrets"),
    ("ls ~/.config/sec*", ".config/sec*"),
    ("cat ~/.config/*", ".config/*"),
    ("cd ~/.config && cat secrets/x", "secrets/"),
    ("cd ~/.config && cat sops/age/keys.txt", "sops/age"),
    # an UNQUOTED heredoc body still expands, so a substitution inside it is a real read
    ("cat > out.txt <<EOF\n$(cat ~/.config/secrets/b2.env)\nEOF", ".config/secrets"),
]

CLEAN = [
    INCIDENT_COMMAND,
    "ls ~/.config/gh/hosts.yml",
    "cat ~/.config/gh/*/hosts.yml",
    "git config --list",
    "rg secrets scripts/ | head",
    "grep -rn 'secrets' docs/ops/ | head",
    "sops -d config/secrets.enc.yaml",
    "cat ~/.modal.toml",
    "cd /Users/alien/Projects/genomics\nrg -n 'GateSpec' scripts/precommit_runner.py | head",
    "uv run python3 scripts/config_consumer_map.py --mode index",
    # a QUOTED-delimiter heredoc body is data the shell never expands: naming the paths is fine
    "cat > notes.md <<'EOF'\nThe ~/.config/secrets/ store and ~/.config/sops/age/keys.txt stay closed.\nEOF",
]


@pytest.mark.parametrize("command,token", FIRES)
def test_fires_on_every_incident_shaped_read(command, token):
    assert offending_secret_path(command) == token
    assert "protected secret store" in reason(token)


@pytest.mark.parametrize("command", CLEAN)
def test_stays_silent_on_ordinary_commands(command):
    assert offending_secret_path(command) is None


def test_quoted_heredoc_rule_has_one_definition():
    """The backtick guard and this guard must strip quoted heredocs by the SAME function object."""
    assert (
        pretool_bash_backtick_guard._strip_quoted_heredocs
        is lib_bash_cmd_strip.strip_quoted_heredocs
    )
    import pretool_secret_path_guard

    assert (
        pretool_secret_path_guard.strip_quoted_heredocs is lib_bash_cmd_strip.strip_quoted_heredocs
    )


def _hermetic_env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    return env


def _run(script: Path, envelope: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(envelope),
        capture_output=True,
        text=True,
        timeout=60,
        env=_hermetic_env(tmp_path),
        cwd=str(tmp_path),
    )


def test_dispatcher_blocks_a_bash_read_of_the_secret_store(tmp_path):
    proc = _run(
        DISPATCHER,
        {"tool_name": "Bash", "tool_input": {"command": "cat ~/.config/secrets/b2.env"}},
        tmp_path,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "protected secret store" in (proc.stdout + proc.stderr)


def test_dispatcher_passes_the_incident_command_and_ordinary_config_reads(tmp_path):
    for command in (INCIDENT_COMMAND, "ls ~/.config/gh/hosts.yml"):
        proc = _run(DISPATCHER, {"tool_name": "Bash", "tool_input": {"command": command}}, tmp_path)
        assert proc.returncode == 0, (command, proc.stdout, proc.stderr)
        assert "protected secret store" not in (proc.stdout + proc.stderr)


@pytest.mark.parametrize(
    "envelope",
    [
        {"tool_name": "Read", "tool_input": {"file_path": "/Users/alien/.config/secrets/b2.env"}},
        {
            "tool_name": "Read",
            "tool_input": {"file_path": "/Users/alien/.config/sops/age/keys.txt"},
        },
        {
            "tool_name": "Grep",
            "tool_input": {"pattern": "key", "path": "/Users/alien/.config/secrets"},
        },
        {"tool_name": "Glob", "tool_input": {"pattern": "/Users/alien/.config/sec*/**"}},
    ],
)
def test_read_twin_blocks_tool_reads_under_the_stores(envelope, tmp_path):
    proc = _run(READ_GUARD, envelope, tmp_path)
    assert proc.returncode == 2, proc.stderr
    assert envelope["tool_name"] in proc.stderr and "protected secret store" in proc.stderr


def test_read_twin_passes_ordinary_reads(tmp_path):
    for envelope in (
        {
            "tool_name": "Read",
            "tool_input": {"file_path": "/Users/alien/Projects/genomics/justfile"},
        },
        {
            "tool_name": "Grep",
            "tool_input": {"pattern": "secrets", "path": "/Users/alien/Projects/genomics/scripts"},
        },
        {"tool_name": "Read", "tool_input": {"file_path": "/Users/alien/.config/gh/hosts.yml"}},
    ):
        proc = _run(READ_GUARD, envelope, tmp_path)
        assert proc.returncode == 0, (envelope, proc.stderr)


def test_read_twin_fails_open_on_malformed_input(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(READ_GUARD)],
        input="not json {{{",
        capture_output=True,
        text=True,
        timeout=60,
        env=_hermetic_env(tmp_path),
    )
    assert proc.returncode == 0


def test_settings_carry_no_read_deny_rule_and_register_the_twin():
    """Drift pin: a re-added `Read()` deny rule re-creates the human prompt on every unresolvable
    path. Protection lives in the deterministic gates, not in a classifier-consulted deny list."""
    settings = json.loads(SETTINGS.read_text())
    deny = settings.get("permissions", {}).get("deny", [])
    assert not [rule for rule in deny if rule.startswith("Read(")], deny
    registered = [
        entry
        for entry in settings["hooks"]["PreToolUse"]
        if "Read" in (entry.get("matcher") or "")
        and any(
            hook.get("command", "").endswith("pretool-secret-path-read-guard.py")
            for hook in entry.get("hooks", [])
        )
    ]
    assert registered, "Read|Grep|Glob twin is not registered in ~/.claude/settings.json"
