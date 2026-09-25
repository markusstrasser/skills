# Routing tables (pre-rewrite snapshot)

> Moved verbatim from model-guide/SKILL.md on 2026-09-25 (principle-first rewrite; skills HEAD before the rewrite). Inline `[historical: …]` tags are the only additions. Source lines: L11, L21-23, L48-63, L65-84.

> **Historical snapshot.** The principles and roster in [SKILL.md](../SKILL.md) supersede these tables. Rows citing GPT-5.6, Opus 4.8, Fable 5 or Grok 4.5/4.6 figures refer to ids retired 2026-09-25, Pareto-frontier prune; the figures stay as evidence.

Select between the current frontier models and prompt them correctly.

**Models covered:** GPT-6 Astra (default OpenAI / Codex flagship, 2026-09), Claude Opus 5.5 (2026-09-22; recommended Claude default, served by the `opus` alias), Claude Opus 5 (exact-ID lanes; cyber and dual-use biology), Claude Fable 5.1 (named-edge lane; Max plan allowance), Claude Sonnet 5 (cost-tier Claude), GPT-6 Sol / Luna (cost tiers, 2026-09-22), Kimi K3 (Moonshot open-weight, 2026-07-16), and Grok 4.7 through the Cursor subscription pool and the Grok Build CLI.
**Last updated:** 2026-09-25 (GPT-6 Sol and Luna, released 2026-09-22, replace the GPT-5.6 cost tiers; both verified live on the Codex subscription and registered in llmx). Previously 2026-09-23 (Claude Opus 5.5 released 2026-09-22; system card read; the `opus` alias now serves it. Grok 4.7, released 2026-09-21, is the current Grok; 4.6 slugs stay admitted until the live registry drops them. **2026-09-23 correction:** the Grok 4.7 Cursor slug is `grok-4.7-*` with no `cursor-` prefix, verified live with `cursor-agent` signed in — a 2026-09-22 guess had assumed the 4.6-style `cursor-grok-4.7-*` prefix, which does not exist).
**Active stance:** This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok-4.20-and-earlier, and Sonnet-4.6-and-earlier routes were removed from active guidance. Sonnet 5 is reinstated as a named, cost-tier Claude option (2026-06-30). Grok 4.7 is an opt-in read-only repo critique lane through exact Cursor slugs and a headless lane through the Grok Build CLI; the xAI API path remains separate and blocked/unverified locally. Use this guide for high-value frontier decisions; use repo-specific batch tooling or search tools for cheap bulk work.

## Default Routing

Judgment below assumes the lane you dispatch to actually delivers the named model — confirm that against Verified Transport above before trusting a routing choice for a tier-sensitive dispatch.

| Situation | Use | Why |
|---|---|---|
| **Most headless/dispatch tasks — the default cheap lane** (extraction, triage, ticks, bulk classification, mechanical audit) | **GPT-6 Astra via codex-cli subscription** (`llmx chat --subscription -m gpt-6-astra`), effort `low` | $0 on the ChatGPT plan. Astra-low beats Luna-max on AA Intelligence Index (57 vs 43). Pass `-m gpt-5.6-luna` only for metered API bulk. [historical: gpt-5.6-* retired 2026-09-25, Pareto-frontier prune; metered bulk is `gpt-6-luna`] |
| Everyday GPT / Codex implementation, tool loops, structured API work | **GPT-6 Astra** (`llmx chat --subscription -m gpt-6-astra`; or omit `-m` on `codex exec`) | Operator Codex config selects Astra. API list $10/$50; subscription is $0 against the ChatGPT plan. Named `gpt-5.6-*` pins remain for evals and cheaper API work. [historical: gpt-5.6-* retired 2026-09-25, Pareto-frontier prune] |
| Hardest / longest / most-ambiguous Claude work: multi-day autonomous runs, codebase-scale migrations, first-shot on complex well-specified systems, dense-image vision, architecture | **Claude Opus 5.5** (`xhigh`; `max` for architecture); **Fable 5.1** only with a named Fable edge or as the operator's interactive choice | Card: 5.5 matches or beats Fable 5.1 on most rows at $4/$20 against $10/$50, with fewer tokens per task; Anthropic says the real gap is narrower than the benchmarks. Max subscription accounting is separate. Pair GPT-6 Astra for cross-lab on the hardest judgment calls. |
| Routine/cost-sensitive coding and code review | **Claude Opus 5.5** at `medium` (its API default), `low` when the brief has mechanical gates | Vendor: 5.5 `medium` beats Opus 5 `high` on coding with fewer tokens. |
| Security review, cyber, lab/molecular biology | **Claude Opus 5** by exact ID (`claude-opus-5`) | 5.5 re-routes most cyber tasks to Opus 4.8 and runs a Fable-class bio classifier that declines dual-use research; Opus 5 has no bio classifier. |
| Quantitative proof, calibration math, hard science/data derivation where mistakes compound | **GPT-6 Astra** + API `reasoning.mode=pro` | Pro is a reasoning *mode* at the same $/MTok (more tokens). Use when the answer will be checked. |
| Cross-model review | **Opus 5.5 + GPT-6 Astra** (Luna OK for mechanical) | Different labs, different failure profiles. Keep the review cross-lab; do not use same-instance self-review as the sole adversarial pressure. PLAN packets get repo-grounded premise falsification from the built-in Composer scout. |
| Architecture / design / high-reasoning critique | **Opus 5.5 `max` + GPT-6 Astra — NEVER Sonnet** | Operator 2026-06-20: architecture → Opus **`max`**; the rule names the tier, and 5.5 now serves it. On AA knowledge work 5.5 `xhigh` finished 26–42 Elo below `max` with 41–51% fewer output tokens. Sonnet is for search + bug-fixes only. For codebase-coupled decisions, rely on the review gate's repo-grounded Composer premise scout before packet-only critics. |
| Agentic SaaS / multi-tool workflows (AutomationBench-shaped) | **Opus 5.5 or GPT-6 Astra** | AutomationBench 40.0 vs 41.4 (5.5 card). Grok led the historical model screen, but the verified local Cursor admission currently covers read-only repo review, not autonomous write/tool workflows. |
| Current facts, quotes, prices, law, news | **Tools first, then model synthesis** | Every model card still shows factuality limits. Retrieval/database truth beats frontier recall. **Not Grok alone** — AA-Omniscience non-hallucination ~46% (mid-pack; worse than Opus 4.8 64% / GLM 72%). |

