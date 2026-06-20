#!/usr/bin/env bash
# stop-uncommitted-warn.sh — Stop hook: auto-commits session changes at session end.
# Files modified during the session (delta from baseline) are committed automatically.
# Pre-existing dirty files are left untouched.
# Falls back to blocking advisory if auto-commit fails.

trap 'exit 0' ERR

INPUT=$(cat)

OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json, subprocess, os, re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

cwd = data.get("cwd", "")
if not cwd:
    sys.exit(0)

if not os.path.isdir(os.path.join(cwd, ".git")):
    sys.exit(0)

# Check for uncommitted changes (exclude gitignored files)
try:
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=cwd, capture_output=True, text=True, timeout=5
    ).stdout.strip()
    unstaged = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=cwd, capture_output=True, text=True, timeout=5
    ).stdout.strip()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=cwd, capture_output=True, text=True, timeout=5
    ).stdout.strip()
except Exception:
    sys.exit(0)

all_changes = []
for section in [staged, unstaged, untracked]:
    if section:
        all_changes.extend(section.split("\n"))
all_changes = sorted(set(f for f in all_changes if f.strip()))

if not all_changes:
    sys.exit(0)

# Delta-based filtering: exclude files dirty at session start. Resolve the session
# id stdin-first (per-invocation, race-immune); .claude/current-session-id is a
# single shared file a concurrent agent overwrites, so it is the last-resort
# fallback only (missing/wrong key degrades safely to "warn about everything").
session_id = (data.get("session_id") or "").strip()
if not session_id:
    try:
        with open(os.path.join(cwd, ".claude", "current-session-id")) as f:
            session_id = f.read().strip()
    except (OSError, FileNotFoundError):
        pass
baseline_files = set()
try:
    with open(f"/tmp/session-baseline-{session_id}.txt") as f:
        for line in f:
            name = line[3:].rstrip("\n")
            if name:
                baseline_files.add(name)
except (OSError, FileNotFoundError):
    pass  # No baseline = warn about everything

new_changes = [f for f in all_changes if f not in baseline_files]

# Per-session Edit/Write ledgers — read BOTH producer conventions so attribution
# works in every repo. The .claude/sessions-only read left every repo EXCEPT
# genomics on the whole-delta fallback, which swept concurrent sessions
# (verified 2026-06-13: a peer session checkpoint swept an unrelated session
# uncommitted helper-kill). Sources, each line a repo-relative (or absolute) path:
#   - global  posttool-session-touched-log.sh  -> /tmp/session-touched-<sid>.txt
#   - per-repo posttool-track-touched-files.sh  -> .claude/sessions/<sid>.touched-files
my_touched = set()
other_touched = set()
ledger_files = []  # (owner_sid, abs_path) — hoisted so the attribution policy below can test it even when session_id is empty
if session_id:
    sessions_dir = os.path.join(cwd, ".claude", "sessions")
    try:
        for entry in os.listdir(sessions_dir):
            if entry.endswith(".touched-files"):
                ledger_files.append((entry[: -len(".touched-files")], os.path.join(sessions_dir, entry)))
    except OSError:
        pass
    tmp_prefix = "session-touched-"
    tmp_suffix = ".txt"
    try:
        for entry in os.listdir("/tmp"):
            if entry.startswith(tmp_prefix) and entry.endswith(tmp_suffix):
                ledger_files.append((entry[len(tmp_prefix): -len(tmp_suffix)], os.path.join("/tmp", entry)))
    except OSError:
        pass
    for owner_sid, ledger_path in ledger_files:
        owned = set()
        try:
            with open(ledger_path) as fh:
                for raw_line in fh:
                    rel = raw_line.strip()
                    if not rel:
                        continue
                    if os.path.isabs(rel):
                        try:
                            rel = os.path.relpath(rel, cwd)
                        except ValueError:
                            continue
                    owned.add(rel)
        except OSError:
            continue
        if owner_sid == session_id:
            my_touched |= owned
        else:
            other_touched |= owned

