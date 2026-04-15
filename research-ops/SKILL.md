---
name: research-ops
description: "Use when: 'run research cycle', 'compile memos into article', 'what's not in training data', 'dispatch parallel audit'. Autonomous research loops, knowledge compilation, training-data diff. For one-shot research questions use /research."
user-invocable: true
argument-hint: <mode> [topic]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent, WebSearch, WebFetch]
effort: high
---

# Research Ops

Operator-initiated research workflows. For one-shot research questions, use `/research`.

| Mode | Trigger | What it does |
|------|---------|--------------|
| `cycle` | `/research-ops cycle` | Autonomous discover/gap/plan/review/execute/verify loop via `/loop 15m` |
| `compile` | `/research-ops compile <concept>` | Synthesize memos into unified article |
| `diff` | `/research-ops diff <text or path>` | Extract what's NOT in training data |
| `dispatch` | `/research-ops dispatch [depth]` | Parallel audit sweep |

---

# Mode: cycle

You run on `/loop`. Each tick you read state, pick the next phase, and execute it — via subagent (preferred, fresh context) or inline (if memory-constrained). **Never ask for input.** The human steers by editing CYCLE.md between ticks.

## Live State

!`bash ${CLAUDE_SKILL_DIR}/scripts/gather-cycle-state.sh "$(pwd)" 2>&1 | head -80`

## Rate Limit Detection

Before each tick, check rate limit status:
```bash
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
```

**If rate-limited (CLAUDE_PROCS >= 6):** Route LLM-heavy phases (discover, gap-analyze, plan) through the shared dispatch helper instead of Claude subagents:
- Use `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile cheap_tick ...` for discover/gap-analyze (shared artifact contract, no raw CLI dispatch)
- Use `model-review.py` for review (already routes through llmx)
- Execute and verify phases use tools, not LLM reasoning — run inline regardless
- Write `[rate-limited: used shared dispatch]` tag in CYCLE.md log entries for tracking

**If not rate-limited:** Normal operation (Claude subagents preferred).

## Each Tick

If "NO STATE CHANGE" -> one-line noop, stop.

Otherwise, pick the highest-priority phase and run it. **Chain phases** if confident — don't wait for the next tick when the next phase has no blockers. Stop chaining when: rate-limited, context is heavy (>60% used), or the next phase needs external data you don't have yet.

### Phase Priority (first match wins)

1. **Recent execution without verification** -> run verify (always verify before executing more)
2. **Items in queue** (CYCLE.md `## Queue`) -> run execute. The queue IS the approval — items land there via human steering or gap-analyze. No `[x] APPROVE` gate needed.
3. **Active plan not yet reviewed** -> run review (probe claims + cross-model via `model-review.py`)
4. **Gaps exist without plan** -> run plan phase (write plan for top gap)
5. **Discoveries exist without gap analysis** -> run gap-analyze
6. **Verification done without improve** -> run improve (includes retro + archival)
7. **Nothing pending** -> run discover (includes brainstorm if discover returns empty)

### Running a Phase

**Route by task type, not line count:**
- Docstring, config, research_only field changes -> **inline** (fast, reliable)
- Logic changes, even 1-line -> **subagent** (fresh context for reasoning about consequences)
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

**Shared dispatch (rate-limited mode):** For discover/gap-analyze/plan phases, write the phase prompt to a temp file and dispatch via the wrapper:
```bash
cat > /tmp/cycle-phase-prompt.md << 'EOF'
[phase prompt with project context]
EOF
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile cheap_tick \
  --context /tmp/cycle-phase-prompt.md \
  --prompt "[phase instruction]" \
  --output /tmp/cycle-phase-output.md \
  --meta /tmp/cycle-phase-meta.json \
  --error-output /tmp/cycle-phase-error.json
# Read output, inspect meta/error artifacts on failure, apply to CYCLE.md, commit
```
For phases needing tool use (discover with Exa/S2), work inline with MCP tools but skip subagent delegation.

**Fallback priority:** subagent (fresh context) -> shared dispatch (rate-limited) -> inline (memory-constrained + rate-limited).

