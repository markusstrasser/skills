#!/usr/bin/env python3
"""Single-source resume-checkpoint file selection + stale-remnant detection.

Two hooks must AGREE on which file is "the current session's resume checkpoint":
  - the PreCompact WRITER  (precompact-extract.py) — decides where to WRITE
  - the SessionStart(compact) READER (sessionstart-compact-resume.sh) — decides
    which file to tell the resuming agent to READ.

The autogen resume pair is exactly two files in <cwd>/.claude/:
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

import json
import os
import re
import sys
import time

# The autogen resume pair — NOT the many manual topical checkpoints
# (checkpoint-markus-currency.md, checkpoint-clinical-waves.md, ...), which are
# human-authored and must never be auto-selected or reclaimed.
PAIR = ("checkpoint.md", "checkpoint-autogen.md")
_SESSION_RE = re.compile(rb"<!-- session: (\S+) -->")

# A live concurrent peer re-writes its checkpoint on every compaction; only a
# dead session leaves one older than this. Reclaim past the floor, protect within.
DEFAULT_REMNANT_AGE_H = 12.0


def read_session_stamp(path):
    """Return the `<!-- session: X -->` id in a checkpoint's header, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
    except OSError:
        return None
    match = _SESSION_RE.search(head)
    return match.group(1).decode("utf-8", "replace") if match else None


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
            }
        )
    return found


def select_for_read(claude_dir, current_session, now=None):
    """The checkpoint a resuming session should read, or None if none exist.

    Preference order:
      1. a file stamped with `current_session` (this session's own fresh write),
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
    chosen = max(pool, key=lambda c: c["mtime"])
    age_hours = max(0.0, (now - chosen["mtime"]) / 3600.0)
    is_current = bool(current_session and chosen["session"] == current_session)
    return {
        "path": chosen["path"],
        "basename": chosen["basename"],
        "session": chosen["session"],
        "mtime": chosen["mtime"],
        "age_hours": round(age_hours, 1),
        "is_current": is_current,
        "sibling_count": len(cands) - 1,
    }


def resume_message(claude_dir, current_session, now=None):
    """The human-facing 'read X first' fragment for the SessionStart hook.

    Empty string when no checkpoint exists. Honest about provenance: never
    claims a cross-session or stale file is "fresh".
    """
    sel = select_for_read(claude_dir, current_session, now=now)
    if not sel:
        return ""
    base = sel["basename"]
    age = sel["age_hours"]
    if sel["is_current"]:
        msg = " Read `.claude/%s` first (this session's fresh resume checkpoint)." % base
        if age > 18:
            msg += (
                " It is %.1fh old — verify its 'done' claims against `git log --oneline -15`"
                " before trusting them." % age
            )
    else:
        sess = (sel["session"] or "unknown")[:8]
        msg = (
            " Read `.claude/%s` first, but treat it with care: it is stamped session %s"
            " (%.1fh old), NOT this resuming session — a handoff from another/earlier session"
            " that may be stale. Verify every 'done' claim against `git log --oneline -15`"
            " before acting on it." % (base, sess, age)
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


def _main(argv):
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
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
