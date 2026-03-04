---
name: model-guide
description: Frontier model selection and prompting guide. Which model for which task, how to prompt each one, known pitfalls, validation checklists. Use when choosing between Claude/GPT/Gemini/Kimi, routing tasks to models, writing prompts for non-Claude models, debugging model-specific issues, or optimizing multi-model workflows. Triggers on "which model", "how to prompt", "model comparison", "model selection", "prompting guide", "GPT tips", "Gemini tips", "Kimi tips".
user-invocable: true
argument-hint: '[task description or model name]'
---

# Model Guide

Select the right frontier model for a task and prompt it correctly.

**Models covered:** Claude Opus 4.6, Claude Sonnet 4.6, GPT-5.2, Gemini 3.1 Pro, Kimi K2.5.
**Last updated:** 2026-02-27. See CHANGELOG.md for update history.

## Quick Selection Matrix

| Task | Best Model | Why | Runner-up |
|------|-----------|-----|-----------|
| **Agentic coding** | Claude Opus 4.6 | SWE-bench 80.8%, Arena coding #1 | Sonnet 4.6 (79.6%, 1/5 cost) |
| **Fact-sensitive work** | Claude Opus 4.6 / Gemini 3.1 | SimpleQA 72% (tied best) | NOT GPT-5.2 (58%), NOT Kimi (37%) |
| **Legal reasoning** | Claude Opus 4.6 | BigLaw 90.2% | -- |
| **Professional analysis** | Claude Opus 4.6 | GDPval-AA Elo 1606 (expert preference) | Sonnet 4.6 (GDPval 1633) |
| **Computer use / browsing** | Claude Opus 4.6 | OSWorld 72.7% | -- |
| **Hard math** | GPT-5.2 | MATH 98%, AIME 100% | Kimi K2.5 (MATH 98%, AIME 96%) |
| **Precise structured output** | GPT-5.2 | IFEval 95%, native Structured Outputs | Claude (94%), Kimi (94%) |
| **Vision / document OCR** | GPT-5.2 | DocVQA 95%, ScreenSpot 86.3% | Kimi K2.5 (MMMU-Pro 78.5%) |
| **Science reasoning** | Gemini 3.1 Pro | GPQA Diamond 94.3% | GPT-5.2 (93.2%) |
| **Abstract pattern recognition** | Gemini 3.1 Pro | ARC-AGI-2 77.1% | Claude (68.8%) |
| **Long document ingestion** (>200K) | Gemini 3.1 Pro | Native 1M context | GPT-5.2 (400K) |
| **Subagent coding** | Claude Sonnet 4.6 | 79.6% SWE-bench at $3/$15 | Kimi K2.5 (76.8%, much cheaper) |
| **Bulk cheap analysis** | Kimi K2.5 | $0.60/$2.50, strong reasoning | Gemini 3.1 ($2/$12) |
| **Multi-agent swarm tasks** | Kimi K2.5 | Native Agent Swarm (100 sub-agents) | -- |
| **Video understanding** | Kimi K2.5 | VideoMMMU 86.6%, native multimodal | Gemini 3.1 (native video) |

For full benchmark tables, read `BENCHMARKS.md`.

## Model Profiles

### Claude Opus 4.6 -- "The Investigator"

**Strengths:** Agentic coding, professional analysis, legal reasoning, factual accuracy, computer use, long-form expert work.
**Weaknesses:** Most expensive ($5/$25), 200K context (1M beta), weaker abstract reasoning than Gemini, weaker raw math than GPT.

**Quick prompting tips:**
- Use **XML tags** for structure -- Claude was trained on this: `<instructions>`, `<context>`, `<documents>`
- Use **adaptive thinking** (`effort: high/medium/low`) -- better than manual extended thinking on Opus 4.6
- Put **long documents at the TOP**, query at the BOTTOM (30% improvement measured)
- Explain the **why** behind constraints -- Claude generalizes from explanations
- Soften forceful instructions -- 4.6 overtriggers on "CRITICAL: You MUST..."
- Prefilling is **deprecated** on 4.6 -- use system prompt instructions instead
- Add `"Avoid over-engineering"` for coding tasks -- Opus tends to over-abstract

For complete guide, read `PROMPTING_CLAUDE.md`.

### Claude Sonnet 4.6 -- "The Workhorse"

