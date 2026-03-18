#!/usr/bin/env bash
# stop-uncommitted-warn.sh — Advisory Stop hook: warns when stopping with uncommitted changes.
# Does NOT block — just injects a reminder via additionalContext.
# Replaces user's manual "IFF everything works: git commit" paste.

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

# Check if this is a git repo
if not os.path.isdir(os.path.join(cwd, ".git")):
    sys.exit(0)

# Check for uncommitted changes (exclude gitignored files)
try:
    # Staged changes
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=cwd, capture_output=True, text=True, timeout=5
    ).stdout.strip()
    # Unstaged changes to tracked files
    unstaged = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=cwd, capture_output=True, text=True, timeout=5
    ).stdout.strip()
    # Untracked files (respects .gitignore — only shows non-ignored untracked)
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

# Deduplicate (file can appear in both staged and unstaged)
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
            # git status --short format: "XY filename" — strip 3-char prefix
            name = line[3:].rstrip("\n")
            if name:
                baseline_files.add(name)
except (OSError, FileNotFoundError):
    pass  # No baseline = warn about everything (current behavior)

new_changes = [f for f in all_changes if f not in baseline_files]
pre_existing = len(all_changes) - len(new_changes)

if not new_changes:
    sys.exit(0)

# Build display for the agent
changes = "\n".join(new_changes)
n = len(new_changes)
pre_msg = f" ({pre_existing} pre-existing excluded)" if pre_existing else ""

prompt = f"""UNCOMMITTED CHANGES ({n} new file{"s" if n != 1 else ""}{pre_msg}):
{changes[:500]}

Before stopping, commit these changes with granular semantic commits.
Use [scope] format. Update CLAUDE.md/README only if warranted by your changes."""

output = {
    "decision": "block",
    "reason": f"Uncommitted changes: {n} files.",
    "additionalContext": prompt,
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "uncommitted-warn" "warn" "uncommitted changes" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
