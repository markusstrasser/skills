#!/usr/bin/env bash
# stop-visual-fix-verify.sh — Advisory Stop hook.
# Detects "I fixed the layout / it's working now" claims that touch visual
# files (.svelte / .css / .scss / .html) but show no in-session evidence of
# actual browser verification (screenshot, Playwright, Chrome MCP page-load).
#
# Triggered by the 2026-05-16 publishing dossier: agent claimed visual fixes
# 3 times in one session; user had to send screenshots showing it wasn't fixed.
#
# Strategy: deterministic, lexical-only. Reads:
#   - data.last_assistant_message (for the claim)
#   - data.transcript_path        (session JSONL, to scan tool calls in this turn)
#
# Emits advisory output. Always exits 0. Skip with `<!-- visual-verify:skip -->`
# anywhere in the last assistant message.

trap 'exit 0' ERR

INPUT=$(cat)

python3 -c '
import sys, json, os, re
from pathlib import Path

try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

msg = data.get("last_assistant_message", "") or ""
if not msg:
    sys.exit(0)

# Skip marker — let the agent opt out for cases where it deliberately deferred QC.
if "<!-- visual-verify:skip -->" in msg or "visual-verify: skip" in msg.lower():
    sys.exit(0)

# 1) Claim of completion?
SUCCESS_VERBS = re.compile(
    r"\b(fix(?:ed|es)?|works?\s+now|now\s+works?|should\s+(?:work|be\s+working|render)|"
    r"layout\s+is\s+fixed|done|resolved|landed)\b",
    re.IGNORECASE,
)
if not SUCCESS_VERBS.search(msg):
    sys.exit(0)

# 2) Visual-domain language in the claim — must be present to fire.
VISUAL_CTX = re.compile(
    r"\b(layout|css|styling?|alignment|margin|padding|grid|spacing|color|"
    r"oklch|hex|font|typography|hover|highlight|sidenote|marginalia|"
    r"render|rendered|visual|appearance|design|component|svelte)\b",
    re.IGNORECASE,
)
if not VISUAL_CTX.search(msg):
    sys.exit(0)

# 3) Did the session actually touch visual files? Scan the transcript for tool calls.
transcript_path = data.get("transcript_path", "")
if not transcript_path or not os.path.isfile(transcript_path):
    sys.exit(0)

# Walk the JSONL: collect tool calls since the last user message. The pattern:
# - find the index of the most recent user message
# - all assistant tool calls after that index are this turn
touched_visual = False
has_evidence = False

# Evidence patterns: any of these proves the agent verified visually.
EVIDENCE_TOOLS = re.compile(
    r"^("
    r"mcp__claude-in-chrome__|"             # Chrome MCP — any call counts
    r"mcp__playwright__|"                    # Playwright MCP
    r")",
    re.IGNORECASE,
)
EVIDENCE_BASH = re.compile(
    r"\b(playwright|"
    r"bun\s+(?:run\s+)?test|"
    r"bun\s+(?:run\s+)?e2e|"
    r"npm\s+(?:run\s+)?test|"
    r"screenshot|"
    r"page\.screenshot|"
    r"page\.goto|"
    r"chromium|"
    r"webkit|"
    r"firefox\s+--headless"
    r")\b",
    re.IGNORECASE,
)
VISUAL_FILE = re.compile(r"\.(svelte|css|scss|sass|html|svx)(?:$|[?:])", re.IGNORECASE)

# Find last user-message boundary in the transcript.
last_user_idx = -1
lines = []
try:
    with open(transcript_path, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            lines.append(line)
            try:
                rec = json.loads(line)
            except Exception:
                continue
            role = rec.get("message", {}).get("role") or rec.get("type")
            if role == "user":
                last_user_idx = i
except Exception:
    sys.exit(0)

# Scan from after the last user message forward — those are this turn.
for line in lines[last_user_idx + 1:]:
    try:
        rec = json.loads(line)
    except Exception:
        continue
    # tool_use blocks in assistant messages
    content = rec.get("message", {}).get("content")
    if not isinstance(content, list):
        continue
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            name = block.get("name", "") or ""
            tool_input = block.get("input", {}) or {}
            # Evidence — visual verification tool?
            if EVIDENCE_TOOLS.match(name):
                has_evidence = True
            if name == "Bash":
                cmd = str(tool_input.get("command", ""))
                if EVIDENCE_BASH.search(cmd):
                    has_evidence = True
            # Touched a visual file?
            file_path = str(tool_input.get("file_path", "") or tool_input.get("path", ""))
            if VISUAL_FILE.search(file_path):
                touched_visual = True

# Fire only when: agent claimed fix AND touched visual files AND no evidence.
if touched_visual and not has_evidence:
    sys.stderr.write("\n")
    sys.stderr.write("Visual-fix verification check:\n")
    sys.stderr.write("  ! Claimed a visual fix; touched .svelte/.css/.html in this turn;\n")
    sys.stderr.write("    no evidence of browser verification (screenshot, Playwright, Chrome MCP page-load).\n")
    sys.stderr.write("  ! 3+ recorded incidents (2026-05-16) where agent claimed layout fixed without\n")
    sys.stderr.write("    checking; user screenshots showed it wasn'\''t.\n")
    sys.stderr.write("  → Run `bunx playwright test`, take a screenshot via Chrome MCP, or say\n")
    sys.stderr.write("    `<!-- visual-verify:skip -->` if verification is deferred deliberately.\n")
    # Trigger log for telemetry
    os.system("~/Projects/skills/hooks/hook-trigger-log.sh visual-fix-verify advise > /dev/null 2>&1 || true")

sys.exit(0)
'