Each phase prompt must include:
- Project root path and name
- Current CYCLE.md content (relevant sections only)
- "Write results back to CYCLE.md. Commit if files changed. Do NOT ask for input."
- **Turn budget:** "Stop searching at 70% of your turns and synthesize. Do NOT exhaust all turns on searching."
- **Recitation:** "Before drawing conclusions, recite the key evidence you're working with."

### Phase Prompts

**Discover:** Search for new information relevant to this project. Lead with Exa (more reliable for tools/releases), then search_preprints for papers. For deep audit sweeps, invoke `/research dispatch`. Compare against git log and research memos. Write findings to CYCLE.md `## Discoveries` as `- [NEW] ...`. Skip anything already known. Commit. Stop searching at 70% of turns and write up. **If nothing found:** invoke `/brainstorm` on the project domain inline. Write ideas to DECISIONS.md as informational context (not approval items). One phase total — brainstorm is part of discover.

**Gap-analyze:** Read CYCLE.md discoveries + improvement signals (from Live State `IMPROVEMENT SIGNALS` section) + project state (CLAUDE.md, git log, research index). Two gap sources: (1) discoveries from discover phase, (2) improvement signals — prioritize `STEER` signals (human steering load) alongside quality/reliability signals. SWE quality gaps (code bugs, freshness, refactoring) are handled by `/maintain` in the separate SWE quality lane — don't duplicate that work here. Write prioritized gaps to `## Gaps`. Classify each: autonomous (reversible, existing pattern) or needs-approval. Commit.

**Plan:** Read top gap from `## Gaps` (skip any marked `FAILED` within cooldown). **Before planning:** check `artifacts/failed-experiments/` for prior attempts on the same subsystem — if found, include "Previously tried: {plan_summary}. Failed because: {failure_reason}" in the plan context so the LLM avoids repeating the same approach. Write implementation plan to `## Active Plan`: files to change, what changes, verification method. Add to `## Queue` for execution. Commit.

**Review:** Three steps — blind assessment, probe, then cross-model review:
1. **Blind first-pass:** Read the plan WITHOUT re-reading the gap-analyze output. Form an independent assessment of whether the plan addresses the right problem and has the right approach. Write your assessment. THEN compare to the gap-analyze output and note divergences. This breaks confirmation bias (SycEval baseline: 58% fold rate without structural mitigation).
2. **Probe external claims inline:** If the plan references any URL, API endpoint, or version number, HTTP-probe it directly. This catches 404s and HTML-instead-of-API before wasting a review cycle (caught 2 bugs in 6 cycles).
3. **Cross-model review via script:** Write the plan to a temp file, then dispatch:
```bash
uv run python3 ~/Projects/skills/critique/scripts/model-review.py \
  --context /tmp/cycle-plan.md \
  --topic "research-cycle-G{N}" \
  --axes standard \
  --project "$(pwd)" \
  "Review this plan for wrong assumptions, missing steps, and anything that could break existing functionality"
```
Route `--axes` by stakes: `standard` for autonomous/low-risk, `deep` for needs-approval, `full` for structural changes. Skip cross-model entirely for trivial changes (docstring fixes, config tweaks).
Read the output files, apply verified findings to plan. If critical issues, move plan back to gaps. **On model-review failure:** check exit code + stderr before retrying. Classify: auth (retry), rate-limit (fall back to other model), timeout (reduce context), schema error (fix input). Do NOT blindly retry the same model (FM24). Commit.

**Execute:** Read reviewed plan. Implement it — the queue is the approval, no `[x]` gate. **Before executing:** note current HEAD SHA. After implementation, commit. **Reflect inline** (1-3 lines under the done entry): what was easier/harder than planned, did plan assumptions hold, anything to carry forward. Move item from Active Plan to `## Autonomous (done)` with date + reflection. Mark corresponding gap entry with `~~done~~` prefix.

**Verify:** Check most recent item in `## Autonomous (done)`. Two verification tracks depending on output type:

**Track A — Infrastructure changes** (code, config, hooks, scripts): Run relevant tests, check file existence, compare with known-good data. Same as before.

**Track B — Research output** (executed item produced or modified `research/*.md`): Run factual claim verification:
1. Extract 3-5 key factual claims from the output (specific numbers, dates, named entities, causal assertions — not opinions or interpretations)
2. For each claim, call `verify_claim` MCP tool
3. Record verdicts in `## Verification Results`:
   ```
   [DATE] **[item]:** claim verification (N claims checked)
   - "Claim text" -> supported (0.85) PASS
   - "Claim text" -> insufficient (0.4) WARN
   - "Claim text" -> contradicted (0.9) FAIL
   ```
