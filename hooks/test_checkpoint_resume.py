#!/usr/bin/env python3
"""Tests for checkpoint_resume — the single-source resume-checkpoint selection.

Regression target (genomics 2026-07-06): a resuming session read a stale 2-day-old
DIFFERENT-session checkpoint.md because the writer had diverted the fresh content to
checkpoint-autogen.md and the reader hardcoded checkpoint.md. These pin the selection
+ stale-remnant contract both consumers rely on.

Run: cd ~/Projects/skills/hooks && python3 -m pytest test_checkpoint_resume.py -q
"""

import hashlib
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
    assert sel is not None
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
    assert sel is not None
    assert sel["basename"] == "checkpoint.md"  # newest of the two
    assert sel["is_current"] is False
    assert sel["age_hours"] > 1.0


def test_select_single_current_file(tmp_path):
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "sess-ME")
    _touch_mtime(str(p), now - 1800)
    sel = cr.select_for_read(str(tmp_path), "sess-ME", now=now)
    assert sel is not None
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
    assert sel is not None
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
    assert sel is not None
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
    assert sel is not None
    assert sel["basename"] == "checkpoint.md"
    assert sel["extract_sibling"] == "checkpoint-autogen.md"


def test_writer_diverts_beside_an_unstamped_hand_written_checkpoint(tmp_path):
    """Regression (immigration-research 2026-09-27 22:43): no session stamp and no hook
    signature must still count as curated; the extract goes beside it, never over it."""
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    curated = claude_dir / "checkpoint.md"
    curated.write_text(
        "# Resume Checkpoint — hand-written brief\n\n## NEXT\n- integrate the lanes\n\n---\n\n"
        "## PEER SESSION section\n- keep me\n"
    )
    before = curated.read_text()

    _run_writer(tmp_path, "sess-ME")

    assert curated.read_text() == before
    extract = claude_dir / "checkpoint-autogen.md"
    assert extract.is_file()
    assert "Written by PreCompact hook at" in extract.read_text()
    # The reader still points the resume at the stamped extract, but names the brief.
    sel = cr.select_for_read(str(claude_dir), "sess-ME")
    assert sel is not None
    assert sel["basename"] == "checkpoint-autogen.md"
    assert sel["unstamped_curated"] == "checkpoint.md"
    assert str(curated) in cr.resume_message(str(claude_dir), "sess-ME")


def test_writer_reclaims_a_stale_unstamped_hand_written_checkpoint(tmp_path):
    """Negative control: an unstamped file past the remnant age is a dead remnant, not a
    brief to protect; the writer reclaims it, and the reader no longer names it."""
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    stale = claude_dir / "checkpoint.md"
    stale.write_text(
        "# Resume Checkpoint — a dead session's brief\n\n## NEXT\n- old work\n"
    )
    _touch_mtime(str(stale), time.time() - (cr.DEFAULT_REMNANT_AGE_H + 1) * 3600)

    _run_writer(tmp_path, "sess-ME")

    assert not (claude_dir / "checkpoint-autogen.md").exists()
    text = stale.read_text()
    assert "Written by PreCompact hook at" in text
    assert "old work" not in text
    selected = cr.select_for_read(str(claude_dir), "sess-ME")
    assert selected is not None
    assert selected["unstamped_curated"] is None


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
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
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
    assert sel is not None
    assert sel["basename"] == "checkpoint-autogen.md"
    assert sel["is_current"] is True


@pytest.mark.skipif(
    shutil.which("jq") is None, reason="the hook parses its envelope with jq"
)
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
        if k
        not in ("CLAUDE_TOOL_INPUT", "CLAUDE_HOOK_SMOKE", "CODEX_HOOK_COMPAT_SMOKE")
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
    assert (
        "Read `%s` first (this session's fresh" % (claude_dir / "checkpoint.md")
        in context
    )
    assert "scope — settled" in context


