#!/usr/bin/env bash
# stop-plan-gate.sh — Unified plan completion gate at stop time.
# Merges plan-status (incomplete plan warning) + verify-plan (acceptance criteria).
#
# Two checks:
# 1. If session's plan has status: partial|running → advisory warning
# 2. If session's plan has ```verify block → run commands, block on failure
#
# State file prevents re-fire after verify criteria pass.

trap 'exit 0' ERR

INPUT=$(cat)

STATE_FILE="/tmp/claude-plan-gate-$PPID"
[[ -f "$STATE_FILE" ]] && exit 0

export GATE_STATE_FILE="$STATE_FILE"

OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json, os, re, glob, subprocess

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

# Find plans modified during this session
sid_path = os.path.join(cwd, ".claude", "current-session-id")
if not os.path.isfile(sid_path):
    sys.exit(0)
session_start = os.path.getmtime(sid_path)

plans = glob.glob(os.path.join(plans_dir, "*.md"))
recent = [(p, os.path.getmtime(p)) for p in plans if os.path.getmtime(p) > session_start]
if not recent:
    sys.exit(0)

recent.sort(key=lambda x: x[1], reverse=True)
plan_path = recent[0][0]
plan_name = os.path.basename(plan_path)

try:
    text = open(plan_path).read(16000)
except Exception:
    sys.exit(0)

issues = []

def resolve_transcript_path():
    transcript_path = data.get("transcript_path", "")
    if transcript_path and os.path.isfile(transcript_path):
        return transcript_path

    session_id = data.get("session_id", "")
    if not session_id and os.path.isfile(sid_path):
        try:
            session_id = open(sid_path).read().strip()
        except Exception:
            session_id = ""
    if not session_id:
        return ""

    project_key = cwd.replace("/", "-")
    candidate = os.path.expanduser(
        f"~/.claude/projects/{project_key}/{session_id}.jsonl"
    )
    if os.path.isfile(candidate):
        return candidate
    return ""

def transcript_flags(transcript_path: str):
    strict_patterns = (
        r"execute the entire plan",
        r"full migration",
        r"do until all is done",
        r"after all is done execute a /plan-close",
    )
    strict_re = re.compile("|".join(strict_patterns), re.IGNORECASE)
    review_close_re = re.compile(
        r"<command-name>/review</command-name>.*?<command-(?:args|message)>close</command-(?:args|message)>",
        re.IGNORECASE | re.DOTALL,
    )
    plan_close_re = re.compile(r"<command-name>/plan-close</command-name>", re.IGNORECASE)
    closeout_artifact_re = re.compile(
        r"build_plan_close_context\\.py|plan-close-context|plan-close-review",
        re.IGNORECASE,
    )

    strict_requested = False
    closeout_observed = False
    if not transcript_path or not os.path.isfile(transcript_path):
        return strict_requested, closeout_observed

    try:
        with open(transcript_path) as handle:
            for raw_line in handle:
                try:
                    entry = json.loads(raw_line)
                except Exception:
                    continue

                entry_type = entry.get("type", "")
                raw = raw_line

                texts = []
                message = entry.get("message", {})
                content = message.get("content", "")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))

                if entry_type == "user":
                    if any(strict_re.search(text or "") for text in texts):
                        strict_requested = True
                    if review_close_re.search(raw) or plan_close_re.search(raw):
                        closeout_observed = True
                else:
                    if review_close_re.search(raw) or plan_close_re.search(raw):
                        closeout_observed = True
                    if closeout_artifact_re.search(raw):
                        closeout_observed = True
        return strict_requested, closeout_observed
    except Exception:
        return False, False

# --- Check 1: incomplete plan status ---
fm = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
if fm:
    m = re.search(r"^status:\s*(.+)$", fm.group(1), re.MULTILINE)
    if m:
        status = m.group(1).strip().strip("\"'\''")
        if status in ("partial", "running"):
            phases = re.findall(r"^#{2,3}\s+Phase\s+\d.*$", text, re.MULTILINE)
            total = len(phases)
            done = sum(1 for p in phases if re.search(r"(DONE|done|\u2713|\u2705|\[x\])", p))
            phase_info = f"{done}/{total} phases done" if total > 0 else "no phase markers"
            issues.append(f"Plan {plan_name}: status={status} ({phase_info})")

# --- Check 1b: strict full-plan sessions require explicit closeout ---
# Only check the transcript for user directives — NOT the plan file text.
# Plan files often mention "full migration" in narrative/description without
# the user requesting full execution in this session (false positive).
transcript_path = resolve_transcript_path()
strict_requested, closeout_observed = transcript_flags(transcript_path)
if strict_requested and not closeout_observed:
    issues.append(
        "FULL-PLAN CLOSEOUT: Session was framed as execute-the-entire-plan/full-migration work, "
        "but no closeout step (`/review close`, `/plan-close`, or plan-close context build) "
        "was observed. Before stopping, run the closeout step or state the deferred residue."
    )

# --- Check 2: verify block acceptance criteria ---
lines = text.splitlines()
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

cmds = [c for c in cmds if c.strip() and not c.strip().startswith("#")]

if cmds:
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

    if not all_pass:
        n_pass = sum(1 for r in results if r["pass"])
        report = [f"ACCEPTANCE CRITERIA ({n_pass}/{len(results)} passed):"]
        for r in results:
            icon = "PASS" if r["pass"] else "FAIL"
            report.append(f"  [{icon}] {r['\''cmd'\'']}")
        issues.append("\n".join(report))
    else:
        # All passed — mark state so we do not re-fire
        sf = os.environ.get("GATE_STATE_FILE", "")
        if sf:
            open(sf, "w").close()

if not issues:
    sys.exit(0)

# Decide severity: verify failures block, status warnings also block (so agent sees feedback)
has_verify_failure = any("ACCEPTANCE CRITERIA" in i for i in issues)

reason_text = "\n\n".join(issues)
if has_verify_failure:
    reason_text += "\n\nFix failing criteria before stopping."

output = {
    "decision": "block",
    "reason": reason_text,
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "plan-gate" "check" "plan completion gate" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
