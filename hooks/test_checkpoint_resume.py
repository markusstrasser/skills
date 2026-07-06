#!/usr/bin/env python3
"""Tests for checkpoint_resume — the single-source resume-checkpoint selection.

Regression target (genomics 2026-07-06): a resuming session read a stale 2-day-old
DIFFERENT-session checkpoint.md because the writer had diverted the fresh content to
checkpoint-autogen.md and the reader hardcoded checkpoint.md. These pin the selection
+ stale-remnant contract both consumers rely on.

Run: cd ~/Projects/skills/hooks && python3 -m pytest test_checkpoint_resume.py -q
"""

import os

import checkpoint_resume as cr


def _write(path, session, body="body"):
    with open(path, "w") as fh:
        fh.write("# Resume Checkpoint\n<!-- session: %s -->\n\n%s\n" % (session, body))


def _touch_mtime(path, mtime):
    os.utime(path, (mtime, mtime))


# ─── read_session_stamp ──────────────────────────────────────────────


def test_read_session_stamp_present(tmp_path):
    p = tmp_path / "checkpoint.md"
    _write(str(p), "sess-A")
    assert cr.read_session_stamp(str(p)) == "sess-A"


def test_read_session_stamp_missing_file(tmp_path):
    assert cr.read_session_stamp(str(tmp_path / "nope.md")) is None


def test_read_session_stamp_no_stamp(tmp_path):
    p = tmp_path / "checkpoint.md"
    p.write_text("# Resume Checkpoint\nno stamp here\n")
    assert cr.read_session_stamp(str(p)) is None


# ─── select_for_read ─────────────────────────────────────────────────


def test_select_none_when_empty(tmp_path):
    assert cr.select_for_read(str(tmp_path), "sess-A") is None


def test_select_prefers_current_session_over_newer_sibling(tmp_path):
    """THE regression: autogen (mine) is OLDER than a peer's checkpoint.md, but I
    must still resume off MY checkpoint, not the newer peer file."""
    now = 1_000_000.0
    mine = tmp_path / "checkpoint-autogen.md"
    peer = tmp_path / "checkpoint.md"
    _write(str(mine), "sess-ME")
    _write(str(peer), "sess-PEER")
    _touch_mtime(str(mine), now - 3600)  # 1h old (mine)
    _touch_mtime(str(peer), now - 60)  # newer, but a different session
    sel = cr.select_for_read(str(tmp_path), "sess-ME", now=now)
    assert sel["basename"] == "checkpoint-autogen.md"
    assert sel["session"] == "sess-ME"
    assert sel["is_current"] is True
    assert sel["sibling_count"] == 1


def test_select_newest_when_no_session_match(tmp_path):
    now = 1_000_000.0
    a = tmp_path / "checkpoint.md"
    b = tmp_path / "checkpoint-autogen.md"
    _write(str(a), "sess-OLD")
    _write(str(b), "sess-OLDER")
    _touch_mtime(str(a), now - 4000)
    _touch_mtime(str(b), now - 8000)
    sel = cr.select_for_read(str(tmp_path), "sess-ME", now=now)
    assert sel["basename"] == "checkpoint.md"  # newest of the two
    assert sel["is_current"] is False
    assert sel["age_hours"] > 1.0


def test_select_single_current_file(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "sess-ME")
    _touch_mtime(str(p), now - 1800)
    sel = cr.select_for_read(str(tmp_path), "sess-ME", now=now)
    assert sel["is_current"] is True
    assert sel["sibling_count"] == 0
    assert sel["age_hours"] == 0.5


# ─── resume_message ──────────────────────────────────────────────────


def test_resume_message_current_is_positive(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "sess-ME")
    _touch_mtime(str(p), now - 600)
    msg = cr.resume_message(str(tmp_path), "sess-ME", now=now)
    assert "this session's fresh resume checkpoint" in msg
    assert "checkpoint.md" in msg


def test_resume_message_cross_session_warns(tmp_path):
    """The exact bug: chosen file is a different session -> message must warn, not
    call it 'fresh'."""
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "1cf836e3")
    _touch_mtime(str(p), now - 48 * 3600)  # 2 days old, like the incident
    msg = cr.resume_message(str(tmp_path), "be0657a9", now=now)
    assert "NOT this resuming session" in msg
    assert "may be stale" in msg
    assert "git log" in msg
    assert "fresh resume checkpoint" not in msg


def test_resume_message_empty_when_none(tmp_path):
    assert cr.resume_message(str(tmp_path), "sess-ME") == ""


def test_resume_message_current_but_old_adds_verify(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "sess-ME")
    _touch_mtime(str(p), now - 20 * 3600)  # 20h — current session but old
    msg = cr.resume_message(str(tmp_path), "sess-ME", now=now)
    assert "verify" in msg.lower()
    assert "git log" in msg


# ─── is_stale_remnant ────────────────────────────────────────────────


def test_remnant_true_for_old_different_session(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "1cf836e3")
    _touch_mtime(str(p), now - 48 * 3600)  # 2 days -> dead remnant
    assert cr.is_stale_remnant(str(p), "be0657a9", now=now) is True


def test_remnant_false_for_own_session(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "be0657a9")
    _touch_mtime(str(p), now - 48 * 3600)  # old, but MINE -> not a "reclaim"
    assert cr.is_stale_remnant(str(p), "be0657a9", now=now) is False


def test_remnant_false_for_fresh_peer(tmp_path):
    """A live concurrent peer (recent write) must be protected, not reclaimed."""
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "peer-live")
    _touch_mtime(str(p), now - 2 * 3600)  # 2h < 12h floor
    assert cr.is_stale_remnant(str(p), "be0657a9", now=now) is False


def test_remnant_false_for_missing(tmp_path):
    assert cr.is_stale_remnant(str(tmp_path / "nope.md"), "sess", now=1_000_000.0) is False


def test_remnant_respects_custom_floor(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "peer")
    _touch_mtime(str(p), now - 5 * 3600)
    assert cr.is_stale_remnant(str(p), "me", now=now, max_age_h=12.0) is False
    assert cr.is_stale_remnant(str(p), "me", now=now, max_age_h=4.0) is True
