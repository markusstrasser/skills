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
    "observe",
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

# --- Check for promised-but-missing output files ---
# If dispatch prompt mentioned a specific output path and that file
# does not exist, the agent exhausted turns without writing. Block stop.
# This catches the dominant failure mode: search momentum → no synthesis.
#
# Strategy: scan ALL claude-agent-paths-* temp files (from pretool gate
# Check 8) for paths that do not exist. PPID chain is unreliable across
# agent spawning, so we check all recent dispatch logs within 30 min.
promised_paths = set()
for f in glob.glob("/tmp/claude-agent-paths-*"):
    try:
        if time.time() - os.path.getmtime(f) > 1800:  # 30 min
            continue
        for line in open(f):
            p = line.strip()
            if p and not os.path.isfile(p):
                # Only count paths in research/docs directories (not scratch)
                if any(d in p for d in ["research", "docs", "artifacts"]):
                    promised_paths.add(p)
    except Exception:
        pass

if not candidates and not promised_paths:
    sys.exit(0)

# If we have promised paths that do not exist, block stop
if promised_paths and not candidates:
    missing = ", ".join(os.path.basename(p) for p in list(promised_paths)[:3])
    state_file_p = f"/tmp/synthesis-gate-{state_key}"
    if os.path.exists(state_file_p):
        # Already fired once — let the agent go (avoid infinite block)
        sys.exit(0)
    try:
        open(state_file_p, "w").write(str(time.time()))
    except Exception:
        pass
    output = {
        "decision": "block",
        "reason": (
            f"OUTPUT FILE MISSING: {missing} was promised in your dispatch "
            "prompt but was never created. You exhausted your turns searching "
            "without writing findings. Write your synthesis NOW — even partial "
            "results are valuable. Use the Write tool to create the file."
        ),
    }
    print(json.dumps(output))
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
