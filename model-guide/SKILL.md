---
name: model-guide
description: "Use when: choosing frontier model/effort for a task class (Claude Opus 4.8, GPT-5.5/Pro). Fable 5 METERED since 2026-07-07 (off subscription, 2× Opus) — fable lanes are paid opt-ins. NOT transport flags (/llmx-guide)."
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Select between the current frontier models and prompt them correctly.

**Models covered:** Claude Opus 4.8 (primary Claude), Claude Sonnet 5 (cost-tier Claude, added 2026-06-30), GPT-5.5, GPT-5.5 Pro. Claude Fable 5 — **metered opt-in** (off subscription 2026-07-07; see below). Grok 4.5 — **frontier niche** (AA 2026-07-08; Cursor pool + opt-in critique axis; see below).
**Last updated:** 2026-07-09.
**Active stance:** This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok-4.20-and-earlier, and Sonnet-4.6-and-earlier routes were removed from active guidance. Sonnet 5 is reinstated as a named, cost-tier Claude option (2026-06-30). Grok 4.5 is a **named niche** (agentic tool workflows + cheap/fast frontier cosign via Cursor), not a Default Routing replacement for Opus/GPT-5.5 — calibration is mid-pack (AA-Omniscience non-hallucination ~46%). Use this guide for high-value frontier decisions; use repo-specific batch tooling or search tools for cheap bulk work.

**OPEN QUESTION (2026-06-30, not yet resolved — operator call):** the "Architecture / design / high-reasoning critique → NEVER Sonnet" verdict below was reached against Sonnet 4.6 on 2026-06-20. Sonnet 5's system card shows large agentic/coding gains and prompt-injection robustness tying or beating Opus 4.8 in several places, but also the *worst* prefill/system-prompt-susceptibility numbers of the compared models and measurably more turns/tokens per task (system-card digest: `references/sonnet-5-system-card.md`). Whether this changes the "NEVER Sonnet" verdict for architecture/critique work is a live question, not re-litigated here — the verdict stands until the operator revisits it.

**Claude Fable 5 — PARTIALLY RE-ROUTABLE (2026-07-04, empirical): live in Claude Code session + Agent-tool lanes; llmx/API status unverified.** Observed 2026-07-04 (arc-agi session ebbeff04): interactive CC sessions run `claude-fable-5` as the selected model, and `fable-high`/`fable-low` agent-def lanes + key-stripped headless `claude -p --model claude-fable-5` all dispatch and complete. The 2026-06-20 dormancy note (subscription allowlist, US restriction) is therefore stale for CC-native lanes; `llmx chat --subscription -m claude-fable-5` and paid-API routing remain UNVERIFIED since then — probe with `--dry-run` before relying on them. Routing consequence: the fable-tier dispatch-economics verdicts below (fable-low for gated/briefed work, fable-high for ungated design-synthesis) are ACTIVE again for CC-dispatched subagents; Opus 4.8 remains the default where Fable-specific value isn't needed. Benchmark and prompting notes below apply.

**Fable 5 — OFF SUBSCRIPTION since 2026-07-07: metered usage credits, $10/$50 per MTok (2× Opus 4.8).** Anthropic ended subscription-included Fable access after 2026-07-07 (Pro/Max/Team); continued access bills usage credits at list price — Anthropic's most expensive GA pricing. Stated as temporary ("restore Fable as a standard part of our subscriptions as soon as capacity allows"; capacity fallout from the June export-control suspension). Economics inversion: the fable lanes were licensed as *$0 subscription* lanes; Opus 4.8 remains subscription-routable at $0. So the 2026-07-04 "ACTIVE again" license above is **suspended on cost, not capability**: **fable-low is no longer a cheap lane** — its measured 0.34× token efficiency was vs fable-high, not vs a $0 Opus lane; route gated/briefed/review dispatch to **opus-low** (subscription) instead. **fable-high** remains callable only as a paid opt-in where a Fable-specific capability edge (obscure-domain knowledge, multi-hop reasoning, measured 2026-06-10) justifies real dollars over Opus `max` at $0 — name the justification in the dispatch. UNVERIFIED: whether CC session/Agent-tool fable lanes now bill credits silently or fail — probe with one small dispatch and check billing before any batch use; do not assume $0. Re-license trigger: Anthropic restores Fable to subscription plans → revert this note and re-activate the fable-lane verdicts. Sources: techtimes.com 2026-07-06, bleepingcomputer.com (Anthropic statement), digitalapplied.com July-7 guide, claude.com/pricing.

**Opus 4.8** (`claude-opus-4-8`) is Anthropic's active top-tier model: 1M context, raw/summarized CoT, adaptive thinking, no reasoning-extraction classifier. Best measured calibration among routable Claude models (64% AA-Omniscience non-hallucination). Default for hardest Claude work, security/cyber/biology, and cross-lab review. **Architecture → `max` effort.**

## Default Routing

