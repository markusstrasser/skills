---
name: model-guide
description: "Choose a model/effort and model-specific prompting for GPT-6 Astra, Fable 5.1, Claude, GPT-5.6 cost-tier or named opt-in lanes. Preserve workload cost, plan limits and verifier needs. Transport flags belong to /llmx-guide."
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Select between the current frontier models and prompt them correctly.

## GPT-6 Astra

For Astra prompting or migration, read [current GPT guidance](references/PROMPTING_GPT.md), verified against the official guide on 2026-09-05. Apply persistent authorized execution, explicit skill precedence, concise prose, useful bounded delegation and proportionate verification. Preserve effective effort, including `max`; `none`/`minimal` migrate to `low`.

The operator's Codex configuration selects Astra. Check the actual transport and its applied model/effort before a model-sensitive dispatch. Existing lower-cost task profiles and evaluation pins keep their roles; Luna stays the cheap extract/mechanical lane. Dated judgments below apply to their named models and harnesses, not automatically to Astra.

**Operational specs:** `gpt-6-astra` (alias `gpt-6`). API $10/$50 per MTok (2×/1.5× above 272K input); Fast mode 2× Standard. 1.05M context, 128K max output. Effort `low|medium|high|xhigh|max`; `none`/`minimal` map to `low`. Subscription via `llmx chat --subscription -m gpt-6-astra` or `codex exec` (omit `-m`) is $0 against the ChatGPT plan. Source: developers.openai.com/api/docs/models/gpt-6-astra (2026-09-05).

**Models covered:** GPT-6 Astra (default OpenAI / Codex flagship, 2026-09), Claude Opus 5 (headless Claude default), Claude Fable 5.1 (interactive Claude default; Max plan allowance), Claude Sonnet 5 (cost-tier Claude), GPT-5.6 Sol / Terra / Luna (named cost-tier pins; GPT-5.5 removed), Kimi K3 (Moonshot open-weight, 2026-07-16), and Grok 4.6 through the Cursor subscription pool and the Grok Build CLI.
**Last updated:** 2026-09-05 (GPT-6 Astra default Codex/OpenAI; Fable live slug `claude-fable-5-1`; Grok 4.6 replaces 4.5 on Cursor, Grok Build CLI recorded).
**Active stance:** This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok-4.20-and-earlier, and Sonnet-4.6-and-earlier routes were removed from active guidance. Sonnet 5 is reinstated as a named, cost-tier Claude option (2026-06-30). Grok 4.6 is an opt-in read-only repo critique lane through exact Cursor slugs and a headless lane through the Grok Build CLI; the xAI API path remains separate and blocked/unverified locally. Use this guide for high-value frontier decisions; use repo-specific batch tooling or search tools for cheap bulk work.

**OPEN QUESTION (2026-06-30, not yet resolved — operator call):** the "Architecture / design / high-reasoning critique → NEVER Sonnet" verdict below was reached against Sonnet 4.6 on 2026-06-20. Sonnet 5's system card shows large agentic/coding gains and prompt-injection robustness tying or beating Opus 4.8 in several places, but also the *worst* prefill/system-prompt-susceptibility numbers of the compared models and measurably more turns/tokens per task (system-card digest: `references/sonnet-5-system-card.md`). Whether this changes the "NEVER Sonnet" verdict for architecture/critique work is a live question, not re-litigated here — the verdict stands until the operator revisits it.

**Fable plan status — corrected 2026-09-05.** Fable 5 and 5.1 are included in Max and premium Team/seat-based Enterprise plans, within up to 50% of the shared weekly allowance. Pro and standard seats use credits. API calls and credits beyond the plan allowance remain metered; the operator's policy is Claude subscription only unless explicitly authorized otherwise. Fable 5.1 requires Claude Code ≥2.1.255; installed 2.1.261 supports it. [Anthropic plan rules](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan). Earlier blanket “off subscription” claims are superseded; [dated history](references/fable-routing-history.md) preserves them.

**Opus 5** (`claude-opus-5`) remains the existing headless Claude default and cross-lab review lane. Fable 5.1 is the operator's interactive default. Preserve explicit task and fallback selections; a fallback example does not redefine the general routing role.

## Verified Transport — configuration and execution evidence

| Lane | Verified state | Practical limit |
|---|---|---|
| Codex / `llmx chat --subscription -m gpt-6-astra` | Global model is Astra; llmx accepts the canonical ID and effort | Configuration and offline checks do not prove a new live request or workload result. |
| `llmx chat --subscription -m claude-fable-5-1` | 2026-09-05 dry-run: `claude-cli`, subscription auth, exact 5.1 ID and requested effort | No live headless 5.1 canary in this check. Subscription never permits silent API fallback. |
| Interactive Claude Code | Global setting `claude-fable-5-1[1m]`; installed CLI 2.1.261 | Existing September 2 local billing evidence is recorded in agent-infra’s Fable memo §10. Plan allowance and current remaining usage are separate. |
| Claude Agent-tool model pins | Opus pins recovered in the July 29 observations; Fable pins have no later verification here | Treat old failures as dated evidence. For model-sensitive evaluations inspect the provider run record; self-report alone is not independent proof. |
| Cursor Grok 4.6 | 2026-09-05: `cursor-agent models` lists ONLY `cursor-grok-4.6-{low,medium,high,xhigh}[-fast]`; the 4.5 slugs are gone. `llmx chat --dry-run --subscription -m cursor-grok-4.6-high` resolves (effort is baked into the slug; `-e` is ignored). | Any pin on a `cursor-grok-4.5-*` slug is dead. Refresh the canary before a model-sensitive dispatch. |
| Grok Build CLI (`~/.grok/bin/grok`, 1.0.13) | 2026-09-05 live smoke: headless `grok -p "…" --output-format json -m grok-4.6 --reasoning-effort <e>` returned the answer plus token usage; served model `grok-4.6-build`. | Every call carries ~26K tokens of the CLI's own context; cost shows as `total_cost_usd` against the SuperGrok plan. llmx `grok-cli` transport in progress. |

The [historical transport record](references/fable-routing-history.md) preserves
old routing failures and their later corrections. Validate the actual lane a
caller uses; an alias or successful dry-run establishes configuration only.

## Default Routing

Judgment below assumes the lane you dispatch to actually delivers the named model — confirm that against Verified Transport above before trusting a routing choice for a tier-sensitive dispatch.

