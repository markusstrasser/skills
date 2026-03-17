#!/usr/bin/env bash
# stop-plan-status.sh — Advisory Stop hook: surfaces incomplete plans when agent stops.
# Scans .claude/plans/*.md for status: partial|running or incomplete phases.
# Does NOT block — injects additionalContext reminder.

trap 'exit 0' ERR

INPUT=$(cat)

SCRIPT=$(mktemp /tmp/plan-status-XXXXXX.py)
trap 'rm -f "$SCRIPT"; exit 0' EXIT ERR

cat > "$SCRIPT" << 'PYEOF'
import sys, json, os, re, glob

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

cwd = data.get("cwd", "")
if not cwd:
    sys.exit(0)

plans_dir = os.path.join(cwd, ".claude", "plans")
if not os.path.isdir(plans_dir):
    sys.exit(0)

def parse_plan(path):
    """Return (status, completed, total) from a plan file."""
    try:
        text = open(path).read(8000)
    except Exception:
        return None
    # Only surface plans with explicit YAML frontmatter status
    fm = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm:
        return None
    m = re.search(r"^status:\s*(.+)$", fm.group(1), re.MULTILINE)
    if not m:
        return None
    status = m.group(1).strip().strip("\"'")
    if status not in ("partial", "running"):
        return None
    phases = re.findall(r"^#{2,3}\s+Phase\s+\d.*$", text, re.MULTILINE)
    total = len(phases)
    done = sum(1 for p in phases if re.search(r"(DONE|done|\u2713|\u2705|\[x\])", p))
    return (status, done, total)

incomplete = []
for f in sorted(glob.glob(os.path.join(plans_dir, "*.md"))):
    result = parse_plan(f)
    if result:
        st, done, total = result
        name = os.path.basename(f)
        phase_info = "{}/{} phases done".format(done, total) if total > 0 else "no phase markers"
        incomplete.append("  {}: {} ({})".format(name, st, phase_info))

if not incomplete:
    sys.exit(0)

n = len(incomplete)
listing = "\n".join(incomplete)
suffix = "s" if n != 1 else ""
prompt = "INCOMPLETE PLANS ({}):\n{}\n\nReview these before stopping. Finish pending work or update plan status.".format(n, listing)

print(json.dumps({
    "decision": "block",
    "reason": "Incomplete plans: {} file{}.".format(n, suffix),
    "additionalContext": prompt,
}))
PYEOF

OUTPUT=$(echo "$INPUT" | python3 "$SCRIPT" 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "plan-status" "warn" "incomplete plans found" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