## Quick Selection Matrix

| Task | First choice | Escalate / pair when |
|---|---|---|
| Agentic coding | Opus 5.5 (`medium`; `xhigh` for hard multi-file work) | Drop to `low` effort when brief has mechanical gates; use GPT-6 Astra when terminal/Codex-heavy. |
| Codebase-scale migration / multi-day autonomous run | Opus 5.5 (`xhigh`/`max`) | Keep human checkpoints at irreversible boundaries. |
| Security review, exploit/vuln work, cyber, molecular biology | Opus 5 by exact ID (`claude-opus-5`) | Classifier-sensitive work stays here: 5.5 re-routes most cyber to Opus 4.8 and declines dual-use biology. The `opus` alias no longer reaches Opus 5. |
| Debugging messy repo state | GPT-6 Astra (or Luna for mechanical) | Pair with Opus if the fix requires architectural judgment. |
| Architecture decision | **Opus 5.5 `max`** | Send the selected proposal to GPT-6 Astra for independent cross-lab critique; use the built-in premise scout for repo-grounded checks. |
| Quantitative audit / CritPt-hard physics | GPT-6 Astra (`max` / pro mode) | Grok CritPt **15%** — weak; do not route hard derivation here. |
| Research-level derivation, model algebra | Opus 5.5 `max` with code execution, or GPT-6 Astra pro | ArXivMath (Aug 2026): 5.5 91.2 / 96.9 without / with tools, Fable 5.1 82.9 / 92.1. Check that it ran the code: answering tool-required tasks from memory is its one reward-hack subclass above Mythos 5.1. |
| Long-context document/repo synthesis | Opus 5.5 or GPT-6 Astra | Both 1M-class (ProgramBench to 1M: 5.5 91.2, Fable 5.1 87.6). Grok API context is **500k** — prefer Opus/GPT for >500k. |
| Browser/computer use | Opus 5.5 (OSWorld 2.0 81.8 partial), GPT-6 Astra or the operator's Fable 5.1 lane | Verify that the chosen transport exposes the required browser/computer tools. Model registration alone does not establish tool availability. On the API, 5.5 takes computer use only through `computer_toolset_20260801`. |
| Source-grounded research memo, wide fact collection | Opus 5.5 at `high` or above | Never `low` on 5.5 for research: DRACO 72.5 and WANDR 31.2 at `low`, against Fable 5.1 at `low` 84.2 and 63.3. At max it ties Fable 5.1 on DRACO report quality and leads WANDR by 3.6 at lower cost. |
| PLAN critique needing repo falsification | **`/critique model` with its default premise scout; add opt-in `grok` for an independent repo cosigner** | Composer checks callers/joins by default; Grok high adds a separately preflighted read-only repo pass when the extra axis is worth the latency. |
| Letter-exact output constraints (exact counts, rigid templates, banned words) | Schema/validator enforcement, any model | Never rely on prose compliance — Claude family is measurably weakest at mechanical constraint-following (IFBench 62–63 vs GPT-5.6-class 76, bottom-5 of 27). Construct caveat: IFBench is majority adversarial-synthetic and high scores trade against answer quality, so this is a weak GPT preference for unschematizable cases, not a routing rule. |
| Claim verification | Neither alone | Use primary sources and deterministic checks; use models to summarize evidence, not to establish it. |
| Contradictory / impossible spec, epistemic guardrails | **Opus 5.5** or **GLM-5.2** (opt-in) | 5.5 card: fewest confident wrong answers among the Claude models shown (AA-Omniscience public split: 17% incorrect, 7% abstain). GPT family historically weak on abstention (re-measure GPT-5.6 TBD); DeepSeek V4 (~6%). Grok ~46% — mid-pack, **not** a calibration pick. More reasoning tokens does not fix paradox blindness — see trilemma section. |

For full score tables, read `references/BENCHMARKS.md`.
