---
name: maintain
description: Rotating maintenance — database freshness, bio-verify audits, deferred item probes, pipeline cross-checks. Run with /loop 30m. Writes to CYCLE.md ## Maintenance and DECISIONS.md.
model: claude-sonnet-4-6
effort: low
---

# Maintain

You run on `/loop 30m`. Each tick you pick ONE maintenance task from the rotation, execute it, and log results. You coordinate with `/research-cycle` through shared files. **Never ask for input.**

## Live State

!`bash -c 'echo "=== DB FRESHNESS ==="; for db in ClinVar gnomAD PharmCAT CPIC; do f=$(find "$(pwd)/databases/" -iname "*${db}*" -type f 2>/dev/null | head -1); if [ -n "$f" ]; then days=$(( ($(date +%s) - $(stat -f%m "$f" 2>/dev/null || stat -c%Y "$f" 2>/dev/null || echo 0)) / 86400 )); echo "  $db: ${days}d old ($f)"; else echo "  $db: not found"; fi; done; echo "=== LAST MAINTENANCE ==="; tail -5 "$(pwd)/MAINTENANCE.log" 2>/dev/null || echo "(no log yet)"; echo "=== SCRIPTS ==="; ls scripts/modal_*.py 2>/dev/null | wc -l | tr -d " "; echo " modal scripts"' 2>&1 | head -30`

## Each Tick: Pick ONE Task

Read `MAINTENANCE.log` to see what was done recently. Pick the highest-priority task that hasn't been run within its cadence window. Execute it. Log the result.

### Task Rotation

| Task | Cadence | How | Skills/Tools |
|------|---------|-----|-------------|
| **Database freshness** | Daily | Check file timestamps in `databases/`. Flag any >30d stale. If ClinVar stale, check for new release via Exa. | Exa search |
| **Bio-verify audit** | Rotate: 1 script/tick | Pick next `scripts/modal_*.py` not audited in 14d. Run `/bio-verify` on it. | `/bio-verify` skill |
| **Deferred probe** | Weekly per item | Read CYCLE.md deferred items. HTTP-probe any URLs. Check release pages. | `requests` / Exa |
| **Cross-check outputs** | Daily | Pick a random T1/T2 variant from review packets. Query biomedical MCP. Compare. | `mcp__biomedical__*` |
| **Research memo staleness** | Weekly | Check if any ACTIVE research memos have related files changed since memo date. | `git log` + grep |
| **Benchmark drift** | After pipeline changes | Run `noncoding_benchmark.py benchmark` if any scoring script changed in last 7d. | Pipeline scripts |

### Running a Task

**Preferred: inline** (maintenance tasks are fast, focused, don't need subagent context).

For bio-verify, invoke the skill:
```
Skill(skill="bio-verify", args="scripts/modal_{target}.py")
```

For deferred probes, probe directly:
```bash
uv run python3 -c "import requests; r = requests.get('{url}', timeout=10); print(r.status_code, r.headers.get('content-type',''))"
```

For cross-checks, use biomedical MCP tools directly.

### Logging

Append one line per task to `MAINTENANCE.log` (project root):
```
2026-03-23T12:00 | freshness | ClinVar 12d OK, gnomAD 45d STALE | action: flag in DECISIONS.md
2026-03-23T12:30 | bio-verify | modal_vep.py | 3 findings, 0 critical
2026-03-23T13:00 | deferred-probe | G-VEP phenomeportal.org | still 404
```

### Writing to Shared Files

**CYCLE.md `## Maintenance Log`** — append a one-line summary per task. Research-cycle reads this to know what's been checked.

**DECISIONS.md** — append when maintenance finds something that needs human input:
```markdown
### [maintain] gnomAD is 45 days stale (2026-03-23)
gnomAD v4.1 files last downloaded 2026-02-06. v4.2 may be available.
**Options:** (a) download v4.2 (~25GB), (b) defer until gnomAD v5
**Your call:** mark chosen option with [x]
- [ ] Download v4.2
- [ ] Defer to v5
```

### What NOT to Do

- Don't modify pipeline code. Maintenance observes and reports.
- Don't run full pipeline stages. Cross-checks use MCP or small queries.
- Don't duplicate research-cycle's work. If CYCLE.md already has a discovery about a stale DB, skip it.
- Don't ask for input. Write questions to DECISIONS.md.

## Operating Rules

1. **One task per tick.** Pick the most overdue task.
2. **Log everything.** MAINTENANCE.log is the audit trail.
3. **Report in 1-2 lines.** Task, result, next scheduled.
4. **Coordinate via files.** Read CYCLE.md before acting. Don't re-discover what research-cycle found.
5. **Propose, don't fix.** Findings go to DECISIONS.md or CYCLE.md gaps. Fixes are research-cycle's job.

$ARGUMENTS
