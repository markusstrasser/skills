---
name: design-review
description: "Creative architectural review of agent sessions — finds better abstractions, missing tools, repeated workflows → pipelines, cross-project patterns → shared infra. Dispatches to Gemini for pattern extraction, uses Claude for creative synthesis. NOT anti-pattern detection (session-analyst) or wasted supervision (supervision-audit)."
user-invocable: true
context: fork
argument-hint: "[--days N] [--project PROJECT] [--focus AREA] [--quick]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - Agent
effort: high
---

# Design Review

## Current Environment
`!echo "Date: $(date +%Y-%m-%d) | CWD: $(basename $PWD) | Sessions (3d): $(find ~/.claude/projects -name '*.jsonl' -mtime -3 -size +10k 2>/dev/null | wc -l | tr -d ' ') | Skills: $(ls ~/Projects/skills/ | wc -l | tr -d ' ') | Hooks: $(grep -c '"command"' ~/.claude/settings.json 2>/dev/null)"`

You are an architectural reviewer. Your job: read what agents and users **actually do** across sessions, then find the design that wants to emerge. You propose architecture — you don't judge behavior (session-analyst) or flag wasted supervision (supervision-audit).

**Mindset:** The best proposals are ones nobody asked for. A pattern that appears in 3 sessions is a coincidence. A pattern that appears in 8 sessions across 3 projects is an abstraction waiting to be born.

## Phase 1: Gather & Compress Transcripts

Parse `$ARGUMENTS` for days (default 3), project filter, focus area, and effort level (--quick = phases 1-2 only).

### 1a. Structural Pre-Filter

Identify which sessions are worth deep analysis:

```bash
# Shape anomaly detection — flags sessions with unusual tool patterns
uv run python3 ~/Projects/meta/scripts/session-shape.py --days {DAYS} {--project PROJECT if specified}
```

Note anomalous sessions. These get priority in Phase 2.

### 1b. Extract Transcripts

Use the **existing** extractors — don't reinvent:

```bash
# Claude Code sessions — strips thinking blocks, base64, compresses tool results
python3 ~/Projects/skills/session-analyst/scripts/extract_transcript.py {PROJECT} --sessions {N} --output ~/Projects/meta/artifacts/design-review/claude.md

# Codex sessions (if any exist)
python3 ~/Projects/skills/session-analyst/scripts/extract_codex_transcript.py {PROJECT} --sessions {N} --output ~/Projects/meta/artifacts/design-review/codex.md 2>/dev/null || true
```

Run per-project. For `--days 3` default, extract from: meta, intel, selve, genomics, arc-agi.

Merge all outputs into `~/Projects/meta/artifacts/design-review/all.md`. Verify size is <500KB (Gemini 3.1 Pro handles this easily within 1M context).

## Phase 2: Pattern Extraction (Gemini 3.1 Pro)

Dispatch compressed transcripts to Gemini for **structured pattern extraction**. Gemini 3.1 Pro has the best abstract pattern recognition (ARC-AGI-2 77.1%) and 1M native context — ideal for cross-session pattern matching.

**Critical:** Gemini's output is DATA, not conclusions. It extracts patterns; YOU (Claude) do the creative synthesis in Phase 3. Don't ask Gemini to propose architecture.

```bash
llmx -p google -m gemini-3.1-pro-preview -f ~/Projects/meta/artifacts/design-review/all.md "$(cat <<'PROMPT'
You are extracting STRUCTURAL PATTERNS from agent session transcripts. Output structured findings, not prose.

For each pattern found, output this exact JSON-like format (one per finding):

### PATTERN: [short name]
- **Type:** WORKFLOW_REPEAT | MANUAL_COORDINATION | REINVENTED_LOGIC | CROSS_PROJECT | DECISION_REVISITED | TOOL_GAP
- **Frequency:** [N occurrences across M sessions]
- **Sessions:** [list session ID prefixes where observed]
- **Evidence:** [verbatim quotes from user messages or tool sequences, max 3 lines each]
- **Tool sequence:** [if WORKFLOW_REPEAT: the repeated tool call pattern]
- **User action:** [if MANUAL_COORDINATION: what the user typed to coordinate]
- **Projects:** [which projects involved]

Pattern types to look for:

1. WORKFLOW_REPEAT: Same sequence of 3+ tool calls appearing in 2+ sessions. Example: Read → Grep → Edit → Bash(git commit) appearing in every bug-fix session.

2. MANUAL_COORDINATION: User acting as message bus — typing transitions like "now take that output and...", "check if X was updated after Y", "in the other project, do Z". The user is doing work the system should do.

3. REINVENTED_LOGIC: Agent builds the same function/query/check/transform in multiple sessions. Copy-paste across sessions = missing shared abstraction.

4. CROSS_PROJECT: Similar work patterns across different projects suggesting shared infrastructure. Example: every project does the same "read CLAUDE.md, check rules, grep for X" dance.

5. DECISION_REVISITED: Same design question debated in multiple sessions. Sign of underdocumented or wrong prior decision.

6. TOOL_GAP: Agent attempts something repeatedly with workarounds, suggesting a missing tool. Example: parsing JSON with sed because no jq MCP tool exists.

IMPORTANT:
- Include VERBATIM evidence (exact user messages, exact tool names). I will verify these.
- Only include patterns that appear 2+ times. Single occurrences are noise.
- Do NOT propose solutions — just extract patterns.
- If you find fewer than 3 patterns, that's fine. Don't fabricate.
- Output ONLY the patterns, no preamble or summary.
PROMPT
)"
```

