#!/usr/bin/env python3
"""Single-source resume-checkpoint naming, selection and expiry.

Two hooks must AGREE on which file is "the current session's resume checkpoint":
  - the PreCompact WRITER  (precompact-extract.py) — decides where to WRITE
  - the SessionStart(compact) READER (sessionstart-compact-resume.sh) — decides
    which file to tell the resuming agent to READ.

Both resolve the directory through project_root(): hook JSON `cwd` is the shell's
CURRENT directory, which drifts into subdirectories. A PreCompact from analysis/
(iq-sex-differences 2026-09-23) wrote analysis/.claude/checkpoint.md with an empty
Branch and left the root checkpoint stale, so the resume read a 3-week-old file.

Files in <project root>/.claude/:
  - checkpoint-auto-<sid8>.md — the ONLY file the hook writes: one per session,
                                stamped `<!-- session: <full id> -->`, expired
                                after AUTO_EXPIRY_DAYS.
  - checkpoint-<sid8>.md      — a session's hand-written brief (agent convention).
  - checkpoint.md and every other checkpoint*.md — hand-curated; the hook never
                                writes or expires them.

Per-session invariant (genomics 2026-10-22): the old writer diverted to ONE shared
slot, checkpoint-autogen.md, so two sessions compacting in one checkout overwrote
each other's checkpoint in turn (339ca089 at ~23:15, 1cce6699 at 00:21).
"""

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from typing import NoReturn

AUTO_PREFIX = "checkpoint-auto-"
CURATED_NAME = "checkpoint.md"
# The transcript horizon: an extract older than this outlives the session it resumes.
AUTO_EXPIRY_DAYS = 14
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_SESSION_RE = re.compile(rb"<!-- session: (\S+) -->")


def git_toplevel(cwd, timeout=5):
    """The git work-tree root containing `cwd`, or None outside a work tree.

    rev-parse, not an isdir(".git") probe: a linked worktree or submodule has a
    `.git` FILE, and a subdirectory has no `.git` at all.
    """
    if not cwd:
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = proc.stdout.strip()
    return top if proc.returncode == 0 and top else None


def project_root(cwd):
    """The directory whose .claude/ holds the checkpoints: git toplevel, else `cwd`."""
    return git_toplevel(cwd) or cwd


def session_prefix(session):
    """The 8-character file-name prefix of a session id, or None for an unusable id."""
    if not session or not _SESSION_ID_RE.fullmatch(session):
        return None
    return session[:8]


def auto_checkpoint_name(session):
    """`checkpoint-auto-<sid8>.md`: the one file the PreCompact hook writes for `session`."""
    prefix = session_prefix(session)
    return AUTO_PREFIX + prefix + ".md" if prefix else None


def handwritten_checkpoint_name(session):
    """`checkpoint-<sid8>.md`: the agent convention for a session's hand-written brief."""
    prefix = session_prefix(session)
    return "checkpoint-" + prefix + ".md" if prefix else None


def prompt_names(session):
    """(extract, brief) basenames for hook prompt text; `<sid8>` placeholders when the
    session id is unusable."""
    return (
        auto_checkpoint_name(session) or AUTO_PREFIX + "<sid8>.md",
        handwritten_checkpoint_name(session) or "checkpoint-<sid8>.md",
    )


