#!/usr/bin/env python3
"""Tests for checkpoint_resume — the single-source resume-checkpoint naming + selection.

Regression targets: genomics 2026-07-06 (a resume read a stale DIFFERENT-session file
as its own) and genomics 2026-10-22 (two sessions in one checkout overwrote each other's
checkpoint through one shared divert slot). These pin the per-session writer and the
reader contract both hooks rely on.

Run: cd ~/Projects/skills/hooks && python3 -m pytest test_checkpoint_resume.py -q
Positive control: CHECKPOINT_WRITER_UNDER_TEST=<pre-fix precompact-extract.py copy,
beside its own checkpoint_resume.py> must make the two-session test fail.
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
WRITER = Path(
    os.environ.get("CHECKPOINT_WRITER_UNDER_TEST") or HOOK_DIR / "precompact-extract.py"
)


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


# ─── naming ──────────────────────────────────────────────────────────

ME = "aaaaaaaa-1111-4111-8111-111111111111"
PEER = "bbbbbbbb-2222-4222-8222-222222222222"
TWIN = "aaaaaaaa-9999-4999-8999-999999999999"  # shares ME's 8-character prefix


def _auto(claude_dir, session):
    return claude_dir / cr.auto_checkpoint_name(session)


def test_names_are_per_session_and_refuse_unusable_ids():
    sid = "339ca089-21ae-455e-84d6-4981fd3479cf"
    assert cr.auto_checkpoint_name(sid) == "checkpoint-auto-339ca089.md"
    assert cr.handwritten_checkpoint_name(sid) == "checkpoint-339ca089.md"
    for bad in ("", None, "../escape", "has space", "-leading"):
        assert cr.auto_checkpoint_name(bad) is None
        assert cr.handwritten_checkpoint_name(bad) is None


# ─── select_for_read ─────────────────────────────────────────────────


def test_select_none_when_empty(tmp_path):
    assert cr.select_for_read(str(tmp_path), ME) is None


def test_select_prefers_own_extract_over_newer_peer_files(tmp_path):
    """Mine is OLDER than a peer's extract and the curated file, but I must still
    resume off MY checkpoint, not the newer peer file."""
    now = 1_000_000.0
    mine, peer = _auto(tmp_path, ME), _auto(tmp_path, PEER)
    curated = tmp_path / "checkpoint.md"
    _write(str(mine), ME)
    _write(str(peer), PEER)
    _write(str(curated), PEER)
    _touch_mtime(str(mine), now - 3600)
    _touch_mtime(str(peer), now - 60)
    _touch_mtime(str(curated), now - 30)
    sel = cr.select_for_read(str(tmp_path), ME, now=now)
    assert sel is not None
    assert sel["basename"] == mine.name
    assert sel["session"] == ME
    assert sel["is_current"] is True and sel["curated"] is False
    assert [s["basename"] for s in sel["siblings"]] == ["checkpoint.md"]
    assert sel["siblings"][0]["is_current"] is False
    assert sel["sibling_count"] == 1


def test_select_never_calls_a_prefix_twin_this_sessions(tmp_path):
    """Same file name, different full id: never 'this session's' checkpoint."""
    twin = _auto(tmp_path, TWIN)
    assert twin == _auto(tmp_path, ME)
    _write(str(twin), TWIN)
    sel = cr.select_for_read(str(tmp_path), ME)
    assert sel is not None
    assert sel["basename"] == twin.name and sel["is_current"] is False
    msg = cr.resume_message(str(tmp_path), ME)
    assert "No checkpoint stamped with this session exists" in msg
    assert TWIN in msg
    assert "this session's fresh" not in msg


def test_select_newest_when_no_session_match(tmp_path):
    now = 1_000_000.0
    curated = tmp_path / "checkpoint.md"
    peer = _auto(tmp_path, PEER)
    _write(str(curated), "sess-OLD")
    _write(str(peer), PEER)
    _touch_mtime(str(curated), now - 4000)
    _touch_mtime(str(peer), now - 8000)
    sel = cr.select_for_read(str(tmp_path), ME, now=now)
    assert sel is not None
    assert sel["basename"] == "checkpoint.md"  # newest of the two
    assert sel["is_current"] is False
    assert sel["age_hours"] > 1.0
    assert sel["siblings"] == []


