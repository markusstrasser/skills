---
name: research-cycle
description: Autonomous research cycle — discover/gap/plan/execute/verify/improve loop via subagents. Reads CYCLE.md for human steering, never asks for input. Run with /loop 15m.
model: claude-sonnet-4-6
effort: low
---

# Research Cycle

You run on `/loop`. Each tick you read state, pick the next phase, and execute it — via subagent (preferred, fresh context) or inline (if memory-constrained). **Never ask for input.** The human steers by editing CYCLE.md between ticks.

## Live State

!`bash ${CLAUDE_SKILL_DIR}/scripts/gather-cycle-state.sh "$(pwd)" 2>&1 | head -80`

## Each Tick

If "NO STATE CHANGE" → one-line noop, stop.

Otherwise, pick the highest-priority phase and run it. One phase per tick.

### Phase Priority (first match wins)

1. **Approved items in queue** (`- [x] APPROVE`) → run execute phase
2. **Active plan not yet reviewed** → run review (dispatch `/model-review` via llmx)
3. **Gaps exist without plan** → run plan phase (write plan for top gap)
4. **Discoveries exist without gap analysis** → run gap-analyze
5. **Recent execution without verification** → run verify
6. **Verification done without improve** → run improve
7. **Nothing pending** → run discover

### Running a Phase

**Preferred: subagent** (fresh context, visible, steerable):
```
Agent(
  prompt="[phase prompt with project context]",
  subagent_type="general-purpose",
  description="research-cycle: [phase]",
  mode="bypassPermissions"
)
```

**Fallback: inline** (if `pgrep -c claude` >= 5, do the work directly).

Each phase prompt must include:
- Project root path and name
- Current CYCLE.md content (relevant sections only)
- "Write results back to CYCLE.md. Commit if files changed. Do NOT ask for input."

### Phase Prompts

**Discover:** Search for new information relevant to this project. Use search_preprints (14 days), Exa for new tools/databases, check vendor changelogs. Compare against git log and research memos. Write findings to CYCLE.md `## Discoveries` as `- [NEW] ...`. Skip anything already known. Commit. Stop searching at 70% of turns and write up.

**Gap-analyze:** Read CYCLE.md discoveries + project state (CLAUDE.md, git log, research index). Identify what's missing or needs updating. Write prioritized gaps to `## Gaps`. Classify each: autonomous (reversible, existing pattern) or needs-approval. Commit.

**Plan:** Read top gap from `## Gaps`. Write implementation plan to `## Active Plan`: files to change, what changes, verification method, autonomous or needs-approval. If needs-approval, add to `## Queue` as `- [ ] APPROVE: ...`. Commit.

**Review:** Read `## Active Plan`. Write it to a temp file, then run the model-review script:
```bash
uv run python3 ~/Projects/meta/scripts/model-review.py \
  --context /tmp/cycle-plan.md \
  --topic "research-cycle-G{N}" \
  --axes simple \
  --project "$(pwd)" \
  "Review this genomics pipeline plan for wrong assumptions, missing steps, and anything that could break existing functionality"
```
Use `--axes simple` for autonomous items, `--axes standard` for needs-approval items, `--axes deep` for structural changes. Read the output files, apply verified findings to plan. If critical issues, move plan back to gaps. Commit.

**Execute:** Read reviewed plan. If autonomous: implement it. If needs-approval: check queue for `[x]` mark. If not approved, skip. After implementation, move to `## Autonomous (done)` with date. Commit.

**Verify:** Check most recent item in `## Autonomous (done)`. Run relevant tests, cross-check with MCP tools, compare with known-good data. Write results to `## Verification Results`. If verification fails, revert and move back to gaps. Commit.

**Improve:** Review what happened this cycle — what worked, broke, was slow. Write proposals to `## Tool Improvements (proposed)`. For structural improvements, write to `~/.claude/steward-proposals/`. NEVER implement tool changes directly — propose only. Commit.

### WIP Caps

- Max 3 undispositioned discoveries
- Max 1 active plan
- Discovery skips if 3+ undispositioned discoveries exist

### Autonomy Boundary

- **Autonomous:** database refreshes (existing sources), config tweaks, `research_only` additions, adding informational fields (no classification change), test runs, verification
- **Queue for human:** new data source downloads (>1GB), structural changes, removing/replacing existing logic, tool upgrades with breaking changes
- **Never:** deleting stages, changing classification thresholds, modifying validated clinical logic, deploying new verification tools (propose only — recursive hallucination trap)

### Human Steering via CYCLE.md

The human edits CYCLE.md between ticks:
- Mark `- [x] APPROVE: ...` to approve queued items
- Delete discoveries or gaps to dismiss them
- Add notes under gaps to redirect approach
- Add `## Priority: ...` to override phase selection

The skill reads CYCLE.md fresh each tick. Human edits take effect on the next tick.

## Operating Rules

1. **Never ask for input.** If uncertain, write the question to CYCLE.md and move on.
2. **One phase per tick.** Don't chain phases — let the loop do the sequencing.
3. **Report in 1-3 lines.** Phase run, outcome, what's next. No preamble.
4. **Budget awareness.** Track cumulative cost in CYCLE.md header. Warn at $15/day.
5. **Idempotent.** Check git log and CYCLE.md before acting. Don't redo completed work.

$ARGUMENTS