# Current decisions are a root-reviewed checkpoint projection, never launch authority.
def _decision_fixture(tmp_path):
    checkpoint = tmp_path / "manual.md"
    transcript = tmp_path / "native.jsonl"
    session = "current-session"
    messages = []
    pins = {}
    for identity, text in (
        ("hold", "Hold for Opus at 20:00."),
        ("approval", "Use Astra xhigh; supersedes hold. Separate GO required."),
    ):
        record = {
            "type": "response_item",
            "timestamp": identity,
            "payload": {
                "type": "message",
                "id": identity,
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
                "internal_chat_message_metadata_passthrough": {
                    "turn_id": identity,
                    "content_item_kinds": ["user.text"],
                },
            },
            "metadata": {"retained_source": {"complete": False}},
        }
        raw = json.dumps(record).encode() + b"\n"
        messages.append(raw)
        pins[identity] = {
            "line": len(messages) + 1,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "message_id": identity,
            "timestamp": identity,
            "turn_id": identity,
            "retained_complete": False,
        }
    header = {"type": "session_meta", "payload": {"id": session, "cwd": str(tmp_path)}}
    transcript.write_bytes(json.dumps(header).encode() + b"\n" + b"".join(messages))
    view = {
        "version": 1,
        "session_id": session,
        "repo_root": str(tmp_path),
        "checkpoint_path": str(checkpoint),
        "native_journal": str(transcript),
        "seen_user_source": "approval",
        "sources": pins,
        "entries": [
            {
                "id": "opus-held",
                "scope": "reviews",
                "state": "held",
                "source": "hold",
                "quote": "Hold for Opus",
                "supersedes": None,
            },
            {
                "id": "astra-approved",
                "scope": "reviews",
                "state": "approved",
                "source": "approval",
                "quote": "Use Astra xhigh",
                "supersedes": "opus-held",
            },
            {
                "id": "production-reserved",
                "scope": "production",
                "state": "go-required",
                "source": "approval",
                "quote": "Separate GO required",
                "supersedes": None,
            },
        ],
    }
    return checkpoint, transcript, session, view


def _write_decision_block(checkpoint, view):
    payload = json.dumps(view, indent=2).encode() + b"\n"
    checkpoint.write_bytes(
        b"# Explicit manual checkpoint\n```current-decisions-json\n"
        + payload
        + b"```\n"
    )
    return hashlib.sha256(payload).hexdigest()


def test_current_decisions_supersedes_old_hold_and_keeps_no_go(tmp_path, monkeypatch):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    # Wall-clock expiry cannot supply a missing human authorization.
    monkeypatch.setattr(cr.time, "time", lambda: 10**12)
    result = cr.read_current_decisions(checkpoint, session, transcript, digest)
    assert result["active"]["reviews"]["id"] == "astra-approved"
    assert result["active"]["production"]["state"] == "go-required"
    assert result["launch_authority"] is False
    # A genuinely hold-only journal stays held after its stated clock time.
    transcript.write_bytes(b"\n".join(transcript.read_bytes().splitlines()[:2]) + b"\n")
    old_view = {
        **view,
        "entries": view["entries"][:1],
        "seen_user_source": "hold",
        "sources": {"hold": view["sources"]["hold"]},
    }
    digest = _write_decision_block(checkpoint, old_view)
    assert (
        cr.read_current_decisions(checkpoint, session, transcript, digest)["active"][
            "reviews"
        ]["state"]
        == "held"
    )


def test_current_decisions_new_user_input_refuses_but_tool_append_does_not(tmp_path):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    with transcript.open("ab") as writer:
        writer.write(
            json.dumps(
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "id": "tool-output",
                        "call_id": "tool-call",
                        "output": "offline check completed",
                        "internal_chat_message_metadata_passthrough": {
                            "turn_id": "approval"
                        },
                    },
                }
            ).encode()
            + b"\n"
        )
    assert cr.read_current_decisions(checkpoint, session, transcript, digest)[
        "is_current"
    ]
    latest = {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "user",
            "internal_chat_message_metadata_passthrough": {
                "content_item_kinds": ["user.text"]
            },
        },
    }
    with transcript.open("ab") as writer:
        writer.write(json.dumps(latest).encode() + b"\n")
    with pytest.raises(ValueError, match="STALE_DECISION_VIEW_NEW_USER_INPUT"):
        cr.read_current_decisions(checkpoint, session, transcript, digest)


