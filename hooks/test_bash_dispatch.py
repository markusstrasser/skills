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
import runpy
import subprocess
import sys

import pytest

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
DISPATCHER = os.path.join(HOOKS_DIR, "pretool-bash-dispatch.py")
SNAPSHOT = os.path.join(HOOKS_DIR, "_bash_gates_pre_dispatch_snapshot.json")
_DISPATCHER_NAMESPACE = runpy.run_path(DISPATCHER)
_GIT_NOEXT_VERDICT = _DISPATCHER_NAMESPACE["_git_noext_inject_verdict"]


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


def _noext_verdict(command: str) -> tuple[str, str]:
    return _GIT_NOEXT_VERDICT({"command": command})


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
    # The frozen shell oracle re-quotes every shlex token; that legacy behavior
    # is the defect, not a parity contract for the raw-splice dispatcher.
    assert oracle["final_command"] == "git --no-pager diff --no-ext-diff 'HEAD~1'"
    assert disp["final_command"] == "git --no-pager diff --no-ext-diff HEAD~1"


def test_git_noext_injects_into_compound_segments(git_sandbox):
    command = "cd /repo; git -C /w diff --stat main -- f | grep '^[+-]'"
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, git_sandbox["env"], git_sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        "cd /repo; git -C /w --no-pager diff --no-ext-diff --stat main -- f | grep '^[+-]'"
    )


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            'true && git diff "$BASE" -- "$FILE"',
            'true && git --no-pager diff --no-ext-diff "$BASE" -- "$FILE"',
        ),
        (
            'GIT_DIR="$PWD/.git" git log -1',
            'GIT_DIR="$PWD/.git" git --no-pager log --no-ext-diff -1',
        ),
        (
            "echo before; git diff --stat & wait",
            "echo before; git --no-pager diff --no-ext-diff --stat & wait",
        ),
        (
            "git status; cat <<'EOF'\n EOF\ngit diff data;\nEOF\ngit log -1",
            "git status; cat <<'EOF'\n EOF\ngit diff data;\nEOF\n"
            "git --no-pager log --no-ext-diff -1",
        ),
    ],
)
def test_git_noext_splice_only_regressions(sandbox, command, expected):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == expected


def test_git_noext_keeps_git_globals_and_quoted_pipe_data(sandbox):
    command = 'cd /r; git -C /w diff main -- "$F" | grep \'^[+-]\''
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        'cd /r; git -C /w --no-pager diff --no-ext-diff main -- "$F" | grep \'^[+-]\''
    )


@pytest.mark.parametrize("prefix", ["!", "time", "command", "exec"])
def test_git_noext_skips_shell_prefix_words(sandbox, prefix):
    command = f'{prefix} GIT_DIR="$PWD/.git" git diff "$BASE"'
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        f'{prefix} GIT_DIR="$PWD/.git" git --no-pager diff --no-ext-diff "$BASE"'
    )


def test_git_noext_changes_only_the_two_splice_points(sandbox):
    command = (
        'time GIT_DIR="$PWD/.git" command git -C "/w d"\tdiff "$BASE" -- "$FILE" '
        '2> "$ERR" & wait # keep ; $TAIL'
    )
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    rewritten = disp["final_command"]
    assert rewritten == (
        'time GIT_DIR="$PWD/.git" command git -C "/w d" --no-pager\tdiff'
        ' --no-ext-diff "$BASE" -- "$FILE" 2> "$ERR" & wait # keep ; $TAIL'
    )
    assert rewritten.replace(" --no-pager", "", 1).replace(
        " --no-ext-diff", "", 1
    ) == command


def test_git_noext_heredoc_dash_strips_only_leading_tabs(sandbox):
    command = "git status; cat <<-'EOF'\n\tbody;\n\tEOF\ngit show HEAD"
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        "git status; cat <<-'EOF'\n\tbody;\n\tEOF\n"
        "git --no-pager show --no-ext-diff HEAD"
    )


