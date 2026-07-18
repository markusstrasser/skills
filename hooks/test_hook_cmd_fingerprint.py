"""Both-polarity tests for hook_cmd_fingerprint.py — the command fingerprinting
primitive T1 (guard-forcerate-study) wires into hook-trigger-log.sh.

Positive: real commands fingerprint to the expected coarse first_token and a
deterministic, non-empty sha8. Negative: empty/whitespace-only commands never
fingerprint to something truthy, and the raw command is never recoverable
from the outputs (only ever asserted indirectly here — this module simply
never returns or logs the input string, verified by inspecting its return
shape)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hook_cmd_fingerprint import fingerprint_command  # noqa: E402


def test_empty_command_fingerprints_empty():
    assert fingerprint_command("") == ("", "")
    assert fingerprint_command(None) == ("", "")
    assert fingerprint_command("   \n\t  ") == ("", "")


def test_simple_command_first_token():
    tok, sha = fingerprint_command("git commit -m test")
    assert tok == "git"
    assert len(sha) == 8
    assert all(c in "0123456789abcdef" for c in sha)


def test_llmx_first_token():
    tok, _ = fingerprint_command("llmx chat -m gpt-5.6 -e high 'ping'")
    assert tok == "llmx"


def test_env_assignment_prefix_skipped():
    tok, _ = fingerprint_command("PYTHONUNBUFFERED=1 python3 foo.py")
    assert tok == "python3"


def test_multiple_env_assignments_skipped():
    tok, _ = fingerprint_command("FOO=1 BAR=baz git status")
    assert tok == "git"


def test_wrapper_commands_skipped():
    assert fingerprint_command("nohup python3 foo.py &")[0] == "python3"
    assert fingerprint_command("sudo rm -rf /tmp/x")[0] == "rm"
    assert fingerprint_command("time git log")[0] == "git"


def test_absolute_path_basenamed():
    tok, _ = fingerprint_command("/usr/bin/git stash list")
    assert tok == "git"


def test_determinism_same_command_same_fingerprint():
    a = fingerprint_command("git commit --only file.py -m 'msg'")
    b = fingerprint_command("git commit --only file.py -m 'msg'")
    assert a == b


def test_whitespace_normalization_same_hash():
    a = fingerprint_command("git   status")
    b = fingerprint_command("git status")
    c = fingerprint_command("  git status  ")
    assert a == b == c


def test_different_commands_different_hash():
    a = fingerprint_command("git commit --only a.py")
    b = fingerprint_command("git commit --only b.py")
    assert a[0] == b[0]  # same first token
    assert a[1] != b[1]  # different fingerprint — the command actually changed


def test_raw_command_never_in_return_value():
    """Negative control: neither return element may equal or contain the
    full raw command — a fingerprint that leaked the command would defeat
    the whole point of not persisting it."""
    cmd = "llmx chat -m gpt-5.6 --subscription 'a very specific secret-looking prompt'"
    tok, sha = fingerprint_command(cmd)
    assert cmd not in tok
    assert cmd not in sha
    assert "secret-looking" not in tok
    assert "secret-looking" not in sha


def test_only_wrappers_and_assignments_yields_empty_token():
    """Degenerate case: nothing but wrappers/assignments — no real command
    survives. Must not crash, must not return a wrapper name as the token."""
    tok, sha = fingerprint_command("FOO=1 nohup sudo")
    assert tok == ""
    # sha is still computed from the (nonempty) normalized text — only the
    # first_token extraction can come up empty.
    assert len(sha) == 8


def test_malformed_shell_quoting_falls_back_without_crashing():
    # Unbalanced quote — shlex.split raises ValueError; must fall back to a
    # plain whitespace split rather than propagating the exception.
    tok, sha = fingerprint_command("echo 'unbalanced")
    assert tok == "echo"
    assert len(sha) == 8


def test_cli_main_prints_token_and_sha(capsys):
    import hook_cmd_fingerprint

    old_argv = sys.argv
    try:
        sys.argv = ["hook_cmd_fingerprint.py", "git status"]
        hook_cmd_fingerprint.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out.strip()
    parts = out.split()
    assert len(parts) == 2
    assert parts[0] == "git"
    assert len(parts[1]) == 8
