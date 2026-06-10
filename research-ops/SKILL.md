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

Two lanes split by the **verifier boundary** (constitution: verifier-conditioned autonomy):

- **Generate (Dreamer)** — unattended idea-generation. Discover, gap-analyze, brainstorm, cross-model critique → write *buildable proposals* to `queue/` and *human-gated questions* to `decisions-pending/`. **Never executes.** Safe to run while you sleep because it only produces reversible drafts for a yes/no. This is the "wake up to N ideas, say yes/no" endgame.
- **Execute (attended)** — plan, review, execute, verify the greenlit queue items. The partial verifier (you + cross-model + `verify_claim`) sits here, so this lane is **attended** — run it via `/loop` in an open session, or by hand.

> **Live reference: hutter `OUTER-LOOP.md`.** hutter runs the *same* two-role shape (Grinder/Dreamer + git bus) and it's the proven, live instance (ledger updated daily). The one difference is the verifier: hutter has a **clean** bit-exact gate (regime 1), so its Grinder auto-ratchets unsupervised. Research domains are **partial-verifier** (regime 2) — synthesis/gap/discovery have no ground truth — so here the unattended lane *generates only*; execution stays attended. Do **not** port hutter's auto-ratchet, parking-lot, or pre-registered-ΔS machinery: those need a clean metric, and faking one is the vetoed `session_quality` trap.

## Scheduling primitives (verified 2026-06-08, OUTER-LOOP.md)

| Primitive | Survives reboot? | Unattended? | Quota | Use for |
|---|---|---|---|---|
| `/loop [int] <cmd>` | No (restores on `--resume` ≤7 d) | No — needs session open | local, ~free | the **attended Execute lane** |
| `/schedule` (Routine) | **Yes — cloud** | **Yes** | counts vs ~15 routines/24 h | the **unattended Generate lane** (Dreamer), model = Opus 4.8 |
| launchd plist | Yes (local only) | only while Mac awake | zero | local state-gathering, not LLM work |

`/loop` is for babysitting an open session; `/schedule` is the only primitive that runs the Dreamer while you sleep. The old "run all six phases unsupervised on `/loop 15m`" design is **retired** — it needed a babysat session *and* auto-executed unverified work (worst of both), which is why every project's CYCLE.md went stale.

## Live State

!`bash ${CLAUDE_SKILL_DIR}/scripts/gather-cycle-state.sh "$(pwd)" 2>&1 | head -80`

## Which lane runs this fire

One invocation of `/research-ops cycle` picks ONE lane from the Bus State above (first match wins):

1. **Greenlit items in `queue/` AND you are attended** (interactive session / `/loop`, not an unattended Routine) → **Lane B (Execute)**. Drain the queue.
2. **Otherwise** → **Lane A (Generate)**. Refill `queue/` + triage `decisions-pending/`.

A `/schedule` Routine ALWAYS runs Lane A — it is unattended, so it must never execute (no clean verifier). Lane B only ever runs when a human is at the desk. If "NO STATE CHANGE" → one-line noop, stop.

---

## Lane A — Generate (Dreamer)

The unattended generator. Runs as a `/schedule` Routine (full) or `/loop /research-ops cycle` in an open Opus session (minimal). Each fire:

