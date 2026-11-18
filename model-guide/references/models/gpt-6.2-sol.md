# GPT-6.2 Sol

Everyday coding, vision, extraction and the subscription fallback for Astra.

- Exact ID `gpt-6.2-sol`. Use `llmx chat --subscription -m gpt-6.2-sol -e low` for a small job.
- Standard API pricing per million tokens is $2 input, $0.10 cached input and $10 output. Above 272K input tokens, input and cache rates double and output costs 1.5× for the full request.
- The API has a 1.05M context window, 922K maximum input and 128K maximum output. The local Codex catalog declares a 500K window. Keep existing workload limits unless tested.
- API effort ranges from `low` through `max`. llmx maps `none` and `minimal` to `low`. Use Responses for tool calls, and preserve the stable message prefix across turns.
- Codex subscription smoke-tested 2026-11-18 at `low` and Standard speed with the bundled CLI. Workload quality and paid API execution need their own verification.

[OpenAI model card](https://developers.openai.com/api/docs/models/gpt-6.2-sol) · [Migration guide](https://developers.openai.com/api/docs/guides/latest-model)