@pytest.mark.parametrize("foreign", ["checkpoint", "view", "journal"])
def test_current_decisions_foreign_session_refuses(tmp_path, foreign):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    if foreign == "view":
        view["session_id"] = "peer"
    digest = _write_decision_block(checkpoint, view)
    if foreign == "checkpoint":
        checkpoint.write_bytes(b"<!-- session: peer -->\n" + checkpoint.read_bytes())
    if foreign == "journal":
        transcript.write_bytes(
            transcript.read_bytes().replace(b'"current-session"', b'"peer"', 1)
        )
    with pytest.raises(ValueError, match="FOREIGN_"):
        cr.read_current_decisions(checkpoint, session, transcript, digest)


@pytest.mark.parametrize("tamper", ["view", "source", "supersedes", "quote"])
def test_current_decisions_tamper_refuses(tmp_path, tamper):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    if tamper == "supersedes":
        view["entries"][1]["supersedes"] = "foreign-entry"
    if tamper == "quote":
        view["entries"][1]["quote"] = "operator GO"
    digest = _write_decision_block(checkpoint, view)
    if tamper == "view":
        checkpoint.write_bytes(
            checkpoint.read_bytes().replace(b'"approved"', b'"held"', 1)
        )
    if tamper == "source":
        transcript.write_bytes(
            transcript.read_bytes().replace(b"Use Astra", b"Use other", 1)
        )
    with pytest.raises(
        ValueError,
        match="DECISION_VIEW_DIGEST_CHANGED|DIRECT_USER_SOURCE_CHANGED|INVALID_OR_FOREIGN_SUPERSESSION",
    ):
        cr.read_current_decisions(checkpoint, session, transcript, digest)


def test_current_decisions_missing_production_go_refuses_cli_before_child(
    tmp_path, monkeypatch, capsys
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    children = []
    monkeypatch.setattr(
        cr.subprocess, "run", lambda *args, **kwargs: children.append(args)
    )
    result = cr._main(
        [
            "checkpoint_resume.py",
            "current-decisions",
            str(checkpoint),
            session,
            str(transcript),
            digest,
            "production",
            "operator-go",
        ]
    )
    captured = capsys.readouterr()
    assert result == 65
    assert "PRODUCTION_GO_REQUIRED" in captured.err
    assert captured.out == "" and children == []


def _append_native_record(transcript, record):
    with transcript.open("ab") as writer:
        writer.write(json.dumps(record).encode() + b"\n")


def _assert_decision_cli_refused(
    checkpoint, transcript, session, digest, capsys, reason
):
    return_code = cr._main(
        [
            "checkpoint_resume.py",
            "current-decisions",
            str(checkpoint),
            session,
            str(transcript),
            digest,
        ]
    )
    captured = capsys.readouterr()
    assert return_code == 65, captured
    assert captured.out == ""
    assert reason in captured.err


@pytest.mark.parametrize(
    "provenance",
    [
        "missing-metadata",
        "empty-metadata",
        "null-metadata",
        "missing-kinds",
        "empty-kinds",
        "unknown-kind",
        "string-kinds",
        "object-kinds",
        "nonstring-kind",
        "empty-kind",
        "bare-user-prefix",
        "mixed-user-unknown",
        "mixed-environment-unknown",
    ],
)
def test_current_decisions_unknown_user_provenance_refuses(
    tmp_path, capsys, provenance
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    payload = {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "Stop; withdraw the approval."}],
    }
    if provenance != "missing-metadata":
        kinds = {
            "empty-kinds": [],
            "unknown-kind": ["unknown.context"],
            "string-kinds": "user.text",
            "object-kinds": {"environments.environment_context": True},
            "nonstring-kind": [None],
            "empty-kind": [""],
            "bare-user-prefix": ["user."],
            "mixed-user-unknown": ["user.text", "unknown.context"],
            "mixed-environment-unknown": [
                "environments.environment_context",
                "unknown.context",
            ],
        }
        metadata = (
            {"content_item_kinds": kinds[provenance]} if provenance in kinds else {}
        )
        payload["internal_chat_message_metadata_passthrough"] = (
            None if provenance == "null-metadata" else metadata
        )
    _append_native_record(transcript, {"type": "response_item", "payload": payload})
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, "UNKNOWN_USER_PROVENANCE"
    )