1. `git pull`. Read `queue/` depth, `decisions-pending/`, the Live State improvement signals, and recent git log.
2. **Decide if there is work.** Queue healthy (≥8 unused proposals) AND no fresh improvement signals → write one `noop` line to `CYCLE.md` log, `git push` if changed, **stop**. Do not manufacture work.
3. **Discover + gap-analyze.** Search for new developments (lead with Exa for tools/releases, `search_preprints` for papers; `/research dispatch` for deep sweeps). Compare against git log + research memos — skip anything already known. Read improvement signals from Live State; prioritize `STEER` signals. If discover returns empty, run `/brainstorm` on the project domain. SWE quality gaps belong to `/maintain` — don't duplicate.
4. **Write proposals to `queue/`.** Append ≤8 concrete, buildable, ONE-change proposals — each with: the change, files it touches, rationale tied to evidence, and how to verify it. These are *candidates*, not approvals.
5. **Human-gated items → `decisions-pending/`.** Anything in the "never autonomous" set (classification thresholds with clinical implications, validated clinical logic, new verification tooling, GOALS.md direction) goes here as a written question — never into `queue/`. For these, run `/critique model` cross-lab (Gemini 3.5 Flash + Opus, a *different* lab than the generator) and write recommendation + dissent + the open question. Do NOT greenlight.
6. `git commit + push` (`queue/`, `decisions-pending/`, `CYCLE.md` log). Keep output small. Never ask whether to continue.

**WIP caps:** ≤8 unused queue proposals (skip discover above that); ≤3 undispositioned discoveries. **Turn budget:** stop searching at 70% of turns and synthesize. **Recitation:** recite key evidence before drawing conclusions.

### The Dreamer Routine prompt (paste into `/schedule`, model Opus 4.8, ~daily)

Parameterize `{PROJECT}` / `{ROOT}`; hutter's filled-in version is the worked example in `hutter/OUTER-LOOP.md`.

```
<role>You are the Dreamer for {PROJECT}. You GENERATE buildable research/improvement
proposals; you never execute them. Read-only on the project; write-only to queue/ and
decisions-pending/. Discovery/synthesis here has no clean verifier, so you produce
reversible drafts for a human yes/no — you never ship.</role>

<on_each_fire>
1. cd {ROOT}; git pull. Read queue/ depth, decisions-pending/, recent git log (-15),
   and improvement signals (run scripts/gather-cycle-state.sh {ROOT}).
2. If queue ≥8 unused AND no fresh STEER/quality signal AND decisions-pending/ empty:
   write one noop line to CYCLE.md, git push if changed, STOP. Don't manufacture work.
3. Discover + gap-analyze: Exa/search_preprints for new developments; /research dispatch
   for deep sweeps; /brainstorm if discover is empty. Skip anything in git log / research
   memos. Prioritize STEER signals. SWE quality → /maintain's lane, skip.
4. Append ≤8 buildable ONE-change proposals to queue/QUEUE_NNN.md — each: change, files,
   evidence-tied rationale, verification method. Candidates, not approvals.
5. "Never autonomous" items (clinical thresholds, validated logic, new verifier tooling,
   GOALS direction) → decisions-pending/ as a written question. Run /critique model
   cross-lab (Gemini 3.5 Flash + Opus) and write recommendation + dissent + open question.
   Do NOT greenlight.
6. git commit + push (queue/, decisions-pending/, CYCLE.md). Keep output small.
   You are bounded and unattended — do the work and STOP. Never ask whether to continue.
</on_each_fire>
```

Cap fires ≤6/day (well under the ~15 routines/24 h ceiling).

---

## Lane B — Execute (attended)

Run when you're at the desk (`/loop /research-ops cycle` in an open session, or by hand). This lane drains the queue the human greenlit. **Verify before execute** — never start a new execution with an unverified prior change.

### Phase priority (first match wins)

1. **Recent execution without verification** → verify.
2. **Greenlit items in `queue/`** → execute. The human greenlights by leaving a proposal in `queue/` (remove to block, reorder to prioritize).
3. **A queue proposal needs a plan/review before it's safe** → plan + review.

### Plan + Review

**Plan:** Read the top greenlit proposal. Check `artifacts/failed-experiments/` for prior attempts on the same subsystem — if found, include "Previously tried: {summary}. Failed: {reason}" so you don't repeat it. Write files-to-change, what changes, verification method.

