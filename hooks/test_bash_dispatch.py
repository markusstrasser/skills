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
_NOEXT_NONGIT_HIT = _DISPATCHER_NAMESPACE["_noext_nongit_hit"]


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


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        # shlex joins adjacent operators into one token; `);` and `)&&` still end the segment.
        ("( cd /w && echo ok 2>&1 | tail -2 ); git -C /w diff --cached --no-ext-diff --stat", None),
        ("(tail -2)&& git diff --no-ext-diff", None),
        ("tail -2 >/dev/null);git log --no-ext-diff -1", None),
        # Controls: a redirection run is not a separator, and real misuse still blocks.
        ("tail -2 2>&1 --no-ext-diff", "tail"),
        ("( rg --no-ext-diff foo )", "rg"),
        ("git diff | grep --no-ext-diff x", "grep"),
        # A heredoc body is stdin data; the command after its terminator is still scanned.
        ("cat > m.txt <<'MSG'\nsee ( rg --no-ext-diff foo )\nMSG\ngit log -1", None),
        ("cat > m.txt <<MSG\n( rg --no-ext-diff foo )\nMSG", None),
        ("cat > m.txt <<'MSG'\nbody\nMSG\nrg --no-ext-diff x", "rg"),
        # A newline ends a command, also after a comment; a quoted newline does not.
        ("tail -5 log\ngit diff --no-ext-diff", None),
        ("tail f # note\ngit diff --no-ext-diff", None),
        ("git status\nrg --no-ext-diff x", "rg"),
        ('git commit -m "a\nrg --no-ext-diff"', None),
        ("rg x \\\n  --no-ext-diff", "rg"),
    ],
)
def test_noext_nongit_segments_reset_on_joined_operator_runs(command, expected):
    assert _NOEXT_NONGIT_HIT(command) == expected


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


@pytest.mark.parametrize("model", ["claude-opus-4-8", "claude-opus-5-5", "claude-fable-5-1"])
def test_opus_concurrency_advises_at_three_or_more(sandbox, tmp_path, model):
    envelope = {"tool_name": "Bash", "tool_input": {"command": f"llmx chat -m {model} -e max hi"}}
    env = dict(sandbox["env"])
    env["OPUS_LOAD_PGREP_BIN"] = _fake_pgrep_bin(tmp_path, 3)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert disp.get("additionalContext") and "concurrent opus-family streams" in disp["additionalContext"]


def test_opus_concurrency_silent_below_three(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "llmx chat -m claude-opus-5-5 -e max hi"}}
    env = dict(sandbox["env"])
    env["OPUS_LOAD_PGREP_BIN"] = _fake_pgrep_bin(tmp_path, 1)
    disp = run_dispatcher(envelope, env, sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert not disp.get("additionalContext")


def test_opus_concurrency_ignores_non_opus_models(sandbox, tmp_path):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "llmx chat -m gpt-6-sol -e max hi"}}
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


def test_timeout_around_modal_container_exec_passes_the_crawl_guard(sandbox):
    """`container exec` is a bounded stream the streaming guard requires a timeout on;
    the crawl guard must not refuse that same timeout (2026-09-02 contradiction)."""
    envelope = {
        "tool_name": "Bash",
        "tool_input": {
            "command": 'timeout 60 uv run python3 -m modal container exec ta-01ABC -- sh -c "cat /proc/loadavg"'
        },
    }
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 0


@pytest.mark.parametrize(
    "command",
    [
        "gsutil -m rm -r gs://bucket/cache",
        "gsutil rm -R gs://bucket/prefix",
        "gsutil rm 'gs://bucket/prefix/**'",
        "gsutil rb gs://bucket",
        "gcloud storage rm --recursive gs://bucket/x",
        "gcloud storage buckets delete gs://bucket",
        "aws s3 rm s3://bucket/x --recursive",
        "aws s3 rb s3://bucket --force",
        "history -c 2>/dev/null; fc -ln -1 >/dev/null 2>&1; echo ok",
        "cd /tmp && bash -c 'gsutil -m rm -r gs://bucket/cache'",
        "ls | xargs gsutil -m rm -r",
    ],
)
def test_remote_delete_guard_blocks(sandbox, command):
    """Opus 5.5 System Card §6.3.1 shapes: hallucinated `history -c` and `gsutil -m rm -r`."""
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 2
    assert "`! <command>`" in disp["block_msg"]