@pytest.mark.parametrize(
    "role", ["missing", None, "usr", "assistant", "system", "tool"]
)
def test_current_decisions_user_provenance_requires_user_role(tmp_path, capsys, role):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    payload = {
        "type": "message",
        "content": [{"type": "input_text", "text": "Withdraw approval."}],
        "internal_chat_message_metadata_passthrough": {
            "content_item_kinds": ["user.text"]
        },
    }
    if role != "missing":
        payload["role"] = role
    _append_native_record(transcript, {"type": "response_item", "payload": payload})
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, "UNKNOWN_USER_RECORD"
    )


@pytest.mark.parametrize("role", ["assistant", "developer", "system", "tool"])
def test_current_decisions_ordinary_nonuser_messages_preserve_view(tmp_path, role):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    _append_native_record(
        transcript,
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": role,
                "content": [{"type": "output_text", "text": "Operational context."}],
                "internal_chat_message_metadata_passthrough": {
                    "content_item_kinds": ["unknown"]
                },
            },
        },
    )
    decision = cr.read_current_decisions(checkpoint, session, transcript, digest)
    assert decision["is_current"] is True
    assert decision["active"]["production"]["state"] == "go-required"


@pytest.mark.parametrize(
    "record_shape", ["missing-message-type", "wrong-message-type", "wrong-record-type"]
)
def test_current_decisions_unknown_user_record_shape_refuses(
    tmp_path, capsys, record_shape
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    payload = {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "Withdraw approval."}],
        "internal_chat_message_metadata_passthrough": {
            "content_item_kinds": ["user.text"]
        },
    }
    if record_shape == "missing-message-type":
        del payload["type"]
    elif record_shape == "wrong-message-type":
        payload["type"] = "function_call_output"
    record_type = (
        "event_msg" if record_shape == "wrong-record-type" else "response_item"
    )
    _append_native_record(transcript, {"type": record_type, "payload": payload})
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, "UNKNOWN_USER_RECORD"
    )


@pytest.mark.parametrize(
    "kinds",
    [
        ["agents_md.instructions", "environments.environment_context"],
        ["additional_content.codex_apps_open_page"],
        ["environments.environment_context"],
    ],
)
def test_current_decisions_native_environment_shapes_remain_current(tmp_path, kinds):
    # Provenance/container shapes inspected in actual native lines 6, 12 and 2942.
    # Synthetic payload text carries no new human instruction or authorization.
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    _append_native_record(
        transcript,
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "id": "environment-context",
                "content": [
                    {
                        "type": "input_text",
                        "text": "<environment_context>fixture</environment_context>",
                    }
                ],
                "internal_chat_message_metadata_passthrough": {
                    "turn_id": "approval",
                    "create_time": 1.0,
                    "content_item_kinds": kinds,
                },
            },
        },
    )
    result = cr.read_current_decisions(checkpoint, session, transcript, digest)
    assert result["is_current"] is True and result["launch_authority"] is False
    assert result["active"]["reviews"]["id"] == "astra-approved"


@pytest.mark.parametrize("kind", ["user.image", "user.audio", "user.text"])
def test_current_decisions_new_nontext_or_text_input_stales_view(
    tmp_path, capsys, kind
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    _append_native_record(
        transcript,
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_image", "image_url": "fixture"}],
                "internal_chat_message_metadata_passthrough": {
                    "content_item_kinds": [kind]
                },
            },
        },
    )
    _assert_decision_cli_refused(
        checkpoint,
        transcript,
        session,
        digest,
        capsys,
        "STALE_DECISION_VIEW_NEW_USER_INPUT",
    )


