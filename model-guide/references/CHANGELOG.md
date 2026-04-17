# Model Guide Changelog

Track what changes with each model release so you know what to update.

## 2026-04-16 -- Add Grok 4.20 Reasoning

xAI's `grok-4.20-0309-reasoning` (public beta 2026-02-17, GA 2026-03-10, "0309" snapshot 2026-03-31) added to selection matrix, profile section, cost table, hallucination table, and BENCHMARKS.md.

### Key positioning (deep-research pass via /research, 2026-04-16)
- **Standout differentiator:** **AA-Omniscience hallucination rate 17%** (v2 0309) — #1 lowest fabrication rate. Wins by abstaining aggressively. Note: on the *composite* AA-Omniscience Index, Grok ranks #3 (15) behind Gemini 3.1 Pro (#1, 33) — Gemini both knows more *and* abstains well. (Earlier "78%" figure = non-hallucination rate, framed misleadingly without composite context.)
- **Real third-party category wins** (cross-checked AA + LiveBench + LMArena):
  - IFBench #1 at 82.9% (note: IFBench ≠ IFEval; +29.2pp over Grok 4)
  - LiveBench Data Analysis #1 at 87.06
  - LMArena Search Arena #1 at 1226 ELO (ahead of GPT-5.2 Search 1219, Gemini 3 Pro Grounding 1215)
  - τ²-Bench Telecom #2 at 97% (agentic tool-use, behind GLM-5)
