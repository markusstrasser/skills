#!/usr/bin/env bash
# sessionend-log.sh — Log session end events + flight receipt for forensics.
# SessionEnd hook. Side-effect only (no decision control). Fails open.
# Logs: timestamp, session, reason, cwd, transcript size, cost (from cockpit state).

HOOK_ERROR_LOG="$HOME/.claude/hook-errors.log"
log_hook_error() {
  local msg="$1"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf '{"ts":"%s","hook":"sessionend-log","error":"%s"}\n' "$ts" "$msg" >> "$HOOK_ERROR_LOG" 2>/dev/null
}
trap 'log_hook_error "bash ERR on line $LINENO"; exit 0' ERR

INPUT=$(cat)

PYTHON_STDERR=$(mktemp)
echo "$INPUT" | python3 -c '
import sys, json, os
from datetime import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session = data.get("session_id", "")
if not session:
    sys.exit(0)

reason = data.get("reason", "unknown")
cwd = data.get("cwd", "")
transcript = data.get("transcript_path", "")

t_lines = 0
if transcript and os.path.isfile(transcript):
    with open(transcript, "rb") as f:
        t_lines = sum(1 for _ in f)

# Read cockpit state persisted by status line
cockpit = {}
cockpit_path = f"/tmp/claude-cockpit-{session}"
if os.path.isfile(cockpit_path):
    try:
        with open(cockpit_path) as f:
            cockpit = json.load(f)
        os.unlink(cockpit_path)  # clean up
    except Exception:
        pass

# Extract project name from cwd
project = os.path.basename(cwd) if cwd else ""

ts = datetime.now().isoformat(timespec="seconds")

# --- Session log (existing format, backwards compatible) ---
log_entry = {
    "ts": ts,
    "session": session,
    "reason": reason,
    "cwd": cwd,
    "transcript_lines": t_lines,
}
log_path = os.path.expanduser("~/.claude/session-log.jsonl")
with open(log_path, "a") as f:
    f.write(json.dumps(log_entry, separators=(",", ":")) + "\n")

# --- Capture recent commits from this session ---
commits = []
if cwd and os.path.isdir(cwd):
    import subprocess
    # Get session start time from current-session-id file mtime
    sid_path = os.path.join(cwd, ".claude", "current-session-id")
    since_arg = None
    if os.path.isfile(sid_path):
        mtime = os.path.getmtime(sid_path)
        since_dt = datetime.fromtimestamp(mtime)
        since_arg = since_dt.strftime("%Y-%m-%dT%H:%M:%S")
    if since_arg:
        try:
            cmd = ["git", "-C", cwd, "log", "--oneline", "-20", f"--since={since_arg}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except Exception:
            pass

# --- Flight receipt (enriched with cockpit data + work summary) ---
duration_ms = int(cockpit.get("duration_ms", 0))
mins = round(duration_ms / 60000, 1) if duration_ms else 0

receipt = {
    "ts": ts,
    "session": session,
    "project": project,
    "model": cockpit.get("model", "?"),
    "branch": cockpit.get("branch", "?"),
    "reason": reason,
    "duration_min": mins,
    "cost_usd": float(cockpit.get("cost", 0)),
    "context_pct": int(cockpit.get("context_pct", 0)),
    "lines_added": int(cockpit.get("lines_added", 0)),
    "lines_removed": int(cockpit.get("lines_removed", 0)),
    "transcript_lines": t_lines,
}
if commits:
    receipt["commits"] = commits
receipt_path = os.path.expanduser("~/.claude/session-receipts.jsonl")
with open(receipt_path, "a") as f:
    f.write(json.dumps(receipt, separators=(",", ":")) + "\n")

# --- Attach git notes to session commits ---
if commits and cwd and os.path.isdir(os.path.join(cwd, ".git")):
    note_body = "session: {}\nmodel: {}\ncost_usd: {:.2f}\nduration_min: {}\nproject: {}".format(session, cockpit.get("model", "?"), float(cockpit.get("cost", 0)), mins, project)
    for commit_line in commits:
        sha = commit_line.split()[0] if commit_line.strip() else ""
        if sha and len(sha) >= 7:
            try:
                subprocess.run(
                    ["git", "-C", cwd, "notes", "--ref=agent", "add", "-f", "-m", note_body, sha],
                    capture_output=True, text=True, timeout=5,
                )
            except Exception:
                pass

# --- Clean up agent state files ---
ppid = os.getppid()
for suffix in ["state", "tool", "prompt", "spinner", "error", "agent", "debrief"]:
    p = f"/tmp/claude-tab-{suffix}-{ppid}"
    try:
        os.unlink(p)
    except FileNotFoundError:
        pass
# Also clean up the agent aggregate file
try:
    os.unlink(f"/tmp/claude-agent-{ppid}")
except FileNotFoundError:
    pass
for p in (f"/tmp/claude-last-notify-{ppid}", f"/tmp/claude-cost-over-{ppid}"):
    try:
        os.unlink(p)
    except FileNotFoundError:
        pass
' 2>"$PYTHON_STDERR"
PYTHON_EXIT=$?

if [ "$PYTHON_EXIT" -ne 0 ]; then
  STDERR_CONTENT=$(cat "$PYTHON_STDERR" | tr '\n' ' ' | tr '"' "'" | head -c 500)
  log_hook_error "python exit=$PYTHON_EXIT: $STDERR_CONTENT"
fi
rm -f "$PYTHON_STDERR"

exit 0