4. **FAIL threshold:** Any claim "contradicted" with confidence >0.7 -> trigger revert flow below
5. **WARN threshold:** "insufficient" verdicts -> append to DECISIONS.md for human review, don't block
6. If all claims supported or insufficient with low confidence -> PASS

For both tracks, write results to `## Verification Results`. **If verification fails:**
1. **Archive the failed attempt** before reverting (DGM-H variant preservation):
   ```bash
   mkdir -p artifacts/failed-experiments
   git format-patch HEAD~1 -o artifacts/failed-experiments/
   ```
   Write a JSON sidecar `artifacts/failed-experiments/{gap-id}-{date}.json` with gap fingerprint schema: `{gap_id, repo, subsystem, failure_mode, mechanism_tags, base_commit, failing_metric, plan_summary, failure_reason, date, patch_file}`. Schema at `~/Projects/agent-infra/schemas/gap-fingerprint.json`.
2. Run `git revert HEAD` (preserves history, unlike reset).
3. Mark the gap as `FAILED: {reason}` — skip it for 2 cycles.
4. Write failure to DECISIONS.md for human triage.
**TTL:** During improve phase archival, prune `artifacts/failed-experiments/` entries >90 days old that were never retrieved by a plan phase.

**Improve:** Three parts — retro + archival + proposals.
1. **Retro (structured):** Classify this cycle's events using retro categories: WRONG_ASSUMPTION, TOOL_MISUSE, SEARCH_WASTE, TOKEN_WASTE, BUILD_THEN_UNDO. Write structured findings to `## Cycle Retro` in CYCLE.md. Also write JSON to `~/Projects/agent-infra/artifacts/session-retro/{date}-cycle.json` for the improvement pipeline.
2. **Archival:** Move entries older than 2 cycles from `## Autonomous (done)`, `## Verification Results`, and `## Cycle Retro` to `CYCLE-archive.md`. Keep CYCLE.md under 200 lines.
3. **Proposals:** Write tool/process improvement proposals to `## Tool Improvements (proposed)`. For structural improvements, write to `~/.claude/steward-proposals/`. For things needing human input, append to `DECISIONS.md` (informational — no approval checkboxes). NEVER implement tool changes directly — propose only. Commit.

### Queue Management

- **The queue IS the approval.** Items in `## Queue` are ready to execute. No `[x] APPROVE` mechanism — the human steers by adding/removing/reordering items in the queue between ticks.
- Human removes items from queue to block them. Human adds items to queue to request them.
- **Auto-defer:** Queue items that fail execution twice auto-move to `## Deferred` with failure reason.

### WIP Caps

- Max 3 undispositioned discoveries
- Max 1 active plan
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

## Shared Files (coordination with human)

| File | Owner | Others | Purpose |
|------|-------|--------|---------|
| `CYCLE.md` | research-cycle | human steers | Growth state + approval queue |
| `CYCLE-archive.md` | research-cycle (improve phase) | human reads | Completed items, old retros |
| `DECISIONS.md` | any skill appends | human reads | Informational: questions, ideas, proposals. NO approval checkboxes. |

Note: `/maintain` owns the separate SWE quality lane (`MAINTAIN.md`). research-cycle does not read or write maintenance state.

**DECISIONS.md convention** (append-only, informational — no approvals here):
```markdown
### [skill-name] Title (date)
Context, question, or idea for human consideration.
No [x] checkboxes — approvals go to CYCLE.md ## Queue only.
```

## Skill Invocations

| Situation | Invoke | Why |
|-----------|--------|-----|
| Deep audit sweep (SWE quality) | `/improve maintain` owns this lane | Use `/research dispatch` directly for growth-adjacent audits only |
| Plan review (non-trivial) | `/critique model` via script | Cross-model adversarial — same-model can't catch own blind spots |
| Discover returns empty | `/brainstorm` inline | Divergent ideation -> ideas to DECISIONS.md (informational) |
| Need literature depth on a paper | `/research query` | Deep paper analysis with epistemic rigor |
| Improve phase (every cycle) | retro classification framework | Structured findings -> JSON for improvement pipeline |
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
- `swe_lane_items`: items in MAINTAIN.md (tracked by /maintain, not research-cycle)
- `review_catch_rate`: issues caught in review
- `verify_fail_rate`: execute -> verify failures
- `cycle_latency`: ticks from discovery to shipped item

