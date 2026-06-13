#!/usr/bin/env bash
# stop-uncommitted-warn.sh — Stop hook: auto-commits session changes at session end.
# Files modified during the session (delta from baseline) are committed automatically.
# Pre-existing dirty files are left untouched.
# Falls back to blocking advisory if auto-commit fails.

trap 'exit 0' ERR

INPUT=$(cat)

OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json, subprocess, os

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
if session_id:
    ledger_files = []  # (owner_sid, absolute_ledger_path)
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
if my_touched:
    unattributable = sorted(
        f for f in new_changes if f not in my_touched and f not in other_touched
    )
    new_changes = [f for f in new_changes if f in my_touched]
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

pre_existing = len(all_changes) - len(new_changes)

if not new_changes:
    # Nothing this session provably owns. Do NOT auto-commit unattributable
    # subprocess output (it may be a peer script output) — surface it
    # non-blocking so the agent can commit its own outputs explicitly.
    if unattributable:
        u = len(unattributable)
        uplural = "s" if u != 1 else ""
        ulist = "\n".join(unattributable[:10])
        output = {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": f"{u} changed file{uplural} were written by a subprocess and are in no session Edit/Write ledger, so this session did not auto-commit them (they may belong to a concurrent agent script). If they are yours, commit them explicitly:\n{ulist}",
            },
        }
        print(json.dumps(output))
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
        if unattributable:
            u = len(unattributable)
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
                "additionalContext": f"Auto-checkpointed {n} session file{plural}{pre_msg} as a [wip] commit. UNGATED (no compile/test ran).{inflight_msg}{u_msg}",
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
