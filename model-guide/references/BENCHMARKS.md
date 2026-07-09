# Frontier Model Benchmarks

**Last updated:** 2026-07-09
**Active scope:** Claude Fable 5, Claude Opus 4.8, GPT-5.6 Sol/Terra/Luna, Grok 4.5 (AA niche).
**Note:** GPT-5.5 columns below are historical AA/vendor snapshots (pre-5.6); do not route to GPT-5.5.

Older GPT/Gemini/Grok-4.20-and-earlier/Sonnet routing rows were removed from the active benchmark surface. Historical comparisons remain only where a vendor used them as a baseline. Fable 5 numbers are the GA-configuration scores (production safety classifiers on, fallback to Opus 4.8 where they fire); the unsafeguarded Mythos 5 scores a touch higher on classifier-adjacent rows. Grok 4.5 rows below are from Artificial Analysis independent evals (2026-07-08), not vendor self-report.

## Headline Routing Scores

| Evaluation | Fable 5 | Opus 4.8 | GPT-5.5 | GPT-5.5 Pro | Routing read |
|---|---:|---:|---:|---:|---|
| SWE-bench Verified | **95** | 88.6 | - | - | Fable for benchmarked GitHub issue resolution (Mythos 95.5). |
| SWE-bench Pro | **80** | 69.2 | 58.6 | - | Fable leads the harder public SWE benchmark by ~11 over Opus (Mythos 80.3). |
| Terminal-Bench 2.1 | **84.3** | 74.6 | 82.7 (2.0) | - | Fable leads; GPT-5.5's Codex-CLI harness is 83.4. Mythos 88.0. |
| FrontierCode (Diamond) | **29.3** | 13.4 | 5.7 | - | Fable more than doubles Opus on Cognition's merge-quality bench. |
| GDPval-AA (Elo) | **1932** | 1890 | 1769 | - | Fable leads professional-work Elo. Construct: single Gemini 3.1 Pro blind-pairwise judge (see AA section below) — the ~160 gap to GPT-5.5 is real; the 42 Fable-Opus gap is within judge noise. |
| OSWorld-Verified | **85.0** | 83.4 | 78.7 | - | Fable ties Mythos (85.0); vision-SOTA with native bash+crop. |
| BrowseComp | - | 84.3 single / 88.5 multi | 84.4 | **90.1** | Mythos multi-agent 93.3; Pro strong on hard search. |
| HLE no tools | 59.0 (Mythos) | 49.8 | 41.4 | 43.1 | Fable n/p; Mythos 59.0 leads unaided expert reasoning. |
| HLE with tools | 64.5 (Mythos) | 57.9 | 52.2 | 57.2 | Mythos Preview 64.7 still top; Opus for the Claude-side number. |
| CharXiv Reasoning (w/tools) | 93.5 (Mythos) | 89.9 | - | - | Fable-class vision reasoning. |
| ArxivMath | 78.5 (Mythos) | 71.8 | 71.5 | 64.8 | Mythos 78.5 leads. |
| CritPt | 28.6 (Mythos) | 20.9 | 27.1 | 17.7 | Vendor-sourced Pro 17.7 is contradicted by AA's independent run (Pro **31, #1**; see AA section) — Pro stays the pick for hardest physics/quant. |
| FrontierMath Tier 4 | - | - | 35.4 | **39.6** | Pro for hard quantitative work. |
| GPQA Diamond | - | 93.6 | 93.6 | - | Use tools/source reading for real science work. |
| MCP-Atlas | - | **82.2** | 75.3 | - | Opus for MCP-heavy tool use. |
| AutomationBench | **17.4** (Fable) | 15.5 | 12.9 | - | Fable for long-horizon automation. |
| Tau2-bench Telecom | - | - | **98.0** | - | Stale routing read — AA measures Fable 99 / Opus 94 / GPT-5.5 94: saturated at the benchmark's noise floor; negative screen only (see AA section). |
| MRCR v2 8-needle 512K-1M | - | 32.2 (4.7/4.6) | **74.0** | - | GPT-5.5 for OpenAI-reported long-context retrieval. |
| ARC-AGI-2 verified | - | - | **85.0** | - | GPT-5.5 for OpenAI-reported abstract reasoning. |

