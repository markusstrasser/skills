---
name: verify-before
description: "Know the true state before acting or diagnosing. Two modes: 'probe' (validate code/config on a tiny slice before full-scale run) and 'status' (query live ground truth before writing a status claim). Use when: about to launch an expensive pipeline, about to diagnose a remote/long-running job, about to claim something 'worked' or 'crashed' without verification, or the user asks for 'probe', 'dry run', 'check status', 'verify'. Promotes global rule #8 (Probe before build) and the ground-truth-first principle to architecture."
user-invocable: true
argument-hint: "[probe|status] [target]"
allowed-tools: [Read, Glob, Grep, Bash, Write]
effort: medium
---

# Verify Before

Architectural promotion of the "know the true state before acting" principle.
Counters two failure modes observed across phenome/genomics sessions:

1. **Pre-launch:** Deploying untested code to full datasets wastes $10–$50 and
   hours per failure. Agents improvise "probes" ad hoc, sometimes overwriting
   production baselines in the process.
2. **Pre-diagnosis:** Agents paraphrase raw logs and hallucinate status
   ("uptime 90m" when it's 10m, "job running fine" when it's crash-looping).
   The fix is fetching structured ground truth and citing it.

Two modes, same principle: **do not claim or commit before verifying.**

---

## Mode: probe

Validate pipeline math, logic, or environment on a representative slice before
full-scale execution.

### Phases

**1. Define the fixture.**
- Pick the smallest biologically/structurally valid slice (e.g., 10 LD blocks,
  25 SVs, 1 chromosome, 100 rows).
- Where it lives: `tests/fixtures/<task>/` or a volume path that is **not** the
  production output path.

**2. Isolate state.**
- Probe scripts write to `probe_results/`, `/tmp/<task>-probe/`, or a suffixed
  output path (e.g., `{base}.probe.tsv`). Never overwrite the full-run target.
- If using Modal volumes, use a dedicated `probe_*` prefix.

**3. Define the success criteria BEFORE running.**
- Numeric comparison: `np.allclose(probe, baseline, rtol=1e-6)` against a known
  reference.
- Structural: exact column set, dtype map, non-null counts.
- Cost extrapolation: probe cost × (full_size / probe_size). Report estimate.

**4. Run the probe. Diff against criteria. Only then scale up.**
- If the probe fails, the full run would too — cheaper diagnosis here.
- If the probe passes, scale up with concrete cost/time extrapolation.

### Cost of skipping

| Incident | Cost |
|---|---|
| int8 vs int32 overwriting production baseline | Near-miss, data loss avoided manually |
| PreMode Conda ABI mismatch on full run | ~45 min blind debugging |
| Full SBayesRC on broken MCMC config | Hours wasted + retry cost |

---

## Mode: status

Query live ground truth before asserting a remote/long-running job's state.

### The rule

> If you are about to write **"the job is running / crashed / completed / stalled"**
> and you have NOT fetched structured state in this turn, stop.
> Fetch first. Cite the structured fields.

### Ground-truth sources by target

| Target | Tool | Structured fields to cite |
|---|---|---|
| Modal app | `mcp__modal-triage__status(app_id)` | `is_running`, `uptime_seconds`, `verified_at` |
| Modal app + logs | `mcp__modal-triage__triage(app_id)` | `signals`, `tail_lines`, `verified_at` |
| Modal log pattern | `mcp__modal-triage__grep_logs(app_id, pattern)` | `match_count`, `matches` |
| DuckDB state | `mcp__duckdb__query(db_path, sql)` | row counts, `verified_at` implicit |
| Background bash | `BashOutput(bash_id)` | stdout/stderr tail with timestamps |
| launchd job | `launchctl list \| grep com.X` | PID, exit code, last run |
| Cron/orchestrator | `sqlite3 ~/.claude/orchestrator.db "SELECT * FROM v_queue"` | state column, updated_at |
| Git state | `git status --porcelain`, `git log -5 --oneline` | exact commit SHAs |
| Remote HTTP | `curl -sS -o /dev/null -w "%{http_code}\n" URL` | status code, not "looks up" |

### Anti-patterns

- **Paraphrasing logs.** "Looks like it OOM'd around the 3-hour mark." Wrong:
  cite `signals.cuda_oom` from triage, or say you didn't check.
- **Uptime guessing.** "It's been running for about 90 minutes." Wrong: cite
  `uptime_seconds` or don't claim uptime.
- **Status from staleness.** "The app list shows it deployed, so it's running."
  Wrong: `deployed` ≠ `is_running=true`; containers can crash-loop under a
  deployed app.
- **Asserting completion from no output.** "No errors in the last 20 lines, so
  it finished." Wrong: use `state == 'stopped'` + `stopped_at` to confirm.

### Pattern

```
# Before writing any status claim:
1. Call the structured tool (modal-triage / duckdb / BashOutput / etc.)
2. Extract the verified fields.
3. Write the claim with the verified value inline.

Example:
  "sven-sv (ap-iKJpvDa1) is_running=true, uptime_seconds=834,
   verified_at=2026-04-18T19:40Z. No fatal signals in last 80 lines."
```

---

## When NOT to use

- Trivial local scripts (<1 min, no remote state, no shared output path).
- Read-only exploration where failure is free.
- User has explicitly authorized a full-scale run without a probe.

## Relationship to other skills

- `/upgrade` — broader refactor workflow; `verify-before` is the narrow
  pre-launch / pre-diagnosis contract.
- `/modal` (reference) — documents Modal SDK gotchas. `verify-before status`
  tells you when to consult it; the modal-triage MCP tells you the actual state.

## Evidence

- Session transcripts (phenome + genomics, 2026-04-10 to 2026-04-18): 6+ ad-hoc
  probe scripts, ~30+ raw `modal app list | grep` calls, at least 3 hallucinated
  status claims corrected by the user.
- Global CLAUDE.md rule #8 "Probe before build" — previously text-only, now
  encoded as a skill with tool-backed checklists.