Save Gemini output to `~/Projects/meta/artifacts/design-review/patterns.md`.

### 2b. Verify Gemini Claims

**Gemini WILL hallucinate session details.** For every pattern Gemini reports:
1. Check the cited session IDs actually exist
2. Verify the quoted user messages appear in the transcript
3. Confirm the tool sequences match reality

Drop any finding where the evidence doesn't verify. Note verification status: `VERIFIED` or `DROPPED:reason`.

## Phase 3: Creative Synthesis (Claude — You)

This is where the value lives. Gemini found patterns; now YOU find the architecture.

### 3a. Cross-Reference Existing Infrastructure

Before generating proposals, check what already exists. This prevents proposing things that are already built:

```bash
# Existing skills
ls ~/Projects/skills/

# Existing hooks (count by event type)
python3 -c "import json; s=json.load(open('$HOME/.claude/settings.json')); [print(f'{k}: {sum(len(g[\"hooks\"]) for g in v)}') for k,v in s.get('hooks',{}).items()]"

# Meta backlog items
grep '^\- \[' ~/Projects/meta/CLAUDE.md | head -20

# Improvement log (recent)
tail -50 ~/Projects/meta/improvement-log.md

# Active pipelines
ls ~/Projects/meta/pipelines/
```

### 3b. Divergent Ideation

For each verified pattern, generate **multiple** architectural responses — not just the obvious one. Use these techniques (from divergent-thinking research, LiveIdeaBench-validated):

**Denial cascade:** For each pattern, ask: "What if we COULDN'T use hooks/skills/pipelines? What would we build instead?" Then: "What if we couldn't use any LLM? What deterministic solution exists?" The constraint forces novel mechanisms.

**Cross-domain forcing:** For each pattern, name an analogous problem in a completely different domain (logistics, biology, compiler design, game theory). What solution exists there? Can it transfer?

**Inversion:** Instead of "how do we automate X?", ask "what if we made X unnecessary?" Can we restructure so the coordination/repetition never arises?

Generate **at least 3 genuinely different approaches** per pattern. Different mechanisms, not parameter variations. Mark your top pick but preserve the others.

### 3c. Convergent Selection

For each pattern, select the best proposal using these filters:
1. **Already exists?** Check Phase 3a results. Mark as `KNOWN:location` and skip.
2. **Bitter-lesson-proof?** Will a better model make this unnecessary? If yes, build only if it's cheap (<30 min).
3. **Reversible?** Prefer hooks (removable) over CLAUDE.md rules (sticky) over architectural changes (costly).
4. **Cross-project leverage?** A tool used by 5 projects beats one used by 1.
5. **Evidence of need?** 2 sessions = weak. 5+ sessions = strong. 10+ = urgent.

## Phase 4: Structured Output

For each surviving proposal:

```markdown
### [TYPE] Proposal Name

**Pattern:** What was observed [sessions: list]
**Frequency:** N occurrences across M sessions, K projects
**Current cost:** Estimated minutes/week of human or agent time
**Approach considered:**
1. [Selected approach] — why selected
2. [Alternative A] — why not (preserve for reference)
3. [Alternative B] — why not
**Proposal:** What to build (hook? skill? pipeline? MCP tool? script? justfile command?)
**Implementation sketch:**
```pseudocode
# 5-15 lines showing the core mechanism
```
**Blast radius:** Which projects/workflows affected
**Reversibility:** easy (hook/script) | medium (skill/pipeline) | hard (architectural)
**Status:** NEW | KNOWN:location
**Priority:** (weekly_minutes_saved × project_count) / implementation_hours
**Wild card?:** [yes/no — at least one proposal must challenge a current assumption]
```