## Operating Rules

1. **Never ask for input.** Write questions to DECISIONS.md (informational) and move on.
2. **Chain confidently, stop when blocked.** Run multiple phases in one tick if the next phase has no external blockers. Stop when: rate-limited, context heavy (>60%), waiting on external data/downloads, or hit a "never autonomous" boundary.
3. **Report in 1-3 lines.** Phase run, outcome, what's next. No preamble.
4. **Budget awareness.** Track cumulative cost in CYCLE.md header. Warn at $15/day.
5. **Idempotent.** Check git log and CYCLE.md before acting. Don't redo completed work.
6. **Verify before execute.** Never start a new execution with an unverified prior change.

---

# Mode: compile

Synthesize scattered research memos into a unified concept article for **human consumption**. Reads across projects, extracts claims with provenance, surfaces contradictions, identifies gaps.

**This is a human UX tool, not an agent navigation tool.** Evidence shows agents navigate better with flat source files + grep than with pre-synthesized articles (Cao et al. 2026: retrieval hurts by 40.5%; Gloaguen et al. 2026: broad context files reduce agent success by 0.5-3% and inflate cost by >20%). Compiled articles are for the human to read when they want a consolidated view of cross-project knowledge. Do NOT build a systematic "wiki layer" of compiled articles — agents should grep the source memos directly.

**Not an entity page.** Entity pages (via /entity-management) track facts about a single entity with versioned provenance. Compiled articles synthesize *understanding* across multiple sources and multiple entities.

## When to Use

- **Human** asks "what do we know about X across projects?" and wants a readable overview
- Before a **human decision** that depends on cross-project domain knowledge
- After a research cycle, to help the **human** consolidate understanding
- Multiple research memos (3+) touch the same concept but were written in different sessions/projects and haven't been synthesized

## Phases

### Phase 1: Discover Sources

Search across all three projects for the concept:

```bash
# Header-grep FIRST — finds files where concept is a primary topic
grep -r "^#.*{concept}" ~/Projects/phenome/docs/ ~/Projects/genomics/docs/ ~/Projects/agent-infra/research/ --include="*.md" -l

# MCP search for section-level matches
search_meta("{concept}", scope="all", max_tokens=500)
```

List all matching files with a one-line relevance snippet. Discard files that mention the concept only in passing (single reference in a list). Keep files where the concept is a primary topic or has a dedicated section.

**Stop at 70% of turns and synthesize** — don't search exhaustively.

### Phase 2: Read and Extract

For each source file (up to 15):

1. Read the file (or relevant sections if large)
2. Extract discrete claims about the concept, each with:
   - The claim text
   - Source file path and project
   - Date (from frontmatter or filename)
   - Confidence/conviction level (if stated)
   - Source grade (if tagged, e.g., [A1], [CALC])
3. Note any contradictions between sources
4. Note the date of each source — older claims may be superseded

### Phase 3: Compile

Produce a unified markdown article:

```markdown
---
type: compiled
concept: {Concept Name}
compiled: {YYYY-MM-DD}
sources: {N}
projects: [{list of projects with sources}]
---

## Summary

[2-3 sentence overview of current understanding. Lead with what's known,
then what's uncertain.]

## Key Claims

| # | Claim | Source | Project | Date | Grade |
|---|-------|--------|---------|------|-------|
| 1 | ... | pgx_deep_dive.md | selve | 2026-03 | [A1] |
| 2 | ... | combinatorial_pgx_memo.md | genomics | 2026-02 | [CALC] |

[Order by confidence, not chronologically. Highest-confidence claims first.]

## Contradictions and Open Questions

[Where sources disagree, cite both sides with their provenance.
These are the most valuable part — they surface disagreements that
live in different repos and would otherwise go unnoticed.]

## Timeline

[If the understanding evolved over time, show the progression:
when beliefs changed and why.]

## Cross-References

[Links to all source memos, grouped by project]

## Gaps

[What's missing — questions that no source addresses, data that
would resolve contradictions, follow-up research suggested.]
```

