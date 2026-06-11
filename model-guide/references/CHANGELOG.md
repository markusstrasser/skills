# Model Guide Changelog

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