# Attribution policy. When this session has a populated Edit/Write ledger, that
# ledger is the source of truth: auto-commit ONLY files in it. A file in NO
# ledger is an unattributable subprocess output (sync-generated-docs,
# emit_*_event.py pin refreshes) that may belong to a concurrent peer script,
# so auto-committing it is the misattribution bug (2026-06-12: a peer
# verification_events ndjson got swept into this session three times). Those are
# surfaced non-blocking instead, so nothing is silently lost. When the ledger is
# empty (no posttool ledger hook in this repo, or no Edit/Write this session)
# fall back to the prior delta-minus-foreign behavior.
unattributable = []
contested = []
if my_touched:
    unattributable = sorted(
        f for f in new_changes if f not in my_touched and f not in other_touched
    )
    # CONTESTED = in MY ledger AND a peer ledger. Two sessions edited the same file,
    # so a whole-file git add would sweep the peer hunks into this sessions [wip]
    # checkpoint -- the e4076b2 misattribution (2026-06-19: a peer justfile debug
    # recipe rode my maintain-tick edit into a [wip] under my session-id, pointing
    # at untracked peer scripts). Never auto-commit a contested file; defer it for an
    # explicit owner-attributed commit (surfaced below, left in the tree, not lost).
    # Same other_touched-based exclusion already used for unattributable + the
    # no-ledger foreign fallback -- just applied to the in-both case.
    contested = sorted(f for f in new_changes if f in my_touched and f in other_touched)
    new_changes = [f for f in new_changes if f in my_touched and f not in other_touched]
elif ledger_files:
    # A ledger producer exists and there ARE session ledgers, but THIS sessions
    # ledger is empty. Under concurrent peers sharing a checkout, current-session-id
    # clobbering can leave my ledger unwritten while delta-minus-foreign would sweep
    # files that NO ledger claims -- committing a peer subprocess output under this
    # session (observed 2026-06-14: codebase-map.py, owned by no ledger, swept into a
    # [wip]). Fail CLOSED: commit nothing, surface everything as unattributable. The
    # human commits their own explicitly; nothing is lost. Only the genuine
    # no-producer case (ledger_files empty) keeps the delta-minus-foreign fallback.
    unattributable = sorted(new_changes)
    new_changes = []
else:
    foreign = other_touched - my_touched
    if foreign:
        new_changes = [f for f in new_changes if f not in foreign]

# Defer files still being actively written (in-flight subagent output). An mtime
# within the last 90s means a write is in progress; committing now freezes a stub.
# Deferred, NOT dropped — the next checkpoint catches the finished file once it
# stops changing. (2026-06-13: a background research agent stub got swept into a
# [wip] commit repeatedly until this guard.)
import time as _time
_now = _time.time()
def _in_flight(path):
    try:
        return (_now - os.path.getmtime(os.path.join(cwd, path))) < 90
    except OSError:
        return False
in_flight = sorted(f for f in new_changes if _in_flight(f))
new_changes = [f for f in new_changes if f not in in_flight]

# Automation-write ledger — the third writer class beyond own/peer sessions.
# launchd jobs + generators (fm.py, digest/sensor writers) write tracked files
# through neither the Edit/Write tool nor a session ledger, so without this they
# fall to "unattributable -> most likely YOURS" (2026-06-20: agent-failure-modes.md
# + a sensor digest mis-flagged on a session that never touched them). Generators
# self-register via scripts/common/automation_ledger.py; here we drop any path an
# automation wrote within the recency window. FAIL-SAFE: this can only REMOVE files
# from the yours/commit/contest sets (they move to the silent pre-existing/other
# bucket), never add one -- an empty/absent ledger is a no-op, so it cannot cause a
# new auto-commit. Recency-windowed so a one-off automation write does not shadow a
# path a human later edits by hand.
automation_owned = set()
_auto_ledger = os.path.join(os.path.expanduser("~"), ".claude", "automation-write-ledger.jsonl")
_AUTO_WINDOW_S = 36 * 3600
try:
    with open(_auto_ledger) as _fh:
        for _raw in _fh:
            _raw = _raw.strip()
            if not _raw:
                continue
            try:
                _rec = json.loads(_raw)
            except ValueError:
                continue
            if _now - float(_rec.get("ts", 0) or 0) > _AUTO_WINDOW_S:
                continue
            _p = _rec.get("path", "")
            if not _p:
                continue
            if os.path.isabs(_p):
                try:
                    _p = os.path.relpath(_p, cwd)
                except ValueError:
                    continue
            automation_owned.add(_p)