def test_select_single_current_file(tmp_path):
    now = 1_000_000.0
    p = _auto(tmp_path, ME)
    _write(str(p), ME)
    _touch_mtime(str(p), now - 1800)
    sel = cr.select_for_read(str(tmp_path), ME, now=now)
    assert sel is not None
    assert sel["is_current"] is True
    assert sel["sibling_count"] == 0
    assert sel["age_hours"] == 0.5


def test_select_falls_back_to_a_hand_written_file_stamped_this_session(tmp_path):
    now = 1_000_000.0
    brief = tmp_path / cr.handwritten_checkpoint_name(ME)
    peer = _auto(tmp_path, PEER)
    _write(str(brief), ME, "## Pending Tasks\n- finish")
    _write(str(peer), PEER)
    _touch_mtime(str(brief), now - 3600)
    _touch_mtime(str(peer), now - 60)
    sel = cr.select_for_read(str(tmp_path), ME, now=now)
    assert sel is not None
    assert sel["basename"] == brief.name
    assert sel["is_current"] is True and sel["curated"] is True


def test_select_read_cli_keeps_the_parsed_keys(tmp_path, capsys):
    _write(str(_auto(tmp_path, ME)), ME)
    assert cr._main(["checkpoint_resume.py", "select-read", str(tmp_path), ME]) == 0
    sel = json.loads(capsys.readouterr().out)
    assert {
        "path",
        "basename",
        "session",
        "age_hours",
        "is_current",
        "curated",
        "siblings",
        "sibling_count",
    } <= set(sel)
    assert sel["is_current"] is True


# ─── resume_message ──────────────────────────────────────────────────


def test_resume_message_current_is_positive(tmp_path):
    now = 1_000_000.0
    p = _auto(tmp_path, ME)
    _write(str(p), ME)
    _touch_mtime(str(p), now - 600)
    msg = cr.resume_message(str(tmp_path), ME, now=now)
    assert "Read `%s` first (this session's fresh resume checkpoint" % p in msg
    # Subagents share the session id and their PreCompact reads the main transcript
    # (2026-10-22 01:02 JST), so the extract's pointer must tell a subagent it is the
    # parent's state.
    assert "resume from its own compaction summary" in msg


def test_resume_message_hand_written_omits_subagent_clause(tmp_path):
    now = 1_000_000.0
    brief = tmp_path / cr.handwritten_checkpoint_name(ME)
    _write(str(brief), ME)
    _touch_mtime(str(brief), now - 600)
    msg = cr.resume_message(str(tmp_path), ME, now=now)
    assert "Read `%s` first (this session's fresh resume checkpoint, hand-written)" % brief in msg
    assert "compaction summary" not in msg


def test_resume_message_cross_session_warns(tmp_path):
    """The exact bug: chosen file is a different session -> message must warn, not
    call it 'fresh'."""
    now = 1_000_000.0
    p = tmp_path / "checkpoint.md"
    _write(str(p), "1cf836e3")
    _touch_mtime(str(p), now - 48 * 3600)  # 2 days old, like the incident
    msg = cr.resume_message(str(tmp_path), "be0657a9", now=now)
    assert "No checkpoint stamped with this session exists" in msg
    assert "NOT this resuming session" in msg
    assert "may be stale" in msg
    assert "git log" in msg
    assert "fresh resume checkpoint" not in msg


def test_resume_message_empty_when_none(tmp_path):
    assert cr.resume_message(str(tmp_path), ME) == ""


def test_resume_message_current_but_old_adds_verify(tmp_path):
    now = 1_000_000.0
    p = _auto(tmp_path, ME)
    _write(str(p), ME)
    _touch_mtime(str(p), now - 20 * 3600)  # 20h — current session but old
    msg = cr.resume_message(str(tmp_path), ME, now=now)
    assert "verify" in msg.lower()
    assert "git log" in msg


def test_resume_message_names_hand_curated_siblings_with_provenance(tmp_path):
    """The extract is read first; the session's own brief and the shared curated file
    are both named, each with whose it is."""
    now = 1_000_000.0
    auto = _auto(tmp_path, ME)
    brief = tmp_path / cr.handwritten_checkpoint_name(ME)
    curated = tmp_path / "checkpoint.md"
    _write(str(auto), ME)
    _write(str(brief), ME, "## Pending Tasks\n- finish")
    _write(str(curated), PEER, "project handoff")
    for path in (auto, brief, curated):
        _touch_mtime(str(path), now - 600)
    sel = cr.select_for_read(str(tmp_path), ME, now=now)
    assert sel is not None
    assert sel["basename"] == auto.name
    roles = {s["basename"]: (s["role"], s["is_current"]) for s in sel["siblings"]}
    assert roles == {
        "checkpoint.md": ("curated", False),
        brief.name: ("session-brief", True),
    }
    msg = cr.resume_message(str(tmp_path), ME, now=now)
    assert "Read `%s` first (this session's fresh" % auto in msg
    assert "This session's hand-written `%s`" % brief in msg
    assert "The shared hand-curated `%s` (stamped session %s" % (curated, PEER) in msg


