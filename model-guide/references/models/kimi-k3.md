# Kimi K3 — open-weight opt-in

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L291-322.

> Comparisons below name Fable 5 and GPT-5.6 Sol, both retired 2026-09-25, Pareto-frontier prune.

## Kimi K3 — open-weight long-horizon coding opt-in (Moonshot, 2026-07-16)

Moonshot's 2.8T-parameter open model — first open 3T-class model — built on Kimi Delta
Attention + Attention Residuals, native vision, **1M context**. Weights promised by
2026-07-27. Posture: frontier-adjacent, self-admittedly trailing Fable 5 / GPT-5.6 Sol
overall, but with table-leading long-horizon agentic results (SWE Marathon **42.0**, best
of table; BrowseComp **91.2**, best; Terminal-Bench 2.1 88.3 ≈ Sol's 88.8; 24h
kernel-optimization parity with Fable 5). 2.5× scaling-efficiency gain over K2 claimed.

**Operational specs:** `kimi-k3` via `llmx chat -p kimi -m kimi-k3` (metered,
`MOONSHOT_API_KEY`; provider now targets api.moonshot.**ai** — the .cn endpoint 401s the
local key, flipped 2026-07-16). **$3.00/MTok cache-miss input, $0.30 cache-hit input,
$15.00/MTok output** (>90% cache-hit rate claimed on coding workloads → effective input
cost can be ~10× under Opus/Sol on repeat-context sweeps). Launch thinking is
**max-only** — low/high effort modes announced, not yet shipped; llmx encodes
`reasoning_effort: False`, don't pass an effort. Also the default model of the local
Kimi Code CLI (`~/.kimi/config.toml` → `moonshot-ai/kimi-k3`).

**Routing read (opt-in, unprobed locally):** a third-lab (Moonshot) long-context
coding lane — worth a measured probe where prompt-cache makes repeat-context work cheap,
and as the open-weight self-serve option once weights land. **Not a default anywhere:**
metered, locally unverified, and no subscription path exists.

**Vendor-disclosed constraints (load-bearing):**
1. **Thinking-history sensitivity** — the harness must return all historical thinking
   content; never switch K3 into an ongoing session from another model. Use Kimi Code or
   a verified-compatible harness.
2. **Excessive proactiveness** — trained for long-horizon autonomy; on ambiguous intent it
   may make decisions on the user's behalf. Bind it with explicit AGENTS.md/system-prompt
   constraints for bounded work.
3. **UX gap** — the vendor concedes a noticeable user-experience gap vs Fable 5 / Sol
   despite competitive scores.
