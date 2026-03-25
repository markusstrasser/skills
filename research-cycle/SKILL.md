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

## Rate Limit Detection

Before each tick, check rate limit status:
```bash
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
```

**If rate-limited (CLAUDE_PROCS >= 6):** Route LLM-heavy phases (discover, gap-analyze, plan) through llmx instead of Claude subagents:
- Use `llmx chat -m gemini-3-flash-preview` for discover/gap-analyze (search + synthesis — Flash is free via CLI)
- Use `model-review.py` for review (already routes through llmx)
- Execute and verify phases use tools, not LLM reasoning — run inline regardless
- Write `[rate-limited: used llmx]` tag in CYCLE.md log entries for tracking

**If not rate-limited:** Normal operation (Claude subagents preferred).

## Each Tick

If "NO STATE CHANGE" → one-line noop, stop.

Otherwise, pick the highest-priority phase and run it. **Chain phases** if confident — don't wait for the next tick when the next phase has no blockers. Stop chaining when: rate-limited, context is heavy (>60% used), or the next phase needs external data you don't have yet.

### Phase Priority (first match wins)

1. **Recent execution without verification** → run verify (always verify before executing more)
2. **Items in queue** (CYCLE.md `## Queue`) → run execute. The queue IS the approval — items land there via human steering or gap-analyze. No `[x] APPROVE` gate needed.
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

**Subagent dispatch (normal mode):**
```
Agent(
  prompt="[phase prompt with project context]",
  subagent_type="general-purpose",
  description="research-cycle: [phase]",
  mode="bypassPermissions"
)
```

**llmx dispatch (rate-limited mode):** For discover/gap-analyze/plan phases, write the phase prompt to a temp file and dispatch via llmx:
```bash
cat > /tmp/cycle-phase-prompt.md << 'EOF'
[phase prompt with project context]
EOF
llmx chat -m gemini-3-flash-preview -f /tmp/cycle-phase-prompt.md \
  --timeout 120 -o /tmp/cycle-phase-output.md \
  "[phase instruction]"
# Read output, apply to CYCLE.md, commit
```
Gemini Flash is free via CLI transport — no rate limit conflict with Claude. For phases needing tool use (discover with Exa/S2), work inline with MCP tools but skip subagent delegation.

**Fallback priority:** subagent (fresh context) → llmx (rate-limited) → inline (memory-constrained + rate-limited).

Each phase prompt must include:
- Project root path and name
- Current CYCLE.md content (relevant sections only)
- "Write results back to CYCLE.md. Commit if files changed. Do NOT ask for input."

### Phase Prompts

**Discover:** Search for new information relevant to this project. Lead with Exa (more reliable for tools/releases), then search_preprints for papers. For deep audit sweeps, invoke `/dispatch-research`. Compare against git log and research memos. Write findings to CYCLE.md `## Discoveries` as `- [NEW] ...`. Skip anything already known. Commit. Stop searching at 70% of turns and write up. **If nothing found:** invoke `/brainstorm` on the project domain inline. Write ideas to DECISIONS.md as informational context (not approval items). One phase total — brainstorm is part of discover.

**Gap-analyze:** Read CYCLE.md discoveries + `## Maintenance Log` (from /maintain) + improvement signals (from Live State `IMPROVEMENT SIGNALS` section) + project state (CLAUDE.md, git log, research index). Three gap sources: (1) discoveries from discover phase, (2) maintenance findings promoted to gaps, (3) improvement signals — prioritize `STEER` signals (human steering load) alongside quality/reliability signals. Write prioritized gaps to `## Gaps`. Classify each: autonomous (reversible, existing pattern) or needs-approval. Commit.

**Plan:** Read top gap from `## Gaps` (skip any marked `FAILED` within cooldown). **Before planning:** check `artifacts/failed-experiments/` for prior attempts on the same subsystem — if found, include "Previously tried: {plan_summary}. Failed because: {failure_reason}" in the plan context so the LLM avoids repeating the same approach. Write implementation plan to `## Active Plan`: files to change, what changes, verification method, autonomous or needs-approval. If needs-approval, add to `## Queue` as `- [ ] APPROVE: {gap-id} — {description}`. Commit.

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