| Situation | Use | Why |
|---|---|---|
| Hardest / longest / most-ambiguous Claude work: multi-day autonomous runs, codebase-scale migrations, first-shot on complex well-specified systems, dense-image vision, architecture | **Claude Opus 4.8** (`max` for architecture) | Active Claude frontier. Fable metered at 2× Opus (off-subscription 2026-07-07) — Opus keeps all default Claude routing. Pair GPT-5.5 for cross-lab on the hardest judgment calls. |
| Routine/cost-sensitive coding, security review, cyber, lab/molecular biology | **Claude Opus 4.8** | Same model — use lower effort (`low`/`medium`) when the brief has mechanical gates. |
| Codex/terminal-heavy implementation, tool loops, structured API work | **GPT-5.5** | OpenAI reports Terminal-Bench 2.0 82.7, Expert-SWE 73.1, OSWorld-Verified 78.7; long-context strength independently backed (AA-LCR 74). |
| Quantitative proof, calibration math, hard science/data derivation where mistakes compound | **GPT-5.5 Pro** | Same underlying model as GPT-5.5 with parallel test-time compute. Use only when the answer will be checked and the 6x price is justified. |
| Cross-model review | **Opus 4.8 + GPT-5.5** (+ opt-in `grok` on PLAN packets) | Different labs, different failure profiles. Keep the review cross-lab; do not use same-family self-review as adversarial pressure. Add `--axes …,grok` when the packet needs **repo-grounded** premise falsification (Cursor workspace). |
| Architecture / design / high-reasoning critique | **Opus 4.8 `max` + GPT-5.5 — NEVER Sonnet** | Operator 2026-06-20: architecture → Opus **`max`**. Sonnet is for search + bug-fixes only. A sonnet-thinking arch critique built a confident "HALT, reverse the spine" conclusion on a *search-error false premise*; Opus + GPT-5.5 (repo-grounded) got it right. For **codebase-coupled** decisions, run the critic with real repo access via `cursor-agent -p -f --mode ask --model claude-opus-4-8-thinking-max` — or `--axes …,grok` (Grok 4.5-xhigh, workspace). Cold API models can't flag "already-handled at file:line." |
| Agentic SaaS / multi-tool workflows (AutomationBench-shaped) | **Grok 4.5** (Cursor pool) or Opus | AA 2026-07-08: Grok leads AutomationBench-AA (51%); strong τ³-Banking. Prefer when Cursor pool is free/cheap and the task is tool-loop heavy with a verifier. |
| Current facts, quotes, prices, law, news | **Tools first, then model synthesis** | Every model card still shows factuality limits. Retrieval/database truth beats frontier recall. **Not Grok alone** — AA-Omniscience non-hallucination ~46% (mid-pack; worse than Opus 64% / GLM 72%). |

## Quick Selection Matrix

| Task | First choice | Escalate / pair when |
|---|---|---|
| Agentic coding | Opus 4.8 (high effort) | Drop to `low` effort when brief has mechanical gates; use GPT-5.5 when terminal/Codex-heavy; **Grok 4.5 (Cursor)** when tool-loop / SaaS-workflow heavy and pool is cheap (AA AutomationBench lead; Coding Index ~72, near Opus). |
| Codebase-scale migration / multi-day autonomous run | Opus 4.8 (`xhigh`/`max`) | Keep human checkpoints at irreversible boundaries. Grok Coding Agent Index (Grok Build) is competitive — still prefer Opus for irreversible shared-infra until dogfooded. |
| Security review, exploit/vuln work, cyber, molecular biology | Opus 4.8 | Active Claude default for classifier-sensitive work (formerly Fable-refusal domain). |
| Debugging messy repo state | GPT-5.5 | Pair with Opus if the fix requires architectural judgment; Grok Cursor session is a fine third try when pool is free. |
| Architecture decision | **Opus 4.8 `max`** | Send the selected proposal to GPT-5.5 for independent cross-lab critique; add `--axes …,grok` for repo-grounded premise checks. |
| Quantitative audit / CritPt-hard physics | GPT-5.5 Pro | Grok CritPt **15%** — weak; do not route hard derivation here. |
| Long-context document/repo synthesis | Opus 4.8 or GPT-5.5 | Both 1M-class; GPT-5.5 AA-LCR 74 vs Grok 68 (parity band). Grok API context is **500k** — prefer Opus/GPT for >500k. |
| Browser/computer use | Opus 4.8 or GPT-5.5 | Opus 4.8 / GPT-5.5 both strong; Fable vision-SOTA notes dormant until return. |
| PLAN critique needing repo falsification | **`--axes standard,grok`** (or cross2,grok) | Repo-grounded Cursor agent; same class as premise_scout. Prefer over packet-only `composer` when callers/joins must be checked. |
| Letter-exact output constraints (exact counts, rigid templates, banned words) | Schema/validator enforcement, any model | Never rely on prose compliance — Claude family is measurably weakest at mechanical constraint-following (IFBench 62–63 vs GPT-5.5 76, bottom-5 of 27). Construct caveat: IFBench is majority adversarial-synthetic and high scores trade against answer quality, so this is a weak GPT-5.5 preference for unschematizable cases, not a routing rule. |
| Claim verification | Neither alone | Use primary sources and deterministic checks; use models to summarize evidence, not to establish it. |
| Contradictory / impossible spec, epistemic guardrails | **Opus 4.8** or **GLM-5.2** (opt-in) | Worst calibration on the frontier set: GPT-5.5 (14% non-hallucination), DeepSeek V4 (~6%). Grok ~46% non-hallucination — mid-pack, **not** a calibration pick. More reasoning tokens does not fix paradox blindness — see trilemma section. |