def test_current_decisions_latest_opening_must_be_complete(tmp_path, capsys):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    with checkpoint.open("ab") as writer:
        writer.write(b'\n```current-decisions-json\n{"version": 1,\n')
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, "INCOMPLETE_DECISION_VIEW"
    )


@pytest.mark.parametrize(
    "opening",
    [
        b"```current-decisions-json\r\n",
        b"```current-decisions-json extra\n",
        b"```current-decisions-json",
    ],
)
def test_current_decisions_malformed_latest_reserved_opening_refuses(
    tmp_path, capsys, opening
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    with checkpoint.open("ab") as writer:
        writer.write(b"\n" + opening)
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, "INCOMPLETE_DECISION_VIEW"
    )


def test_current_decisions_malformed_latest_complete_block_refuses(tmp_path, capsys):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    old_digest = _write_decision_block(checkpoint, view)
    malformed_payload = b'{"version": 1,\n'
    with checkpoint.open("ab") as writer:
        writer.write(b"\n```current-decisions-json\n" + malformed_payload + b"```\n")
    _assert_decision_cli_refused(
        checkpoint,
        transcript,
        session,
        old_digest,
        capsys,
        "DECISION_VIEW_DIGEST_CHANGED",
    )
    _assert_decision_cli_refused(
        checkpoint,
        transcript,
        session,
        hashlib.sha256(malformed_payload).hexdigest(),
        capsys,
        "CURRENT_DECISIONS_REFUSED",
    )


def test_current_decisions_valid_latest_block_requires_its_reviewed_digest(
    tmp_path, capsys
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    old_digest = _write_decision_block(checkpoint, view)
    view["entries"][1]["id"] = "astra-approved-reviewed"
    latest_payload = json.dumps(view, indent=2).encode() + b"\n"
    with checkpoint.open("ab") as writer:
        writer.write(b"\n```current-decisions-json\n" + latest_payload + b"```\n")
    _assert_decision_cli_refused(
        checkpoint,
        transcript,
        session,
        old_digest,
        capsys,
        "DECISION_VIEW_DIGEST_CHANGED",
    )
    result = cr.read_current_decisions(
        checkpoint, session, transcript, hashlib.sha256(latest_payload).hexdigest()
    )
    assert result["active"]["reviews"]["id"] == "astra-approved-reviewed"
    assert result["launch_authority"] is False


@pytest.mark.parametrize("appended_session", ["foreign-session", "current-session"])
def test_current_decisions_repeated_session_header_refuses(
    tmp_path, capsys, appended_session
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    _append_native_record(
        transcript,
        {
            "type": "session_meta",
            "payload": {"id": appended_session, "cwd": str(tmp_path)},
        },
    )
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, "MULTI_SESSION_NATIVE_JOURNAL"
    )


@pytest.mark.parametrize(
    "tamper",
    [
        "duplicate-source-line",
        "empty-sources",
        "missing-source-alias",
        "duplicate-entry-id",
        "chronological-reversal",
        "cross-scope-predecessor",
        "empty-quote",
        "checkpoint-path",
        "journal-path",
        "source-message-id",
        "source-turn-id",
        "source-time",
        "retention-flag",
    ],
)
def test_current_decisions_bound_contract_tampering_refuses(tmp_path, capsys, tamper):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    expected_reason = "INVALID_OR_FOREIGN_SUPERSESSION"
    if tamper == "duplicate-source-line":
        view["sources"]["approval"]["line"] = view["sources"]["hold"]["line"]
        expected_reason = "INVALID_SOURCE_PINS"
    elif tamper == "empty-sources":
        view["sources"] = {}
        expected_reason = "INVALID_SOURCE_PINS"
    elif tamper == "missing-source-alias":
        view["entries"][1]["source"] = "absent"
        expected_reason = "CURRENT_DECISIONS_REFUSED"
    elif tamper == "duplicate-entry-id":
        view["entries"][2]["id"] = view["entries"][1]["id"]
    elif tamper == "chronological-reversal":
        hold, approval = view["entries"][:2]
        approval["supersedes"] = None
        hold["supersedes"] = approval["id"]
        view["entries"][:2] = [approval, hold]
    elif tamper == "cross-scope-predecessor":
        view["entries"][2]["supersedes"] = view["entries"][1]["id"]
    elif tamper == "empty-quote":
        view["entries"][1]["quote"] = ""
    elif tamper in {"checkpoint-path", "journal-path"}:
        view["checkpoint_path" if tamper == "checkpoint-path" else "native_journal"] = (
            str(tmp_path / "foreign")
        )
        expected_reason = "FOREIGN_DECISION_VIEW"
    else:
        pin_field = {
            "source-message-id": "message_id",
            "source-turn-id": "turn_id",
            "source-time": "timestamp",
            "retention-flag": "retained_complete",
        }[tamper]
        view["sources"]["approval"][pin_field] = (
            True if tamper == "retention-flag" else "foreign"
        )
        expected_reason = "DIRECT_USER_SOURCE_CHANGED"
    digest = _write_decision_block(checkpoint, view)
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, expected_reason
    )