**Review** — three steps:
1. **Blind first-pass:** read the plan WITHOUT re-reading the proposal's framing; form an independent assessment, THEN compare and note divergence (breaks confirmation bias — SycEval 58% fold rate without structural mitigation).
2. **Probe external claims inline:** HTTP-probe any URL / API / version the plan cites before trusting it.
3. **Cross-model review** (skip for trivial docstring/config tweaks):
```bash
uv run python3 ~/Projects/skills/critique/scripts/model-review.py \
  --context /tmp/cycle-plan.md --topic "research-cycle-{N}" \
  --axes standard --project "$(pwd)" \
  "Review for wrong assumptions, missing steps, anything that breaks existing functionality"
```
Route `--axes` by stakes (standard / deep / full). On failure, classify before retrying (auth→retry, rate-limit→other model, timeout→shrink context); never blind-retry the same model.

### Execute + Verify

**Execute:** Note HEAD SHA. Implement. Commit. Reflect 1-3 lines (what was easier/harder, did assumptions hold). Mark the queue proposal consumed.

**Verify** — two tracks:
- **Track A — infra** (code/config/hooks/scripts): run tests, check file existence, compare to known-good.
- **Track B — research output** (`research/*.md` produced/modified): extract 3-5 falsifiable claims (numbers, dates, named entities, causal assertions), call `verify_claim` on each, record verdicts. **FAIL** = any claim contradicted >0.7 confidence → revert flow. **WARN** = insufficient → `decisions-pending/`, don't block.

**If verification fails:** archive before reverting (`git format-patch HEAD~1 -o artifacts/failed-experiments/` + JSON sidecar per `~/Projects/agent-infra/schemas/gap-fingerprint.json`), then `git revert HEAD` (not reset), mark the proposal `FAILED: {reason}` (skip 2 cycles), write to `decisions-pending/`.

## The bus = git files

| File/dir | Dreamer (Lane A) | Execute (Lane B) / human |
|---|---|---|
| `queue/QUEUE_NNN.md` | appends buildable proposals | drains greenlit items; human blocks by removing |
| `decisions-pending/*.md` | appends human-gated questions + cross-lab synthesis | human reads, greenlights into `queue/` |
| `CYCLE.md` | one-line fire log + rolling state board | reads; human steers via notes |
| `artifacts/failed-experiments/` | — | archived patches + fingerprints (prune >90 d) |

Git is the durable, mergeable, auditable substrate (native-patterns). Separate `queue/` files avoid the merge conflicts a shared `CYCLE.md` queue caused. If Dreamer (cloud Routine) and Execute (local) are on different hosts, the Routine `git pull`s at fire start and `git push`es at end.

`/maintain` owns the separate SWE quality lane (`MAINTAIN.md`) — this skill doesn't touch it.

## Rate-limit fallback

Before a Lane-A fire, `CLAUDE_PROCS=$(pgrep claude | wc -l)`. If ≥6, route discover/gap-analyze through the shared dispatch helper instead of Claude subagents:
```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py --profile cheap_tick \
  --context /tmp/cycle-phase.md --prompt "[instruction]" --output /tmp/cycle-out.md \
  --meta /tmp/cycle-meta.json --error-output /tmp/cycle-err.json
```
`model-review.py` already routes through llmx. Tag `[rate-limited]` in the CYCLE.md log.

## Minimal vs full

- **Minimal (start here):** Lane B attended; Lane A run **manually** (`/loop /research-ops cycle` in an open Opus session at the desk). Zero Routine quota.
- **Full:** Lane A as a `/schedule` Routine refilling `queue/` + triaging `decisions-pending/` while you sleep (~daily). Promote minimal → full only once the queue demonstrably empties for lack of fresh ideas — not before (demand-gated, per OUTER-LOOP.md).

## Operating rules

1. **Never ask for input** in either lane. Lane A writes questions to `decisions-pending/`; Lane B surfaces them to the human at the desk.
2. **Lane A generates, never executes.** Lane B executes only greenlit items, only attended, verify-before-execute.
3. **Report in 1-3 lines:** phase, outcome, what's next.
4. **Idempotent:** check git log + queue before acting; don't redo completed work.

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