### Phase 4: File

Route the compiled article based on scope:

**Cross-project compilations** (sources from 2+ projects):
- Write to `~/Projects/agent-infra/research/compiled/{concept-slug}.md`

**Single-project compilations** (all sources from one project):
- Write to that project's `docs/compiled/{concept-slug}.md`

Create the `compiled/` directory if it doesn't exist.

Commit with message: `[research] Compile {concept} — {N} sources across {projects}`

## Anti-Patterns

- **Don't compile with <3 sources.** Below 3, just read the memos directly.
- **Don't resolve contradictions.** Surface them. Resolution requires judgment the skill doesn't have.
- **Don't include every mention.** A memo that mentions CYP2D6 once in a list is not a source about CYP2D6. Filter to substantive coverage.
- **Don't skip the gaps section.** The gaps are what make the next research session productive.
- **Don't build a wiki layer.** Evidence shows pre-synthesized articles hurt agent navigation. Compile for human understanding, not for agent consumption.

---

# Mode: diff

Extract the information delta between a text and your training knowledge. The output should let a fresh model instance — with no memory of the original text — reason about the topic as if it had read it.

## Input Handling

Accept input as:
1. **Inline text** — user pastes directly after the command
2. **File path** — read the file
3. **URL** — fetch and extract (use WebFetch or firecrawl_scrape)

If no input provided, ask: "Paste the text, or give me a file path / URL."

## Calibrating Your Knowledge Boundary

Before extracting, establish what you actually know vs. don't:

**Training cutoffs (as of 2026-03):**
- Claude Opus/Sonnet 4.6: ~May 2025
- GPT-5.4: ~April 2025
- Gemini 3.1 Pro: ~March 2025

**Reliability by source date:**
- **Pre-2024:** Almost certainly in training. Self-test is unreliable here — you'll both miss things you "know" and flag things you don't. Low value unless the source is niche/private.
- **2024-cutoff:** Partially in training. Medium reliability. Flag with `[UNCERTAIN -- may be in training]` when unsure.
- **Post-cutoff:** Genuinely novel. High delta density expected. Most valuable use case.
- **Private/unpublished content:** Always novel regardless of date. Highest reliability.

**The fundamental honesty problem:** You cannot reliably introspect on your own knowledge boundaries (SimpleQA: ~72% accuracy across frontier models -- 28% of "confident" factual answers are wrong). This skill works best when the content is *obviously* outside your training (post-cutoff, private, niche domain). For borderline cases, state uncertainty rather than guessing.

**Optional verification:** If `verify_claim` is available, spot-check 2-3 extracted "novel" claims. If Exa/Brave finds them in multiple pre-cutoff sources, they're probably not novel -- you just failed to recall them. Reclassify as `[IN TRAINING -- failed to recall]`.

## The Process

### Step 1: Read and Internalize

Read the full text. Note the publication date if available — this calibrates your confidence in the self-test.

### Step 2: Self-Test

For each candidate statement, apply this filter:

> "Could I produce this claim as an answer to a direct question, WITHOUT having seen this text, purely from pre-training?"

- **Yes -> exclude.** This is already in your weights.
- **Uncertain -> include with caveat.** Tag `[UNCERTAIN]` — may be in training but you can't confirm.
- **No -> include.** This is the delta.

Edge cases:
- **Known concept, novel application:** Include. "Transformers can do X" might be novel even if you know transformers.
- **Known fact, novel framing:** Include only if the framing itself is the insight.
- **Quantitative claims with specific numbers:** Include — models confabulate exact figures even for "known" topics. Specific numbers are almost always delta.
- **Named entities you haven't seen:** Include with `[NEW ENTITY]` tag.
- **Benchmark results, version numbers, release dates:** Almost always delta — these change frequently and models hallucinate stale values.

### Step 3: Extract as Atomic Statements

Output self-contained, declarative statements. Each must:
- Be **standalone** — understandable without the source text
- Be **falsifiable** — testable, not vague
- Preserve **specificity** — keep names, numbers, dates, mechanisms
- Avoid demonstrative pronouns that reference something outside the statement

