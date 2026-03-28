---
name: maintain
description: Rotating maintenance — database freshness, bio-verify audits, deferred item probes, code-quality scans, pipeline cross-checks. Run with /loop 30m. Writes to MAINTAIN.md and DECISIONS.md.
model: claude-haiku-4-5-20251001
effort: low
---

# Maintain

You run on `/loop 30m`. Each tick you pick ONE maintenance task from the rotation, execute it, and log results. You own the SWE quality lane — separate from `/research-cycle` (growth lane). **Never ask for input.**

## Live State

!`bash -c 'echo "=== DB FRESHNESS ==="; for db in ClinVar gnomAD PharmCAT CPIC; do f=$(find "$(pwd)/databases/" -iname "*${db}*" -type f 2>/dev/null | head -1); if [ -n "$f" ]; then days=$(( ($(date +%s) - $(stat -f%m "$f" 2>/dev/null || stat -c%Y "$f" 2>/dev/null || echo 0)) / 86400 )); echo "  $db: ${days}d old ($f)"; else echo "  $db: not found"; fi; done; echo "=== LAST MAINTENANCE ==="; tail -5 "$(pwd)/MAINTENANCE.log" 2>/dev/null || echo "(no log yet)"; echo "=== MAINTAIN STATE ==="; if [ -f "$(pwd)/MAINTAIN.md" ]; then findings=$(grep -c "^\- \*\*M[0-9]" "$(pwd)/MAINTAIN.md" 2>/dev/null || echo 0); queued=$(grep -c "\[queued\]" "$(pwd)/MAINTAIN.md" 2>/dev/null || echo 0); echo "  $findings findings, $queued queued"; else echo "  (no MAINTAIN.md — first run, create from template)"; fi; echo "=== DEFERRED ==="; grep -c "revisit:" "$(pwd)/MAINTAIN.md" 2>/dev/null || echo "0"; echo " deferred items"; echo "=== SCRIPTS ==="; ls scripts/modal_*.py 2>/dev/null | wc -l | tr -d " "; echo " modal scripts"' 2>&1 | head -30`

## Rate Limit Check

Before each tick:
```bash
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
```
If `CLAUDE_PROCS >= 6`: skip tasks that spawn subagents (bio-verify, subagent dispatch). For LLM-heavy analysis, route through `llmx chat -m gemini-3-flash-preview` (free via CLI). Most maintain tasks are tool-based (Exa, git, scripts) and work fine rate-limited.

## Each Tick: Pick ONE Task

Read `MAINTENANCE.log` to see what was done recently. Pick the highest-priority task that hasn't been run within its cadence window. Execute it. Log the result.

**Queue priority override:** If MAINTAIN.md `## Queue` has 3+ items, skip discovery tasks and focus on dispatching fixes (see Execution Model below).

### Task Rotation