@pytest.mark.parametrize(
    "journal_failure",
    [
        "empty",
        "missing-pinned-source",
        "truncated-line",
        "wrong-cwd",
        "wrong-initial-record",
    ],
)
def test_current_decisions_incomplete_or_foreign_journal_refuses(
    tmp_path, capsys, journal_failure
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    expected_reason = "DIRECT_USER_SOURCE_MISSING"
    if journal_failure == "empty":
        transcript.write_bytes(b"")
    elif journal_failure == "missing-pinned-source":
        transcript.write_bytes(
            b"\n".join(transcript.read_bytes().splitlines()[:2]) + b"\n"
        )
    elif journal_failure == "truncated-line":
        with transcript.open("ab") as writer:
            writer.write(b'{"type": "response_')
        expected_reason = "CURRENT_DECISIONS_REFUSED"
    else:
        records = transcript.read_bytes().splitlines(keepends=True)
        header = json.loads(records[0])
        if journal_failure == "wrong-cwd":
            header["payload"]["cwd"] = str(tmp_path / "foreign")
        else:
            header["type"] = "event_msg"
        transcript.write_bytes(
            json.dumps(header).encode() + b"\n" + b"".join(records[1:])
        )
        expected_reason = "FOREIGN_NATIVE_SESSION"
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, expected_reason
    )


@pytest.mark.parametrize("missing", ["file", "empty", "fence"])
def test_current_decisions_missing_view_refuses(tmp_path, capsys, missing):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    expected_reason = "CURRENT_DECISIONS_REFUSED"
    if missing == "file":
        checkpoint.unlink()
    else:
        checkpoint.write_text("" if missing == "empty" else "# Manual checkpoint\n")
        expected_reason = "MISSING_DECISION_VIEW"
    _assert_decision_cli_refused(
        checkpoint, transcript, session, digest, capsys, expected_reason
    )


@pytest.mark.parametrize("precondition", [[], ["reviews", "approved"]])
def test_current_decisions_successful_cli_keeps_read_only_scope(
    tmp_path, capsys, precondition
):
    checkpoint, transcript, session, view = _decision_fixture(tmp_path)
    digest = _write_decision_block(checkpoint, view)
    return_code = cr._main(
        [
            "checkpoint_resume.py",
            "current-decisions",
            str(checkpoint),
            session,
            str(transcript),
            digest,
            *precondition,
        ]
    )
    captured = capsys.readouterr()
    assert return_code == 0 and captured.err == ""
    result = json.loads(captured.out)
    assert result["is_current"] is True and result["launch_authority"] is False
    assert result["active"]["reviews"]["state"] == "approved"
    assert result["active"]["production"]["state"] == "go-required"