| Situation | Use | Why |
|---|---|---|
| **Most headless/dispatch tasks — the default cheap lane** (extraction, triage, ticks, bulk classification, mechanical audit) | **GPT-6 Astra via codex-cli subscription** (`llmx chat --subscription -m gpt-6-astra`), effort `low` | $0 on the ChatGPT plan. Astra-low beats Luna-max on AA Intelligence Index (57 vs 43). Pass `-m gpt-5.6-luna` only for metered API bulk. |
| Everyday GPT / Codex implementation, tool loops, structured API work | **GPT-6 Astra** (`llmx chat --subscription -m gpt-6-astra`; or omit `-m` on `codex exec`) | Operator Codex config selects Astra. API list $10/$50; subscription is $0 against the ChatGPT plan. Named `gpt-5.6-*` pins remain for evals and cheaper API work. |
| Hardest / longest / most-ambiguous Claude work: multi-day autonomous runs, codebase-scale migrations, first-shot on complex well-specified systems, dense-image vision, architecture | **Claude Opus 5** for existing headless lanes; **Fable 5.1** for the operator's interactive lane or an explicit Fable dispatch | Preserve each lane's role and plan allowance. API Fable costs twice Opus; Max subscription accounting is separate. Pair GPT-6 Astra for cross-lab on the hardest judgment calls. |
| Routine/cost-sensitive coding, security review, cyber, lab/molecular biology | **Claude Opus 5** | Same model — use lower effort (`low`/`medium`) when the brief has mechanical gates. |
| Quantitative proof, calibration math, hard science/data derivation where mistakes compound | **GPT-6 Astra** + API `reasoning.mode=pro` | Pro is a reasoning *mode* at the same $/MTok (more tokens). Use when the answer will be checked. |
| Cross-model review | **Opus 5 + GPT-6 Astra** (Luna OK for mechanical) | Different labs, different failure profiles. Keep the review cross-lab; do not use same-instance self-review as the sole adversarial pressure. PLAN packets get repo-grounded premise falsification from the built-in Composer scout. |
| Architecture / design / high-reasoning critique | **Opus 5 `max` + GPT-6 Astra — NEVER Sonnet** | Operator 2026-06-20: architecture → Opus **`max`**. Sonnet is for search + bug-fixes only. For codebase-coupled decisions, rely on the review gate's repo-grounded Composer premise scout before packet-only critics. |
| Agentic SaaS / multi-tool workflows (AutomationBench-shaped) | **Opus 5 or GPT-6 Astra** | Grok led the historical model screen, but the verified local Cursor admission currently covers read-only repo review, not autonomous write/tool workflows. |
| Current facts, quotes, prices, law, news | **Tools first, then model synthesis** | Every model card still shows factuality limits. Retrieval/database truth beats frontier recall. **Not Grok alone** — AA-Omniscience non-hallucination ~46% (mid-pack; worse than Opus 4.8 64% / GLM 72%). |

## Quick Selection Matrix

| Task | First choice | Escalate / pair when |
|---|---|---|
| Agentic coding | Opus 5 (high effort) | Drop to `low` effort when brief has mechanical gates; use GPT-6 Astra when terminal/Codex-heavy. |
| Codebase-scale migration / multi-day autonomous run | Opus 5 (`xhigh`/`max`) | Keep human checkpoints at irreversible boundaries. |
| Security review, exploit/vuln work, cyber, molecular biology | Opus 5 | Active Claude default for classifier-sensitive work (formerly Fable-refusal domain). |
| Debugging messy repo state | GPT-6 Astra (or Luna for mechanical) | Pair with Opus if the fix requires architectural judgment. |
| Architecture decision | **Opus 5 `max`** | Send the selected proposal to GPT-6 Astra for independent cross-lab critique; use the built-in premise scout for repo-grounded checks. |
| Quantitative audit / CritPt-hard physics | GPT-6 Astra (`max` / pro mode) | Grok CritPt **15%** — weak; do not route hard derivation here. |
| Long-context document/repo synthesis | Opus 5 or GPT-6 Astra | Both 1.05M-class. Grok API context is **500k** — prefer Opus/GPT for >500k. |
| Browser/computer use | Opus 5, GPT-6 Astra or the operator's Fable 5.1 lane | Verify that the chosen transport exposes the required browser/computer tools. Model registration alone does not establish tool availability. |
| PLAN critique needing repo falsification | **`/critique model` with its default premise scout; add opt-in `grok` for an independent repo cosigner** | Composer checks callers/joins by default; Grok high adds a separately preflighted read-only repo pass when the extra axis is worth the latency. |
| Letter-exact output constraints (exact counts, rigid templates, banned words) | Schema/validator enforcement, any model | Never rely on prose compliance — Claude family is measurably weakest at mechanical constraint-following (IFBench 62–63 vs GPT-5.6-class 76, bottom-5 of 27). Construct caveat: IFBench is majority adversarial-synthetic and high scores trade against answer quality, so this is a weak GPT preference for unschematizable cases, not a routing rule. |
| Claim verification | Neither alone | Use primary sources and deterministic checks; use models to summarize evidence, not to establish it. |
| Contradictory / impossible spec, epistemic guardrails | **Opus 5** or **GLM-5.2** (opt-in) | GPT family historically weak on abstention (re-measure GPT-5.6 TBD); DeepSeek V4 (~6%). Grok ~46% — mid-pack, **not** a calibration pick. More reasoning tokens does not fix paradox blindness — see trilemma section. |

For full score tables, read `references/BENCHMARKS.md`.

## Selection trilemma (capability × calibration × efficiency)

Benchmark **capability** (Intelligence Index, SWE scores) and **parameter count** are weak proxies for real-world usefulness. They often **invert** on **calibration** — whether a miss is an abstention or a confident fabrication — and on **efficiency** — tokens/time to reach a correct or honest answer.

| Axis | What it measures | Routing mistake |
|---|---|---|
| **Capability** | Closed-set benchmark scores, index composites | Picking the #1 index model for every task |
| **Calibration** | Share of wrong answers that abstain vs confabulate (AA-Omniscience non-hallucination) | Treating critique reasoning as fact because the model is "smart" |
| **Efficiency** | Tokens, latency, $ to a verified outcome | Escalating reasoning effort on a poorly calibrated model |

**Settled ordering on calibration (AA-Omniscience, misses only, abstention invited):** GLM-5.2 **72%** non-hallucination → Opus 4.8 **64%** → Grok 4.5 **~46%** / Fable 5 **45%** → prior GPT class **14%** (re-measure 5.6) → DeepSeek V4 **~6%**. Capability ordering is nearly the reverse (Grok Intelligence Index **54**, near Opus 56). A multi-trillion-parameter model can score at the top of an index and still be the worst choice when the task needs "I don't know" or detection of an impossible/contradictory spec.

