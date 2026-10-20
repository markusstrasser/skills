# Modal — budget kills, spend queries and budget defense

> Moved verbatim from modal/SKILL.md (2026-10-21, context-cost reduction). SKILL.md keeps the one-line rules.

### Budget kills
When account spend hits the limit, ALL running containers die instantly — no graceful shutdown, no checkpoint write, no `@modal.exit()` handler. The only defense is frequent `vol.commit()` between steps AND committing partial work during long steps.

Evidence: SBayesRC 80GB×200 parallel containers couldn't schedule. Pangenie 192GB preempted 3+ times across 3 days. Budget limit killed all 3 active apps simultaneously mid-run — 6h of SBayesRC compute, 4h of sven_sv annotation (21.8GB artifact on ephemeral disk), 5h of pangenie genotyping — all lost because ephemeral disk is wiped and the commit-at-step-boundary model saves nothing mid-step (2026-04-13).

**The frozen-workspace TELL (spend-cap disable):** every endpoint returns 404 with a "workspace disabled" body, `modal app list` renders an EMPTY table, and deploys/API calls fail — indistinguishable from a slow cold boot to a naive HTTP poll, so poll loops burn their full timeout on it (2026-07-11 arc-agi: 2700s poll against a capped workspace read as "boot never ready"). Poll loops must check the 404 body for "disabled" and fail fast + distinctly (reference: arc-agi `modal_serve_lib.sh::msl_poll_ready` exit 2). Same-day `billing report` lag (gotcha 23) means the freeze usually arrives BEFORE the dashboard shows the spend that caused it.

### Rule: budget monitoring before launch
Check Modal Live Usage before launching anything significant. >85% = don't launch long jobs. There's no graceful budget-aware degradation; you hit the limit and everything dies.

### Programmatic spend queries
For current 1.5.1 work, prefer the new Workspace/Environment billing API or its
CLI frontend. The CLI check is:

```bash
modal billing report --for today --json --show-resources --tag-names run_id,stage,attempt_id
modal environment billing report <environment> --for today --json --show-resources --tag-names run_id,stage,attempt_id
```

The Python-side replacement for the old workspace API is:
`modal.Workspace().billing.report(...)` or
`modal.Environment.from_name(...).billing.report(...)` after probing the active
SDK shape. These reports include resource-level cost breakdowns (CPU, memory,
specific GPU types), which stage telemetry should preserve.

Deprecated historical surface: `modal.billing.workspace_billing_report(...)`.
Do not build new code on it.

Cloud billing APIs typically lag 5-15 min. A 60s watchdog poll + 90% threshold can still miss bursts that cross the cap before the poll. Pair polling (belt) with admission control at launch (suspenders).

### Budget defense: sidecar watchdog + halt flag
The most reliable defense against budget kill is prevention: a separate daemon
that polls a live-probed billing surface (CLI JSON or a verified Python API)
and sets a halt flag in `modal.Dict` which every launch path reads before
dispatching.

```python
# Daemon (local process, not on Modal — it'd be killed by the event it detects):
dict_ = modal.Dict.from_name("orchestrator_state", create_if_missing=True)
if mtd >= threshold_usd:
    dict_["budget_halt"] = {"set_at": time.time(), "reason": "...", "remaining_budget": cap - mtd}

# Launcher (orchestrator):
halt = dict_.get("budget_halt")
if halt:
    raise BudgetHaltError(halt["reason"])  # refuse launch cleanly
```

On launch failure, also inspect the subprocess stderr for `ResourceExhausted` / `quota exceeded` / `workspace budget` / `spend limit`. Do NOT include `auth error` / `unauthenticated` in that signature set — `MODAL_TOKEN_ID` rotation gets misclassified and poisons `orchestrator_state` globally until a human clears it.
