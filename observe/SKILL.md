---
name: observe
description: "Use when: 'what went wrong in recent sessions', 'check session quality', 'retrospective', 'where was time wasted'. Modes: /observe sessions (anti-patterns), /observe architecture (design patterns), /observe supervision (wasted human time), /observe retro (this session)."
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

## Artifact Contract

See `references/artifact-contract.md` for the canonical observe artifact tree, deterministic
signal/candidate flow, and promotion gates.

## Mode Routing

| Mode | Question answered | Gemini dispatch? | Canonical artifacts |
|------|------------------|------------------|---------------------|
| `sessions` | What behavioral anti-patterns appeared? | Yes | `manifest.json` -> `signals.jsonl` -> `candidates.jsonl` -> `digest.md` (+ `dispatch.meta.json` when dispatched) |
| `architecture` | What design wants to emerge? | Yes | `manifest.json` -> `signals.jsonl` -> `candidates.jsonl` -> `patterns.jsonl` -> `YYYY-MM-DD.md` |
| `supervision` | Where was human time wasted? | Yes | `manifest.json` -> `signals.jsonl` -> `candidates.jsonl` -> `digest.md` (+ `dispatch.meta.json` when dispatched) |
| `retro` | What went wrong this session? | No (local) | `artifacts/session-retro/` |

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
OBSERVE_PROJECT_ROOT="${OBSERVE_PROJECT_ROOT:-$HOME/Projects/agent-infra}"
ARTIFACT_DIR="${OBSERVE_ARTIFACT_ROOT:-$OBSERVE_PROJECT_ROOT/artifacts/observe}"
mkdir -p "$ARTIFACT_DIR"
cat > "$ARTIFACT_DIR/manifest.json" <<EOF
{"mode":"$MODE","project":"${PROJECT:-all}","artifact_dir":"$ARTIFACT_DIR"}
EOF

# Claude Code sessions
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_transcript.py <project> --sessions <N> --full --output "$ARTIFACT_DIR/input.md"

# Codex CLI sessions (GPT-5.4) — reads ~/.codex/state_5.sqlite + rollout JSONL.
# Codex runs alongside Claude Code on the same project. Absence is non-fatal, but
# presence MUST be included in the dispatch context (never silently dropped).
# The `|| : > ...` ensures codex.md exists even when no sessions match, so the
# downstream concatenation in Step 2 doesn't fail.
python3 ${CLAUDE_SKILL_DIR}/scripts/extract_codex_transcript.py <project> --sessions <N> --output "$ARTIFACT_DIR/codex.md" 2>/dev/null || : > "$ARTIFACT_DIR/codex.md"
```

Record both inputs in `manifest.json` so downstream tooling can audit what was analyzed:

```bash
cat > "$ARTIFACT_DIR/manifest.json" <<EOF
{"mode":"$MODE","project":"${PROJECT:-all}","artifact_dir":"$ARTIFACT_DIR","inputs":["input.md","codex.md"]}
EOF
```

### Operational Context

Build operational context (hook triggers, receipts, git commits) for the session window. See `references/transcript-extraction.md` Step 1.3 for the full script.

### Coverage Digest

Generate existing-coverage digest so Gemini doesn't re-report known patterns:

```bash
bash "$OBSERVE_PROJECT_ROOT/scripts/coverage-digest.sh" > "$ARTIFACT_DIR/coverage-digest.txt"
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

### Step 0: Run Manifest

Treat `manifest.json`, `signals.jsonl`, and `candidates.jsonl` as the primary outputs.
`improvement-log.md` is a promotion sink, not the working artifact store.

At run start, record:
- mode
- project filter
- session ids / extraction inputs
- artifact root
- whether dispatch ran

If the same session set already exists in the current manifest and `--force` was not passed, stop instead of appending another narrative-only run.

### Step 1: Extract & Pre-Filter

Run shared transcript extraction above. Build operational context per `references/transcript-extraction.md` Step 1.3.

