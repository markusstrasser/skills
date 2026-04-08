---
name: harvest
description: "Cross-artifact improvement harvester — gathers retro findings, design-review patterns, session-analyst outputs, suggest-skill candidates, user #f feedback, and git corrections from recent days. Deduplicates against improvement-log and vetoed-decisions, synthesizes ranked infrastructure/tooling improvements. NOT session analysis (session-analyst) or architectural review (design-review) — those PRODUCE artifacts, this CONSUMES them."
user-invocable: true
argument-hint: "[--days N] [--focus hooks|skills|scripts|architecture|rules|all]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
effort: medium
---

# Harvest

Cross-artifact improvement harvester. Reads the last N days of analysis artifacts, user feedback, and git corrections, then synthesizes a ranked list of infrastructure/tooling improvements — deduplicated against what's already tracked or vetoed.

**You consume artifacts. You don't produce analysis.** Session-analyst, design-review, retro, and suggest-skill produce the raw findings. You aggregate, deduplicate, rank, and surface what fell through the cracks.

## Phase 0: Parse & Setup

Parse `$ARGUMENTS`:
- `--days N` (default: 3)
- `--focus` filter: `hooks`, `skills`, `scripts`, `architecture`, `rules`, `all` (default: `all`)

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
ARTIFACT_DIR="$HOME/Projects/meta/artifacts/harvest"
mkdir -p "$ARTIFACT_DIR"
DATE=$(date +%Y-%m-%d)
OUTFILE="${ARTIFACT_DIR}/${DATE}-${SID}-harvest.md"
```

Compute the date cutoff for the window:
```bash
# macOS date
CUTOFF=$(date -v-${DAYS}d +%Y-%m-%d)
```

## Phase 1: Load Dedup Baselines

Read these two files in full — they define what's already known:

1. **`improvement-log.md`** — Extract all finding summaries and their statuses (proposed/implemented/in-progress). These are the "already tracked" set. Pay attention to `[x] implemented` vs `[ ] proposed`.

2. **`.claude/rules/vetoed-decisions.md`** — Extract all vetoed proposals. These are the "already rejected" set. Do NOT re-propose anything on this list.

Build two mental lists:
- `TRACKED`: summary + status for each improvement-log entry
- `VETOED`: each vetoed decision summary

## Phase 2: Harvest Structured Artifacts

For each source type, glob within the date window, read each file, extract actionable items.

### 2a. Session Retros (`artifacts/session-retro/`)

```bash
# Find retros within date window
find ~/Projects/meta/artifacts/session-retro/ -name "${CUTOFF//-/}*" -o -newer ~/Projects/meta/artifacts/session-retro/sentinel 2>/dev/null
```

Better: glob for files matching `YYYY-MM-*` patterns within the window.

- **JSON retros** (`.json`): Parse `findings[]` array. Each has: `category`, `summary`, `severity`, `evidence`, `proposed_fix`, `project`.
- **Markdown retros** (`.md`): Look for `### [FINDING-` sections with structured fields.

For each finding, extract:
- `summary` (one-line)
- `category` (TOKEN_WASTE, SYSTEM_DESIGN, BUILD_THEN_UNDO, WRONG_ASSUMPTION, etc.)
- `severity`
- `proposed_fix` (the actionable part)
- `source_file` (provenance)

### 2b. Design Reviews (`artifacts/design-review/`)

Glob for files within date window. Prioritize synthesis files (`*-synthesis.md`, `*-cross-platform.md`) over raw pattern files.

Extract:
- **Findings** (sections starting with `### F`): summary, severity, recommendation
- **Proposals** (sections with `**Proposal:**` or `**Recommendation:**`): the suggested change
- Skip findings already marked as "Already exists" or with struck-through recommendations

### 2c. Session Analyst Findings (`artifacts/session-analyst/`)

Glob for `*.json` files within date window.

Parse `findings[]` arrays. Each has: `category`, `summary`, `severity`, `evidence`, `root_cause`, `proposed_fix`, `session_uuid`, `project`.

### 2d. Suggest-Skill Outputs (`artifacts/suggest-skill/`)

Glob for files within date window.

Extract skill candidates — typically structured as sections with frequency, ROI estimate, and proposed skill name.

## Phase 3: Harvest Unstructured Signals

### 3a. User `#f` Feedback

Search recent session transcripts for `#f` tags:

```bash
# Find recent session files
find ~/.claude/projects/ -name '*.jsonl' -mtime -${DAYS} -size +10k 2>/dev/null | head -20
```

For each, grep for `"#f"` in user messages. Extract the feedback text after `#f`. These are ground-truth corrections — highest signal.

**Use the collocated extraction script:**
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/extract_user_tags.py --days ${DAYS} --tag f
```

### 3b. Git Corrections

```bash
# Governance commits with Evidence trailers (corrections that were important enough to document)
git -C ~/Projects/meta log --since="${CUTOFF}" --format='%h %s' --grep='Evidence:' -- 