**Reasoning budget is not monotonic.** On badly calibrated models, more reasoning often buys longer confident wrong answers, not better ones. Anecdotal corroboration (Shrimpton 2026-06-18, n=1, high effort, temp 1): an impossible asyncio event-loop spec — DeepSeek V4 Pro ~7.7k reasoning tokens, 3m52s, full wrong implementation; GLM-5.2 ~800 tokens, 12s, correctly flagged the paradox. Don't throw `xhigh`/`max` at poorly calibrated GPT or DeepSeek for epistemic guardrails; use Opus, GLM (opt-in), or deterministic impossibility checks.

**Consumer rule:** match model to the axis that matters for the task — capability for gated mechanical work with a verifier; calibration for unsourced facts, paradox detection, and "should we even do this?"; efficiency for throughput. Never select on size or index rank alone.

## Transport facts (llmx — not judgment)

**Read before dispatch:** `~/.claude/cache/llmx-routing.json` (regenerate: `llmx info --write-mirror`). Transport table, effort maps, exit classes live there — not in this skill.

**Claude policy:** NEVER `anthropic-direct`/API by default. Subscription only (`llmx chat --subscription`, `claude -p` with key stripped, Agent tool) unless the user explicitly requests metered API billing.

**Probe subscription path before critique batches:**

```bash
llmx chat --dry-run --subscription -m claude-opus-5 -e max
# or: uv run python3 ~/Projects/skills/critique/scripts/model-review.py --preflight
```

Mechanics and footguns: `/llmx-guide`.

## llmx Cosigner / Dispatch Defaults (judgment — transport in mirror)

- **Cosigner / critique / synthesis:** `gemini-3.8-flash` (GA 2026-09-02; intro $0.75/$3.75 through 2026-12-31). **Always in the 2G+2GPT mix — never the only reviewer.** Probe flags invention on clean packets; orchestrator dispositions via `--extract --verify`.
- **Cheap classification / mechanical audits:** `gpt-6-astra` at `low` via codex-cli subscription ($0). Luna does not beat Astra-low on quality (AA Astra-low 57 vs Luna-max 43); keep `-m gpt-5.6-luna` for metered API bulk. Gemini is critique-only since 2026-07-14.
- **GPT-6 Astra default effort:** preserve the requested effort; `none`/`minimal` map to `low`. Suite supports `max`. Pass `-e high`/`xhigh`/`max` for depth; reasoning bills as output.
- **GLM-5.2 (Z.ai, NEW LAB) = opt-in review cosigner, NOT an extractor (2026-06-19).** A 4th independent training lab (Zhipu) → real cross-lab diversity for critique; request explicitly `--axes …,glm` (`glm_review` profile, routed via OpenRouter). **Calibration edge:** 72% AA-Omniscience non-hallucination (2026-06-18 independent read) — best among commonly-routed large models, ahead of Opus 4.8 64%; strong on impossibility/paradox detection in anecdotal coding probes. Accepts ONLY `high`/`xhigh` reasoning (no low tier) → structurally expensive+slow → **rejected for high-volume extraction/ingestion** (cost-dominated, no quality gain; keep gpt-5.3/gemini-3-flash). Match reasoning floor to task: GLM for occasional thorough review and epistemic guardrails, not throughput. See `agent-infra/decisions/2026-06-19-glm-5.2-integration.md`, `evals` DECISIONS `glm-5.2-extraction`.
- **Grok 4.6 is the Cursor Grok pool as of 2026-09-05 (4.5 slugs removed).** Use exact `cursor-grok-4.6-{low,medium,high,xhigh}` or matching trailing-`-fast` slugs. The opt-in critique `grok` axis pins `cursor-grok-4.6-high` in a read-only repo workspace and fails closed on registry or unrevealed repo-canary drift. The bare `grok-4.6` xAI API lane and the Grok Build CLI (`grok -p`) are separate lanes.
- **Gemini 3.6 Flash / 3.5 Flash-Lite (launched 2026-07-21) are REGISTERED, NOT ROUTED (2026-07-22).**
  Live API ids `gemini-3.6-flash`, `gemini-3.5-flash-lite` (GA, no `-preview` suffix; verified
  against `models.list`, not guessed). Registered in llmx (`652d1ed`) purely so the spend guard
  stops refusing them as *unpriced* — **the 2026-07-14 critique-only policy is unchanged and no
  default moved.** Prices (verified at ai.google.dev/gemini-api/docs/pricing 2026-07-22):
  3.6 Flash **$1.50/$7.50**, 3.5 Flash-Lite **$0.30/$2.50**, 3.1 Flash-Lite **$0.25/$1.50**.
  Same pass corrected two badly stale entries — `gemini-3-flash` was priced in llmx at $0.075/$0.30
  against an actual **$0.50/$3.00**, so cost dashboards were understating Gemini ~7-10x. Note
  3.5 Flash-Lite is **6x input / 12.5x output the price of 3.1 Flash-Lite** — the "Lite" tier is no
  longer a rounding error. Effort ladders probed live: 3.5-Flash-Lite accepts `minimal`,
  3.1-Flash-Lite **rejects** it (do not pin `minimal` on the older one).
- **Do NOT reach for Flash-Lite as the cheap extraction lane — `gpt-5.6-luna` stays it.** Luna is
  **$0 on the ChatGPT subscription**; Flash-Lite is metered under a policy that only permits
  /critique. A metered lane cannot beat a $0 lane on cost, so Flash-Lite would have to win big on
  quality, and our own screening probe says it does not (see below).
- **Open, operator's call — 3.6 Flash as the /critique cosigner in place of 3.5 Flash.** Strictly
  cheaper on the one lane Gemini is still allowed on: **$7.50 vs $9.00 output** *and* a vendor-claimed
  ~17% output-token reduction, i.e. roughly -30% on cosigner spend. NOT changed unilaterally — the
  `gemini-3.5-flash` cosigner default was set operator-empirical (2026-06-13, re-confirmed), and a
  vendor claim is not evidence that it reviews as well. Swap is one line in the critique axes.
