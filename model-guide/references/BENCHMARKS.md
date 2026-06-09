# Frontier Model Benchmarks

**Last updated:** 2026-06-09
**Active scope:** Claude Fable 5, Claude Opus 4.8, GPT-5.5, GPT-5.5 Pro.

Older GPT/Gemini/Grok/Sonnet routing rows were removed from the active benchmark surface. Historical comparisons remain only where a vendor used them as a baseline. Fable 5 numbers are the GA-configuration scores (production safety classifiers on, fallback to Opus 4.8 where they fire); the unsafeguarded Mythos 5 scores a touch higher on classifier-adjacent rows.

## Headline Routing Scores

| Evaluation | Fable 5 | Opus 4.8 | GPT-5.5 | GPT-5.5 Pro | Routing read |
|---|---:|---:|---:|---:|---|
| SWE-bench Verified | **95** | 88.6 | - | - | Fable for benchmarked GitHub issue resolution (Mythos 95.5). |
| SWE-bench Pro | **80** | 69.2 | 58.6 | - | Fable leads the harder public SWE benchmark by ~11 over Opus (Mythos 80.3). |
| Terminal-Bench 2.1 | **84.3** | 74.6 | 82.7 (2.0) | - | Fable leads; GPT-5.5's Codex-CLI harness is 83.4. Mythos 88.0. |
| FrontierCode (Diamond) | **29.3** | 13.4 | 5.7 | - | Fable more than doubles Opus on Cognition's merge-quality bench. |
| GDPval-AA (Elo) | **1932** | 1890 | 1769 | - | Fable leads professional-work Elo. |
| OSWorld-Verified | **85.0** | 83.4 | 78.7 | - | Fable ties Mythos (85.0); vision-SOTA with native bash+crop. |
| BrowseComp | - | 84.3 single / 88.5 multi | 84.4 | **90.1** | Mythos multi-agent 93.3; Pro strong on hard search. |
| HLE no tools | 59.0 (Mythos) | 49.8 | 41.4 | 43.1 | Fable n/p; Mythos 59.0 leads unaided expert reasoning. |
| HLE with tools | 64.5 (Mythos) | 57.9 | 52.2 | 57.2 | Mythos Preview 64.7 still top; Opus for the Claude-side number. |
| CharXiv Reasoning (w/tools) | 93.5 (Mythos) | 89.9 | - | - | Fable-class vision reasoning. |
| ArxivMath | 78.5 (Mythos) | 71.8 | 71.5 | 64.8 | Mythos 78.5 leads. |
| CritPt | 28.6 (Mythos) | 20.9 | 27.1 | 17.7 | Mythos 28.6 leads physics reasoning. |
| FrontierMath Tier 4 | - | - | 35.4 | **39.6** | Pro for hard quantitative work. |
| GPQA Diamond | - | 93.6 | 93.6 | - | Use tools/source reading for real science work. |
| MCP-Atlas | - | **82.2** | 75.3 | - | Opus for MCP-heavy tool use. |
| AutomationBench | **17.4** (Fable) | 15.5 | 12.9 | - | Fable for long-horizon automation. |
| Tau2-bench Telecom | - | - | **98.0** | - | GPT-5.5 for customer-service style tool workflows. |
| MRCR v2 8-needle 512K-1M | - | 32.2 (4.7/4.6) | **74.0** | - | GPT-5.5 for OpenAI-reported long-context retrieval. |
| ARC-AGI-2 verified | - | - | **85.0** | - | GPT-5.5 for OpenAI-reported abstract reasoning. |

**Reading cautions:**
- Fable 5 / Opus 4.8 scores are from the Anthropic system cards, generally with adaptive thinking at max effort. Production default is `high`; on Fable, lower effort often exceeds prior-model `xhigh`.
- Several Claude-side rows report the **Mythos 5** number (marked) because Fable was not separately published or its classifiers depress the GA score. Mythos 5 = same weights, classifiers lifted, Glasswing-only — treat its scores as the capability ceiling, Fable's as the production floor.
- OpenAI notes GPT evals on the announcement page were run at reasoning effort `xhigh` in a research environment; production may differ.
- GPT-5.5 Pro is the same underlying model using parallel test-time compute, with separate evals where extra compute may change risks or safeguards.
- Do not compare Terminal-Bench versions (2.0 vs 2.1) without noting harness differences.

## Specs And Pricing

| Model | Input/MTok | Cached input/MTok | Output/MTok | Context | Max output | Knowledge cutoff | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Claude Opus 4.8 | $5.00 | - | $25.00 | 1M | 128K | Jan 2026 | Fast mode: $10/$50, up to 2.5x output speed. |
| GPT-5.5 | $5.00 | $0.50 | $30.00 | 1.05M | 128K | Dec 1 2025 | Batch/Flex available; Priority costs more. |
| GPT-5.5 Pro | $30.00 | - | $180.00 | 1.05M | 128K | Dec 1 2025 | Same weights plus parallel test-time compute. |

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
