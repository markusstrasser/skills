# Frontier Model Benchmarks

**Last updated:** 2026-06-06
**Active scope:** Claude Opus 4.8, GPT-5.5, GPT-5.5 Pro.

Older GPT/Gemini/Grok/Sonnet routing rows were removed from the active benchmark surface. Historical comparisons remain only where a vendor used them as a baseline.

## Headline Routing Scores

| Evaluation | Opus 4.8 | GPT-5.5 | GPT-5.5 Pro | Routing read |
|---|---:|---:|---:|---|
| SWE-bench Verified | **88.6** | - | - | Opus for benchmarked GitHub issue resolution. |
| SWE-bench Pro | **69.2** | 58.6 | - | Opus leads on the harder public SWE benchmark. |
| Terminal-Bench 2.0 / 2.1 | 74.6 (2.1) | **82.7** (2.0) | - | GPT-5.5 for terminal/Codex-heavy work; versions differ. |
| Expert-SWE | - | **73.1** | - | OpenAI internal long-horizon coding signal. |
| GDPval / GDPval-AA | **1890 Elo** (AA) | 84.9 wins/ties | 82.3 wins/ties | Opus leads on AA Elo; GPT-5.5 is strong on OpenAI's wins/ties table. |
| OSWorld-Verified | **83.4** | 78.7 | - | Opus leads direct computer-use benchmark. |
| BrowseComp | 84.3 single / 88.5 multi-agent | 84.4 | **90.1** | Pro helps tool/search-heavy hard questions; base tie is close. |
| FrontierMath Tier 4 | - | 35.4 | **39.6** | Pro for hard quantitative work. |
| GeneBench | - | 25.0 | **33.2** | Pro is the strongest listed OpenAI science-analysis variant. |
| BixBench | - | **80.5** | - | GPT-5.5 for quantified biology benchmark where reported. |
| GPQA Diamond | 93.6 | 93.6 | - | Tie on reported base numbers; use tools/source reading for real science work. |
| HLE no tools | **49.8** | 41.4 | 43.1 | Opus for unaided expert reasoning. |
| HLE with tools | **57.9** | 52.2 | 57.2 | Opus slight lead; Pro close when tool use is allowed. |
| MCP-Atlas | **82.2** | 75.3 | - | Opus for MCP-heavy tool use. |
| AutomationBench | **15.5** | 12.9 | - | Opus for long-horizon automation. |
| Tau2-bench Telecom | - | **98.0** | - | GPT-5.5 for customer-service style tool workflows. |
| MRCR v2 8-needle 512K-1M | 32.2 (reported for Opus 4.7/4.6 comparison) | **74.0** | - | GPT-5.5 for OpenAI-reported long-context retrieval. |
| ARC-AGI-2 verified | - | **85.0** | - | GPT-5.5 for OpenAI-reported abstract reasoning. |

**Reading cautions:**
- Opus 4.8 scores are from the Anthropic system card, generally with adaptive thinking at max effort. Production default is `high`.
- OpenAI notes GPT evals on the announcement page were run with reasoning effort set to `xhigh` in a research environment; production ChatGPT/API may differ.
- GPT-5.5 Pro is not a separate training run. OpenAI describes it as the same underlying model using parallel test-time compute, with separate evals where extra compute may change risks or safeguards.
- Do not compare Opus Terminal-Bench 2.1 directly to GPT Terminal-Bench 2.0 without noting harness/version differences. Anthropic also notes GPT-5.5's Codex CLI harness score is 83.4.

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