For full score tables, read `references/BENCHMARKS.md`.

## Selection trilemma (capability × calibration × efficiency)

Benchmark **capability** (Intelligence Index, SWE scores) and **parameter count** are weak proxies for real-world usefulness. They often **invert** on **calibration** — whether a miss is an abstention or a confident fabrication — and on **efficiency** — tokens/time to reach a correct or honest answer.

| Axis | What it measures | Routing mistake |
|---|---|---|
| **Capability** | Closed-set benchmark scores, index composites | Picking the #1 index model for every task |
| **Calibration** | Share of wrong answers that abstain vs confabulate (AA-Omniscience non-hallucination) | Treating critique reasoning as fact because the model is "smart" |
| **Efficiency** | Tokens, latency, $ to a verified outcome | Escalating reasoning effort on a poorly calibrated model |

**Settled ordering on calibration (AA-Omniscience, misses only, abstention invited):** GLM-5.2 **72%** non-hallucination → Opus 4.8 **64%** → Grok 4.5 **~46%** / Fable 5 **45%** → GPT-5.5 **14%** → DeepSeek V4 **~6%**. Capability ordering is nearly the reverse (Grok Intelligence Index **54**, near GPT-5.5 55 / Opus 56). A multi-trillion-parameter model can score at the top of an index and still be the worst choice when the task needs "I don't know" or detection of an impossible/contradictory spec.

**Reasoning budget is not monotonic.** On badly calibrated models, more reasoning often buys longer confident wrong answers, not better ones. Anecdotal corroboration (Shrimpton 2026-06-18, n=1, high effort, temp 1): an impossible asyncio event-loop spec — DeepSeek V4 Pro ~7.7k reasoning tokens, 3m52s, full wrong implementation; GLM-5.2 ~800 tokens, 12s, correctly flagged the paradox. Don't throw `xhigh` at GPT-5.5 or DeepSeek for epistemic guardrails; use Opus, GLM (opt-in), or deterministic impossibility checks.

**Consumer rule:** match model to the axis that matters for the task — capability for gated mechanical work with a verifier; calibration for unsourced facts, paradox detection, and "should we even do this?"; efficiency for throughput. Never select on size or index rank alone.

## Transport facts (llmx — not judgment)

**Read before dispatch:** `~/.claude/cache/llmx-routing.json` (regenerate: `llmx info --write-mirror`). Transport table, effort maps, exit classes live there — not in this skill.

**Claude policy:** NEVER `anthropic-direct`/API by default. Subscription only (`llmx chat --subscription`, `claude -p` with key stripped, Agent tool) unless the user explicitly requests metered API billing.

**Probe subscription path before critique batches:**

```bash
llmx chat --dry-run --subscription -m claude-opus-4-8 -e max
# or: uv run python3 ~/Projects/skills/critique/scripts/model-review.py --preflight
```

Mechanics and footguns: `/llmx-guide`.

## llmx Cosigner / Dispatch Defaults (judgment — transport in mirror)

