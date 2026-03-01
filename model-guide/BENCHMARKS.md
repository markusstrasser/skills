# Frontier Model Benchmarks

**Last updated:** 2026-02-27
**Sources:** Artificial Analysis, LLM Stats, SWE-bench.com, LMSYS Chatbot Arena, official docs (Anthropic, OpenAI, Google DeepMind, Moonshot AI).

## Head-to-Head: Current Frontier

| Benchmark | Claude Opus 4.6 | Claude Sonnet 4.6 | GPT-5.2 | Gemini 3.1 Pro | Kimi K2.5 | Measures |
|-----------|:---:|:---:|:---:|:---:|:---:|----------|
| **SWE-bench Verified** | **80.8%** | 79.6% | 80.0% | 80.6% | 76.8% | Real-world coding |
| **GPQA Diamond** | 91.3% | -- | 93.2% | **94.3%** | 87.6% | Graduate science reasoning |
| **AIME 2025** | ~95% | -- | **100%** | ~95% | 96.1% | Competition math |
| **MATH-500** | 93% | -- | **98%** | 91.1% | **98%** | Math problem solving |
| **MMLU** | **92%** | -- | 88% | 85.9% | **92%** | Broad knowledge |
| **MMLU-Pro** | 82% | -- | 83% | **89.5%** | 87.1% | Hard multi-domain reasoning |
| **HumanEval** | **95%** | -- | **95%** | 84.1% | **99%** | Code generation |
| **LiveCodeBench** | 76% | -- | 80% | 73% | **85%** | Up-to-date coding |
| **IFEval** | 94% | -- | **95%** | 89.2% | 94% | Instruction following |
| **SimpleQA** | **72%** | -- | 58% | **72.1%** | 36.9% | Factual accuracy |
| **ARC-AGI-2** | 68.8% | -- | 52.9% | **77.1%** | ~52 | Novel abstract reasoning |
| **Terminal-Bench 2.0** | 65.4% | -- | 60% | **68.5%** | 50.8% | Terminal/CLI tasks |
| **GDPval-AA Elo** | 1606 | **1633** | -- | 1317 | -- | Expert preference |
| **BigLaw Bench** | **90.2%** | -- | -- | -- | -- | Legal reasoning |
| **OSWorld** | **72.7%** | -- | -- | -- | -- | Computer use |
| **BrowseComp** | 84.0% | -- | -- | **85.9%** | 78.4% | Web browsing |
| **HLE (with tools)** | **53.1%** | -- | 45% | 51.4% | 50.2% | Humanity's Last Exam |
| **Chatbot Arena** | #4-8 | -- | #5-6 | **#1** | ~#5 | User preference |
| **Arena: Coding** | **#1** | -- | #3 | #4 | -- | Coding preference |
| **MMMU-Pro (Vision)** | -- | -- | -- | -- | **78.5%** | Multimodal understanding |
| **VideoMMMU** | -- | -- | -- | -- | **86.6%** | Video understanding |

## Pricing

| Model | Input/MTok | Output/MTok | Cache Discount | Context | Max Output |
|-------|:----------:|:-----------:|:--------------:|:-------:|:----------:|
| Claude Opus 4.6 | $5.00 | $25.00 | -- | 200K (1M beta) | 128K |
| Claude Sonnet 4.6 | $3.00 | $15.00 | -- | 200K (1M beta) | 64K |
| GPT-5.2 | $1.75 | $14.00 | 90% input | 400K | 100-128K |
| Gemini 3.1 Pro | $2.00 | $12.00 | 75% | 1M | 64K |
| Kimi K2.5 | $0.60 | $2.50 | -- | 256K | 96K (thinking) |

**Effective cost note:** Kimi K2.5's verbose output style means real-world costs are often 2-4x the per-token price. Budget accordingly.

## Category Winners

| Category | Winner | Score | Key Gap |
|----------|--------|:-----:|---------|
| Agentic coding | Claude Opus 4.6 | 80.8% SWE-bench | +0.2pp over Gemini |
| Expert preference | Claude Sonnet 4.6 | 1633 GDPval | +27 over Opus, +316 over Gemini |
| Factual accuracy | Tie: Claude / Gemini | 72% SimpleQA | +14pp over GPT, +35pp over Kimi |
| Math | GPT-5.2 / Kimi K2.5 | 98% MATH | +5pp over Claude |
| Science reasoning | Gemini 3.1 Pro | 94.3% GPQA | +1.1pp over GPT |
| Abstract reasoning | Gemini 3.1 Pro | 77.1% ARC-AGI-2 | +8.3pp over Claude |
| Instruction following | GPT-5.2 | 95% IFEval | +1pp over Claude/Kimi |
| Legal reasoning | Claude Opus 4.6 | 90.2% BigLaw | No competition |
| Computer use | Claude Opus 4.6 | 72.7% OSWorld | No competition |
| Long context | Gemini 3.1 Pro | 1M native | 5x Claude standard |
| Cost efficiency | Kimi K2.5 | $0.60/$2.50 | 8x cheaper than Opus |
| Code generation | Kimi K2.5 | 99% HumanEval | +4pp over Claude/GPT |
| Video understanding | Kimi K2.5 | 86.6% VideoMMMU | Unique benchmark |
| Multi-agent swarm | Kimi K2.5 | 100 sub-agents | Unique capability |