### Step 2: Dispatch to Gemini

Send full-fidelity transcript + coverage digest + operational context to Gemini 3.1 Pro. Full prompt in `references/gemini-dispatch-prompt.md`.

Dispatch via the shared wrapper, not raw SDK calls. Concatenate BOTH transcript sources
(Claude Code + Codex) plus the coverage digest. The `[ -s codex.md ]` guard keeps dispatch
working when no Codex sessions exist in the window, but when they do, Codex must be included:

```bash
{
  cat "$ARTIFACT_DIR/input.md"
  if [ -s "$ARTIFACT_DIR/codex.md" ]; then
    printf '\n\n---\n\n'
    cat "$ARTIFACT_DIR/codex.md"
  fi
  printf '\n\n---\n\n'
  cat "$ARTIFACT_DIR/coverage-digest.txt"
} > /tmp/observe-context.md
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile deep_review \
  --context /tmp/observe-context.md \
  --prompt-file "$CLAUDE_SKILL_DIR/references/gemini-dispatch-prompt.md" \
  --output "$ARTIFACT_DIR/gemini-output.md" \
  --meta "$ARTIFACT_DIR/gemini-output.meta.json" \
  --error-output "$ARTIFACT_DIR/gemini-output.error.json"
```

### Step 3: Stage Findings

Validate Gemini output against transcript, check session UUIDs, and stage the result as a candidate record before any promotion. Full procedure, JSON template, and candidate contract live in `references/findings-staging.md` and `references/artifact-contract.md`.

