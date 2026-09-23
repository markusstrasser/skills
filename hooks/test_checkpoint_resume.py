#!/usr/bin/env python3
"""Tests for checkpoint_resume — the single-source resume-checkpoint selection.

Regression target (genomics 2026-07-06): a resuming session read a stale 2-day-old
DIFFERENT-session checkpoint.md because the writer had diverted the fresh content to
checkpoint-autogen.md and the reader hardcoded checkpoint.md. These pin the selection
+ stale-remnant contract both consumers rely on.

Run: cd ~/Projects/skills/hooks && python3 -m pytest test_checkpoint_resume.py -q
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import checkpoint_resume as cr

HOOK_DIR = Path(__file__).resolve().parent


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
    assert (
        cr.is_stale_remnant(str(tmp_path / "nope.md"), "sess", now=1_000_000.0) is False
    )


def test_remnant_respects_custom_floor(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "peer")
    _touch_mtime(str(p), now - 5 * 3600)
    assert cr.is_stale_remnant(str(p), "me", now=now, max_age_h=12.0) is False
    assert cr.is_stale_remnant(str(p), "me", now=now, max_age_h=4.0) is True


# ─── is_curated + the curated-clobber guard ──────────────────────────


def _write_signed(path, session, stamp, body="body"):
    with open(path, "w") as fh:
        fh.write(
            "# Resume Checkpoint\n<!-- session: %s -->\n\nWritten by PreCompact hook at %s.\n\n%s\n"
            % (session, stamp, body)
        )


def _stamp_for(epoch):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epoch))


def test_curated_when_no_hook_signature(tmp_path):
    path = tmp_path / "checkpoint.md"
    _write(str(path), "sess-ME", "## Pending Tasks\n- finish")
    assert cr.is_curated(str(path)) is True


def test_not_curated_for_the_hooks_own_fresh_write(tmp_path):
    path = tmp_path / "checkpoint.md"
    written = 1_000_000_000
    _write_signed(str(path), "sess-ME", _stamp_for(written))
    _touch_mtime(str(path), written + 59)  # minute-resolution stamp: the same write
    assert cr.is_curated(str(path)) is False


def test_curated_when_edited_after_the_hook_wrote_it(tmp_path):
    path = tmp_path / "checkpoint.md"
    written = 1_000_000_000
    _write_signed(str(path), "sess-ME", _stamp_for(written))
    _touch_mtime(str(path), written + 600)
    assert cr.is_curated(str(path)) is True


def test_curated_false_for_missing(tmp_path):
    assert cr.is_curated(str(tmp_path / "nope.md")) is False


def test_select_prefers_curated_own_file_over_fresher_extract(tmp_path):
    """The writer diverted its extract beside a curated file; the reader must send the
    resuming agent to the curated file and name the extract."""
    now = 1_000_000.0
    curated = tmp_path / "checkpoint.md"
    extract = tmp_path / "checkpoint-autogen.md"
    _write(str(curated), "sess-ME", "## Pending Tasks\n- finish")
    _write_signed(str(extract), "sess-ME", _stamp_for(now - 60))
    _touch_mtime(str(curated), now - 3600)
    _touch_mtime(str(extract), now - 60)
    sel = cr.select_for_read(str(tmp_path), "sess-ME", now=now)
    assert sel["basename"] == "checkpoint.md"
    assert sel["curated"] is True
    assert sel["extract_sibling"] == "checkpoint-autogen.md"
    msg = cr.resume_message(str(tmp_path), "sess-ME", now=now)
    assert "`%s` first" % curated in msg
    assert "`%s`" % extract in msg


def test_select_newest_own_file_when_none_is_curated(tmp_path):
    now = 1_000_000.0
    older = tmp_path / "checkpoint.md"
    newer = tmp_path / "checkpoint-autogen.md"
    _write_signed(str(older), "sess-ME", _stamp_for(now - 7200))
    _write_signed(str(newer), "sess-ME", _stamp_for(now - 60))
    _touch_mtime(str(older), now - 7200)
    _touch_mtime(str(newer), now - 60)
    sel = cr.select_for_read(str(tmp_path), "sess-ME", now=now)
    assert sel["basename"] == "checkpoint-autogen.md"
    assert sel["curated"] is False
    assert sel["extract_sibling"] is None


def _run_writer(tmp_path, session, cwd=None):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("")
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {
            "session_id": session,
            "cwd": str(cwd or tmp_path / "proj"),
            "transcript_path": str(transcript),
            "trigger": "auto",
        }
    )
    proc = subprocess.run(
        [sys.executable, str(HOOK_DIR / "precompact-extract.py")],
        input=payload,
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc


def test_writer_diverts_beside_a_curated_own_checkpoint(tmp_path):
    """End to end: the PreCompact writer must not clobber the session's hand-written file."""
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    curated = claude_dir / "checkpoint.md"
    _write(str(curated), "sess-ME", "## Pending Tasks\n- finish the thing")
    before = curated.read_text()

    _run_writer(tmp_path, "sess-ME")

    assert curated.read_text() == before
    extract = claude_dir / "checkpoint-autogen.md"
    assert extract.is_file()
    assert "Written by PreCompact hook at" in extract.read_text()
    assert cr.is_curated(str(extract)) is False
    sel = cr.select_for_read(str(claude_dir), "sess-ME")
    assert sel["basename"] == "checkpoint.md"
    assert sel["extract_sibling"] == "checkpoint-autogen.md"


