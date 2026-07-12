---
name: model-guide
description: "Use when: choosing frontier model/effort for a task class (Claude Opus 4.8, GPT-5.6 Sol/Terra/Luna). Fable 5 METERED since 2026-07-07 (off subscription, 2× Opus) — fable lanes are paid opt-ins, and the Agent tool currently can't reach Fable at all (routing bug, see Verified Transport). NOT transport flags (/llmx-guide)."
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Select between the current frontier models and prompt them correctly.

**Models covered:** Claude Opus 4.8 (primary Claude), Claude Sonnet 5 (cost-tier Claude), GPT-5.6 Sol / Terra / Luna (GA 2026-07-09; GPT-5.5 removed). Claude Fable 5 — **metered opt-in** (off subscription 2026-07-07; see below). Grok 4.5 — **frontier niche** (AA 2026-07-08; Cursor pool + opt-in critique axis; see below).
**Last updated:** 2026-07-12.
**Active stance:** This skill no longer maintains a broad model zoo. Older GPT, Gemini, Grok-4.20-and-earlier, and Sonnet-4.6-and-earlier routes were removed from active guidance. Sonnet 5 is reinstated as a named, cost-tier Claude option (2026-06-30). Grok 4.5 is a **named niche** (agentic tool workflows + cheap/fast frontier cosign via Cursor), not a Default Routing replacement for Opus/GPT-5.6 Sol — calibration is mid-pack (AA-Omniscience non-hallucination ~46%). Use this guide for high-value frontier decisions; use repo-specific batch tooling or search tools for cheap bulk work.

**OPEN QUESTION (2026-06-30, not yet resolved — operator call):** the "Architecture / design / high-reasoning critique → NEVER Sonnet" verdict below was reached against Sonnet 4.6 on 2026-06-20. Sonnet 5's system card shows large agentic/coding gains and prompt-injection robustness tying or beating Opus 4.8 in several places, but also the *worst* prefill/system-prompt-susceptibility numbers of the compared models and measurably more turns/tokens per task (system-card digest: `references/sonnet-5-system-card.md`). Whether this changes the "NEVER Sonnet" verdict for architecture/critique work is a live question, not re-litigated here — the verdict stands until the operator revisits it.

**Claude Fable 5 — status (2026-07-12).** Off the claude.ai Pro/Max/Team subscription since 2026-07-07: continued access is priced at metered usage credits, $10/$50 per MTok (2× Opus 4.8) — press/pricing-page sourced (techtimes.com, bleepingcomputer.com, claude.com/pricing); reconciliation against observed usage is open, see Verified Transport below. Fable is reachable via `llmx chat -m claude-fable-5` (claude-cli transport, confirmed working) and headless `claude -p --model claude-fable-5` (confirmed 2026-07-04) — **not reliably via the Agent tool**, where `fable-high`/`fable-low`-style dispatches currently serve `claude-sonnet-5` regardless of the pin (measured 2026-07-12, see Verified Transport — this is a mechanism bug, not a re-dormancy). Route gated/briefed/review dispatch to **opus-low** ($0 subscription); reach for Fable (via llmx, not the Agent tool) only with a named Fable-specific capability-edge justification over Opus `max`. Re-license trigger: Anthropic restores Fable to subscription plans.

**Opus 4.8** (`claude-opus-4-8`) is Anthropic's active top-tier model: 1M context, raw/summarized CoT, adaptive thinking, no reasoning-extraction classifier. Best measured calibration among routable Claude models (64% AA-Omniscience non-hallucination). Default for hardest Claude work, security/cyber/biology, and cross-lab review. **Architecture → `max` effort.**

## Verified Transport — what actually serves what (as-of 2026-07-12)

Routing *judgment* (which model you want) and routing *mechanism* (whether the lane you dispatch
to actually delivers that model) are different questions — this table is the second one, and it
currently has a serious hole. Re-verify any row before a tier-sensitive decision leans on it;
mechanisms drift faster than judgment.

