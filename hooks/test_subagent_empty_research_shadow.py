#!/usr/bin/env python3
"""Test subagent-empty-research-shadow.py: pathological-empty fires, legitimate partial passes."""
import importlib.util
import json
import tempfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "shadow", Path(__file__).resolve().parent / "subagent-empty-research-shadow.py"
)
shadow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shadow)


def _transcript(tool_uses):
    """tool_uses: list of (name, input_dict) -> a JSONL transcript path."""
    d = Path(tempfile.mkdtemp())
    p = d / "t.jsonl"
    lines = []
    for name, inp in tool_uses:
        lines.append(json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]},
        }))
    p.write_text("\n".join(lines))
    return str(p)


def test_pathological_empty_fires():
    # 8 research calls, only the initial untagged stub write -> would_fire
    tu = [("mcp__research__search_papers", {"query": "x"})] * 4
    tu += [("WebFetch", {"url": "u"})] * 4
    tu += [("Write", {"content": "# Research memo\nPROBE IN PROGRESS\n"})]
    rec = shadow.evaluate(_transcript(tu))
    assert rec["would_fire"] is True, rec
    assert rec["research_calls"] == 8


def test_legitimate_partial_passes():
    # 8 research calls but a tagged finding written -> PASS (CORAL-correct)
    tu = [("mcp__research__search_papers", {"query": "x"})] * 8
    tu += [("Write", {"content": "# memo\n[SOURCE: arXiv:1234] finding one.\n[GAP] section 2 pending."})]
    rec = shadow.evaluate(_transcript(tu))
    assert rec["would_fire"] is False, rec
    assert rec["tagged_writes"] == 1


def test_below_threshold_passes():
    # only 2 research calls, no findings -> below N, PASS (a quick lookup that legitimately rests)
    tu = [("Read", {"file_path": "a"}), ("Grep", {"pattern": "b"})]
    rec = shadow.evaluate(_transcript(tu))
    assert rec["would_fire"] is False, rec


def test_edit_with_tag_passes():
    tu = [("WebSearch", {"query": "x"})] * 7
    tu += [("Edit", {"new_string": "[DATA] 42% measured."})]
    rec = shadow.evaluate(_transcript(tu))
    assert rec["would_fire"] is False, rec


def test_missing_transcript_fail_open():
    rec = shadow.evaluate("/nonexistent/xyz.jsonl")
    assert rec["would_fire"] is False
    assert rec["research_calls"] == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("OK: test_subagent_empty_research_shadow")
