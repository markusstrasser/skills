#!/bin/bash
# PostToolUse:Agent — verify promised output file exists after agent completion.
# Advisory only (measure false-positive rate before escalating).
#
# Problem it addresses (3rd recurrence by 2026-04-07):
#   Researcher/general-purpose subagent exhausts turns or dies mid-run,
#   returns status=completed, but the promised output file is absent or empty.
#   Coordinator assumes success and moves on; findings are lost silently.
#
# Heuristic:
#   1. Extract output path from the dispatch prompt (same regex as Check 8
#      in pretool-subagent-gate.sh — Write/save/output instructions).
#   2. After the agent returns, check: does the file exist and is it >0 bytes?
#   3. If not, emit additionalContext telling the agent the promise was unmet.

trap 'exit 0' ERR
INPUT=$(cat)

# Parse both tool_input (original dispatch) and tool_response (what returned)
eval "$(echo "$INPUT" | python3 -c '
import sys, json, re
try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input", {}) or {}
    prompt = ti.get("prompt", "") or ""
    desc = ti.get("description", "") or ""
    stype = ti.get("subagent_type", "") or ""

    # Extract output file path from prompt. Matches patterns like:
    #   "write to /path/to/foo.md"
    #   "save results to path: artifacts/x.json"
    #   "output file: research/memo.md"
    #   "Return the file path" (no specific path — skip)
    # Mirror the subagent-gate Check 8 regex.
    m = re.search(
        r"(?:Write|write|save|output)[^\n]{0,80}?(?:to|path|at|into|in)?[^\n]{0,40}?"
        r"([~/a-zA-Z0-9_./-]+\.(?:md|json|txt|py|jsonl|csv|tsv|yaml|yml))",
        prompt,
    )
    out_path = m.group(1) if m else ""

    # Shell-safe escaping
    def esc(s): return s.replace("\x27", "\x27\\\x27\x27")
    print(f"OUT_PATH=\x27{esc(out_path)}\x27")
    print(f"STYPE=\x27{esc(stype)}\x27")
    print(f"DESC=\x27{esc(desc[:80])}\x27")
except Exception:
    print("OUT_PATH=\x27\x27")
    print("STYPE=\x27\x27")
    print("DESC=\x27\x27")
' 2>/dev/null)"

# No output path mentioned → nothing to verify. Most Agent calls (Explore,
# brainstorm, single-answer research) don't promise a file and are fine.
[ -z "$OUT_PATH" ] && exit 0

# Expand ~ if present
CHECK_PATH="${OUT_PATH/#\~/$HOME}"

# Resolve relative paths against CWD
case "$CHECK_PATH" in
    /*) ;;  # absolute, keep
    *)  CHECK_PATH="$(pwd)/$CHECK_PATH" ;;
esac

# Verify file exists and is non-empty
STATUS=""
if [ ! -e "$CHECK_PATH" ]; then
    STATUS="MISSING"
elif [ ! -s "$CHECK_PATH" ]; then
    STATUS="EMPTY"
fi

if [ -n "$STATUS" ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-output-check" "warn" \
        "${STATUS} path=${OUT_PATH} stype=${STYPE}" 2>/dev/null || true

    MSG="SUBAGENT OUTPUT ${STATUS}: Dispatch prompt promised file at '${OUT_PATH}' but the file is ${STATUS,,} after completion. The subagent likely exhausted turns, hit API limits, or mis-wrote the path. Before trusting its returned summary, (1) verify by reading the file, (2) re-dispatch with write-stub-first instruction, or (3) treat this output as lost and redo the task directly."

    SAFE_MSG=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$MSG" 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE_MSG}}"
fi

exit 0
