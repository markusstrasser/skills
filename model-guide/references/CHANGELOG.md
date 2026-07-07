# Model Guide Changelog

## 2026-07-07 - Fable 5 off subscription: metered usage credits, fable lanes suspended on cost

Anthropic ended subscription-included Fable 5 access after 2026-07-07 (Pro/Max/Team);
continued access bills metered usage credits at $10/$50 per MTok — 2× Opus 4.8, which
stays subscription-routable at $0. Anthropic states the change is temporary (capacity
fallout from the June export-control suspension/relaunch): "restore Fable as a standard
part of our subscriptions as soon as capacity allows."

### Changed
- Top-of-skill OFF-SUBSCRIPTION note added; description + Fable section header now say
  "metered opt-in" instead of "dormant".
- fable-low lane license SUSPENDED ON COST (not capability): its measured token savings
  (0.34× review, 0.65× gate-redesign) were vs fable-high, never vs a $0 Opus lane —
  gated/briefed/review dispatch routes to opus-low. fable-high stays a paid opt-in
  requiring a named Fable-specific justification (obscure-domain, multi-hop edge,
  measured 2026-06-10).
- Working copies updated in the same pass: execute/SKILL.md (repricing rider on the
  Fable lanes), critique/SKILL.md (fable-subagent axis repriced), and the
  ~/.claude/agents/fable-{low,high}.md definitions.

### Unverified / triggers
- Whether CC session/Agent-tool fable dispatches now bill credits silently or fail:
  UNVERIFIED — probe one small dispatch and check billing before batch use.
- Re-license trigger: Anthropic restores Fable to subscription plans → revert the
  OFF-SUBSCRIPTION note and re-activate the 2026-07-04 fable-lane verdicts.

Sources: techtimes.com 2026-07-06 (subsidy end + rates), bleepingcomputer.com
(Anthropic "not permanent" statement), digitalapplied.com (July-7 usage-credits guide),
claude.com/pricing.

## 2026-06-30 - Claude Sonnet 5 reinstated as a named cost-tier Claude option

Anthropic released Claude Sonnet 5 (2026-06-30): "near-Opus intelligence at Sonnet
pricing," $3/$15 per MTok ($2/$10 intro through 2026-08-31), first Sonnet-tier model
with `xhigh` effort. System card reviewed in full (145 pages); digest at
`references/sonnet-5-system-card.md`.

### Added
- New "Claude Sonnet 5" section (operational specs, system-card insights, prompting).
- "After Claude Sonnet 5" validation checklist.
- Quick/Dispatch-Economics rows: cost-sensitive coding/agentic work with a mechanical
  gate → Sonnet 5; resolved the orphaned "Sonnet/haiku tier" Dispatch Economics row
  (no live model named) to point at `claude-sonnet-5` explicitly.
- OPEN QUESTION callout: whether the 2026-06-20 "NEVER Sonnet" verdict for
  architecture/design/high-reasoning critique should be revisited given Sonnet 5's
  capability profile — explicitly NOT resolved here; flagged for operator decision.

### Not changed
- The "NEVER Sonnet" architecture/critique verdict itself (operator call, not
  re-litigated by this update).
- Opus 4.8 / GPT-5.5 / GPT-5.5 Pro routing.
- Sonnet 5 is not yet on the llmx subscription allowlist (`lite_allowed_models`) —
  that's llmx's own config, out of scope for this skill.

## 2026-06-20 - Fable dormant; Opus primary; architecture → Opus max

Fable 5 not routable on subscription (`lite_allowed_models` = `claude-opus-4-8` only for Anthropic) and US access restricted. Opus 4.8 becomes the live default for all Claude work.

### Changed
- All Fable-first routing → Opus 4.8.
- Architecture / design / high-reasoning critique → **Opus 4.8 `max`** (operator 2026-06-20; was `high|max`).
- Cross-model review: Opus 4.8 + GPT-5.5 (Fable removed).
- Fable section marked **DORMANT**; Opus section promoted to primary.
- `cursor-agent` arch critique example → `claude-opus-4-8-thinking-max`.

### Not changed
- GPT-5.5 / GPT-5.5 Pro routing; trilemma section; GLM opt-in cosigner.

