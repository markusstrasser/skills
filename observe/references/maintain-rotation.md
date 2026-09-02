# `maintain` P3 rotation table

The cadence values of record live in `../scripts/rotation_due.py` (single source). This file
documents *how* each task is run and the judgment calls. The session-learning rows come first —
they are why the conductor runs on a loop: mine what happened, drain what is actionable, scan the
frontier.

**Logging contract.** A tick that picks a rotation task appends
`{"ts": …, "action": "rotation", "target": "<task-key>", "result": …}` to
`maintenance-actions.jsonl`. `rotation_due.py` only sees what is logged with its task keys — an
unlogged run stays "due" forever.

| Task | Cadence | How |
|------|---------|-----|
| Hook health | every tick | `just hooks-smoke` — cheapest catch for silently-dead hooks |
| Session anti-patterns | daily / ~5 sessions | `/observe sessions` → `[obs]` |
| Steering vectors (full corpus) | weekly | `just steer-mine`; cluster recurring `vector` fields → GOALS tension or steward-proposal. Do NOT auto-promote to hooks without the promotion gates |
| Supervision waste | daily | `/observe supervision`. A reiteration of something already decided elsewhere is the highest-signal defect → `decisions-pending/` |
| Governance downstream watch | after constitution/GOALS/invariants edits | review sessions since the edit for friction, reverts, anomalies → flag or revert. **The compensating control for inferred-approval governance autonomy** (invariants #1): that autonomy is only sound if a loop catches a bad edit downstream |
| Governance health read | daily | read `artifacts/gov/gov-report.md`; act on the 3 REAL `gov_invariants` assertions (rule-hook balance, recurrence-architecture, verifier-coverage). Graders in `~/Projects/evals/graders/governance/`. Escalate failures to `decisions-pending/` |
| Maintain motor | daily | `scripts/maintain_tick.py` drafts a tier-0 BUILD proposal (SAFE/dry-run — never edits, commits, deploys); `--subtract --ablate` drafts a governance RETIREMENT. Both land in `artifacts/maintain/`. **BUILD** → P2. **RETIRE** is governance DELETION → `decisions-pending/` for human sign-off **even when local and ablation-PASS**. Never auto-remove governance in an unattended tick |
| ACT drain | daily | read `~/.claude/act-drain-digest.md` (written by the `pulse-tick` job; surfaces at SessionStart). Ranks quarantine / steward / RSI-close pending. Human dispositions via `/rsi close`, `just reflect-review`, steward triage |
| Finding drain | weekly | `/observe harvest` |
| Tool failures | weekly | `/observe failures` — Tier-1 is $0; escalate big clusters |
| Cross-harness shell env | weekly | `doctor.py` → `global:shell-env-*`. Failures mean home-dir shell config drift, not repo hooks |
| Blindspot → detector | daily | read `.claude/blindspot-digest.md`, cluster, propose the DETECTOR for the top cluster → `improvement-log` `[ ]` / `decisions-pending/`. The flag rate is the declining-supervision objective |
| Architecture patterns | weekly (alt. frontier) | `/observe architecture` |
| Leverage scan | weekly | `/observe lever` — the prospective wins the retro modes are blind to |
| Frontier sweeps | freshness-driven | `/trending-scout` when DUE (2d) + agent-infra-sweep when DUE (3d) |
| Code quality scan | weekly | `/observe audit --quick` |
| Database freshness · research-memo staleness | daily · weekly | check timestamps, flag >30d stale · ACTIVE memos vs recent file changes |
| Deferred probe · cross-check outputs | after revisit date · daily | HTTP-probe URLs, check release pages · pick a T1/T2 variant, query the biomedical MCP, compare |
| Calibration canary | weekly | `calibration-canary.py --mode sampling --difficulty hard --runs 10 --backend llmx` |
| Genomics canary | after classification changes | `just canary` in genomics |
| Doctor health · session cost | daily | `uv run python3 scripts/doctor.py` · flag sessions >$5 or no-commit anomalies |
| Infra coverage · doc currency | monthly · fallback | `git log` → categorize fixes by detection source · `just check-codebase-map && just check-claude-md` |