- **Math is the weak axis** — LiveBench Math 43.33 (lowest sub-score), LMArena Math 1458. Don't route hard math to Grok.
- **2M context unverified by independent multi-needle benchmarks** — Awesome Agents leaderboard explicitly lists Grok 4 Fast (2M) with all RULER/MRCR-v2/LongBench-v2 scores as dashes. xAI's ">95% NIAH at 2M" is vendor-sourced. AA confirmed *capacity*, not *retrieval quality at scale*. Treat as marketing for now.
- **Multi-agent variant underperforms single-model** on AI Benchy (#47 vs #24, agent-wars.com 2026-03-13). Cost scales without intelligence return.
- **Pricing:** $2/$6 per M (≤200K input), $0.20/M cached. Cheaper output than Sonnet, Opus, GPT-5.4, Gemini Pro.
- **Long-context cliff:** >200K input triggers $40/$120 tier (20×). Operationally use up to 200K only.
- **No published Simon Willison / Mollick / McLau review** as of 2026-04-16 — negative finding (could be search miss, but no viral practitioner endorsement to date).

### API gotchas
- `reasoning_effort` param **errors** on `grok-4.20-reasoning` — model reasons automatically.
- On `grok-4.20-multi-agent`, `reasoning.effort` controls **agent count** (low/med→4 agents, high/xhigh→16), not depth.
- `logprobs` silently ignored on all 4.20 SKUs.
- Endpoint `https://api.x.ai/v1` — both native Responses API and OpenAI-compatible SDK.
- xAI web search not yet supported via OpenAI SDK (per llmx provider notes).

### Integration verdicts (from /research)
- **ADOPT — research-mcp claim/quote verification.** AA-Omniscience methodology directly maps to citation-fabrication failure mode. Pattern: `verify_claim_with_quote(claim, quote, paper_text) -> {SUPPORTED, NOT_SUPPORTED, ABSTAIN}` after Claude synthesis. ~$0.03/synthesis check at typical volumes. Use the **non-reasoning** variant for high-volume (abstention bias is in post-training, not CoT).
- **PROBE-FIRST — session-analyst / agent-infra audit second-pass.** Run 50-finding probe against last 30 days of session-analyst output. Measure how many findings Grok flags as NOT_SUPPORTED that human review confirms were noise. Deploy if catch rate >10%; don't deploy if <5% (theater).
- **DECLINE — `/critique model` 3rd opinion.** Grok 4.20's strengths are abstention and IF, not adversarial design pressure. Cross-family value of /critique is epistemic diversity — xAI's lineage is real but its training data overlaps OpenAI/Anthropic enough that novel critiques are rare. AA Intelligence Index 49 vs Gemini/GPT 57 also means it under-calls complex critiques.
- **DECLINE — PGx variant verification.** AA-Omniscience Health domain is general health knowledge, not clinical-grade. PGx hallucinations are *typed* (wrong star allele) not *unknown* — abstention bias doesn't help unless paired with PharmCAT/CPIC structured grounding. Reuse claim/quote pattern (above) for PGx literature only.

### Verification gaps (flagged, not fabricated)
- No public AIME / HLE / LiveCodeBench / ARC-AGI / MMLU number for the `-reasoning` SKU specifically. Cells marked `--` in BENCHMARKS.md.
- No Opus 4.7 head-to-head on Grok-equivalent tasks.
- Pricing inconsistency in third-party recaps ($20/$60 vs xAI's $2/$6) likely Grok-4-base conflation; xAI docs treated as canonical.

### Files updated
- model-guide/SKILL.md (selection matrix, profile, cost table, hallucination table, models-covered list)
- model-guide/references/BENCHMARKS.md (head-to-head column, AA-Omniscience row, AA Intelligence Index row, pricing rows, category-winners rows)
- llmx-guide/SKILL.md, references/models.md, references/transport-routing.md (xAI provider, model names, reasoning_effort gotcha, search support)

## 2026-04-16 -- Claude Opus 4.7 Release

**Claude Opus 4.7 replaces Opus 4.6 as the default Opus model.** Same pricing ($5/$25), 1M native context (no long-context premium), 128K max output.

### Key changes
- **Default model:** `claude-opus-4-6` → `claude-opus-4-7` across SKILL.md, claude-api reference docs, and prompting guides.
- **Effort levels:** new `xhigh` level between `high` and `max`. Recommended default for coding/agentic.
- **Adaptive thinking:** OFF by default on 4.7 — must be set explicitly. `budget_tokens` returns 400. `thinking.display` defaults to `"omitted"` (set `"summarized"` for visible reasoning in UIs).
- **Sampling parameters removed:** `temperature`, `top_p`, `top_k` all return 400. Steer via prompting.
- **Tokenizer:** new tokenizer produces 1.0–1.35× more input tokens than Opus 4.6 for the same text.
- **Vision:** high-resolution image support up to 2576px / 3.75 MP (up to ~4,784 tokens per full-res image). Bounding-box coordinates are 1:1 with image pixels.
- **Behavior:** more literal instruction following, fewer subagents/tool calls by default, stricter effort calibration at low/medium, more direct tone.
- **New stop_reason:** `model_context_window_exceeded` (distinct from `max_tokens`).
- **Task budgets:** new beta feature (`task-budgets-2026-03-13`) for agentic loops to self-pace.
- **Beta headers now GA** and removed from docs: `effort-2025-11-24`, `interleaved-thinking-2025-05-14`, `fine-grained-tool-streaming-2025-05-14`, `structured-outputs-2025-11-13`.
- **Legacy model catalog trimmed:** `shared/models.md` now lists only current frontier (Opus 4.7, Sonnet 4.6, Haiku 4.5). Older models resolved via WebFetch of the Anthropic Models Overview.

### Files updated
- claude-api SKILL.md + all language refs (Python, TypeScript, Java, Go, Ruby, C#, PHP, cURL)
- claude-api shared/ (models.md, error-codes.md, tool-use-concepts.md, live-sources.md)
- model-guide SKILL.md (selection matrix, Opus profile, cost table, Sonnet profile)
- model-guide references (PROMPTING_CLAUDE.md rewritten, BENCHMARKS.md relabeled)
- agent-infra: skill-authoring example; compaction-canary (no functional change)

## 2026-04-08 -- Drop Kimi K2.5, Add Flash-Lite

### Key changes
- **Kimi K2.5 removed** from all model selection, benchmarks, prompting guides, and routing. 63% hallucination rate + derivative reasoning capabilities don't justify the routing complexity. Only Claude, GPT, and Gemini models tracked.
- **Gemini 3.1 Flash-Lite added** to cost table ($0.25/$1.50, cheapest frontier).
- **Review skill**: cross-model CLI dispatch no longer default. Direct analysis is primary path; model-review.py available for user-initiated dispatch.
- **Observe skill**: all modes use direct Claude analysis instead of Gemini dispatch via llmx.

### Files updated
- SKILL.md: selection matrix, profiles, cost table, hallucination table
- BENCHMARKS.md: Kimi rows removed, Flash-Lite added
- PROMPTING_KIMI.md: deleted
- review/SKILL.md: dispatch made optional
- observe/SKILL.md: Gemini dispatch removed
- improve/SKILL.md: Gemini dispatch removed from suggest mode
- llmx-guide references: Kimi model names removed
- meta/scripts: Kimi adapter and fixtures removed

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

## 2026-03-20 -- Freshness Sweep (Codex audit + web verification)

### Key changes
- **Claude 1M context is GA** (announced March 13). All "200K (1M beta)" references updated to "1M". MRCR v2: 78.3% at 1M tokens (highest among frontier models). Media limits: 600 images/PDF pages per request.
- **GPT-5.4 max output: 128K** (was TBD). Context: 1.1M (922K input + 128K output). Sources: CloudPrice, Galaxy.ai.
- **GPT-5.4 ARC-AGI-2: 52.9%** synced from BENCHMARKS.md to SKILL.md profile (was TBD in profile).
- **Sonnet cost description**: "1/5 cost" → "~60% cost" ($3/$15 vs $5/$25 = 60%, not 20%).
- **Gemini 3 Pro deprecated March 9**: llmx name `gemini-3-pro-preview` → `gemini-3.1-pro-preview` in PROMPTING_GEMINI.md.
- **Gemini Pro thinking**: `medium` not supported on Pro (low + high only). Corrected in thinking table.
- **PROMPTING_KIMI comparison table**: GPT-5.4 pricing $1.75/$14 → $2.50/$15, factual accuracy 58% → ~72%, video now supported.
- **PROMPTING_GEMINI comparison table**: Claude context → 1M, GPT context 400K → 1M.
- Long context category updated: all three frontier families (Claude, GPT, Gemini) now 1M native.

### Audit methodology
- 2 Codex (GPT-5.4) agents dispatched for internal consistency and prompting guide audits
- Web freshness sweep via Brave + Exa for all 4 model families
- ~28% Codex error rate on counts/severity — all findings verified against actual code

### GPT-5.3 Instant, Gemini 3 Flash, Gemini 3.1 Flash-Lite provenance
These models were added between 2026-03-06 and 2026-03-07 but not documented in this changelog. They remain in SKILL.md but are absent from BENCHMARKS.md benchmark tables. Backfill noted.

### Not updated (deferred)
- PROMPTING_GPT.md: `response_format` → `text.format` API drift (Responses API), `strict: true` default, `original` image detail mode, 24h cache retention scope — need API testing to confirm
- PROMPTING_KIMI.md: kimi-k2-thinking / kimi-k2-thinking-turbo variants, llmx model name — need Moonshot API testing
- BENCHMARKS.md: GPT-5.3 Instant, Flash, Flash-Lite benchmark rows — data not yet available
- Gemini context caching: 75% → possibly 90% discount on Vertex AI — conflicting sources

## 2026-03-06 -- GPT-5.4 Pricing + Full Effort Spectrum

### Key changes
- GPT-5.4 pricing confirmed: $2.50/$15.00 (<272K), $5.00/$22.50 (>272K), 90% cache discount
- Full reasoning effort spectrum documented: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`
- `none` effort enables temperature/top_p/logprobs (only way to use these params)
- `xhigh` effort verified working via llmx
- `phase` parameter documented (Responses API: `commentary`/`final_answer` for multi-step tasks)
- 272K pricing boundary noted — long-context work costs 2x input
- GPT-5.4 Pro noted as variant (slow, manual testing recommended)

### Not added (user decision)
- gpt-5-mini ($0.25/$2.00) and gpt-5-nano ($0.05/$0.40) exist and work via llmx but intentionally excluded from guide

### Files updated
- SKILL.md: pricing table, model profile (pricing, effort levels, Pro note)
- BENCHMARKS.md: pricing table
- PROMPTING_GPT.md: none/xhigh effort, phase parameter, effort table, key differences table

## Update Checklist

When a new frontier model releases:

1. [ ] Update `BENCHMARKS.md` -- new scores, pricing, context limits
2. [ ] Update relevant `PROMPTING_*.md` -- API changes, new features, deprecated features
3. [ ] Update `SKILL.md` selection matrix if rankings change
4. [ ] Update `SKILL.md` cost table
5. [ ] Add changelog entry with date and key changes
6. [ ] Consider whether any model should be added or removed from coverage