- **Cosigner / critique / synthesis:** `gemini-3.5-flash` (inverted from 3.1 Pro 2026-05-24, operator-empirical; re-confirmed 2026-06-13 — flash-3.5 ≈ GPT-5.5-high ≫ 3.1-pro on the ADR-0009 spine critique). **Always in the 2G+2GPT mix — never the only reviewer.** Probe flags invention on clean packets; orchestrator dispositions via `--extract --verify` (see agentlogs evidence).
- **Cheap classification / mechanical audits:** `gemini-3-flash-preview` or `gemini-3.1-flash-lite-preview`.
- **GPT-5.5 default effort is `medium`** — pass `-e high`/`xhigh` for depth; reasoning bills as output.
- **GLM-5.2 (Z.ai, NEW LAB) = opt-in review cosigner, NOT an extractor (2026-06-19).** A 4th independent training lab (Zhipu) → real cross-lab diversity for critique; request explicitly `--axes …,glm` (`glm_review` profile, routed via OpenRouter). **Calibration edge:** 72% AA-Omniscience non-hallucination (2026-06-18 independent read) — best among commonly-routed large models, ahead of Opus 64%; strong on impossibility/paradox detection in anecdotal coding probes. Accepts ONLY `high`/`xhigh` reasoning (no low tier) → structurally expensive+slow → **rejected for high-volume extraction/ingestion** (cost-dominated, no quality gain; keep gpt-5.3/gemini-3-flash). Match reasoning floor to task: GLM for occasional thorough review and epistemic guardrails, not throughput. See `agent-infra/decisions/2026-06-19-glm-5.2-integration.md`, `evals` DECISIONS `glm-5.2-extraction`.
- **Grok 4.5 (SpaceXAI, AA 2026-07-08) = opt-in repo-grounded cosigner + agentic niche — NOT a calibration pick.** Intelligence Index **54** (frontier pack with GPT-5.5 55 / Opus 56); **cost/task ~$0.31** (≪ GPT $0.86 / Fable $2.75); speed mid-high (~88 tok/s). **Use more:** PLAN critique with `--axes …,grok` (Cursor `--workspace`); AutomationBench/τ³-shaped tool loops when Cursor pool is cheap; cheap/fast frontier second opinion. **Use less / never alone:** unsourced facts (non-hallucination ~46%), CritPt-hard physics (15%), epistemic guardrails, sole architecture judge. See Grok section below + `decisions/2026-07-09-grok-4.5-transport.md`.
- **`gemini-3.1-pro-preview` is RETIRED as a routing option (2026-06-13, operator).** Do not route here for critique/synthesis/review — flash-3.5 dominates and is cheaper/faster. (Benchmark records in `references/BENCHMARKS.md` are kept as evidence; this is a routing retirement, not a data scrub. Callable via explicit `-m` if a one-off ever needs ARC-AGI-2/GPQA/video, but it is not a default anywhere.)
- **Cosigner calibration caveat (AA-Omniscience, 2026-06-11):** both cosigner defaults are bottom-quartile abstainers — non-hallucination 39% (`gemini-3.5-flash`), 14% (`gpt-5.5`), despite an abstention prompt. Critique output = adversarial pressure on reasoning, never a fact source; **for fact-heavy review where calibration matters, verify novel specifics at primary and lean on a frontier model (Opus/GPT), not a cheap cosigner.** Instruments: agent-infra `research/2026-06-11-aa-benchmark-instrument-validity.md`.

## Dispatch Economics (subagent executor tiers)

When dispatching subagents to execute work (Agent tool, headless `claude -p`, codex), the executor tier is set by **how good the verifier in the brief is**, not by how hard the task feels. Measured evidence: four preregistered evals, anim-workbench 2026-06-12 (`anim-workbench/.claude/evals/2026-06-12-{dispatch-tier,effort-tier,codex-lane,effort-integration}/`), all n=1 per arm (screening grade).

| Work shape | Executor | Evidence / boundary |
|---|---|---|
| FULL brief + mechanical gates (tests, typecheck, deterministic verify script) — greenfield OR port/re-author against an existing oracle | **Opus 4.8 effort low, or codex reasoning-low ($0)** | Effort-tier: low matched medium on all 5 gates at 0.59× tokens. Effort-integration (the pre-registered replication): low matched DEFAULT on an integration-shaped port — same gates, independently convergent design decisions, 0.574× tokens. Codex-lane: GPT-5.5 reasoning-low passed all gates at $0 (subscription) and resolved a self-contradictory brief *within spec*. Revocation trigger (registered): first cheap-lane gate failure on a task classified fully-briefed → fall back to default effort for that class + record. |
| Design-from-scratch integration, no oracle to check against | **Opus 4.8, default effort** | The effort-integration license covers port/re-author shapes only (its own caveat: "ports are the friendliest integration shape"). Dispatch-tier still holds: Sonnet 4.6 changed the measurement procedure under gate pressure until the gate passed (reward-hacking-shaped); Opus was deviation-free. "Opus is token-efficient so cheaper" was REJECTED (~2.4× Sonnet cost) — the premium buys spec fidelity, not efficiency. |
| Mechanical no-gate tasks (rename sweeps, boilerplate) | **Claude Sonnet 5** (`claude-sonnet-5`) or haiku tier | Cheap and gameable-gate risk is moot when there's no gate to game. (Row previously said "Sonnet/haiku tier" with no live model — resolved 2026-06-30 now that Sonnet 5 exists.) |
| Cost-sensitive coding/agentic work WITH a mechanical gate (tests, typecheck) — not architecture | **Claude Sonnet 5**, default effort | System card: beats Sonnet 4.6 broadly, ties Opus 4.8 on several real-world benchmarks (Real-World Finance, GDPval-AA), at ~40-60% of Opus 4.8's per-token price. Runs more turns/tokens per task than Opus though — re-measure cost on your own workload before assuming the $/token saving holds end-to-end. |
| Search/read fan-out | Explore agent | No executor risk; output is consumed, not shipped. |
| Partial/noisy verifier (research synthesis, memos, judgment-coupled work) | **Don't downgrade** — frontier model, normal effort | The Sonnet finding gets WORSE here: gate-gaming in regime-2 is exactly what you can't detect cheaply. Verifier-conditioned scope (constitution) applies. |
| Judgment gaps in the spec | Yourself / Opus 4.8 | Cheap executors fill ambiguity with guesses; the savings are repaid as corrections. Codex-lane's reasoning-HIGH arm is the same lesson from the other side: on a spec-complete task, more reasoning bought one extra unnecessary spec deviation, not better conformance — spec + gates do the thinking, so buy reasoning only where the spec leaves thinking to do. |