except OSError:
    pass
if automation_owned:
    unattributable = [f for f in unattributable if f not in automation_owned]
    new_changes = [f for f in new_changes if f not in automation_owned]
    contested = [f for f in contested if f not in automation_owned]

# Contested-file advisory (computed once; reused by the empty-branch surface and the
# success-branch note). Empty string when no file is in both ledgers.
contested_note = ""
if contested:
    c = len(contested)
    cplural = "s" if c != 1 else ""
    cnames = ", ".join(contested[:6])
    cmore = f" (+{len(contested) - 6} more)" if len(contested) > 6 else ""
    contested_note = (f" {c} contested file{cplural} (in BOTH this session and a peer ledger) were NOT "
                      f"auto-committed -- whole-file staging would sweep the peer hunks; commit your own "
                      f"hunks explicitly: {cnames}{cmore}.")

def _unattrib_seen_path(sid):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", sid or "nosession")[:64] or "nosession"
    return os.path.join(os.path.expanduser("~"), ".claude", f"stop-unattrib-seen-{safe}.txt")

def _fresh_unattributable(sid, paths):
    if not paths:
        return []
    if not sid:
        return paths
    seen = set()
    p = _unattrib_seen_path(sid)
    try:
        if os.path.isfile(p):
            with open(p) as fh:
                seen = {ln.strip() for ln in fh if ln.strip()}
    except OSError:
        pass
    fresh = [x for x in paths if x not in seen]
    if fresh:
        try:
            with open(p, "a") as fh:
                for x in fresh:
                    fh.write(x + "\n")
        except OSError:
            pass
    return fresh

def _peer_count(d):
    # SINGLE-SOURCE peer detection (epistemic-#9): the same detector SessionStart
    # uses. >=1 means a peer claude shares THIS checkout, so an unattributable
    # subprocess file may be the peers, not ours — never assert "yours" then.
    try:
        r = subprocess.run(
            ["/Users/alien/Projects/skills/hooks/peer-session-count.sh", d],
            capture_output=True, text=True, timeout=8)
        return int((r.stdout or "0").strip() or 0)
    except Exception:
        return 0

unattributable_fresh = _fresh_unattributable(session_id, unattributable)

# Genuinely pre-existing/foreign = everything NOT committed, NOT deferred-in-flight, NOT
# unattributable. The latter two are surfaced in their own messages, so excluding them here
# keeps the "(N pre-existing/other-session excluded)" count from double-counting them.
pre_existing = len(all_changes) - len(new_changes) - len(in_flight) - len(unattributable)

if not new_changes:
    # Nothing this session SOLELY owns (contested files were excluded from auto-commit
    # above). Two categories may still need a non-blocking surface:
    #   (1) CONTESTED (in my ledger AND a peer ledger) -- partly mine, always surface.
    #   (2) UNATTRIBUTABLE subprocess output (in NO ledger) -- may be a peer script
    #       output; surface ONLY when no peer shares the checkout, else it is pure noise
    #       (4 firings on peer debug files, 85bd3604 2026-06-19; suppressed per d1907d3).
    # Files stay in the working tree + git status either way -- no data loss.
    parts = []
    if contested:
        parts.append(contested_note.strip())
    if unattributable_fresh and _peer_count(cwd) < 1:
        u = len(unattributable_fresh)
        uplural = "s" if u != 1 else ""
        ulist = "\n".join(unattributable_fresh[:10])
        parts.append(f"{u} changed file{uplural} were written by a background subprocess (a codex/llmx "
               f"worker YOU launched, or local automation), NOT via the Edit/Write tool, so this "
               f"session did not auto-commit them. No peer claude shares this checkout, so they are "
               f"most likely YOURS: review and commit explicitly:\n{ulist}")
    if parts:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "\n\n".join(parts)}}))
    sys.exit(0)