@pytest.mark.parametrize(
    "command",
    [
        '( git diff HEAD )',
        '( echo x; git diff HEAD )',
        '{ git diff HEAD; }',
        '{ echo x; git show HEAD; }',
        'for ref in HEAD; do git diff "$ref"; done',
        'for ref in HEAD; do echo "$ref"; git diff "$ref"; done',
        'git diff "unterminated',
    ],
)
def test_git_noext_ambiguous_shell_forms_fail_open(sandbox, command):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == command


def test_git_noext_accepts_nonword_heredoc_delimiter(sandbox):
    command = (
        "git status; cat <<'END-DATA'\n"
        "git diff data;\n"
        "END-DATA\n"
        "git log -1"
    )
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        "git status; cat <<'END-DATA'\n"
        "git diff data;\n"
        "END-DATA\n"
        "git --no-pager log --no-ext-diff -1"
    )


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            ">out git diff HEAD",
            ">out git --no-pager diff --no-ext-diff HEAD",
        ),
        (
            "git 2>/dev/null diff HEAD",
            "git --no-pager 2>/dev/null diff --no-ext-diff HEAD",
        ),
        (
            "git -C /w 2>err diff HEAD",
            "git -C /w --no-pager 2>err diff --no-ext-diff HEAD",
        ),
        (
            "{fd}>out git diff HEAD",
            "{fd}>out git --no-pager diff --no-ext-diff HEAD",
        ),
    ],
)
def test_git_noext_skips_redirects_before_subcommand(sandbox, command, expected):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == expected
    assert disp["final_command"].replace(" --no-pager", "", 1).replace(
        " --no-ext-diff", "", 1
    ) == command


def test_git_noext_skips_c_and_generic_git_globals(sandbox):
    command = "git -c color.ui=always --literal-pathspecs diff HEAD"
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        "git -c color.ui=always --literal-pathspecs --no-pager "
        "diff --no-ext-diff HEAD"
    )


@pytest.mark.parametrize(
    ("command", "expected", "injection_count"),
    [
        (
            "echo x; git --no-pager diff --cached --stat",
            "echo x; git --no-pager diff --no-ext-diff --cached --stat",
            1,
        ),
        (
            "git diff main -- a && git diff main -- b",
            "git --no-pager diff --no-ext-diff main -- a"
            " && git --no-pager diff --no-ext-diff main -- b",
            2,
        ),
        (
            "echo before; git show HEAD | git log --oneline; echo after",
            "echo before; git --no-pager show --no-ext-diff HEAD"
            " | git --no-pager log --no-ext-diff --oneline; echo after",
            2,
        ),
        (
            "false || git log -1\ngit show HEAD",
            "false || git --no-pager log --no-ext-diff -1\n"
            "git --no-pager show --no-ext-diff HEAD",
            2,
        ),
    ],
)
def test_git_noext_compound_forms_rewrite_only_git_segments(
    sandbox, command, expected, injection_count
):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == expected
    assert disp["final_command"].count("--no-ext-diff") == injection_count


def test_git_noext_quoted_command_text_is_not_rewritten(sandbox):
    command = 'echo "git diff x; y"'
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == command


def test_git_noext_keeps_heredoc_and_comment_data_opaque(sandbox):
    command = (
        "git status; cat <<'EOF'\n"
        "git diff data; git show data\n"
        "EOF\n"
        "# git diff comment; git show comment\n"
        "git log -1"
    )
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp["final_command"] == (
        "git status; cat <<'EOF'\n"
        "git diff data; git show data\n"
        "EOF\n"
        "# git diff comment; git show comment\n"
        "git --no-pager log --no-ext-diff -1"
    )