Bad: "The authors found this approach works better."
Good: "LoRA fine-tuning with rank 4 matches full fine-tuning on MMLU within 0.3% for Llama-3 70B (Hu et al., 2024)."

### Step 4: Organize by Information Type

Group the extracted statements:

```markdown
## Knowledge Diff: [source title or description]
**Source date:** [date if known, else "unknown"]  |  **Model cutoff:** [your cutoff]  |  **Confidence:** [high if post-cutoff/private, medium if near-cutoff, low if pre-cutoff]

### Novel Claims (things you likely can't produce from training)
- [statement]

### Novel Quantitative (specific numbers, dates, benchmarks)
- [statement]

### Novel Entities or Terminology
- [statement] `[NEW ENTITY]`

### Novel Relationships (known concepts, new connections)
- [statement]

### Corrections (contradicts what you'd predict from training)
- [statement] — **Contradicts:** [what you'd have said instead]
```

### Step 5: Completeness Check

If the source text had N major sections or arguments, verify each produced at least one delta statement. If a section produced zero delta, note: "Section [X]: no novel information detected — aligns with training knowledge."

### Step 6: Compression Signal

End with:

```
---
Source: [title/URL/filename]
Delta density: [low/medium/high] — [X] novel claims from ~[Y] word source
Dominant novelty type: [claims/quantitative/entities/relationships/corrections]
```

If delta density is genuinely zero (the text contains nothing beyond your training), respond with `...` and a one-line explanation of why.

## Guardrails

- **No summarizing.** This is not a summary. A summary captures the text's main points. A diff captures only what's NEW relative to your knowledge.
- **No hedging inflation.** Don't include things "just in case" you might not know them. If you're >90% confident you'd produce it from training, exclude it. But DO include with `[UNCERTAIN]` when genuinely unsure — false negatives (missing real delta) are worse than false positives.
- **No editorial commentary.** Don't evaluate whether the novel claims are correct — just extract them. The user decides what to do with the delta.
- **Preserve the author's precision.** If the source says "37.2%", don't round to "about 37%". The specificity IS the delta.
- **State the date.** Always note the source's publication date (if known) and your training cutoff in the output header.

---

# Mode: dispatch

Research -> Dispatch -> Verify -> Plan -> Execute. Opus orchestrates the full loop: dispatches parallel audits to GPT-5.4 via Codex CLI, verifies findings against actual code, synthesizes an execution plan, then implements it.

## When to use

"dispatch research", "run audits", "codex sweep", "audit and fix", or when the user wants autonomous project improvement — from discovery through implementation.

**Depth modes:**
- `"quick sweep"` -> 3-5 lightweight audits, stop at findings (no execute)
- `"audit"` / default -> full 5-phase loop
- `"deep audit"` -> 15+ thorough audits, comprehensive plan

**Stop points:** "just audit" (stop after Phase 3), "plan only" (stop after Phase 4), "full auto" (all 5 phases).

## Pipeline

```
Phase 1: RECON     Read project state, identify gaps              (~15%)
Phase 2: DISPATCH  Craft prompts, fire 3-5 parallel Codex audits  (~25%)
Phase 3: VERIFY    Check findings against actual code              (~20%)
Phase 4: PLAN      Synthesize verified findings into exec plan     (~15%)
Phase 5: EXECUTE   Implement the plan (with user approval)         (~25%)
```

## GPT-5.4 via Codex — what to know

**CAN do:** Read files, shell commands, cross-reference, count/compare, structured output. Has 9 MCPs (scite, exa, brave, perplexity, research, meta-knowledge, paper-search, context7, codex_apps).