**Codex lane mechanics** (from codex-lane eval): `codex exec --full-auto -C <out-of-repo-worktree> -c model_reasoning_effort="low"` — the `-c` override is verified per-invocation (resolved effort confirmed in rollout logs). Gotchas: pre-install deps (the *shell* sandbox has no network); `git commit` fails inside worktrees (gitfile points outside workspace) — grade the dirty tree, commit from outside; require a final-message manifest (the `-o` empty-output gotcha).

**Codex as a research/work subprocess** (verified 2026-06-18): codex carries the **same skills + MCP stack** as Claude (`~/.codex/skills/`, `~/.codex/config.toml`) — invoke a skill in the prompt via its `$name` keyword (single-quote the prompt). **Network-backed MCP tools (research-mcp, exa, brave, scite) DO work under `--full-auto`** — MCP servers are separate processes, so the shell-sandbox "no network" gotcha above does NOT apply to MCP calls. So a codex worker can do real (not training-memory) research and write its own memo, at $0 on the subscription. Full pattern — `$skill` invocation, canary-first discipline, stub-first/intern-rule briefs, the `commit`-word hook false-positive, benign MCP-teardown noise, llmx-is-not-the-vehicle: **`references/codex-subprocess-dispatch.md`**.

**The conditioning rule:** low effort doesn't mean less verification — both eval arms ran every gate *because the gates were written in the brief*. Self-initiated checking is what higher effort buys; an explicit verifier in the brief makes that purchase unnecessary. So the brief MUST carry: verification commands (exact, runnable), cleanup directives (worktree/scratch teardown), and a files-touched manifest requirement. A cheap executor on a gate-less brief is the worst quadrant.

**Intern rule (gate-less delegation):** exploratory, divergent, or conceptual dispatches (research sweeps, brainstorms, design options, synthesis) have no mechanical gate to put in the brief — so the coordinator's review IS the gate. Treat the return like an intern's draft: don't re-do the work, but spot-check it before adopting. Concretely: re-run 1-2 of its load-bearing probes/citations yourself, check one claimed source actually says what's claimed, run the completeness check (does every input appear in the output, are dropped items justified), and ask what the brief would have rewarded the agent for skipping. Scale the spot-check to stakes — a brainstorm needs a sniff test, a synthesis feeding a decision needs the citation check. Skipping this turns "delegate" into "launder": unverified subagent output adopted wholesale is the same failure as adopting cross-model critique without cosigning.

**Effort knob mechanics:** the Agent tool exposes only `model:`. Per-dispatch effort exists via (1) headless `claude -p --model opus --effort low` (verified working, CLI 2.1.175; background Bash + `--output-format json` for usage), or (2) `.claude/agents/*.md` frontmatter `effort:` (does NOT hot-register mid-session — usable only in later sessions). Codex/GPT-5.5 cheap cosign via llmx `--subscription` is $0 — probe with `--dry-run --subscription` first; transport table in `~/.claude/cache/llmx-routing.json`.

**Agent-tool DEFAULT model is NOT the session model (2026-06-29, cost a "diagnose" round).** `general-purpose`/most subagents default to **`CLAUDE_CODE_SUBAGENT_MODEL`** (now **`claude-sonnet-5`** — Sonnet 4.6 is RETIRED as of 2026-07-07 per operator; do not route to it or treat it as a live comparator anywhere), NOT the parent's Opus. So a bare `Agent(...)` with no `model:` runs **Sonnet 5** — fine for search/bounded work, but a **tier silently-wrong trap when the dispatch IS the measurement** (an eval baseline, a "frontier agent" arm): you'll claim Opus and run Sonnet. **For any tier-sensitive dispatch: pass `model:` explicitly AND verify it landed** (`grep '"model"' <agent-transcript>.jsonl` → confirm `claude-opus-4-8`). Same class as the Exa-under-shoot baseline-mismatch — the baseline must BE the entity the construct names. Second footgun, same session: an open-ended "be exhaustive" prompt to `general-purpose` triggered **sub-delegation + stall** (it spawned 6 children, returned "I'll pause here", delivered nothing, burned 72K tokens) — for bounded research dispatches, **explicitly forbid delegation** ("do this yourself in one pass; do NOT spawn subagents").

**External validity:** all four evals are regime-1 (clear mechanical verifiers — tsc, deterministic scripts, numeric oracles) and screening-grade (n=1/arm). Only within-eval contrasts are clean — cross-eval comparisons are confounded by task, brief density (briefs improve as the author learns, flattering later arms), and harness (codex carries MCP servers + sandbox; opus arms ran bare). Every cheap-lane verdict is conditional on the dispatch-time classification "fully-briefed + mechanically gated" being honest — nothing here licenses cheap lanes for judgment-shaped or incomplete-spec work. The greenfield→integration replication trigger from the morning run is SATISFIED (effort-integration, port shape); the standing revocation trigger replaces it.