# Commits touching rules, hooks, CLAUDE.md (behavioral corrections)
git -C ~/Projects/meta log --since="${CUTOFF}" --oneline -- .claude/rules/ improvement-log.md

# Same for skills repo
git -C ~/Projects/skills log --since="${CUTOFF}" --oneline -- '*/SKILL.md' hooks/
```

These show what was already fixed. Look for **patterns** — if 3 commits fix hook edge cases, that's a signal that hook testing infrastructure is weak.

### 3c. Daily Memory Logs (optional)

Check `~/.claude/projects/-Users-alien-Projects-meta/memory/` for `YYYY-MM-DD.md` files within the window. Scan for notes about issues, workarounds, or ideas.

## Phase 4: Deduplicate & Classify

For each harvested item:

1. **Check against TRACKED list.** If the summary matches an existing improvement-log entry:
   - If status is `implemented` → skip (done)
   - If status is `proposed` → note as "reinforced" (appeared again, still unimplemented)
   - If status is `in-progress` → skip (being worked on)

2. **Check against VETOED list.** If the item matches a vetoed decision → skip, but note if the new evidence changes the calculus (e.g., a vetoed tool now has 10x more usage).

3. **Classify by improvement type:**
   - `hook` — new hook, hook fix, hook promotion/demotion
   - `skill` — new skill, skill fix, skill gap
   - `script` — new script, script fix, script enhancement
   - `architecture` — structural change, new abstraction, system redesign
   - `rule` — new rule, rule update, rule in CLAUDE.md or rules/
   - `config` — settings.json, launchd, MCP config changes

4. **Apply `--focus` filter** if specified (skip items outside the focus category).

5. **Count cross-source recurrence.** An item appearing in a retro AND a design review is stronger than one appearing in only one source. Track which sources mention each theme.

## Phase 5: Rank

Score each surviving item:

```
priority = recurrence_count × severity_weight × novelty_bonus
```

Where:
- `severity_weight`: high=3, medium=2, low=1
- `recurrence_count`: number of distinct sources mentioning this theme (1-6)
- `novelty_bonus`: 1.5 if completely new (not in improvement-log at all), 1.0 if reinforcing an unimplemented proposal, 0.5 if tangentially related to existing work

Sort descending by priority.

## Phase 6: Output

Write to `$OUTFILE` with this structure:

```markdown
# Harvest — {DATE}

**Window:** {CUTOFF} to {DATE} ({DAYS} days)
**Focus:** {FOCUS}
**Sources scanned:** N retros, N design-reviews, N session-analyst, N suggest-skill, N #f tags, N git corrections
**Items found:** N total → N after dedup → N after focus filter

## Summary

| # | Improvement | Type | Sources | Recurrence | Severity | Status |
|---|------------|------|---------|------------|----------|--------|
| 1 | ... | hook | retro, design-review | 3 | high | NEW |
| 2 | ... | skill | suggest-skill, #f | 2 | medium | NEW |
| 3 | ... | rule | retro | 1 | medium | REINFORCED (proposed 2026-03-30) |

## Details

### 1. [Improvement title]

**Type:** hook | skill | script | architecture | rule | config
**Priority:** {score} (recurrence={N} × severity={S} × novelty={B})
**Status:** NEW | REINFORCED | VETOED-BUT-REVISIT

**Sources:**
- retro `artifacts/session-retro/2026-04-02-manual.json`: "{finding summary}"
- design-review `artifacts/design-review/2026-04-02-synthesis.md`: "{recommendation}"
- #f feedback (session abc123): "{user feedback text}"

**Proposed action:** {concrete next step — what to build/change/configure}

**Dedup notes:** {what was checked — "not in improvement-log, not in vetoed-decisions" or "reinforces proposed finding from 2026-03-30"}

---
### 2. ...
```

## Anti-Patterns

- **Don't re-analyze sessions.** Session-analyst and design-review already did that. You read their output.
- **Don't propose vetoed items.** Unless you have concrete new evidence that changes the calculation, in which case say so explicitly.
- **Don't inflate recurrence.** Two mentions in the same retro artifact = 1 source, not 2. Count distinct source types.
- **Don't skip the dedup.** The whole point of this skill is surfacing what's NOT already tracked. If everything you find is already in improvement-log, say so — that's a valid (good) result.
- **Don't propose "improvements" that are just maintenance.** This skill finds infrastructure/tooling/architecture changes, not "update this dependency" or "fix this typo."

## When to Run

- After a multi-day work sprint (end of week)
- After running session-analyst + design-review + retro (harvest their output)
- Before planning the next work cycle (what should get built?)
- On `/loop` schedule with steward (if desired)

## Relationship to Other Skills

```
session-analyst ──→ artifacts/session-analyst/*.json ──┐
design-review ────→ artifacts/design-review/*.md ──────┤
retro ────────────→ artifacts/session-retro/*.json ────┼──→ harvest ──→ artifacts/harvest/*.md
suggest-skill ────→ artifacts/suggest-skill/*.md ──────┤
user #f feedback ─→ session transcripts ───────────────┤
git corrections ──→ git log ───────────────────────────┘
```