def test_writer_still_overwrites_its_own_signed_checkpoint(tmp_path):
    """Negative control: the hook's own fresh, unedited file keeps the overwrite path."""
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    own = claude_dir / "checkpoint.md"
    written = time.time() - 30
    _write_signed(str(own), "sess-ME", _stamp_for(written), body="old extract")
    _touch_mtime(str(own), written)

    _run_writer(tmp_path, "sess-ME")

    assert not (claude_dir / "checkpoint-autogen.md").exists()
    text = own.read_text()
    assert "Written by PreCompact hook at" in text
    assert "old extract" not in text


# ─── project root: hook cwd drifts into subdirectories ───────────────
# iq-sex-differences 2026-09-23: a PreCompact from analysis/ wrote
# analysis/.claude/checkpoint.md with an empty Branch, the tracked root checkpoint
# stayed stale, and the resume read a 3-week-old file.


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
         "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _repo_with_subdir(tmp_path, tracked_checkpoint=None):
    proj = tmp_path / "proj"
    sub = proj / "analysis"
    sub.mkdir(parents=True)
    _git(proj, "init", "-q", "-b", "main")
    if tracked_checkpoint is not None:
        (proj / ".claude").mkdir()
        (proj / ".claude" / "checkpoint.md").write_text(tracked_checkpoint)
        _git(proj, "add", "-f", ".claude/checkpoint.md")
    _git(proj, "commit", "-q", "--allow-empty", "-m", "init")
    return proj.resolve(), sub.resolve()


def test_project_root_from_a_subdir_is_the_toplevel(tmp_path):
    proj, sub = _repo_with_subdir(tmp_path)
    assert cr.git_toplevel(str(sub)) == str(proj)
    assert cr.project_root(str(sub)) == str(proj)


def test_project_root_outside_git_is_cwd(tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert cr.git_toplevel(str(plain)) is None
    assert cr.project_root(str(plain)) == str(plain)


def test_writer_reads_git_state_in_a_linked_worktree(tmp_path):
    """A linked worktree's `.git` is a FILE; the old isdir probe left Branch empty."""
    proj, _ = _repo_with_subdir(tmp_path)
    wt = tmp_path / "wt"
    _git(proj, "worktree", "add", "-q", "-b", "wtb", str(wt))
    assert (wt / ".git").is_file()

    _run_writer(tmp_path, "sess-ME", cwd=wt)

    assert "- **Branch:** `wtb`" in (wt / ".claude" / "checkpoint.md").read_text()


def test_writer_files_a_subdir_checkpoint_at_the_toplevel(tmp_path):
    proj, sub = _repo_with_subdir(tmp_path)

    _run_writer(tmp_path, "sess-ME", cwd=sub)

    assert not (sub / ".claude").exists()
    text = (proj / ".claude" / "checkpoint.md").read_text()
    assert "<!-- session: sess-ME -->" in text
    assert "- **Branch:** `main`" in text


def test_writer_diverts_beside_a_tracked_toplevel_checkpoint_from_a_subdir(tmp_path):
    """The incident shape: tracked root checkpoint.md, compaction fired in analysis/."""
    curated = "# Handoff\n<!-- session: old-sess -->\nhand-written\n"
    proj, sub = _repo_with_subdir(tmp_path, tracked_checkpoint=curated)

    _run_writer(tmp_path, "sess-ME", cwd=sub)

    assert not (sub / ".claude").exists()
    assert (proj / ".claude" / "checkpoint.md").read_text() == curated
    extract = proj / ".claude" / "checkpoint-autogen.md"
    assert "Written by PreCompact hook at" in extract.read_text()
    sel = cr.select_for_read(str(proj / ".claude"), "sess-ME")
    assert sel["basename"] == "checkpoint-autogen.md"
    assert sel["is_current"] is True


@pytest.mark.skipif(shutil.which("jq") is None, reason="the hook parses its envelope with jq")
def test_sessionstart_reader_resolves_the_toplevel_from_a_subdir(tmp_path):
    proj, sub = _repo_with_subdir(tmp_path)
    sid = "ckpt-root-test-%d" % os.getpid()
    claude_dir = proj / ".claude"
    claude_dir.mkdir()
    _write(str(claude_dir / "checkpoint.md"), sid)
    (proj / "docs" / "decisions").mkdir(parents=True)
    (proj / "docs" / "decisions" / "REFRAMINGS.md").write_text("## scope — settled\n")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CLAUDE_TOOL_INPUT", "CLAUDE_HOOK_SMOKE", "CODEX_HOOK_COMPAT_SMOKE")
    }
    try:
        proc = subprocess.run(
            ["bash", str(HOOK_DIR / "sessionstart-compact-resume.sh")],
            input=json.dumps({"source": "compact", "cwd": str(sub), "session_id": sid}),
            text=True,
            capture_output=True,
            env=env,
            timeout=60,
        )
    finally:
        Path("/tmp/claude-postcompact-%s" % sid).unlink(missing_ok=True)

    assert proc.returncode == 0, proc.stderr
    context = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Read `%s` first (this session's fresh" % (claude_dir / "checkpoint.md") in context
    assert "scope — settled" in context
