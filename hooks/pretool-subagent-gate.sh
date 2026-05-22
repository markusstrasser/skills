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

# Checks 1+2 removed 2026-05-22: brainstorm/single-tool advisory nags fired
# constantly on legitimate dispatches without measurable behavior change.
# 82 warns/3d, 0 blocks. Routing decisions (Checks 3+4) are the real signal.

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

# Implementation-task heuristic — production-code/test writes, not synthesis
# Used to downgrade Check 7 + Check 10 from BLOCK to advisory when the agent
# is being told to write production files under e2e/, scripts/, src/,
# packages/, tests/, or to create files with code-tree extensions. These
# tasks are short-scoped (5-15 tool calls), not multi-source research, so
# turn-budget / write-stub gates are misapplied. They produced 5+ false-
# positive blocks in one session (2026-05-21) and were the user-cited
# "subagent dispatch boilerplate" complaint.
#
# Two-clause classifier (both required) so that a research prompt that
# *mentions* paths/extensions ("Read all .ts files. Do not write anything.")
# does NOT bypass the gates — only prompts that BOTH name a source-tree
# path AND express write/create/edit intent qualify as implementation.
IS_IMPL_TASK=0
if [ -n "$PROMPT" ]; then
    HAS_PATH=$(echo "$PROMPT" | grep -ciE '(^|[[:space:]/`"'\''])\b(e2e|scripts|src|packages|tests?)/[A-Za-z0-9_./-]+|\.(ts|tsx|mjs|svelte|svx|py|sh|test\.[tj]sx?)\b' || true)
    HAS_WRITE_INTENT=$(echo "$PROMPT" | grep -ciE '\b(write|create|add|edit|modify|patch|implement|fix|build|generate|emit|scaffold|introduce)\b' || true)
    # Negation guard: "do not write" / "don't write" / "without writing" / "no
    # writes" cancels the intent. Read-only research prompts that explicitly
    # disclaim writes must NOT be classified as impl — that would let them
    # bypass the synthesis-budget block they actually need.
    NEGATED_WRITE=$(echo "$PROMPT" | grep -ciE '\b(do not|do[[:space:]]?n.?t|never|without|no)\s+(writ|creat|edit|modif|patch|implement|emit|scaffold|add)' || true)
    if [ "$HAS_PATH" -gt 0 ] && [ "$HAS_WRITE_INTENT" -gt 0 ] && [ "$NEGATED_WRITE" -eq 0 ]; then
        IS_IMPL_TASK=1
    fi
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
            Explore|observe|claude-code-guide|statusline-setup|researcher)
                # Advisory only — these subtypes self-manage via their SKILL.md.
                # researcher's SKILL.md already embeds the CORAL 70%-stop epoch
                # convention; re-requiring it in every dispatch is redundant
                # friction. If a researcher subagent still exhausts turns, the
                # fix is in its SKILL.md, not in dispatch prompts.
                CHECK_IDS="${CHECK_IDS}7,"
                WARNINGS="${WARNINGS}SUBAGENT OUTPUT: Dispatch prompt missing ${MISSING}. "
                ;;
            *)
                # Skip blocking for worktree agents (implementation, not research)
                if [ "$HAS_WORKTREE" -gt 0 ]; then
                    CHECK_IDS="${CHECK_IDS}7,"
                    WARNINGS="${WARNINGS}SUBAGENT OUTPUT: Dispatch prompt missing ${MISSING}. (Advisory — worktree agent, likely implementation.) "
                # Skip blocking for implementation tasks (writing production files
                # under e2e/, scripts/, src/, etc. — short-scoped, not research)
                elif [ "$IS_IMPL_TASK" -gt 0 ]; then
                    CHECK_IDS="${CHECK_IDS}7,"
                    WARNINGS="${WARNINGS}SUBAGENT OUTPUT: Dispatch prompt missing ${MISSING}. (Advisory — implementation task targeting source tree.) "
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
# Also writes promised paths to /tmp/claude-agent-paths-$PPID so the stop-hook
# (stop-subagent-synthesis-gate.sh) can block stop when promised files do not exist.
# Case-insensitive on leading verb (2026-05-07 fix: capital "Output to ..." was missed,
# letting researchers claim "Memo finalized at <path>" without writing the file).
if [ -n "$PROMPT" ]; then
    # Extract file paths from Write/output instructions in the prompt
    OUT_PATH=$(echo "$PROMPT" | grep -oiE '(write|save|output).*(to|path)[^"'\'']*["'\''"]?([~/a-zA-Z0-9_./-]+\.(md|json|txt|py))' | grep -oE '[~/a-zA-Z0-9_./-]+\.(md|json|txt|py)' | head -1 || true)
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
# 2026-05-11 escalation: advisory fired 36 consecutive times in intel sessions
# 4ef78841 + 1792c708 without behavior change. Promoted to BLOCK for substantial
# non-worktree dispatches, mirroring Check 7's case logic. Advisory retained for
# self-managing subtypes and short prompts.
if [ -n "$PROMPT" ] && [ "${HAS_FILE_OUTPUT:-0}" -gt 0 ]; then
    HAS_EARLY_WRITE=$(echo "$PROMPT" | grep -ciE 'probe in progress|write.*(stub|scaffold|skeleton|draft|placeholder|empty).*(first|before|initially)|(first|before)[, ]+writ|(first|before).*(tool|call|action|step).*write|write.*(before|prior to).*(search|probe|fetch|research)|initial.*(write|draft).*file|(scaffold|stub|placeholder).*(first|before)|(begin|start) (by|with).*(writ|creat|scaffold)' || true)
    if [ "$HAS_EARLY_WRITE" -eq 0 ]; then
        PROMPT_LEN=${#PROMPT}
        HAS_WORKTREE=$(echo "$INPUT" | grep -c '"worktree"' || true)
        STUB_FIX="Add to your prompt: 'Your FIRST tool call MUST be Write with a PROBE IN PROGRESS stub at the output path. Then append findings incrementally.' Guards against API-limit / turn-exhaustion producing zero output."
        case "$STYPE" in
            Explore|observe|claude-code-guide|statusline-setup|researcher)
                CHECK_IDS="${CHECK_IDS}10,"
                WARNINGS="${WARNINGS}SUBAGENT WRITE-FIRST: Prompt specifies file output but doesn't instruct write-stub-first. ${STUB_FIX} "
                ;;
            *)
                if [ "$HAS_WORKTREE" -gt 0 ]; then
                    CHECK_IDS="${CHECK_IDS}10,"
                    WARNINGS="${WARNINGS}SUBAGENT WRITE-FIRST: Prompt specifies file output but doesn't instruct write-stub-first. ${STUB_FIX} (Advisory — worktree agent.) "
                elif [ "$IS_IMPL_TASK" -gt 0 ]; then
                    CHECK_IDS="${CHECK_IDS}10,"
                    WARNINGS="${WARNINGS}SUBAGENT WRITE-FIRST: Prompt specifies file output but doesn't instruct write-stub-first. ${STUB_FIX} (Advisory — implementation task; production files are the deliverable, not a synthesis memo.) "
                elif [ "$PROMPT_LEN" -gt 200 ]; then
                    ~/Projects/skills/hooks/hook-trigger-log.sh "subagent-gate" "block" "check=10 missing=write-stub-first" 2>/dev/null || true
                    echo "{\"decision\": \"block\", \"reason\": \"SUBAGENT WRITE-FIRST REQUIRED: Prompt specifies file output but doesn't instruct write-stub-first. ${STUB_FIX}\"}"
                    exit 2
                else
                    CHECK_IDS="${CHECK_IDS}10,"
                    WARNINGS="${WARNINGS}SUBAGENT WRITE-FIRST: Prompt specifies file output but doesn't instruct write-stub-first. ${STUB_FIX} "
                fi
                ;;
        esac
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