@pytest.mark.parametrize(
    "command",
    [
        "gsutil ls gs://bucket",
        "gsutil rm gs://bucket/one-object.txt",
        "gsutil cp -r gs://bucket/x /tmp/x",
        "gcloud storage ls --recursive gs://bucket",
        "aws s3 ls s3://bucket --recursive",
        "modal volume rm genomics-data /results/old.bam",
        "history | tail -5",
        "rg -e 'gsutil -m rm -r' -e 'history -c' .",
        "echo 'gsutil -m rm -r gs://bucket'",
    ],
)
def test_remote_delete_guard_passes(sandbox, command):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 0


# ---------------------------------------------------------------------------
# git-history-guard (2026-09-23): history rewrites in a checkout shared with peers.
# Peer detection is forced through PEER_SESSION_COUNT_BIN, as for the stash guard.
# ---------------------------------------------------------------------------

sys.path.insert(0, HOOKS_DIR)
import pretool_git_history_guard as _ghg  # noqa: E402

_SIMPLE_COMMANDS = _DISPATCHER_NAMESPACE["_simple_commands"]

# session_id of a real Bash PreToolUse envelope recorded by pretool-universal-dispatch.py's
# opt-in probe (/tmp/claude-hook-envelope-probe.log, 2026-09-21), with that envelope's key
# set. The probe records names and ids only, so the non-identity values are placeholders.
# The same records list the hook process's CLAUDE* variables: CLAUDE_CODE_SESSION_ID is
# present and CLAUDE_SESSION_ID is not.
MINE = "adae2b38-fa63-4fd0-b727-08c73975b287"
PEER = "7d3f29c0-9e1b-4c2a-8f00-5a5a5a5a5a5a"
_RECORDED_BASH_ENVELOPE_KEYS = [
    "cwd", "effort", "hook_event_name", "permission_mode", "prompt_id", "scratchpad_dir",
    "session_id", "tool_input", "tool_name", "tool_use_id", "transcript_path",
]


def _history_env(sandbox, tmp_path, peers):
    env = dict(sandbox["env"])
    for name in ("CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID"):
        env.pop(name, None)
    env["PEER_SESSION_COUNT_BIN"] = _fake_peer_bin(tmp_path, peers)
    return env


def _make_history(sandbox, owners):
    """One commit per owner (None = no Session-ID trailer); returns the shas, oldest first."""
    repo, env = sandbox["cwd"], sandbox["env"]
    for args in (["init", "-q"], ["config", "user.email", "t@t.co"], ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=repo, env=env, check=True)
    shas = []
    for n, owner in enumerate(owners):
        with open(os.path.join(repo, "f.txt"), "a") as f:
            f.write(f"line {n}\n")
        with open(os.path.join(repo, "g.txt"), "a") as f:
            f.write(f"line {n}\n")
        subprocess.run(["git", "add", "f.txt", "g.txt"], cwd=repo, env=env, check=True)
        message = ["-m", f"commit {n}"] + (["-m", f"Session-ID: {owner}"] if owner else [])
        subprocess.run(["git", "commit", "-q", *message], cwd=repo, env=env, check=True)
        shas.append(
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, env=env, capture_output=True, text=True, check=True
            ).stdout.strip()
        )
    return shas


def _run_history(sandbox, tmp_path, command, *, peers=1, session=MINE, cwd=None, env_extra=None):
    env = _history_env(sandbox, tmp_path, peers)
    env.update(env_extra or {})
    where = cwd or sandbox["cwd"]
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": where}
    if session:
        envelope["session_id"] = session
    return run_dispatcher(envelope, env, where)


