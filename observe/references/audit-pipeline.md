<!-- Reference file for observe skill (audit + harness modes). Loaded on demand. -->
# `audit` / `harness` pipeline

`harness` runs the same phases with `model-prompts-harness.md` at phase 2.

| Phase | What | Reference |
|-------|------|-----------|
| 0 | Pre-flight: env, backlog gate, language detect, baseline | `references/preflight-scripts.md` |
| 1 | Dump codebase (diff-aware or full) | `references/codebase-dump.md` |
| 2 | Parallel Gemini + GPT analysis | `references/model-prompts-standard.md` |
| 3 | Cross-validation (`--thorough` only) | `references/cross-validation.md` |
| 4 | Extract, auto-validate, triage | `references/triage-procedures.md` |
| 5 | Execute with per-finding verify + rollback | `references/execution-loop.md` |
| 6 | Report, MAINTAIN.md integration, baseline SHA | `references/report-template.md` |

**Tiers:** `--quick` = phases 0-2, findings only, ~2 min · default = full, ~15-30 min ·
`--thorough` adds cross-validation, ~30-60 min · `--deferred` re-triages prior deferrals, skipping
phases 1-3 (`references/deferred-retriage.md`). Route through the shared dispatch surfaces and the
packet contract in `shared/context_packet.py`; consume `coverage.json` + `findings.json`. **Do not
rebuild provider flags, packet manifests, or raw model recipes here.**

Phase 4 consumes the structured findings artifacts the shared review/dispatch path emits —
parsing rules and the fallbacks when a model returns prose instead of JSON are in
`references/json-parsing.md`.
