"""The cat-guard must block missing files without blocking valid pipelines.

Regression anchor (2026-07-26): `$(cat real.md | wc -c)` was BLOCKED with
"missing: |" and "missing: wc" — find_cat_spans yielded the whole pipeline, so
the caller scanned a downstream command's argv as if those tokens were paths.
A guard that rejects correct commands teaches agents to route around it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "pretool_bash_cat_guard", Path(__file__).with_name("pretool_bash_cat_guard.py")
)
assert _SPEC and _SPEC.loader
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)


def missing_for(cmd: str, cwd: str) -> list[str]:
    """The filter both callers use (dispatch gate and the .sh wrapper's main)."""
    return guard.missing_paths(cmd, cwd)


# --- the false positive this test exists for -------------------------------


def test_pipeline_inside_cat_substitution_is_not_scanned(tmp_path):
    (tmp_path / "real.md").write_text("x")
    assert missing_for("n=$(cat real.md | wc -c)", str(tmp_path)) == []


def test_pipeline_without_spaces(tmp_path):
    (tmp_path / "real.md").write_text("x")
    assert missing_for("n=$(cat real.md|wc -c)", str(tmp_path)) == []


def test_chained_operators_are_not_scanned(tmp_path):
    (tmp_path / "real.md").write_text("x")
    assert missing_for("$(cat real.md && echo nope)", str(tmp_path)) == []
    assert missing_for("$(cat real.md ; echo nope)", str(tmp_path)) == []


# --- the guard's real job must still work ----------------------------------


def test_missing_file_still_blocks(tmp_path):
    assert missing_for("n=$(cat gone.md)", str(tmp_path)) == ["gone.md"]


def test_missing_file_still_blocks_before_a_pipe(tmp_path):
    assert missing_for("n=$(cat gone.md | wc -c)", str(tmp_path)) == ["gone.md"]


def test_multiple_args_all_checked(tmp_path):
    (tmp_path / "here.md").write_text("x")
    assert missing_for("$(cat here.md gone.md)", str(tmp_path)) == ["gone.md"]


def test_pipe_outside_the_substitution_is_unaffected(tmp_path):
    assert missing_for("$(cat gone.md) | wc -c", str(tmp_path)) == ["gone.md"]


def test_multiple_substitutions(tmp_path):
    (tmp_path / "a.md").write_text("x")
    assert missing_for("$(cat a.md | wc -c) $(cat b.md)", str(tmp_path)) == ["b.md"]


def test_cat_text_inside_a_quoted_heredoc_is_not_scanned(tmp_path):
    """2026-09-22: a Python patch script and a log entry, both inside <<'EOF', were blocked."""
    cmd = "python3 - <<'EOF'\nmsg = '$(cat <<PARTIALEOF\\nnot a file\\nPARTIALEOF\\n)'\nEOF\necho done"
    assert missing_for(cmd, str(tmp_path)) == []
    cmd = 'cat >> log.md <<"EOF"\n- read $(cat <<EOF ...) as a substitution\nEOF\n'
    assert missing_for(cmd, str(tmp_path)) == []


def test_heredoc_fed_cat_has_no_file_arguments(tmp_path):
    cmd = 'X=$(cat <<EOF\nsome words here\nEOF\n)\necho "$X"'
    assert missing_for(cmd, str(tmp_path)) == []
    assert missing_for('Y=$(cat <<< "two words")', str(tmp_path)) == []


def test_unquoted_heredoc_still_scans_real_substitutions(tmp_path):
    """Unquoted heredoc bodies DO expand, so a missing file there still blocks."""
    cmd = "cat <<EOF\nvalue: $(cat nope.txt)\nEOF"
    assert missing_for(cmd, str(tmp_path)) == ["nope.txt"]


def test_file_before_heredoc_marker_is_still_checked(tmp_path):
    assert missing_for("Z=$(cat gone.md <<EOF\nx\nEOF\n)", str(tmp_path)) == ["gone.md"]


# --- text the shell never expands (third 2026-09-22 false block and its class) ---


def test_escaped_dollar_is_not_a_substitution(tmp_path):
    """2026-09-22: a commit message saying "The \\$(cat ...) guard" was blocked on '...'."""
    assert missing_for('git commit -m "The \\$(cat ...) guard scanned words"', str(tmp_path)) == []


def test_single_quoted_and_commented_text_is_not_scanned(tmp_path):
    assert missing_for("python3 -c 'print(\"$(cat nope.txt)\")'", str(tmp_path)) == []
    assert missing_for("echo $'$(cat nope.txt)'", str(tmp_path)) == []
    assert missing_for("echo hi  # was $(cat nope.txt)", str(tmp_path)) == []


def test_commit_message_heredoc_inside_double_quotes_is_literal(tmp_path):
    """The form the backtick guard recommends: $( ) restarts quoting inside "...", so
    the <<'EOF' body stays literal even though the whole thing is double-quoted."""
    cmd = "git commit -m \"$(cat <<'EOF'\nSubject\n\nIt read $(cat nope.txt) and \"quotes\" too.\nEOF\n)\""
    assert missing_for(cmd, str(tmp_path)) == []


def test_apostrophe_in_unquoted_heredoc_body_does_not_desync_quotes(tmp_path):
    """Quotes are plain text in an unquoted body: the live substitution there is still
    checked, and the single-quoted one after the heredoc is still ignored."""
    cmd = "cat > f.md <<EOF\nit's $(cat nope.txt)\nEOF\necho '$(cat also-nope.txt)'"
    assert missing_for(cmd, str(tmp_path)) == ["nope.txt"]


def test_double_quoted_substitution_still_blocks(tmp_path):
    assert missing_for('echo "$(cat nope.txt)"', str(tmp_path)) == ["nope.txt"]


def test_quoted_argument_is_one_path(tmp_path):
    assert missing_for("x=$(cat 'my notes.md')", str(tmp_path)) == ["my notes.md"]
    (tmp_path / "my notes.md").write_text("x")
    assert missing_for("x=$(cat 'my notes.md')", str(tmp_path)) == []


def test_redirect_target_created_earlier_is_skipped(tmp_path):
    assert missing_for("echo x > made.md && y=$(cat made.md)", str(tmp_path)) == []