_AMEND_FORMS = [
    "git commit --amend --no-edit",
    "git commit -a --amend",
    "git commit -am 'reword' --amend",
    "GIT_EDITOR=true git commit --amend",
]


@pytest.mark.parametrize("owners", [[PEER, MINE], [MINE, PEER], [MINE, None]], ids=["own", "foreign", "untagged"])
@pytest.mark.parametrize("command", _AMEND_FORMS)
def test_git_history_guard_blocks_every_amend_with_peers(sandbox, tmp_path, owners, command):
    """--amend commits the whole shared index, so HEAD ownership does not make it safe
    (arc-agi 2026-07-10: a self-amend swept two peer-staged rows)."""
    head = _make_history(sandbox, owners)[-1]
    disp = _run_history(sandbox, tmp_path, command)
    assert disp["exit_code"] == 2, disp
    msg = disp["block_msg"]
    assert "1 peer session(s) share this checkout" in msg
    assert "--amend commits the whole shared index and rewrites HEAD" in msg
    owner = f"session {owners[-1][:8]}" if owners[-1] else "no Session-ID"
    assert f"HEAD {head[:7]} ({owner})" in msg
    assert "make a follow-up commit instead" in msg


_FOREIGN_HEAD_BLOCKS = [
    "git reset --soft HEAD~1",
    "git reset --mixed HEAD~1",
    "git reset --keep HEAD~1",
    "git reset --merge HEAD~1",
    "git reset HEAD~1",
    "git reset -q {base}",
    "git reset",
    "git rebase -i HEAD~1",
    "git rebase --onto {base} HEAD~1",
    "timeout 30 git rebase -i HEAD~1",
    "git -C {repo} reset --soft HEAD~1",
    "cd {repo} && git reset --soft HEAD~1",
    'R={repo}; git -C "$R" reset --soft HEAD~1',
    "(cd {repo} && git reset --soft HEAD~1)",
]


@pytest.mark.parametrize("template", _FOREIGN_HEAD_BLOCKS)
def test_git_history_guard_blocks_rewrite_of_foreign_head(sandbox, tmp_path, template):
    base, head = _make_history(sandbox, [MINE, PEER])
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    command = template.format(repo=sandbox["cwd"], base=base)
    cwd = str(elsewhere) if "{repo}" in template else None
    disp = _run_history(sandbox, tmp_path, command, cwd=cwd)
    assert disp["exit_code"] == 2, disp
    msg = disp["block_msg"]
    assert f"HEAD {head[:7]}" in msg
    assert f"session {PEER[:8]}" in msg
    assert "1 live peer session(s)" in msg
    assert "fix forward with a new commit" in msg.lower()


@pytest.mark.parametrize(
    "command",
    [
        "git commit --amend --no-edit",
        "git reset --soft HEAD~1",
        "git reset HEAD~1",
        "git reset",
        "git rebase -i HEAD~1",
        "git reset --hard",
    ],
)
def test_git_history_guard_solo_never_fires(sandbox, tmp_path, command):
    _make_history(sandbox, [MINE, PEER])
    disp = _run_history(sandbox, tmp_path, command, peers=0)
    assert disp["exit_code"] == 0, disp


@pytest.mark.parametrize(
    "command",
    ["git reset --soft HEAD~1", "git reset HEAD~1", "git reset", "git rebase -i HEAD~1"],
)
def test_git_history_guard_allows_own_head_with_peers(sandbox, tmp_path, command):
    _make_history(sandbox, [PEER, MINE])
    disp = _run_history(sandbox, tmp_path, command)
    assert disp["exit_code"] == 0, disp