**Reasoning escalation guard (calibration × effort):** the cheap-lane evals show *less* reasoning is fine when the verifier is in the brief. The inverse also holds outside regime-1: escalating effort on poorly calibrated models (GPT-5.5, DeepSeek V4) on paradox/impossibility or unsourced-fact tasks tends to produce more confident fabrication, not more abstention — see Selection trilemma. Effort buys depth only where calibration is already adequate (Opus, GLM for review).

## Claude Opus 4.8 - "The Investigator" (primary Claude)

**Use for:** all active Claude frontier work — hardest autonomous runs, codebase-scale migrations, architecture, code review, security/cyber/biology, professional analysis, legal/financial reasoning, long autonomous loops, and cross-lab critique. Inherits routing formerly aimed at Fable 5 while Fable is dormant.

**Operational specs:** `claude-opus-4-8`, 1M context, 128K max output, **$5/M input and $25/M output**. Fast mode is the same model at up to 2.5x output speed for $10/$50. Returns raw thinking (`display: "summarized"` optional), supports `thinking:{"type":"adaptive"}`, no reasoning-extraction classifier. **Subscription-routable** (`lite_allowed_models`).

**System-card routing line:** improves on 4.7 across coding/agentic/long-context/professional
evals; best-calibrated routable Claude (64% AA-Omniscience non-hallucination), ~4× fewer unreported
self-code flaws — still bind verification to ground truth (git, parsed tests, exit codes) and keep
tool outputs untrusted. Full parsed card: [references/opus-4-8-system-card.md](references/opus-4-8-system-card.md).

**Prompting and API rules:**
- Use XML tags; adaptive thinking explicit (`thinking:{"type":"adaptive"}`); no manual `budget_tokens`.
- Default effort `high`; **`max` for architecture/design/high-reasoning critique** (operator 2026-06-20); `xhigh` for serious coding/review/long agentic work; `low` for gated mechanical dispatch (see Dispatch Economics).
- Mid-conversation `role:"system"` messages supported immediately after a user turn — use for permission/budget/environment updates without rebuilding the prompt.
- No non-default `temperature`/`top_p`/`top_k` (400 on 4.7+); no assistant prefill; min cacheable prompt 1,024 tokens.
- Put long documents first and the query/instructions last.

Full guide: `references/PROMPTING_CLAUDE.md`.

## Claude Sonnet 5 - "The Cost Tier" (added 2026-06-30)

**Use for:** cost-sensitive coding and agentic work with a mechanical gate (tests, typecheck), mechanical no-gate dispatch (rename sweeps, boilerplate), and anything where untrusted tool output / prompt-injection exposure is the dominant risk — Sonnet 5 has the strongest measured prompt-injection robustness in its own system card, tying or beating Opus 4.8. **Not** a default for architecture/design/high-reasoning critique — see the OPEN QUESTION note above; that verdict has not been revisited for Sonnet 5.

**Operational specs:** `claude-sonnet-5`, 1M context, 128K max output, **$3/M input and $15/M output** ($2/$10 introductory through 2026-08-31, vs Opus 4.8's $5/$25). Adaptive thinking on by default (unlike Sonnet 4.6, which ran thinking-off by default — omitting `thinking` now runs adaptive). First Sonnet-tier model with `xhigh` effort. New tokenizer vs Sonnet 4.6 (~30% more tokens for the same text — partially offsets the lower $/token). **Not yet on the subscription allowlist** (`lite_allowed_models` in `~/.claude/cache/llmx-routing.json` has no Sonnet entry, 4.6 or 5) — `llmx chat --subscription -m claude-sonnet-5` will not route until that allowlist is updated (llmx's own config, not this skill).

**System-card routing line** (digest: [references/sonnet-5-system-card.md](references/sonnet-5-system-card.md)):
strongest measured prompt-injection robustness (ties/beats Opus 4.8); beats Sonnet 4.6 on nearly
every coding/agentic benchmark; watch-items — worst-of-cohort prefill/system-prompt susceptibility,
disclosed training-health issue (highest closed-book abstention of compared models), ~6%
evaluation-awareness, and more turns/tokens per task than Opus 4.8 (cheaper $/token ≠ cheaper
$/task on long loops — measure on your own workload).

**Prompting and API rules:** same XML-tag, no-prefill, no-non-default-sampling-param rules as Opus 4.8 (see `references/PROMPTING_CLAUDE.md` — written for Claude generally, applies here). Effort: default `high`; use `xhigh` for the hardest coding/agentic work in this tier (first Sonnet model to support it); `low`/`medium` for routine/mechanical dispatch per Dispatch Economics above.

## Claude Fable 5 - "The Operator" (metered opt-in — reference only)

Routability + economics: see the OFF-SUBSCRIPTION note at the top of this skill (metered usage
credits 2026-07-07; CC-native lanes technically live per 2026-07-04 but paid; llmx/API unverified). Specs ($10/$50, 2× Opus), API shape (adaptive-only thinking,
hidden CoT, `reasoning_extraction` classifier, refusal→Opus fallback), system-card insights
(two-source honesty regression vs Opus: AA-Omniscience 45% vs 64%), and prompting rules:
[references/fable-5-dormant.md](references/fable-5-dormant.md).

