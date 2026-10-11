#!/usr/bin/env python3
"""Single-source resume-checkpoint file selection + stale-remnant detection.

Two hooks must AGREE on which file is "the current session's resume checkpoint":
  - the PreCompact WRITER  (precompact-extract.py) — decides where to WRITE
  - the SessionStart(compact) READER (sessionstart-compact-resume.sh) — decides
    which file to tell the resuming agent to READ.

Both resolve the directory through project_root(): hook JSON `cwd` is the shell's
CURRENT directory, which drifts into subdirectories. A PreCompact from analysis/
(iq-sex-differences 2026-09-23) wrote analysis/.claude/checkpoint.md with an empty
Branch and left the root checkpoint stale, so the resume read a 3-week-old file.

The autogen resume pair is exactly two files in <project root>/.claude/:
  - checkpoint.md          — default write target AND historical read target
  - checkpoint-autogen.md  — divert target when checkpoint.md must not be
                             clobbered (git-tracked/curated, or a LIVE peer
                             session's file). Anti-clobber history:
                             hutter 2026-06-11 (curated overwrite),
                             2026-06-17 (peer clobber).

THE BUG this closes (genomics 2026-07-06): the writer diverted a fresh checkpoint
to checkpoint-autogen.md (existing checkpoint.md was a different, stale session),
but the reader hardcoded "a fresh checkpoint.md was written — read it first". The
resuming agent re-oriented off a 2-day-old DEAD session's checkpoint. Root cause =
a reader/writer contract split: the reader never checked the session stamp or the
sibling file.

select_for_read() fixes the reader: pick the CURRENT session's checkpoint (else
the newest), with honest provenance so the reader can warn on a cross-session or
old file. is_stale_remnant() lets the writer RECLAIM a dead different-session
checkpoint.md (a genuinely live peer re-writes far more often than the age floor),
so the divert only protects a live peer, not a corpse — keeping non-hook readers
(the CLAUDE.md "read .claude/checkpoint.md" convention) on fresh content too.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from typing import NoReturn

# The autogen resume pair — NOT the many manual topical checkpoints
# (checkpoint-markus-currency.md, checkpoint-clinical-waves.md, ...), which are
# human-authored and must never be auto-selected or reclaimed.
PAIR = ("checkpoint.md", "checkpoint-autogen.md")
_SESSION_RE = re.compile(rb"<!-- session: (\S+) -->")
# The writer signs every file it writes; the signature is the ownership marker.
_HOOK_SIGNATURE_RE = re.compile(
    rb"Written by PreCompact hook at (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\."
)
# The stamp has minute resolution, so the hook's own write lands < 60 s after it; an
# mtime further past the stamp than this is a hand edit after the hook wrote the file.
CURATED_EDIT_GRACE_S = 180.0

# A live concurrent peer re-writes its checkpoint on every compaction; only a
# dead session leaves one older than this. Reclaim past the floor, protect within.
DEFAULT_REMNANT_AGE_H = 12.0


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
    """The directory whose .claude/ holds the resume pair: git toplevel, else `cwd`."""
    return git_toplevel(cwd) or cwd


def read_session_stamp(path):
    """Return the `<!-- session: X -->` id in a checkpoint's header, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
    except OSError:
        return None
    match = _SESSION_RE.search(head)
    return match.group(1).decode("utf-8", "replace") if match else None


