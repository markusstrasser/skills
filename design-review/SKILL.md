---
name: design-review
description: Creative architectural review of recent agent sessions. Reads Claude Code and Codex chat logs to find better abstractions, missing tools, repeated workflows that should be pipelines, and system design improvements. NOT anti-pattern detection (use session-analyst) — this is creative synthesis.
argument-hint: [days to review, default 3] [focus area, optional]
---

# Design Review

## Current State
`!echo "Date: $(date +%Y-%m-%d) | Project: $(basename $PWD) | Recent sessions: $(find ~/.claude/projects -name '*.jsonl' -mtime -3 2>/dev/null | wc -l | tr -d ' ') (3d)"`

You are an architectural reviewer. Your job is to read what agents and users actually DO in sessions, then propose better abstractions — not flag mistakes. You're looking for the design that wants to emerge from the usage patterns.

## What This Is NOT
- NOT session-analyst (behavioral anti-patterns)
- NOT supervision-audit (wasted human effort)
- NOT code-review (code quality)
- You don't judge. You observe patterns and propose architecture.

## Phase 1: Gather Sessions

Parse the user's argument for days (default 3) and optional focus area.

**Step 1a: Index recent sessions across all projects.**

```bash
uv run python3 ~/Projects/meta/scripts/sessions.py list --days {DAYS} --format json 2>/dev/null | head -200
```

If `sessions.py` isn't available, fall back to direct discovery:
```bash
find ~/.claude/projects -name '*.jsonl' -mtime -{DAYS} -size +10k | sort -t/ -k6 | head -50
```

**Step 1b: For each session, extract a compressed transcript.**

For each session file, extract ONLY:
- User messages (full text)
- Tool names called (not full results — just the tool name and key argument)
- Agent subagent dispatches (prompt summary)
- Errors and retries
- Final commits (from git commit tool calls)

Use a subagent for each project (parallel) with this extraction prompt:
> Read {session_file}. Extract a compressed log: each user message verbatim, each tool call as one line (tool_name: key_arg), each error as one line, each git commit subject. Skip assistant prose and tool results. Output as markdown.

Target: ~500 lines per session, not 5000.

## Phase 2: Pattern Recognition

With compressed transcripts in context, identify these categories:

### 2a. Repeated Workflows
Sequences of 3+ tool calls that appear in 2+ sessions. These are pipeline candidates.
Format: `workflow_name | tool_sequence | frequency | sessions`

### 2b. Manual Coordination
Places where the user acts as message bus between phases, projects, or agents. The user typing "now do X with the output of Y" is a coordination failure.
Format: `coordination_point | what_user_typed | automation_proposal`

### 2c. Missing Abstractions
When agents reinvent the same logic across sessions — a function, a query, a check, a transform. If it's built twice, it should be a tool.
Format: `abstraction | where_reinvented | proposed_form (function/hook/skill/MCP tool)`

### 2d. Cross-Project Patterns
Similar work happening in different projects that suggests shared infrastructure.
Format: `pattern | projects_affected | shared_infra_proposal`

### 2e. Design Decisions Revisited
Decisions that keep being reconsidered — a sign the original decision was wrong or underdocumented.
Format: `decision | times_revisited | sessions | proposed_resolution`

### 2f. Emergent Architecture
What structure is the system trying to evolve toward? Read the trajectory, not just the current state. What would the system look like if the current trends continued for 6 months?

## Phase 3: Cross-Reference

Before proposing anything, check what already exists:

1. **Read meta's CLAUDE.md** — especially the Constitution, Backlog, and Decision Journal sections
2. **Read meta's improvement-log.md** — are any of your findings already known?
3. **Read meta's research index** (`.claude/rules/research-index.md`) — is there research that applies?
4. **Check existing skills** — `ls ~/Projects/skills/` — does a skill already do this?
5. **Check existing hooks** — grep settings.json for similar hooks

Mark each proposal: `NEW` (not in any existing artifact) or `KNOWN:location` (already tracked somewhere).

## Phase 4: Propose

For each proposal, output:

```markdown
### [Category] Proposal Name

**Pattern:** What you observed (with session references)
**Current cost:** How much human/agent time this wastes per week (estimate)
**Proposal:** What to build (be specific — script? hook? skill? pipeline? MCP tool?)
**Implementation sketch:** 5-10 lines of pseudocode or shell
**Blast radius:** What projects/workflows this affects
**Reversibility:** Easy/medium/hard to undo
**Status:** NEW | KNOWN:location
**Priority:** ROI estimate (time_saved × frequency / implementation_effort)
```

Sort by priority descending.

## Phase 5: Output

Write proposals to `artifacts/design-review/YYYY-MM-DD.md` in the meta project.

**Do NOT:**
- Implement anything (this is a review, not an execution)
- Write to improvement-log.md directly
- Propose changes to the constitution
- Propose things that are already in the meta backlog (just note them as KNOWN)

**DO:**
- Be creative — the best proposals are ones nobody asked for
- Look for the 80/20 — what one abstraction would eliminate the most manual work?
- Name the design that wants to emerge, even if it's not obvious from any single session
- Include at least one "wild card" proposal that challenges a current assumption

## Effort Scaling

- **Quick** (1-2 days, ~10 sessions): Phases 1-2 only, bullet-point output
- **Standard** (3 days, ~20-30 sessions): Full pipeline, written proposals
- **Deep** (7 days, all sessions): Full pipeline + cross-model review of proposals + implementation sketches

Default to **standard** unless the user specifies otherwise.

## Loop Mode

When invoked via `/loop`, use **quick** effort and append to the same daily file. Focus on delta from last run — what's new since the last review?
