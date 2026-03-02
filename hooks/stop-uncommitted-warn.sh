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

# Build display for the agent
changes = "\n".join(all_changes)
n = len(all_changes)

prompt = f"""UNCOMMITTED CHANGES ({n} file{"s" if n != 1 else ""}):
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
    echo "$OUTPUT"
fi

exit 0