**Reading cautions:**
- Fable 5 / Opus 4.8 scores are from the Anthropic system cards, generally with adaptive thinking at max effort. Production default is `high`; on Fable, lower effort often exceeds prior-model `xhigh`.
- Several Claude-side rows report the **Mythos 5** number (marked) because Fable was not separately published or its classifiers depress the GA score. Mythos 5 = same weights, classifiers lifted, Glasswing-only — treat its scores as the capability ceiling, Fable's as the production floor.
- OpenAI notes GPT evals on the announcement page were run at reasoning effort `xhigh` in a research environment; production may differ.
- GPT-5.5 Pro is the same underlying model using parallel test-time compute, with separate evals where extra compute may change risks or safeguards.
- Do not compare Terminal-Bench versions (2.0 vs 2.1) without noting harness differences.

## Independent Measurement — Artificial Analysis (2026-06-11)

First independent, same-harness, cross-lab measurement of the active scope (everything above is vendor-reported). Configs: Fable 5 is measured as "(with fallback)" — the GA system including Opus 4.8 answering classifier-refused items; Claude models at max effort, GPT-5.5 at xhigh. Instrument constructs verified by full-paper reads: `agent-infra/research/2026-06-11-aa-benchmark-instrument-validity.md`.

| Evaluation | Fable 5 | Opus 4.8 | GPT-5.5 | What the instrument measures (construct caution) |
|---|---:|---:|---:|---|
| AA Intelligence Index v4 | **64.9** | 61.4 | 60.2 | Composite; heaviest component (GDPval-AA, 16.7%) is an LLM-preference Elo. Screen, not verifier — route on per-eval rows. |
| GDPval-AA win Elo | **1932** | 1890 | 1769 | One-shot, fully-specified knowledge-work deliverables in AA's generic Stirrup harness, judged by a single Gemini 3.1 Pro blind-pairwise (Bradley-Terry). Original GDPval human–human grader agreement is only 71%, so the construct is taste-adjacent even before the LLM judge. Cross-lab judge for the Claude result (it ranks its own family 18th). |
| Terminal-Bench Hard | **63** | 58 | 61 | 44 hard tasks in a generic Terminus-2 scaffold — model capability, not product-harness performance (see Coding Agent Index row). |
| τ²-Bench Telecom | 99 | 94 | 94 | Dual-control (the user holds device tools; agent diagnoses + instructs) with deterministic state-assertion verification — good construct, but the 94–99 frontier band sits at the user-simulator's ~6% critical-error noise floor. Saturated; only low scores carry signal (Sonnet 4.6: 76, Haiku 4.5: 55 = real dual-control discipline gaps). |
| AA-LCR (long context) | 70 | 68 | **74** | 100 questions over ~100K-token document sets. 68–74 is a parity band; independently backs the GPT-5.5 long-context row above. |
| AA-Omniscience accuracy | **61** | 47 | 57 | Closed-book recall of expert-hard long-tail facts. Questions are GPT-5-generated — wording bias, if any, favors GPT, so Fable's lead is conservative. |
| AA-Omniscience non-hallucination | 45 | **64** | 14 | Of not-fully-correct answers, the share that were abstentions rather than confident fabrications — measured DESPITE an explicit "better to say you don't know" instruction. Rankings transfer; absolute rates are long-tail-specific. |
| IFBench | 63 | 62 | 76 | Generalization to unseen, majority adversarial-synthetic output constraints (every-Nth-word-Japanese, prime-length-words). Tracks RLVR constraint-training, which measurably trades against answer quality (7.0→6.4 judge score in the IFBench paper). NOT operational instruction-following; enforce formats architecturally regardless of model. |
| Humanity's Last Exam | **53** | 46 | 44 | AA's no-tools run; fills the Fable gap the vendor left (card published Mythos-only 59). |
| SciCode | **60** | 53 | 56 | Research-paper-derived scientific coding subproblems. |
| CritPt | 29 | 21 | 27 | GPT-5.5 Pro: **31 (#1)** — contradicts the vendor 17.7 above; independent backing for Pro on hardest physics/quant derivation. |
| Coding Agent Index | n/a | **77** (Claude Code, max) | 65 (Codex, xhigh) | The only public harness×model benchmark. Same-model swings across harnesses are large (Gemini 3.1 Pro: 54 on TB-Hard standalone, dead-last in Gemini CLI) — the harness dominates. Fable 5 not yet listed. |

**Trust ordering inverts capability ordering.** Fable 5 is #1 on knowledge accuracy and #13 on calibration (45% non-hallucination); GPT-5.5 is #3/#19 (14%). Of commonly-routed models: **GLM-5.2 72%** (2026-06-18 AA leaderboard read, Shrimpton), Haiku 4.5 74%, Opus 4.8 64%, Sonnet 4.6 54%, Gemini 3.1 Pro 50%, Gemini 3.5 Flash 39%, GPT-5.4 mini 10%, **DeepSeek V4 Pro ~6%** (94% hallucination-on-miss per same read; negative Omniscience Index — more wrong than right when answering; never use for unsourced facts or epistemic guardrails). GLM-5.2 scores within ~4 Intelligence Index points of GPT-5.5 despite ~2× smaller active params — capability plateaus while calibration diverges. This quantifies the cosign-to-primary policy: a wrong unsourced factual specific from GPT-5.5 is ~6× more likely to be a confident fabrication than an admitted unknown.

Provenance: artificialanalysis.ai leaderboard snapshot 2026-06-11, spot-checked against the live site (Fable OI 40 / acc 61%, Opus OI 27, GPT-5.5 acc 57% — match); Omniscience columns internally validated (accuracy − confabulated share reproduces the published index ±1). Instruments: arXiv:2511.13029 (AA-Omniscience), arXiv:2507.02833 (IFBench), arXiv:2510.04374 (GDPval), arXiv:2506.07982 (τ²-bench).

## Independent Measurement — Grok 4.5 (Artificial Analysis, 2026-07-08)

Same-harness AA v4.1 board after SpaceXAI launch. Config: **Grok 4.5 (high)**. Numbers from operator paste of the live leaderboard 2026-07-09 (screen-grade; re-spot-check before citing as settled). Peer columns are the same paste for relative ranking.

| Evaluation | Grok 4.5 | Fable 5 | Opus 4.8 | GPT-5.5 | Routing read |
|---|---:|---:|---:|---:|---|
| Intelligence Index v4.1 | **54** | 60 | 56 | 55 | Frontier pack; not a default-replace |
| Coding Index | **72.4** | 76.5 | 74.3 | 74.9 | Near Opus/GPT |
| Terminal-Bench v2.1 | **82%** | 85% | 85% | 84% | Parity |
| AutomationBench-AA | **51%** | 49% | 49% | 42% | **Lead** — agentic SaaS/tool workflows |
| τ³-Banking | **33%** | 27% | 28% | 31% | **Lead** — agentic tool use |
| AA-Briefcase Elo | **1328** | 1583 | 1354 | 1158 | Strong knowledge-work agent; Fable still ahead |
| GDPval-AA v2 Elo | **1543** | 1760 | 1600 | 1494 | Near Opus; below Fable/Sonnet |
| CritPt | **15%** | 29% | 21% | 27 (Pro 31) | **Weak** — hard physics → Pro |
| AA-Omniscience accuracy | **52%** | 61% | 47% | 57% | Solid recall |
| AA-Omniscience non-hallucination | **~46%** | 45% | **64%** | 14% | Mid-pack — not a fact/epistemic pick |
| Cost / Intelligence Index task | **~$0.31** | $2.75 | ~$1.8 | $0.86 | **Cheap frontier** |
| Output speed (tok/s) | **~88** | 70 | ~61 | 68 | Faster than Fable/GPT |

**Coding Agent Index (harness×model):** Grok Build + Grok 4.5 (high) **76** — ties Codex GPT-5.5 xhigh; Claude Code Fable max **77**. Harness still dominates; do not promote Grok as default executor from this alone.

**Trust ordering update:** Grok joins Fable in the mid-calibration band (~45–46% non-hallucination) while sitting in the frontier capability pack — same cosign-to-primary rule as GPT: weight reasoning, verify facts.

## Specs And Pricing

| Model | Input/MTok | Cached input/MTok | Output/MTok | Context | Max output | Knowledge cutoff | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Claude Opus 4.8 | $5.00 | - | $25.00 | 1M | 128K | Jan 2026 | Fast mode: $10/$50, up to 2.5x output speed. |
| GPT-5.6 Sol | $5.00 | (cache 90% off) | $30.00 | 1.05M | 128K | Feb 16 2026 | Flagship; Pro = reasoning.mode=pro. |
| GPT-5.6 Terra | $2.50 | (cache 90% off) | $15.00 | 1.05M | 128K | Feb 16 2026 | Mid opt-in. |
| GPT-5.6 Luna | $1.00 | (cache 90% off) | $6.00 | 1.05M | 128K | Feb 16 2026 | Everyday GPT (≈ prior 5.5 perf). |
| Grok 4.5 | $2.00 | - | $6.00 | 500k | - | - | Cursor fast variant $4/$18. Reasoning low/med/high. |

## Model-Card Behavior Signals

| Signal | Opus 4.8 | GPT-5.5 | Operational consequence |
|---|---|---|---|
| Honesty / factuality | Around 4x less likely than Opus 4.7 to leave flaws in its own code unreported; lower incorrect-rate on several factual benchmarks mainly via abstention. | Individual claims 23% more likely correct in flagged factual-error cases; response-level error only 3% lower because it makes more claims. | Still verify. Opus can be trusted slightly more as a monitor; GPT still needs source grounding. |
| Destructive actions | Reckless and destructive actions substantially reduced vs prior Opus releases. | Destructive-action avoidance 0.90; perfect reversion 0.52; user-work preserved 0.57. | Both improved, neither replaces git/test safeguards. |
| Agentic misalignment | Improved over 4.7 on most alignment measures; watch grader speculation/evaluation awareness. | Slightly more low-severity misalignment than 5.4 Thinking in coding-agent resampling; no novel severe misalignment found. | Bind agents to ground truth and explicit action permissions. |
| Prompt injection | Some agentic-context robustness weaker than Opus 4.7 before safeguards; deployed safeguards close much of the gap. | Connector prompt-injection score 0.963 vs 0.998 for 5.4 Thinking. | Treat tool outputs as hostile. Do not mix retrieved text with instructions. |
| CoT monitorability | Low CoT controllability and broadly monitorable extended thinking; preliminary caveat that visible CoT may not catch all grader awareness. | Comparable CoT monitorability to GPT-5 reasoning models; 0.2% CoT controllability at 50K chars. | Reasoning traces are diagnostic, not proof. Use deterministic verification. |
| Safety preparedness | Does not advance Anthropic's capability frontier beyond Mythos Preview; catastrophic risk low with mitigations. | High bio/chem and High cybersecurity below Critical; AI self-improvement below High. | Cyber/bio workflows need policy-aware routing and sources. |
| Impossible-task behavior | Main watch item is appearance-of-success / grader speculation. | Apollo reports 29% lying rate on an impossible coding task. | Build impossibility checks into eval harnesses. |

## Sources

- Anthropic system-card registry: `https://www.anthropic.com/system-cards`
- Anthropic launch/API notes: `https://www.anthropic.com/news/claude-opus-4-8`, `https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-8`
- Local vendored Opus card: `references/opus-4-8-system-card.md`
- OpenAI launch: `https://openai.com/index/introducing-gpt-5-5/`
- OpenAI system card: `https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf`
- OpenAI pricing/model docs: `https://openai.com/api/pricing/`, `https://developers.openai.com/api/docs/models/compare`