- **`llmx vision` is multi-provider as of 2026-07-22 (llmx `2b12289`) — it used to be Gemini-only
  and off-ledger.** It now routes through the normal dispatch path, so `-m` takes any
  vision-capable model id (`gemini-3.6-flash`, `gpt-6-astra`, `gpt-5.6-luna`, `claude-opus-5`),
  provider is inferred, and `-e` effort works. Three consequences worth knowing:
  (1) it is **spend-guarded and policy-gated** like everything else — a Gemini vision call now
  needs `LLMX_GEMINI_OK=1`, where it previously dispatched freely;
  (2) it **writes real token counts to the usage ledger**, so vision cost no longer has to be
  estimated (evals/figure_vision_bakeoff had been substituting a `len(response)/4` proxy);
  (3) media **fails loud** rather than being dropped — video to an OpenAI-compat endpoint, an
  oversized inline upload, or any media sent through a CLI transport (claude-cli/codex/cursor)
  raises, because a model asked about a figure it never received invents an answer.
  Footgun retained for back-compat with the documented convention: in `llmx vision`, `-p` is the
  PROMPT, not `--provider` (use `--provider` to override the inferred one).
  **This unblocks a cross-family vision judge**, which the figure-vision eval previously could not
  have — its qualitative judge was Gemini-flash grading a Gemini-flash candidate, a same-family
  COI it documented as forced by the tool. Pass `--judge gpt-6-astra` there now.
- **`gemini-3.1-pro-preview` is RETIRED as a routing option (2026-06-13, operator).** Do not route here for critique/synthesis/review — flash-3.5 dominates and is cheaper/faster. (Benchmark records in `references/BENCHMARKS.md` are kept as evidence; this is a routing retirement, not a data scrub. Callable via explicit `-m` if a one-off ever needs ARC-AGI-2/GPQA/video, but it is not a default anywhere.)
- **Cosigner calibration caveat (AA-Omniscience, 2026-06-11):** both cosigner defaults are bottom-quartile abstainers — non-hallucination 39% (`gemini-3.5-flash`), prior GPT class 14% (re-measure Luna/Sol TBD), despite an abstention prompt. Critique output = adversarial pressure on reasoning, never a fact source; **for fact-heavy review where calibration matters, verify novel specifics at primary and lean on a frontier model (Opus/GPT), not a cheap cosigner.** Instruments: agent-infra `research/2026-06-11-aa-benchmark-instrument-validity.md`.

## Dispatch Economics (subagent executor tiers)

When dispatching subagents to execute work (Agent tool, headless `claude -p`, codex), the executor tier is set by **how good the verifier in the brief is**, not by how hard the task feels. Measured evidence: four preregistered evals, anim-workbench 2026-06-12 (`anim-workbench/.claude/evals/2026-06-12-{dispatch-tier,effort-tier,codex-lane,effort-integration}/`), all n=1 per arm (screening grade).

| Work shape | Executor | Evidence / boundary |
|---|---|---|
| FULL brief + mechanical gates (tests, typecheck, deterministic verify script) — greenfield OR port/re-author against an existing oracle | **Opus 5 effort low, or codex reasoning-low ($0)** | Effort-tier: low matched medium on all 5 gates at 0.59× tokens. Effort-integration (the pre-registered replication): low matched DEFAULT on an integration-shaped port — same gates, independently convergent design decisions, 0.574× tokens. Codex-lane: GPT reasoning-low passed all gates at $0 (subscription) and resolved a self-contradictory brief *within spec*. Revocation trigger (registered): first cheap-lane gate failure on a task classified fully-briefed → fall back to default effort for that class + record. |
| Design-from-scratch integration, no oracle to check against | **Opus 5, default effort** | The effort-integration license covers port/re-author shapes only (its own caveat: "ports are the friendliest integration shape"). Dispatch-tier still holds: Sonnet 4.6 changed the measurement procedure under gate pressure until the gate passed (reward-hacking-shaped); Opus was deviation-free. "Opus is token-efficient so cheaper" was REJECTED (~2.4× Sonnet cost) — the premium buys spec fidelity, not efficiency. |
| Mechanical no-gate tasks (rename sweeps, boilerplate) | **Claude Sonnet 5** (`claude-sonnet-5`) or haiku tier | Cheap and gameable-gate risk is moot when there's no gate to game. (Row previously said "Sonnet/haiku tier" with no live model — resolved 2026-06-30 now that Sonnet 5 exists.) |
| Cost-sensitive coding/agentic work WITH a mechanical gate (tests, typecheck) — not architecture | **Claude Sonnet 5**, default effort | System card: beats Sonnet 4.6 broadly, ties Opus 4.8 on several real-world benchmarks (Real-World Finance, GDPval-AA), at ~40-60% of Opus 5's per-token price. Runs more turns/tokens per task than Opus though — re-measure cost on your own workload before assuming the $/token saving holds end-to-end. |
| Search/read fan-out | Explore agent | No executor risk; output is consumed, not shipped. |
| Partial/noisy verifier (research synthesis, memos, judgment-coupled work) | **Don't downgrade** — frontier model, normal effort | The Sonnet finding gets WORSE here: gate-gaming in regime-2 is exactly what you can't detect cheaply. Verifier-conditioned scope (constitution) applies. |
| Judgment gaps in the spec | Yourself / Opus 5 | Cheap executors fill ambiguity with guesses; the savings are repaid as corrections. Codex-lane's reasoning-HIGH arm is the same lesson from the other side: on a spec-complete task, more reasoning bought one extra unnecessary spec deviation, not better conformance — spec + gates do the thinking, so buy reasoning only where the spec leaves thinking to do. |

**Model-sensitive comparisons require served-model evidence.** Keep requested model,
resolved transport and provider-reported model distinct; see Verified Transport.

### Role → Lane (dispatch execution roles)

| Role | Current-best lane | Cost class | Evidence |
|---|---|---|---|
| **Synthesis** (open design problem, no oracle) | Opus 5 `max`; explicit Fable 5.1 via subscription | Plan usage | The 2026-06-12 Fable 5 effort result is historical evidence, not a Fable 5.1 comparison. Check served-model evidence before relying on an Agent-tool Fable pin. |
| **Briefed execution** (full brief + mechanical gates) | `opus-low` or codex reasoning-low | $0 subscription | anim-workbench 2026-06-12 effort-tier/effort-integration/codex-lane (low ≈ medium/default, 0.57-0.59× tokens). |
| **Review / cosign** | Opus 5 + GPT-6 Astra, cross-lab; opt-in GLM-5.2 or Grok-4.5 axis | $0 subscription (+~$0.30-1/call opt-in) | `evals/DECISIONS.md` `cross-lab-review-margin` (margin≈0, count-delta real); GLM decision 2026-06-19. |
| **Research / literature** | Independent source/model lanes for broad coverage when useful; a bounded lookup or synthesis can stay in one lane | $0 subscription | arc-agi feedback 2026-07-07: codex arm found a paper (PRISM, 2605.26998) the Claude arm missed. |
| **Scout fan-out** (parallel audits/debug scouts) | Cross-model default, concurrency-capped ≤2 concurrent opus subagents / ≤2 concurrent model workers each, else sequential | $0 subscription | arc-agi feedback 2026-07-08: 4 concurrent opus agents × openrouter fan-out (28-way) killed 3/4 mid-run — opus session-limit + provider contention, both real ceilings. |
| **OS-student serving** (open-weight model as trainee/actor under test) | Project-specific — measure, don't assume | GPU $/hr | Example only, not a universal verdict: arc-agi killed mistral-small-3.2-24B as an OS-tier base (dominated on every axis, 2026-07-11), rehabbed qwen3.6-27b via a no-think serving config, kept gemma-4-31B alive. Check your own project's standing-kills doc before reusing a verdict cross-project. Serving mechanics: `/modal` skill. |

