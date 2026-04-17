---
name: model-guide
description: Frontier model selection and prompting guide. Which model for which task, how to prompt each one, known pitfalls, validation checklists. Use when choosing between Claude/GPT/Gemini, routing tasks to models, writing prompts for non-Claude models, debugging model-specific issues, or optimizing multi-model workflows. Triggers on "which model", "how to prompt", "model comparison", "model selection", "prompting guide", "GPT tips", "Gemini tips".
user-invocable: true
argument-hint: '[task description or model name]'
effort: low
---

# Model Guide

Select the right frontier model for a task and prompt it correctly.

**Models covered:** Claude Opus 4.7, Claude Sonnet 4.6, GPT-5.4, GPT-5.3 Instant, Gemini 3.1 Pro, Gemini 3 Flash, Gemini 3.1 Flash-Lite, Grok 4.20 Reasoning.
**Last updated:** 2026-04-16. See `${CLAUDE_SKILL_DIR}/references/CHANGELOG.md` for update history.
**Benchmark note:** Numbers cited for Claude Opus are the published Opus 4.6 baseline. Opus 4.7 (released 2026-04-16) improves on most of these per Anthropic's announcement; specific 4.7 figures update on the next benchmark refresh.

## Long-Horizon Research Routing

For long novelty sweeps and frontier-mapping work:

- Use cheaper/faster models or plain search for **search perturbation** and seam discovery.
- Use stronger models for **compression, synthesis, and adversarial filtering**.
- Watch for template artifacts such as repeated survivor counts or repeated memo shapes; these can be model-structure effects, not evidence about the search space.

Practical split:

- `Gemini 3.1 Pro` or `GPT-5.4`: compress overlapping ideas, detect hidden operator structure, write synthesis memos
- `Gemini 3 Flash` or broad search tools: generate cheap perturbation passes and map candidate seams
- `Claude` or the main orchestrator: decide what survives and what gets rejected

## Quick Selection Matrix