**Strengths:** Near-Opus coding (79.6% SWE-bench) at 1/5 cost, GDPval 1633 (actually *beats* Opus on expert preference), best speed/intelligence ratio.
**Weaknesses:** May guess tool parameters instead of asking, 64K max output (vs Opus 128K).

**Quick prompting tips:**
- Same XML tag patterns as Opus
- Use **manual extended thinking** with `budget_tokens` (adaptive thinking also works)
- For interleaved thinking (between tool calls): use `interleaved-thinking-2025-05-14` beta header
- Add parameter validation instruction: `"If a required parameter is missing, ask instead of guessing"`
- Set `max_tokens` to 64K at medium/high effort to give room for thinking
- Best at `medium` effort for most applications; `low` for high-volume

For complete guide, read `PROMPTING_CLAUDE.md`.

### GPT-5.2 -- "The Mathematician"

**Strengths:** Math (MATH 98%, AIME 100%), vision (DocVQA 95%), precise instruction compliance (IFEval 95%), structured outputs, 400K context, 90% prompt cache discount.
**Weaknesses:** Highest hallucination (SimpleQA 58%), weakest abstract reasoning (ARC-AGI-2 52.9%), robotic tone.

**Quick prompting tips (thinking mode, high effort):**
- Do **NOT** use "think step by step" -- hurts performance when thinking is on
- Keep prompts **simple and direct** -- the model does heavy reasoning internally
- Use **`strict: true`** on all function definitions -- guaranteed schema conformance
- Use **XML format** for documents: `<doc id='1' title='Title'>Content</doc>` (JSON performs poorly)
- Add `Formatting re-enabled` as first line of developer message (markdown off by default in thinking)
- Enable **web search** for fact-sensitive queries (drops hallucination from 42% to ~5%)
- Use Responses API with `previous_response_id` for **reasoning persistence** across tool calls
- **STATIC prefix (top) + DYNAMIC content (bottom)** for 90% cache discount
- **llmx defaults to `--reasoning-effort high`** for GPT-5 models automatically

For complete guide, read `PROMPTING_GPT.md`.

### Gemini 3.1 Pro -- "The Polymath"

**Strengths:** Science reasoning (GPQA 94.3%), abstract reasoning (ARC-AGI-2 77.1%), 1M native context, cheapest closed frontier ($2/$12), grounding with Google Search.
**Weaknesses:** Worst instruction following (IFEval 89.2%), lower expert preference (GDPval 1317), 64K max output.