**Execute:** Read reviewed plan. Implement it — the queue is the approval, no `[x]` gate. **Before executing:** note current HEAD SHA. After implementation, commit. Move item from Active Plan to `## Autonomous (done)` with date. Mark corresponding gap entry with `~~done~~` prefix.

**Verify:** Check most recent item in `## Autonomous (done)`. Run relevant tests, cross-check with MCP tools, compare with known-good data. Write results to `## Verification Results`. **If verification fails:**
1. **Archive the failed attempt** before reverting (DGM-H variant preservation):
   ```bash
   mkdir -p artifacts/failed-experiments
   git format-patch HEAD~1 -o artifacts/failed-experiments/
   ```
   Write a JSON sidecar `artifacts/failed-experiments/{gap-id}-{date}.json` with gap fingerprint schema: `{gap_id, repo, subsystem, failure_mode, mechanism_tags, base_commit, failing_metric, plan_summary, failure_reason, date, patch_file}`. Schema at `~/Projects/meta/schemas/gap-fingerprint.json`.
2. Run `git revert HEAD` (preserves history, unlike reset).
3. Mark the gap as `FAILED: {reason}` — skip it for 2 cycles.
4. Write failure to DECISIONS.md for human triage.
**TTL:** During improve phase archival, prune `artifacts/failed-experiments/` entries >90 days old that were never retrieved by a plan phase.

**Improve:** Three parts — retro + archival + proposals.
1. **Retro (structured):** Classify this cycle's events using retro categories: WRONG_ASSUMPTION, TOOL_MISUSE, SEARCH_WASTE, TOKEN_WASTE, BUILD_THEN_UNDO. Write structured findings to `## Cycle Retro` in CYCLE.md. Also write JSON to `~/Projects/meta/artifacts/session-retro/{date}-cycle.json` for the improvement pipeline.
2. **Archival:** Move entries older than 2 cycles from `## Autonomous (done)`, `## Verification Results`, and `## Cycle Retro` to `CYCLE-archive.md`. Keep CYCLE.md under 200 lines.
3. **Proposals:** Write tool/process improvement proposals to `## Tool Improvements (proposed)`. For structural improvements, write to `~/.claude/steward-proposals/`. For things needing human input, append to `DECISIONS.md` (informational — no approval checkboxes). NEVER implement tool changes directly — propose only. Commit.

### Queue Management

- **The queue IS the approval.** Items in `## Queue` are ready to execute. No `[x] APPROVE` mechanism — the human steers by adding/removing/reordering items in the queue between ticks.
- Human removes items from queue to block them. Human adds items to queue to request them.
- **Auto-defer:** Queue items that fail execution twice auto-move to `## Deferred` with failure reason.

### WIP Caps

- Max 3 undispositioned discoveries
- Max 1 active plan
- Max 3 unprocessed maintenance findings (from /maintain)
- Discovery skips if 3+ undispositioned discoveries exist

### Autonomy Boundary

- **Autonomous (most things):** refactoring, architecture, integration, infrastructure, database refreshes, config tweaks, `research_only` additions, new scripts, test runs, verification, removing dead code, consolidating duplicates, wiring new stages. Given enough context, the model outperforms the human on how-to-build decisions.
- **Human steers what-to-build:** which analyses matter personally, which clinical decisions to encode, GOALS.md direction. The human expresses this by editing CYCLE.md queue between ticks.
- **Never autonomous:** changing classification thresholds with clinical implications, modifying validated clinical logic, deploying new verification tools (propose only — recursive hallucination trap)

### Human Steering via CYCLE.md

The human edits CYCLE.md between ticks:
- Add items to `## Queue` to request work
- Remove items from `## Queue` to block them
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
2. **Chain confidently, stop when blocked.** Run multiple phases in one tick if the next phase has no external blockers. Stop when: rate-limited, context heavy (>60%), waiting on external data/downloads, or hit a "never autonomous" boundary.
3. **Report in 1-3 lines.** Phase run, outcome, what's next. No preamble.
4. **Budget awareness.** Track cumulative cost in CYCLE.md header. Warn at $15/day.
5. **Idempotent.** Check git log and CYCLE.md before acting. Don't redo completed work.
6. **Verify before execute.** Never start a new execution with an unverified prior change.

$ARGUMENTS