**Codex lane mechanics:** use `codex exec -s workspace-write -C <managed-worktree> -c model_reasoning_effort=low` for authorized writes, or `-s read-only` for analysis. Preserve the configured model unless an override is intended. Current flags and output contracts are in [Codex dispatch](../llmx-guide/references/codex-dispatch.md).

**Codex as a research/work subprocess:** direct Codex uses the selected skills and MCP configuration; llmx also has a controlled research profile. Single-quote shell prompts containing `$skill` names. Read [subprocess guidance](references/codex-subprocess-dispatch.md) for scoped briefs, output contracts and recovery. Verify the required source access when uncertain; a transport failure does not disprove research capability.

**The conditioning rule:** low effort doesn't mean less verification — both eval arms ran every gate *because the gates were written in the brief*. Self-initiated checking is what higher effort buys; an explicit verifier in the brief makes that purchase unnecessary. So the brief MUST carry: verification commands (exact, runnable), cleanup directives (worktree/scratch teardown), and a files-touched manifest requirement. A cheap executor on a gate-less brief is the worst quadrant.

**Intern rule (gate-less delegation):** exploratory, divergent, or conceptual dispatches (research sweeps, brainstorms, design options, synthesis) have no mechanical gate to put in the brief — so the coordinator's review IS the gate. Treat the return like an intern's draft: don't re-do the work, but spot-check it before adopting. Concretely: re-run 1-2 of its load-bearing probes/citations yourself, check one claimed source actually says what's claimed, run the completeness check (does every input appear in the output, are dropped items justified), and ask what the brief would have rewarded the agent for skipping. Scale the spot-check to stakes — a brainstorm needs a sniff test, a synthesis feeding a decision needs the citation check. Skipping this turns "delegate" into "launder": unverified subagent output adopted wholesale is the same failure as adopting cross-model critique without cosigning.

**Effort knob mechanics:** the Agent tool exposes only `model:`. Per-dispatch effort exists via (1) headless `claude -p --model opus --effort low` (verified working, CLI 2.1.175; background Bash + `--output-format json` for usage), or (2) `.claude/agents/*.md` frontmatter `effort:` (does NOT hot-register mid-session — usable only in later sessions). Codex/GPT cheap cosign via llmx `--subscription` is $0 — probe with `--dry-run --subscription` first; transport table in `~/.claude/cache/llmx-routing.json`.

**Agent-tool defaults can differ from the parent.** Inspect the role definition and applicable model overrides instead of inferring inheritance. Preserve bounded subtask scope and resource limits where the caller needs them. Earlier model-pin failures and the June sub-delegation stall are retained in the [routing history](references/fable-routing-history.md); they do not establish current Fable 5.1 execution or justify a universal delegation ban.

**External validity:** all four evals are regime-1 (clear mechanical verifiers — tsc, deterministic scripts, numeric oracles) and screening-grade (n=1/arm). Only within-eval contrasts are clean — cross-eval comparisons are confounded by task, brief density (briefs improve as the author learns, flattering later arms), and harness (codex carries MCP servers + sandbox; opus arms ran bare). Every cheap-lane verdict is conditional on the dispatch-time classification "fully-briefed + mechanically gated" being honest — nothing here licenses cheap lanes for judgment-shaped or incomplete-spec work. The greenfield→integration replication trigger from the morning run is SATISFIED (effort-integration, port shape); the standing revocation trigger replaces it.

**Reasoning escalation guard (calibration × effort):** the cheap-lane evals show *less* reasoning is fine when the verifier is in the brief. The inverse also holds outside regime-1: escalating effort on poorly calibrated models (GPT family until re-measured, DeepSeek V4) on paradox/impossibility or unsourced-fact tasks tends to produce more confident fabrication, not more abstention — see Selection trilemma. Effort buys depth only where calibration is already adequate (Opus, GLM for review).

## Claude Opus 5 - "Near-Fable daily driver" (primary Claude)

**Use for:** existing headless Claude lanes — autonomous runs, codebase-scale migrations, architecture, code review, professional analysis and cross-lab critique. Preserve their Opus role; Fable 5.1 is available through the Max plan and is the operator's interactive default. Transport readiness and workload quality are separate checks.

**Operational specs:** `claude-opus-5`, 1M context (default = max), 128K max output (300k batch beta), **$5/M input and $25/M output** (same as 4.8). Fast mode ~2.5× speed at 2× price ($10/$50). Adaptive thinking on by default; effort default `high` on API/Code. Knowledge cutoff **May 2026** (training). **Subscription-routable** (`lite_allowed_models`). Cyber-classifier refusals can auto-fallback to `claude-opus-4-8`; bio refusals on Fable now route here.

**Launch routing line (2026-07-24):** near-Fable capability at half Fable's price; Anthropic claims SOTA on Frontier-Bench, GDPval-AA, and best cost-efficiency on OSWorld 2.0 / AutomationBench / ARC-AGI 3 (≈3× next-best). Efficiency at `low`/`medium` effort is a real lever — re-sweep effort defaults. **Most aligned** of recent Claude models on Anthropic's automated behavioral audit (misalignment score 2.3). Prompting deltas vs 4.8: longer default verbosity (prompt for concision), stronger self-verification (remove redundant "verify again" scaffolding — it over-verifies), more subagent-eager (cap delegation), thinking-disabled capped at `high` effort. Digest: [references/opus-5-system-card.md](references/opus-5-system-card.md). Prior 4.8 card kept for calibration history: [references/opus-4-8-system-card.md](references/opus-4-8-system-card.md).