def test_resume_message_flags_briefs_it_cannot_attribute(tmp_path):
    _write(str(_auto(tmp_path, ME)), ME)
    brief = tmp_path / cr.handwritten_checkpoint_name(ME)
    _write(str(brief), TWIN)
    msg = cr.resume_message(str(tmp_path), ME)
    assert "shares this session's 8-character prefix but is stamped session %s" % TWIN in msg
    assert "This session's hand-written" not in msg
    brief.write_text("# brief without a stamp\n")
    msg = cr.resume_message(str(tmp_path), ME)
    assert "is named for this session but has no session stamp" in msg


# ─── the PreCompact writer ───────────────────────────────────────────


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
        [sys.executable, str(WRITER)],
        input=payload,
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc


def test_two_sessions_compacting_in_turn_keep_their_own_checkpoints(tmp_path):
    """Regression (genomics 2026-10-22): beside a hand-curated checkpoint.md, both
    sessions' extracts went to the one shared divert slot, so each compaction erased
    the other's checkpoint. Positive control: fails against the pre-fix writer."""
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    curated = claude_dir / "checkpoint.md"
    _write(str(curated), "cc1925f3-d4e2-4445-859c-97903394462a", "## project handoff")
    before = curated.read_text()

    for session in (ME, PEER, ME, PEER):
        _run_writer(tmp_path, session)

    stamps = {
        path.name: cr.read_session_stamp(str(path))
        for path in claude_dir.glob("checkpoint*.md")
    }
    assert {ME, PEER} <= set(stamps.values()), stamps
    assert curated.read_text() == before
    for session in (ME, PEER):
        own = claude_dir / cr.auto_checkpoint_name(session)
        assert cr.read_session_stamp(str(own)) == session
        sel = cr.select_for_read(str(claude_dir), session)
        assert sel is not None
        assert sel["path"] == str(own) and sel["is_current"] is True
        msg = cr.resume_message(str(claude_dir), session)
        assert "Read `%s` first (this session's fresh" % own in msg


def test_writer_leaves_hand_written_and_curated_checkpoints_untouched(tmp_path):
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    curated = claude_dir / "checkpoint.md"
    curated.write_text("# Hand-written brief, no stamp\n\n## NEXT\n- integrate the lanes\n")
    brief = claude_dir / cr.handwritten_checkpoint_name(ME)
    _write(str(brief), ME, "## Pending Tasks\n- finish the thing")
    topical = claude_dir / "checkpoint-markus-currency.md"
    topical.write_text("topical handoff\n")
    before = {path: path.read_text() for path in (curated, brief, topical)}

    _run_writer(tmp_path, ME)

    assert {path: path.read_text() for path in before} == before
    extract = claude_dir / cr.auto_checkpoint_name(ME)
    text = extract.read_text()
    assert "<!-- session: %s -->" % ME in text
    assert "Written by PreCompact hook at" in text
    assert "`.claude/%s`" % brief.name in text  # where hand-written notes belong
    assert sorted(p.name for p in claude_dir.iterdir()) == sorted(
        [curated.name, brief.name, topical.name, extract.name]
    )


def test_writer_rewrites_its_own_checkpoint_on_the_next_compaction(tmp_path):
    """Negative control: the session's own extract is the hook's to overwrite."""
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    own = claude_dir / cr.auto_checkpoint_name(ME)
    _write(str(own), ME, "old extract")

    _run_writer(tmp_path, ME)

    text = own.read_text()
    assert "Written by PreCompact hook at" in text
    assert "old extract" not in text


def test_writer_refuses_a_prefix_collision(tmp_path):
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    twin = claude_dir / cr.auto_checkpoint_name(TWIN)
    _write(str(twin), TWIN, "the twin's extract")
    before = twin.read_text()

    proc = _run_writer(tmp_path, ME)

    assert twin.read_text() == before
    assert "collision" in proc.stderr
    assert [p.name for p in claude_dir.iterdir()] == [twin.name]


