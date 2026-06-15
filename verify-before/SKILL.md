---
name: verify-before
description: "Use when: dry-run before expensive work, 'did it work/crash', live status probe, pre-register prediction before results. Modes: probe, status, preregister. NOT eval design (/eval) or adversarial review (/critique)."
user-invocable: true
argument-hint: "[probe|status|preregister] [target]"
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

Three modes, same principle: **do not claim, commit, or rationalize before
verifying.** `probe` verifies the mechanism before you spend compute; `status`
verifies the state before you claim; `preregister` verifies your prediction was
fixed before you saw the outcome.

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

### Step 2: Composer interpret (optional, default ON for multi-signal triage)

After fetching structured ground truth, you may need to **interpret** ambiguous signals
(stack traces, partial logs, conflicting fields). Do NOT paraphrase from memory — pass the
raw structured payload to Composer with a tight output contract:

```bash
# Write fetched ground truth to a file first (never inline a huge blob in the prompt)
cat > /tmp/status-ground-truth.json <<'EOF'
{paste structured fields from modal-triage / duckdb / BashOutput here}
EOF

uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile composer_review \
  --context /tmp/status-ground-truth.json \
  --prompt "Interpret this ground truth. Output JSON only: {\"status\": running|crashed|completed|stalled|unknown, \"confidence\": high|low, \"evidence_fields\": [\"...\"], \"recommended_next_probe\": \"...\"}. Cite field names from the input — no invented uptime or exit codes." \
  --output /tmp/status-interpret.md
```

**Rules:**
- Composer interprets **fetched** data only — if you skipped Step 1 (fetch), do not run Step 2.
- When `confidence` is `low`, run the `recommended_next_probe` before claiming status.
- The human-facing claim must still cite the **structured fields**, not Composer's paraphrase alone.

Skip Step 2 when ground truth is already unambiguous (single boolean `is_running`, explicit
`state=stopped`, zero exit code with empty queue).

---

## Mode: preregister

Lock a prediction and a decision rule **before the experiment, eval, or analysis
reveals its outcome** — so a confirmatory claim can't be retrofitted to whatever
the result happened to be.

### The failure this guards (HARKing / post-hoc rationalization)

This is the **structural mitigation for Failure Mode 25** (Belief-6 / Outcome
Bias) in `agent-failure-modes.md`, whose root cause is exactly the gap this
fills: *"agents have no natural access to their own pre-action expected outcome
... narrative defaults to present-tense outcome framing without the temporal
structure needed to separate prediction from result."* Pre-registration IS that
temporal structure. The existing FM25 surfaces (`stop-unsupported-completion.sh`
shadow hook + session-analyst) detect the *symptom* (a claim with no cited
prediction); this mode prevents the *cause*.

The other two modes act *before spending* and *before claiming*. This one acts
*before seeing*. The gap is real and recurring in this system:

- Agent saw a result ("you used Gemini 2.5"), rationalized it post-hoc, and
  deployed a global hook instead of checking runlogs (improvement-log 2026-04).
- Agent acknowledged a shared-infra change needed approval, then rationalized a
  bypass after the fact. Outcome first, justification after.

The constitution already pre-registers tests for *governance* changes ("check
via /observe after 2 weeks; test: zero reverts in 14 days"). This mode extends
the same discipline to *experiments and evals* — the place it's currently
missing.

### The rule

> NO CONFIRMATORY CLAIM WITHOUT A PRE-REGISTERED PREDICTION FIRST.
> Anything analyzed after the outcome was visible is **exploratory** — label it
> so, and never relabel it confirmatory.

### When it fires

Reach for `preregister` before, not after:
- a compute-heavy experimental run (>~10 min, the constitution's Operational
  Rule 6 threshold) whose point is to confirm/refute a hypothesis;
- a benchmark / eval / A-B comparison where you have a stake in the direction
  (new hook "reduces failures", new model "is better", refactor "is faster");
- any analysis where you could be tempted to call the result a success after
  seeing which way it broke.

Skip it for: pure exploration with no claim attached, mechanism probes (use
`probe`), and runs where no directional prediction exists yet.

### Phases

**1. Write the registration (before touching outcomes).** Smallest useful form:

```markdown
# Prereg: <topic> — <date>
- **Hypothesis:** <null> vs <directional alternative>
- **Exact procedure:** model/script, dataset/slice, metric, inclusion rules.
  Enough that a second agent could run it identically.
- **Prediction:** direction + rough magnitude ("≥30% fewer ≥5-failure streaks").
- **Decision rule:** the exact threshold that counts as confirm vs disconfirm
  ("confirmed iff streaks drop ≥20% AND no new false-positive class appears").
- **Stopping / N:** fixed sample / run count. No optional stopping — don't keep
  running until it looks good.
- **Falsifiability check:** name a concrete result that would DISCONFIRM it.
  If you can't, the hypothesis isn't testable — fix it before running.
- **Secondary / exploratory:** anything not above is exploratory, listed here.
```

**2. Freeze it in git.** Commit to `decisions/preregistrations/YYYY-MM-DD-<topic>.md`
(meta) or the project's equivalent. The commit timestamp is the external proof
the prediction preceded the result — that's the whole enforcement mechanism, so
commit *before* you run, not in the same batch as the results.

**3. Run exactly what was registered.** Deviations are allowed but must be noted
and move the affected claim to exploratory.

**4. Report against the decision rule.** State confirm/disconfirm by the
pre-committed threshold. Don't move the goalpost to the number you got.

### Enforcement honesty

This mode is **instruction-tier**, like `probe` and `status` — the git timestamp
is the only hard artifact. Per Constitution Principle 1, instructions shift the
intercept, not the slope. The hookable upgrade (deferred, gate on recurrence):
a PreToolUse gate on long Modal/eval dispatches that refuses to launch unless a
prereg file for the topic was committed in the last N commits. Build that only
if post-hoc-rationalization recurs after this mode ships.

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
- `preregister` mode: pattern extracted from K-Dense-AI/science-superpowers
  (2026-05-29), which centers a pre-registration discipline for research agents.
  We took only the temporal-lock kernel (predict + decision rule before outcome)
  and grafted it onto this skill rather than adopting the framework — its
  auto-trigger skill architecture overlaps the Autobrowse graduation mechanism
  vetoed 2026-05-28, and its enforcement is the same instruction-tier as ours.
  Failure mode it guards (post-hoc rationalization) is documented in
  improvement-log.md (Gemini-2.5 hook deploy; shared-infra bypass).
