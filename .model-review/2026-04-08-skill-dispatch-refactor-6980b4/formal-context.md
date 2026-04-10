# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler/hacky approaches because they're 'faster to implement'
- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort
- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters

# Context: Skill Refactor Review

## What changed
We refactored 3 skills (review, observe, improve) to:
1. Replace llmx CLI subprocess dispatch with llmx Python API (`from llmx.api import chat`)
2. Add structured JSON extraction with FINDING_SCHEMA for cross-model finding merge
3. Keep free-form markdown prompts for reviews (don't constrain nuance)
4. Remove Kimi K2.5 — only Claude, GPT, Gemini models tracked
5. Restore Gemini dispatch (it's important for cost/cross-model perspective)

## Failure history that motivated the changes (from improvement-log.md)
- Multi-file `-f` flag drops context: 4 occurrences (llmx CLI bug, not Gemini)
- `-o` flag produces 0-byte output: 5+ occurrences (llmx output layer)
- Gemini CLI rate limits cause retry loops: 4+ occurrences
- Large context Gemini hallucination (898KB input): 3 occurrences
- Model-review parallel dispatch hangs: recurring
- Poll loops on background llmx tasks: recurring

## Intent
- Cross-model review (Gemini + GPT) is essential — different failure modes provide real adversarial pressure
- The Python API (`llmx.api.chat()`) bypasses all CLI transport issues
- Structured extraction + programmatic merge replaces the old 2-round LLM extraction
- The user wants the agent to decide model routing based on model-guide, not hardcoded

## Scope
- Personal infrastructure, one operator
- ~6 projects (meta, selve, genomics, intel, skills, research-mcp)
- Agent-built, human-steered
---
name: review
description: "Cross-model validation — adversarial review, fact-checking, post-implementation close. Dispatches to Gemini 3.1 Pro + GPT-5.4 for independent critique."
user-invocable: true
argument-hint: <mode> [target]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Cross-Model Review Workflow

Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

## Modes

| Mode | Trigger | What it does |
|------|---------|-------------|
| `model` | Default, or explicit `/review model [topic]` | Adversarial cross-model review via Gemini + GPT |
| `verify` | `/review verify <report>` | Fact-check LLM findings against actual code |
| `close` | `/review close` | Post-implementation: tests, review, caught-red-handed loop |

**Auto-routing (when no mode specified):**
- Recent plan in `.claude/plans/` with commits since plan start → `close`
- Recent findings/audit output in context → `verify`
- Otherwise → `model`

---

## Mode: model — Cross-Model Adversarial Review

**Purpose:** Convergent/critical only — find what's wrong. For divergent ideation, use `/brainstorm`.

See `lenses/adversarial-review.md` for full dispatch methodology, axis descriptions, depth presets, per-model prompts, and known issues.

### 1. Assemble Context

Write review material to a single context file.

**Pre-flight — scope declaration (mandatory):** Include a `## Scope` block near the top:
- **Target users:** personal / team / multi-tenant / public
- **Scale:** current entity counts AND designed-for scale (e.g., "currently 40 compounds, designed for thousands of subjects")
- **Rate of change:** how often does new data arrive?

This prevents the #1 review failure mode: models optimizing for the wrong scale. Evidence: selve UMLS review (2026-04-06) — GPT scored a plan 27/100 as "over-engineered for 105 personal entities" when the actual scope was multi-user scalable.

**Constitutional anchoring:** Check for constitution (`## Constitution` in CLAUDE.md) and GOALS.md. Include as preamble if found.

See `references/context-assembly.md` for detailed context gathering (narrow, broad, auto-assembled).

#### Context Anti-Patterns

Common review biases — check your context for these before analysis:

| Anti-pattern | How it biases | Fix |
|-------------|--------------|-----|
| **Scale ambiguity** — large number without clarifying which ops touch it | Models optimize for the large number even when the change affects a small boundary | Include concrete volumes at the decision boundary |
| **Priming alternatives** — listing tools/packages in the prompt | Models evaluate named alternatives favorably instead of finding flaws | For convergent: "find what's wrong" only. For alternatives: use `/brainstorm` or the `alternatives` axis |
| **Framing incumbents as limited** — describing existing tools by narrow current use | Models treat incumbent as constrained | Frame by capability: "Pydantic v2 is established (13 models, 100% typed). Question: extend to output schemas?" |
| **Missing boundary volumes** — not stating how many objects schemas will process | Models default to optimizing for largest number in context | Always include: "Largest output: N entries." |
| **"Rethink entirely" in convergent** — asking for alternatives alongside finding problems | Models dodge critique by proposing alternatives | Keep convergent and divergent separate |
| **Presupposing new infra should exist** — reviewing NEW system without incident history | Models critique within frame instead of questioning it | Include incident history. Prompt: "cite the specific past incident each component prevents. If none, say SPECULATIVE." |
| **Ambiguous domain terminology** — terms that mean different things in different contexts | Models share the same misread | Define terms precisely. Disambiguate similar-named systems on first use. |
| **Missing project identity** in cross-project reviews | Models apply principles too literally to unfamiliar projects | Include 2-3 line identity per project |
| **Missing scope declaration** — not stating target users and designed-for scale | Models assume personal/small when reviewing shared infra, or assume production when reviewing prototypes | Always include scope block (see above) |

### 2. Dispatch

**Always use the script.** It handles: context assembly, constitutional preamble injection, parallel dispatch to Gemini + GPT via the llmx Python API, extraction, and disposition generation.

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "$ARGUMENTS"
```

Set `timeout: 660000` on the Bash tool call. Add `--extract` to all standard/deep reviews.

See `references/dispatch.md` for `--questions`, `--context-files`, depth presets, and troubleshooting.

#### Depth Presets

| Preset | Axes | When |
|--------|------|------|
| `standard` (default) | arch (Gemini) + formal (GPT-5.4) | Most reviews |
| `--axes simple` | combined Gemini Pro | Config tweaks, refreshes |
| `--axes deep` | arch + formal + domain + mechanical | Structural changes, domain-dense |
| `--axes full` | all 5 | Shared infra, clinical, high-stakes |

**Genomics classification review** (monthly or after >10 commits to LR-engine/scoring): Use `--axes formal,domain`. GPT-5.4 found 11 conceptual/mathematical bugs for $6.54 — the only detector for incoherent Bayes.

### 3. Fact-Check (Mandatory)

**Both models hallucinate. Never adopt without verification.**

1. **Code claims** — Read the actual file. Models frequently cite wrong line numbers, invent function names.
2. **Research claims** — Check if the cited finding actually says what the model claims.
3. **"Missing feature" claims** — Grep the codebase. The feature may already exist.

Use a **different model family** than the claim's author. Cross-family verification: +31pp accuracy vs same-family (FINCH-ZK, Amazon 2025). For code claims, always verify by reading the actual file first.

### 4. Extract & Disposition

**If `--extract` was used:** Read `disposition.md` and skip to Step 5. The script does cross-family extraction automatically (Flash extracts GPT output, GPT-Instant extracts Gemini output).

**If no `--extract`:** See `references/extraction.md` for manual extraction workflow. The core rule: **never go from raw model outputs directly to synthesis.** Extract mechanically first, then disposition every item, then synthesize. Extraction before synthesis: +24% recall, +29% precision (EVE, arXiv:2602.06103).

### 5. Synthesize

Build synthesis from the disposition table. Every INCLUDE item must appear. Reference IDs for auditability.

**Trust ranking:**

| Level | Criterion | Action |
|-------|-----------|--------|
| Very high | Both agree + code-verified | Adopt |
| High | One found + code-verified | Adopt |
| Medium | Both agree, unverified | Verify first |
| Low | Single model, unverified | Flag for investigation |
| Reject | Self-recommendation or contradicts verified code | Discard |

**Output header:**
```
## Cross-Model Review: [topic]
Models: [actual], Date: YYYY-MM-DD, Constitutional anchoring: Yes/No
Extraction: N items, M included, D deferred, R rejected
```

Sections: Verified Findings | Deferred | Rejected | Where I Was Wrong | Gemini Errors | GPT Errors | Revised Priority List

#### Auto-Verify File-Specific Findings

If synthesis has INCLUDE items with file:line citations, run `verify` mode on the synthesis before Step 6. Only implement CONFIRMED or CORRECTED findings. Drop HALLUCINATED. Skip if all findings are architectural or fewer than 3 code citations.

#### Over-Adoption Check

The disposition file includes an **Agent Response** template at the bottom (added by `--extract`). Fill it in before implementing any findings — the two questions are:

1. **Where do you disagree with the disposition?** "Nowhere" is valid. Don't invent disagreements.
2. **Context you had that the models didn't?** If the context file was comprehensive, say so.

Write your answers directly in `disposition.md`. Valid outcomes: "No changes" (proceed) or "Revising N items" (state which, why, update synthesis).

**Why this exists:** Models produce rigorous-looking analysis that can override your judgment through sheer detail. The template is in the artifact so it's visible every time you read the disposition — architecture over instructions.

### 6. Close the Loop (Mandatory if INCLUDE items exist)

**The synthesis is not the deliverable — the updated artifact is.**

- **Case A (existing plan/doc):** Apply verified INCLUDEs directly. Tag changes with finding IDs. Don't ask permission.
- **Case B (decision/code, no plan):** Offer plan-mode handoff if context is depleted.
- **Case C (all DEFER/REJECT):** Synthesis is the deliverable.

### Artifact Handoff

Write summary JSON to `~/.claude/artifacts/$(basename $PWD)/model-review-$(date +%Y-%m-%d).json` with: skill, project, date, topic, include/defer/reject counts, key_findings[]. Used by project-upgrade as a cache gate.

---

## Mode: verify — Fact-Check LLM Findings

Standalone verification of LLM-generated audit findings. Use after `model` mode, `/dispatch-research`, `/project-upgrade`, or any automated audit that produces file-specific claims.

See `lenses/verification.md` for the full procedure.

### When to Use

- After `model` mode produces codebase critique
- After `/dispatch-research` generates audit findings
- After `/project-upgrade` suggests changes
- After receiving external audit output (Codex, Gemini, GPT)
- When someone pastes a list of "bugs found" from any LLM
- Before implementing ANY fix list from an LLM source

### When NOT to Use

- For verifying scientific/factual claims (use `/researcher` or `/epistemics`)
- For verifying a single specific bug (just read the code directly)
- When findings are already human-verified

### Procedure

1. **Extract Claims** — Parse the report. Extract every file-specific, verifiable claim. Number each for tracking.
2. **Ground Truth Verification** — For each claim, verify against actual code using the checklist in `lenses/verification.md`.
3. **Synthesis Table** — Produce verification summary with CONFIRMED / CORRECTED / HALLUCINATED / INCONCLUSIVE verdicts.
4. **Action** — Fix ALL CONFIRMED and CORRECTED findings. Never fix HALLUCINATED. Never self-select "top N" from confirmed. If hallucination rate exceeds 40%, warn user the source is unreliable.

### Output Convention

If total findings > 10, write the synthesis table to a file and return the path. Don't dump 30-row tables inline.

---

## Mode: close — Post-Implementation Plan Close

After a plan's implementation is committed, there's a gap between "code works" and "code is correct." Regression tests verify existing behavior doesn't change — but they're blind to bugs in new code paths. This mode closes that gap.

See `lenses/plan-close-review.md` for full workflow, bug class table, and migration checklist.

### Why This Exists

Three independent lines of evidence:

1. **Empirical (suspense accounts, 2026-04-07):** GPT-5.4 found 6 confirmed bugs in freshly committed code. All 74 canary tests and 11 IR invariants passed. The bugs were in new functions with zero test coverage.

2. **Failure Mode 15 — Silent Semantic Failures** (MAS-FIRE, arXiv:2602.19843): Reasoning drift, wrong buckets, misleading diagnostics propagate without runtime exceptions.

3. **Failure Mode 16 — Reward Hacking** (TRACE, arXiv:2601.20103): Agents evaluated by test passage may hack the test rather than solve the task.

### Workflow

**Phase 0: Pre-Close Discipline** — Normalize closeout: separate code/data validation, sync generated docs, prove migration completion. Build review packet:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

**Phase 1: Write Tests for New Code** — Identify new functions from plan commits. Write unit tests covering happy path, edge cases, error paths, and contract invariants.

**Phase 2: Cross-Model Review** — Run `/review model` on the plan-close review packet (not a hand-written summary). Use `--context .model-review/plan-close-context.md`. Fact-check and disposition every finding.

**Phase 3: The Caught-Red-Handed Loop** — For each confirmed finding: would any Phase 1 tests have caught this? If yes, fix the test gap. If no, write a new test. Verify against pre-fix code:
```bash
git stash
pytest tests/test_<new>.py -x  # should FAIL
git stash pop
pytest tests/test_<new>.py -x  # should PASS
```

**Phase 4: Close the Plan** — Commit tests, update plan status, run `validate-code`, summarize findings.

### When NOT to Use

- Trivial plans (< 30 lines, single function, obvious correctness)
- Research/analysis plans that don't produce code
- Plans that only modify config/data with no logic changes

---

## References

- `references/context-assembly.md` — detailed context gathering patterns
- `references/dispatch.md` — full dispatch mechanics, manual dispatch, timeouts, model flags
- `references/extraction.md` — manual extraction workflow
- `references/prompts.md` — full prompt templates per model
- `references/biases-and-antipatterns.md` — known model biases, per-model failure modes, common mistakes

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] llmx output flag — never use shell redirects (> file) with llmx; use --output/-o flag instead. Shell redirects buffer until process exit, producing 0-byte files. Fixed in llmx v0.5.0 (2026-03-06).**

$ARGUMENTS
---
name: observe
description: "Diagnostic production -- behavioral anti-patterns, architectural patterns, supervision waste, retrospectives. Dispatches to Gemini 3.1 Pro for analysis. The recursive self-improvement engine."
user-invocable: true
argument-hint: <mode> [project] [options...]
context: fork
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: medium
---

# Observe

Unified diagnostic workflow. Four lenses on the same transcript data, each answering a different question.

## Current Environment
`!echo "Date: $(date +%Y-%m-%d) | CWD: $(basename $PWD) | Transcripts: $(ls ~/.claude/projects/ | wc -l | tr -d ' ') project dirs"`

## Mode Routing

| Mode | Question answered | Gemini dispatch? | Output destination |
|------|------------------|------------------|--------------------|
| `sessions` | What behavioral anti-patterns appeared? | Yes | improvement-log.md |
| `architecture` | What design wants to emerge? | Yes | artifacts/observe/ |
| `supervision` | Where was human time wasted? | Yes | improvement-log.md |
| `retro` | What went wrong this session? | No (local) | artifacts/session-retro/ |

Parse `$ARGUMENTS` for mode. First positional arg is the mode. Remaining args are project, options.

**Default mode logic:**
- If the session is ending (user said "retro", "retrospective", or session is wrapping up) -> `retro`
- Otherwise -> `sessions`

**Options common to all modes:**
- `--days N` -- time window (default: 1 for sessions/architecture/supervision, current session for retro)
- `--project PROJECT` -- filter to one project
- `--corrections` -- sessions mode only: extract user correction patterns instead of anti-patterns

## Shared: Transcript Extraction

All modes except `retro` start with transcript extraction. See `references/transcript-extraction.md` for full commands.

```bash
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/observe"
mkdir -p "$ARTIFACT_DIR"

# Claude Code sessions
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py <project> --sessions <N> --full --output "$ARTIFACT_DIR/input.md"

# Codex sessions (if any)
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_codex_transcript.py <project> --sessions <N> --output "$ARTIFACT_DIR/codex.md" 2>/dev/null || true
```

### Operational Context

Build operational context (hook triggers, receipts, git commits) for the session window. See `references/transcript-extraction.md` Step 1.3 for the full script.

### Coverage Digest

Generate existing-coverage digest so Gemini doesn't re-report known patterns:

```bash
bash ~/Projects/meta/scripts/coverage-digest.sh > "$ARTIFACT_DIR/coverage-digest.txt"
```

### Shape Pre-Filter (optional)

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/session-shape.py --days {DAYS} {--project PROJECT}
```

Focus deep analysis on flagged sessions. Skip normal-profile sessions unless you have specific concerns.

---

## Mode: sessions

Analyze session transcripts for behavioral anti-patterns that no linter or static analysis can detect. Scoring rubric and 20-item taxonomy in `lenses/behavioral-antipatterns.md`. Grounding examples in `references/grounding-examples.md`.

Parse the project argument from $ARGUMENTS. Default: last 5 sessions.

### Step 1: Extract & Pre-Filter

Run shared transcript extraction above. Build operational context per `references/transcript-extraction.md` Step 1.3.

### Step 2: Dispatch to Gemini

Send full-fidelity transcript + coverage digest + operational context to Gemini 3.1 Pro. Full prompt in `references/gemini-dispatch-prompt.md`.

Dispatch via llmx Python API (not CLI subprocess):

```python
from llmx.api import chat as llmx_chat

# Concatenate all context into one string
context = Path("$ARTIFACT_DIR/input.md").read_text()
coverage = Path("$ARTIFACT_DIR/coverage-digest.txt").read_text()
ops_ctx = Path("$ARTIFACT_DIR/operational-context.txt").read_text()
prompt = Path("${CLAUDE_SKILL_DIR}/references/gemini-dispatch-prompt.md").read_text()

response = llmx_chat(
    prompt=context + "\n\n" + coverage + "\n\n" + ops_ctx + "\n\n" + prompt,
    provider="google",
    model="gemini-3.1-pro-preview",
    timeout=300,
)
Path("$ARTIFACT_DIR/gemini-output.md").write_text(response.content)
```

Or write this as a short script and run with `uv run python3`. The key: use `llmx.api.chat()`, never shell out to `llmx` CLI.

### Step 3: Stage Findings

Validate Gemini output against transcript, check session UUIDs, save as JSON artifact. Full procedure and JSON template in `references/findings-staging.md`.

**Judgment calls when staging:**
- Gemini flags "unprompted commit" as HIGH -- false positive, global CLAUDE.md authorizes auto-commit
- `done_with_denials` status is NOT a failure -- it's a constitutional approval gate
- "Agent paused before executing" -- rubber-stamp approvals are intentional oversight, not sycophancy
- Promotion criteria: recurs 2+ sessions, not already covered, checkable predicate or architectural change
- Novel high-severity findings can be promoted immediately (don't wait for recurrence)

### Step 4: Summary

Report to user:
- Sessions analyzed: N
- Shape anomalies detected: N
- Findings staged: N (by category)
- Ready for promotion: N (2+ recurrences)
- New failure modes discovered: N
- Proposed fixes: list

### Output Format (appended to improvement-log.md)

```markdown
### [YYYY-MM-DD] [CATEGORY]: [summary]
- **Session:** [project] [session-id-prefix]
- **Evidence:** [what happened, with message excerpts]
- **Failure mode:** [link to agent-failure-modes.md category, or "NEW"]
- **Proposed fix:** [hook | skill | rule | CLAUDE.md change | architectural]
- **Root cause:** [system-design | agent-capability | task-specification | skill-router | skill-weakness | skill-execution | skill-coverage]
- **Status:** [ ] proposed
```

### Corrections Mode (`--corrections`)

Extract user correction patterns instead of behavioral anti-patterns. Full procedure in `references/corrections-mode.md`.

Steps: extract correction signals (zero LLM) -> classify with Haiku -> stage candidates -> check promotion gates (recurs 2+, not covered, checkable) -> integrate with hook telemetry.

---

## Mode: architecture

Creative architectural review -- find better abstractions, missing tools, repeated workflows that should be pipelines, cross-project patterns that should be shared infra. Pattern types in `lenses/architectural-patterns.md`.

**Mindset:** The best proposals are ones nobody asked for. A pattern in 3 sessions is coincidence. A pattern in 8 sessions across 3 projects is an abstraction waiting to be born.

Parse `$ARGUMENTS` for days (default 1), project filter, focus area. `--quick` = phases 1-2 only.

### Phase 1: Gather & Compress

Run shared transcript extraction. Extract from all active projects (meta, intel, selve, genomics, arc-agi) unless `--project` filters. Merge into `$ARTIFACT_DIR/all.md`. Verify <500KB.

Run shape pre-filter. Note anomalous sessions for priority analysis.

### Phase 2: Pattern Extraction (Gemini)

Dispatch to Gemini 3.1 Pro for structured pattern extraction. Full prompt in `references/gemini-prompt.md`. Use `llmx.api.chat()` (Python API), not CLI subprocess.

**Gemini's output is DATA, not conclusions.** It extracts patterns; you do the creative synthesis in Phase 3.

**Operational limits:**
- Pattern extraction degrades past ~80 sessions in one Gemini call. For `--days 7+`, batch by project.
- Gemini hallucination rate on session details: ~20-30%. Verification below is mandatory.
- Cross-project patterns are harder to detect when batched by project — note this gap.

**Verify Gemini claims (mandatory):**
1. Check cited session IDs actually exist
2. Verify quoted user messages appear in the transcript
3. Confirm tool sequences match reality
Drop any finding where evidence doesn't verify. Mark: `VERIFIED` or `DROPPED:reason`.

### Phase 3: Creative Synthesis

Cross-reference existing infrastructure before generating proposals. Load `references/existing-infra-checks.md` for command set.

**Divergent ideation** -- for each verified pattern, generate 3+ genuinely different approaches:
- **Denial cascade:** "What if we COULDN'T use hooks/skills/pipelines?"
- **Cross-domain forcing:** Name an analogous problem in a different domain.
- **Inversion:** Instead of "how do we automate X?", ask "what if we made X unnecessary?"

**Convergent selection** -- apply filters from `lenses/architectural-patterns.md`.

### Phase 4: Structured Output

Load `references/output-template.md` for proposal template. Sort proposals by priority descending.

### Phase 5: Write Output

Write to `$ARTIFACT_DIR/YYYY-MM-DD.md`. Include header from `references/output-template.md`.

**Do NOT:** implement anything, write to improvement-log.md, modify constitution/GOALS.md, propose things in backlog without marking KNOWN.

**DO:** include at least one wild card challenging a current assumption, name the system's trajectory, flag the single highest-leverage abstraction.

### Effort Scaling

| Trigger | Sessions | Phases | Budget |
|---------|----------|--------|--------|
| `--quick` or `/loop` | ~10 (1 day) | 1-2 only | ~$0.10 |
| default | ~15 (1 day) | Full 1-5 | ~$0.50 |
| `--days 7+` | ~50+ (7 days) | Full + cross-model review | ~$2.00 |

**Loop mode:** Load `references/loop-mode.md` for JSONL format, synthesis triggers, implementation tracking.

---

## Mode: supervision

Audit sessions for wasted supervision -- corrections, boilerplate, rubber stamps. Classification in `lenses/supervision-waste.md`.

Every correction, boilerplate instruction, and rubber stamp is a candidate for automation.

### Step 1: Structural Extraction

```bash
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/observe"
mkdir -p "$ARTIFACT_DIR"
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_supervision.py $ARGUMENTS --json --output "$ARTIFACT_DIR/supervision-raw.json"
```

Default: `--days 1`. Pass `--days 7` for weekly, `--project X` to filter.

Read output, report headline numbers:
- Total sessions, total user messages
- Wasted supervision % (CORRECTION + BOILERPLATE + RUBBER_STAMP + RE_ORIENT)
- Top sub-patterns by count

### Step 2: Extract Transcripts for Context

For the top 3-5 sessions with most wasted supervision:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py <project> --sessions 5 --output "$ARTIFACT_DIR/supervision-transcripts.md"
```

### Step 3: LLM Synthesis (Gemini)

Dispatch raw classification + transcripts to Gemini 3.1 Pro via `llmx.api.chat()`:

```python
from llmx.api import chat as llmx_chat

raw = Path("$ARTIFACT_DIR/supervision-raw.json").read_text()
transcripts = Path("$ARTIFACT_DIR/supervision-transcripts.md").read_text()

response = llmx_chat(
    prompt=raw + "\n\n" + transcripts + "\n\n" + SUPERVISION_PROMPT,
    provider="google",
    model="gemini-3.1-pro-preview",
    timeout=300,
)
```

The supervision prompt asks Gemini to classify each non-NEW_AGENCY pattern by:
1. Is it genuinely automatable? (Filter out actual new information)
2. Fix type: HOOK | RULE | DEFAULT | SKILL | ARCHITECTURAL
3. Recurrence count (3+ is signal, 1 is noise)
4. Specific fix implementation

Output format per finding:

```
### [PATTERN_NAME]: [one-line description]
- **Category:** CORRECTION | BOILERPLATE | RUBBER_STAMP | RE_ORIENT
- **Occurrences:** N (across M sessions)
- **Fix type:** HOOK | RULE | DEFAULT | SKILL | ARCHITECTURAL
- **Proposed fix:** [specific implementation]
- **Maintenance:** NONE | LOW | MEDIUM
- **Expected reduction:** what % of this pattern would this fix eliminate?
```

### Step 4: Review and Act

1. Read Gemini output critically -- it may hallucinate session details
2. Cross-check specific claims against raw JSON and transcripts
3. For HIGH/MEDIUM priority findings:
   - Hook fix: implement now (cheap, deterministic, reversible)
   - Rule fix: check not already covered, then add
   - Architectural fix: add to maintenance-checklist.md with evidence
4. Append summary to `~/Projects/meta/improvement-log.md`

### Step 5: Trend Report (weekly)

If `--days 7+`, compare against previous runs:
- Wasted supervision % trending down? (fixes working)
- New patterns appearing? (expected -- old ones get automated)
- RE_ORIENT patterns declining? (checkpoint.md working?)

```markdown
### [YYYY-MM-DD] Supervision Audit
- **Period:** [N days], [M sessions], [K user messages]
- **Wasted:** [X%] (target: <15%)
- **Top patterns:** [list]
- **Fixes deployed:** [list]
- **Status:** [ ] reviewed
```

---

## Mode: retro

End-of-session retrospective. LOCAL analysis only -- no Gemini dispatch. Classification in `lenses/retro-reflection.md`.

The goal is error correction -- turning observations into hooks, rules, or architectural fixes.

### Phase 1: Evidence Collection

Scan THIS session for concrete events:
1. **Failures**: commands that errored, tools that returned wrong results, approaches abandoned
2. **Corrections**: places the user redirected you -- what did they say and what were you doing wrong?
3. **Wasted work**: code written then deleted, searches that found nothing, repeated attempts
4. **Environment friction**: missing dependencies, wrong paths, permission errors, hook blocks, API rate limits
5. **Time sinks**: disproportionate turns relative to value delivered

### Phase 2: Classification

Classify each finding into exactly one category from `lenses/retro-reflection.md`.

### Phase 3: Prior Art Check

Before proposing fixes:
1. Run: `grep -c "^### " ~/Projects/meta/improvement-log.md` to confirm accessible
2. Search for similar findings: `grep -i "KEYWORD" ~/Projects/meta/improvement-log.md | head -5`
3. Match existing entry -> mark "RECURRING: matches entry from YYYY-MM-DD"
4. Check if hook/rule/skill already addresses this -> note it

### Phase 4: Output

Use template from `lenses/retro-reflection.md`.

### Phase 5: Persist Findings

Write findings as JSON to `~/Projects/meta/artifacts/session-retro/`:

```bash
mkdir -p ~/Projects/meta/artifacts/session-retro
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
```

Write `{date}-{SID}-manual.json` with:
```json
{"findings": [{"category": "...", "summary": "...", "severity": "high|medium|low", "evidence": "...", "project": "...", "proposed_fix": "..."}], "source": "manual-retro"}
```

---

## Model Selection for Dispatch

Default: Gemini 3.1 Pro (cheapest 1M context, good at pattern extraction). Use GPT-5.4 at medium effort for formal/quantitative analysis or when Gemini rate-limits. Both via `llmx.api.chat()` — never CLI subprocess. See `/model-guide` for detailed routing.

```python
from llmx.api import chat as llmx_chat
# Gemini (default — pattern extraction, large context)
r = llmx_chat(prompt=..., provider="google", model="gemini-3.1-pro-preview", timeout=300)
# GPT-5.4 medium effort (formal analysis, fact verification)
r = llmx_chat(prompt=..., provider="openai", model="gpt-5.4", reasoning_effort="medium", timeout=300)
```

## Notes

- Transcript source: `~/.claude/projects/-Users-alien-Projects-{project}/` (native Claude Code storage)
- Preprocessor strips thinking blocks and base64 content
- Gemini 3.1 Pro at ~$0.001/query cached -- cheap enough to run frequently
- Codex transcript extraction requires `~/.codex/state_5.sqlite`

$ARGUMENTS
---
name: improve
description: "Synthesis and implementation — harvest findings, suggest skills, maintain infrastructure, orchestrator ticks. The action arm of the diagnostic loop."
user-invocable: true
argument-hint: <mode> [options...]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: medium
---

# Improve

The action arm of the diagnostic loop. Four modes: harvest cross-artifact findings, suggest new skills from usage patterns, maintain infrastructure quality, or run orchestrator ticks.

## Modes

| Mode | Purpose | Loop | Default args |
|------|---------|------|-------------|
| `harvest` | Cross-artifact gathering, dedup, ranked output | no | `--days 3 --focus all` |
| `suggest` | Detect repeated workflows, propose skill/MCP candidates | no | `--sessions 10` |
| `maintain` | Quality checks, finding implementation, routine rotation | `/loop 15m` | (none) |
| `tick` | Single orchestrator tick, queue status | `/loop 5m` | (none) |

**Default (no mode):** Run harvest with defaults, show top 5, implement top confirmed finding.

Parse mode from first positional argument in `$ARGUMENTS`. Remaining args pass through to the mode.

---

## Mode: harvest

Cross-artifact improvement harvester. Reads recent analysis artifacts, user feedback, and git corrections. Deduplicates against improvement-log and vetoed-decisions. Outputs a ranked list of infrastructure/tooling improvements.

**You consume artifacts. You don't produce analysis.** Session-analyst, design-review, retro, and suggest-skill produce the raw findings. You aggregate, deduplicate, rank, and surface what fell through the cracks.

### Phase 0: Parse & Setup

Parse from `$ARGUMENTS`:
- `--days N` (default: 3)
- `--focus` filter: `hooks`, `skills`, `scripts`, `architecture`, `rules`, `all` (default: `all`)

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/harvest"
mkdir -p "$ARTIFACT_DIR"
DATE=$(date +%Y-%m-%d)
OUTFILE="${ARTIFACT_DIR}/${DATE}-${SID}-harvest.md"
CUTOFF=$(date -v-${DAYS}d +%Y-%m-%d)
```

### Phase 1: Load Dedup Baselines

Read in full -- they define what's already known:

1. **`improvement-log.md`** -- Extract all finding summaries and statuses (proposed/implemented/in-progress). Build `TRACKED` list.
2. **`.claude/rules/vetoed-decisions.md`** -- Extract all vetoed proposals. Build `VETOED` list. Do NOT re-propose anything on this list.

### Phase 2: Harvest Structured Artifacts

For each source type, glob within the date window, read each file, extract actionable items.

**2a. Session Retros** (`artifacts/session-retro/`):
- JSON retros: parse `findings[]` array (category, summary, severity, evidence, proposed_fix, project).
- Markdown retros: look for `### [FINDING-` sections.

**2b. Design Reviews** (`artifacts/design-review/`):
- Prioritize synthesis files (`*-synthesis.md`, `*-cross-platform.md`) over raw pattern files.
- Extract findings (sections `### F`) and proposals (`**Proposal:**` / `**Recommendation:**`).
- Skip findings marked "Already exists" or struck-through.

**2c. Session Analyst Findings** (`artifacts/session-analyst/`):
- Parse `findings[]` arrays from `*.json` files.

**2d. Suggest-Skill Outputs** (`artifacts/suggest-skill/`):
- Extract skill candidates with frequency, ROI estimate, proposed name.

### Phase 3: Harvest Unstructured Signals

**3a. User `#f` Feedback** -- highest signal, ground-truth corrections:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/extract_user_tags.py --days ${DAYS} --tag f
```

**3b. Git Corrections:**
```bash
git -C ~/Projects/meta log --since="${CUTOFF}" --format='%h %s' --grep='Evidence:' --
git -C ~/Projects/meta log --since="${CUTOFF}" --oneline -- .claude/rules/ improvement-log.md
git -C ~/Projects/skills log --since="${CUTOFF}" --oneline -- '*/SKILL.md' hooks/
```
Look for patterns -- if 3 commits fix hook edge cases, that signals weak hook testing.

**3c. Daily Memory Logs** (optional):
Check `~/.claude/projects/-Users-alien-Projects-meta/memory/` for `YYYY-MM-DD.md` files within window.

### Phase 4: Deduplicate & Classify

For each harvested item:

1. **Check TRACKED list.** Match against improvement-log: `implemented` -> skip, `proposed` -> mark "reinforced", `in-progress` -> skip.
2. **Check VETOED list.** Match against vetoed-decisions -> skip (unless concrete new evidence changes the calculus).
3. **Classify:** `hook`, `skill`, `script`, `architecture`, `rule`, `config`.
4. **Apply `--focus` filter** if specified.
5. **Count cross-source recurrence.** Two mentions in the same retro = 1 source, not 2. Count distinct source types.

### Phase 5: Rank

```
priority = recurrence_count x severity_weight x novelty_bonus
```
- `severity_weight`: high=3, medium=2, low=1
- `recurrence_count`: distinct sources mentioning this theme (1-6)
- `novelty_bonus`: 1.5 if completely new, 1.0 if reinforcing unimplemented, 0.5 if tangential

Sort descending.

### Phase 6: Output

Write to `$OUTFILE`:

```markdown
# Harvest -- {DATE}

**Window:** {CUTOFF} to {DATE} ({DAYS} days)
**Focus:** {FOCUS}
**Sources scanned:** N retros, N design-reviews, N session-analyst, N suggest-skill, N #f tags, N git corrections
**Items found:** N total -> N after dedup -> N after focus filter

## Summary

| # | Improvement | Type | Sources | Recurrence | Severity | Status |
|---|------------|------|---------|------------|----------|--------|
| 1 | ... | hook | retro, design-review | 3 | high | NEW |

## Details

### 1. [Improvement title]
**Type:** hook | skill | script | architecture | rule | config
**Priority:** {score} (recurrence={N} x severity={S} x novelty={B})
**Status:** NEW | REINFORCED | VETOED-BUT-REVISIT
**Sources:** (list with file paths and quoted findings)
**Proposed action:** {concrete next step}
**Dedup notes:** {what was checked}
```

### Anti-Patterns
- Don't re-analyze sessions -- read existing artifact output.
- Don't propose vetoed items without concrete new evidence.
- Don't inflate recurrence -- count distinct source types.
- Don't skip dedup. If everything is already tracked, say so.
- Don't propose maintenance as "improvement." This finds infrastructure/tooling/architecture changes.

---

## Mode: suggest

Detect repeated multi-tool workflows in recent sessions and propose skill or MCP tool candidates.

### What This Detects

1. **Repeated tool sequences** -- same 3+ step tool chain across 2+ sessions.
2. **Manual orchestration** -- user giving same multi-step instructions repeatedly.
3. **MCP tool gaps** -- agent shells out to bash for what a single MCP tool could do.
4. **Workflow templates** -- recurring session shapes that could be parameterized.

### Step 1: Extract Transcripts

Parse project from `$ARGUMENTS`. Default: current project, last 10 sessions.

```bash
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/suggest-skill"
mkdir -p "$ARTIFACT_DIR"
python3 ~/Projects/skills/session-analyst/scripts/extract_transcript.py <project> --sessions 10 --output "$ARTIFACT_DIR/input.md"
```

Fall back to reading the 10 most recent JSONL files from `~/.claude/projects/-Users-alien-Projects-<project>/` if extractor unavailable.

### Step 2: Extract Tool Sequences

Local analysis to identify candidate patterns -- extract 3/4/5-grams of tool sequences, count frequencies, filter to those appearing 2+ times.

### Step 3: Dispatch to Gemini

Send transcripts + tool sequence analysis to Gemini 3.1 Pro via `llmx.api.chat()`:

```python
from llmx.api import chat as llmx_chat

transcripts = Path("$ARTIFACT_DIR/input.md").read_text()
response = llmx_chat(
    prompt=transcripts + "\n\nAnalyze Claude Code session transcripts for repeated workflows. "
    "Classify as SKILL candidate (multi-step, judgment needed) or MCP TOOL candidate (deterministic, reusable). "
    "For each: pattern, frequency, current cost, trigger, parameters, skeleton. "
    "Only patterns appearing 2+ times across different sessions. Max 7 candidates. "
    "Rank by frequency x complexity saved.",
    provider="google",
    model="gemini-3.1-pro-preview",
    timeout=300,
)
```

### Step 4: Validate and Deduplicate

1. Check existing skills: `ls ~/Projects/skills/`
2. Check existing MCP tools: read `.mcp.json` files
3. Check ideas.md backlog: `grep -i "KEYWORD" ~/Projects/meta/ideas.md`
4. Spot-check Gemini's frequency claims against transcripts

### Step 5: Output

Present candidates ranked by ROI. Save to `$ARTIFACT_DIR/YYYY-MM-DD-{SID}.md`.

### Step 6: Scaffold

If user approves a candidate:
- SKILL: create directory in `~/Projects/skills/` with SKILL.md
- MCP_TOOL: propose addition to the relevant MCP server

### Guardrails
- Don't suggest skills for coincidental one-offs that happened twice.
- Don't suggest MCP tools for things better as bash aliases.
- Frequency matters more than complexity.
- No strong candidates? Say so. Don't fabricate.
- Cross-check 10-use threshold from constitution.

---

## Mode: maintain

Unified quality agent. Run with `/loop 15m`. Each tick: check state hash, pick ONE task by priority, execute, log to JSONL. Owns SWE quality (rotation) and infrastructure health (findings, proposals, orchestrator). Separate from `/research-cycle` (growth lane). **Never ask for input.**

### Live State

!`bash -c '
HASH_FILE=~/.claude/maintain-state-hash.txt
ORCH_HASH=$(sqlite3 ~/.claude/orchestrator.db "SELECT count(*),group_concat(status) FROM tasks WHERE status IN (\"failed\",\"blocked\",\"pending\") ORDER BY id" 2>/dev/null || echo "na")
RECEIPT_HASH=$(tail -3 ~/.claude/session-receipts.jsonl 2>/dev/null | md5 || echo "na")
FINDING_HASH=$(grep -c "Status:\*\* \[ \]" ~/Projects/meta/improvement-log.md 2>/dev/null || echo "0")
MAINTAIN_HASH=$(md5 < "$(pwd)/MAINTAIN.md" 2>/dev/null || echo "na")
PROPOSAL_HASH=$(ls -la ~/.claude/steward-proposals/ 2>/dev/null | md5 || echo "na")
DB_HASH=$(for db in ClinVar gnomAD PharmCAT CPIC; do f=$(find "$(pwd)/databases/" -iname "*${db}*" -type f 2>/dev/null | head -1); [ -n "$f" ] && stat -f%m "$f" 2>/dev/null; done | md5 || echo "na")
GIT_HASH=$(for p in meta intel selve genomics; do cd ~/Projects/$p 2>/dev/null && git log --oneline -1 2>/dev/null; done | md5 || echo "na")
CURRENT_HASH="${ORCH_HASH}|${RECEIPT_HASH}|${FINDING_HASH}|${MAINTAIN_HASH}|${PROPOSAL_HASH}|${DB_HASH}|${GIT_HASH}"
PREV_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
echo "$CURRENT_HASH" > "$HASH_FILE"
if [ "$CURRENT_HASH" = "$PREV_HASH" ]; then
  echo "NO STATE CHANGE since last tick. Logging noop."
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\",\"action\":\"noop\",\"target\":\"state-unchanged\",\"result\":\"ok\",\"detail\":\"hash match\"}" >> "$(pwd)/maintenance-actions.jsonl" 2>/dev/null
  exit 0
fi
echo "=== ORCHESTRATOR ==="; cd ~/Projects/meta && uv run python3 scripts/orchestrator.py status 2>/dev/null || echo "(unavailable)"
echo ""; echo "=== RECENT SESSIONS ==="; tail -8 ~/.claude/session-receipts.jsonl 2>/dev/null | python3 -c "
import sys,json
for line in sys.stdin:
  try:
    r=json.loads(line.strip()); cost=\"\${:.2f}\".format(r.get(\"cost_usd\",0)); nc=len(r.get(\"commits\",[])); ts=r.get(\"ts\",\"?\")[:16]; proj=r.get(\"project\",\"?\"); reason=r.get(\"reason\",\"?\")
    print(f\"  {ts} | {proj:10} | {cost:>6} | {nc}c | {reason:12}\")
  except: pass
" || echo "(no receipts)"
echo ""; echo "=== UNIMPLEMENTED FINDINGS ==="; grep -B2 "Status:\*\* \[ \]" ~/Projects/meta/improvement-log.md 2>/dev/null | grep -E "(###|\*\*Status)" | head -10 || echo "(all clear)"
echo ""; echo "=== PROPOSALS ==="; ls ~/.claude/steward-proposals/*.md 2>/dev/null | while read f; do echo "  $(basename "$f")"; done || echo "(none)"
echo ""; echo "=== DB FRESHNESS ==="; for db in ClinVar gnomAD PharmCAT CPIC; do f=$(find "$(pwd)/databases/" -iname "*${db}*" -type f 2>/dev/null | head -1); if [ -n "$f" ]; then days=$(( ($(date +%s) - $(stat -f%m "$f" 2>/dev/null || echo 0)) / 86400 )); echo "  $db: ${days}d old"; else echo "  $db: not found"; fi; done
echo ""; echo "=== MAINTAIN STATE ==="; if [ -f "$(pwd)/MAINTAIN.md" ]; then findings=$(grep -c "^\- \*\*M[0-9]" "$(pwd)/MAINTAIN.md" 2>/dev/null || echo 0); queued=$(grep -c "\[queued\]" "$(pwd)/MAINTAIN.md" 2>/dev/null || echo 0); echo "  $findings findings, $queued queued"; else echo "  (no MAINTAIN.md -- first run, create from template)"; fi
echo ""; echo "=== RECENT ACTIONS ==="; tail -5 "$(pwd)/maintenance-actions.jsonl" 2>/dev/null || echo "(none yet)"
echo ""; echo "=== GIT (last 2h) ==="; for proj in meta intel selve genomics; do dir=~/Projects/$proj; [ -d "$dir/.git" ] || continue; out=$(cd "$dir" && git log --oneline --since="2 hours ago" 2>/dev/null | head -3); [ -n "$out" ] && echo "  $proj:" && echo "$out" | sed "s/^/    /"; done
' 2>&1 | head -80`

If state says "NO STATE CHANGE" -- report "noop" in one line and stop.

### Rate Limit Check

```bash
CLAUDE_PROCS=$(pgrep -lf claude 2>/dev/null | wc -l | tr -d ' ')
```
If >= 5: skip subagent dispatch (Tier 2). Route LLM-heavy analysis through `llmx chat -m gemini-3-flash-preview` (free).

### Each Tick: Pick ONE Task by Priority

**P0: Orchestrator Failures.**
If any tasks show failed/blocked: transient (network, rate limit) -> retry. Permission denied -> report. Blocked (approval gate) -> list, don't approve.

**P1: Queue Dispatch** (if queue >= 3).
Dispatch one Opus subagent for the oldest queued item. Rate-limit gate: skip if CLAUDE_PROCS >= 5.

**P2: Implement Promoted Findings.**
For unimplemented findings with `[ ]`: read context, verify 2+ recurrence, classify autonomous vs propose, execute or write proposal.

**P2.5: Route Design-Review Proposals.**
New design-review artifacts -> extract proposal -> write to `~/.claude/steward-proposals/`.

**P3: Routine Rotation.**
Pick highest-priority task that hasn't run within cadence:

| Task | Cadence | How |
|------|---------|-----|
| Database freshness | Daily | Check timestamps. Flag >30d stale. |
| Bio-verify audit | Rotate: 1/tick | `just bio-verify-queue` -> top item |
| Deferred probe | After revisit date | HTTP-probe URLs, check release pages |
| Cross-check outputs | Daily | Pick T1/T2 variant, query biomedical MCP, compare |
| Research memo staleness | Weekly | Check ACTIVE memos vs recent file changes |
| Code quality scan | Weekly | `/project-upgrade --quick` |
| Calibration canary | Weekly | `calibration-canary.py --mode sampling --difficulty hard --runs 10 --backend llmx` |
| Genomics canary | After classification changes | `just canary` in genomics |
| Doctor.py health | Daily | `uv run python3 scripts/doctor.py` |
| Session cost tracking | Daily | Flag sessions >$5 or no-commit anomalies |
| Infra coverage | Monthly | git log -> categorize fixes by detection source |
| Doc currency | Fallback | `just check-codebase-map && just check-claude-md` |

**P4: Implement Proposals.**
Read `~/.claude/steward-proposals/`. Autonomous -> implement, verify, commit. Append `**Status:** IMPLEMENTED`. Propose-only -> skip.

**P5: Triage & Escalation.**
Finding triage (>20 `[ ] proposed` -> batch-triage). Hook escalation (>100 warns/day for 3+ days with <20% FP -> write promote proposal).

**P6: All Clear.** Nothing actionable? Say so in one line. Don't invent work.

### Tier 2: Dispatched Work

Max 1 per tick. Rate-limit gate.

| Task | Cadence | Skill/Tool |
|------|---------|-----------|
| Audit sweep | Biweekly | `/dispatch-research quick sweep` |
| Benchmark drift | After pipeline changes | `noncoding_benchmark.py benchmark` |

### Execution Model

Auto-fix deterministic (unused imports, stale versions) inline. Dispatch multi-file fixes via Opus subagent.

### Logging

Append JSONL to `maintenance-actions.jsonl` for EVERY action:
```json
{"ts":"2026-04-06T12:00","action":"freshness","target":"ClinVar","result":"ok","detail":"12d old"}
```

### MAINTAIN.md

Unified quality state. If it doesn't exist, create from `${CLAUDE_SKILL_DIR}/references/MAINTAIN.md`.

Sections: Findings, Queue, Fixed, Deferred, Strategic Notes, Drift Alerts.
Item IDs: monotonic M001, M002... WIP caps enforce flow:
- Max 5 findings — when full, skip new findings until dispositioned
- Max 3 queued — when full, halt discovery, focus dispatch
- Items >90 days stale — auto-move to end with `[STALE]` note

### Autonomy Rules

**Autonomous:** meta-only files, advisory hooks, measurement scripts, retry transient failures, finding triage, rule additions (2+ recurrence).
**Propose only:** changes to intel/selve/genomics/skills, shared hooks/skills, new pipelines, structural changes, multiple viable approaches.
**Never:** constitution/GOALS.md, capital deployment, external contacts, shared infra deployment.

### Error Recovery

Task fails: log error, skip this tick, don't retry same task consecutively. Subagent fails: log, keep in queue, retry next tick if rate-limit allows.

### Operating Rules

1. One task per tick. Highest priority.
2. Log everything. JSONL is the audit trail.
3. Report in 1-3 lines.
4. Auto-fix deterministic, dispatch the rest.
5. Respect revisit dates.
6. Don't touch CYCLE.md.
7. Idempotent -- check action log and git log before acting.
8. Ultrathink for implementation.
9. Classify before acting.

---

## Mode: tick

Run one orchestrator tick and report status. Designed for `/loop 5m /tick`.

### Execute

```bash
uv run python3 ~/Projects/meta/scripts/orchestrator.py tick 2>&1
```

### Status

```bash
uv run python3 ~/Projects/meta/scripts/orchestrator.py status 2>&1 | head -30
```

### Report

One paragraph: what ran (if anything), what's next in queue, any failures. If nothing pending, say so and stop.

---

## Relationship to Other Skills

```
session-analyst ---> artifacts/session-analyst/*.json --+
design-review ----> artifacts/design-review/*.md ------+
retro ------------> artifacts/session-retro/*.json ----+---> improve harvest ---> artifacts/harvest/*.md
suggest-skill ----> artifacts/suggest-skill/*.md ------+
user #f feedback -> session transcripts ---------------+
git corrections --> git log ----------------------------+
```

$ARGUMENTS
#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Simple review (1 query: combined)
    model-review.py --context plan.md --topic "config tweak" --axes simple "Review this change"

    # Deep review (4 queries: arch + formal + domain + mechanical)
    model-review.py --context plan.md --topic "classification logic" --axes arch,formal,domain,mechanical "Review this"

    # With project dir for constitution discovery
    model-review.py --context plan.md --topic "data wiring" --project ~/Projects/intel "Review this plan"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from llmx.api import chat as llmx_chat

# --- Structured output schema (both models return this) ---

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Sequential finding number"},
                    "category": {
                        "type": "string",
                        "enum": ["bug", "logic", "architecture", "missing", "performance", "security", "style", "constitutional"],
                    },
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "title": {"type": "string", "description": "One-line summary"},
                    "description": {"type": "string", "description": "Detailed explanation with evidence"},
                    "file": {"type": "string", "description": "File path if applicable, empty string if architectural"},
                    "line": {"type": "integer", "description": "Line number if applicable, 0 if N/A"},
                    "fix": {"type": "string", "description": "Specific proposed fix"},
                    "confidence": {"type": "number", "description": "0.0-1.0 confidence in this finding"},
                },
                "required": ["id", "category", "severity", "title", "description", "file", "fix", "confidence"],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string", "description": "2-3 sentence overall assessment"},
        "blind_spots": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Where this model is likely wrong",
        },
    },
    "required": ["findings", "summary", "blind_spots"],
    "additionalProperties": False,
}

# --- Axis definitions: model + prompt + api kwargs ---

AXES = {
    "arch": {
        "label": "Gemini (architecture/patterns)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code, configs, and findings. It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
{constitution_instruction}

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?""",
    },
    "formal": {
        "label": "GPT-5.4 (quantitative/formal)",
        "model": "gpt-5.4",
        "provider": "openai",
        "api_kwargs": {"timeout": 600, "reasoning_effort": "high", "max_tokens": 32768},
        "prompt": """\
<system>
You are performing QUANTITATIVE and FORMAL analysis. Other reviewers handle qualitative pattern review. Focus on what they can't do well. Be precise. Show your reasoning. No hand-waving.
Budget: ~2000 words. Tables over prose. Source-grade claims.
</system>

{question}

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
{constitution_instruction}

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.""",
    },
    "domain": {
        "label": "Gemini Pro (domain correctness)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
You are verifying DOMAIN-SPECIFIC CLAIMS in this plan. Other reviewers handle architecture and formal logic.
Focus exclusively on: are the domain facts correct? Are citations real? Are API endpoints, database schemas,
biological claims, financial numbers accurate? Check every specific claim against your knowledge.
Budget: ~1500 words. Flat list of claims with verdict (CORRECT / WRONG / UNVERIFIABLE).
</system>

{question}

For each domain-specific claim in the reviewed material:
1. State the claim
2. Verdict: CORRECT / WRONG / UNVERIFIABLE
3. If WRONG: what's actually true
4. If UNVERIFIABLE: what would you need to check

Flag any URLs, API endpoints, or version numbers that should be probed before implementation.""",
    },
    "mechanical": {
        "label": "Gemini Flash (mechanical audit)",
        "model": "gemini-3-flash-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 120},
        "prompt": """\
<system>
Mechanical audit only. No analysis, no recommendations. Fast and precise.
</system>

Find in the reviewed material:
- Stale references (wrong versions, deprecated APIs, broken links)
- Inconsistent naming (model names, paths, conventions that don't match)
- Missing cross-references between related documents
- Duplicated content
- Paths or file references that look wrong
Output as a flat numbered list. One issue per line.""",
    },
    "alternatives": {
        "label": "Gemini Pro (alternative approaches)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
You are generating ALTERNATIVE APPROACHES to the proposed plan. Other reviewers check correctness.
Your job: what ELSE could be done? Different mechanisms, not variations.
Budget: ~1500 words.
</system>

{question}

Generate 3-5 genuinely different approaches to the same problem. For each:
1. Core mechanism (how it works differently)
2. What it's better at than the proposed approach
3. What it's worse at
4. Maintenance burden and complexity cost (not implementation effort — agents build everything)

Do NOT critique the existing plan — generate alternatives. Different mechanisms, not tweaks.""",
    },
    "simple": {
        "label": "Gemini Pro (combined review)",
        "model": "gemini-3.1-pro-preview",
        "provider": "google",
        "api_kwargs": {"timeout": 300},
        "prompt": """\
<system>
Quick combined review. Be concrete. It is {date}. Budget: ~1000 words.
</system>

{question}

Check for: (1) anything that breaks existing functionality, (2) wrong assumptions, (3) missing edge cases.
If everything looks correct, say so concisely.""",
    },
}

# Presets map a single name to a list of axes
PRESETS = {
    "simple": ["simple"],
    "standard": ["arch", "formal"],
    "deep": ["arch", "formal", "domain", "mechanical"],
    "full": ["arch", "formal", "domain", "mechanical", "alternatives"],
}

GEMINI_PRO_MODEL = "gemini-3.1-pro-preview"
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"
GEMINI_RATE_LIMIT_MARKERS = (
    "503",
    "rate limit",
    "rate-limit",
    "resource_exhausted",
    "overloaded",
    "429",
)


def slugify(text: str, max_len: int = 40) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:max_len]


def _call_llmx(
    provider: str,
    model: str,
    context_path: Path,
    prompt: str,
    output_path: Path,
    schema: dict | None = None,
    **kwargs,
) -> dict:
    """Call llmx Python API, write output to file, return result dict."""
    context = context_path.read_text()
    full_prompt = context + "\n\n---\n\n" + prompt
    try:
        response = llmx_chat(
            prompt=full_prompt,
            provider=provider,
            model=model,
            temperature=0.7,
            response_format=schema,
            **kwargs,
        )
        output_path.write_text(response.content)
        return {
            "exit_code": 0,
            "size": output_path.stat().st_size,
            "latency": response.latency,
            "error": None,
        }
    except Exception as e:
        error_msg = str(e)[:500]
        print(f"warning: llmx call failed ({model}): {error_msg}", file=sys.stderr)
        return {
            "exit_code": 1,
            "size": 0,
            "latency": 0,
            "error": error_msg,
        }


def axis_output_failed(info: object) -> bool:
    """Return True when an axis failed to produce a usable review artifact."""
    if not isinstance(info, dict):
        return False
    return int(info.get("exit_code", 0)) != 0 or int(info.get("size", 0)) == 0


def collect_dispatch_failures(
    dispatch_result: dict,
    ctx_files: dict[str, Path],
) -> list[dict[str, object]]:
    """Summarize failed axes for machine-readable failure artifacts."""
    failures: list[dict[str, object]] = []
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}
    for axis, info in dispatch_result.items():
        if axis in skip_keys or not axis_output_failed(info):
            continue
        entry = dict(info)
        entry["axis"] = axis
        entry["context"] = str(ctx_files.get(axis, ""))
        entry["failure_reason"] = (
            "nonzero_exit" if int(entry.get("exit_code", 0)) != 0 else "empty_output"
        )
        failures.append(entry)
    return failures


def is_gemini_rate_limit_failure(model: str, exit_code: int, stderr: str, output_size: int) -> bool:
    if model != GEMINI_PRO_MODEL:
        return False
    if exit_code == 0 and output_size > 0:
        return False
    stderr_lower = stderr.lower()
    return exit_code == 3 or any(marker in stderr_lower for marker in GEMINI_RATE_LIMIT_MARKERS)


def rerun_axis_with_flash(
    axis: str,
    axis_def: dict[str, object],
    review_dir: Path,
    ctx_file: Path,
    prompt: str,
) -> dict:
    """Retry a failed Gemini Pro axis with Gemini Flash."""
    out_path = review_dir / f"{axis}-output.md"
    print(
        f"warning: {axis} hit Gemini Pro rate limits; retrying once with Gemini Flash",
        file=sys.stderr,
    )
    api_kwargs = dict(axis_def.get("api_kwargs") or {})  # type: ignore[arg-type]
    return _call_llmx(
        provider="google",
        model=GEMINI_FLASH_MODEL,
        context_path=ctx_file,
        prompt=prompt,
        output_path=out_path,
        **api_kwargs,
    )


def find_constitution(project_dir: Path) -> tuple[str, str | None]:
    """Find constitution text and GOALS.md path in project dir."""
    constitution = ""
    goals_path = None

    # Check .claude/rules/constitution.md first (genomics, projects with standalone file)
    rules_const = project_dir / ".claude" / "rules" / "constitution.md"
    if rules_const.exists():
        constitution = rules_const.read_text().strip()

    # Fall back to CLAUDE.md <constitution> tag or ## Constitution heading
    if not constitution:
        claude_md = project_dir / "CLAUDE.md"
        if claude_md.exists():
            text = claude_md.read_text()
            m = re.search(r"<constitution>(.*?)</constitution>", text, re.DOTALL)
            if m:
                constitution = m.group(1).strip()
            elif "## Constitution" in text:
                idx = text.index("## Constitution")
                rest = text[idx:]
                end = re.search(r"\n## (?!Constitution)", rest)
                constitution = rest[: end.start()].strip() if end else rest.strip()

    for gp in [project_dir / "GOALS.md", project_dir / "docs" / "GOALS.md"]:
        if gp.exists():
            goals_path = str(gp)
            break

    return constitution, goals_path


def parse_file_spec(spec: str) -> str:
    """Parse a file:start-end spec and return the content.

    Formats:
      path/file.py           — entire file
      path/file.py:100-150   — lines 100-150 (1-based, inclusive)
      path/file.py:100       — single line
    """
    if ":" in spec and not spec.startswith("/") or spec.count(":") == 1:
        parts = spec.rsplit(":", 1)
        file_path = parts[0]
        range_spec = parts[1] if len(parts) > 1 else ""
    else:
        file_path = spec
        range_spec = ""

    path = Path(file_path).expanduser()
    if not path.exists():
        return f"# [FILE NOT FOUND: {file_path}]\n"

    text = path.read_text()

    if range_spec and "-" in range_spec:
        try:
            start, end = range_spec.split("-", 1)
            start_line = int(start) - 1  # 0-based
            end_line = int(end)
            lines = text.splitlines()
            text = "\n".join(lines[start_line:end_line])
        except (ValueError, IndexError):
            pass
    elif range_spec:
        try:
            line_no = int(range_spec) - 1
            lines = text.splitlines()
            text = lines[line_no] if 0 <= line_no < len(lines) else text
        except (ValueError, IndexError):
            pass

    return f"# {file_path}" + (f" (lines {range_spec})" if range_spec else "") + f"\n\n{text}\n\n"


def assemble_context_files(specs: list[str]) -> str:
    """Assemble content from multiple file:range specs into one context string."""
    parts = []
    for spec in specs:
        parts.append(parse_file_spec(spec.strip()))
    return "\n".join(parts)


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
    *,
    context_file_specs: list[str] | None = None,
) -> dict[str, Path]:
    """Assemble per-axis context files with constitutional preamble.

    Context sources (in order of precedence):
      1. --context FILE — single pre-assembled context file
      2. --context-files spec1 spec2 ... — auto-assembled from file:range specs
    """
    constitution, goals_path = find_constitution(project_dir)

    preamble = ""
    if constitution:
        # Always include full constitution verbatim — summaries lose nuance
        # that causes reviewers to over-apply or misapply principles
        preamble += "# PROJECT CONSTITUTION (verbatim — review against these, not your priors)\n\n"
        preamble += constitution + "\n\n"
    if goals_path:
        preamble += "# PROJECT GOALS\n\n"
        preamble += Path(goals_path).read_text() + "\n\n"

    # Agent economics framing — always included so reviewers don't
    # recommend trading quality for dev time (which is ~free with agents)
    preamble += "# DEVELOPMENT CONTEXT\n"
    preamble += "All code, plans, and features in this project are developed by AI agents, not human developers. "
    preamble += "Dev creation time is effectively zero. Therefore:\n"
    preamble += "- NEVER recommend trading stability, composability, or robustness for dev time savings\n"
    preamble += "- NEVER recommend simpler/hacky approaches because they're 'faster to implement'\n"
    preamble += "- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort\n"
    preamble += "- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters\n\n"

    # Assemble content from the right source
    if context_file:
        content = context_file.read_text()
    elif context_file_specs:
        content = assemble_context_files(context_file_specs)
    else:
        content = ""

    ctx_files = {}
    for axis in axis_names:
        ctx_path = review_dir / f"{axis}-context.md"
        ctx_path.write_text(preamble + content)
        ctx_files[axis] = ctx_path

    # Warn on size
    for axis, path in ctx_files.items():
        size = path.stat().st_size
        if size > 15_000:
            print(f"warning: {axis} context {size} bytes > 15KB — consider summarizing", file=sys.stderr)

    return ctx_files


def dispatch(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_constitution: bool,
    question_overrides: dict[str, str] | None = None,
) -> dict:
    """Fire N llmx API calls in parallel (one per axis), wait, return results."""
    today = date.today().isoformat()

    const_instruction = {
        "arch": (
            "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?"
            if has_constitution
            else "No constitution provided — assess internal consistency only."
        ),
        "formal": (
            "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes."
            if has_constitution
            else "No constitution provided — assess internal logical consistency."
        ),
    }

    prompts: dict[str, str] = {}
    t0 = time.time()

    for axis in axis_names:
        axis_def = AXES[axis]
        axis_question = (question_overrides or {}).get(axis, question)
        prompts[axis] = axis_def["prompt"].format(
            date=today,
            question=axis_question,
            constitution_instruction=const_instruction.get(axis, ""),
        )

    def _run_axis(axis: str) -> tuple[str, dict]:
        axis_def = AXES[axis]
        out_path = review_dir / f"{axis}-output.md"
        result = _call_llmx(
            provider=str(axis_def["provider"]),
            model=str(axis_def["model"]),
            context_path=ctx_files[axis],
            prompt=prompts[axis],
            output_path=out_path,
            **dict(axis_def.get("api_kwargs") or {}),  # type: ignore[arg-type]
        )
        entry = {
            "label": axis_def["label"],
            "requested_model": str(axis_def["model"]),
            "model": str(axis_def["model"]),
            "exit_code": result["exit_code"],
            "output": str(out_path),
            "size": result["size"],
        }
        if result.get("latency"):
            entry["latency"] = result["latency"]
        if result.get("error"):
            entry["stderr"] = result["error"]

        # Gemini Pro fallback to Flash on rate limit
        if (
            str(axis_def["model"]) == GEMINI_PRO_MODEL
            and result["exit_code"] != 0
            and result.get("error")
            and any(m in result["error"].lower() for m in GEMINI_RATE_LIMIT_MARKERS)
        ):
            entry["fallback_from"] = str(axis_def["model"])
            entry["fallback_reason"] = "gemini_rate_limit"
            entry["initial_exit_code"] = result["exit_code"]
            flash_result = rerun_axis_with_flash(
                axis, axis_def, review_dir, ctx_files[axis], prompts[axis],
            )
            entry["model"] = GEMINI_FLASH_MODEL
            entry["exit_code"] = flash_result["exit_code"]
            entry["size"] = flash_result["size"]

        if entry["size"] == 0:
            entry["failure_reason"] = "empty_output"

        return axis, entry

    # Parallel dispatch via threads
    results: dict = {"review_dir": str(review_dir), "axes": axis_names, "queries": len(axis_names)}
    with ThreadPoolExecutor(max_workers=len(axis_names)) as pool:
        futures = {pool.submit(_run_axis, axis): axis for axis in axis_names}
        for future in as_completed(futures):
            axis, entry = future.result()
            results[axis] = entry

    results["elapsed_seconds"] = round(time.time() - t0, 1)
    return results


EXTRACTION_PROMPT = (
    "Extract every discrete recommendation, finding, or claimed bug from the review. "
    "Return JSON matching the schema. For each finding: category, severity, a one-line title, "
    "description with the reviewer's evidence, file path if cited, proposed fix, "
    "and confidence 0.0-1.0 based on specificity of evidence. "
    "SKIP confirmatory observations that merely describe correct behavior. "
    "Only extract items that propose a change, flag a problem, or claim something is wrong/missing."
)


_UNCALIBRATED_RE = re.compile(
    r"(?:"
    r"(?:≥|>=|>|at least|minimum|must exceed)\s*(\d+(?:\.\d+)?)\s*"  # op NUMBER unit
    r"(?:%|pp|percentage points?|AUPRC|AUROC|PPV|NPV|F1|AUC)"
    r"|"
    r"(?:AUPRC|AUROC|PPV|NPV|F1|AUC)\s*(?:\w+\s+)?(?:≥|>=|>)\s*(\d+(?:\.\d+)?)"  # UNIT [by] op NUMBER
    r"|"
    r"(?:≥|>=|>)\s*(\d+(?:\.\d+)?)\s*(?:%|pp)[/,]"  # ≥95%/ or ≥50%, (slash-separated thresholds)
    r")",
    re.IGNORECASE,
)

# Source indicators — if these appear near the number, it's probably calibrated
_SOURCE_INDICATORS = re.compile(
    r"(?:paper|study|benchmark|calibrat|empirical|measured|observed|from\s+\w+\s+\d{4}|"
    r"doi|PMID|arXiv|Table\s+\d|Figure\s+\d|Supplementary)",
    re.IGNORECASE,
)


def _flag_uncalibrated_thresholds(text: str) -> str:
    """Flag numeric threshold claims that lack cited sources.

    Adds [UNCALIBRATED] tag to lines with threshold operators (≥X%, PPV ≥0.8)
    that don't mention a paper, benchmark, or empirical source nearby.
    """
    lines = text.split("\n")
    flagged = []
    for line in lines:
        if _UNCALIBRATED_RE.search(line) and not _SOURCE_INDICATORS.search(line):
            if "[UNCALIBRATED]" not in line:
                line = line.rstrip() + " [UNCALIBRATED]"
        flagged.append(line)
    return "\n".join(flagged)


def extract_claims(
    review_dir: Path,
    dispatch_result: dict,
) -> str | None:
    """Cross-family extraction: Flash extracts GPT outputs, GPT-Instant extracts Gemini outputs.

    Returns path to disposition.md, or None if no outputs to extract.
    """
    extraction_tasks: list[tuple[str, Path, str, str]] = []  # (axis, output_path, model, provider)
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}

    for axis, info in dispatch_result.items():
        if axis in skip_keys or not isinstance(info, dict):
            continue
        if info.get("size", 0) == 0:
            continue

        output_path = Path(info["output"])
        if not output_path.exists():
            continue

        model = info.get("model", "")

        # Cross-family: Gemini outputs → GPT extraction, GPT outputs → Gemini Flash extraction
        if "gemini" in model.lower():
            extraction_tasks.append((axis, output_path, "gpt-5.3-chat-latest", "openai"))
        else:
            extraction_tasks.append((axis, output_path, "gemini-3-flash-preview", "google"))

    if not extraction_tasks:
        return None

    print(
        f"Extracting claims from {len(extraction_tasks)} outputs...",
        file=sys.stderr,
    )

    def _extract_one(task: tuple[str, Path, str, str]) -> tuple[str, list[dict] | None]:
        axis, output_path, model, provider = task
        extraction_path = review_dir / f"{axis}-extraction.json"
        result = _call_llmx(
            provider=provider,
            model=model,
            context_path=output_path,
            prompt=EXTRACTION_PROMPT,
            output_path=extraction_path,
            schema=FINDING_SCHEMA,
            timeout=120,
        )
        if result["exit_code"] != 0:
            print(f"warning: extraction for {axis} failed: {result.get('error', 'unknown')}", file=sys.stderr)
            return axis, None
        if result["size"] > 0:
            try:
                data = json.loads(extraction_path.read_text())
                return axis, data.get("findings", [])
            except (json.JSONDecodeError, KeyError) as e:
                print(f"warning: extraction for {axis} returned invalid JSON: {e}", file=sys.stderr)
                # Fall back to raw text
                return axis, None
        print(f"warning: extraction for {axis} produced empty output", file=sys.stderr)
        return axis, None

    # Parallel extraction
    axis_findings: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(extraction_tasks)) as pool:
        for axis, findings in pool.map(_extract_one, extraction_tasks):
            if findings:
                axis_findings[axis] = findings

    if not axis_findings:
        return None

    # Merge findings across axes — tag source model, cross-reference overlaps
    merged_findings: list[dict] = []
    seen_titles: dict[str, dict] = {}  # title_lower -> finding
    for axis, findings in axis_findings.items():
        source_label = dispatch_result[axis].get("label", axis)
        source_model = dispatch_result[axis].get("model", "unknown")
        for f in findings:
            f["source_axis"] = axis
            f["source_model"] = source_model
            f["source_label"] = source_label
            title_key = f.get("title", "").lower().strip()
            if title_key in seen_titles:
                # Cross-model agreement — boost confidence, tag both sources
                existing = seen_titles[title_key]
                existing.setdefault("also_found_by", []).append(source_label)
                existing["cross_model"] = True
                existing["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.2)
            else:
                seen_titles[title_key] = f
                merged_findings.append(f)

    # Sort: cross-model agreements first, then by severity, then confidence
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    merged_findings.sort(key=lambda f: (
        0 if f.get("cross_model") else 1,
        severity_order.get(f.get("severity", "low"), 3),
        -(f.get("confidence", 0)),
    ))

    # Renumber
    for i, f in enumerate(merged_findings, 1):
        f["id"] = i

    # Write structured JSON
    structured_path = review_dir / "findings.json"
    structured_path.write_text(json.dumps({"findings": merged_findings}, indent=2) + "\n")

    # Write human-readable disposition
    extractions: list[str] = []
    for f in merged_findings:
        source = f.get("source_label", "unknown")
        also = f.get("also_found_by", [])
        agreement = f" **[CROSS-MODEL: also {', '.join(also)}]**" if also else ""
        conf = f.get("confidence", 0)
        extractions.append(
            f"{f['id']}. **[{f.get('severity', '?').upper()}]** {f.get('title', '?')}{agreement}\n"
            f"   Category: {f.get('category', '?')} | Confidence: {conf:.1f} | Source: {source}\n"
            f"   {f.get('description', '')}\n"
            f"   File: {f.get('file', 'N/A')}\n"
            f"   Fix: {f.get('fix', 'N/A')}"
        )

    if not extractions:
        return None

    disposition = review_dir / "disposition.md"
    merged = "\n\n---\n\n".join(extractions)

    # Flag uncalibrated thresholds — numeric claims without cited sources
    merged = _flag_uncalibrated_thresholds(merged)

    response_template = (
        "\n\n---\n\n"
        "## Agent Response (fill before implementing)\n\n"
        "### Where I disagree with the disposition:\n"
        '<!-- "Nowhere" is valid. Don\'t invent disagreements. -->\n\n\n'
        "### Context I had that the models didn't:\n"
        "<!-- If context file was comprehensive, say so. -->\n\n"
    )
    cross_model_count = sum(1 for f in merged_findings if f.get("cross_model"))
    header = (
        f"# Review Findings — {date.today().isoformat()}\n\n"
        f"**{len(merged_findings)} findings** from {len(axis_findings)} axes"
        f" ({cross_model_count} cross-model agreements)\n"
        f"Structured data: `findings.json`\n\n"
    )
    disposition.write_text(header + merged + response_template)
    return str(disposition)


def verify_claims(
    review_dir: Path,
    disposition_path: str,
    project_dir: Path,
) -> str:
    """Verify extracted claims against the actual codebase.

    Checks if cited files and symbols exist. Grades each claim:
    - CONFIRMED: all cited files/symbols found
    - HALLUCINATED: cited file does not exist in project
    - UNVERIFIABLE: no file references to check

    Returns path to verified-disposition.md.
    """
    disposition_text = Path(disposition_path).read_text()

    # Parse claims: numbered lines (e.g., "1. Function X in foo.py has bug")
    claims: list[dict] = []
    current_section = ""
    for line in disposition_text.splitlines():
        section_match = re.match(r"^##\s+(.+)", line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue
        claim_match = re.match(r"^(\d+)\.\s+(.+)", line.strip())
        if claim_match:
            claims.append({
                "num": int(claim_match.group(1)),
                "text": claim_match.group(2),
                "section": current_section,
            })

    if not claims:
        print("No numbered claims found in disposition.", file=sys.stderr)
        return disposition_path

    # Verify each claim
    verified: list[dict] = []
    for claim in claims:
        text = claim["text"]
        verdict = "UNVERIFIABLE"
        notes: list[str] = []

        # Extract file references: path/file.ext or file.ext:line or `file.ext`
        file_refs = re.findall(
            r"`?([a-zA-Z_][\w/.-]*\.(?:py|js|ts|md|sh|json|yaml|yml|toml|cfg|sql|html|css|clj|cljc|edn))(?::(\d+))?`?",
            text,
        )

        if not file_refs:
            verified.append({**claim, "verdict": verdict, "notes": "no file references"})
            continue

        all_found = True
        for filepath, line_str in file_refs:
            candidates = list(project_dir.rglob(filepath))
            if not candidates:
                verdict = "HALLUCINATED"
                notes.append(f"{filepath} not found")
                all_found = False
            else:
                found_path = candidates[0]
                if line_str:
                    line_num = int(line_str)
                    try:
                        lines = found_path.read_text().splitlines()
                        if line_num > len(lines):
                            notes.append(f"{filepath}:{line_num} beyond EOF ({len(lines)} lines)")
                        else:
                            notes.append(f"{filepath} exists, L{line_num} readable")
                    except Exception:
                        notes.append(f"{filepath} exists but unreadable")
                else:
                    notes.append(f"{filepath} exists")

        if all_found and verdict != "HALLUCINATED":
            verdict = "CONFIRMED"

        verified.append({**claim, "verdict": verdict, "notes": "; ".join(notes)})

    # Stats
    confirmed = sum(1 for v in verified if v["verdict"] == "CONFIRMED")
    hallucinated = sum(1 for v in verified if v["verdict"] == "HALLUCINATED")
    unverifiable = sum(1 for v in verified if v["verdict"] == "UNVERIFIABLE")

    # Write verified disposition
    out_path = review_dir / "verified-disposition.md"
    lines_out = [
        f"# Verified Disposition — {date.today().isoformat()}\n",
        f"**Claims:** {len(verified)} total — "
        f"{confirmed} CONFIRMED, {hallucinated} HALLUCINATED, {unverifiable} UNVERIFIABLE\n",
    ]
    if hallucinated > 0:
        rate = round(hallucinated / len(verified) * 100)
        lines_out.append(f"**Hallucination rate:** {rate}%\n")
    lines_out.append("")
    lines_out.append("| # | Verdict | Claim | Notes |")
    lines_out.append("|---|---------|-------|-------|")
    for v in verified:
        claim_short = v["text"][:80] + ("..." if len(v["text"]) > 80 else "")
        lines_out.append(f"| {v['num']} | {v['verdict']} | {claim_short} | {v.get('notes', '')} |")
    lines_out.append("")

    out_path.write_text("\n".join(lines_out) + "\n")
    print(
        f"Verification: {confirmed} confirmed, {hallucinated} hallucinated, "
        f"{unverifiable} unverifiable ({len(verified)} total)",
        file=sys.stderr,
    )
    return str(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Model-review dispatch: context assembly + parallel llmx + output collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Presets: {', '.join(PRESETS.keys())}. Axes: {', '.join(AXES.keys())}.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--context", type=Path, help="Context file for narrow review")
    group.add_argument(
        "--context-files", nargs="+", metavar="FILE_SPEC",
        help="Auto-assemble context from file:range specs (e.g., plan.md scripts/ir.py:86-110)",
    )
    parser.add_argument("--topic", required=True, help="Short topic label (used in output dir name)")
    parser.add_argument("--project", type=Path, help="Project dir for constitution discovery (default: cwd)")
    parser.add_argument(
        "--axes", default="standard",
        help="Comma-separated axes or preset name (simple, standard, deep, full). Default: standard",
    )
    parser.add_argument(
        "--extract", action="store_true",
        help="After dispatch, auto-extract claims from each output into disposition.md",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After extraction, verify cited files/symbols exist. Implies --extract.",
    )
    parser.add_argument(
        "--questions", type=Path,
        help="JSON file mapping axis names to custom questions (overrides positional question per-axis)",
    )
    parser.add_argument(
        "question", nargs="?",
        default="Review this for logical gaps, missed edge cases, and constitutional alignment.",
        help="Review question for all models",
    )

    args = parser.parse_args()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    # Resolve axes
    if args.axes in PRESETS:
        axis_names = PRESETS[args.axes]
    else:
        axis_names = [a.strip() for a in args.axes.split(",")]
        for a in axis_names:
            if a not in AXES:
                print(f"error: unknown axis '{a}'. Available: {', '.join(AXES.keys())}", file=sys.stderr)
                return 1

    print(f"Dispatching {len(axis_names)} queries: {', '.join(axis_names)}", file=sys.stderr)

    # Create output directory
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    # Assemble context
    ctx_files = build_context(
        review_dir, project_dir, args.context, axis_names,
        context_file_specs=args.context_files,
    )

    constitution, _ = find_constitution(project_dir)

    # Load per-axis question overrides
    question_overrides = None
    if args.questions:
        if not args.questions.exists():
            print(f"error: questions file {args.questions} not found", file=sys.stderr)
            return 1
        question_overrides = json.loads(args.questions.read_text())

    # Dispatch and wait
    result = dispatch(review_dir, ctx_files, axis_names, args.question, bool(constitution), question_overrides)
    failures = collect_dispatch_failures(result, ctx_files)
    if failures:
        failure_path = review_dir / "dispatch-failures.json"
        failure_path.write_text(json.dumps({"failures": failures}, indent=2) + "\n")
        result["dispatch_failures"] = str(failure_path)
        result["failed_axes"] = [failure["axis"] for failure in failures]
        print(
            f"error: model-review dispatch produced unusable outputs for "
            f"{', '.join(result['failed_axes'])}; see {failure_path}",
            file=sys.stderr,
        )
        print(json.dumps(result, indent=2))
        return 2

    # --verify implies --extract
    do_extract = args.extract or args.verify

    # Optional extraction phase
    if do_extract:
        disposition_path = extract_claims(review_dir, result)
        if disposition_path:
            result["disposition"] = disposition_path
            print(f"Disposition written to {disposition_path}", file=sys.stderr)

            # Optional verification phase
            if args.verify:
                verified_path = verify_claims(review_dir, disposition_path, project_dir)
                result["verified_disposition"] = verified_path
                print(f"Verified disposition written to {verified_path}", file=sys.stderr)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
