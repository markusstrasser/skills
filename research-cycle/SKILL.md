---
name: research-cycle
description: Autonomous research cycle — discover/gap/plan/review/execute/verify/improve loop via subagents. Reads CYCLE.md for human steering, never asks for input. Run with /loop 15m.
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

1. **Recent execution without verification** → run verify (always verify before executing more)
2. **Approved items in queue** (`- [x] APPROVE` in CYCLE.md `## Queue`) → run execute
3. **Active plan not yet reviewed** → run review (probe claims + cross-model via `model-review.py`)
4. **Gaps exist without plan** → run plan phase (write plan for top gap)
5. **Discoveries exist without gap analysis** → run gap-analyze
6. **Verification done without improve** → run improve (includes retro + archival)
7. **Nothing pending** → run discover (includes brainstorm if discover returns empty)

### Running a Phase

**Route by task type, not line count:**
- Docstring, config, research_only field changes → **inline** (fast, reliable)
- Logic changes, even 1-line → **subagent** (fresh context for reasoning about consequences)
- If subagent returns empty (no edit), retry inline once

**Subagent dispatch:**
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

**Discover:** Search for new information relevant to this project. Lead with Exa (more reliable for tools/releases), then search_preprints for papers. For deep audit sweeps, invoke `/dispatch-research`. Compare against git log and research memos. Write findings to CYCLE.md `## Discoveries` as `- [NEW] ...`. Skip anything already known. Commit. Stop searching at 70% of turns and write up. **If nothing found:** invoke `/brainstorm` on the project domain inline. Write ideas to DECISIONS.md as informational context (not approval items). One phase total — brainstorm is part of discover.

**Gap-analyze:** Read CYCLE.md discoveries + `## Maintenance Log` (from /maintain) + project state (CLAUDE.md, git log, research index). Promote actionable maintenance findings to gaps (e.g., "ClinVar 45d stale" → gap: refresh ClinVar). Identify what's missing or needs updating. Write prioritized gaps to `## Gaps`. Classify each: autonomous (reversible, existing pattern) or needs-approval. Commit.

**Plan:** Read top gap from `## Gaps` (skip any marked `FAILED`). Write implementation plan to `## Active Plan`: files to change, what changes, verification method, autonomous or needs-approval. If needs-approval, add to `## Queue` as `- [ ] APPROVE: {gap-id} — {description}`. Commit.

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

**Execute:** Read reviewed plan. If autonomous: implement it. If needs-approval: check `## Queue` for `[x]` mark. If not approved, skip. **Before executing:** note current HEAD SHA. After implementation, commit. Move item from Active Plan to `## Autonomous (done)` with date. Mark corresponding gap entry with `~~done~~` prefix.

**Verify:** Check most recent item in `## Autonomous (done)`. Run relevant tests, cross-check with MCP tools, compare with known-good data. Write results to `## Verification Results`. **If verification fails:** run `git revert HEAD` (preserves history, unlike reset). Mark the gap as `FAILED: {reason}` — skip it for 2 cycles to prevent revert→same-plan→same-fail infinite loops. Write failure to DECISIONS.md for human triage.

**Improve:** Three parts — retro + archival + proposals.
1. **Retro (structured):** Classify this cycle's events using retro categories: WRONG_ASSUMPTION, TOOL_MISUSE, SEARCH_WASTE, TOKEN_WASTE, BUILD_THEN_UNDO. Write structured findings to `## Cycle Retro` in CYCLE.md. Also write JSON to `~/Projects/meta/artifacts/session-retro/{date}-cycle.json` for the improvement pipeline.
2. **Archival:** Move entries older than 2 cycles from `## Autonomous (done)`, `## Verification Results`, and `## Cycle Retro` to `CYCLE-archive.md`. Keep CYCLE.md under 200 lines.
3. **Proposals:** Write tool/process improvement proposals to `## Tool Improvements (proposed)`. For structural improvements, write to `~/.claude/steward-proposals/`. For things needing human input, append to `DECISIONS.md` (informational — no approval checkboxes). NEVER implement tool changes directly — propose only. Commit.

### Queue Management

