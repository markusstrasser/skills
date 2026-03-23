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
2. **Active plan not yet reviewed** → run review (probe claims + cross-model via `model-review.py`)
3. **Gaps exist without plan** → run plan phase (write plan for top gap)
4. **Discoveries exist without gap analysis** → run gap-analyze
5. **Recent execution without verification** → run verify
6. **Verification done without improve** → run improve
7. **Nothing pending** → run discover
8. **Discover returned empty** → run `/brainstorm` on the project domain, write ideas to DECISIONS.md

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

**Discover:** Search for new information relevant to this project. Lead with Exa (more reliable for tools/releases), then search_preprints for papers. For deep audit sweeps, invoke `/dispatch-research`. Compare against git log and research memos. Write findings to CYCLE.md `## Discoveries` as `- [NEW] ...`. Skip anything already known. Commit. Stop searching at 70% of turns and write up.

**Gap-analyze:** Read CYCLE.md discoveries + project state (CLAUDE.md, git log, research index). Identify what's missing or needs updating. Write prioritized gaps to `## Gaps`. Classify each: autonomous (reversible, existing pattern) or needs-approval. Commit.

**Plan:** Read top gap from `## Gaps`. Write implementation plan to `## Active Plan`: files to change, what changes, verification method, autonomous or needs-approval. If needs-approval, add to `## Queue` as `- [ ] APPROVE: ...`. Commit.

**Review:** Two steps — probe first, then cross-model review:
1. **Probe external claims inline:** If the plan references any URL, API endpoint, or version number, HTTP-probe it directly. This catches 404s and HTML-instead-of-API before wasting a review cycle (caught 2 bugs in 6 cycles).
2. **Cross-model review via script:** Write the plan to a temp file, then dispatch:
```bash
uv run python3 ~/Projects/meta/scripts/model-review.py \
  --context /tmp/cycle-plan.md \
  --topic "research-cycle-G{N}" \
  --axes simple \
  --project "$(pwd)" \
  "Review this plan for wrong assumptions, missing steps, and anything that could break existing functionality"
```
Route `--axes` by stakes: `simple` for autonomous/low-risk, `standard` for needs-approval, `deep` for structural changes. Skip cross-model entirely for trivial changes (docstring fixes, config tweaks).
Read the output files, apply verified findings to plan. If critical issues, move plan back to gaps. Commit.

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

## Shared Files (coordination with /maintain and human)

| File | Owner | Others | Purpose |
|------|-------|--------|---------|
| `CYCLE.md` | research-cycle | maintain reads + appends `## Maintenance Log` | Research state dashboard |
| `DECISIONS.md` | any skill appends | human reviews | Questions, proposals, ideas needing human input |
| `MAINTENANCE.log` | maintain | research-cycle reads | Maintenance audit trail |

**DECISIONS.md convention** (append-only, any skill can write):
```markdown
### [skill-name] Title (date)
Context and question.
**Options:**
- [ ] Option A
- [ ] Option B
**Your call:** mark chosen option with [x]
```

The human reviews DECISIONS.md periodically. Skills read it for `[x]` marks.

## Skill Invocations

Research-cycle can invoke other skills when appropriate:

| Situation | Invoke | Why |
|-----------|--------|-----|
| Deep audit sweep during discover | `/dispatch-research` | Parallel Codex agents for cross-file auditing |
| Plan review (non-trivial) | `/model-review` via script | Cross-model adversarial — same-model can't catch own blind spots |
| Discover returns empty + no gaps | `/brainstorm` on the project domain | Divergent ideation → ideas written to DECISIONS.md |
| Need literature depth on a paper | `/researcher` | Deep paper analysis with epistemic rigor |

## Operating Rules

1. **Never ask for input.** Write questions to DECISIONS.md and move on.
2. **One phase per tick.** Don't chain phases — let the loop do the sequencing.
3. **Report in 1-3 lines.** Phase run, outcome, what's next. No preamble.
4. **Budget awareness.** Track cumulative cost in CYCLE.md header. Warn at $15/day.
5. **Idempotent.** Check git log and CYCLE.md before acting. Don't redo completed work.
6. **Small edits inline.** Don't dispatch subagents for <10-line changes — inline is faster and more reliable (confirmed in 6-cycle test).

$ARGUMENTS