def read_session_stamp(path):
    """Return the `<!-- session: X -->` id in a checkpoint's header, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
    except OSError:
        return None
    match = _SESSION_RE.search(head)
    return match.group(1).decode("utf-8", "replace") if match else None


def _entry(claude_dir, name, role):
    path = os.path.join(claude_dir, name)
    try:
        info = os.stat(path)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    return {
        "path": path,
        "basename": name,
        "session": read_session_stamp(path),
        "mtime": info.st_mtime,
        "role": role,
    }


def _auto_entries(claude_dir):
    try:
        names = sorted(os.listdir(claude_dir))
    except OSError:
        return []
    found = []
    for name in names:
        if name.startswith(AUTO_PREFIX) and name.endswith(".md"):
            entry = _entry(claude_dir, name, "auto")
            if entry:
                found.append(entry)
    return found


def select_for_read(claude_dir, current_session, now=None):
    """The checkpoint a resuming session should read, or None if none exist.

    Preference order:
      1. this session's checkpoint-auto-<sid8>.md, whose stamp must equal the FULL
         session id (a shared 8-character prefix never makes a file this session's),
      2. a hand-curated file stamped with this session (checkpoint.md or
         checkpoint-<sid8>.md), newest first,
      3. the newest checkpoint of any session, with is_current false.
    `siblings` names the hand-curated files beside the choice (the shared
    checkpoint.md and this session's checkpoint-<sid8>.md) with their provenance, so
    the reader never passes them by and never calls another session's file this
    session's (genomics 2026-07-06: a resume re-oriented off a dead session's file).
    """
    now = time.time() if now is None else now
    auto_name = auto_checkpoint_name(current_session)
    brief_name = handwritten_checkpoint_name(current_session)
    curated = [
        entry
        for entry in (
            _entry(claude_dir, brief_name, "session-brief") if brief_name else None,
            _entry(claude_dir, CURATED_NAME, "curated"),
        )
        if entry
    ]
    autos = _auto_entries(claude_dir)

    def is_own(entry):
        return bool(current_session) and entry["session"] == current_session

    def age_hours(entry):
        return round(max(0.0, (now - entry["mtime"]) / 3600.0), 1)

    chosen = next(
        (e for e in autos if e["basename"] == auto_name and is_own(e)), None
    )
    if chosen is None:
        own_curated = [e for e in curated if is_own(e)]
        if own_curated:
            chosen = max(own_curated, key=lambda e: e["mtime"])
    if chosen is None:
        pool = autos + curated
        if not pool:
            return None
        chosen = max(pool, key=lambda e: e["mtime"])
    siblings = [
        {
            "path": e["path"],
            "basename": e["basename"],
            "session": e["session"],
            "role": e["role"],
            "age_hours": age_hours(e),
            "is_current": is_own(e),
        }
        for e in curated
        if e is not chosen
    ]
    return {
        "path": chosen["path"],
        "basename": chosen["basename"],
        "session": chosen["session"],
        "mtime": chosen["mtime"],
        "age_hours": age_hours(chosen),
        "is_current": is_own(chosen),
        "curated": chosen["role"] != "auto",
        "role": chosen["role"],
        "siblings": siblings,
        "sibling_count": len(siblings),
    }


def _provenance(entry, current_session):
    # The full id: a prefix twin's first 8 characters are this session's own.
    if not entry["session"]:
        return "no session stamp"
    if current_session and entry["session"] == current_session:
        return "stamped this session"
    return "stamped session " + entry["session"]


def resume_message(claude_dir, current_session, now=None):
    """The human-facing 'read X first' fragment for the SessionStart hook.

    Empty string when no checkpoint exists. Honest about provenance: never
    claims a cross-session or stale file is "fresh". Names absolute paths: a
    relative `.claude/X` resolves against whatever subdirectory the agent's
    shell sits in, not the project root the file lives at.
    """
    sel = select_for_read(claude_dir, current_session, now=now)
    if not sel:
        return ""
    path = os.path.abspath(sel["path"])
    age = sel["age_hours"]
    if sel["is_current"]:
        kind = (
            "the PreCompact extract of the session's main conversation"
            if sel["role"] == "auto"
            else "hand-written"
        )
        msg = " Read `%s` first (this session's fresh resume checkpoint, %s)." % (
            path,
            kind,
        )
        if sel["role"] == "auto":
            # Subagents share the parent's session id, and Claude Code (2.1.306) hands
            # every PreCompact hook the main transcript with no agent_id, so a subagent's
            # compaction re-extracts the parent's conversation into this file. Observed
            # 2026-10-22 01:02 JST: a subagent's resume was pointed at its parent's tasks.
            msg += (
                " A subagent shares its parent's session id and its PreCompact hook reads"
                " the main transcript, so a resuming subagent must treat this file as its"
                " parent's work and resume from its own compaction summary."
            )
        if age > 18:
            msg += (
                " It is %.1fh old — verify its 'done' claims against `git log --oneline -15`"
                " before trusting them." % age
            )
    else:
        msg = (
            " No checkpoint stamped with this session exists. The newest is `%s` (%s,"
            " %.1fh old), NOT this resuming session — another session's work that may be"
            " stale: do not adopt its Pending Tasks, and verify every 'done' claim against"
            " `git log --oneline -15` before acting on it."
            % (path, _provenance(sel, current_session), age)
        )
    for sib in sel["siblings"]:
        sib_path = os.path.abspath(sib["path"])
        if sib["is_current"]:
            msg += (
                " This session's hand-written `%s` (%.1fh old) sits beside it: read it"
                " too; it carries what the transcript extract cannot."
                % (sib_path, sib["age_hours"])
            )
        elif sib["role"] == "session-brief" and sib["session"]:
            msg += (
                " `%s` shares this session's 8-character prefix but is %s: it is NOT"
                " this session's brief." % (sib_path, _provenance(sib, current_session))
            )
        elif sib["role"] == "session-brief":
            msg += (
                " `%s` is named for this session but has no session stamp; if it is this"
                " session's brief, read it too and add a `<!-- session: <id> -->` line to"
                " its header." % sib_path
            )
        else:
            msg += (
                " The shared hand-curated `%s` (%s, %.1fh old) is project-level, not this"
                " session's checkpoint: verify it before acting on it."
                % (sib_path, _provenance(sib, current_session), sib["age_hours"])
            )
    return msg


def expire_auto_checkpoints(claude_dir, now=None, max_age_days=AUTO_EXPIRY_DAYS):
    """Delete hook-written checkpoint-auto-*.md files older than `max_age_days`.

    Touches nothing else: hand-curated checkpoint*.md files, symlinks and directories
    are never removed. Returns the removed basenames.
    """
    now = time.time() if now is None else now
    removed = []
    for entry in _auto_entries(claude_dir):
        if now - entry["mtime"] < max_age_days * 86400 or os.path.islink(entry["path"]):
            continue
        try:
            os.unlink(entry["path"])
        except OSError:
            continue
        removed.append(entry["basename"])
    return removed


_NATIVE_INJECTED_USER_KINDS = frozenset(
    {
        "agents_md.instructions",
        "environments.environment_context",
        "additional_content.codex_apps_open_page",
    }
)


def read_current_decisions(
    checkpoint,
    current_session,
    transcript,
    expected_sha256,
    required_scope=None,
    required_state=None,
):
    """Read a ROOT-reviewed projection in an explicitly selected checkpoint.

    This never auto-selects a manual file or grants launch authority. The caller
    supplies the reviewed JSON-block hash and native Codex journal. Raw user
    messages remain authoritative; semantic interpretation needs human/root
    review. Tool-only journal appends do not stale the view; a new human input does.
    Currency is relative to the inspected journal, not proof that its full human
    history was retained: removing a complete suffix after the pinned sources
    cannot be detected without an external high-water mark. The checkpoint keeps
    the full reviewed source pins and supersession history; this result names its
    head and active entries, and is not a self-contained audit record.
    """

    def refuse(reason) -> NoReturn:
        raise ValueError("CURRENT_DECISIONS_REFUSED: " + reason)

    stamp = read_session_stamp(checkpoint)
    if stamp and stamp != current_session:
        refuse("FOREIGN_CHECKPOINT_SESSION")
    with open(checkpoint, "rb") as reader:
        checkpoint_bytes = reader.read()
    openings = list(
        re.finditer(rb"(?m)^```current-decisions-json[^\n]*(?:\n|$)", checkpoint_bytes)
    )
    if not openings:
        refuse("MISSING_DECISION_VIEW")
    if openings[-1].group() != b"```current-decisions-json\n":
        refuse("INCOMPLETE_DECISION_VIEW")
    latest_start = openings[-1].end()
    closing = re.search(rb"(?m)^```(?:\n|$)", checkpoint_bytes[latest_start:])
    if closing is None:
        refuse("INCOMPLETE_DECISION_VIEW")
    payload = checkpoint_bytes[latest_start : latest_start + closing.start()]
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        refuse("DECISION_VIEW_DIGEST_CHANGED")
    view = json.loads(payload)
    if (
        view["version"] != 1
        or view["session_id"] != current_session
        or view["checkpoint_path"] != os.path.abspath(checkpoint)
        or view["native_journal"] != os.path.abspath(transcript)
    ):
        refuse("FOREIGN_DECISION_VIEW")
    sources = view["sources"]
    by_line = {source["line"]: name for name, source in sources.items()}
    if len(by_line) != len(sources) or not sources:
        refuse("INVALID_SOURCE_PINS")
    found, latest_user = {}, None
    with open(transcript, "rb") as reader:
        for line_number, raw in enumerate(reader, 1):
            record = json.loads(raw)
            native = record.get("payload", {})
            if line_number == 1 and (
                record.get("type") != "session_meta"
                or native.get("id") != current_session
                or native.get("cwd") != view["repo_root"]
            ):
                refuse("FOREIGN_NATIVE_SESSION")
            if line_number != 1 and record.get("type") == "session_meta":
                refuse("MULTI_SESSION_NATIVE_JOURNAL")
            meta = native.get("internal_chat_message_metadata_passthrough")
            kinds = meta.get("content_item_kinds") if isinstance(meta, dict) else None
            if (
                isinstance(meta, dict)
                and "content_item_kinds" in meta
                and (
                    not isinstance(kinds, list)
                    or not kinds
                    or any(not isinstance(kind, str) or not kind for kind in kinds)
                )
            ):
                refuse("UNKNOWN_USER_PROVENANCE")
            if (
                record.get("type") == "response_item"
                and native.get("type") == "message"
                and native.get("role")
                not in {"user", "assistant", "developer", "system", "tool"}
            ) or (
                native.get("role") != "user"
                and isinstance(kinds, list)
                and any(
                    isinstance(kind, str) and kind.startswith("user.") for kind in kinds
                )
            ):
                refuse("UNKNOWN_USER_RECORD")
            is_direct = False
            if native.get("role") == "user":
                if (
                    record.get("type") != "response_item"
                    or native.get("type") != "message"
                ):
                    refuse("UNKNOWN_USER_RECORD")
                if not isinstance(meta, dict):
                    refuse("UNKNOWN_USER_PROVENANCE")
                kinds = meta.get("content_item_kinds")
                if (
                    not isinstance(kinds, list)
                    or not kinds
                    or any(not isinstance(kind, str) or not kind for kind in kinds)
                ):
                    refuse("UNKNOWN_USER_PROVENANCE")
                if any(
                    not (kind.startswith("user.") and len(kind) > len("user."))
                    and kind not in _NATIVE_INJECTED_USER_KINDS
                    for kind in kinds
                ):
                    refuse("UNKNOWN_USER_PROVENANCE")
                is_direct = any(kind.startswith("user.") for kind in kinds)
            if is_direct:
                latest_user = line_number
            is_user = is_direct and isinstance(kinds, list) and "user.text" in kinds
            if line_number not in by_line:
                continue
            name = by_line[line_number]
            pin = sources[name]
            retained = record.get("metadata", {}).get("retained_source", {})
            if (
                not is_user
                or hashlib.sha256(raw).hexdigest() != pin["sha256"]
                or native.get("id") != pin["message_id"]
                or meta.get("turn_id") != pin["turn_id"]
                or record.get("timestamp") != pin["timestamp"]
                or retained.get("complete") is not pin["retained_complete"]
            ):
                refuse("DIRECT_USER_SOURCE_CHANGED")
            found[name] = "\n".join(
                block["text"]
                for block in native["content"]
                if block.get("type") == "input_text"
            )
    if len(found) != len(sources):
        refuse("DIRECT_USER_SOURCE_MISSING")
    if latest_user != sources[view["seen_user_source"]]["line"]:
        refuse("STALE_DECISION_VIEW_NEW_USER_INPUT")
    active, seen_ids = {}, set()
    for entry in view["entries"]:
        scope, identity = entry["scope"], entry["id"]
        predecessor = active.get(scope)
        if (
            not identity
            or identity in seen_ids
            or not entry["quote"]
            or entry["quote"] not in found[entry["source"]]
            or entry["state"] not in {"held", "approved", "go-required", "operator-go"}
            or entry["supersedes"] != (predecessor["id"] if predecessor else None)
            or (
                predecessor
                and sources[entry["source"]]["line"]
                < sources[predecessor["source"]]["line"]
            )
        ):
            refuse("INVALID_OR_FOREIGN_SUPERSESSION")
        seen_ids.add(identity)
        active[scope] = entry
    if required_scope and (
        required_scope not in active
        or active[required_scope]["state"] != required_state
    ):
        refuse(
            "PRODUCTION_GO_REQUIRED"
            if required_scope == "production"
            else "REQUIRED_CURRENT_DECISION_MISSING"
        )
    return {
        "is_current": True,
        "launch_authority": False,
        "session_id": current_session,
        "source_head": sources[view["seen_user_source"]],
        "active": active,
    }


def _main(argv):
    if len(argv) in (6, 8) and argv[1] == "current-decisions":
        try:
            decision = read_current_decisions(*argv[2:])
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            AttributeError,
        ) as error:
            sys.stderr.write("CURRENT_DECISIONS_REFUSED: " + str(error) + "\n")
            return 65
        sys.stdout.write(json.dumps(decision))
        return 0
    if len(argv) >= 3 and argv[1] == "project-root":
        sys.stdout.write(project_root(argv[2]))
        return 0
    if len(argv) >= 3 and argv[1] == "resume-message":
        claude_dir = argv[2]
        sid = argv[3] if len(argv) > 3 else ""
        sys.stdout.write(resume_message(claude_dir, sid))
        return 0
    if len(argv) >= 3 and argv[1] == "select-read":
        claude_dir = argv[2]
        sid = argv[3] if len(argv) > 3 else ""
        sel = select_for_read(claude_dir, sid)
        sys.stdout.write(json.dumps(sel) if sel else "")
        return 0
    sys.stderr.write(
        "usage: checkpoint_resume.py {resume-message|select-read} <claude_dir> <session_id>\n"
        "       checkpoint_resume.py project-root <cwd>\n"
        "       checkpoint_resume.py current-decisions <checkpoint> <session_id> "
        "<native_journal> <reviewed_view_sha256> [<scope> <state>]\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