**CANNOT do:** DB queries, `uv`/project CLIs (sandbox lacks env), conversation history. **28% factual error rate on external knowledge.** Hallucinates fix status ("already fixed" when it wasn't). `--search` only works in interactive mode.

**Auth:** ChatGPT account auth. Only `gpt-5.4` (default) and `gpt-5.3-codex` work. `o3`/`gpt-4.1` rejected.

**Token overhead:** ~37K baseline per `codex exec` call (9 MCP servers, no disable flag). Cost-effective for substantial tasks only.

## Critical gotchas

**Turn limits (~15-20 tool calls):** Max 5 files per agent. Split larger audits. Include synthesis deadline in EVERY prompt: "After reading at most 5 files, STOP and synthesize. 70% reading, 30% writing. Partial report > no report." (6th+ recurrence, 2026-03-28). Codex doesn't see CLAUDE.md — the instruction must be in the prompt.

**Template-first anti-pattern:** Agents that create skeleton markdown first waste a write turn, then exhaust turns filling it in. Failed 3/4 sessions. Use `-o FILE` instead — captures final text message automatically.

**Memory pressure gate:** Before dispatching, count active processes (`pgrep -lf claude | wc -l`, NOT `pgrep -c` on macOS). If >= 4, reduce to sequential or audit directly.

**MCP contention:** Max 4 parallel Codex agents. Each starts 9 MCP servers. 5+ agents = 132+ simultaneous startups = system overwhelm.

**Output preservation:** Tell agents to write to `docs/audit/`, NOT `/tmp`. Immediately `git add` or `cp` after completion — sandbox cleanup can delete files. Do NOT use `--ephemeral` (deletes `-o` output).

**Verification is mandatory (Phase 3).** ~28% error rate concentrated in counts, severity, external knowledge. Code-grounded findings (file:line) are consistently reliable. See `references/verification-procedure.md` for checklist and hallucination patterns.

**S2 API outages:** Tell agents to fall back to `backend="openalex"` or exa if Semantic Scholar returns 403.

## Model selection

| Target | When | Tradeoff |
|--------|------|----------|
| `codex exec --model gpt-5.4` | Cross-referencing, counting, structured output | Free, parallel, output extraction fragile |
| Claude Code `Agent` subagents | Same + DuckDB/MCP access | Costs tokens, output inline (reliable) |
| `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile deep_review ...` | 1M context, huge file ingestion | Best for monolithic analysis |

**Use Codex for:** 5+ parallel audits, cross-file grep+read tracing, wiring/drift/completeness checks.
**Use Claude subagents for:** <3 file audits, tasks needing project-specific tooling (uv, DuckDB, MCP).

## Phase-by-phase execution

**Phase 1 -- Recon:** Read CLAUDE.md, `.claude/overviews/`, plans, `git log --oneline -30`, `docs/audit/` (skip completed). Build mental model, identify audit targets.

**Phase 2 -- Dispatch:** Craft self-contained prompts per `references/prompt-construction.md`. Execute per `references/codex-dispatch-mechanics.md`. Each prompt: "Read [files], check [properties], cross-reference [A vs B], cite file:line."

**Phase 3 -- Verify:** Every finding checked against actual code. Follow `references/verification-procedure.md`. Output: confirmed / rejected (with reason) / corrected findings.

**Phase 4 -- Plan:** Synthesize into phased execution plan per `references/plan-and-execute.md`. Fix ALL verified findings -- don't self-select "top N." Present to user; wait for approval.

**Phase 5 -- Execute:** Implement per `references/plan-and-execute.md`. Read before editing. One commit per logical change. If other agents active, commit after each fix (not batched) or use `isolation: worktree`.

## References (loaded on demand)

| File | Contents |
|------|----------|
| `references/prompt-construction.md` | Target selection categories, prompt structure, good/bad patterns |
| `references/codex-dispatch-mechanics.md` | Bash commands, flags, MCP config, `-o` caveats, fallback |
| `references/verification-procedure.md` | Verification checklist, hallucination pattern table, output format |
| `references/plan-and-execute.md` | Plan template, plan principles, execution principles, MAINTAIN.md integration |
| `references/paper-reading-dispatch.md` | DOI handling, S2 fallbacks, turn budget, GPT-5.4 strengths/weaknesses for papers |
| `references/agent-system-prompt.md` | Full system prompt for subagent dispatch |

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Commit contamination — when dispatch-research agents don't use worktree isolation, their uncommitted changes get swept into the parent session's next commit.**

---

$ARGUMENTS

<!-- knowledge-index
generated: 2026-04-08T21:42:46Z
hash: fce0e32de4a2

cross_refs: docs/compiled/{concept-slug}.md, docs/research/*.md, research/*.md, research/adversarial-case-library.md, research/compiled/{concept-slug}.md
sources: 1
  DATA: BASE: name
table_claims: 8

end-knowledge-index -->
