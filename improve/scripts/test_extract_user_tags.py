"""Pin extract_user_tags.py against the real Claude Code transcript shapes.

Regression guard for the 2026-07-05 silent-false-zero: the extractor read
msg["content"] with a fallback to msg["message"] (a dict), so every modern
transcript line ({"type":"user","message":{"role":"user","content":...}})
yielded no text and #f harvest reported 0 forever.

Run: uv run python3 -m pytest scripts/test_extract_user_tags.py -q
"""

import json

from extract_user_tags import _message_texts, scan_session, tag_re


def _envelope(content):
    """Modern Claude Code line: text nested inside the message dict."""
    return {"type": "user", "message": {"role": "user", "content": content}}


def test_envelope_string_content():
    assert _message_texts(_envelope("do the thing #f")) == ["do the thing #f"]


def test_envelope_block_content_text_only():
    blocks = [
        {"type": "text", "text": "real feedback #g"},
        {"type": "tool_result", "content": "#f inside tool output must not count"},
    ]
    assert _message_texts(_envelope(blocks)) == ["real feedback #g"]


def test_legacy_flat_shape():
    assert _message_texts({"role": "user", "content": "flat #f works"}) == [
        "flat #f works"
    ]


def test_assistant_lines_ignored():
    msg = {"type": "assistant", "message": {"role": "assistant", "content": "#f"}}
    assert _message_texts(msg) == []


def test_harness_injected_lines_ignored():
    compact = _envelope("This session is being continued ... old #f quoted")
    compact["isCompactSummary"] = True
    assert _message_texts(compact) == []
    meta = _envelope("injected #g")
    meta["isMeta"] = True
    assert _message_texts(meta) == []


def test_tag_re_word_boundary():
    f = tag_re("f")
    assert f.search("fix this #f")
    assert f.search("#f leading")
    assert f.search("trailing #f")
    assert f.search("mid #f sentence")
    assert not f.search("#foo is not feedback")
    assert not f.search("ref #fg")
    g = tag_re("g")
    assert g.search("global issue #g do it everywhere")
    assert not g.search("#gt")


def test_scan_session_end_to_end(tmp_path):
    skill_inject = _envelope(
        "Base directory for this skill: /x\n# Improve\nuses #f tags"
    )
    lines = [
        _envelope("Nothing else you can parallelize? #g #f"),
        _envelope([{"type": "text", "text": "block form #f too"}]),
        {"type": "assistant", "message": {"role": "assistant", "content": "#f no"}},
        _envelope("no tag here"),
        skill_inject,
    ]
    p = tmp_path / "session.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines))

    hits = scan_session(p, tag_re("f"))
    assert [h["line"] for h in hits] == [1, 2]
    assert hits[0]["feedback"].startswith("Nothing else")

    g_hits = scan_session(p, tag_re("g"))
    assert [h["line"] for h in g_hits] == [1]