def test_git_noext_compound_rewrite_is_idempotent(sandbox):
    command = "echo x; git diff main -- a && git --no-pager log --no-ext-diff -1"
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    first = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert first["exit_code"] == 0
    second_envelope = {
        "tool_name": "Bash",
        "tool_input": {"command": first["final_command"]},
    }
    second = run_dispatcher(second_envelope, sandbox["env"], sandbox["cwd"])
    assert second["exit_code"] == 0
    assert second["final_command"] == first["final_command"]
    proc = subprocess.run(
        ["python3", DISPATCHER],
        input=json.dumps(second_envelope),
        capture_output=True,
        text=True,
        timeout=30,
        env=sandbox["env"],
        cwd=sandbox["cwd"],
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_git_noext_compound_keeps_nongit_guard_behavior(sandbox):
    simple_envelope = {
        "tool_name": "Bash",
        "tool_input": {"command": "grep --no-ext-diff needle file"},
    }
    simple = run_dispatcher(simple_envelope, sandbox["env"], sandbox["cwd"])
    command = "git diff main -- a; grep --no-ext-diff needle file"
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, sandbox["env"], sandbox["cwd"])
    assert simple["exit_code"] == 2
    assert disp["exit_code"] == 2
    assert disp["block_msg"] == simple["block_msg"]
    assert "GIT-ONLY flag" in disp["block_msg"]
    assert "applied it to 'grep'" in disp["block_msg"]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "printf '%s\\n' ${fallback:-plain;git diff HEAD}",
            ("pass", ""),
        ),
        (
            "${x:-a}; git diff",
            ("mutate", "${x:-a}; git --no-pager diff --no-ext-diff"),
        ),
        (
            "${outer:-${inner:-a;git diff HEAD}}; git log -1",
            (
                "mutate",
                "${outer:-${inner:-a;git diff HEAD}}; "
                "git --no-pager log --no-ext-diff -1",
            ),
        ),
        (
            "printf %s $(git diff HEAD); git log -1",
            (
                "mutate",
                "printf %s $(git diff HEAD); "
                "git --no-pager log --no-ext-diff -1",
            ),
        ),
        (
            "printf %s $(printf x # )\n); git diff HEAD",
            (
                "mutate",
                "printf %s $(printf x # )\n); "
                "git --no-pager diff --no-ext-diff HEAD",
            ),
        ),
        (
            "printf %s $( (printf x)# comment )\n); git diff HEAD",
            (
                "mutate",
                "printf %s $( (printf x)# comment )\n); "
                "git --no-pager diff --no-ext-diff HEAD",
            ),
        ),
        (
            "printf %s $(cat <<'EOF'\n)\nEOF\n); git diff HEAD",
            (
                "mutate",
                "printf %s $(cat <<'EOF'\n)\nEOF\n); "
                "git --no-pager diff --no-ext-diff HEAD",
            ),
        ),
        (
            'printf "%s\\n" "$((1 << 2))"; git diff HEAD',
            (
                "mutate",
                'printf "%s\\n" "$((1 << 2))"; '
                "git --no-pager diff --no-ext-diff HEAD",
            ),
        ),
        (
            "printf %s `git diff HEAD`; git log -1",
            (
                "mutate",
                "printf %s `git diff HEAD`; "
                "git --no-pager log --no-ext-diff -1",
            ),
        ),
    ],
)
def test_git_noext_keeps_expansions_opaque(command, expected):
    assert _noext_verdict(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        "printf %s ${fallback:-plain;git diff HEAD",
        "printf %s $(git diff HEAD",
        "printf %s `git diff HEAD",
        'echo "$(printf x"; git diff HEAD',
        'echo "${x:-y"; git diff HEAD',
        'echo "`printf x"; git diff HEAD',
    ],
)
def test_git_noext_unbalanced_expansions_fail_open(command):
    assert _noext_verdict(command) == ("pass", "")


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "git diff HEAD & printf '%s\\n' --no-ext-diff",
            "git --no-pager diff --no-ext-diff HEAD & "
            "printf '%s\\n' --no-ext-diff",
        ),
        (
            "sleep 1 & git log -1",
            "sleep 1 & git --no-pager log --no-ext-diff -1",
        ),
        (
            "git diff HEAD 2>&1 | head",
            "git --no-pager diff --no-ext-diff HEAD 2>&1 | head",
        ),
        (
            "git diff HEAD |& head",
            "git --no-pager diff --no-ext-diff HEAD |& head",
        ),
        (
            "git diff HEAD &>out",
            "git --no-pager diff --no-ext-diff HEAD &>out",
        ),
        (
            "git diff HEAD &>>out",
            "git --no-pager diff --no-ext-diff HEAD &>>out",
        ),
        (
            "git diff HEAD >&2",
            "git --no-pager diff --no-ext-diff HEAD >&2",
        ),
        (
            "git diff HEAD <&0",
            "git --no-pager diff --no-ext-diff HEAD <&0",
        ),
    ],
)
def test_git_noext_distinguishes_background_separators_from_redirects(
    command, expected
):
    verdict, rewritten = _noext_verdict(command)
    assert verdict == "mutate"
    assert rewritten == expected
    assert rewritten.replace(" --no-pager", "", 1).replace(
        " --no-ext-diff", "", 1
    ) == command


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            'git "diff" HEAD',
            'git --no-pager "diff" --no-ext-diff HEAD',
        ),
        (
            '"git" diff HEAD',
            '"git" --no-pager diff --no-ext-diff HEAD',
        ),
        (
            r"g\it d\iff HEAD",
            r"g\it --no-pager d\iff --no-ext-diff HEAD",
        ),
        (
            "time -p git diff HEAD",
            "time -p git --no-pager diff --no-ext-diff HEAD",
        ),
        (
            "command -p git show HEAD",
            "command -p git --no-pager show --no-ext-diff HEAD",
        ),
        (
            "exec -a git-alias git log -1",
            "exec -a git-alias git --no-pager log --no-ext-diff -1",
        ),
        (
            "git diff HEAD -- --no-ext-diff",
            "git --no-pager diff --no-ext-diff HEAD -- --no-ext-diff",
        ),
    ],
)
def test_git_noext_classifies_unquoted_words_and_prefix_options(command, expected):
    verdict, rewritten = _noext_verdict(command)
    assert verdict == "mutate"
    assert rewritten == expected
    assert rewritten.replace(" --no-pager", "", 1).replace(
        " --no-ext-diff", "", 1
    ) == command


