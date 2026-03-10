#!/usr/bin/env bash
# pretool-subagent-gate.sh — Advisory gate on Agent tool calls.
# PreToolUse:Agent command hook. Advisory only (exit 0 + additionalContext).
#
# Checks:
# 1. Suggestion/brainstorm pattern in description
# 2. Single-tool pattern (short description matching direct-tool verbs)
# 3. general-purpose when Explore would work
# 4. Research task routed to general-purpose
# 5. File-edit intent via subagent (should use Edit/Write directly)
# 6. Delegation cascade (3+ consecutive Agent calls, with known-limitations prompt)

trap 'exit 0' ERR

INPUT=$(cat)

# Parse description and subagent_type from tool_input
eval "$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input", {})
    desc = ti.get("description", "")
    stype = ti.get("subagent_type", "")
    # Shell-safe
    desc = desc.replace("'\''", "'\''\\'\'''\''")
    stype = stype.replace("'\''", "'\''\\'\'''\''")
    print(f"DESC='\''{ desc }'\''")
    print(f"STYPE='\''{ stype }'\''")
except Exception:
    print("DESC='\'''\''")
    print("STYPE='\'''\''")
' 2>/dev/null)"

[ -z "$DESC" ] && exit 0

WARNINGS=""

# Check 1: Suggestion/brainstorm pattern
if echo "$DESC" | grep -qiE 'suggest|brainstorm|ideas for|what could be|improvements?$'; then
    WARNINGS="${WARNINGS}SUBAGENT BRAINSTORM: Description matches suggestion/brainstorm pattern. Subagents produce ungrounded output for open-ended prompts — consider working directly or using cross-model review instead. "
fi

# Check 2: Single-tool pattern (short description + direct-tool verb)
DESC_LEN=${#DESC}
if [ "$DESC_LEN" -lt 80 ]; then
    if echo "$DESC" | grep -qiE '^(search|find|grep|read|check|look up|fetch|get) '; then
        WARNINGS="${WARNINGS}SUBAGENT OVERHEAD: Short description (${DESC_LEN} chars) matches a single-tool task. A direct Grep/Read/search call would be faster and cheaper than spawning a subagent. "
    fi
fi

# Check 3: general-purpose when Explore would work
if [ "$STYPE" = "general-purpose" ]; then
    if echo "$DESC" | grep -qiE 'explore|find files|codebase|search for|look through|scan.*files'; then
        WARNINGS="${WARNINGS}SUBAGENT TYPE: general-purpose agent for what looks like codebase exploration. Use Explore agent instead — it has the right tools and is purpose-built for this. "
    fi
fi

# Check 4: Research task routed to general-purpose instead of researcher
if [ "$STYPE" = "general-purpose" ]; then
    if echo "$DESC" | grep -qiE 'verify|evidence|literature|systematic review|meta.analysis|primary source|PMID|PubMed|cite|citation|research.*claim|check.*paper'; then
        WARNINGS="${WARNINGS}SUBAGENT TYPE: Research/verification task using general-purpose agent. Use researcher subagent_type instead — it has maxTurns:20, epistemics+source-grading skills, and source-check stop hook. general-purpose agents have no epistemic guardrails. "
    fi
fi

# Check 5: File-edit intent via subagent
PROMPT=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("prompt", ""))
except Exception:
    pass
' 2>/dev/null)

if echo "$DESC $PROMPT" | grep -qiE 'edit (the |a |this )?file|write (to |the )?file|modify (the |a )?file|update (the |a )?file|fix (the |a |this )?(code|file|bug|issue)|implement (the |a |this )?|create (a |the )?file|add (to|code|a function|the)'; then
    # Exception: worktree isolation is fine for code changes
    if ! echo "$INPUT" | grep -q '"worktree"'; then
        WARNINGS="${WARNINGS}SUBAGENT FILE EDIT: Description/prompt suggests file modification. Agent() creates isolated context — use Edit/Write directly for file changes. If you need isolated code changes, use isolation: worktree. "
    fi
fi

# Check 6: Delegation cascade tracking
CASCADE_FILE="/tmp/claude-agent-cascade-$PPID"
NON_AGENT_FILE="/tmp/claude-non-agent-$PPID"

# Check if a non-Agent tool has fired since last count (reset signal)
if [ -f "$NON_AGENT_FILE" ]; then
    NON_AGENT_TS=$(cat "$NON_AGENT_FILE" 2>/dev/null)
    CASCADE_TS=$(stat -f %m "$CASCADE_FILE" 2>/dev/null || echo 0)
    if [ "${NON_AGENT_TS:-0}" -gt "${CASCADE_TS:-0}" ]; then
        echo "0" > "$CASCADE_FILE"
    fi
fi

# Increment cascade counter
COUNT=$(cat "$CASCADE_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$CASCADE_FILE"

if [ "$COUNT" -ge 5 ]; then
    WARNINGS="${WARNINGS}SUBAGENT CASCADE (${COUNT}): 5+ consecutive Agent calls without other tool use. This suggests sequential work being delegated when it should run directly. Consider whether these tasks actually need subagent isolation. Have you surfaced known limitations of this approach before investing further? "
elif [ "$COUNT" -ge 3 ]; then
    WARNINGS="${WARNINGS}SUBAGENT CASCADE (${COUNT}): 3+ consecutive Agent calls. Check if these are truly independent — sequential chains should run directly. Have you surfaced known limitations/ceilings of the current approach? "
fi

# Emit combined warnings
if [ -n "$WARNINGS" ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-gate" "warn" "${WARNINGS:0:100}" 2>/dev/null || true
    # JSON-safe the warnings
    SAFE_WARN=$(echo "$WARNINGS" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE_WARN}}"
fi

exit 0