| Task | Best Model | Why | Runner-up |
|------|-----------|-----|-----------|
| **Agentic coding** | Claude Opus 4.7 | SWE-bench 80.8%, Arena coding #1 | Sonnet 4.6 (79.6%, ~60% cost) |
| **Fact-sensitive work** | Claude Opus 4.7 / Gemini 3.1 / GPT-5.4 | SimpleQA ~72% (tied) | -- |
| **Legal reasoning** | Claude Opus 4.7 | BigLaw 90.2% | -- |
| **Professional analysis** | Claude Opus 4.7 | GDPval-AA Elo 1606 (expert preference) | Sonnet 4.6 (GDPval 1633) |
| **Computer use / browsing** | Claude Opus 4.7 | OSWorld 72.7% | -- |
| **Hard math** | GPT-5.4 | MATH 98%+, AIME 100% | Gemini 3.1 Pro (GPQA 94.3%) |
| **Precise structured output** | GPT-5.4 | IFEval 95%+, native Structured Outputs + Tool Search | Claude (94%) |
| **Vision / document OCR** | GPT-5.4 | DocVQA 95%+, native computer use | Gemini 3.1 Pro |
| **Science reasoning** | Gemini 3.1 Pro | GPQA Diamond 94.3% | GPT-5.4 |
| **Abstract pattern recognition** | Gemini 3.1 Pro | ARC-AGI-2 77.1% | Claude (68.8%) |
| **Long document ingestion** (>200K) | Gemini 3.1 Pro / GPT-5.4 / Claude | Native 1M context (all three) | -- |
| **Subagent coding** | Claude Sonnet 4.6 | 79.6% SWE-bench at $3/$15, 1M context | Gemini 3 Flash (cheap) |
| **Doc → schema extraction** | GPT-5.3 Instant | Less preachy, structured output, fast | GPT-5.4 (stronger reasoning) |
| **Cross-model review** | Pro + GPT-5.4 | Cross-family required (+31pp accuracy, FINCH-ZK). Same-family = no adversarial pressure | (Grok 4.20 NOT recommended as 3rd — abstention bias ≠ adversarial pressure) |
| **Claim/quote verification** | Grok 4.20 Reasoning | AA-Omniscience 17% hallucination rate (#1) — strongly prefers "UNCERTAIN" over guessing | Claude Opus 4.7 |
| **Strict instruction following** | Grok 4.20 Reasoning | IFBench 82.9% (#1) | GPT-5.4 (IFEval 95%) |
| **Tabular data analysis** | Grok 4.20 Reasoning | LiveBench Data Analysis 87.06 (#1) | -- |
| **Web-grounded search** | Grok 4.20 Reasoning | LMArena Search Arena 1226 (#1) | GPT-5.2 Search (1219) |
| **High-volume classification** | Gemini 3 Flash | $0.50/$3/M, 1M ctx | Gemini 3.1 Flash-Lite ($0.25/$1.50) |
| **Video understanding** | Gemini 3.1 Pro | Native video support | GPT-5.4 |

For full benchmark tables, read `${CLAUDE_SKILL_DIR}/references/BENCHMARKS.md`.

## Model Profiles

### Claude Opus 4.7 -- "The Investigator"

**Strengths:** Agentic coding, professional analysis, legal reasoning, factual accuracy, computer use, long-form expert work, memory across sessions, high-resolution vision (2576px). 1M native context at standard pricing (no long-context premium). Best-in-class on Finance Agent and GDPval-AA per Anthropic's 2026-04-16 release.
**Weaknesses:** Most expensive ($5/$25), weaker abstract reasoning than Gemini, weaker raw math than GPT. New tokenizer produces 1.0–1.35× more input tokens than Opus 4.6 for the same text — re-baseline cost expectations on migration.

**Quick prompting tips:**
- Use **XML tags** for structure -- Claude was trained on this: `<instructions>`, `<context>`, `<documents>`
- **Set `thinking: {type: "adaptive"}` explicitly** — adaptive is OFF by default on Opus 4.7. `budget_tokens` returns a 400 error.
- **Start at `effort: "xhigh"` for coding and agentic work** — new effort level between `high` and `max`. Minimum `high` for most intelligence-sensitive work. Low and medium strictly scope to what was asked (may under-think on complex problems).
- **Drop `temperature`, `top_p`, `top_k`** — non-default values return 400 on Opus 4.7. Use prompting to guide behavior.
- **Drop assistant-message prefills** — return 400 on Opus 4.7. Use `output_config.format`, system prompts, or continuation-as-user-turn patterns.
- Put **long documents at the TOP**, query at the BOTTOM (30% improvement measured)
- Explain the **why** behind constraints -- Claude generalizes from explanations
- **4.7 is more literal than 4.6** — remove scaffolding like "summarize progress after 3 tool calls"; 4.7 has built-in progress updates. Fewer subagents and tools called by default; raise effort to `xhigh` if you need more.
- **Set `thinking.display: "summarized"`** in UIs that show reasoning — default is `"omitted"` on 4.7, so the UI appears frozen until first output otherwise.
- **Re-budget `max_tokens`** — same text → more tokens; 4.7 uses more output at high efforts. Start at 64K for `xhigh`/`max`.
- **High-resolution images** — 4.7 reads up to 2576px. Full-res images use up to ~3× more image tokens. Remove scale-factor conversion on bounding-box coordinates; 4.7 returns 1:1 with actual pixels.
- Add `"Avoid over-engineering"` for coding tasks -- Opus tends to over-abstract

For complete guide, read `${CLAUDE_SKILL_DIR}/references/PROMPTING_CLAUDE.md`.

### Claude Sonnet 4.6 -- "The Workhorse"

**Strengths:** Near-Opus coding (79.6% SWE-bench) at ~60% cost, GDPval 1633 (actually *beats* Opus on expert preference), best speed/intelligence ratio. 1M native context (GA March 13, 2026).
**Weaknesses:** May guess tool parameters instead of asking, 64K max output (vs Opus 128K).

**Quick prompting tips:**
- Same XML tag patterns as Opus
- Use **adaptive thinking** (`thinking: {type: "adaptive"}`).
- Adaptive thinking automatically enables **interleaved thinking** (between tool calls) — no beta header needed.
- Add parameter validation instruction: `"If a required parameter is missing, ask instead of guessing"`
- Set `max_tokens` to 64K at medium/high effort to give room for thinking
- Best at `medium` effort for most applications; `low` for high-volume

For complete guide, read `${CLAUDE_SKILL_DIR}/references/PROMPTING_CLAUDE.md`.

### GPT-5.4 -- "The Professional"

**Strengths:** 1M context (up from 400K), math (MATH 98%+, AIME 100%), vision + native computer use, 33% fewer claim errors vs 5.2 (SimpleQA ~72% inferred), Tool Search API, structured outputs, 90% prompt cache discount. Consolidates GPT-5.3-Codex coding capabilities. First general-purpose model rated **High capability in Cybersecurity** (Preparedness Framework) — strong at CTF, CVE exploitation, end-to-end cyber operations.
**Weaknesses:** Abstract reasoning still below Gemini (ARC-AGI-2 52.9%). CoT controllability is near-zero (0.3% at 10k chars) — you cannot steer what the model reasons about via prompts. CoT monitorability lower than GPT-5 Thinking overall (but near-100% for agentic misalignment detection).
**Pricing:** $2.50/$15.00 per MTok (<272K context), $5.00/$22.50 (>272K). 90% cache discount. 272K boundary means long-context work costs 2x — prefer Gemini for bulk 1M ingestion.

**Variants** (same weights, different compute ceiling):
- GPT-5.4 (base) — API/llmx, effort none→high. Default for programmatic use.
- GPT-5.4 effort=xhigh — API/llmx, extended reasoning. Pro-lite. Timeouts at ~15 min.
- GPT-5.4 Pro — **ChatGPT Pro web UI only** ($200/mo). No API access. No time ceiling. Use for domain-heavy derivations that exceed 15 min.
- "Thinking" in ChatGPT web UI = effort=high (the default mode). Not a separate model.

**Effort levels:** `none` (no reasoning, enables temperature/top_p), `minimal`, `low`, `medium`, `high` (default via llmx), `xhigh` (max compute).

**Quick prompting tips (thinking mode, high effort):**
- Do **NOT** use "think step by step" -- hurts performance when thinking is on
- Keep prompts **simple and direct** -- the model does heavy reasoning internally
- Use **`strict: true`** on all function definitions -- guaranteed schema conformance
- Use **XML format** for documents: `<doc id='1' title='Title'>Content</doc>` (JSON performs poorly)
- Add `Formatting re-enabled` as first line of developer message (markdown off by default in thinking)
- Enable **web search** for fact-sensitive queries
- Use Responses API with `previous_response_id` for **reasoning persistence** across tool calls
- **STATIC prefix (top) + DYNAMIC content (bottom)** for 90% cache discount
- **Tool Search** for large tool sets -- avoids dumping all tool definitions into prompt
- **llmx defaults to `--reasoning-effort high`** for GPT-5 models automatically

For complete guide, read `${CLAUDE_SKILL_DIR}/references/PROMPTING_GPT.md`.

### GPT-5.3 Instant -- "The Restructurer"

**Strengths:** Less preachy than 5.2 (fewer defensive disclaimers), 26.8% reduced hallucination with search, structured output, fast responses, good for doc→schema extraction.
**Weaknesses:** Max `reasoning_effort: medium` (no deep analysis), 16K max output (half of 5.2), same pricing as 5.2, 128K context.

**Quick prompting tips:**
- llmx name: `gpt-5.3-chat-latest` — **NOT** `gpt-5.3` or `gpt-5.3-instant` (404)
- Auto-defaults to `--reasoning-effort medium` (only supported level)
- Use `--schema` for structured extraction — combines well with reduced hallucination
- Same XML format tip as 5.2: `<doc id='1' title='Title'>Content</doc>`
- Good at: entity extraction from research papers, restructuring documents into schemas, summarization
- **When to use over 5.4:** conversational tasks, schema extraction, anything that doesn't need deep reasoning
- **When to use 5.4 instead:** math verification, formal analysis, outputs >16K tokens, computer use

### Gemini 3 Flash -- "The Budget Workhorse"

**Strengths:** $0.50/$3/M (cheapest capable Gemini), 1M context, 65K max output, thinking mode.
**Weaknesses:** Shallower analysis than Pro on complex multi-file reasoning, less tested for deep architectural review.

**Quick prompting tips:**
- llmx name: `gemini-3-flash-preview`
- Supports `--reasoning-effort low/medium/high`
- Temperature locked at 1.0 server-side (thinking model)
- Same prompting patterns as Gemini Pro: query at END, critical constraints at END
- Best for: high-volume classification, document processing, mechanical audits, extraction
- **When to use over Pro:** cost-sensitive tasks, high-volume processing, reviews under 50K context
- **When to use Pro instead:** architectural review, multi-file cross-referencing, outputs requiring deep reasoning

### Gemini 3.1 Flash-Lite -- "The Speed Demon"

**Strengths:** $0.25/$1.50/M (**cheapest frontier model**), 99th percentile speed (389 tok/s), 1M context, 1000K output. Best cost/speed ratio for high-volume workloads.
**Weaknesses:** Lower intelligence (34 vs Flash 46, Pro 57), not Pareto-optimal (Flash non-reasoning is cheaper AND smarter), struggles with complex reasoning.

**Quick prompting tips:**
- llmx name: `gemini-3.1-flash-lite-preview`
- **3x cheaper than Flash**, 12x cheaper than Pro — use for ultra-high-volume tasks
- Same 1M context window as other Gemini 3 models
- Best for: translation, content moderation, UI generation, simulations, simple classification
- **When to use over Flash:** pure speed matters, maximum cost reduction on simple tasks
- **When to use Flash/Pro instead:** reasoning, math, multi-step analysis, fact-sensitive work
- Released March 3, 2026 — monitor for stability before production use

### Grok 4.20 Reasoning -- "The Calibrated Skeptic"

**Real third-party category wins** (cross-checked Artificial Analysis, LiveBench, LMArena, Apr 2026):
- **AA-Omniscience hallucination rate #1** — 17% (v2 0309), beating Claude 4.5 Haiku at 25%. Wins by abstaining aggressively rather than knowing more.
- **IFBench #1** — 82.9% strict instruction-following (note: IFBench ≠ IFEval, where it's untested; +29.2pp over Grok 4).
- **LiveBench Data Analysis #1** — 87.06 sub-score.
- **LMArena Search Arena #1** — 1226 ELO, ahead of GPT-5.2 Search (1219) and Gemini 3 Pro Grounding (1215).
- **τ²-Bench Telecom #2** — 97% agentic tool-use (behind GLM-5).

**Honest weaknesses:**
- **AA-Omniscience Index #3** (15) — Gemini 3.1 Pro wins the *composite* (33). Grok wins on raw fabrication rate, not on calibrated knowledge breadth.
- **Math is the weak axis** — LiveBench Math 43.33 (lowest sub-score), LMArena Math 1458. Don't route hard math to Grok.
- AA Intelligence Index 49 (#11/132) vs GPT-5.4/Gemini 3.1 Pro at 57, Opus at 53.
- SWE-Bench 73.5% (below Claude/GPT ~80%), GPQA 78.5% (below Gemini 94.3%).
- **2M context window is unverified by independent benchmarks.** No published RULER / MRCR-v2 / LongBench-v2 score for Grok 4.20. xAI's ">95% NIAH at all 2M positions" is vendor-sourced. AA confirmed *capacity*, not *retrieval quality at scale*.
- **20× price cliff above 200K input** ($40/$120 per M) makes the 2M window economically usable only up to 200K.
- **Multi-agent variant underperforms single-model** on AI Benchy (#47 vs #24). Cost scales without intelligence return — avoid by default.
- xAI hasn't disclosed AIME/HLE/LiveCodeBench/ARC-AGI numbers for the `-reasoning` SKU.
- **No published Simon Willison / Ethan Mollick / Aidan McLau review** of Grok 4.20 (negative finding as of 2026-04-16). Hands-on testers (Medium/Elizabeta, 5hr) confirm all four frontier models including Grok fail the same reasoning traps — Grok was *fastest* but didn't break any pattern.

**Quick prompting tips:**
- **Do NOT pass `reasoning_effort` to `grok-4.20-reasoning`** — the API errors out. The model reasons automatically. Only `grok-4.20-multi-agent` accepts a `reasoning.effort` field, and there it controls **agent count** (low/med→4, high/xhigh→16), not thinking depth.
- **`logprobs` is silently ignored** on all 4.20 SKUs. Don't rely on it.
- **Endpoint:** `https://api.x.ai/v1` — both native Responses API and OpenAI-compatible SDK. Use `openai` client with `base_url="https://api.x.ai/v1"` for drop-in compatibility.
- **Pair with web grounding** for current events — knowledge cutoff is Sep 1, 2025.
- **xAI web search not yet supported** via OpenAI SDK (per llmx provider notes) — use Exa/Perplexity/Brave separately for grounding.
- **Don't pass full documents >200K tokens** — price cliff + multi-needle retrieval at scale unverified. Pre-summarize or chunk.
- **Best-fit applications:**
  1. **Claim/quote verification on synthesized outputs** (research-mcp paper synthesis post-pass) — AA-Omniscience methodology directly maps to citation-fabrication failure mode. ~$0.03/synthesis check at $6/M output.
  2. **Convergent "no findings" verification** (session-analyst, audit outputs) — second-pass adversarial reviewer with prompt that strongly prefers UNCERTAIN over guessing. Probe with 50 findings before deploying broadly.
  3. **Web-grounded search re-ranking** — its LMArena Search Arena #1 holds when paired with external grounding (Exa/Perplexity).
- **Don't use for:** raw math, hard agentic coding, GPQA-tier science reasoning, deep multi-step abstract reasoning, anything >200K context. Don't add as a 3rd `/critique model` opinion (epistemic diversity vs Gemini+GPT is small — its strength is abstention, not adversarial design pressure).

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
- **llmx supports `--reasoning-effort`** for Gemini (maps to thinkingLevel internally)

For complete guide, read `${CLAUDE_SKILL_DIR}/references/PROMPTING_GEMINI.md`.

## Validation Checklists

Run these when using outputs from each model:

### All Models
- [ ] **Don't trust reasoning traces as evidence of correctness.** CoT faithfulness baseline: 7-13% unfaithful (multiple sources). The model can reach the right answer via wrong reasoning, or vice versa.
- [ ] **Cross-family review for non-trivial decisions.** Same-model correction: 59.1% accuracy. Cross-family: 90.4% (FINCH-ZK). Same-family models share ~60% of errors (Kim et al. ICML 2025).
- [ ] **Sequential debate doesn't improve correctness** (martingale proof, Choi et al. ACL 2025). Use independent parallel reviews + voting, not models critiquing each other.

### After Claude Opus/Sonnet 4.6
- [ ] Cross-check mathematical derivations (MATH 93% < GPT's 98%)
- [ ] For novel abstract patterns, consider Gemini second opinion
- [ ] On documents near 1M tokens, check for context-edge information loss (MRCR v2: 78.3% at 1M)

### After GPT-5.4
- [ ] **Still fact-check** (SimpleQA ~72% inferred -- improved from 5.2's 58%, but 28% error rate remains)
- [ ] Don't trust unsourced claims -- demand citations
- [ ] Abstract reasoning still below Gemini -- consider Gemini second opinion for novel patterns
- [ ] Destructive action avoidance: 0.86 (slightly below GPT-5.3-Codex 0.88) -- verify file operations in agentic use
- [ ] `max_completion_tokens` includes reasoning tokens — 4096 + high effort = 0 output. Use 16384+ for reasoning models

### After Gemini 3.1 Pro
- [ ] Verify it followed instructions precisely (IFEval 89.2% -- misses ~11%)
- [ ] Expert-quality writing may need editing (GDPval 1317 vs Claude 1606)
- [ ] Check output wasn't silently truncated (64K max, 8K default)

## Cost Comparison

| Model | Input/MTok | Output/MTok | Cache Discount | Context | Max Output |
|-------|:----------:|:-----------:|:--------------:|:-------:|:----------:|
| Claude Opus 4.7 | $5 | $25 | -- | 1M | 128K |
| Claude Sonnet 4.6 | $3 | $15 | -- | 1M | 64K |
| GPT-5.4 (<272K) | $2.50 | $15.00 | 90% ($0.25) | 1M | 128K |
| GPT-5.4 (>272K) | $5.00 | $22.50 | 90% ($0.50) | 1M | 128K |
| GPT-5.3 Instant | $1.75 | $14 | 90% input | 128K | 16K |
| Gemini 3.1 Pro | $2 | $12 | 75% | 1M | 64K |
| **Gemini 3 Flash** | **$0.50** | **$3** | 75% | 1M | 65K |
| **Gemini 3.1 Flash-Lite** | **$0.25** | **$1.50** | 75% | 1M | 1000K |
| Grok 4.20 Reasoning (≤200K in) | $2 | $6 | 90% ($0.20) | **2M** | 128K |
| Grok 4.20 Reasoning (>200K in) | **$40** | **$120** | 90% ($4.00) | 2M | 128K |

**Cost optimization:** Default to Sonnet 4.6 for subagents. Reserve Opus for synthesis, narratives, and orchestration. Use Gemini Flash/Flash-Lite for bulk work. GPT-5.4 with cache hits ($0.25/M input) is the cheapest frontier reasoning — but only for cache-friendly workloads with static prefixes. For long-context (>272K), Gemini Pro ($2/$12) is cheaper than GPT-5.4 ($5/$22.50).

## Multi-Model Architecture Pattern

```
Claude (orchestrator -- best professional judgment)
  ├── Data tools (DuckDB, CLI tools -- ground truth)
  └── Multi-model validation
        ├── review    → Pro + GPT-5.4          [adversarial, ~$3-5]
        ├── pattern   → Gemini 3.1 Pro        [1M context, ARC-AGI-2 77.1%]
        ├── verify    → Gemini 3 Flash        [$0.50/M, fast fact-check]
        ├── extract   → GPT-5.3              [doc→schema, less preachy]
        ├── math      → GPT-5.4              [MATH 98%+, AIME 100%]
        ├── classify  → Gemini 3 Flash        [$0.50/M, high-volume]
        └── compare   → Multiple             [side-by-side for high-stakes]
```

**Cross-family rule:** Never use the same model family for both review and synthesis. GPT reviewing GPT = self-preference bias (74.9% demographic parity bias, Wataoka NeurIPS 2024). Gemini Flash fallback for Gemini Pro review = same family, defeats adversarial purpose. Use GPT-fast to extract Gemini claims, Gemini-fast to extract GPT claims.

## The Hallucination Problem

| Model | SimpleQA | Error Rate |
|-------|:--------:|:----------:|
| Claude Opus 4.7 | 72% | 28% wrong |
| Gemini 3.1 Pro | 72.1% | 28% wrong |
| GPT-5.4 | ~72% | ~28% wrong (33% fewer errors vs 5.2) |
| GPT-5.4 + web search | ~95%+ | ~5% wrong |
| Grok 4.20 Reasoning | n/a (no public SimpleQA); **AA-Omniscience 78%** (best at calibrated abstention) | -- |

**Key insight:** GPT-5.4 closed most of the hallucination gap vs Claude/Gemini (33% fewer errors vs 5.2). But ~28% error rate remains — always query data sources for dollar amounts, dates, entity names, and legal claims.

**AA-Omniscience vs SimpleQA:** SimpleQA tests *factual recall* ("did the model know the answer?"). AA-Omniscience tests *calibrated abstention* ("when the model didn't know, did it say 'I don't know' instead of fabricating?"). Grok 4.20 Reasoning leads on the second axis — useful for verification workflows where false confidence is more costly than missing answers.

## Compliance Pressure & Null Paths

All frontier models share a structural failure: when a prompt asks "find X" or "analyze Y for Z," the most probable completion is findings, not "nothing found." The prompt shape determines the answer shape before reasoning begins. Extended thinking makes this worse — more token space = more room to construct elaborate justifications for findings that aren't there (arXiv:2602.07796, "Thinking Makes LLM Agents Introverted").

**This is not sycophancy toward the user — it's sycophancy toward the prompt itself.**

### Patterns That Reduce Compliance Pressure

**1. Triage gate before elaboration.** Force a classification step before detailed analysis:
```
Phase 1: Does this [thing] have problems worth reporting? (YES / NO / MINOR ONLY)
  If NO → output one-line justification and stop.
  If MINOR → one-line notes only.
  If YES → proceed to detailed analysis.
```
The gate makes refusal a first-class output with lower token cost than fabrication.

**2. Explicit null output format.** Give the model a formatted, easy-to-complete "nothing here" option:
```
If no significant findings exist, output EXACTLY:
## Result: No actionable findings
Reason: [one line]
```
Without this, the null path requires generating a novel structure — lower probability than filling the expected template.

**3. Contrastive framing.** "What's wrong with X?" primes for findings. Better: "Does X have problems, or is it fine as-is?" gives both completions similar probability. Numeric scales ("Rate 1-5") avoid elaboration priming entirely.

**4. Third-person perspective.** "A reviewer examining this would say..." reduces sycophancy by up to 63.8% (SYCON Bench, arXiv:2505.23840). The perspective shift breaks the helpfulness frame.

**5. Normalize the null.** State that no findings is expected and valid: "Many sessions will have no findings — report that." Counterbalances the 14 "look for X" items that follow.

### Convergent vs Divergent Evaluation

Not all evaluative prompts need the same fix. The distinction:

| Mode | Question shape | Example skills | Mitigation |
|------|---------------|----------------|------------|
| **Convergent** | "Is there a problem?" (yes/no) | session-analyst, verify-findings, bio-verify, retro | **Triage gate** — force YES/NO classification before elaboration |
| **Divergent** | "What could be better?" (always has answers) | design-review, project-upgrade, suggest-skill, brainstorm | **Downstream filtering** — let generation run, filter quality after |
| **Exploratory** | "What's missing?" (absence is the finding) | negative-space-sweep, novel-expansion | **Neither** — divergent by design, pertinent negatives are the output |

**Why different fixes:** Next-token prediction is convergent by nature (research/divergent-convergent-thinking-llms.md). For convergent evaluation, the model defaults to "yes, problem found" because elaboration has higher token probability than refusal — a triage gate fixes this by making refusal a first-class completion. For divergent evaluation, gating would *suppress useful output* — the model should generate freely, and quality filtering happens downstream (disposition tables, verify-findings, dedup).

**The structural insight:** Compliance pressure is a convergent-mode failure. In divergent mode, the same pressure is actually productive — you *want* the model to generate aggressively. The problem is when a prompt is convergent (should I report this?) but the template forces divergent output (fill in these 14 finding slots).

### When To Apply Triage Gates

Apply to prompts where:
- The honest answer might be "nothing to report" (convergent evaluation)
- Structured output templates have slots that create fill-pressure
- External model dispatch increases fabrication risk (less project context)
- Findings drive downstream actions (hooks, rules, code changes)

Do NOT gate:
- Divergent/creative prompts (brainstorm, design-review, suggest-skill) — use downstream filtering instead
- Exploratory prompts (negative-space-sweep) — absence is the output
- Prescriptive/reference prompts, code generation, direct Q&A

## When to Update This Skill

Update after any frontier model release:
1. Update `${CLAUDE_SKILL_DIR}/references/BENCHMARKS.md` with new scores
2. Update relevant `references/PROMPTING_*.md` with API/behavior changes
3. Update selection matrix if rankings change
4. Add entry to `references/CHANGELOG.md`