- **Approvals live ONLY in CYCLE.md `## Queue`.** DECISIONS.md is informational — no `[x]` approval mechanism.
- Human marks `- [x] APPROVE: G5 — description` to approve. Research-cycle reads `[x]` marks from Queue only.
- **Auto-defer:** Queue items not approved within 3 cycles auto-move to `## Deferred` with note "no human response — revisit on request."

### WIP Caps

- Max 3 undispositioned discoveries
- Max 1 active plan
- Max 3 unprocessed maintenance findings (from /maintain)
- Discovery skips if 3+ undispositioned discoveries exist

### Autonomy Boundary

- **Autonomous:** database refreshes (existing sources), config tweaks, `research_only` additions, adding informational fields (no classification change), test runs, verification
- **Queue for human:** new data source downloads (>1GB), structural changes, removing/replacing existing logic, tool upgrades with breaking changes
- **Never:** deleting stages, changing classification thresholds, modifying validated clinical logic, deploying new verification tools (propose only — recursive hallucination trap)

### Human Steering via CYCLE.md

The human edits CYCLE.md between ticks:
- Mark `- [x] APPROVE: ...` in `## Queue` to approve queued items
- Delete discoveries or gaps to dismiss them
- Add notes under gaps to redirect approach
- Add `## Priority: ...` to override phase selection

The skill reads CYCLE.md fresh each tick. Human edits take effect on the next tick.

## Shared Files (coordination with /maintain and human)

| File | Owner | Others | Purpose |
|------|-------|--------|---------|
| `CYCLE.md` | research-cycle | maintain reads + appends `## Maintenance Log` | Research state + approval queue |
| `CYCLE-archive.md` | research-cycle (improve phase) | human reads | Completed items, old retros |
| `DECISIONS.md` | any skill appends | human reads | Informational: questions, ideas, proposals. NO approval checkboxes. |
| `MAINTENANCE.log` | maintain | research-cycle reads | Maintenance audit trail |

**DECISIONS.md convention** (append-only, informational — no approvals here):
```markdown
### [skill-name] Title (date)
Context, question, or idea for human consideration.
No [x] checkboxes — approvals go to CYCLE.md ## Queue only.
```

## Skill Invocations

| Situation | Invoke | Why |
|-----------|--------|-----|
| Deep audit sweep during discover | `/dispatch-research` | Parallel Codex agents for cross-file auditing |
| Plan review (non-trivial) | `/model-review` via script | Cross-model adversarial — same-model can't catch own blind spots |
| Discover returns empty | `/brainstorm` inline | Divergent ideation → ideas to DECISIONS.md (informational) |
| Need literature depth on a paper | `/researcher` | Deep paper analysis with epistemic rigor |
| Improve phase (every cycle) | retro classification framework | Structured findings → JSON for improvement pipeline |
| Domain claim verification | `/bio-verify` or biomedical MCP | Tool-backed evidence, not model reasoning |
| External tool/version check | `/trending-scout` (meta only) | Agent ecosystem scans — not for domain projects |

## Error Recovery

If any phase fails with an error (script crash, tool denied, MCP timeout):
1. Log the error to CYCLE.md `## Errors`
2. Skip the phase for this tick
3. Don't retry the same failing phase more than once consecutively
4. Write the error to DECISIONS.md for human triage
5. Continue to the next tick

## Instrumentation (append to MAINTENANCE.log each improve phase)

Log these counters for measurement:
- `orphan_rate`: approved items not acted on within 2 ticks
- `duplicate_rate`: same discovery/gap appearing twice
- `handoff_success`: maintenance finding → gap promotion
- `review_catch_rate`: issues caught in review
- `verify_fail_rate`: execute → verify failures
- `cycle_latency`: ticks from discovery to shipped item

## Operating Rules

1. **Never ask for input.** Write questions to DECISIONS.md (informational) and move on.
2. **One phase per tick.** Don't chain phases — let the loop do the sequencing.
3. **Report in 1-3 lines.** Phase run, outcome, what's next. No preamble.
4. **Budget awareness.** Track cumulative cost in CYCLE.md header. Warn at $15/day.
5. **Idempotent.** Check git log and CYCLE.md before acting. Don't redo completed work.
6. **Verify before execute.** Never start a new execution with an unverified prior change.

$ARGUMENTS
