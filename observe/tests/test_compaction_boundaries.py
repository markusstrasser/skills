"""Tests for the compaction-boundary lane: contract detection, carry-over, re-read share."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import compaction_boundaries as cb  # noqa: E402

OLD = " ".join(f"w{i}" for i in range(40))
CONTRACT_SUMMARY = (
    "This is a lossy compaction summary; the files it lists are the source of truth.\n"
    "## Re-read before relying on details\n- /repo/src/a.py\n- /repo/docs/b.md\n" + OLD
)


def boundary(ts: str) -> dict:
    return {"type": "system", "subtype": "compact_boundary", "timestamp": ts,
            "compactMetadata": {"trigger": "auto", "preTokens": 470_000}}


def summary(text: str) -> dict:
    return {"type": "user", "isCompactSummary": True, "message": {"content": text}}


def tool(name: str, **inp) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def write(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "proj" / "s1.jsonl"
    path.parent.mkdir()
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def test_contract_reread_and_carry(tmp_path: Path) -> None:
    rows = [
        boundary("2026-10-15T00:00:00Z"), summary("plain summary " + OLD),
        boundary("2026-10-15T01:00:00Z"), summary(CONTRACT_SUMMARY),
        {"type": "attachment", "attachment": {"type": "compact_file_reference", "filename": "/repo/c.ts"}},
        {"type": "attachment", "attachment": {"type": "file", "filename": "/repo/docs/b.md"}},
        tool("Read", file_path="/repo/src/a.py"),
        tool("Bash", command="sed -n 1,20p /repo/elsewhere.py"),
    ]
    first, second = [cb.finish(b) for b in cb.boundaries(write(tmp_path, rows))]
    assert first["contract"] is False and first["refs"] == 0 and first["reread"] is None
    assert second["contract"] is True
    # refs = a.py (section) + c.ts (reference); b.md was restored with content, so excluded
    assert second["refs"] == 2 and second["reread"] == 0.5
    assert second["unopened"] == ["/repo/c.ts"]
    assert second["carry12"] > 0.5  # the 40-word tail carried over verbatim


def test_window_caps_counted_tools(tmp_path: Path) -> None:
    rows = [boundary("2026-10-15T00:00:00Z"), summary(CONTRACT_SUMMARY)]
    rows += [tool("Bash", command="true")] * cb.WINDOW
    rows += [tool("Read", file_path="/repo/src/a.py")]
    (row,) = [cb.finish(b) for b in cb.boundaries(write(tmp_path, rows))]
    assert row["reread"] == 0.0


def test_unread_edit_error_counted(tmp_path: Path) -> None:
    err = {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": True,
           "content": "File has not been read yet. Read it first before writing to it."}]}}
    rows = [boundary("2026-10-15T00:00:00Z"), summary("s"), err]
    (row,) = [cb.finish(b) for b in cb.boundaries(write(tmp_path, rows))]
    assert row["unread_err"] == 1
