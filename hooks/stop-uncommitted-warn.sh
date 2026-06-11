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

# Multi-agent attribution: a sibling agent editing a file mid-session makes it
# dirty AFTER this baseline, so the delta above wrongly claims it. Drop files a
# DIFFERENT session ledger owns that this one does not — the same per-session
# Edit/Write ledger commit-mine reads (.claude/sessions/<id>.touched-files).
# Sibling edits stay with them; files this session itself edited, and its
# unclaimed subprocess outputs (a regenerated golden lives in no ledger), are
# kept. No session id or no sessions dir falls back to current behavior.
if session_id:
    my_touched = set()
    other_touched = set()
    sessions_dir = os.path.join(cwd, ".claude", "sessions")
    try:
        ledger_entries = os.listdir(sessions_dir)
    except OSError:
        ledger_entries = []
    for entry in ledger_entries:
        if not entry.endswith(".touched-files"):
            continue
        owner_sid = entry[: -len(".touched-files")]
        owned = set()
        try:
            with open(os.path.join(sessions_dir, entry)) as fh:
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
    foreign = other_touched - my_touched
    if foreign:
        new_changes = [f for f in new_changes if f not in foreign]

pre_existing = len(all_changes) - len(new_changes)

if not new_changes:
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
    msg = f"[{scope}] Auto-commit {n} file{plural} at session end"
    body_lines = new_changes[:10]
    if len(new_changes) > 10:
        body_lines.append(f"... and {len(new_changes) - 10} more")
    body = "\n".join(body_lines)
    full_msg = f"{msg}\n\n{body}"

    result = subprocess.run(
        ["git", "commit", "-m", full_msg],
        cwd=cwd, capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        # Auto-commit succeeded. decision:"allow" + top-level additionalContext
        # was never a valid Stop shape — the FYI was silently dropped. The nested
        # hookSpecificOutput channel (>=2.1.163) actually reaches the agent.
        pre_msg = f" ({pre_existing} pre-existing/other-session excluded)" if pre_existing else ""
        output = {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": f"Auto-committed {n} session file{plural}{pre_msg}. No action needed unless the commit grouping is wrong.",
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