@pytest.mark.parametrize("session", ["", "../escape", "has space"])
def test_writer_without_a_usable_session_id_writes_nothing(tmp_path, session):
    proj = tmp_path / "proj"
    proj.mkdir()

    proc = _run_writer(tmp_path, session)

    assert not (proj / ".claude").exists()
    assert "wrote no checkpoint" in proc.stderr
    log = tmp_path / "home" / ".claude" / "compact-log.jsonl"
    entry = json.loads(log.read_text().splitlines()[-1])
    assert entry["checkpoint"] is None
    assert entry["checkpoint_skipped"] == "missing or unusable session_id"


def test_expiry_removes_only_old_auto_checkpoints(tmp_path):
    claude_dir = tmp_path / "proj" / ".claude"
    claude_dir.mkdir(parents=True)
    old = time.time() - (cr.AUTO_EXPIRY_DAYS + 1) * 86400
    expired = claude_dir / cr.auto_checkpoint_name(PEER)
    _write(str(expired), PEER)
    fresh = claude_dir / "checkpoint-auto-cccccccc.md"
    _write(str(fresh), "cccccccc-3333-4333-8333-333333333333")
    hand_written = [
        claude_dir / "checkpoint.md",
        claude_dir / "checkpoint-dddddddd.md",
        claude_dir / "checkpoint-markus-currency.md",
        claude_dir / "checkpoint-auto-notes.txt",
    ]
    for path in hand_written:
        path.write_text("hand-written\n")
    target = tmp_path / "outside.md"
    target.write_text("linked\n")
    link = claude_dir / "checkpoint-auto-linked.md"
    link.symlink_to(target)
    for path in [expired, *hand_written, target]:
        _touch_mtime(str(path), old)
    _touch_mtime(str(fresh), time.time() - (cr.AUTO_EXPIRY_DAYS - 1) * 86400)

    _run_writer(tmp_path, ME)

    assert sorted(p.name for p in claude_dir.iterdir()) == sorted(
        [fresh.name, link.name, cr.auto_checkpoint_name(ME)]
        + [path.name for path in hand_written]
    )
    assert target.read_text() == "linked\n"


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

    _run_writer(tmp_path, ME, cwd=wt)

    assert "- **Branch:** `wtb`" in _auto(wt / ".claude", ME).read_text()


def test_writer_files_a_subdir_checkpoint_at_the_toplevel(tmp_path):
    proj, sub = _repo_with_subdir(tmp_path)

    _run_writer(tmp_path, ME, cwd=sub)

    assert not (sub / ".claude").exists()
    text = _auto(proj / ".claude", ME).read_text()
    assert "<!-- session: %s -->" % ME in text
    assert "- **Branch:** `main`" in text


def test_writer_leaves_a_tracked_toplevel_checkpoint_alone_from_a_subdir(tmp_path):
    """The incident shape: tracked root checkpoint.md, compaction fired in analysis/."""
    curated = "# Handoff\n<!-- session: old-sess -->\nhand-written\n"
    proj, sub = _repo_with_subdir(tmp_path, tracked_checkpoint=curated)

    _run_writer(tmp_path, ME, cwd=sub)

    assert not (sub / ".claude").exists()
    assert (proj / ".claude" / "checkpoint.md").read_text() == curated
    extract = _auto(proj / ".claude", ME)
    assert "Written by PreCompact hook at" in extract.read_text()
    sel = cr.select_for_read(str(proj / ".claude"), ME)
    assert sel is not None
    assert sel["basename"] == extract.name
    assert sel["is_current"] is True
    assert [s["basename"] for s in sel["siblings"]] == ["checkpoint.md"]


@pytest.mark.skipif(
    shutil.which("jq") is None, reason="the hook parses its envelope with jq"
)
def test_sessionstart_reader_resolves_the_toplevel_from_a_subdir(tmp_path):
    proj, sub = _repo_with_subdir(tmp_path)
    sid = "ckpt-root-test-%d" % os.getpid()
    claude_dir = proj / ".claude"
    claude_dir.mkdir()
    _write(str(_auto(claude_dir, sid)), sid)
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
    assert "Read `%s` first (this session's fresh" % _auto(claude_dir, sid) in context
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
