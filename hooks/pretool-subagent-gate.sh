#!/usr/bin/env bash
# pretool-subagent-gate.sh — Advisory + blocking gate on Agent tool calls.
# PreToolUse:Agent command hook.
#
# BLOCKING checks (exit 2):
# 0. Memory pressure — blocks on actual system memory (vm_stat) + hard process ceiling
#
# Advisory checks (exit 0 + additionalContext):
# 1. Suggestion/brainstorm pattern in description
# 2. Single-tool pattern (short description matching direct-tool verbs)
# 3. general-purpose when Explore would work
# 4. Research task routed to general-purpose
# 5. File-edit intent via subagent (should use Edit/Write directly)
# 6. Delegation cascade (3+ consecutive Agent calls, with known-limitations prompt)

# ERR trap only for advisory checks — blocking checks handle their own errors
INPUT=$(cat)

# === Check 0: Memory pressure gate (BLOCKING) ===
# Two-tier: actual memory availability via vm_stat (primary) + hard process ceiling (backstop)

CLAUDE_PROCS=$(pgrep -x claude 2>/dev/null | wc -l | tr -d ' ')

# Tier 1: Hard process ceiling — catch runaway spawning regardless of memory
if [ "$CLAUDE_PROCS" -ge 15 ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-gate" "block" "process-ceiling: ${CLAUDE_PROCS}/15" 2>/dev/null || true
    echo '{"decision": "block", "reason": "PROCESS CEILING: '"$CLAUDE_PROCS"' claude processes (hard limit: 15). Likely runaway spawning — wait for agents to finish."}'
    exit 2
fi

# Tier 2: Actual memory pressure via vm_stat (free + inactive + purgeable = reclaimable)
# Cache vm_stat for 5s — same result, avoids 150ms parse on every Agent call
VMSTAT_CACHE="/tmp/claude-vmstat-${PPID}"
CACHE_AGE=999
if [ -f "$VMSTAT_CACHE" ]; then
    CACHE_AGE=$(( $(date +%s) - $(stat -f %m "$VMSTAT_CACHE" 2>/dev/null || echo 0) ))
fi
if [ "$CACHE_AGE" -gt 5 ]; then
    AVAIL_MB=$(vm_stat 2>/dev/null | awk '
      /page size of/ { ps = $(NF-1)+0 }
      /Pages free/      { free = $NF+0 }
      /Pages inactive/  { inactive = $NF+0 }
      /Pages purgeable/ { purgeable = $NF+0 }
      END {
        if (ps > 0) printf "%d", (free + inactive + purgeable) * ps / 1048576
        else print "-1"
      }
    ')
    echo "$AVAIL_MB" > "$VMSTAT_CACHE" 2>/dev/null
else
    AVAIL_MB=$(cat "$VMSTAT_CACHE" 2>/dev/null || echo -1)
fi

# Sanitize — if awk produced garbage, skip memory check (fail open)
case "$AVAIL_MB" in
    ''|*[!0-9-]*) AVAIL_MB=-1 ;;
esac

if [ "$AVAIL_MB" -gt 0 ] && [ "$AVAIL_MB" -lt 1500 ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-gate" "block" "memory-pressure: ${AVAIL_MB}MB avail, ${CLAUDE_PROCS} procs" 2>/dev/null || true
    echo '{"decision": "block", "reason": "MEMORY PRESSURE: '"$AVAIL_MB"'MB available (free+inactive+purgeable), '"$CLAUDE_PROCS"' claude processes. Wait for work to finish or close other apps."}'
    exit 2
fi

# Low-memory advisory (passed to warnings section, doesn't block)
MEM_ADVISORY=""
if [ "$AVAIL_MB" -gt 0 ] && [ "$AVAIL_MB" -lt 3000 ]; then
    MEM_ADVISORY="LOW MEMORY: ${AVAIL_MB}MB available, ${CLAUDE_PROCS} claude procs. Spawning allowed but monitor responsiveness. "
fi

# Advisory checks below — fail open
trap 'exit 0' ERR

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

WARNINGS="${MEM_ADVISORY:-}"
CHECK_IDS=""

# Check 1: Suggestion/brainstorm pattern
if echo "$DESC" | grep -qiE 'suggest|brainstorm|ideas for|what could be|improvements?$'; then
    CHECK_IDS="${CHECK_IDS}1,"
    WARNINGS="${WARNINGS}SUBAGENT BRAINSTORM: Description matches suggestion/brainstorm pattern. Subagents produce ungrounded output for open-ended prompts — consider working directly or using cross-model review instead. "
fi

# Check 2: Single-tool pattern (short description + direct-tool verb)
DESC_LEN=${#DESC}
if [ "$DESC_LEN" -lt 80 ]; then
    if echo "$DESC" | grep -qiE '^(search|find|grep|read|check|look up|fetch|get) '; then
        CHECK_IDS="${CHECK_IDS}2,"
        WARNINGS="${WARNINGS}SUBAGENT OVERHEAD: Short description (${DESC_LEN} chars) matches a single-tool task. A direct Grep/Read/search call would be faster and cheaper than spawning a subagent. "
    fi
fi

# Check 3: general-purpose when Explore would work
if [ "$STYPE" = "general-purpose" ]; then
    if echo "$DESC" | grep -qiE 'explore|find files|codebase|search for|look through|scan.*files'; then
        CHECK_IDS="${CHECK_IDS}3,"
        WARNINGS="${WARNINGS}SUBAGENT TYPE: general-purpose agent for what looks like codebase exploration. Use Explore agent instead — it has the right tools and is purpose-built for this. "
    fi
fi

# Check 4: Research task routed to general-purpose instead of researcher
if [ "$STYPE" = "general-purpose" ]; then
    if echo "$DESC" | grep -qiE 'verify|evidence|literature|systematic review|meta.analysis|primary source|PMID|PubMed|cite|citation|research.*claim|check.*paper'; then
        CHECK_IDS="${CHECK_IDS}4,"
        WARNINGS="${WARNINGS}SUBAGENT TYPE: Research/verification task using general-purpose agent. Use researcher subagent_type instead — it has maxTurns:25, epistemic guardrails, and source-check stop hook. general-purpose agents have no epistemic guardrails. "
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
        CHECK_IDS="${CHECK_IDS}5,"
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
    CHECK_IDS="${CHECK_IDS}6,"
    WARNINGS="${WARNINGS}SUBAGENT CASCADE (${COUNT}): 5+ consecutive Agent calls without other tool use. This suggests sequential work being delegated when it should run directly. Consider whether these tasks actually need subagent isolation. Have you surfaced known limitations of this approach before investing further? "
elif [ "$COUNT" -ge 3 ]; then
    CHECK_IDS="${CHECK_IDS}6,"
    WARNINGS="${WARNINGS}SUBAGENT CASCADE (${COUNT}): 3+ consecutive Agent calls. Check if these are truly independent — sequential chains should run directly. Have you surfaced known limitations/ceilings of the current approach? "
fi

# Check 7: Turn-budget / file-output instruction missing in dispatch prompt
# BLOCKING for research-heavy agents (researcher, general-purpose, Plan, unset)
# Advisory for Explore, observe (read-only or self-managed)
if [ -n "$PROMPT" ]; then
    HAS_TURN_BUDGET=$(echo "$PROMPT" | grep -ciE '(stop|halt|synthesize|write).*(70%|turn|budget|before running out)|max.*(turn|epoch)|epoch.*boundar' || true)
    HAS_FILE_OUTPUT=$(echo "$PROMPT" | grep -ciE '(write|save|output).*(file|path|memo|artifact)' || true)
    if [ "$HAS_TURN_BUDGET" -eq 0 ] || [ "$HAS_FILE_OUTPUT" -eq 0 ]; then
        MISSING=""
        [ "$HAS_TURN_BUDGET" -eq 0 ] && MISSING="turn-budget instruction (stop at 70% and synthesize)"
        [ "$HAS_FILE_OUTPUT" -eq 0 ] && MISSING="${MISSING:+$MISSING + }file-output instruction (write results to a file)"

        # Block research-heavy agents; advise read-only ones
        PROMPT_LEN=${#PROMPT}
        # Check if worktree isolation is set (implementation agent, not research)
        HAS_WORKTREE=$(echo "$INPUT" | grep -c '"worktree"' || true)

        case "$STYPE" in
            Explore|observe|claude-code-guide|statusline-setup)
                # Advisory only — these are read-only or self-managed
                CHECK_IDS="${CHECK_IDS}7,"
                WARNINGS="${WARNINGS}SUBAGENT OUTPUT: Dispatch prompt missing ${MISSING}. "
                ;;
            *)
                # Skip blocking for worktree agents (implementation, not research)
                if [ "$HAS_WORKTREE" -gt 0 ]; then
                    CHECK_IDS="${CHECK_IDS}7,"
                    WARNINGS="${WARNINGS}SUBAGENT OUTPUT: Dispatch prompt missing ${MISSING}. (Advisory — worktree agent, likely implementation.) "
                # Block if prompt is substantial (>200 chars = real research task)
                elif [ "$PROMPT_LEN" -gt 200 ]; then
                    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-gate" "block" "check=7 missing=${MISSING}" 2>/dev/null || true
                    SAFE_MISSING=$(echo "$MISSING" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
                    echo "{\"decision\": \"block\", \"reason\": \"SYNTHESIS BUDGET REQUIRED: Dispatch prompt missing ${MISSING}. Add to your prompt: 'Stop searching at 70% of turns and write synthesis to a file. Return the file path.' This prevents subagent turn exhaustion (6+ confirmed incidents, 30 min recovery each).\"}"
                    exit 2
                else
                    CHECK_IDS="${CHECK_IDS}7,"
                    WARNINGS="${WARNINGS}SUBAGENT OUTPUT: Dispatch prompt missing ${MISSING}. "
                fi
                ;;
        esac
    fi
fi

# Check 8: Disjoint file paths — detect 2+ agents dispatched to same output file
if [ -n "$PROMPT" ]; then
    # Extract file paths from Write/output instructions in the prompt
    OUT_PATH=$(echo "$PROMPT" | grep -oE '(Write|write|save|output).*(to|path)[^"'\'']*["'\''"]?([~/a-zA-Z0-9_./-]+\.(md|json|txt|py))' | grep -oE '[~/a-zA-Z0-9_./-]+\.(md|json|txt|py)' | head -1 || true)
    if [ -n "$OUT_PATH" ]; then
        DISPATCH_LOG="/tmp/claude-agent-paths-$PPID"
        if [ -f "$DISPATCH_LOG" ] && grep -qF "$OUT_PATH" "$DISPATCH_LOG" 2>/dev/null; then
            CHECK_IDS="${CHECK_IDS}8,"
            WARNINGS="${WARNINGS}SUBAGENT PATH COLLISION: Output path '$OUT_PATH' was already dispatched to another agent in this session. Each agent MUST write to its own file — concurrent writes silently overwrite each other. Use unique filenames per agent. "
        fi
        echo "$OUT_PATH" >> "$DISPATCH_LOG"
    fi
fi

# Check 10: Write-stub-first discipline when output file is specified
# When a dispatch prompt requests file output, it should instruct the agent to
# write a stub/scaffold file FIRST, before searching. Without this, the agent
# can die mid-run (API rate limit, network blip, turn exhaustion) and leave
# zero output — the transcript holds the work but nothing persists.
# 2026-04-16 incident: general-purpose agent on HF OpenMed probe hit API limit
# after 43 tool calls, returned status=completed with zero file output.
if [ -n "$PROMPT" ] && [ "${HAS_FILE_OUTPUT:-0}" -gt 0 ]; then
    HAS_EARLY_WRITE=$(echo "$PROMPT" | grep -ciE 'write.*(stub|scaffold|skeleton|draft|placeholder|empty).*(first|before|initially)|(first|before).*(tool|call|action|step).*write|write.*(before|prior to).*(search|probe|fetch|research)|initial.*(write|draft).*file|(scaffold|stub|placeholder).*(first|before)' || true)
    if [ "$HAS_EARLY_WRITE" -eq 0 ]; then
        CHECK_IDS="${CHECK_IDS}10,"
        WARNINGS="${WARNINGS}SUBAGENT WRITE-FIRST: Prompt specifies file output but doesn't instruct write-stub-first. Add: 'Your FIRST tool call MUST be Write with a PROBE IN PROGRESS stub at the output path. Then append findings incrementally.' Guards against API-limit / turn-exhaustion producing zero output. "
    fi
fi

# Check 9: Inject write_json_atomic guidance for genomics project agents
# Agents consistently use json.dump(…, fh) which fails the ratchet test.
# 3/3 measurement agents in 2026-04-05 session needed post-hoc fixes.
if [ -n "$PROMPT" ]; then
    CWD_CHECK=$(pwd)
    if echo "$CWD_CHECK" | grep -q "genomics"; then
        HAS_JSON_GUIDANCE=$(echo "$PROMPT" | grep -c "write_json_atomic" || true)
        if [ "$HAS_JSON_GUIDANCE" -eq 0 ]; then
            PROMPT_WRITES=$(echo "$PROMPT" | grep -ciE '(write|save|output).*(json|file)' || true)
            if [ "$PROMPT_WRITES" -gt 0 ]; then
                CHECK_IDS="${CHECK_IDS}9,"
                WARNINGS="${WARNINGS}GENOMICS JSON: Use write_json_atomic from variant_evidence_core, not json.dump(…, fh). Ratchet test blocks new json.dump-to-file. "
            fi
        fi
    fi
fi

# Emit combined warnings
if [ -n "$WARNINGS" ]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-gate" "warn" "checks=${CHECK_IDS%,} ${WARNINGS:0:80}" 2>/dev/null || true
    # JSON-safe the warnings
    SAFE_WARN=$(echo "$WARNINGS" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null)
    echo "{\"additionalContext\": ${SAFE_WARN}}"
fi

exit 0