Sort by priority descending.

## Phase 5: Write Output

Write to `~/Projects/meta/artifacts/design-review/YYYY-MM-DD.md`.

```bash
mkdir -p ~/Projects/meta/artifacts/design-review
```

Include a header:

```markdown
# Design Review — YYYY-MM-DD
**Sessions analyzed:** N across K projects (DAYS days)
**Patterns extracted:** N (Gemini), M verified
**Proposals:** N (P new, Q known)
**Top proposal:** [name] — estimated [X] min/week saved
**Wild card:** [name]
```

**Do NOT:**
- Implement anything — this is a review, not execution
- Write to improvement-log.md (that's session-analyst's job)
- Modify the constitution or GOALS.md
- Propose things already in the meta backlog without marking KNOWN

**DO:**
- Include at least one wild card that challenges a current architectural assumption
- Name the system's trajectory — what design is trying to emerge?
- Flag the single highest-leverage abstraction (the 80/20)

## Effort Scaling

| Mode | Trigger | Sessions | Phases | Model budget |
|------|---------|----------|--------|-------------|
| Quick | `--quick` or `/loop` | ~10 (1-2 days) | 1-2 only, bullet output | ~$0.10 (Gemini only) |
| Standard | default | ~25 (3 days) | Full 1-5 | ~$0.50 |
| Deep | `--days 7+` | ~50+ (7 days) | Full + cross-model review | ~$2.00 |

**Loop mode:** When invoked via `/loop`, use quick mode. Output patterns as JSONL (one per line) to the rolling patterns file:

```bash
PATTERNS_FILE="$HOME/Projects/meta/artifacts/design-review/patterns.jsonl"
mkdir -p "$(dirname "$PATTERNS_FILE")"
```

For each pattern found, append one JSON line:
```json
{"ts": "2026-03-17T14:00:00Z", "type": "WORKFLOW_REPEAT", "name": "research-verify-commit", "frequency": 4, "sessions": ["abc123", "def456"], "projects": ["intel", "meta"], "evidence": "user typed 'now verify those claims'...", "verified": true}
```

After writing patterns, check timestamp of last synthesis:
```bash
SYNTH_FILE="$HOME/Projects/meta/artifacts/design-review/last-synthesis.md"
```
If `last-synthesis.md` is >24h old or doesn't exist, AND there are 5+ new patterns since last synthesis, trigger a full synthesis (Phases 3-5) and write to `artifacts/design-review/YYYY-MM-DD-synthesis.md`. The synthesis reads ALL patterns from the last 7 days, deduplicates by name, counts recurrences, and produces ranked proposals.

The synthesis file is picked up by `propose-work.py` in the morning brief — proposals with 3+ recurrences surface as work items.

**Delta detection:** Check `artifacts/design-review/last-synthesis.md` mtime for timestamp of last run. Only analyze sessions modified after that timestamp.

## Accrual → Synthesis → Execute Loop

```
Quick runs (every 4h)
  → patterns.jsonl (append-only, rolling)
     → Daily synthesis (auto-triggered when 5+ new patterns + >24h since last)
        → YYYY-MM-DD-synthesis.md (ranked proposals)
           → propose-work.py morning brief (surfaces top proposals)
              → Human approves → orchestrator task or interactive session
```

**Recurrence is the quality signal.** A pattern seen once is noise. Seen 3 times across 2 projects = proposal. Seen 5+ times = urgent. The patterns.jsonl file is the institutional memory of what the system wants to become.

**Pruning:** Patterns older than 30 days are archived to `patterns-archive.jsonl`. Implemented proposals are marked `"status": "implemented"`.

**Implementation tracking:** After writing patterns, check implementation status:
```bash
for pattern in $(cat artifacts/design-review/patterns.jsonl | python3 -c "import sys,json; [print(json.loads(l).get('name','')) for l in sys.stdin]"); do
  if git log --oneline --since="30 days ago" --grep="$pattern" | head -1 | grep -q .; then
    echo "IMPLEMENTED: $pattern"
  fi
done
```
Mark implemented patterns in patterns.jsonl with `"status": "implemented"`.

## Known Limitations

- Gemini hallucination rate on session details: ~20-30%. Phase 2b verification is mandatory.
- Codex transcript extraction requires `~/.codex/state_5.sqlite` — may not exist if Codex hasn't been used.
- Pattern extraction degrades past ~80 sessions in one Gemini call. For deep mode, batch by project.
- Cross-project patterns are harder to detect when sessions are batched by project. The merged file in Phase 1b helps but isn't perfect.

$ARGUMENTS
