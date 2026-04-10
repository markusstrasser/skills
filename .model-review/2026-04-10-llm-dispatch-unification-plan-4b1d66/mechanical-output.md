1. Path mismatch: `research-ops/scripts/run-cycle.sh` usage comment refers to `research-cycle/scripts/run-cycle.sh`.
2. Naming inconsistency: `scripts/llm_dispatch.py` uses an underscore; all existing repo scripts (`model-review.py`, `run-cycle.sh`, `generate-overview.sh`, `pretool-llmx-guard.sh`) use hyphens.
3. Duplicate logic: `review/scripts/model-review.py` contains hardcoded reasoning model detection (`gpt-5`, `gemini-3`) for setting `temperature = 1.0`; the plan does not explicitly move this logic into the shared helper.
4. Type inconsistency: `DispatchResult` is described as a "typed object or dict" in Phase 1, but Phase 2 `axis_output_failed` helper explicitly expects a `dict`.
5. Missing migration target: `research-ops/scripts/gather-cycle-state.sh` is a dependency of `run-cycle.sh` but is absent from the migration and audit list.
6. Stale reference: `llmx-guide/references/error-codes.md` is not slated for update despite the introduction of a new "Typed error taxonomy" in the plan.
7. Profile omission: `claude-sonnet-4-6` is mentioned in the `llmx-guide/SKILL.md` checklist but is not included in the "Initial profile set" defined in the plan.
8. Bootstrap duplication: The hardcoded `uv` site-packages path logic is duplicated across `pretool-llmx-guard.sh`, `observe/SKILL.md`, and `brainstorm/references/llmx-dispatch.md`.
9. Telemetry gap: `hooks/hook-trigger-log.sh` is used to log CLI blocks, but the plan does not include adding equivalent telemetry to the new Python-based dispatch path.
10. Redundant instructions: `llmx-guide` "Five Footguns" (Section 3 and 3.5) provides advice on CLI flags (`-o`) and shell pipelines that are forbidden for agents following this migration.
11. File path ambiguity: The plan lists `scripts/llm_dispatch.py` as a deliverable in Phase 1, but Open Question 1 suggests it might move to a `shared/` package.
12. Schema redundancy: `DispatchResult` returns `output_path` and `meta_path` as part of its metadata, which are already required input arguments for the `dispatch` function.
13. Version inconsistency: `research-ops/scripts/run-cycle.sh` and the plan use `gemini-3-flash-preview`, but `llmx-guide` and `pretool-llmx-guard.sh` use `gemini-3.1-pro-preview`.