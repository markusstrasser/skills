# Observe: failures

Use the [candidate lifecycle](candidate-lifecycle.md) when staging or promoting. Read [analysis dispatch](analysis-dispatch.md) only if Tier 2 or 3 requires a model; an empty healthy Tier 1 result needs no dispatch.

**"Which tools/CLIs are actually BROKEN in real use?"** — the question the proxy health checks
(hooks-smoke, launchd exit codes, indexer status) structurally cannot answer. The signal lives in
`agentlogs` (errored `tool_calls` + their result-event stderr) and went unread while a dead `corpus`
CLI failed for days (2026-06-14, operator: *"don't you check the logs for what doesn't work?"*).
**Hierarchical: a cheap deterministic net first, real money only on the big clusters.**

**Tier 1 — deterministic miner ($0, always run).**
`uv run python3 "${CLAUDE_SKILL_DIR}/scripts/scan_tool_failures.py" --days 21 --json > "$ARTIFACT_DIR/failures.json"`
joins errored tool_calls → result-event text and keeps only real crash **signatures**: Traceback + a
raised `ModuleNotFoundError`/`ImportError`, a real shell `command not found`, an entry-point shim
crash, or a cross-harness zsh-env failure (`zsh-env:nomatch`, `:alias-collision`, `:parse-error`).
**PreToolUse hook blocks are excluded** — those are working guards, not broken tools. High recall;
residual noise is Tier 2's job.

**Shell-env gate (auto, $0).** After `failures.json`, `observe_run.py` runs
`scripts/shell_env_loop_gate.py`. At `zsh-env:*` volume ≥50/30d **and** failing `doctor.py`
cross-harness shell checks it stages `shell-env-candidate.jsonl` for `harvest`, no transcript mining.

**Tier 2 — cheap triage.** One bulk call at the cheapest profile classifying each cluster
`REAL_INFRA_BREAK` / `TRANSIENT` (one-off scratch script, wrong-dir invocation) / `EXPECTED`. A
which/yes-no call, not analysis, so it is cheap by construction. Output ranked REAL breaks only.

**Tier 3 — escalate the big ones ($).** For clusters that are REAL *and* high-volume/multi-day (e.g.
`missing-module:duckdb` ×46/10d), dispatch a deeper root-cause+fix pass: a dep missing from an env,
or agents invoking bare `python3` instead of `uv run`? **Spend here** — fixing a recurring class
beats a handful of cheap lookups that miss it. Route confirmed breaks to `improvement-log.md` `[ ]`,
or `decisions-pending/` if shared-infra or irreversible; drop one-off scratch failures.
