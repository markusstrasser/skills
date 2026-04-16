# Frontier Model Benchmarks

**Last updated:** 2026-04-16
**Sources:** Artificial Analysis, LLM Stats, SWE-bench.com, LMSYS Chatbot Arena, official docs (Anthropic, OpenAI, Google DeepMind).

> **Note:** Claude Opus numbers reflect the Opus 4.6 measured baseline; Opus 4.7 (released 2026-04-16) matches or exceeds them per Anthropic's release. Rows will be updated when third-party benchmarks publish 4.7 figures.

## Head-to-Head: Current Frontier

| Benchmark | Claude Opus 4.7 | Claude Sonnet 4.6 | GPT-5.4 | Gemini 3.1 Pro | Measures |
|-----------|:---:|:---:|:---:|:---:|----------|
| **SWE-bench Verified** | **80.8%** | 79.6% | 80.0% | 80.6% | Real-world coding |
| **GPQA Diamond** | 91.3% | -- | 93.2% | **94.3%** | Graduate science reasoning |
| **AIME 2025** | ~95% | -- | **100%** | ~95% | Competition math |
| **MATH-500** | 93% | -- | **98%** | 91.1% | Math problem solving |
| **MMLU** | **92%** | -- | 88% | 85.9% | Broad knowledge |
| **MMLU-Pro** | 82% | -- | 83% | **89.5%** | Hard multi-domain reasoning |
| **HumanEval** | **95%** | -- | **95%** | 84.1% | Code generation |
| **LiveCodeBench** | 76% | -- | **80%** | 73% | Up-to-date coding |
| **IFEval** | 94% | -- | **95%** | 89.2% | Instruction following |
| **SimpleQA** | **72%** | -- | ~72% | **72.1%** | Factual accuracy |
| **ARC-AGI-2** | 68.8% | -- | 52.9% | **77.1%** | Novel abstract reasoning |
| **Terminal-Bench 2.0** | 65.4% | -- | 60% | **68.5%** | Terminal/CLI tasks |
| **GDPval-AA Elo** | 1606 | **1633** | -- | 1317 | Expert preference |
| **BigLaw Bench** | **90.2%** | -- | -- | -- | Legal reasoning |
| **OSWorld** | **72.7%** | -- | -- | -- | Computer use |
| **BrowseComp** | 84.0% | -- | -- | **85.9%** | Web browsing |
| **HLE (with tools)** | **53.1%** | -- | 45% | 51.4% | Humanity's Last Exam |
| **Chatbot Arena** | #4-8 | -- | #5-6 | **#1** | User preference |
| **Arena: Coding** | **#1** | -- | #3 | #4 | Coding preference |

## Pricing

| Model | Input/MTok | Output/MTok | Cache Discount | Context | Max Output |
|-------|:----------:|:-----------:|:--------------:|:-------:|:----------:|
| Claude Opus 4.7 | $5.00 | $25.00 | -- | 1M | 128K |
| Claude Sonnet 4.6 | $3.00 | $15.00 | -- | 1M | 64K |
| GPT-5.4 (<272K) | $2.50 | $15.00 | 90% ($0.25) | 1M | 128K |
| GPT-5.4 (>272K) | $5.00 | $22.50 | 90% ($0.50) | 1M | 128K |
| GPT-5.3 Instant | $1.75 | $14.00 | 90% input | 128K | 16K |
| Gemini 3.1 Pro | $2.00 | $12.00 | 75% | 1M | 64K |
| Gemini 3 Flash | $0.50 | $3.00 | 75% | 1M | 65K |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | 75% | 1M | 1000K |

## Category Winners

| Category | Winner | Score | Key Gap |
|----------|--------|:-----:|---------|
| Agentic coding | Claude Opus 4.7 | 80.8% SWE-bench | +0.2pp over Gemini |
| Expert preference | Claude Sonnet 4.6 | 1633 GDPval | +27 over Opus, +316 over Gemini |
| Factual accuracy | Tie: Claude / Gemini / GPT-5.4 | ~72% SimpleQA | All within 0.1pp |
| Math | GPT-5.4 | 98% MATH, 100% AIME | +5pp over Claude |
| Science reasoning | Gemini 3.1 Pro | 94.3% GPQA | +1.1pp over GPT |
| Abstract reasoning | Gemini 3.1 Pro | 77.1% ARC-AGI-2 | +8.3pp over Claude |
| Instruction following | GPT-5.4 | 95% IFEval | +1pp over Claude |
| Legal reasoning | Claude Opus 4.7 | 90.2% BigLaw | No competition |
| Computer use | Claude Opus 4.7 | 72.7% OSWorld | No competition |
| Long context | Gemini 3.1 Pro / GPT-5.4 / Claude | 1M native (all) | Claude: MRCR v2 78.3% at 1M |
| Cost efficiency | Gemini 3.1 Flash-Lite | $0.25/$1.50 | Cheapest frontier model |
