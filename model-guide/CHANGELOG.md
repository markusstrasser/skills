# Model Guide Changelog

Track what changes with each model release so you know what to update.

## 2026-02-27 -- Initial Creation

**Models covered:** Claude Opus 4.6, Claude Sonnet 4.6, GPT-5.2, Gemini 3.1 Pro, Kimi K2.5.

- Benchmarks sourced from official docs + Artificial Analysis, LLM Stats, SWE-bench.com, LMSYS
- Prompting guides sourced from official docs (Anthropic, OpenAI, Google DeepMind, Moonshot AI)
- Selection matrix, validation checklists, cost comparison, multi-model architecture pattern

### Key data points at creation
- Claude Opus 4.6: released Feb 5, 2026. Prefill deprecated. Adaptive thinking recommended over manual.
- Claude Sonnet 4.6: released Feb 5, 2026. GDPval 1633 (beats Opus). Interleaved thinking via beta header.
- GPT-5.2: released Dec 11, 2025. MATH 98%, SimpleQA 58%. Web search drops errors to 5%.
- Gemini 3.1 Pro: released Feb 19, 2026. Uses `thinkingLevel` not `thinkingBudget`. Temperature must stay 1.0.
- Kimi K2.5: released Jan 26, 2026. Open-weight MoE (1T/32B active). SimpleQA 37% (worst). Agent Swarm unique.

### Design decisions
- Focused on current frontier only (no legacy models like GPT-4.1, Gemini 2.5, DeepSeek)
- One prompting guide per model family for easy updates
- BENCHMARKS.md is the most frequently updated file

## 2026-03-05 -- GPT-5.4 Release

**GPT-5.4 replaces GPT-5.2** as frontier GPT model. Variants: base, Thinking, Pro.

### Key changes
- Context window: 400K → 1M tokens (matches Claude/Gemini)
- SimpleQA: ~72% inferred (33% fewer claim errors vs 5.2's 58%) — now tied with Claude/Gemini
- Native computer use added
- Tool Search API — avoids dumping all tool definitions into prompt
- Consolidates GPT-5.3-Codex coding capabilities
- GDPval: 83% (OpenAI's benchmark, not Artificial Analysis Elo)
- APEX-Agents benchmark leader (law + finance)
- Uses fewer tokens per solution vs 5.2

### What's still unknown (update when available)
- Exact pricing (marked TBD)
- Most benchmark scores (MATH, AIME, GPQA, ARC-AGI-2, IFEval, SWE-bench)
- Exact llmx model name (assumed `gpt-5.4` following 5.2 pattern)
- Max output tokens

### Files updated
- SKILL.md: selection matrix, model profile, cost table, hallucination table, validation checklist
- BENCHMARKS.md: GPT-5.2 → GPT-5.4, SimpleQA updated, pricing TBD
- PROMPTING_GPT.md: title, context window, hallucination section
- model-review SKILL.md: dispatch model updated
- llmx-guide SKILL.md: model name updated
- postwrite-frontier-timeliness.sh: current frontier reference
- Global ~/.claude/CLAUDE.md: model reference
- project-upgrade SKILL.md: dispatch model
- constitution SKILL.md: prompting tip

## Update Checklist

When a new frontier model releases:

1. [ ] Update `BENCHMARKS.md` -- new scores, pricing, context limits
2. [ ] Update relevant `PROMPTING_*.md` -- API changes, new features, deprecated features
3. [ ] Update `SKILL.md` selection matrix if rankings change
4. [ ] Update `SKILL.md` cost table
5. [ ] Add changelog entry with date and key changes
6. [ ] Consider whether any model should be added or removed from coverage