def test_git_history_guard_blocks_head_without_trailer(sandbox, tmp_path):
    _, head = _make_history(sandbox, [MINE, None])
    disp = _run_history(sandbox, tmp_path, "git reset --soft HEAD~1")
    assert disp["exit_code"] == 2
    assert f"HEAD {head[:7]}" in disp["block_msg"]
    assert "no Session-ID" in disp["block_msg"]


def test_git_history_guard_checks_every_commit_the_reset_drops(sandbox, tmp_path):
    """HEAD is this session's, but HEAD~1 (also dropped by HEAD~2) is the peer's."""
    _, peer_commit, head = _make_history(sandbox, [MINE, PEER, MINE])
    disp = _run_history(sandbox, tmp_path, "git reset --soft HEAD~2")
    assert disp["exit_code"] == 2
    assert f"HEAD {head[:7]} is yours" in disp["block_msg"]
    assert f"{peer_commit[:7]} in the rewritten range" in disp["block_msg"]


@pytest.mark.parametrize(
    "command",
    [
        "git reset -- f.txt",
        "git reset HEAD -- f.txt",
        "git reset f.txt g.txt",
        "git reset f.txt",
        "git reset -q -- f.txt g.txt",
        "git reset -p",
        "git reset --pathspec-from-file=paths.txt",
    ],
)
def test_git_history_guard_allows_path_scoped_reset(sandbox, tmp_path, command):
    _make_history(sandbox, [MINE, PEER])
    disp = _run_history(sandbox, tmp_path, command)
    assert disp["exit_code"] == 0, disp


@pytest.mark.parametrize(
    "command",
    [
        "git rebase --continue",
        "git rebase --abort",
        "git rebase --skip",
        "git rebase --quit",
        "git rebase --edit-todo",
        "git rebase --show-current-patch",
    ],
)
def test_git_history_guard_allows_rebase_controls(sandbox, tmp_path, command):
    _make_history(sandbox, [MINE, PEER])
    disp = _run_history(sandbox, tmp_path, command)
    assert disp["exit_code"] == 0, disp


@pytest.mark.parametrize(
    "template",
    ["git reset --hard", "git reset --hard HEAD", "git reset -q --hard HEAD~1", "W={repo}; git -C $W reset --hard HEAD"],
)
def test_git_history_guard_blocks_reset_hard_even_on_own_head(sandbox, tmp_path, template):
    _, head = _make_history(sandbox, [PEER, MINE])
    disp = _run_history(sandbox, tmp_path, template.format(repo=sandbox["cwd"]))
    assert disp["exit_code"] == 2, disp
    msg = disp["block_msg"]
    assert "discards every uncommitted change" in msg
    assert f"HEAD is {head[:7]} (session {MINE[:8]})" in msg
    assert "1 live peer session(s)" in msg
    assert "fix forward with a new commit" in msg


def test_git_history_guard_reads_identity_from_recorded_envelope(sandbox, tmp_path):
    """Envelope with the recorded key set; hook env as recorded: CLAUDE_CODE_SESSION_ID only."""
    _make_history(sandbox, [PEER, MINE])
    env = _history_env(sandbox, tmp_path, 1)
    env["CLAUDE_CODE_SESSION_ID"] = MINE
    envelope = {key: f"<{key}>" for key in _RECORDED_BASH_ENVELOPE_KEYS}
    envelope.update(
        tool_name="Bash",
        tool_input={"command": "git reset --soft HEAD~1"},
        cwd=sandbox["cwd"],
        session_id=MINE,
        hook_event_name="PreToolUse",
    )
    assert sorted(envelope) == _RECORDED_BASH_ENVELOPE_KEYS
    assert "CLAUDE_SESSION_ID" not in env
    assert run_dispatcher(envelope, env, sandbox["cwd"])["exit_code"] == 0
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "peer", "-m", f"Session-ID: {PEER}"],
        cwd=sandbox["cwd"], env=sandbox["env"], check=True,
    )
    assert run_dispatcher(envelope, env, sandbox["cwd"])["exit_code"] == 2


