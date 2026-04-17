# Frontier Model Benchmarks

**Last updated:** 2026-04-16
**Sources:** Artificial Analysis, LLM Stats, SWE-bench.com, LMSYS Chatbot Arena, official docs (Anthropic, OpenAI, Google DeepMind).

> **Note:** Claude Opus numbers reflect the Opus 4.6 measured baseline; Opus 4.7 (released 2026-04-16) matches or exceeds them per Anthropic's release. Rows will be updated when third-party benchmarks publish 4.7 figures.

## Head-to-Head: Current Frontier

| Benchmark | Claude Opus 4.7 | Claude Sonnet 4.6 | GPT-5.4 | Gemini 3.1 Pro | Grok 4.20 Reasoning | Measures |
|-----------|:---:|:---:|:---:|:---:|:---:|----------|
| **SWE-bench Verified** | **80.8%** | 79.6% | 80.0% | 80.6% | 73.5% | Real-world coding |
| **GPQA Diamond** | 91.3% | -- | 93.2% | **94.3%** | ~78.5% | Graduate science reasoning |
| **AIME 2025** | ~95% | -- | **100%** | ~95% | -- | Competition math |
| **MATH-500** | 93% | -- | **98%** | 91.1% | -- | Math problem solving |
| **MMLU** | **92%** | -- | 88% | 85.9% | -- | Broad knowledge |
| **MMLU-Pro** | 82% | -- | 83% | **89.5%** | -- | Hard multi-domain reasoning |
| **HumanEval** | **95%** | -- | **95%** | 84.1% | -- | Code generation |
| **LiveCodeBench** | 76% | -- | **80%** | 73% | -- | Up-to-date coding |
| **IFEval** | 94% | -- | **95%** | 89.2% | -- | Instruction following |
| **IFBench (AA)** | -- | -- | -- | -- | **82.9%** (#1) | Strict instruction-following (AA's IFBench, +29.2pp over Grok 4) |
| **SimpleQA** | **72%** | -- | ~72% | **72.1%** | -- | Factual accuracy |
| **AA-Omniscience Hallucination Rate** *(lower better)* | -- | -- | -- | -- | **17%** (#1) | Fabrication rate when answering (Grok 4.20 v2 0309) |
| **AA-Omniscience Index** *(composite, accuracy + abstention)* | -- | -- | -- | **33** (#1) | 15 (#3) | Knows what it knows AND what it doesn't |
| **AA Intelligence Index v4.0** | 53 | -- | **57** | **57** | 49 (#11/132) | Composite intelligence |
| **LiveBench Data Analysis** | -- | -- | 78.56 | -- | **87.06** (#1) | Tabular/data analysis sub-bench |
| **LiveBench Math** | -- | -- | 47.46 | -- | **43.33** (weak) | Confirms Math weakness — lowest sub-score on LiveBench |
| **LiveBench Overall** *(2026-01-08)* | -- | **68.19** | 67.54 | -- | 67.96 (#2) | Composite |
| **τ²-Bench Telecom** | -- | -- | -- | -- | **97%** (#2) | Agentic tool-use (behind GLM-5) |
| **LMArena Search Arena** | -- | -- | 1219 | 1215 | **1226** (#1) | Web-grounded search ranking (Feb 2026) |
| **LMArena Coding ELO** | -- | -- | -- | -- | 1524 | Above its overall ELO (1490) |
| **ARC-AGI-2** | 68.8% | -- | 52.9% | **77.1%** | -- | Novel abstract reasoning |
| **Terminal-Bench 2.0** | 65.4% | -- | 60% | **68.5%** | -- | Terminal/CLI tasks |
| **GDPval-AA Elo** | 1606 | **1633** | -- | 1317 | -- | Expert preference |
| **BigLaw Bench** | **90.2%** | -- | -- | -- | -- | Legal reasoning |
| **OSWorld** | **72.7%** | -- | -- | -- | -- | Computer use |
| **BrowseComp** | 84.0% | -- | -- | **85.9%** | -- | Web browsing |
| **HLE (with tools)** | **53.1%** | -- | 45% | 51.4% | -- | Humanity's Last Exam |
| **Chatbot Arena** | #4-8 | -- | #5-6 | **#1** | -- | User preference |
| **Arena: Coding** | **#1** | -- | #3 | #4 | -- | Coding preference |

> **Grok 4.20 Reasoning — read with care:**
> - **Hallucination rate** (17%, #1) is its standout — the AA-Omniscience methodology rewards "I don't know" and penalizes guessing, so Grok wins by abstaining aggressively. **AA-Omniscience Index** (composite) puts Grok at #3 (15) behind Gemini 3.1 Pro (#1, 33), which both knows more *and* abstains well.
> - **2M context unverified by third parties.** No published independent RULER / MRCR-v2 / LongBench-v2 score for Grok 4.20 specifically — Awesome Agents leaderboard explicitly lists Grok 4 Fast (2M) with all retrieval scores as dashes. The xAI ">95% NIAH at all 2M positions" claim is vendor-sourced. AA confirmed *capacity*, not *retrieval quality at scale*. Combined with the 20× price cliff above 200K, treat 2M as marketing for now.
> - **Multi-agent variant underperforms single-model** on AI Benchy (#47 vs #24, agent-wars.com 2026-03-13). Cost scales with agent count without intelligence return.
> - **Math is the weak axis** (LiveBench 43.33, LMArena 1458). Don't route hard math to Grok.
> - xAI did not separately disclose AIME/MATH/MMLU/HumanEval/LiveCodeBench/ARC-AGI/HLE numbers for the `-reasoning` SKU; published Grok 4 base figures don't transfer cleanly.

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
| Grok 4.20 Reasoning (≤200K in) | $2.00 | $6.00 | 90% ($0.20) | **2M** | 128K |
| Grok 4.20 Reasoning (>200K in) | **$40.00** | **$120.00** | 90% ($4.00) | 2M | 128K |

> **Grok long-context cliff:** crossing 200K input tokens triggers a 20× price tier — `2M context` is technically available but operationally usable only up to 200K unless cost is irrelevant. Plan to chunk or summarize before exceeding 200K.

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
| **Hallucination rate (raw)** | Grok 4.20 Reasoning v2 | **17%** AA-Omniscience hallucination rate | Lowest fabrication rate — wins by abstaining aggressively |
| **Calibrated knowledge (composite)** | Gemini 3.1 Pro | **33** AA-Omniscience Index | Knows more *and* abstains well — Grok #3 |
| Strict instruction following | Grok 4.20 Reasoning | **82.9%** IFBench (#1) | +29.2pp over Grok 4 — strongest single-version improvement |
| Tabular / data analysis | Grok 4.20 Reasoning | **87.06** LiveBench Data Analysis | Sub-bench lead |
| Web-grounded search | Grok 4.20 Reasoning | **1226** LMArena Search Arena | #1 ahead of GPT-5.2 Search (1219) and Gemini 3 Pro Grounding (1215) |
| Agentic tool-use | GLM-5 | -- | Grok 4.20 #2 at 97% τ²-Bench Telecom |
