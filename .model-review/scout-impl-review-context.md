# Review packet: VOI premise scout + llmx auth/mode

## Intent

Ship VOI-sequenced critique dispatch:

1. **Premise scout** (default `--scout`): `cursor-agent --workspace $PROJECT --mode ask` falsifies load-bearing premises before packet-only Gemini/GPT axes.
2. Scout output → `premise-scout.md` + `voi-scout.json` → injected as "Premise Scout" section in `shared-context.md`.
3. **llmx surface**: explicit `auth=api|subscription`, `mode=chat|agent` (scout uses cursor-agent directly for repo workspace, not llmx empty-cwd).

ADR: `agent-infra/decisions/2026-06-15-voi-sequenced-review.md`

## Design choices

| Choice | Rationale |
|--------|-----------|
| Scout via subprocess `cursor-agent`, not llmx | llmx cursor transport uses empty cwd; scout needs full repo |
| `--scout` default on | Fixes packet-only blindness (0-for-5 premise misses) |
| Skip gracefully if no cursor-agent | Don't block review on missing binary |
| `--no-scout` for debugging | |
| `premise_scout` profile in llm_dispatch | Metadata only; dispatch is in model-review.py |

## Key new functions (model-review.py)

- `run_premise_scout()` — subprocess cursor-agent, parses voi-scout.json from markdown fence
- `build_context(..., premise_scout_path=)` — injects scout section at priority 450
- CLI: `--scout` / `--no-scout`, `--fork`

## Risks to review

1. Scout runs on `--context` only (not `--context-files`-only) — is that OK?
2. Scout timeout 300s blocks whole review — should it be background?
3. Premise scout prompt asks for JSON in markdown — fragile parse?
4. Default scout on every `standard` review — cost/latency (Composer pool)?
5. Circular: reviewing scout with `--scout` on — we use `--no-scout` for this meta-review
6. llmx auth/mode decoupling — any footguns for claude_review profile?

## Files changed (skills)

- `critique/scripts/model-review.py` (+~200 lines scout phase)
- `shared/llm_dispatch.py` (auth/mode on profiles, premise_scout profile)
- `critique/SKILL.md`, `references/dispatch.md`
- `critique/scripts/test_model_review.py` (PremiseScoutTest)

## Review question

Adversarial review of THIS implementation. Focus:

1. Will premise scout actually fix packet-only blindness or add theater?
2. Failure modes: skip path, timeout, bad JSON parse, truncated packet
3. Breaking changes for callers expecting old model-review.py behavior
4. Missing tests or invariants
5. Should scout conviction=low block adjudication (ADR says only low+irreversible)?

Cite specific code paths and propose concrete fixes, not generic advice.