def test_git_history_guard_accepts_codex_thread_id(sandbox, tmp_path):
    _make_history(sandbox, [PEER, MINE])
    disp = _run_history(
        sandbox, tmp_path, "git reset --soft HEAD~1", session=None, env_extra={"CODEX_THREAD_ID": MINE}
    )
    assert disp["exit_code"] == 0, disp


def test_git_history_guard_without_any_identity_cannot_claim_head(sandbox, tmp_path):
    _make_history(sandbox, [PEER, MINE])
    disp = _run_history(sandbox, tmp_path, "git reset --soft HEAD~1", session=None)
    assert disp["exit_code"] == 2


@pytest.mark.parametrize(
    "command",
    [
        'git -C "$NOT_SET_ANYWHERE" reset --soft HEAD~1',
        "echo 'git reset --soft HEAD~1' > notes.txt",
        "cat > notes.md <<'EOF'\ngit reset --hard HEAD\nEOF",
        "git log --grep 'git reset --soft' -1 --format=%h",
    ],
)
def test_git_history_guard_fails_open_or_ignores_data(sandbox, tmp_path, command):
    _make_history(sandbox, [MINE, PEER])
    disp = _run_history(sandbox, tmp_path, command)
    assert disp["exit_code"] == 0, disp


def test_git_history_guard_fails_open_when_peer_detector_breaks(sandbox, tmp_path):
    _make_history(sandbox, [MINE, PEER])
    env = _history_env(sandbox, tmp_path, 1)
    env["PEER_SESSION_COUNT_BIN"] = str(tmp_path / "missing-peer-bin")
    envelope = {
        "tool_name": "Bash",
        "tool_input": {"command": "git reset --soft HEAD~1"},
        "cwd": sandbox["cwd"],
        "session_id": MINE,
    }
    assert run_dispatcher(envelope, env, sandbox["cwd"])["exit_code"] == 0


def test_git_history_guard_fails_open_outside_a_repo(sandbox, tmp_path):
    disp = _run_history(sandbox, tmp_path, "git reset --soft HEAD~1")
    assert disp["exit_code"] == 0


def test_git_history_guard_logs_block_and_exposure_rows(sandbox, tmp_path):
    _make_history(sandbox, [PEER, MINE])
    assert _run_history(sandbox, tmp_path, "git reset --soft HEAD~1")["exit_code"] == 0
    assert _run_history(sandbox, tmp_path, "git reset --hard")["exit_code"] == 2
    rows = [r for r in _read_trigger_log(sandbox) if r.get("hook") == "git-history-guard"]
    assert [r["action"] for r in rows] == ["exposure-clean", "block"]
    assert all(r.get("cmd_tok") == "git" and "cmd" not in r for r in rows)
    assert "peers=1" in rows[0]["detail"] and "mode=hard" in rows[1]["detail"]


def _ops(command, base="/base", environ=None):
    return _ghg.find_ops(_SIMPLE_COMMANDS(command), base, environ or {"HOME": "/home/u"})


@pytest.mark.parametrize(
    "command",
    [
        "git commit --amen --no-edit",
        "git -c core.editor=true commit --amend",
        "command git commit -q --amend",
        "if git commit --amend --no-edit; then echo ok; fi",
        "git commit --amend -m -h",  # `-h` is the message here, not a help request
    ],
)
def test_git_history_parse_finds_amend(command):
    assert [op.verb for op in _ops(command)] == ["amend"]


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m --amend",
        "git commit --fixup=amend:HEAD",
        "git commit --amend --no-amend",
        "git commit -m x -- --amend",
        "echo 'git commit --amend'",
        "command -v git && echo 'git reset --hard'",
        "git reset HEAD -- a.py",
        "git reset a.py b.py",
        "git rebase --continue",
        # usage requests (seen in the 2026-09-23 agentlogs replay): git rewrites nothing
        "git rebase -h",
        "git reset -h",
        "git reset --help",
        "git commit --amend -h",
    ],
)
def test_git_history_parse_ignores_non_rewrites(command):
    assert _ops(command) == []


