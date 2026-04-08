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

### Step 2: Analyze Transcripts

Analyze directly using the taxonomy in `lenses/behavioral-antipatterns.md` and grounding examples in `references/grounding-examples.md`. Read the coverage digest to avoid re-reporting known patterns.

For each session transcript:
1. Read the transcript
2. Score against the 20-item taxonomy
3. Flag any patterns that score above threshold

If transcripts exceed context, use the shape pre-filter output to prioritize flagged sessions and skip normal-profile ones.

### Step 3: Stage Findings

Validate findings against transcript evidence, check session UUIDs, save as JSON artifact. Full procedure and JSON template in `references/findings-staging.md`.

**Judgment calls when staging:**
- "Unprompted commit" is NOT an anti-pattern -- global CLAUDE.md authorizes auto-commit
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

### Phase 2: Pattern Extraction

Extract patterns directly from the transcripts using the pattern types in `lenses/architectural-patterns.md`. The prompt frame in `references/gemini-prompt.md` describes what to look for — use it as your analysis guide.

**Operational limits:**
- For `--days 7+` (>80 sessions): batch by project and analyze each batch separately.
- Cross-project patterns are harder to detect when batched by project — note this gap.

**Self-verify (mandatory):**
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

### Step 3: Synthesize

Read the raw classification JSON and transcripts directly. For each non-NEW_AGENCY pattern, determine:
1. Is it genuinely automatable? Some "corrections" are actually new information — filter those out.
2. What's the right fix type? (HOOK, RULE, DEFAULT, SKILL, ARCHITECTURAL)
3. How many times did it recur? Single occurrences are noise. 3+ is signal.
4. What would the fix look like? Be specific — hook pseudocode, rule text, or architectural sketch.

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

Don't propose fixes for things that are genuinely new agency. Don't propose rules for things already in CLAUDE.md. Rank by (occurrences x automation potential). If nothing is worth fixing, say so.

### Step 4: Review and Act

1. Cross-check findings against raw JSON and transcripts
2. For HIGH/MEDIUM priority findings:
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

## Notes

- Transcript source: `~/.claude/projects/-Users-alien-Projects-{project}/` (native Claude Code storage)
- Preprocessor strips thinking blocks and base64 content
- All analysis is direct (Claude 1M context). No external LLM dispatch needed.
- Codex transcript extraction requires `~/.codex/state_5.sqlite`

$ARGUMENTS