| Task | Cadence | How | Skills/Tools |
|------|---------|-----|-------------|
| **Database freshness** | Daily | Check file timestamps in `databases/`. Flag any >30d stale. If ClinVar stale, check for new release via Exa. | Exa search |
| **Bio-verify audit** | Rotate: 1 script/tick | Run `just bio-verify-queue` to get the priority queue. Pick top item. Run `/bio-verify` on it. After completion, state auto-updates via `bio_verify_status.py --update`. | `/bio-verify` skill |
| **Deferred probe** | Only after `revisit` date | Read MAINTAIN.md `## Deferred` items. Only probe items whose `revisit: YYYY-MM-DD` date has passed. HTTP-probe URLs, check release pages. | `requests` / Exa |
| **Cross-check outputs** | Daily | Pick a random T1/T2 variant from review packets. Query biomedical MCP. Compare. | `mcp__biomedical__*` |
| **Research memo staleness** | Weekly | Check if any ACTIVE research memos have related files changed since memo date. | `git log` + grep |
| **Code quality scan** | Weekly | Run `/project-upgrade --quick` (diff-aware, Phase 0-2 only: findings, no execution). Append findings to MAINTAIN.md `## Findings` with IDs. | `/project-upgrade` skill |
| **Audit sweep** | Biweekly | Run `/dispatch-research quick sweep` (3-5 audits, stop at findings). Append findings to MAINTAIN.md `## Findings` with IDs. | `/dispatch-research` skill |
| **Benchmark drift** | After pipeline changes | Run `noncoding_benchmark.py benchmark` if any scoring script changed in last 7d. | Pipeline scripts |
| **Calibration canary** | Weekly | Run `uv run python3 ~/Projects/meta/scripts/calibration-canary.py --mode sampling --difficulty hard --runs 10 --backend llmx --model gpt-4o-mini`. Uses llmx backend (no Claude API credits needed). Check hard canary accuracy is 30-70% (if >90%, canary isn't hard enough). Compare with prior run in `~/.claude/epistemic-metrics.jsonl`. | Meta scripts |
| **Genomics canary gate** | After classification changes | Run `just canary` in genomics. Pre-commit hook catches this, but maintenance verifies the hook is working. | Genomics justfile |
| **Doc currency** | Weekly | Run `just check-codebase-map && just check-claude-md` in genomics. If stale, run `just regen-codebase-map`, update CLAUDE.md counts via `validate_claude_md.py --fix`, commit. Post-commit hook auto-regenerates codebase-map on significant drift, but this catches CLAUDE.md count staleness and minor map drift. | Justfile recipes |

### Running a Task

**Preferred: inline** (maintenance tasks are fast, focused, don't need subagent context).

For bio-verify, use the priority queue:
```bash
# Get the next file to verify
uv run python scripts/bio_verify_status.py --queue
```
Then invoke the skill on the top item:
```
Skill(skill="bio-verify", args="scripts/{top_item}.py")
```
After verification, update tracking (the bio-verify skill does this in Step 9):
```bash
uv run python scripts/bio_verify_status.py --update scripts/{file}.py 2026-03-24 0
```

For deferred probes, probe directly:
```bash
uv run python3 -c "import requests; r = requests.get('{url}', timeout=10); print(r.status_code, r.headers.get('content-type',''))"
```

For cross-checks, use biomedical MCP tools directly.

### Execution Model

**Auto-fix deterministic, dispatch the rest.**

**Auto-fix (Haiku, inline):** Unused import removal (ruff --fix), stale version string update (when authoritative source is known). These have deterministic postconditions verifiable by lint/syntax check. Fix inline, verify with `ruff check`, commit, log to MAINTAIN.md `## Fixed`.

**Dispatch (Opus subagent):** Everything else — BROKEN_REFERENCE, DEAD_CODE, NAMING_INCONSISTENCY, HARDCODED, PATTERN_INCONSISTENCY, DUPLICATION, COUPLING, MISSING_SHARED_UTIL, ERROR_SWALLOWED, anything touching >1 file. Write to MAINTAIN.md `## Queue`, then dispatch:
```
Agent(
  prompt="Fix MAINTAIN.md queue item {id}: {description}. Files: {list}. Read the files, fix the issue, verify (run tests/lint), commit with [maintain] scope.",
  subagent_type="general-purpose",
  mode="bypassPermissions"
)
```
**Rate-limit gate:** Only dispatch subagent if `CLAUDE_PROCS < 4`. Otherwise, item stays queued for next tick.
**One dispatch per tick max** to prevent cascading waste.
**After subagent completes:** Update MAINTAIN.md item status from `[queued]` to `[fixed]` with commit hash.

### Logging

Append one line per task to `MAINTENANCE.log` (project root):
```
2026-03-23T12:00 | freshness | ClinVar 12d OK, gnomAD 45d STALE | action: flag in MAINTAIN.md
2026-03-23T12:30 | bio-verify | modal_vep.py | 3 findings, 0 critical
2026-03-23T13:00 | deferred-probe | G-VEP phenomeportal.org | still 404, revisit: 2026-04-06
2026-03-23T13:30 | dispatch | M003 BROKEN_REFERENCE | subagent spawned
```

### MAINTAIN.md Item IDs

Items get monotonic IDs: M001, M002, ... Find the highest existing ID and increment. Items move through statuses: `[new]` → `[queued]` (multi-file) or `[fixed]` (auto-fix) → `[fixed]` (after dispatch) or `[deferred]`.

### WIP Caps

- Max 5 unprocessed findings in MAINTAIN.md `## Findings`
- Max 3 queued items in `## Queue`
- If queue is full (3 items), halt discovery and focus on dispatching fixes
- If findings are full (5 items), skip writing new findings until existing ones are dispositioned

### Writing to Shared Files

**MAINTAIN.md** (project root) — the SWE quality lane state file. maintain owns this file. If it doesn't exist on first tick, create it from the template in `${CLAUDE_SKILL_DIR}/templates/MAINTAIN.md`.

**DECISIONS.md** — append when maintenance finds something that needs human context (informational — no approval checkboxes):
```markdown
### [maintain] gnomAD is 45 days stale (2026-03-23)
gnomAD v4.1 files last downloaded 2026-02-06. v4.2 may be available.
Options to consider: download v4.2 (~25GB) or defer until gnomAD v5.
```

| File | Owner | Others | Purpose |
|------|-------|--------|---------|
| `MAINTAIN.md` | maintain | project-upgrade writes; dispatch-research writes | SWE quality state |
| `MAINTENANCE.log` | maintain | human reads | Audit trail |
| `DECISIONS.md` | any skill appends | human reads | Informational |

### Deferred Item Management

- Deferred items in MAINTAIN.md have `revisit: YYYY-MM-DD`
- Only probe after that date (not every tick)
- If still deferred after 90 days: auto-move to end of `## Deferred` with note "stale — reopen on request"
- Update `revisit` date after each probe: +7 days for URLs, +30 days for blocked-on-platform items

### What NOT to Do

- Don't run full pipeline stages. Cross-checks use MCP or small queries.
- Don't duplicate research-cycle's work. Check MAINTAIN.md before acting.
- Don't ask for input. Write context to DECISIONS.md.
- Don't write to CYCLE.md. That's the growth lane (research-cycle's file).

## Error Recovery

If a task fails (bio-verify crashes, MCP timeout, probe hangs):
1. Log the error to MAINTENANCE.log with `| ERROR |`
2. Skip that task for this tick
3. Don't retry the same failing task consecutively
4. Continue to next tick with a different task

If a subagent dispatch fails:
1. Log the failure to MAINTENANCE.log
2. Keep the item in MAINTAIN.md `## Queue` (don't remove it)
3. Retry on next tick if rate-limit allows

## Operating Rules

1. **One task per tick.** Pick the most overdue task. Exception: queue-full triggers dispatch priority.
2. **Log everything.** MAINTENANCE.log is the audit trail.
3. **Report in 1-2 lines.** Task, result, next scheduled.
4. **Auto-fix deterministic, dispatch the rest.** Only fix what has a verifiable postcondition (ruff check passes). Everything else goes to an Opus subagent.
5. **Respect revisit dates.** Don't probe deferred items before their revisit date.
6. **Don't touch CYCLE.md.** Growth lane is separate.

$ARGUMENTS