## 2026-06-20 - Selection trilemma: capability × calibration × efficiency

Oliver Shrimpton ("Bigger models are not the way", 2026-06-18) + AA-Omniscience leaderboard read: benchmark capability and parameter count plateau while calibration diverges sharply. Integrated as routing judgment, not a default-model change.

### Added
- SKILL.md **Selection trilemma** section: three axes, inverted capability/calibration ordering, reasoning-budget-is-not-monotonic guard (DeepSeek V4 Pro vs GLM-5.2 impossible-asyncio anecdote, n=1).
- Quick Selection Matrix row: contradictory/impossible spec → Opus 4.8 or GLM-5.2 opt-in; avoid GPT-5.5 / DeepSeek V4.
- Dispatch Economics **reasoning escalation guard** (inverse of cheap-lane finding).
- **After GLM-5.2** validation checklist.
- BENCHMARKS.md: GLM-5.2 72% non-hallucination in trust ordering; DeepSeek V4 Pro explicit 94% hallucination-on-miss; capability-plateau note.

### Changed
- GLM-5.2 cosigner bullet: calibration edge (72% non-hallucination) + impossibility/paradox use case.
- Last-updated stamp → 2026-06-20.

### Not changed
- Default frontier routing (Fable/Opus/GPT-5.5) — capability still wins for gated mechanical work; trilemma adds when NOT to pick by index/size alone.

### Sources
- Oliver Shrimpton 2026-06-18 (AA-Omniscience rates + asyncio impossibility probe via OpenRouter).
- Prior AA instrument read: `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`.

## 2026-06-12 - Add Kradle Four Bridges deception finding to GPT-5.5 insights

### Added
- GPT-5.5 system-card insights: Kradle Four Bridges (kradle.ai, 2026-06-04, n=100 informed runs) — 90% uninstructed deception under a small competitive incentive (~0.23-0.30 expected apples), typically framed as cooperative coordination ("let's spread out"). Third independent source on incentive-sensitive honesty alongside Apollo (29% lie rate, impossible task) and AA-Omniscience (14% non-hallucination). Construct caveat: peer-competition game with explicit scarcity payoffs, not assistant contexts; no routing or mitigation change — deterministic verification over self-report already covers it.

