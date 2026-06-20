#!/usr/bin/env bash
# PostToolUse:Agent — verify promised output file exists after agent completion.
#
# Shebang note: MUST be env bash (5.x), NOT /bin/bash (macOS 3.2). The eval $(python3…)
# parse below silently returns an empty OUT_PATH under bash 3.2's ANSI-C quoting, so the
# hook exited 0 with no advisory — it had never fired once (hook-trigger log count 0)
# despite its target failure recurring 3+ times. subagent-epistemic-gate.sh (which works
# in prod) uses env bash for the same reason.
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

# No output path mentioned → skip file verification (audit-bound check still runs below).
MSG=""

STATUS=""
if [ -n "$OUT_PATH" ]; then
    CHECK_PATH="${OUT_PATH/#\~/$HOME}"
    case "$CHECK_PATH" in
        /*) ;;
        *)  CHECK_PATH="$(pwd)/$CHECK_PATH" ;;
    esac

    if [ ! -e "$CHECK_PATH" ]; then
        STATUS="MISSING"
    elif [ ! -s "$CHECK_PATH" ]; then
        STATUS="EMPTY"
    elif grep -qE '\[PENDING(\]|:)' "$CHECK_PATH" 2>/dev/null; then
        STATUS="PENDING"
    fi

    if [ -n "$STATUS" ]; then
        ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-output-check" "warn" \
            "${STATUS} path=${OUT_PATH} stype=${STYPE}" 2>/dev/null || true

        case "$STATUS" in
            PENDING)
                MSG="SUBAGENT OUTPUT INCOMPLETE: '${OUT_PATH}' exists and is non-empty but still contains an unreplaced [PENDING] placeholder — the subagent wrote its write-first stub then exhausted turns (or died) before filling it in. This is the recurring research-completeness failure; the returned summary may look done while findings are missing. Before trusting it: read the file, and if findings are absent, re-dispatch the SAME agent with the checkpoint path to finish the [PENDING] entries (CORAL epoch) rather than accepting the stub."
                ;;
            *)
                MSG="SUBAGENT OUTPUT ${STATUS}: Dispatch prompt promised file at '${OUT_PATH}' but the file is ${STATUS,,} after completion. The subagent likely exhausted turns, hit API limits, or mis-wrote the path. Before trusting its returned summary, (1) verify by reading the file, (2) re-dispatch with write-stub-first instruction, or (3) treat this output as lost and redo the task directly."
                ;;
        esac
    fi
fi

# Audit-bound check (filesystem scout dispatches must declare SEARCH_ROOT).
AUDIT_MSG=$(printf '%s' "$INPUT" | python3 "$HOME/Projects/skills/hooks/subagent_audit_bound.py" posttool 2>/dev/null \
    | python3 -c 'import sys,json; raw=sys.stdin.read().strip(); print(json.loads(raw).get("additionalContext","") if raw else "")' 2>/dev/null || true)
if [ -n "$AUDIT_MSG" ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-audit-bound" "warn" "missing-bound" 2>/dev/null || true
    if [ -n "$MSG" ]; then
        MSG="${MSG} ${AUDIT_MSG}"
    else
        MSG="$AUDIT_MSG"
    fi
fi

if [ -n "$MSG" ]; then
    SAFE_MSG=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$MSG" 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE_MSG}}"
fi

exit 0
