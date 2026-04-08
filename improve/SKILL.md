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

### Step 3: Pattern Analysis

Analyze the transcripts and tool sequence data directly. For each repeated pattern:
- Classify as SKILL candidate (multi-step, judgment needed) or MCP TOOL candidate (deterministic, reusable)
- Note: pattern, frequency, current cost, trigger, parameters, skeleton
- Only patterns appearing 2+ times across different sessions. Max 7 candidates. Rank by frequency x complexity saved.

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
