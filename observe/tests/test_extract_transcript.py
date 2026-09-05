"""Tests for transcript source resolution and empty-versus-failed extraction."""
from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import extract_transcript as et  # noqa: E402
import extract_codex_transcript as ect  # noqa: E402


@pytest.fixture
def transcript_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(et, "TRANSCRIPT_BASE", tmp_path)
    return tmp_path


def test_resolve_prefers_canonical_over_topic_subdir(transcript_root: Path) -> None:
    canonical = transcript_root / "-Users-alien-Projects-agent-infra"
    subdir = transcript_root / "-Users-alien-Projects-agent-infra-research-papers-2026-06-20-refute"
    canonical.mkdir()
    subdir.mkdir()
    (canonical / "main.jsonl").write_text("{}\n")
    (subdir / "topic.jsonl").write_text("{}\n")

    resolved = et.resolve_project_dir("agent-infra")
    assert resolved == canonical


def test_find_transcripts_respects_days_window(transcript_root: Path) -> None:
    project_dir = transcript_root / "-Users-alien-Projects-agent-infra"
    project_dir.mkdir()
    recent = project_dir / "recent.jsonl"
    old = project_dir / "old.jsonl"
    recent.write_text("{}\n")
    old.write_text("{}\n")

    import os
    import time

    now = time.time()
    os.utime(recent, (now, now))
    os.utime(old, (now - 30 * 86400, now - 30 * 86400))

    found = et.find_transcripts("agent-infra", limit=5, days=7)
    assert [p.name for p in found] == ["recent.jsonl"]


@pytest.mark.parametrize("outside_window", [False, True])
def test_claude_empty_success_replaces_stale_output(
    transcript_root: Path, monkeypatch: pytest.MonkeyPatch, outside_window: bool,
) -> None:
    project_dir = transcript_root / "-Users-alien-Projects-agent-infra"
    project_dir.mkdir()
    if outside_window:
        (project_dir / "old.jsonl").write_text("{}\n")
    out = transcript_root / "output.md"
    out.write_text("previous run")
    monkeypatch.setattr(sys, "argv", ["extract_transcript.py", "agent-infra", "--days", "0", "--output", str(out)])

    assert et.main() is None
    assert out.read_text() == ""


def test_claude_missing_project_fails_without_erasing_output(
    transcript_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = transcript_root / "output.md"
    out.write_text("previous run")
    monkeypatch.setattr(sys, "argv", ["extract_transcript.py", "absent", "--output", str(out)])

    with pytest.raises(SystemExit) as error:
        et.main()
    assert error.value.code == 1
    assert out.read_text() == "previous run"


@pytest.mark.parametrize("outside_window", [False, True])
def test_codex_empty_success_replaces_stale_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outside_window: bool,
) -> None:
    database = tmp_path / "state.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE threads (cwd TEXT, updated_at REAL)")
        if outside_window:
            connection.execute("INSERT INTO threads VALUES (?, ?)", ("/projects/agent-infra", 0))
    monkeypatch.setattr(ect, "CODEX_DB", database)
    out = tmp_path / "output.md"
    out.write_text("previous run")
    monkeypatch.setattr(sys, "argv", ["extract_codex_transcript.py", "agent-infra", "--days", "1", "--output", str(out)])

    assert ect.main() is None
    assert out.read_text() == ""


@pytest.mark.parametrize("database_exists", [False, True])
def test_codex_missing_or_broken_database_preserves_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, database_exists: bool,
) -> None:
    database = tmp_path / "state.sqlite"
    if database_exists:
        database.touch()  # SQLite opens it, but the required threads table is absent.
    monkeypatch.setattr(ect, "CODEX_DB", database)
    out = tmp_path / "output.md"
    out.write_text("previous run")
    monkeypatch.setattr(sys, "argv", ["extract_codex_transcript.py", "agent-infra", "--output", str(out)])

    expected = sqlite3.OperationalError if database_exists else SystemExit
    with pytest.raises(expected) as error:
        ect.main()
    if not database_exists:
        assert error.value.code == 1
    assert out.read_text() == "previous run"
