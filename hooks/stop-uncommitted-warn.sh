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

# Delta-based filtering: exclude files dirty at session start
session_id_file = os.path.join(cwd, ".claude", "current-session-id")
baseline_files = set()
try:
    with open(session_id_file) as f:
        session_id = f.read().strip()
    with open(f"/tmp/session-baseline-{session_id}.txt") as f:
        for line in f:
            name = line[3:].rstrip("\n")
            if name:
                baseline_files.add(name)
except (OSError, FileNotFoundError):
    pass  # No baseline = warn about everything

new_changes = [f for f in all_changes if f not in baseline_files]
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
    msg = f"[{scope}] Auto-commit {n} file{\"s\" if n != 1 else \"\"} at session end"
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
        # Auto-commit succeeded — allow stop
        pre_msg = f" ({pre_existing} pre-existing excluded)" if pre_existing else ""
        output = {
            "decision": "allow",
            "additionalContext": f"Auto-committed {n} session file{\"s\" if n != 1 else \"\"}{pre_msg}.",
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
pre_msg = f" ({pre_existing} pre-existing excluded)" if pre_existing else ""
prompt = f"""AUTO-COMMIT FAILED — {n} uncommitted file{"s" if n != 1 else ""}{pre_msg}:
{changes[:500]}

Commit these changes with granular semantic commits before stopping.
Use [scope] format."""

output = {
    "decision": "block",
    "reason": f"Uncommitted changes: {n} files (auto-commit failed).",
    "additionalContext": prompt,
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "uncommitted-warn" "auto-commit" "session changes" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