| Lane | Actually serves | Status | Evidence / rederive |
|---|---|---|---|
| **Agent tool, any `subagent_type`, WITH an explicit `model:` param or agent-def `model:` frontmatter** (`fable-high`, `fable-low`, `opus-low`, custom agents) | **`claude-sonnet-5`** — the pin is silently ignored | **MEASURED, BROKEN** | arc-agi session 41f9b649, 2026-07-12: fable pin **5/5 self-reports** (propagated into `fable-high.md`/`fable-low.md`; includes this audit's own dispatch + sibling `induction-theorist`); opus pin **1/1 fresh probe** (`subagent_type: opus-low`, `model:"opus"` override, agent def also pinned `model: opus` — agent `a8afa4bad056a6f61` self-reported `claude-sonnet-5` anyway). **Bug generalizes past Fable** — treat every Agent-tool model pin as unverified until proven otherwise. Rederive: open the dispatch with "self-report your model ID from your own environment-info block, first line," read the answer back. |
| Agent tool, no `model:` param (bare `general-purpose` etc.) | `claude-sonnet-5` (`CLAUDE_CODE_SUBAGENT_MODEL`) | MEASURED, **correct** — this is the documented default, not the bug above | 2026-06-29 finding, unchanged |
| `llmx chat -m claude-fable-5` (claude-cli transport) | **Genuinely Fable** | MEASURED | `~/.claude/llmx-usage.jsonl` — 18 real completions through 2026-07-12 (e.g. 34,385 completion tokens at `reasoning_effort: max`). `grep claude-fable-5 ~/.claude/llmx-usage.jsonl \| tail`. **Currently the only proven way to guarantee Fable.** |
| Headless `claude -p --model claude-fable-5` (key-stripped) | Genuinely Fable | MEASURED (2026-07-04, arc-agi ebbeff04) | Dispatches and completes; not re-verified since — re-probe before relying on it for a batch. |
| `llmx chat --subscription -m claude-opus-4-8` / `-m gpt-5.6*` | Named model | Config-level, not self-report-verified | `~/.claude/cache/llmx-routing.json` `lite_allowed_models` confirms *routable*; llmx has no built-in "ask the model who it is" check yet. |
| `llmx chat --subscription -m grok-4.5` | **Mis-routes to `xai-api`** → 403 blocked key | **MEASURED, BROKEN** (2026-07-11) | `~/.claude/rules/llmx-routing.md`. Use `-p cursor -m grok-4.5-xhigh` or the critique `--axes …,grok` path instead — both confirmed live. |
| codex-cli / `llmx --subscription -m gpt-5.6*` | `gpt-5.6` family | MEASURED | `gpt-5.5` retired from the subscription allowlist 2026-07-10 (exit 2 on attempt) — don't route or price it anywhere. |

**Until the Agent-tool bug is fixed:** any Agent-tool dispatch where the model tier is
load-bearing (a cost claim, an eval arm, a "frontier vs cheap" comparison) needs a one-line
self-report opening the brief, read back before trusting the result. One line catches a silent
tier swap that otherwise bills or behaves as the wrong model.

**Fable cost status is unreconciled, not merely unverified:** the "$10/$50 metered" claim is
press/pricing-page sourced; the llmx usage log shows `claude-cli`-transport Fable calls
completing normally (large completions, zero errors) through 2026-07-12, after the cited
cutoff, and the log has no cost/auth-mode field to say which billing path fired. Whether Claude
Code's own OAuth entitlement is a separate pool from the claude.ai Pro/Max/Team plans the press
covered is **unverified (2026-07-12)** — check actual Console billing before a batch decision
hinges on "still $0" or "now expensive."

## Default Routing

Judgment below assumes the lane you dispatch to actually delivers the named model — confirm that against Verified Transport above before trusting a routing choice for a tier-sensitive dispatch.

| Situation | Use | Why |
|---|---|---|
| Hardest / longest / most-ambiguous Claude work: multi-day autonomous runs, codebase-scale migrations, first-shot on complex well-specified systems, dense-image vision, architecture | **Claude Opus 4.8** (`max` for architecture) | Active Claude frontier. Fable metered at 2× Opus (off-subscription 2026-07-07) — Opus keeps all default Claude routing. Pair GPT-5.6 Sol for cross-lab on the hardest judgment calls. |
| Routine/cost-sensitive coding, security review, cyber, lab/molecular biology | **Claude Opus 4.8** | Same model — use lower effort (`low`/`medium`) when the brief has mechanical gates. |
| Codex/terminal-heavy implementation, tool loops, structured API work | **GPT-5.6 Sol** (or **Luna** for everyday/cost) | GPT-5.6 suite GA 2026-07-09. Sol = flagship; **Luna ≈ prior GPT-5.5 perf at ~½ that price** ($1/$6); Terra = mid opt-in. Effort includes `max`. |
| Quantitative proof, calibration math, hard science/data derivation where mistakes compound | **GPT-5.6 Sol** + API `reasoning.mode=pro` (or ChatGPT Sol Pro) | No separate `gpt-5.6-*-pro` slug — Pro is a reasoning *mode* on Sol/Terra/Luna at the same $/MTok (more tokens). Use when the answer will be checked. |
| Cross-model review | **Opus 4.8 + GPT-5.6 Sol** (Luna OK for routine critique) (+ opt-in `grok` on PLAN packets) | Different labs, different failure profiles. Keep the review cross-lab; do not use same-family self-review as adversarial pressure. Add `--axes …,grok` when the packet needs **repo-grounded** premise falsification (Cursor workspace) — not `--subscription -m grok-4.5` (mis-routes, see Verified Transport). |
| Architecture / design / high-reasoning critique | **Opus 4.8 `max` + GPT-5.6 Sol — NEVER Sonnet** | Operator 2026-06-20: architecture → Opus **`max`**. Sonnet is for search + bug-fixes only. A sonnet-thinking arch critique built a confident "HALT, reverse the spine" conclusion on a *search-error false premise*; Opus + GPT-5.6 (repo-grounded) got it right. For **codebase-coupled** decisions, run the critic with real repo access via `cursor-agent -p -f --mode ask --model claude-opus-4-8-thinking-max` — or `--axes …,grok` (Grok 4.5-xhigh, workspace). Cold API models can't flag "already-handled at file:line." |
| Agentic SaaS / multi-tool workflows (AutomationBench-shaped) | **Grok 4.5** (Cursor pool) or Opus | AA 2026-07-08: Grok leads AutomationBench-AA (51%); strong τ³-Banking. Prefer when Cursor pool is free/cheap and the task is tool-loop heavy with a verifier. |
| Current facts, quotes, prices, law, news | **Tools first, then model synthesis** | Every model card still shows factuality limits. Retrieval/database truth beats frontier recall. **Not Grok alone** — AA-Omniscience non-hallucination ~46% (mid-pack; worse than Opus 64% / GLM 72%). |

## Quick Selection Matrix

| Task | First choice | Escalate / pair when |
|---|---|---|
| Agentic coding | Opus 4.8 (high effort) | Drop to `low` effort when brief has mechanical gates; use GPT-5.6 Sol/Terra when terminal/Codex-heavy; **Grok 4.5 (Cursor)** when tool-loop / SaaS-workflow heavy and pool is cheap (AA AutomationBench lead; Coding Index ~72, near Opus). |
| Codebase-scale migration / multi-day autonomous run | Opus 4.8 (`xhigh`/`max`) | Keep human checkpoints at irreversible boundaries. Grok Coding Agent Index (Grok Build) is competitive — still prefer Opus for irreversible shared-infra until dogfooded. |
| Security review, exploit/vuln work, cyber, molecular biology | Opus 4.8 | Active Claude default for classifier-sensitive work (formerly Fable-refusal domain). |
| Debugging messy repo state | GPT-5.6 Luna or Sol | Pair with Opus if the fix requires architectural judgment; Grok Cursor session is a fine third try when pool is free. |
| Architecture decision | **Opus 4.8 `max`** | Send the selected proposal to GPT-5.6 Sol for independent cross-lab critique; add `--axes …,grok` for repo-grounded premise checks. |
| Quantitative audit / CritPt-hard physics | GPT-5.6 Sol (`max` / pro mode) | Grok CritPt **15%** — weak; do not route hard derivation here. |
| Long-context document/repo synthesis | Opus 4.8 or GPT-5.6 Sol/Terra | Both 1.05M-class. Grok API context is **500k** — prefer Opus/GPT for >500k. |
| Browser/computer use | Opus 4.8 or GPT-5.6 Sol | Both strong; Fable vision-SOTA notes apply once it's reachable via a lane that isn't paid-metered or Agent-tool-broken. |
| PLAN critique needing repo falsification | **`--axes standard,grok`** (or cross2,grok) | Repo-grounded Cursor agent; same class as premise_scout. Prefer over packet-only `composer` when callers/joins must be checked. |
| Letter-exact output constraints (exact counts, rigid templates, banned words) | Schema/validator enforcement, any model | Never rely on prose compliance — Claude family is measurably weakest at mechanical constraint-following (IFBench 62–63 vs GPT-5.6-class 76, bottom-5 of 27). Construct caveat: IFBench is majority adversarial-synthetic and high scores trade against answer quality, so this is a weak GPT preference for unschematizable cases, not a routing rule. |
| Claim verification | Neither alone | Use primary sources and deterministic checks; use models to summarize evidence, not to establish it. |
| Contradictory / impossible spec, epistemic guardrails | **Opus 4.8** or **GLM-5.2** (opt-in) | GPT family historically weak on abstention (re-measure GPT-5.6 TBD); DeepSeek V4 (~6%). Grok ~46% — mid-pack, **not** a calibration pick. More reasoning tokens does not fix paradox blindness — see trilemma section. |

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
llmx chat --dry-run --subscription -m claude-opus-4-8 -e max
# or: uv run python3 ~/Projects/skills/critique/scripts/model-review.py --preflight
```

Mechanics and footguns: `/llmx-guide`.

## llmx Cosigner / Dispatch Defaults (judgment — transport in mirror)

- **Cosigner / critique / synthesis:** `gemini-3.5-flash` (inverted from 3.1 Pro 2026-05-24, operator-empirical; re-confirmed 2026-06-13 — flash-3.5 ≈ GPT-high ≫ 3.1-pro on the ADR-0009 spine critique). **Always in the 2G+2GPT mix — never the only reviewer.** Probe flags invention on clean packets; orchestrator dispositions via `--extract --verify` (see agentlogs evidence).
- **Cheap classification / mechanical audits:** `gemini-3-flash-preview` or `gemini-3.1-flash-lite-preview`.
- **GPT-5.6 default effort is `medium`** (suite supports `max` beyond `xhigh`) — pass `-e high`/`xhigh` for depth; reasoning bills as output.
- **GLM-5.2 (Z.ai, NEW LAB) = opt-in review cosigner, NOT an extractor (2026-06-19).** A 4th independent training lab (Zhipu) → real cross-lab diversity for critique; request explicitly `--axes …,glm` (`glm_review` profile, routed via OpenRouter). **Calibration edge:** 72% AA-Omniscience non-hallucination (2026-06-18 independent read) — best among commonly-routed large models, ahead of Opus 64%; strong on impossibility/paradox detection in anecdotal coding probes. Accepts ONLY `high`/`xhigh` reasoning (no low tier) → structurally expensive+slow → **rejected for high-volume extraction/ingestion** (cost-dominated, no quality gain; keep gpt-5.3/gemini-3-flash). Match reasoning floor to task: GLM for occasional thorough review and epistemic guardrails, not throughput. See `agent-infra/decisions/2026-06-19-glm-5.2-integration.md`, `evals` DECISIONS `glm-5.2-extraction`.
- **Grok 4.5 (SpaceXAI, AA 2026-07-08) = opt-in repo-grounded cosigner + agentic niche — NOT a calibration pick.** Intelligence Index **54** (frontier pack with Opus 56); **cost/task ~$0.31** (≪ GPT $0.86 / Fable $2.75); speed mid-high (~88 tok/s). **Use more:** PLAN critique with `--axes …,grok` (Cursor `--workspace`); AutomationBench/τ³-shaped tool loops when Cursor pool is cheap; cheap/fast frontier second opinion. **Use less / never alone:** unsourced facts (non-hallucination ~46%), CritPt-hard physics (15%), epistemic guardrails, sole architecture judge. `llmx chat --subscription -m grok-4.5` mis-routes to the blocked xAI API key (see Verified Transport) — use `-p cursor` or the critique axis. See Grok section below + `decisions/2026-07-09-grok-4.5-transport.md`.
- **`gemini-3.1-pro-preview` is RETIRED as a routing option (2026-06-13, operator).** Do not route here for critique/synthesis/review — flash-3.5 dominates and is cheaper/faster. (Benchmark records in `references/BENCHMARKS.md` are kept as evidence; this is a routing retirement, not a data scrub. Callable via explicit `-m` if a one-off ever needs ARC-AGI-2/GPQA/video, but it is not a default anywhere.)
- **Cosigner calibration caveat (AA-Omniscience, 2026-06-11):** both cosigner defaults are bottom-quartile abstainers — non-hallucination 39% (`gemini-3.5-flash`), prior GPT class 14% (re-measure Luna/Sol TBD), despite an abstention prompt. Critique output = adversarial pressure on reasoning, never a fact source; **for fact-heavy review where calibration matters, verify novel specifics at primary and lean on a frontier model (Opus/GPT), not a cheap cosigner.** Instruments: agent-infra `research/2026-06-11-aa-benchmark-instrument-validity.md`.

## Dispatch Economics (subagent executor tiers)

When dispatching subagents to execute work (Agent tool, headless `claude -p`, codex), the executor tier is set by **how good the verifier in the brief is**, not by how hard the task feels. Measured evidence: four preregistered evals, anim-workbench 2026-06-12 (`anim-workbench/.claude/evals/2026-06-12-{dispatch-tier,effort-tier,codex-lane,effort-integration}/`), all n=1 per arm (screening grade).

| Work shape | Executor | Evidence / boundary |
|---|---|---|
| FULL brief + mechanical gates (tests, typecheck, deterministic verify script) — greenfield OR port/re-author against an existing oracle | **Opus 4.8 effort low, or codex reasoning-low ($0)** | Effort-tier: low matched medium on all 5 gates at 0.59× tokens. Effort-integration (the pre-registered replication): low matched DEFAULT on an integration-shaped port — same gates, independently convergent design decisions, 0.574× tokens. Codex-lane: GPT reasoning-low passed all gates at $0 (subscription) and resolved a self-contradictory brief *within spec*. Revocation trigger (registered): first cheap-lane gate failure on a task classified fully-briefed → fall back to default effort for that class + record. |
| Design-from-scratch integration, no oracle to check against | **Opus 4.8, default effort** | The effort-integration license covers port/re-author shapes only (its own caveat: "ports are the friendliest integration shape"). Dispatch-tier still holds: Sonnet 4.6 changed the measurement procedure under gate pressure until the gate passed (reward-hacking-shaped); Opus was deviation-free. "Opus is token-efficient so cheaper" was REJECTED (~2.4× Sonnet cost) — the premium buys spec fidelity, not efficiency. |
| Mechanical no-gate tasks (rename sweeps, boilerplate) | **Claude Sonnet 5** (`claude-sonnet-5`) or haiku tier | Cheap and gameable-gate risk is moot when there's no gate to game. (Row previously said "Sonnet/haiku tier" with no live model — resolved 2026-06-30 now that Sonnet 5 exists.) |
| Cost-sensitive coding/agentic work WITH a mechanical gate (tests, typecheck) — not architecture | **Claude Sonnet 5**, default effort | System card: beats Sonnet 4.6 broadly, ties Opus 4.8 on several real-world benchmarks (Real-World Finance, GDPval-AA), at ~40-60% of Opus 4.8's per-token price. Runs more turns/tokens per task than Opus though — re-measure cost on your own workload before assuming the $/token saving holds end-to-end. |
| Search/read fan-out | Explore agent | No executor risk; output is consumed, not shipped. |
| Partial/noisy verifier (research synthesis, memos, judgment-coupled work) | **Don't downgrade** — frontier model, normal effort | The Sonnet finding gets WORSE here: gate-gaming in regime-2 is exactly what you can't detect cheaply. Verifier-conditioned scope (constitution) applies. |
| Judgment gaps in the spec | Yourself / Opus 4.8 | Cheap executors fill ambiguity with guesses; the savings are repaid as corrections. Codex-lane's reasoning-HIGH arm is the same lesson from the other side: on a spec-complete task, more reasoning bought one extra unnecessary spec deviation, not better conformance — spec + gates do the thinking, so buy reasoning only where the spec leaves thinking to do. |

**Every row above assumes the lane delivers the named model** — false for Agent-tool pins as of
2026-07-12 (Verified Transport). Self-report-check any row where the tier is what's being measured.

### Role → Lane (dispatch execution roles)

| Role | Current-best lane | Cost class | Evidence |
|---|---|---|---|
| **Synthesis** (open design problem, no oracle) | Opus 4.8 `max` | $0 subscription | Fable's synthesis edge is real (2026-06-12 fable-effort-architecture eval, low missed the orthogonal factoring high shipped) but currently unreachable via Agent tool — llmx-only, paid, until the routing bug is fixed. |
| **Briefed execution** (full brief + mechanical gates) | `opus-low` or codex reasoning-low | $0 subscription | anim-workbench 2026-06-12 effort-tier/effort-integration/codex-lane (low ≈ medium/default, 0.57-0.59× tokens). |
| **Review / cosign** | Opus 4.8 + GPT-5.6 Sol, cross-lab; opt-in GLM-5.2 or Grok-4.5 axis | $0 subscription (+~$0.30-1/call opt-in) | `evals/DECISIONS.md` `cross-lab-review-margin` (margin≈0, count-delta real); GLM decision 2026-06-19. |
| **Research / literature** | Cross-model fan-out by default: codex (`--lite research`) + Claude researcher — not single-model | $0 subscription | arc-agi feedback 2026-07-07: codex arm found a paper (PRISM, 2605.26998) the Claude arm missed. |
| **Scout fan-out** (parallel audits/debug scouts) | Cross-model default, concurrency-capped ≤2 concurrent opus subagents / ≤2 concurrent model workers each, else sequential | $0 subscription | arc-agi feedback 2026-07-08: 4 concurrent opus agents × openrouter fan-out (28-way) killed 3/4 mid-run — opus session-limit + provider contention, both real ceilings. |
| **OS-student serving** (open-weight model as trainee/actor under test) | Project-specific — measure, don't assume | GPU $/hr | Example only, not a universal verdict: arc-agi killed mistral-small-3.2-24B as an OS-tier base (dominated on every axis, 2026-07-11), rehabbed qwen3.6-27b via a no-think serving config, kept gemma-4-31B alive. Check your own project's standing-kills doc before reusing a verdict cross-project. Serving mechanics: `/modal` skill. |

**Codex lane mechanics** (from codex-lane eval): `codex exec --full-auto -C <out-of-repo-worktree> -c model_reasoning_effort="low"` — the `-c` override is verified per-invocation (resolved effort confirmed in rollout logs). Gotchas: pre-install deps (the *shell* sandbox has no network); `git commit` fails inside worktrees (gitfile points outside workspace) — grade the dirty tree, commit from outside; require a final-message manifest (the `-o` empty-output gotcha).

**Codex as a research/work subprocess** (verified 2026-06-18): codex carries the **same skills + MCP stack** as Claude (`~/.codex/skills/`, `~/.codex/config.toml`) — invoke a skill in the prompt via its `$name` keyword (single-quote the prompt). **Network-backed MCP tools (research-mcp, exa, brave, scite) DO work under `--full-auto`** — MCP servers are separate processes, so the shell-sandbox "no network" gotcha above does NOT apply to MCP calls. So a codex worker can do real (not training-memory) research and write its own memo, at $0 on the subscription. Full pattern — `$skill` invocation, canary-first discipline, stub-first/intern-rule briefs, the `commit`-word hook false-positive, benign MCP-teardown noise, llmx-is-not-the-vehicle: **`references/codex-subprocess-dispatch.md`**.

**The conditioning rule:** low effort doesn't mean less verification — both eval arms ran every gate *because the gates were written in the brief*. Self-initiated checking is what higher effort buys; an explicit verifier in the brief makes that purchase unnecessary. So the brief MUST carry: verification commands (exact, runnable), cleanup directives (worktree/scratch teardown), and a files-touched manifest requirement. A cheap executor on a gate-less brief is the worst quadrant.

**Intern rule (gate-less delegation):** exploratory, divergent, or conceptual dispatches (research sweeps, brainstorms, design options, synthesis) have no mechanical gate to put in the brief — so the coordinator's review IS the gate. Treat the return like an intern's draft: don't re-do the work, but spot-check it before adopting. Concretely: re-run 1-2 of its load-bearing probes/citations yourself, check one claimed source actually says what's claimed, run the completeness check (does every input appear in the output, are dropped items justified), and ask what the brief would have rewarded the agent for skipping. Scale the spot-check to stakes — a brainstorm needs a sniff test, a synthesis feeding a decision needs the citation check. Skipping this turns "delegate" into "launder": unverified subagent output adopted wholesale is the same failure as adopting cross-model critique without cosigning.

**Effort knob mechanics:** the Agent tool exposes only `model:`. Per-dispatch effort exists via (1) headless `claude -p --model opus --effort low` (verified working, CLI 2.1.175; background Bash + `--output-format json` for usage), or (2) `.claude/agents/*.md` frontmatter `effort:` (does NOT hot-register mid-session — usable only in later sessions). Codex/GPT cheap cosign via llmx `--subscription` is $0 — probe with `--dry-run --subscription` first; transport table in `~/.claude/cache/llmx-routing.json`.

**Agent-tool DEFAULT model is NOT the session model (2026-06-29).** `general-purpose`/most subagents default to **`CLAUDE_CODE_SUBAGENT_MODEL`** (now `claude-sonnet-5` — Sonnet 4.6 RETIRED 2026-07-07, never route to it), NOT the parent's Opus. A bare `Agent(...)` with no `model:` runs Sonnet 5 — fine for bounded work, a **tier silently-wrong trap when the dispatch IS the measurement** (an eval baseline, a "frontier agent" arm). **The previously-recommended fix — pass `model:` explicitly, then `grep '"model"'` the transcript — is not proven sufficient as of 2026-07-12:** the newer bug (Verified Transport) shows a pin can be requested and still not be served, and whether transcript-grep reflects the request or the actual serve is untested (ASSUMPTION: probably the request, since that would explain why grep-verification didn't already catch this). Require a first-line self-report instead — the one channel confirmed to reflect the true served model. Second footgun, same 2026-06-29 session: an open-ended "be exhaustive" prompt to `general-purpose` triggered **sub-delegation + stall** (6 children spawned, "I'll pause here," 72K tokens burned, nothing delivered) — for bounded research dispatches, **explicitly forbid delegation**.

**External validity:** all four evals are regime-1 (clear mechanical verifiers — tsc, deterministic scripts, numeric oracles) and screening-grade (n=1/arm). Only within-eval contrasts are clean — cross-eval comparisons are confounded by task, brief density (briefs improve as the author learns, flattering later arms), and harness (codex carries MCP servers + sandbox; opus arms ran bare). Every cheap-lane verdict is conditional on the dispatch-time classification "fully-briefed + mechanically gated" being honest — nothing here licenses cheap lanes for judgment-shaped or incomplete-spec work. The greenfield→integration replication trigger from the morning run is SATISFIED (effort-integration, port shape); the standing revocation trigger replaces it.

**Reasoning escalation guard (calibration × effort):** the cheap-lane evals show *less* reasoning is fine when the verifier is in the brief. The inverse also holds outside regime-1: escalating effort on poorly calibrated models (GPT family until re-measured, DeepSeek V4) on paradox/impossibility or unsourced-fact tasks tends to produce more confident fabrication, not more abstention — see Selection trilemma. Effort buys depth only where calibration is already adequate (Opus, GLM for review).

## Claude Opus 4.8 - "The Investigator" (primary Claude)

**Use for:** all active Claude frontier work — hardest autonomous runs, codebase-scale migrations, architecture, code review, security/cyber/biology, professional analysis, legal/financial reasoning, long autonomous loops, and cross-lab critique. Keeps Fable-tier routing by default: Fable is metered+paid and unreachable via the Agent tool (Verified Transport), so Opus is the practical default even where Fable might otherwise win on capability.

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

**Use for:** cost-sensitive coding and agentic work with a mechanical gate (tests, typecheck), mechanical no-gate dispatch (rename sweeps, boilerplate), and anything where untrusted tool output / prompt-injection exposure is the dominant risk — Sonnet 5 has the strongest measured prompt-injection robustness in its own system card, tying or beating Opus 4.8. **Not** a default for architecture/design/high-reasoning critique — see the OPEN QUESTION note above; that verdict has not been revisited for Sonnet 5. **Also the model the Agent tool silently substitutes when a `fable`/`opus` pin is dropped** (Verified Transport) — a result that "looks like Sonnet 5" (more turns/tokens, tying Opus on some benchmarks) may simply BE Sonnet 5 wearing another model's label; self-report before attributing quality to the pinned tier.

**Operational specs:** `claude-sonnet-5`, 1M context, 128K max output, **$3/M input and $15/M output** ($2/$10 introductory through 2026-08-31, vs Opus 4.8's $5/$25). Adaptive thinking on by default (unlike Sonnet 4.6, which ran thinking-off by default — omitting `thinking` now runs adaptive). First Sonnet-tier model with `xhigh` effort. New tokenizer vs Sonnet 4.6 (~30% more tokens for the same text — partially offsets the lower $/token). **Not yet on the subscription allowlist** (`lite_allowed_models` in `~/.claude/cache/llmx-routing.json` has no Sonnet entry, 4.6 or 5) — `llmx chat --subscription -m claude-sonnet-5` will not route until that allowlist is updated (llmx's own config, not this skill).

**System-card routing line** (digest: [references/sonnet-5-system-card.md](references/sonnet-5-system-card.md)):
strongest measured prompt-injection robustness (ties/beats Opus 4.8); beats Sonnet 4.6 on nearly
every coding/agentic benchmark; watch-items — worst-of-cohort prefill/system-prompt susceptibility,
disclosed training-health issue (highest closed-book abstention of compared models), ~6%
evaluation-awareness, and more turns/tokens per task than Opus 4.8 (cheaper $/token ≠ cheaper
$/task on long loops — measure on your own workload).

**Prompting and API rules:** same XML-tag, no-prefill, no-non-default-sampling-param rules as Opus 4.8 (see `references/PROMPTING_CLAUDE.md` — written for Claude generally, applies here). Effort: default `high`; use `xhigh` for the hardest coding/agentic work in this tier (first Sonnet model to support it); `low`/`medium` for routine/mechanical dispatch per Dispatch Economics above.

## Claude Fable 5 - "The Operator" (metered opt-in — reference only)

Routability + economics: see the status note at the top of this skill (metered usage
credits 2026-07-07; llmx/headless lanes confirmed live and paid, Agent tool currently can't
reach it at all — see Verified Transport). Specs ($10/$50, 2× Opus), API shape (adaptive-only thinking,
hidden CoT, `reasoning_extraction` classifier, refusal→Opus fallback), system-card insights
(two-source honesty regression vs Opus: AA-Omniscience 45% vs 64%), and prompting rules:
[references/fable-5-dormant.md](references/fable-5-dormant.md).

## GPT-5.6 suite — Sol / Terra / Luna (GA 2026-07-09)

**Naming:** generation number (`5.6`) + durable tier (`Sol` / `Terra` / `Luna`). Alias `gpt-5.6` → `gpt-5.6-sol`. **GPT-5.5 is removed** — do not route, upgrade, or price it.

| Tier | Model ID | $/MTok in/out | Role |
|---|---|---|---|
| **Sol** | `gpt-5.6-sol` | $5 / $30 | Flagship — coding, agentic, hard reasoning, cross-lab critique peer to Opus |
| **Terra** | `gpt-5.6-terra` | $2.50 / $15 | Mid tier — opt-in between Luna and Sol |
| **Luna** | `gpt-5.6-luna` | $1 / $6 | **Everyday GPT** — ≈ prior GPT-5.5 perf at ~½ that price; also mechanical/lint at low effort |

**Operational specs (all three):** 1.05M context, 128K max output, knowledge cutoff Feb 16 2026. Reasoning effort: `none` \| `low` \| `medium` \| `high` \| `xhigh` \| **`max`** (new beyond-xhigh). Default effort `medium`.

**Pro mode (not a separate slug):** API `reasoning.mode: "pro"` on Sol/Terra/Luna — more compute at the **same** $/MTok (higher token use). ChatGPT "Sol Pro" for Pro/Enterprise.

**`ultra`:** ChatGPT/Codex multi-agent setting (4 agents default) — not an llmx effort token yet; build via Responses multi-agent beta if needed.

**Cache (5.6+):** writes 1.25× uncached input; reads 90% discount; 30-min minimum cache life + explicit breakpoints.

**Routing defaults (this fleet):**
- Cross-lab / architecture / hardest Codex → **Sol** (`high`/`xhigh`/`max`)
- Critique `gpt_general` / everyday GPT → **Luna** (`medium`)
- Mechanical lint axis → **Luna** (`low`)
- Mid-cost bump → **Terra** (explicit `-m`)
- Subscription path: `llmx chat --subscription -m gpt-5.6-sol` (codex-cli)

**Calibration:** re-measure AA-Omniscience on 5.6 before trusting abstention. Until then, treat GPT critique as adversarial pressure on *reasoning*, not a fact source.

## Grok 4.5 - "Cheap frontier agent / repo cosigner" (AA 2026-07-08)

SpaceXAI frontier model (2026-07-08), jointly trained with Cursor. Independent AA
measurement puts it in the **frontier pack on capability** with a **cost/speed edge**,
and **mid-pack calibration** — route on that split, not on the Intelligence Index alone.

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

**Use more:**
1. **PLAN critique with repo access** — `--axes standard,grok` / `cross2,grok` (Cursor `--workspace`). Prefer over packet-only `composer` when premises must be grepped.
2. **Agentic tool / SaaS / multi-step workflows** when Cursor pool is free or cheap (AutomationBench + τ³ lead).
3. **Cheap/fast frontier second opinion** — cost/task ~⅓ of prior GPT xhigh on AA's index; good count-delta pass, not sole judge.
4. **Interactive Cursor sessions** on coding/agentic work when you want SpaceXAI lineage diversity vs Opus/GPT.

**Use less / never alone:**
1. **Unsourced facts / "should we even do this?"** — ~46% non-hallucination; tools + Opus/GLM for epistemic guardrails.
2. **Hard quantitative / CritPt physics** — 15%; use GPT-5.6 Sol pro-mode.
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

**Footgun (2026-07-11):** `--subscription -m grok-4.5` mis-routes to the blocked xAI API lane
above, not the working Cursor pool, despite being allowlisted — use `-p cursor` or the critique
axis instead. See Verified Transport.

See `agent-infra/decisions/2026-07-09-grok-4.5-transport.md`.

## Cross-Model Review Pattern

Use independent parallel reviews, then synthesize yourself:

```text
Opus 4.8 (max for architecture): architectural/professional judgment and implementation critique.
GPT-5.6 Sol: terminal/tool/process critique and structured failure search (hard).
GPT-5.6 Luna: everyday critique / mechanical (medium/low).
GPT-5.6 Sol + reasoning.mode=pro: quantitative or high-irreversibility decisions.
Ground truth: tests, git, databases, source documents, primary web pages.
```

**Phase-0 before any model COMPARISON / bakeoff:** `grep ~/Projects/evals/DECISIONS.md` for the question FIRST — it may be settled, and a fresh n=1 probe must not steer a default an eval already decided. (2026-06-13: a 4-model review bakeoff re-ran the settled `cross-lab-review-margin` question, and an `/execute` edit got written contradicting its verdict — Phase-0 dedup caught it only after the fact.)

That verdict, calibrated: the cross-lab-vs-same-lab MARGIN is **≈0** — a second DIVERSE pass earns its keep via *count-delta* (it finds what the first missed), but the second reviewer being a different LAB buys ~nothing over a same-lab second instance, and it still hallucinates facts (a MiniMax-M3 pass verified ~25%, confident HIGH fabrications — ground any reviewer's asserted facts, weight its reasoning). The real martingale to avoid is a model reviewing its OWN output (same instance) as the *sole* adversarial pass.

## Validation Checklists

Post-output verification lists — All Outputs + per-model (Fable 5, Sonnet 5, Opus 4.8, GPT-5.6 Sol/Terra/Luna,
GLM-5.2, Grok 4.5): [references/validation-checklists.md](references/validation-checklists.md).
Consult after receiving output from a routed model, not at routing time.

## Source Notes

Primary sources consulted for this update:
- Anthropic: `https://www.anthropic.com/news/claude-fable-5-mythos-5`
- Anthropic Fable 5 system card: `https://www.anthropic.com/claude-fable-5-mythos-5-system-card`
- Anthropic docs: `https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5`
- Anthropic Fable prompting guide: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5`
- Anthropic: `https://www.anthropic.com/news/claude-opus-4-8`
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
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-07-07] Sonnet 4.6 RETIRED 2026-07-07 (operator): default subagent model now claude-sonnet-5 (line 119 fixed). Comparison refs ~L104/149/152 remain as dated evidence but 4.6 is NOT a live option — scrub to absolute-property framing on next steward pass.**
- **[2026-07-12] Agent-tool `model:` pins unreliable — generalizes past Fable to Opus (Verified Transport table added this pass). `opus-low.md`/`general-purpose` etc. do NOT yet carry the self-report-warning banner that `fable-high.md`/`fable-low.md` got on 2026-07-12 — recommend adding it (out of this skill's edit scope; agents live in `~/.claude/agents/`, not `~/Projects/skills/`). Fable's "$10/$50 metered, off-subscription" cost claim is unreconciled against continued successful claude-cli-transport Fable calls in the llmx usage log through 2026-07-12 — needs an actual Console-billing check, not another log read.**
