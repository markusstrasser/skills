"""Tests for extract_transcript project-dir resolution."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import extract_transcript as et  # noqa: E402


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