def test_git_noext_recognizes_quoted_existing_flag():
    command = 'git --no-pager diff "--no-ext-diff" HEAD'
    assert _noext_verdict(command) == ("pass", "")


@pytest.mark.parametrize("option", ["-v", "-V"])
def test_git_noext_leaves_command_query_modes_unchanged(option):
    command = f"command {option} git show HEAD"
    assert _noext_verdict(command) == ("pass", "")


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "git -C --no-ext-diff diff HEAD",
            "git -C --no-ext-diff --no-pager diff --no-ext-diff HEAD",
        ),
        (
            "git -C -- diff HEAD",
            "git -C -- --no-pager diff --no-ext-diff HEAD",
        ),
    ],
)
def test_git_noext_ignores_global_option_operands_during_flag_detection(
    command, expected
):
    assert _noext_verdict(command) == ("mutate", expected)
    assert _noext_verdict(expected) == ("pass", "")


@pytest.mark.parametrize(
    "command",
    [
        "${x:-a}; git diff",
        "git diff HEAD & printf '%s\\n' --no-ext-diff",
        "sleep 1 & git log -1",
        'git "diff" HEAD',
        '"git" diff HEAD',
        "time -p git diff HEAD",
        "git diff HEAD -- --no-ext-diff",
    ],
)
def test_git_noext_pass2_round_trips_are_idempotent(command):
    verdict, rewritten = _noext_verdict(command)
    assert verdict == "mutate"
    assert _noext_verdict(rewritten) == ("pass", "")


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


def test_worktree_cd_persistent_blocks(sandbox):
    envelope = {
        "tool_name": "Bash",
        "tool_input": {"command": "cd /repo/.claude/worktrees/codex-x && git log --oneline -3"},
    }
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 2
    assert "persistent cwd" in disp["block_msg"]
    assert "git -C /repo/.claude/worktrees/codex-x" in disp["block_msg"]


@pytest.mark.parametrize(
    "command",
    [
        "git -C /repo/.claude/worktrees/codex-x status --short",
        "(cd /repo/.claude/worktrees/codex-x && git status --short)",
        "cd /repo && ls .claude/worktrees/",
        "W=/repo/.claude/worktrees/codex-x; ls $W/scripts | head -3",
    ],
)
def test_worktree_paths_without_persistent_cd_pass(sandbox, command):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 0