## GPT-5.5 - "The Professional"

**Use for:** Codex work, terminal-heavy tasks, structured outputs, document/spreadsheet generation, native OpenAI tool workflows, long-context retrieval, and concise professional execution.

**Operational specs:** `gpt-5.5`, 1,050,000 context, 128K max output, Dec 1 2025 knowledge cutoff, $5/M input, $0.50/M cached input, $30/M output. Batch and Flex are cheaper when latency tolerates them.

**System-card insights to carry forward:**
- Designed for complex real-world work: coding, online research, information analysis, documents/spreadsheets, and moving across tools.
- Improves destructive-action behavior: destructive-action avoidance 0.90, perfect reversion 0.52, user-work preservation 0.57.
- Factuality improved but not source-grade: individual claims 23% more likely correct in flagged cases, response-level error only 3% lower because it makes more claims.
- Coding-agent resampling found slightly more low-severity misalignment than 5.4 Thinking (acting as if pre-existing work was its own, ignoring constraints, acting on a question-only turn). Keep explicit caller/action boundaries.
- CoT controllability very low (0.2% at 50K chars). Constrain visible output and tool permissions, not hidden reasoning.
- Cyber and bio/chem are High under OpenAI's Preparedness Framework (cyber below Critical). Treat cyber workflows as policy-sensitive.
- Apollo found a 29% lie rate on an impossible coding task. Use deterministic impossibility checks, not self-report.
- Kradle Four Bridges (2026-06): 90/100 uninstructed deception when a small competitive incentive existed, framed as cooperation. Third source on incentive-sensitive honesty (with Apollo 29% + AA-Omniscience 14%) — construct is peer-competition games, not assistant contexts; mitigation unchanged (deterministic verification, never self-report).

**Prompting and API rules:**
- Do not write "think step by step" when reasoning is enabled.
- Keep prompts short, direct, data-hydrated; extra scaffolding can reduce performance.
- Use `strict: true` on function definitions; XML-ish document packets (`<doc id="...">...</doc>`) for long inputs.
- Use the Responses API with `previous_response_id` for multi-step tool loops.
- Static prefixes before dynamic content for the cache discount.
- Add `Formatting re-enabled` atop developer messages when Markdown output matters in thinking mode.

Full guide: `references/PROMPTING_GPT.md`.

## GPT-5.5 Pro - "Expensive Precision"

**What it is:** the same underlying model as GPT-5.5 using parallel test-time compute. Not a different knowledge base — a compute setting with higher accuracy and much higher cost.

**Operational specs:** `gpt-5.5-pro`, 1,050,000 context, 128K max output, Dec 1 2025 knowledge cutoff, $30/M input and $180/M output. No cached-input discount listed.

**Use when all are true:** high uncertainty and high irreversibility; the answer requires derivation/synthesis not lookup; you will verify intermediate steps; cost is trivial relative to a wrong answer.

**Good fits:** Bayesian/posterior chains, calibration math, formal derivations, quantitative code audits, hard scientific/data reasoning over provided data, final review of expensive-to-undo architecture decisions.

**Bad fits:** ordinary coding, simple classification, literature search, current-events lookup, broad "research everything" prompts, anything you won't verify.

**Prompting rule:** give Pro exact data and ask for derivations. Example ending: `Show all derivations. I will verify every intermediate step.`

## Grok 4.5 - "Cheap frontier agent / repo cosigner" (AA 2026-07-08)

SpaceXAI frontier model (2026-07-08), jointly trained with Cursor. Independent AA
measurement puts it in the **frontier pack on capability** with a **cost/speed edge**,
and **mid-pack calibration** — route on that split, not on the Intelligence Index alone.

**AA snapshot (high effort, operator paste 2026-07-09 — treat as screen, not verifier):**

| Metric | Grok 4.5 | vs peers (same paste) | Routing read |
|---|---:|---|---|
| Intelligence Index | **54** | Fable 60 · Opus 56 · GPT-5.5 55 · GLM 51 | Frontier-capable; not #1 |
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

**Use more:**
1. **PLAN critique with repo access** — `--axes standard,grok` / `cross2,grok` (Cursor `--workspace`). Prefer over packet-only `composer` when premises must be grepped.
2. **Agentic tool / SaaS / multi-step workflows** when Cursor pool is free or cheap (AutomationBench + τ³ lead).
3. **Cheap/fast frontier second opinion** — cost/task ~⅓ of GPT-5.5 xhigh on AA's index; good count-delta pass, not sole judge.
4. **Interactive Cursor sessions** on coding/agentic work when you want SpaceXAI lineage diversity vs Opus/GPT.