**Judgment calls when staging:**
- Gemini flags "unprompted commit" as HIGH -- false positive, global CLAUDE.md authorizes auto-commit
- `done_with_denials` status is NOT a failure -- it's a constitutional approval gate
- "Agent paused before executing" -- rubber-stamp approvals are intentional oversight, not sycophancy
- Promotion criteria: recurs 2+ sessions, not already covered, checkable predicate or architectural change
- Novel high-severity findings can be promoted immediately (don't wait for recurrence)
- If the item is not promotable, leave it in `candidates.jsonl` with an explicit state instead of forcing a log entry.

### Step 4: Summary

Report to user:
- Sessions analyzed: N
- Shape anomalies detected: N
- Signals staged: N
- Candidates staged: N (by category)
- Ready for promotion: N (2+ recurrences)
- New failure modes discovered: N
- Proposed fixes: list

Write the operator summary to `digest.md`. Only write `improvement-log.md` entries for promoted candidates that pass the gates in `references/artifact-contract.md`.

### Promotion Sink (`improvement-log.md`, only after promotion)

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

Treat this as a narrower signal source over the same pipeline:
deterministic extraction -> `signals.jsonl` -> optional classification -> `candidates.jsonl` -> promotion check.

---

## Mode: architecture

Creative architectural review -- find better abstractions, missing tools, repeated workflows that should be pipelines, cross-project patterns that should be shared infra. Pattern types in `lenses/architectural-patterns.md`.

**Mindset:** The best proposals are ones nobody asked for. A pattern in 3 sessions is coincidence. A pattern in 8 sessions across 3 projects is an abstraction waiting to be born.

Parse `$ARGUMENTS` for days (default 1), project filter, focus area. `--quick` = phases 1-2 only.

### Phase 1: Gather & Compress

Run shared transcript extraction. Extract from all active projects (meta, intel, selve, genomics, arc-agi) unless `--project` filters. Merge into `$ARTIFACT_DIR/all.md`. Verify <500KB.

Run shape pre-filter. Note anomalous sessions for priority analysis.

### Phase 2: Pattern Extraction (Gemini)

Dispatch to Gemini 3.1 Pro for structured pattern extraction. Full prompt in `references/gemini-prompt.md`. Use the shared dispatch helper, not raw CLI subprocess calls.

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
OBSERVE_PROJECT_ROOT="${OBSERVE_PROJECT_ROOT:-$HOME/Projects/agent-infra}"
ARTIFACT_DIR="${OBSERVE_ARTIFACT_ROOT:-$OBSERVE_PROJECT_ROOT/artifacts/observe}"
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

Dispatch raw classification + transcripts to Gemini 3.1 Pro via the shared dispatch wrapper. Read both files, concatenate with the prompt below, and call the wrapper (same pattern as sessions mode dispatch). For each non-NEW_AGENCY pattern, Gemini should determine:
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

### Step 4: Review and Stage

1. Read Gemini output critically -- it may hallucinate session details
2. Cross-check specific claims against raw JSON and transcripts
3. Stage verified items into `candidates.jsonl` with explicit state transitions
4. Write the human-readable summary to `"$ARTIFACT_DIR/digest.md"`
5. Promote to `"$OBSERVE_PROJECT_ROOT/improvement-log.md"` only when the canonical gates pass

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

### Phase 0: Idempotency Check

Before analyzing, check for existing retro artifacts for this session:

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
EXISTING=$(find "$OBSERVE_PROJECT_ROOT/artifacts/session-retro" -maxdepth 1 -name "$(date +%Y-%m-%d)-${SID}-*.json" 2>/dev/null | wc -l | tr -d ' ')
```

If EXISTING > 0 and `--force` was NOT passed: report "Already retro'd ({EXISTING} artifact(s) exist for session {SID} today). Use --force to re-analyze." and stop. This prevents diminishing-returns loops (5 retros on the same session observed, each adding zero new findings after the 2nd).

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
1. Review `"$ARTIFACT_DIR/candidates.jsonl"` for existing candidate matches and prior state transitions
2. Search `"$OBSERVE_PROJECT_ROOT/improvement-log.md"` only for already-promoted parallels: `grep -i "KEYWORD" "$OBSERVE_PROJECT_ROOT/improvement-log.md" | head -5`
3. Match existing entry -> mark "RECURRING: matches entry from YYYY-MM-DD"
4. Check if hook/rule/skill already addresses this -> note it

### Phase 4: Output

Use template from `lenses/retro-reflection.md`.

### Phase 5: Persist Findings

Write findings as JSON to `"$OBSERVE_PROJECT_ROOT/artifacts/session-retro/"`:

```bash
mkdir -p "$OBSERVE_PROJECT_ROOT/artifacts/session-retro"
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
```

Write `{date}-{SID}-manual.json` with:
```json
{"findings": [{"category": "...", "summary": "...", "severity": "high|medium|low", "evidence": "...", "project": "...", "proposed_fix": "..."}], "source": "manual-retro"}
```

---

## Model Selection for Dispatch

Default: Gemini 3.1 Pro (cheapest 1M context, good at pattern extraction). Use GPT-5.4 at medium effort for formal/quantitative analysis or when Gemini rate-limits. Route both through the shared dispatch helper. See `/model-guide` for detailed routing.

```python
from pathlib import Path
from shared.llm_dispatch import dispatch
# Gemini (default — pattern extraction, large context)
r = dispatch(profile="deep_review", prompt="...", context_text="...", output_path=Path("/tmp/observe.md"))
# GPT-5.4 medium effort (formal analysis, fact verification)
r = dispatch(profile="gpt_general", prompt="...", context_text="...", output_path=Path("/tmp/observe-gpt.md"))
```

## Notes

- Transcript sources (BOTH must be extracted and concatenated into dispatch context):
  - Claude Code JSONL at `~/.claude/projects/-Users-alien-Projects-{project}/`
  - Codex CLI at `~/.codex/state_5.sqlite` + rollout JSONL (reads project by `cwd` match)
- Codex runs alongside Claude Code on the same project; dropping it silently loses ~50% of the signal
- Preprocessor strips thinking blocks and base64 content
- Gemini 3.1 Pro at ~$0.001/query cached -- cheap enough to run frequently

$ARGUMENTS
