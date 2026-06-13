---
title: LOOP.md contract schema
date: 2026-06-13
---

# The `LOOP.md` contract — typed, not prose

A repo's loop is declared in a `LOOP.md` whose machine-readable config is **YAML** (frontmatter or
a single ```yaml fence). It is *typed and validated*, not free-form prose the agent soft-parses —
soft-parsed prose invites instruction drift. The outer-loop skill reads it as data; the conformance
linter (`scripts/lint_ledger_conformance.py`) validates the ledger half; `scripts/route.py` consumes
the regime + action properties.

**Why typed:** the contract is the *data* layer of the policy/data/structure split. Policy (the
skill) is shared and stable; structure (the ledger schema) is shared and linted; only the contract
varies per repo — so it must be the unambiguous, checkable surface. A global skill edit must not
silently change a repo's behaviour, which is why the contract pins `outer_loop_skill.version` and
`expected_schema`.

## Fields

```yaml
loop:
  repo: <str>                       # repo name
  outer_loop_skill:
    name: outer-loop                # which skill drives this loop
    version: <YYYY-MM-DD>           # pinned skill version — a global edit past this is a flagged change
    expected_schema: <int>          # contract schema version this file is written against

verifier:
  regime: clean-cheap | clean-expensive | partial | principal | mixed   # ONE input to route.py

schedule:
  driver: <str>                     # how the loop ticks: "/loop /dream" | "launchd claude -p /dream" | "/loop 30m"
  noop_on: <str>                    # the no-work condition: "queue-healthy" | "state-hash-unchanged"
  lock: <path|null>                 # single-writer lock script (optional); acquire + heartbeat each tick

proposer:
  skills: [<skill>, ...]            # swappable divergence engines: leverage, research, brainstorm, critique
  dedup_against: [<view|path>, ...] # ledger views / files the proposer reads to not re-propose (v_dead_ends, ...)
  max_per_fire: <int>               # cap on fresh candidates per tick (hutter: 8) — don't flood the inner loop

bus:                                # the git-mediated channels (no direct coupling between inner/outer)
  ledger: <path>#<table>            # the ledger (path#table); table defaults to "ledger"
  queue: <path>                     # fresh-candidate dir the inner loop consumes
  human_queue: <path>               # sign-off-ready items (decisions-pending/) — the human-gate output
  flags: [<path>, ...]              # inner-loop state flags the outer loop reads (STALL, QUEUE_LOW)
  discovery_flags: <path|null>      # where the inner loop flags a discovery/model-class move (proposals-pending/)

accept_gate:
  cmd: <str>                        # the EXACT runnable gate command (shelled; emits a structured verdict)
  verdict_field: <str>              # where the structured verdict appears (stdout key / ledger column)
  accept_verdicts: [<str>, ...]     # which verdicts authorise a ratchet (default: ACCEPT, BASELINE, GATE_PASS)
  error_verdicts: [<str>, ...]      # which verdicts are gate-failure → fail-closed (default: ERROR)
  independence: external | differential | decorrelated | same-lineage | human   # the gate's trust level
  gate_version: <str|null>          # version stamped per row (recommended; load-bearing in soft-gate regimes)
  budget: <null|{field, per_period, period}>   # rate-limit on an expensive gate (arc-agi: submissions/day)

ledger:
  path: <path>                      # schema file (.sql) / live DB (.db) / event log (.jsonl) the linter introspects
  table: <str>                      # table name (default: ledger)
  field_map:                        # canonical → this repo's actual column (only where they differ)
    candidate: <col>
    score: <col>
    predicted_score: <col>
    lineage_parent: <col>
    # ... any canonical field whose column name differs; unmapped canonicals use their own name
  calibration: {predicted: <col>, actual: <col>, view: <view>}   # the honesty view

actions:                            # the matrix — each action → typed properties route.py reads.
  # autonomy is either a literal level OR "route()" (defer to route.py with the properties below).
  <action_name>:
    autonomy: route() | unattended | attended | human_required
    reversible: <bool>
    blast_radius: local | shared | irreversible
    regime: <regime|null>           # override the loop regime for this action (mixed loops)
    reason: <str|null>              # why, for human_required / protected actions

human_owned:                        # things the loop proposes-but-never-edits (meta-Goodhart guard)
  - strategic-move-checklist
  - GOALS
```

## Required vs optional

- **Always required:** `loop.repo`, `loop.outer_loop_skill.{name,version,expected_schema}`,
  `verifier.regime`, `accept_gate.cmd`, `ledger.path`. The linter fails without `verifier.regime`
  and `ledger.path`.
- **Ledger fields:** the linter enforces the REQUIRED core (ts, candidate, verdict, lineage_parent,
  dead_end, tags) for every regime, plus score+predicted_score for clean regimes and
  proxy_score+ground_truth_score+budget_consumed for clean-expensive — all resolved through
  `field_map`. RECOMMENDED fields warn-only. See `ledger-schema.sql`.
- **`actions`:** declare at least the actions the loop actually takes. Any action in the hard-coded
  PROTECTED set (`modify_the_gate`, `model_class_change`, `update_goals`) is human-required whether or
  not it appears here — the contract can add protected actions, never remove these.

## Filled templates

### clean-cheap (hutter — full instance in `examples/hutter-LOOP.md`)
Deterministic free gate; low-blast auto-ratchets; discovery human-gated. Auto-ratchet lives here and
ONLY here — never in a partial regime (the gate has no ground truth to ratchet against).

### clean-expensive (arc-agi)
```yaml
verifier: {regime: clean-expensive}
accept_gate:
  cmd: "python eval.py --proxy ; on-submit: kaggle submit"
  accept_verdicts: [ACCEPT]
  independence: external            # truth tier is external; proxy is same-lineage (track proxy↔truth corr)
  budget: {field: submissions_spent, per_period: 5, period: day}
actions:
  run_candidate:    {autonomy: unattended, reversible: true, blast_radius: local}   # local proxy is free
  submit_ground_truth: {autonomy: route(), reversible: true, blast_radius: local}   # route() → BUDGETED while budget>0
  accept_candidate: {autonomy: route(), reversible: true, blast_radius: local}      # needs proxy↑ AND truth↑
```

### partial (intel / genomics / science)
```yaml
verifier: {regime: partial}
accept_gate:
  cmd: "scripts/freshness_gate.py"  # a CONSUMED differential check — gates, never just reports
  accept_verdicts: [PASS]
  independence: differential        # count-delta vs a held baseline — decorrelated, needs no second model
actions:
  generate_finding: {autonomy: unattended, reversible: true, blast_radius: local}
  execute_finding:  {autonomy: route(), reversible: true, blast_radius: local}      # attended unless narrow+reversible
  publish_recommend: {autonomy: human_required, blast_radius: shared, reason: "partial verifier — human signs off"}
```

### mixed (agent-infra `/improve maintain`)
Regime is per-action, not per-repo — each finding carries its own `{reversible, blast_radius,
regime}` and `route()` resolves it. See the agent-infra Phase-0 probe
(`agent-infra/research/scratch/2026-06-13-rsi-phase0-probe-agent-infra-contract.md`).
