# GPT prompting and Astra migration

Verified 2026-09-05 against [official model guidance](https://developers.openai.com/api/docs/guides/latest-model). Preserve the requested model and workload: a migration does not collapse a cost-tier router, replace an evaluation baseline or authorize API spending.

## GPT-6 Astra behavior

The shared global instructions own the general defaults. Apply them when writing an Astra brief:

- State the task, relevant inputs, success criteria and action boundaries. Tell the worker to finish authorized work and make routine assumptions; keep genuine missing decisions visible. A side question or new requirement steers the active task.
- Carry existing authorization forward. Prepare the reviewable result before an outstanding approval. User instructions outrank skill guidelines; a skill-driven pause must identify the exact file, instruction and reason.
- Request concise, plain prose and only the output structure needed by the consumer. Astra already tends toward detailed formatting; do not prepend `Formatting re-enabled` by habit.
- Delegate bounded independent work when it improves time or quality. Preserve parent judgment, file ownership and artifact contracts. Do not require a panel for a single-source lookup or forbid useful delegation across all research.
- Specify the checks needed for the change. Complete them, then stop repeating or broadening checks unless new evidence warrants it. Persistence and verification are useful behavioral instructions; avoid elaborate prescriptions for private reasoning.

These are vendor-recommended starting points, not local performance measurements. Validate a changed brief on representative tasks, including an authorized continuation, a genuinely gated action and a small edit that should stay small.

## When migrating an actual Astra caller

1. Preserve the effective reasoning effort. Map `none`/`minimal` to `low`; Astra supports `low`, `medium`, `high`, `xhigh` and `max` in the documented API. Check the specific CLI/runtime's supported settings separately.
2. Use Responses for tool calling. Plain-text Chat Completions remains supported; a text-only caller does not need a new tool loop.
3. Omit unsupported sampling/logprob parameters: `temperature`, `top_p`, `top_logprobs`; also Chat Completions `logprobs` and Responses `message.output_text.logprobs` in `include`.
4. If a caller actually changes effort across responses, inspect `configuration_update` compatibility before adopting it. Preserve a stable prompt prefix; do not add state machinery to independent one-shot calls.
5. If migrating an existing GPT-5.5-or-earlier cache-retention caller, use the documented `prompt_cache_options.ttl` replacement. No existing cache parameter means no migration is needed there.
6. For a configured EU data-residency endpoint, use Standard processing; Astra fast/priority is unsupported there. User geography alone is not endpoint residency.

Verify request construction and command parsing offline first. Keep pricing/admission and authorization controls; a mocked request is not a successful live API call. Optional async tools, WebSocket steering and pro mode need an actual caller and their specific documentation.

## Other GPT models and historical evidence

Use the official guide for the exact model and current transport. Keep strict output schemas when a real consumer needs them, preserve source identity, and supply decisive code/data instead of vague task labels. For technical/numerical work, specify which calculations require independent checking.

The [historical GPT guide](gpt-prompting-history.md) preserves prior model-specific observations and recipes. Its blanket bans on persistence/verification prompts and formatting prefix are superseded for Astra; do not transfer its reported error rates or model-selection verdicts without measurement.
