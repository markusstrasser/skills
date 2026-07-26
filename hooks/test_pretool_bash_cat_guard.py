"""The cat-guard must block missing files without blocking valid pipelines.

Regression anchor (2026-07-26): `$(cat real.md | wc -c)` was BLOCKED with
"missing: |" and "missing: wc" — find_cat_spans yielded the whole pipeline, so
the caller scanned a downstream command's argv as if those tokens were paths.
A guard that rejects correct commands teaches agents to route around it.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "pretool_bash_cat_guard", Path(__file__).with_name("pretool_bash_cat_guard.py")
)
assert _SPEC and _SPEC.loader
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)


def missing_for(cmd: str, cwd: str) -> list[str]:
    """Mirror the caller's token filter over find_cat_spans (see dispatch gate)."""
    found: list[str] = []
    for span in guard.find_cat_spans(cmd):
        for tok in span.split():
            if tok.startswith("-") or tok in ("<<", "<<<"):
                continue
            if ">" in tok or "<" in tok:
                continue
            if any(c in tok for c in "$`*?[]{}~"):
                continue
            tok = tok.strip("\"'")
            if not tok:
                continue
            path = tok if os.path.isabs(tok) else os.path.join(cwd, tok)
            if not os.path.exists(path):
                found.append(tok)
    return list(dict.fromkeys(found))


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
