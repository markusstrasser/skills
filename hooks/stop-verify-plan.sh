#!/usr/bin/env bash
# stop-verify-plan.sh — Blocks stop if plan's ```verify block has failing commands.
# Plans with executable acceptance criteria get mechanical verification.
# No verify block → skip silently. All pass → mark state, don't re-fire.

trap 'exit 0' ERR

INPUT=$(cat)

# State file prevents re-fire after all criteria already passed
STATE_FILE="/tmp/claude-verify-$PPID"
if [[ -f "$STATE_FILE" ]]; then
    exit 0
fi

export VERIFY_STATE_FILE="$STATE_FILE"

OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json, os, subprocess, glob

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

cwd = data.get("cwd", "")
if not cwd:
    sys.exit(0)

plan_dir = os.path.join(cwd, ".claude", "plans")
if not os.path.isdir(plan_dir):
    sys.exit(0)

# Find the plans for THIS session. PRIMARY: filename carries the session-id
# prefix (.claude/plans/{session_id[:8]}-{slug}.md) — race-immune. FALLBACK:
# modified after the current-session-id file mtime (legacy; under-detects when a
# peer agent overwrites that SHARED file and bumps its mtime past the plan edits
# this session already made). See memory stop_hook_session_id_concurrency_race.
session_file = os.path.join(cwd, ".claude", "current-session-id")
sid_prefix = (data.get("session_id") or "")[:8]
has_mtime = os.path.isfile(session_file)
if not has_mtime and not sid_prefix:
    sys.exit(0)
session_mtime = os.path.getmtime(session_file) if has_mtime else float("inf")
plans = glob.glob(os.path.join(plan_dir, "*.md"))
def _belongs(p):
    if sid_prefix and os.path.basename(p).startswith(sid_prefix):
        return True
    return has_mtime and os.path.getmtime(p) > session_mtime
recent = [(p, os.path.getmtime(p)) for p in plans if _belongs(p)]
if not recent:
    sys.exit(0)

# Use most recently modified plan
recent.sort(key=lambda x: x[1], reverse=True)
plan_path = recent[0][0]

# Extract ```verify fenced block
with open(plan_path) as f:
    lines = f.readlines()

in_verify = False
cmds = []
for line in lines:
    s = line.rstrip()
    if s.startswith("```verify"):
        in_verify = True
        continue
    if in_verify and s.startswith("```"):
        break
    if in_verify:
        cmds.append(s)

# Filter blanks and comments
cmds = [c for c in cmds if c.strip() and not c.strip().startswith("#")]
if not cmds:
    sys.exit(0)

# Run each command with 30s timeout
results = []
all_pass = True
for cmd in cmds:
    try:
        r = subprocess.run(
            ["bash", "-c", cmd], cwd=cwd,
            capture_output=True, text=True, timeout=30
        )
        passed = r.returncode == 0
        results.append({"cmd": cmd, "pass": passed})
        if not passed:
            all_pass = False
    except subprocess.TimeoutExpired:
        results.append({"cmd": cmd, "pass": False, "error": "timeout"})
        all_pass = False
    except Exception as e:
        results.append({"cmd": cmd, "pass": False, "error": str(e)})
        all_pass = False

if all_pass:
    # Mark state so hook does not re-fire this session
    sf = os.environ.get("VERIFY_STATE_FILE", "")
    if sf:
        open(sf, "w").close()
    sys.exit(0)

# Build failure report
n_pass = sum(1 for r in results if r["pass"])
report = [f"PLAN ACCEPTANCE CRITERIA ({n_pass}/{len(results)} passed):"]
for r in results:
    cmd = r["cmd"]
    icon = "PASS" if r["pass"] else "FAIL"
    report.append(f"  [{icon}] {cmd}")

output = {
    "decision": "block",
    "reason": f"Plan {os.path.basename(plan_path)}: {n_pass}/{len(results)} criteria passed",
    "additionalContext": "\n".join(report) + "\n\nFix failing criteria before stopping."
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    echo "$OUTPUT"
fi

exit 0
