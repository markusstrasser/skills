#!/usr/bin/env bash
# stop-subagent-synthesis-gate.sh — Stop hook for subagents.
# Blocks stop if the agent wrote output files that are scaffold-only (headers
# without findings). Forces one more turn to synthesize before exiting.
#
# Targets: researcher, general-purpose subagents.
# Skips: main sessions, code-focused types (Explore, Plan, etc.).
# State file prevents re-fire — agent gets one chance to synthesize.

trap 'exit 0' ERR

INPUT=$(cat)

OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json, os, re, time, glob

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

agent_type = data.get("agent_type", "")

# Only fire for subagents — main session has no agent_type
if not agent_type:
    sys.exit(0)

# Skip code-focused types where thin output files are normal
SKIP = {
    "Explore", "Plan", "statusline-setup", "claude-code-guide",
    "session-analyst", "design-review", "supervision-audit",
}
if agent_type in SKIP:
    sys.exit(0)

# State file keyed by agent_id — prevents re-fire after first block
agent_id = data.get("agent_id", "")
state_key = agent_id or str(os.getppid())
state_file = f"/tmp/synthesis-gate-{state_key}"
if os.path.exists(state_file):
    sys.exit(0)

msg = data.get("last_assistant_message", "") or ""
cwd = data.get("cwd", "") or os.getcwd()

# --- Collect candidate output files ---
candidates = set()

# 1. Extract file paths mentioned in the final message
for m in re.finditer(r"(/[\w/._ -]+\.(?:md|json))", msg):
    p = m.group(1)
    if os.path.isfile(p):
        candidates.add(p)

# 2. Scan common output directories for recently modified .md files
search_dirs = [
    os.path.join(cwd, "research"),
    os.path.join(cwd, "docs", "research"),
    os.path.join(cwd, "artifacts"),
]
# Also check home-relative research paths
home = os.path.expanduser("~")
for proj in ["meta", "genomics", "selve", "intel"]:
    for sub in ["research", os.path.join("docs", "research"), "artifacts"]:
        d = os.path.join(home, "Projects", proj, sub)
        if d not in search_dirs:
            search_dirs.append(d)

cutoff = time.time() - 300  # 5 minutes
for d in search_dirs:
    if not os.path.isdir(d):
        continue
    try:
        for f in os.listdir(d):
            if not f.endswith(".md"):
                continue
            fp = os.path.join(d, f)
            try:
                if os.path.getmtime(fp) > cutoff:
                    candidates.add(fp)
            except OSError:
                pass
    except OSError:
        pass

if not candidates:
    sys.exit(0)

# --- Check each candidate for substance ---
MIN_CONTENT_LINES = 10

thin_files = []
for fp in candidates:
    try:
        text = open(fp).read(16384)  # Cap read at 16KB
    except Exception:
        continue

    lines = text.strip().split("\n")
    if len(lines) < 3:
        thin_files.append(os.path.basename(fp))
        continue

    # Count content lines: skip frontmatter, headers, empty, bare list markers
    in_frontmatter = False
    content_count = 0
    for line in lines:
        s = line.strip()
        if s == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s in ("-", "*", "+", "- [ ]", "- [x]"):
            continue
        # Placeholder patterns: "TBD", "TODO", "...", "[content]"
        if re.match(r"^(TBD|TODO|\.\.\.|N/A|\[.*\])$", s, re.IGNORECASE):
            continue
        content_count += 1

    if content_count < MIN_CONTENT_LINES:
        thin_files.append(os.path.basename(fp))

if not thin_files:
    sys.exit(0)

# --- Block and require synthesis ---
# Write state file so we only block once
try:
    open(state_file, "w").write(str(time.time()))
except Exception:
    pass

names = ", ".join(thin_files[:3])
if len(thin_files) > 3:
    names += f" (+{len(thin_files) - 3} more)"

output = {
    "decision": "block",
    "reason": (
        f"SYNTHESIS REQUIRED: {names} contain only scaffolding — "
        "headers and placeholders without actual findings. "
        "Before stopping, write your findings into the file. "
        "Even partial results are valuable. If searches failed, "
        "summarize what you attempted and what the errors indicate. "
        "Do not leave empty sections."
    ),
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    HOOK_DIR="$(dirname "$0")"
    "$HOOK_DIR/hook-trigger-log.sh" "synthesis-gate" "block" "thin subagent output" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