def test_git_history_parse_resolves_directories():
    (op,) = _ops("W=/x/wt; git -C $W reset --hard main")
    assert (op.target_dir, op.reset_mode, op.rev) == ("/x/wt", "hard", "main")
    (op,) = _ops("cd /a && git -C b reset --soft HEAD~1")
    assert op.target_dir == "/a/b"
    (op,) = _ops("(cd /a && git status); git reset --soft HEAD~1")
    assert op.target_dir == "/base"
    (op,) = _ops("cd ~/proj && git rebase -i HEAD~2")
    assert op.target_dir == "/home/u/proj"
    (op,) = _ops('git -C "$UNSET" reset --soft HEAD~1')
    assert op.target_dir is None


def test_git_history_parse_reset_and_rebase_targets():
    (op,) = _ops("git reset HEAD~1 --")
    assert op.rev == "HEAD~1" and not op.needs_disambiguation
    (op,) = _ops("git reset abc123")
    assert op.rev == "abc123" and op.needs_disambiguation
    (op,) = _ops('git reset --hard "$(git rev-parse main)"')
    assert op.rev is _ghg.UNKNOWN and op.reset_mode == "hard"
    (op,) = _ops("git rebase -x 'make test' HEAD~3")
    assert op.rev == "HEAD~3"
    (op,) = _ops("git rebase --onto main topic~2")
    assert op.rev == "topic~2"
    (op,) = _ops("git rebase")
    assert op.rev == "@{upstream}"


# ---------------------------------------------------------------------------
# rg-replace-flag-guard (2026-09-23): glued `rg -rn` is `--replace n`, not recursive.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command,cluster",
    [
        ("rg -rn foo .", "-rn"),
        ("rg -rln foo src/", "-rln"),
        ("rg -rl foo", "-rl"),
        ("rg -rc foo", "-rc"),
        ("rg -rin foo", "-rin"),
        ("rg -ril foo", "-ril"),
        ("cd /tmp && rg -rn foo", "-rn"),
        ("rg --glob '*.py' -rn foo", "-rn"),
        ("rg -rn foo src/ | head -5", "-rn"),
        ("timeout 20 rg -rln foo", "-rln"),
    ],
)
def test_rg_glued_replace_flag_advises(sandbox, command, cluster):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 0
    ctx = disp.get("additionalContext") or ""
    assert "rg is recursive by default; `-r` is `--replace`" in ctx
    assert f"`{cluster}` rewrites every match to `{cluster[2:]}`. Drop the `r`." in ctx


@pytest.mark.parametrize(
    "command",
    [
        "rg -r 'x' foo",
        "rg -r x foo",
        "rg --replace x foo",
        "rg --replace=x foo",
        "rg -e -rn file.txt",
        "rg -g -rn foo",
        "rg -nr foo",
        "rg -r2 foo",
        "rg -- -rn file.txt",
        "grep -rn foo .",
        "echo 'rg -rn foo'",
        "rg -n foo src/",
    ],
)
def test_rg_legit_forms_stay_silent(sandbox, command):
    envelope = {"tool_name": "Bash", "tool_input": {"command": command}}
    disp = run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    assert disp["exit_code"] == 0
    assert "--replace" not in (disp.get("additionalContext") or "")


def test_rg_glued_replace_logs_a_warn_row(sandbox):
    envelope = {"tool_name": "Bash", "tool_input": {"command": "rg -rln needle ."}}
    run_dispatcher(envelope, dict(sandbox["env"]), sandbox["cwd"])
    rows = [r for r in _read_trigger_log(sandbox) if r.get("hook") == "rg-replace-flag-guard"]
    assert [(r["action"], r["detail"]) for r in rows] == [("warn", "-rln")]
    assert rows[0].get("cmd_tok") == "rg" and "cmd" not in rows[0]
