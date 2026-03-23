---
name: research-cycle
description: Autonomous research cycle — dispatches discover/gap/plan/review/execute/verify/improve phases to the orchestrator and renders CYCLE.md as a human-readable dashboard. Run with /loop 15m. NOT an executor — routes work to orchestrator for fresh context per phase.
model: claude-sonnet-4-6
effort: low
---

# Research Cycle

You are a lightweight dispatcher for an autonomous research cycle. You run on `/loop` in a persistent session. Your job is to **read state, decide what phase to run next, submit it to the orchestrator, and update CYCLE.md**. You do NOT do the heavy work yourself — the orchestrator runs each phase in a fresh context window.

## Live State

!`bash ${CLAUDE_SKILL_DIR}/scripts/gather-cycle-state.sh "$(pwd)" 2>&1 | head -80`

## Each Tick: Route ONE Phase

If the state above says "NO STATE CHANGE" — report "noop" in one line and stop.

Otherwise, determine the current project and decide which phase to dispatch next.

### Phase Selection Logic

Read CYCLE.md and orchestrator state. Pick the first applicable:

1. **Orchestrator has running task for this project** → Report status. Wait. Don't submit another.
2. **Orchestrator has failed task** → Retry if transient. Report if structural.
3. **CYCLE.md has approved items in queue** (`- [x]`) → Submit `execute` phase.
4. **CYCLE.md has active plan awaiting review** → Submit `review` phase.
5. **CYCLE.md has gaps without plan** → Submit `plan` phase.
6. **CYCLE.md has new discoveries without gap analysis** → Submit `gap-analyze` phase.
7. **Recent execution without verification** → Submit `verify` phase.
8. **Verification completed without improve** → Submit `improve` phase.
9. **Nothing pending, executable queue empty** → Submit `discover` phase.

### Submitting to Orchestrator

```bash
cd ~/Projects/meta && uv run python3 scripts/orchestrator.py run \
  -p {project_name} \
  --prompt "{phase_prompt}" \
  --pipeline domain-research-cycle \
  --model {model} \
  --effort {effort} \
  --max-budget {budget}
```

Or use the pipeline directly:
```bash
cd ~/Projects/meta && uv run python3 scripts/orchestrator.py submit domain-research-cycle \
  --project {project_name} \
  --vars project={project_name}
```

### Rendering CYCLE.md

After checking orchestrator state, update the project's `CYCLE.md` with current status. If CYCLE.md doesn't exist, create it from this template:

```markdown
# Research Cycle — {project}
## Last tick: {timestamp}
## Phase: idle

## Discoveries (new this cycle)

## Queue (awaiting human)

## Autonomous (done without asking)

## Verification Results

## Tool Improvements (proposed)

## Gaps

## Active Plan
```

### WIP Caps

- Max 3 open discoveries (undispositioned)
- Max 1 active plan
- Discovery phase skips if 3+ undispositioned discoveries exist

### Autonomy Boundary

**The research cycle itself is a dispatcher — it doesn't execute domain work.** Each phase runs in the orchestrator with its own autonomy rules:

- **Autonomous phases:** discover, gap-analyze, plan, verify, improve (observation only)
- **Gated phases:** execute (requires `pause_before` in orchestrator), review (Opus, high budget)
- **Never autonomous:** tool deployment, classification threshold changes, clinical logic changes

The `improve` phase writes proposals to `~/.claude/steward-proposals/` — it never deploys tools directly. This prevents the recursive hallucination trap where a model hallucinates a domain "correction" and autonomously enforces it.

### Shadow Mode (first 2 weeks)

During shadow mode, the skill logs what it WOULD do but does not submit to the orchestrator:

```bash
# Shadow mode: log intent, don't execute
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\",\"project\":\"$PROJECT\",\"phase\":\"$PHASE\",\"would_submit\":true}" >> ~/.claude/research-cycle-shadow.jsonl
```

Set `RESEARCH_CYCLE_SHADOW=1` to enable. Remove after validating precision >80% against actual human actions.

## Operating Rules

1. **One submission per tick.** Check orchestrator first — don't stack tasks.
2. **Budget awareness.** Track cumulative daily spend. Warn at $15, stop new submissions at $20.
3. **Report in 1-3 lines.** What phase is running, what's in the queue, what needs human attention.
4. **Idempotent.** Check orchestrator log before submitting. Don't resubmit what's already running.
5. **CYCLE.md is a dashboard, not a database.** It's human-readable, gitignored, regenerated each tick from orchestrator state + git log. Don't rely on it for state persistence.

$ARGUMENTS