# Auto-commit session changes
try:
    # Stage only session files
    subprocess.run(
        ["git", "add", "--"] + new_changes,
        cwd=cwd, capture_output=True, text=True, timeout=10,
        check=True
    )
    # Build commit message from file extensions/dirs
    dirs = sorted(set(f.split("/")[0] if "/" in f else "." for f in new_changes))
    scope = dirs[0] if len(dirs) == 1 else "multi"
    n = len(new_changes)
    # NB: this whole program lives in a bash single-quoted string — no single
    # quotes allowed, and backslash-escaped quotes inside f-string expressions
    # are a SyntaxError (this exact idiom kept the hook silently dead until
    # 2026-06-11; the fail-open trap + 2>/dev/null hid it). Precompute plurals.
    plural = "s" if n != 1 else ""
    msg = f"[wip] Auto-checkpoint {n} file{plural} ({scope}) at session end"
    body_lines = new_changes[:10]
    if len(new_changes) > 10:
        body_lines.append(f"... and {len(new_changes) - 10} more")
    body = "\n".join(body_lines)
    full_msg = f"{msg}\n\n{body}\n\nUngated checkpoint: no compile/test ran. Squash into a real commit before building on it."

    result = subprocess.run(
        ["git", "commit", "-m", full_msg],
        cwd=cwd, capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        # Auto-commit succeeded. decision:"allow" + top-level additionalContext
        # was never a valid Stop shape — the FYI was silently dropped. The nested
        # hookSpecificOutput channel (>=2.1.163) actually reaches the agent.
        pre_msg = f" ({pre_existing} pre-existing/other-session excluded)" if pre_existing else ""
        u_msg = ""
        if unattributable_fresh:
            u = len(unattributable_fresh)
            uplural = "s" if u != 1 else ""
            u_msg = f" {u} subprocess-written file{uplural} (in no ledger) were left uncommitted — commit them explicitly if yours."
        inflight_msg = ""
        if in_flight:
            k = len(in_flight)
            kplural = "s" if k != 1 else ""  # precompute plural — NO inline single quotes here, they break the bash-embedded program (see L191 NB)
            inflight_msg = f" Deferred {k} in-flight file{kplural} (mtime<90s, still being written) to the next checkpoint."
        output = {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": f"Auto-checkpointed {n} session file{plural}{pre_msg} as a [wip] commit. UNGATED (no compile/test ran).{inflight_msg}{u_msg}{contested_note}",
            },
        }
        print(json.dumps(output))
        sys.exit(0)
except Exception:
    pass  # Fall through to blocking advisory

# Fallback: auto-commit failed, block and ask agent to commit manually
try:
    subprocess.run(["git", "reset", "HEAD"], cwd=cwd, capture_output=True, timeout=5)
except Exception:
    pass

changes = "\n".join(new_changes)
n = len(new_changes)
plural = "s" if n != 1 else ""
pre_msg = f" ({pre_existing} pre-existing excluded)" if pre_existing else ""
prompt = f"""AUTO-COMMIT FAILED — {n} uncommitted file{plural}{pre_msg}:
{changes[:500]}

Commit these changes with granular semantic commits before stopping.
Use [scope] format."""

output = {
    "decision": "block",
    "reason": prompt,
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "uncommitted-warn" "auto-commit" "session changes" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