### Not added
- Sonnet 4.6 (27% deception, hint-don't-lie), Gemini 3.1 Pro (54%, bimodal disclose-or-lie), Grok 4.20 (5%) — outside this skill's active routing surface since 2026-06-09. Study-internal confounds noted: RED-always-death (semantic prior), Claude-family judge, first-mover timing drives Grok's score per the authors' own discussion.

## 2026-06-11 - Add AA independent benchmark section with construct annotations

First independent (Artificial Analysis) measurement of the Fable 5 / Opus 4.8 / GPT-5.5 scope, added to BENCHMARKS.md with per-instrument construct cautions derived from full-paper reads of AA-Omniscience (arXiv:2511.13029), IFBench (2507.02833), GDPval (2510.04374), and τ²-bench (2506.07982).

### Added
- BENCHMARKS.md "Independent Measurement" section: per-eval table + calibration trust table (non-hallucination: Fable 45 / Opus 64 / GPT-5.5 14, measured despite an explicit abstention prompt).
- Quantified hallucination priors in the SKILL.md validation checklists (Fable, Opus, GPT-5.5).
- Quick Selection Matrix row for letter-exact output constraints: schema/validator enforcement first; Claude family measurably weakest at prose-mode mechanical compliance (IFBench, with construct caveat — majority adversarial-synthetic constraints that trade against answer quality).
- Independent confirmation line under Fable system-card insights (honesty regression vs Opus now two-source: system card + AA-Omniscience).

### Changed
- τ²-Telecom routing read retired (saturated at the user-simulator ~6% noise floor; Fable 99 ≥ GPT-5.5 94); negative screen only.
- GDPval-AA row annotated: single Gemini 3.1 Pro blind-pairwise judge; original human–human agreement 71%; small Elo gaps are judge noise.
- CritPt: AA independently measures GPT-5.5 Pro at 31 (#1), contradicting the vendor-sourced 17.7.

### Sources checked
- artificialanalysis.ai leaderboard (2026-06-11 snapshot, spot-checked live) + intelligence-benchmarking methodology page.
- Full-paper reads via research-mcp; analysis memo: `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`.

## 2026-06-09 - Add Claude Fable 5 as primary frontier Claude; Opus 4.8 becomes the fallback

Fable 5 / Mythos 5 launched 2026-06-09. Restructured the Claude side of the guide around the new routing pair.

### Added
- **Claude Fable 5** (`claude-fable-5`) as the top frontier Claude model: 1M ctx, 128K out, $10/$50 (2× Opus 4.8), cache $1/$12.50. Adaptive-thinking-only, summarized-CoT-only, no thinking budgets. Effort low→max (default high; lower effort exceeds prior-model xhigh). Covered Model: 30-day retention, no ZDR.
- Fable's safety classifiers (offensive cyber / bio-life-sciences / reasoning-extraction) → `stop_reason:"refusal"` (HTTP 200) → server/client fallback to **Opus 4.8**.
- Benchmarks: SWE-Pro 80, SWE-Verified 95, Terminal-Bench 84.3, FrontierCode-Diamond 29.3 (Opus 13.4), GDPval-AA 1932; Mythos 5 ceiling rows (HLE 59, ArxivMath 78.5, CritPt 28.6) marked.
- Fable prompting deltas: don't recite reasoning (reasoning_extraction trigger), steer with brief instructions not enumerations, ground progress claims, don't surface context countdowns, longer turns by default, add a `send_to_user` tool for long async agents.

### Changed
- **Opus 4.8 reframed as the fallback** — the automatic classifier-refusal target AND the deliberate choice for routine/cost-sensitive work, security/cyber/biology (which Fable refuses anyway), and raw-CoT needs. Half the price; slightly more careful on self-report honesty.
- Cross-model review pattern: Fable 5 *or* Opus 4.8 on the Claude side, paired cross-lab with GPT-5.5.
- Added an "After Claude Fable 5" validation checklist (self-report honesty regression, unrequested actions, defect-framing, refusal/fallback confirmation).

### Sources checked
- Anthropic Fable 5 / Mythos 5 announcement, docs (introducing + overview), Fable prompting guide, and the 319pp system card (§8.1 benchmarks, §6.3.5 diligence, §2.3.3 shortcomings).
- Cross-repo analysis: `agent-infra/research/2026-06-09-fable-5-mythos-5-harness-impact.md`.

## 2026-06-06 - Narrow model-guide to Opus 4.8 and GPT-5.5

Removed the broad active model catalog from `model-guide`.

### Removed from active routing

- Claude Sonnet fallback routing.
- GPT-5.4 and GPT-5.3 Instant active sections.
- Gemini 3.x active routing and `PROMPTING_GEMINI.md`.
- Grok 4.20 active routing.
- Broad cost-optimization tables that encouraged model-shopping instead of a clear frontier default.

Historical details remain available in git history. This skill now answers only the current high-value question: Opus 4.8, GPT-5.5, or GPT-5.5 Pro?

### Added / retained

- Opus 4.8 system-card insights: honesty/self-verification, reduced destructive actions, grader-speculation watch, prompt-injection caveat, high-effort default, mid-conversation system messages, dynamic workflows.
- GPT-5.5 system-card insights: destructive-action metrics, factuality caveat, low-severity coding-agent misalignment patterns, low CoT controllability, impossible-coding-task lying rate, High bio/chem and High-below-Critical cyber classification.
- GPT-5.5 Pro positioning: same underlying model plus parallel test-time compute, $30/$180 pricing, use only for verified high-stakes derivation.
- Current benchmark table and pricing table limited to Opus 4.8, GPT-5.5, and GPT-5.5 Pro.

### Sources checked

- Anthropic system-card registry and Opus 4.8 launch/API pages.
- Local vendored Opus 4.8 system card.
- OpenAI GPT-5.5 announcement, system card, API pricing, and model comparison docs.

## 2026-07-04 — Fable 5 partially re-routable (empirical)
CC-native lanes verified live (interactive session model, fable-high/low agent defs, key-stripped
headless `claude -p`) in arc-agi session ebbeff04; dormancy header softened accordingly. llmx
subscription + paid-API routing still unverified. Dispatch-economics fable-tier verdicts re-activated
for CC-dispatched subagents.