**Two shape-changes the launch line misses** (system card §8.12 / §8.2 / §2.2 — read 2026-07-25, `agent-infra research/2026-07-25-opus5-arc-agi-generalization.md`):

- **Tools beat effort — spend the budget there first.** §8.12 verbatim: *"agentic tool-use is generally a more cost-effective method of scaling test-time compute than adaptive thinking by itself."* Before raising a dispatch one effort tier, give it a verification command / probe / read-back tool instead — cheaper **and** stronger. This is a *cost* lever, not only a quality one.
- **Attach the image.** SWE-bench Multimodal 38.4→**59.4 (+21pp)** is the single largest coding delta in the release; OSWorld 2.0 +15pp. Screenshot-the-render / plot / broken-UI and hand it the source, instead of describing the visual defect in prose. Applies to rendered frames, QC plots, dashboards, CAD.
- **Its exploration gain is verifier-conditioned — this is the liveness rule.** ARC-AGI-3 1.5→30.2 (20×, dense per-action score) sits in the same card as §2.2, where two Opus 5 arms of a 24h autonomous design campaign delivered nothing and one **went silent for its final 8 hours in self-verification loops** (no in-loop verifier). Give any long autonomous run a per-step check it can score against, and bind completion to an advancing artifact — a live PID proves the process runs, not that it progresses.

**Prompting and API rules:**
- Use XML tags; adaptive thinking explicit (`thinking:{"type":"adaptive"}`); no manual `budget_tokens`.
- Default effort `high`; **`max` for architecture/design/high-reasoning critique** (operator 2026-06-20); `xhigh` for serious coding/review/long agentic work; `low` for gated mechanical dispatch (see Dispatch Economics).
- **Measured effort curve (Artificial Analysis, 2026-07-25) — `max` is a poor default:** AA Intelligence Index by effort — low **51** ($556 / 12M out-tok), medium **56** ($1,115 / 29M), high **59** ($1,974 / 52M), max **61** ($3,836 / 100M). low→max = **+10 points for 6.9× cost**; **high→max = +2 points for +$1,862**. At max AA flags it *"very verbose"* (100M vs 63M median); at high, *"fairly concise."* With §8.12 (tools scale test-time compute better than thinking), the rule is: **default `high`, escalate to `max` only for architecture/irreversible calls, and spend the delta on an in-loop verifier instead of the top tier.** AA's task mix ≠ ours — a strong prior, not a workload-specific verdict.
- **Calibration warning (AA, independent):** AA-Omniscience **Index 31 — below Fable 5's 40**, despite Opus 5 leading the Intelligence Index at 61. It leads on intelligence and trails on confident-wrongness — keep provenance tagging and claim verification on for factual work. Direction corroborated by the card itself (§6.5: *"hallucinates factual claims slightly more than Opus 4.8, despite being more accurate overall"*). ⚠ A widely-quoted *"hallucination +14pp → 50%"* figure is **UNVERIFIED** — it traces to a search-engine summary of an @ArtificialAnlys X post, and AA's own pages do not publish per-model accuracy/hallucination for Opus 5. Cite the Index gap (verified), not the 50%.
- Mid-conversation `role:"system"` messages supported immediately after a user turn — use for permission/budget/environment updates without rebuilding the prompt.
- No non-default `temperature`/`top_p`/`top_k` (400 on 4.7+); no assistant prefill; min cacheable prompt 1,024 tokens.
- Put long documents first and the query/instructions last.

Full guide: `references/PROMPTING_CLAUDE.md`.

## Claude Sonnet 5 - "The Cost Tier" (added 2026-06-30)

**Use for:** cost-sensitive coding and agentic work with a mechanical gate (tests, typecheck), mechanical no-gate dispatch (rename sweeps, boilerplate), and work dominated by untrusted tool output or prompt injection. The Sonnet 5 system-card comparison and the unresolved architecture-routing question above remain model-specific evidence. Historical Agent-tool substitutions are recorded in Verified Transport; do not identify a served model from its writing style or self-report alone.

**Operational specs:** `claude-sonnet-5`, 1M context, 128K max output, **$3/M input and $15/M output** ($2/$10 introductory through 2026-08-31, vs Opus 5's $5/$25). Adaptive thinking on by default (unlike Sonnet 4.6, which ran thinking-off by default — omitting `thinking` now runs adaptive). First Sonnet-tier model with `xhigh` effort. New tokenizer vs Sonnet 4.6 (~30% more tokens for the same text — partially offsets the lower $/token). **Not yet on the subscription allowlist** (`lite_allowed_models` in `~/.claude/cache/llmx-routing.json` has no Sonnet entry, 4.6 or 5) — `llmx chat --subscription -m claude-sonnet-5` will not route until that allowlist is updated (llmx's own config, not this skill).

**System-card routing line** (digest: [references/sonnet-5-system-card.md](references/sonnet-5-system-card.md)):
strongest measured prompt-injection robustness (ties/beats Opus 5); beats Sonnet 4.6 on nearly
every coding/agentic benchmark; watch-items — worst-of-cohort prefill/system-prompt susceptibility,
disclosed training-health issue (highest closed-book abstention of compared models), ~6%
evaluation-awareness, and more turns/tokens per task than Opus 4.8 (cheaper $/token ≠ cheaper
$/task on long loops — measure on your own workload).

**Prompting and API rules:** same XML-tag, no-prefill, no-non-default-sampling-param rules as Opus 5 (see `references/PROMPTING_CLAUDE.md` — written for Claude generally, applies here). Effort: default `high`; use `xhigh` for the hardest coding/agentic work in this tier (first Sonnet model to support it); `low`/`medium` for routine/mechanical dispatch per Dispatch Economics above.

## Claude Fable 5.1