def is_curated(path):
    """True iff `path` is a hand-curated resume checkpoint the writer must not clobber.

    A checkpoint without the writer's signature line was written by hand; one whose
    mtime sits more than CURATED_EDIT_GRACE_S past the stamped write time was edited by
    hand after the hook wrote it (an agent updating Pending Tasks in place). Either way
    the transcript extract cannot reconstruct it: genomics 2026-09-07 02:31 lost a
    hand-written Pending Tasks list to the extract, whose "Working Summary" was an
    older block. Missing or unreadable files are not curated.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
        mtime = os.path.getmtime(path)
    except OSError:
        return False
    match = _HOOK_SIGNATURE_RE.search(head)
    if not match:
        return True
    try:
        stamped = time.mktime(
            time.strptime(match.group(1).decode("ascii"), "%Y-%m-%d %H:%M")
        )
    except (ValueError, OverflowError):
        return True
    return (mtime - stamped) > CURATED_EDIT_GRACE_S


def _candidates(claude_dir):
    found = []
    for name in PAIR:
        path = os.path.join(claude_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        found.append(
            {
                "path": path,
                "basename": name,
                "session": read_session_stamp(path),
                "mtime": mtime,
                "curated": is_curated(path),
            }
        )
    return found


def select_for_read(claude_dir, current_session, now=None):
    """The checkpoint a resuming session should read, or None if none exist.

    Preference order:
      1. a file stamped with `current_session` (this session's own fresh write),
         a hand-curated one first — the writer diverts its transcript extract
         beside a curated file precisely so the curated Pending Tasks survive,
      2. the newest file by mtime.
    Returned dict carries provenance so the reader can warn when the chosen file
    is NOT the resuming session's (a handoff/possibly-stale doc).
    """
    now = time.time() if now is None else now
    cands = _candidates(claude_dir)
    if not cands:
        return None
    own = [c for c in cands if current_session and c["session"] == current_session]
    pool = own if own else cands
    curated = [c for c in pool if c["curated"]] if own else []
    chosen = max(curated or pool, key=lambda c: c["mtime"])
    extract_siblings = (
        [c for c in own if c is not chosen and not c["curated"]]
        if chosen["curated"]
        else []
    )
    # The writer diverts beside a fresh hand-written file with no session stamp, but
    # that file never joins `own`; name it so the resume does not silently pass it by.
    unstamped_curated = [
        c
        for c in cands
        if c is not chosen
        and c["curated"]
        and not c["session"]
        and (now - c["mtime"]) / 3600.0 < DEFAULT_REMNANT_AGE_H
    ]
    age_hours = max(0.0, (now - chosen["mtime"]) / 3600.0)
    is_current = bool(current_session and chosen["session"] == current_session)
    return {
        "path": chosen["path"],
        "basename": chosen["basename"],
        "session": chosen["session"],
        "mtime": chosen["mtime"],
        "age_hours": round(age_hours, 1),
        "is_current": is_current,
        "curated": bool(chosen["curated"]),
        "extract_sibling": extract_siblings[0]["basename"]
        if extract_siblings
        else None,
        "sibling_count": len(cands) - 1,
        "unstamped_curated": unstamped_curated[0]["basename"]
        if unstamped_curated
        else None,
    }


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
        msg = " Read `%s` first (this session's fresh resume checkpoint)." % path
        if sel["curated"] and sel["extract_sibling"]:
            msg += (
                " It is hand-curated; the hook's transcript extract sits beside it in"
                " `%s`." % os.path.join(os.path.dirname(path), sel["extract_sibling"])
            )
        if age > 18:
            msg += (
                " It is %.1fh old — verify its 'done' claims against `git log --oneline -15`"
                " before trusting them." % age
            )
    else:
        sess = (sel["session"] or "unknown")[:8]
        msg = (
            " Read `%s` first, but treat it with care: it is stamped session %s"
            " (%.1fh old), NOT this resuming session — a handoff from another/earlier session"
            " that may be stale. Verify every 'done' claim against `git log --oneline -15`"
            " before acting on it." % (path, sess, age)
        )
    if sel["unstamped_curated"]:
        msg += (
            " A hand-written `%s` with no session stamp sits beside it; if it is this"
            " session's brief, read it too and add a `<!-- session: <id> -->` line to"
            " its header."
            % os.path.join(os.path.dirname(path), sel["unstamped_curated"])
        )
    return msg


def is_stale_remnant(path, current_session, now=None, max_age_h=DEFAULT_REMNANT_AGE_H):
    """True iff `path` is a DIFFERENT-session checkpoint old enough to be a dead
    remnant the writer may safely reclaim (overwrite).

    False for: a missing file, the current session's own file, or a fresh
    (< max_age_h) different-session file (a plausibly-live peer — do not clobber).
    """
    now = time.time() if now is None else now
    if not os.path.isfile(path):
        return False
    stamp = read_session_stamp(path)
    if stamp and current_session and stamp == current_session:
        return False  # our own checkpoint — normal overwrite, not a "reclaim"
    try:
        age_hours = (now - os.path.getmtime(path)) / 3600.0
    except OSError:
        return False
    return age_hours >= max_age_h


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
