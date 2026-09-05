# Observe recipes and maintenance tools

Recipe availability and job state are live data: use `just -f ~/Projects/agent-infra/justfile --list` before invoking an unfamiliar entry. These are workflow entry points, not a requirement to run every check.

Every one verified present in `~/Projects/agent-infra` via `just --list`:

```bash
just observe-run <mode> [project] [days]    # THE orchestrator — all deterministic lanes
just observe-all                            # full RSI pass
just observe-context [project] [sessions]   # size-safe context build (<600KB)
just observe-drift                          # wide-window drift context
just observe-preflight | just observe-gates # promotion gate
just blindspot                              # emb-contrastive loop-miss miner
just steer-mine                             # incremental full-corpus steer mining
just hooks-smoke                            # the SWEEP's first check
just freshness                              # which surveillance sweeps are DUE
just orphan-findings                        # canonical finding-routing ratchet
just reflect-review | just reflect-classify # quarantine triage
just memory-harvest                         # cross-project memory generalization
just supervision-audit                      # supervision KPI
just questions                              # human-gated pending decisions
```

Scripts under `${CLAUDE_SKILL_DIR}/scripts/`: `observe_gates.py` · `scan_tool_failures.py` ·
`extract_transcript.py` · `extract_codex_transcript.py` · `session-shape.py` · `mine_steers.py` ·
`rank_agent_miss.py` · `smart_judge_stats.py` · `validate_session_ids.py` · `observe_artifacts.py` ·
`extract_user_tags.py` · `rotation_due.py` · `maintain_live_state.sh` · `dump_codebase.py`.
