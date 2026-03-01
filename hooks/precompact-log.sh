#!/usr/bin/env bash
# precompact-log.sh — Record context snapshot + resume checkpoint before compaction.
# PreCompact hook. Side-effect only (no decision control). Fails open.
# Outputs:
#   1. ~/.claude/compact-log.jsonl — append-only compaction log
#   2. <project>/.claude/checkpoint.md — resume checkpoint for continuations

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c '
import sys, json, os, subprocess
from datetime import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session = data.get("session_id", "")
if not session:
    sys.exit(0)

trigger = data.get("trigger", "unknown")
cwd = data.get("cwd", "")
transcript = data.get("transcript_path", "")

t_lines = 0
if transcript and os.path.isfile(transcript):
    with open(transcript, "rb") as f:
        t_lines = sum(1 for _ in f)

# --- Git state ---
modified = []
branch = ""
recent_commits = ""
staged = []
untracked = []
diff_stat = ""

if cwd and os.path.isdir(os.path.join(cwd, ".git")):
    def git(*args, timeout=5):
        r = subprocess.run(
            ["git"] + list(args),
            cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip() if r.returncode == 0 else ""

    try:
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
        modified = [l for l in git("diff", "--name-only").split("\n") if l][:20]
        staged = [l for l in git("diff", "--cached", "--name-only").split("\n") if l][:20]
        untracked = [l for l in git("ls-files", "--others", "--exclude-standard").split("\n") if l][:10]
        recent_commits = git("log", "--oneline", "-5")
        diff_stat = git("diff", "--stat")
    except Exception:
        pass

# --- 1. Append to compaction log (unchanged) ---
log_path = os.path.expanduser("~/.claude/compact-log.jsonl")
entry = {
    "ts": datetime.now().isoformat(timespec="seconds"),
    "session": session,
    "trigger": trigger,
    "cwd": cwd,
    "transcript_lines": t_lines,
    "modified_files": modified,
}
with open(log_path, "a") as f:
    f.write(json.dumps(entry, separators=(",", ":")) + "\n")

# --- 2. Write resume checkpoint ---
if not cwd:
    sys.exit(0)

checkpoint_dir = os.path.join(cwd, ".claude")
os.makedirs(checkpoint_dir, exist_ok=True)
checkpoint_path = os.path.join(checkpoint_dir, "checkpoint.md")

ts = datetime.now().strftime("%Y-%m-%d %H:%M")

lines = []
lines.append("# Resume Checkpoint")
lines.append("")
lines.append("Written by PreCompact hook at " + ts + ".")
lines.append("Read this file at session start or after continuation to re-orient.")
lines.append("")
lines.append("## Session State")
lines.append("- **Session:** `" + session + "`")
lines.append("- **Branch:** `" + branch + "`")
lines.append("- **Trigger:** " + trigger)
lines.append("- **Transcript lines at compaction:** " + str(t_lines))
lines.append(f"")

if modified or staged:
    lines.append("## Uncommitted Changes")
    if staged:
        lines.append("### Staged")
        for fn in staged:
            lines.append("- `" + fn + "`")
    if modified:
        lines.append("### Modified (unstaged)")
        for fn in modified:
            lines.append("- `" + fn + "`")
    lines.append("")

if untracked:
    lines.append("## New Files (untracked)")
    for fn in untracked:
        lines.append("- `" + fn + "`")
    lines.append("")

if diff_stat:
    lines.append("## Diff Summary")
    lines.append("```")
    lines.append(diff_stat)
    lines.append("```")
    lines.append("")

if recent_commits:
    lines.append("## Recent Commits")
    lines.append("```")
    lines.append(recent_commits)
    lines.append("```")
    lines.append("")

with open(checkpoint_path, "w") as f:
    f.write("\n".join(lines) + "\n")
'

exit 0