**Quick prompting tips:**
- **Keep temperature at 1.0** -- lowering causes looping and degraded reasoning (opposite of Claude/GPT)
- Put **query at the END** after all context -- critical for Gemini
- Place **critical constraints at the END** too -- Gemini 3 drops early constraints
- **Defaults to `thinkingLevel: high`** server-side; thinking **cannot be disabled** on Pro (lowest is `low`)
- Use **`thinkingLevel`**: low/medium/high for Pro (not `thinkingBudget` -- that's Gemini 2.5)
- Default `maxOutputTokens` is only **8,192** -- you must explicitly raise it
- **Grounding with Google Search** reduces hallucination ~40% -- unique capability
- Use **few-shot examples always** -- matters more for Gemini than other models
- Add `"Remember it is 2026"` -- Gemini benefits from explicit date anchoring
- **llmx supports `--reasoning-effort`** for Gemini (maps to thinkingLevel via LiteLLM)

For complete guide, read `PROMPTING_GEMINI.md`.

### Kimi K2.5 -- "The Budget Polymath"

**Strengths:** Exceptional cost efficiency ($0.60/$2.50), strong math (MATH 98%, AIME 96.1%), native multimodal (vision + video), Agent Swarm (100 parallel sub-agents), open weights (modified MIT), LiveCodeBench 85%.
**Weaknesses:** Worst factual accuracy (SimpleQA 37%), verbose outputs inflate real costs, slower (~42 tok/s), weaker writing quality, limited production track record.

**Quick prompting tips:**
- **Thinking mode** (default): use `temperature=1.0`, `top_p=0.95` -- budget 2-4x tokens for reasoning
- **Instant mode** (for speed): `temperature=0.6`, disable thinking with `extra_body={'thinking': {'type': 'disabled'}}`
- **Non-thinking mode is often better for code** -- Moonshot's own guidance says this
- Reasoning traces appear in `response.choices[0].message.reasoning_content`
- OpenAI-compatible API format (`chat.completions`)
- **Agent Swarm** for long-horizon tasks: up to 1,500 tool calls per session
- For vision: set `max_tokens=64k`, average over multiple runs
- **ALWAYS fact-check** -- SimpleQA 37% means 63% factual error rate without tools

For complete guide, read `PROMPTING_KIMI.md`.

## Validation Checklists

Run these when using outputs from each model:

### After Claude Opus/Sonnet 4.6
- [ ] Cross-check mathematical derivations (MATH 93% < GPT's 98%)
- [ ] For novel abstract patterns, consider Gemini second opinion
- [ ] On documents >200K tokens, check for context-edge information loss

### After GPT-5.2
- [ ] **ALWAYS fact-check** (SimpleQA 58% -- hallucinates 42% of factual questions)
- [ ] Don't trust unsourced claims -- demand citations
- [ ] Abstract reasoning may miss non-obvious patterns (ARC-AGI-2 52.9%)

### After Gemini 3.1 Pro
- [ ] Verify it followed instructions precisely (IFEval 89.2% -- misses ~11%)
- [ ] Expert-quality writing may need editing (GDPval 1317 vs Claude 1606)
- [ ] Check output wasn't silently truncated (64K max, 8K default)

### After Kimi K2.5
- [ ] **ALWAYS fact-check** (SimpleQA 37% -- hallucinates 63% of factual questions)
- [ ] Check output length vs. value -- verbose outputs inflate costs 2-4x
- [ ] Writing quality may need significant editing for professional use
- [ ] Verify tool-augmented results independently -- limited production track record

## Cost Comparison

| Model | Input/MTok | Output/MTok | Cache Discount | Context | Max Output |
|-------|:----------:|:-----------:|:--------------:|:-------:|:----------:|
| Claude Opus 4.6 | $5 | $25 | -- | 200K (1M beta) | 128K |
| Claude Sonnet 4.6 | $3 | $15 | -- | 200K (1M beta) | 64K |
| GPT-5.2 | $1.75 | $14 | 90% input | 400K | 100-128K |
| Gemini 3.1 Pro | $2 | $12 | 75% | 1M | 64K |
| Kimi K2.5 | $0.60 | $2.50 | -- | 256K | 96K (thinking) |

**Cost optimization:** Default to Sonnet 4.6 for subagents. Reserve Opus for synthesis, narratives, and orchestration. Use Kimi for bulk work that doesn't need factual precision. This cuts costs 60-80%.

## Multi-Model Architecture Pattern

```
Claude (orchestrator -- best professional judgment)
  ├── Data tools (DuckDB, CLI tools -- ground truth)
  └── Multi-model validation
        ├── pattern   → Gemini 3.1 Pro  [1M context, ARC-AGI-2 77.1%]
        ├── verify    → Gemini 3.1 Pro  [SimpleQA 72.1%, cheap]
        ├── math      → GPT-5.2         [MATH 98%, AIME 100%]
        ├── review    → Gemini 3.1 Pro  [1M context, full-doc review]
        ├── bulk      → Kimi K2.5       [$0.60/$2.50, strong reasoning]
        └── compare   → Multiple        [side-by-side for high-stakes]
```

## The Hallucination Problem

| Model | SimpleQA | Error Rate |
|-------|:--------:|:----------:|
| Claude Opus 4.6 | 72% | 28% wrong |
| Gemini 3.1 Pro | 72.1% | 28% wrong |
| GPT-5.2 | 58% | 42% wrong |
| GPT-5.2 + web search | 95.1% | 5% wrong |
| Kimi K2.5 | 37% | **63% wrong** |

**Key insight:** Reasoning/thinking modes hallucinate MORE on factual questions. Thinking harder helps reasoning over facts, not recall of facts. Always query data sources for dollar amounts, dates, entity names, and legal claims. Kimi is especially dangerous for unsourced factual claims.

## When to Update This Skill

Update after any frontier model release:
1. Update `BENCHMARKS.md` with new scores
2. Update relevant `PROMPTING_*.md` with API/behavior changes
3. Update selection matrix if rankings change
4. Add entry to `CHANGELOG.md`