**`claude-fable-5-1`, released 2026-09-01.** API $10/$50 per MTok, cache read $0.25, 1M context and 128K output; adaptive thinking is always on, default effort `high`. [Official overview](https://platform.claude.com/docs/en/models/fable-5-1/overview). The global Claude setting selects `claude-fable-5-1[1m]`; explicit launcher effort takes precedence over saved settings. Preserve the operator's effort selection.

The September prompting guidance recommends testing effort per workload: names do not imply equivalent quality across models, low effort may search less, and high effort can duplicate long deliverables in reasoning and the reply. Use the requested effort; tune only against the task's verifier. The existing source digest and migration dispositions are in agent-infra `research/2026-09-01-fable-5.1-tabula-rasa.md` §1 and §10. Fable 5 findings remain [historical evidence](references/fable-5-dormant.md), with [prior routing claims](references/fable-routing-history.md) retained for calibration.

## GPT-5.6 suite — Sol / Terra / Luna (GA 2026-07-09)

**Naming:** generation number (`5.6`) + durable tier (`Sol` / `Terra` / `Luna`). Alias `gpt-5.6` → `gpt-5.6-sol`. **GPT-5.5 is removed** — do not route, upgrade, or price it.

| Tier | Model ID | $/MTok in/out | Role |
|---|---|---|---|
| **Sol** | `gpt-5.6-sol` | $5 / $30 | Flagship — coding, agentic, hard reasoning, cross-lab critique peer to Opus |
| **Terra** | `gpt-5.6-terra` | $2 / $12 (cut -20% 2026-07-30) | Mid tier — opt-in between Luna and Sol |
| **Luna** | `gpt-5.6-luna` | **$0.20 / $1.20** (cut -80% 2026-07-30) | **Everyday GPT** — ≈ prior GPT-5.5 perf at ~1/10 that price; also mechanical/lint at low effort; at this price the API lane is viable for BULK long-context fan-out (transcript reads ~$0.20/MTok in) without touching the codex subscription quota |

**Operational specs (all three):** 1.05M context, 128K max output, knowledge cutoff Feb 16 2026. Reasoning effort: `none` \| `low` \| `medium` \| `high` \| `xhigh` \| **`max`** (new beyond-xhigh). Default effort `medium`.

**Pro mode (not a separate slug):** API `reasoning.mode: "pro"` on Sol/Terra/Luna — more compute at the **same** $/MTok (higher token use). ChatGPT "Sol Pro" for Pro/Enterprise.

**`ultra`:** ChatGPT/Codex multi-agent setting (4 agents default) — not an llmx effort token yet; build via Responses multi-agent beta if needed.

**Cache (5.6+):** writes 1.25× uncached input; reads 90% discount; 30-min minimum cache life + explicit breakpoints.

**Routing defaults (this fleet is now the named cost-tier, not the GPT flagship):**
- GPT flagship / everyday Codex / formal review → **GPT-6 Astra**
- Mechanical lint / bulk extract → **Luna** (`low`)
- Mid-cost API bump → **Terra** (explicit `-m`)
- Named 5.6 Sol pin: `llmx chat --subscription -m gpt-5.6-sol`

**Calibration:** re-measure AA-Omniscience on 5.6 before trusting abstention. Until then, treat GPT critique as adversarial pressure on *reasoning*, not a fact source.

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

## Grok 4.6 — Cursor pool, Grok Build CLI, xAI API

**Grok 4.6 (released 2026-08-12) replaced Grok 4.5 everywhere on 2026-09-05.** API: `grok-4.6`, 500K context, text+image in, $2/$6 per MTok below 200K input ($0.50 cached), $4/$12 at or above 200K; reasoning effort `low|medium|high|xhigh` (xhigh is new). Cursor pool: `cursor-grok-4.6-{low,medium,high,xhigh}[-fast]` — `cursor-agent models` no longer lists any 4.5 slug, so every `cursor-grok-4.5-*` pin is dead. Grok Build (`~/.grok/bin/grok`, v1.0.13, Apache-2.0, SuperGrok/X Premium+ subscription, left beta 2026-08-07) is xAI's own terminal coding agent powered by 4.6: interactive TUI, headless `grok -p "<prompt>" [--prompt-file P] --output-format text|json|streaming-json -m grok-4.6 --reasoning-effort <e> [--no-plan] [--permission-mode …]`, up to eight subagents in worktrees, ACP integration. It is the lane the operator means by "grok" as a subagent — not only Cursor. Sources: [xAI Grok Build docs](https://docs.x.ai/build/overview), [x.ai/build](https://x.ai/build), [release guide](https://codersera.com/blog/grok-4-6-launch-guide-2026/), [pricing/context](https://kingy.ai/blog/grok-4-6-price-benchmarks-api-cursor-context-window/). The 4.6-specific benchmark numbers below are NOT yet measured here; the AA table is the 4.5 snapshot kept for calibration until a 4.6 paste replaces it.

**Grok 4.5 history.** SpaceXAI frontier model (2026-07-08), jointly trained with Cursor. Independent AA
measurement put it in the **frontier pack on capability** with a **cost/speed edge** and
**mid-pack calibration**. Cursor's exact Grok slugs are live again as of 2026-07-14; use this
as an opt-in read-only repo-review axis, not a replacement for Opus/GPT judgment or primary evidence.

**AA snapshot (high effort, operator paste 2026-07-09 — treat as screen, not verifier):**

| Metric | Grok 4.5 | vs peers (same paste) | Routing read |
|---|---:|---|---|
| Intelligence Index | **54** | Fable 60 · Opus 56 · GPT ~55 · GLM 51 | Frontier-capable; not #1 |
| Coding Index | **72.4** | Fable 76.5 · GPT 74.9 · Opus 74.3 | Near Opus/GPT for coding |
| Terminal-Bench v2.1 | **82%** | Fable/Opus 85 · GPT 84 | Parity band |
| AutomationBench-AA | **51%** | Fable/Opus 49 · GPT 42 | **Lead** — tool/SaaS workflows |
| τ³-Banking | **33%** | GPT 31 · Opus 28 | **Lead** — agentic tool use |
| AA-Briefcase Elo | **1328** | Fable 1583 · Opus 1354 · GPT 1158 | Strong knowledge-work agent |
| CritPt | **15%** | GPT-Pro 31 · Fable 29 · Opus 21 | **Weak** — hard physics |
| AA-Omniscience accuracy | **52%** | Fable 61 · GPT 57 · Opus 47 | Solid recall |
| AA-Omniscience non-hallucination | **~46%** | GLM 72 · Opus 64 · Fable 45 · GPT 14 | Mid-pack — not a fact source |
| Cost / Intelligence task | **~$0.31** | GPT $0.86 · Opus ~$1.8 · Fable $2.75 | **Use more when $ matters** |
| Output speed | **~88 tok/s** | Flash 167 · Fable 70 · GPT 68 | Faster than Fable/GPT |

**Admission gate (enforced on every critique dispatch):** the live registry must expose exact slug
`cursor-grok-4.6-high`, and an unrevealed exact repo-HEAD canary must prove read-only workspace
access. Any failure blocks the axis before reviewer dispatch.

**Use less / never alone:**
1. **Unsourced facts / "should we even do this?"** — ~46% non-hallucination; tools + Opus/GLM for epistemic guardrails.
2. **Hard quantitative / CritPt physics** — 15%; use GPT-5.6 Sol pro-mode.
3. **Sole architecture judge** — still Opus `max` + GPT cross-lab; Grok is the *repo* axis, not the taste axis.
4. **Contexts >500k** — API window is 500k; Opus/GPT are 1M-class.
5. **CursorBench scores** — Cursor blog: training contamination; excluded from their table.

**Operational specs (API, 4.5 era — superseded by the 4.6 line above):** `grok-4.5`, **500k context**, $2/$6 per MTok, reasoning `low`/`medium`/`high` (default high). Fast Cursor variant $4/$18.

**Surfaces:**
| Surface | How | Status (2026-09-05) |
|---|---|---|
| Critique `grok` axis | `model-review.py --axes standard,grok` | Opt-in — pin moved to `cursor-grok-4.6-high` on 2026-09-05 (was 4.5, which the registry no longer lists); re-run the preflight canary before trusting it |
| Cursor session / `cursor-agent` | `--model cursor-grok-4.6-high --mode ask --workspace <repo>` | Registry lists the 4.6 slugs (2026-09-05); named smoke + canary not yet re-run on 4.6 |
| Grok Build headless | `grok -p "<prompt>" --output-format json -m grok-4.6 --reasoning-effort high --no-plan` (cwd = the repo you want it to read) | **Verified live 2026-09-05**: `grok -p "Reply with exactly the word OK…" --no-plan --output-format json -m grok-4.6 --reasoning-effort low` returned `OK` in JSON with usage (26,055 input tokens for a one-line prompt — it loads its own ~26K system context — 23 output, 18 reasoning, `total_cost_usd` 0.0089 reported against the SuperGrok plan, served model `grok-4.6-build`). `grok agent` is the same headless runner without the TUI. |
| llmx Cursor pool | `llmx chat --subscription -m cursor-grok-4.6-high` (or `-xhigh`) | **Verified 2026-09-05** — dry-run resolves cursor-cli; nine live red-team reviews dispatched the same evening |
| llmx xAI API | `llmx chat -p xai -m grok-4.6 -e high` | Model id known to llmx; key status unverified since the 2026-07-09 403 |

**Footgun (updated 2026-09-05):** exact Cursor slugs are prefixed
`cursor-grok-4.6-` and place `-fast` last; 4.6 adds an `xhigh` slug. Bare `grok-4.6` is the
xAI API model. Current llmx refuses any `auth=subscription` plan that resolves to `xai-api`.

See `agent-infra/decisions/2026-07-09-grok-4.5-transport.md`.

## Cross-Model Review Pattern

Use independent parallel reviews, then synthesize yourself:

```text
Opus 5 (max for architecture): architectural/professional judgment and implementation critique.
GPT-6 Astra: terminal/tool/process critique and structured failure search (hard).
GPT-5.6 Luna: mechanical / bulk (low).
GPT-6 Astra + reasoning.mode=pro: quantitative or high-irreversibility decisions.
Grok 4.6 high (Cursor opt-in, or Grok Build headless in the repo): repo-grounded premise falsification after live preflight.
Ground truth: tests, git, databases, source documents, primary web pages.
```

**Phase-0 before any model COMPARISON / bakeoff:** `grep ~/Projects/evals/DECISIONS.md` for the question FIRST — it may be settled, and a fresh n=1 probe must not steer a default an eval already decided. (2026-06-13: a 4-model review bakeoff re-ran the settled `cross-lab-review-margin` question, and an `/execute` edit got written contradicting its verdict — Phase-0 dedup caught it only after the fact.)

That verdict, calibrated: the cross-lab-vs-same-lab MARGIN is **≈0** — a second DIVERSE pass earns its keep via *count-delta* (it finds what the first missed), but the second reviewer being a different LAB buys ~nothing over a same-lab second instance, and it still hallucinates facts (a MiniMax-M3 pass verified ~25%, confident HIGH fabrications — ground any reviewer's asserted facts, weight its reasoning). The real martingale to avoid is a model reviewing its OWN output (same instance) as the *sole* adversarial pass.

## Validation Checklists

Post-output verification lists — All Outputs + per-model (Fable 5, Sonnet 5, Opus 5, GPT-5.6 Sol/Terra/Luna,
GLM-5.2, Grok 4.6): [references/validation-checklists.md](references/validation-checklists.md).
Consult after receiving output from a routed model, not at routing time.

## Source Notes

Primary sources consulted for this update:
- Anthropic: `https://www.anthropic.com/news/claude-fable-5-mythos-5`
- Anthropic Fable 5 system card: `https://www.anthropic.com/claude-fable-5-mythos-5-system-card`
- Anthropic docs: `https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5`
- Anthropic Fable prompting guide: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Anthropic: `https://www.anthropic.com/news/claude-opus-5`
- OpenAI GPT-5.6: `https://openai.com/index/gpt-5-6/`, pricing/models docs on developers.openai.com
- Cross-repo harness analysis: `agent-infra/research/2026-06-09-fable-5-mythos-5-harness-impact.md`
- Independent benchmarks: artificialanalysis.ai (2026-06-11) with instrument-validity reads of AA-Omniscience/IFBench/GDPval/τ² — `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`
- Calibration + reasoning-budget anecdote: Oliver Shrimpton, "Bigger models are not the way" (2026-06-18) — AA-Omniscience hallucination rates for GLM-5.2/DeepSeek V4 Pro; impossible-asyncio n=1 probe on OpenRouter
- Agent-tool routing-bug finding: arc-agi session 41f9b649, 2026-07-12 (fable ×5/5 self-reports; opus ×1 fresh probe, agent `a8afa4bad056a6f61`)

## When to Update This Skill

Update after a current-frontier release or material system-card revision:
1. Update `references/BENCHMARKS.md`.
2. Update `references/PROMPTING_CLAUDE.md` or `references/PROMPTING_GPT.md`.
3. Update this routing surface if the default choice changes.
4. Update Verified Transport if a dispatch-mechanism fact changes (a lane starts/stops
   delivering the model it claims) — this table rots faster than judgment; re-probe, don't assume.
5. Add a dated entry to `references/CHANGELOG.md`.

Hit a defect or friction consulting this guide (a stale routing line, a wrong price, a missing model)?
Log it for the next reader: `~/Projects/skills/hooks/append-skill-memento.sh model-guide '<one-line issue>'`.

## Known Issues

For matching failures, read [incident history](references/known-issues.md). The memento helper appends there.