**Use less / never alone:**
1. **Unsourced facts / "should we even do this?"** — ~46% non-hallucination; tools + Opus/GLM for epistemic guardrails.
2. **Hard quantitative / CritPt physics** — 15%; use GPT-5.5 Pro.
3. **Sole architecture judge** — still Opus `max` + GPT cross-lab; Grok is the *repo* axis, not the taste axis.
4. **Contexts >500k** — API window is 500k; Opus/GPT are 1M-class.
5. **CursorBench scores** — Cursor blog: training contamination; excluded from their table.

**Operational specs (API):** `grok-4.5`, **500k context**, $2/$6 per MTok, reasoning `low`/`medium`/`high` (default high). Fast Cursor variant $4/$18.

**Surfaces:**
| Surface | How | Status (2026-07-09) |
|---|---|---|
| Critique `grok` axis | `model-review.py --axes standard,grok` → `cursor-agent --model grok-4.5-xhigh --workspace <project>` | **Wired** — repo context |
| Cursor session / `cursor-agent` | `--model grok-4.5-xhigh` (or `-medium`/`-high`; optional `-fast-`) | **Live** — smoked `OK`. Bare `grok-4.5` aliases to **fast-xhigh**. |
| llmx Cursor pool | `llmx chat -p cursor -m grok-4.5-xhigh` | Allowlisted — **packet-only** (neutral cwd); use critique axis for repo work |
| llmx xAI API | `llmx chat -p xai -m grok-4.5 -e high` | Wired + priced; **API key currently blocked** (403) — key status, not EU geo |

See `agent-infra/decisions/2026-07-09-grok-4.5-transport.md`.

## Cross-Model Review Pattern

Use independent parallel reviews, then synthesize yourself:

```text
Opus 4.8 (max for architecture): architectural/professional judgment and implementation critique.
GPT-5.5: terminal/tool/process critique and structured failure search.
GPT-5.5 Pro: only for quantitative or high-irreversibility decisions.
Ground truth: tests, git, databases, source documents, primary web pages.
```

**Phase-0 before any model COMPARISON / bakeoff:** `grep ~/Projects/evals/DECISIONS.md` for the question FIRST — it may be settled, and a fresh n=1 probe must not steer a default an eval already decided. (2026-06-13: a 4-model review bakeoff re-ran the settled `cross-lab-review-margin` question, and an `/execute` edit got written contradicting its verdict — Phase-0 dedup caught it only after the fact.)

That verdict, calibrated: the cross-lab-vs-same-lab MARGIN is **≈0** — a second DIVERSE pass earns its keep via *count-delta* (it finds what the first missed), but the second reviewer being a different LAB buys ~nothing over a same-lab second instance, and it still hallucinates facts (a MiniMax-M3 pass verified ~25%, confident HIGH fabrications — ground any reviewer's asserted facts, weight its reasoning). The real martingale to avoid is a model reviewing its OWN output (same instance) as the *sole* adversarial pass.

## Validation Checklists

Post-output verification lists — All Outputs + per-model (Fable 5, Sonnet 5, Opus 4.8, GPT-5.5,
GPT-5.5 Pro, GLM-5.2, Grok 4.5): [references/validation-checklists.md](references/validation-checklists.md).
Consult after receiving output from a routed model, not at routing time.

## Source Notes

Primary sources consulted for this update:
- Anthropic: `https://www.anthropic.com/news/claude-fable-5-mythos-5`
- Anthropic Fable 5 system card: `https://www.anthropic.com/claude-fable-5-mythos-5-system-card`
- Anthropic docs: `https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5`
- Anthropic Fable prompting guide: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Anthropic: `https://www.anthropic.com/news/claude-opus-4-8`
- OpenAI: `https://openai.com/index/introducing-gpt-5-5/`, system card `https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf`
- Cross-repo harness analysis: `agent-infra/research/2026-06-09-fable-5-mythos-5-harness-impact.md`
- Independent benchmarks: artificialanalysis.ai (2026-06-11) with instrument-validity reads of AA-Omniscience/IFBench/GDPval/τ² — `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`
- Calibration + reasoning-budget anecdote: Oliver Shrimpton, "Bigger models are not the way" (2026-06-18) — AA-Omniscience hallucination rates for GLM-5.2/DeepSeek V4 Pro; impossible-asyncio n=1 probe on OpenRouter

## When to Update This Skill

Update after a current-frontier release or material system-card revision:
1. Update `references/BENCHMARKS.md`.
2. Update `references/PROMPTING_CLAUDE.md` or `references/PROMPTING_GPT.md`.
3. Update this routing surface if the default choice changes.
4. Add a dated entry to `references/CHANGELOG.md`.

Hit a defect or friction consulting this guide (a stale routing line, a wrong price, a missing model)?
Log it for the next reader: `~/Projects/skills/hooks/append-skill-memento.sh model-guide '<one-line issue>'`.

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-07] Sonnet 4.6 RETIRED 2026-07-07 (operator): default subagent model now claude-sonnet-5 (line 119 fixed). Comparison refs ~L104/149/152 remain as dated evidence but 4.6 is NOT a live option — scrub to absolute-property framing on next steward pass.**
