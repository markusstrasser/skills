# GPT-5.4 Prompting Guide

Specific to GPT-5.4 with thinking (high effort). Updated 2026-03-06. Most GPT-5.4 prompting patterns carry forward — GPT-5.4 adds 1M context, native computer use, Tool Search, and fewer hallucinations.

**Sources:** OpenAI official docs (developers.openai.com).

---

## 1. Thinking Mode -- The Default

GPT-5.4 with thinking enabled at high effort is the version that hits the frontier benchmarks (MATH 98%, AIME 100%, DocVQA 95%). Always use thinking mode for non-trivial work.

### `none` Effort — Non-Thinking Mode

Setting `reasoning.effort: "none"` disables internal reasoning entirely. This is the **only** way to use `temperature`, `top_p`, and `logprobs` — these parameters are unavailable at any other effort level.

```bash
llmx -m gpt-5.4 --reasoning-effort none --temperature 0.9 "creative writing prompt"
```

Use `none` for: creative generation needing temperature control, logprob analysis, classification where reasoning overhead isn't worth it.

### Critical Rules

**Do NOT use chain-of-thought prompting** ("think step by step") -- the model reasons internally. Explicit CoT scaffolding **hurts performance** when thinking is on.

**DO:**
- Keep prompts simple and direct -- the model does the heavy reasoning internally
- Use delimiters (markdown, XML) for structure
- Start with zero-shot; add few-shot only if needed
- Let the model allocate its own reasoning budget

**DO NOT:**
- Ask it to "explain your reasoning" or "show your work"
- Prescribe step-by-step plans -- the model's internal reasoning exceeds what you'd prescribe
- Over-engineer prompts with CoT scaffolding or "think carefully" instructions

### Effort Levels

```python
# Direct API
response = client.responses.create(
    model="gpt-5.4",
    reasoning={"effort": "high"},  # none, minimal, low, medium, high, xhigh
    input=[...]
)
```

```bash
# Via llmx (our unified CLI) -- defaults to high effort for GPT-5 models
llmx -m gpt-5.4 "complex query"                                    # Defaults to --reasoning-effort high
llmx -m gpt-5.4 --reasoning-effort high --stream "complex query"    # Explicit (same result)
llmx -m gpt-5.4 --reasoning-effort low "simple query"               # Override for speed/cost
```

| Effort | Use When | llmx auto-timeout |
|--------|----------|:-:|
| `xhigh` | Maximum compute — hardest problems, Pro-lite behavior. **Domain-heavy prompts (PGx, clinical) can exceed 15 min and timeout at llmx's 900s cap.** Use ChatGPT Pro for those. Pure math xhigh fits in ~8 min. | 900s (15 min, hard max) |
| `high` | Complex reasoning, math, analysis, coding -- **use this for serious work** | 600s (10 min) |
| `medium` | Balanced cost/quality for moderate tasks | 300s (5 min) |
| `low` | Moderate queries, cost-sensitive | 120s |
| `minimal` | Simple queries, high-volume, latency-sensitive | 120s |
| `none` | No reasoning — enables temperature/top_p/logprobs | 120s |

### Reasoning Persistence

Use the Responses API with `store: true` and pass `previous_response_id`. This preserves internal reasoning state across tool calls, directly improving accuracy on multi-step tasks. The Chat Completions API does NOT preserve reasoning items, increasing token usage and reducing quality.

### `phase` Parameter (Responses API)

For multi-step agentic tasks, set `phase` on assistant messages to prevent early stopping:
- `"commentary"` — intermediate updates, preambles before tool calls
- `"final_answer"` — completed response

Without `phase`, the model may treat intermediate commentary as a final answer and stop prematurely. Important for pipelines with tool call sequences.

### CoT Controllability (System Card, March 2026)

GPT-5.4 Thinking has **near-zero CoT controllability**: only 0.3% of 10k-character reasoning chains can be steered by user instructions (e.g., avoiding keywords, formatting constraints on the chain). This means:
- You **cannot** control what the model thinks about via prompting
- Don't waste prompt space trying to shape the reasoning chain — shape the *output* instead
- This is a safety property (low obfuscation ability) but also a practical constraint

CoT **monitorability** is lower than GPT-5 Thinking overall, but near-100% for detecting agentic misalignment. Safety monitors reading the CoT can still catch problematic reasoning.

### Markdown in Thinking Mode

Thinking mode **disables markdown by default**. To re-enable, add as the first line of your developer message:

```
Formatting re-enabled
```

---

## 1b. GPT-5.4 Pro vs Thinking vs xhigh — What's Actually Different

**Same weights, different compute ceilings.** All three are the same model:

| Variant | Access | Reasoning budget | Pricing (in/out per MTok) | Timeout |
|---------|--------|-----------------|--------------------------|---------|
| `gpt-5.4` effort=high | API, llmx | Standard reasoning | $2.50/$15 | ~10 min |
| `gpt-5.4` effort=xhigh | API, llmx | Extended reasoning | $2.50/$15 | ~15 min (llmx hard cap 900s) |
| `gpt-5.4-pro` | ChatGPT Pro web UI only | Maximum reasoning — no practical ceiling | Subscription ($200/mo) | Minutes to tens of minutes |
| GPT-5.4 Thinking | ChatGPT web UI | Same as effort=high (default) | Subscription | N/A |

**The only real difference is how long the model is allowed to think.** `xhigh` on base is "Pro-lite" — same extended reasoning, but capped by API timeout. Pro can think for 10+ minutes on a single request with no ceiling. ChatGPT "Thinking" in the web UI is just `effort=high` as the default mode.

**When does extra thinking time matter?** From our 59 Q&A eval:
- Pure math (Bayesian derivations, HWE calculations): `xhigh` via llmx is sufficient (~8 min). Zero errors.
- Domain-heavy prompts (PGx risk models, clinical decision trees): exceeded llmx's 900s cap. Had to use ChatGPT Pro web UI.
- We did NOT A/B test the same prompt at high vs xhigh vs Pro, so we can't confirm that Pro's extra compute produces measurably better answers vs xhigh. The zero-math-error result was all Pro — it might hold at xhigh too.

**Practical rule:** Start with `effort=high` (default). Escalate to `xhigh` if the answer feels incomplete or the reasoning chain was truncated. Use ChatGPT Pro web UI for prompts that need >15 min reasoning (multi-domain clinical synthesis, architectural audits with >10K lines of context).

### When to Use Pro

Pro is justified when the problem has **all three** of:
1. **Multi-step quantitative reasoning** where intermediate errors compound (Bayesian chains, coupled equations, formal proofs)
2. **Verification matters** — you'll check the answer, and a wrong answer has consequences
3. **Not solvable by search** — the answer requires derivation, not lookup

Concrete examples from our genomics eval (2026-03-22, 21 claims verified):
- Bayesian posterior computation with calibrated likelihood ratios (zero errors across 100+ claims)
- Catching planted numerical traps (coordinate normalization, sign errors)
- Adversarial self-review of its own classification (found PP2/LR14 overclaim)
- Multi-step PK fold-change derivations across drug-gene interactions

### When NOT to Use Pro

- **Coding tasks** — base GPT-5.4 (or Claude) is sufficient; Pro's extra reasoning doesn't help linear code generation
- **Literature search/synthesis** — reasoning depth doesn't help fact retrieval (still ~28% hallucination on SimpleQA)
- **Simple classification** — diminishing returns; high effort on base model is equivalent
- **Any task where you won't verify the output** — Pro's value is precision, which only matters if consumed precisely

### Pro Prompting

Same as base GPT-5.4, plus:
- **Keep prompts simple and direct** — Pro's reasoning handles complexity internally. Over-structured prompts waste the reasoning budget on parsing your instructions instead of solving the problem.
- **Include real data, not descriptions** — Pro reasons over exact numbers. "AM=0.976, GPN=-9.6" beats "high AlphaMissense, strong conservation."
- **End with "Show all derivations. I will verify every intermediate step."** — this focuses the reasoning on precision, which is Pro's comparative advantage.
- **Use Responses API with background mode** — requests can take 2-5 minutes. Set `reasoning.effort: "xhigh"` for maximum depth.
- **Budget: `max_completion_tokens: 32768+`** — Pro generates long reasoning chains. 4096 + xhigh effort = 0 output tokens.

### Pro vs Opus for Adversarial Review

Our eval showed GPT-5.4 Pro is **better than Opus at adversarial self-review** — it found mathematical overclaims in its own TP53 classification (PP2 removal dropped posterior from 0.90→0.81, uncalibrated LR14→4.33 dropped to 0.74). Opus tends to be more agreeable with its own outputs. Use Pro for auditing quantitative code, scoring functions, and calibration math.

### Empirical Prompting Patterns (75 Q&A pairs, 6 rounds, 2026-03-22→28)

Corpus: `.scratch/gpt54pro-r{1..6}-qa-*.md` in genomics repo.

**What worked (Round 3: 69% implementation rate):**

1. **Data-hydrated prompts dominate.** Paste actual pipeline output (JSON, scores, variant data), then ask "what's wrong?" Round 3 pasted 516 LOC of `variant_priority_score.py` → found 5 real bugs. Round 1 asked abstract classification questions → 10% implementation rate. The data IS the prompt.

2. **"Derive from first principles" beats "look up the answer."** Asking GPT to derive EUR DPD deficiency prevalence from allele frequencies + Hardy-Weinberg produced exact, verifiable numbers. Asking it to look up CPIC guidelines produced hallucinated citation details. Zero math errors across 100+ quantitative claims, but ~28% hallucination on fact lookup.

3. **Adversarial framing extracts the most.** "Find bugs in this code" and "what's wrong with this classification" outperform "review this" or "what do you think?" The model responds to adversarial pressure with precision; it responds to open-ended asks with balanced hedging.

4. **One derivation per prompt, not surveys.** Focused prompts asking for a single risk model produced 3.5 quant claims/prompt. Architecture-dump megaprompts produced 2.2. Dense > broad.

5. **"Show all derivations. I will verify every intermediate step."** This sentence at the end consistently forced full working, not just conclusions. Without it, Pro often stated results without showing the chain.

6. **"Design X from scratch" > "what's wrong with X."** (R6 finding, 2026-03-28.) Rounds 1-5 asked Pro to audit existing pipeline math — found 14 bugs total (good). Round 6 asked Pro to *design* replacement methods from first principles — found 3 bugs, 7 theoretical bounds, AND produced implementable formulas (concordance-only discount, coalescent ROH estimator, VOI-based triage, stratified FDR null). The design prompts produced higher-impact findings because Pro's extended reasoning explores solution spaces, not just verifies existing ones. Use audit prompts when you suspect specific bugs; use design prompts when you need the correct method and don't trust the current one.

7. **Include the current data distribution.** (R6 finding.) "244 variants → 122 NEEDS_REVIEW, 55 LIKELY_BENIGN, 54 ARTIFACT, 13 BENIGN" let Pro derive that the condition FDR was at null level (z=-0.14) and that 35 T1 variants exceed any 30-variant review budget. Without real counts, Pro gives parametric answers that need separate calibration.

8. **Include boundary conditions from the actual code.** (R6 finding.) "T_max = 5.86 + 2.77 = 8.63 from listed AM/SpliceAI ranges" let Pro derive the exact minimum discount factor for monotonicity (d ≥ 0.7335). Without T_max, Pro gives d ≥ 1 - c_min/T_max as a formula — correct but not actionable until you plug in your own ranges.

9. **Pro corrects prompt assumptions.** (R6 finding.) Pro corrected 5 errors in our prompt setup: n_eff for "10-50%" range (19.17 not 8.6), stroke 10yr risk (3.2% not 5.2% under our stated logistic model), AM=0.95 is in the 1.46 bin not 5.86, minimax regret is degenerate (need expected regret instead), raw tool correlations don't determine I(Y;T_1,...,T_8). These corrections are often more valuable than the answers to the questions asked.

**What failed:**

1. **Prompts without code/data.** Round 3 prompt 09a sent an adversarial audit request without pasting the code. GPT correctly refused — but the lesson is that Pro needs material to reason over. Abstract "audit my approach" prompts get abstract answers.

2. **Citation-dependent prompts.** Any prompt requiring specific paper citations (PMID, author+year+journal) gets fabricated details. The facts are often correct; the citations are invented. Always verify PMIDs. (Confirmed: "correct proof on wrong object" — real finding, fake source.)

3. **Framing sensitivity for classification.** Same TP53 variant got LP in one framing, VUS in another (Round 1). The evidence didn't change — the prompt framing did. Never use GPT for final classification. Use it for derivation, then classify yourself.

4. **Search-enabled prompts for database lookups.** Round 4 enabled web search, which found CPIC coverage gaps — but also returned stale/wrong tool version info. Search helps for "what exists?" but not for "what's the current version of X?"

**Prompt templates:**

*Audit prompt (find bugs in existing math):*
```
Here is [actual code + config, 100-500 lines]:
[paste]

Current data distribution: [paste real counts, e.g. "244 variants → 122 NEEDS_REVIEW"]

Questions (show all working):
1. [Specific quantitative question with boundary conditions from the code]
2. [Ask for the proof/derivation, not just the answer]
```

*Design prompt (derive correct method from scratch):*
```
A pipeline does [X]. Here is the exact architecture:
[paste code + config + real numbers]

Current distribution: [paste real counts]
Known parameter ranges: [paste from code, e.g. "T_max = 5.86 + 2.77 = 8.63"]

Design [replacement method] from first principles. Show all working.
Constraints: [monotonicity, calibration, backward compatibility, etc.]
```

Design prompts produce higher-impact findings than audit prompts (R6 vs R1-R5). Use audit when you suspect specific bugs; use design when you need the correct method.

### llmx Usage

```bash
# Pro is NOT available via API or llmx — ChatGPT Pro web UI only ($200/mo subscription).
# For API, xhigh on base model is the closest:
llmx -m gpt-5.4 --reasoning-effort xhigh --timeout 900 --stream "complex query"

# For domain-heavy prompts that exceed 15 min: use ChatGPT Pro web UI.
# Copy-paste the prompt; Pro has no practical time ceiling.
```

---

## 2. Message Roles

OpenAI defines a strict authority chain: `developer` > `user` > `assistant`.

- The `developer` message (formerly "system message") carries highest priority
- Do NOT use both `developer` and `system` in the same request
- Think of developer and user messages like a function and its arguments

**Recommended developer message structure:**
1. Identity and communication style
2. Instructions, rules, function-calling guidance
3. Examples (input/output pairs)
4. Context and reference data (near end)

---

## 3. Structured Outputs & JSON

GPT-5.4 has the best native structured output support of any frontier model.

### The Hierarchy

| Method | Schema Enforced | Use When |
|--------|:-:|----------|
| **Structured Outputs** (`response_format`) | Guaranteed | Final-step extraction, no back-and-forth |
| **Function Calling** (`strict: true`) | Guaranteed | External API calls, model chooses among tools |
| **JSON Mode** | Valid JSON only | **Not recommended** -- always prefer Structured Outputs |

### Key Rules

- **Always enable `strict: true`** -- requires `additionalProperties: false`
- **Structured Outputs is incompatible with parallel function calls.** Set `parallel_tool_calls: false`
- Use Pydantic (Python) or Zod (JavaScript) for schema definitions
- Prevents schema violations but NOT value errors -- add examples for semantic correctness
- Use `anyOf` for union types; all fields must be required (use nullable instead of optional)

---

## 4. Long Context (1M tokens)

### Document Formatting

Use **XML format** for multiple documents (best performing with GPT-5.4 thinking):
```xml
<doc id='1' title='Annual Report'>Content here</doc>
<doc id='2' title='Competitor Analysis'>Content here</doc>
```

- JSON performs **poorly** for large document sets
- Pipe-delimited (`ID|TITLE|CONTENT`) is a solid alternative
- For maximum thoroughness, place key instructions at **both beginning and end** of the prompt

---

## 5. Hallucination -- The #1 Risk

GPT-5.4 has **~72% SimpleQA** (inferred from OpenAI's "33% fewer claim errors vs 5.2") -- significantly improved from 5.2's 58%, now roughly tied with Claude/Gemini. Still a ~28% error rate on factual questions.

**The improvement:** GPT-5.4 closed most of the hallucination gap. But it still rarely refuses to answer — it will **confidently fabricate** rather than say "I don't know." Web search remains the most impactful mitigation.

### With Thinking Enabled
- Medical cases (HealthBench): 1.6% error rate vs GPT-4o's 15.8% -- thinking helps enormously for *reasoning over* provided facts
- SimpleQA improved to ~72% -- both reasoning and factual recall improved in 5.4
- GPT-5.4 is OpenAI's most factual model to date, but ~28% error rate remains

### Mitigation Techniques

1. **Enable web search** for fact-sensitive queries -- drops error to ~5%. This is the single most impactful mitigation.
2. **Ask for citations inline** -- forces two errors to hallucinate (fact + fabricated citation)
3. **Provide grounding context** -- the closer source material is to the desired answer, the less it invents
4. **Give an "out":** `"Respond with 'not found' if the answer isn't present in the documents"`
5. **Use Structured Outputs** with mandatory fields for confidence/source
6. **Cross-validate** with Claude or Gemini for fact-sensitive claims (all three now ~72% SimpleQA)

---

## 6. Prompt Caching (Up to 90% Input Cost Reduction)

### How It Works
- **Automatic** -- no code changes required
- Minimum **1,024 tokens** to activate
- Matches in **128-token blocks** -- exact prefix match until first mismatch
- Reduces latency up to 80%, input costs up to 90%

### Maximize Cache Hits

**STATIC PREFIX (top) -> DYNAMIC CONTENT (bottom)**

1. Developer message, instructions, tool definitions, examples, schemas at **top**
2. User-specific, variable content at **bottom**
3. **Never put timestamps or request IDs early** -- invalidates cache
4. Images, tool definitions, schemas all cacheable but must be **identical**

### `prompt_cache_key` Parameter
- Improved one customer's hit rate from 60% to 87%
- Keep each prefix + key combo under ~15 requests/minute

### Cache Retention

| Type | Duration |
|------|----------|
| In-Memory | 5-10 min idle, max 1 hour |
| Extended (24h) | Up to 24 hours (GPT-5.4 supported) |

Monitor: check `usage.prompt_tokens_details.cached_tokens` in API response.

---

## 7. Tool / Function Calling

- Write **detailed, specific** function descriptions -- clear descriptions scored **6% higher** than verbose alternatives
- Flatten deeply nested parameter structures -- flat schemas reduce parsing errors
- Under ~100 tools and ~20 arguments per tool is in-distribution
- Add: `"Do NOT promise to call a function later. If required, emit it now."` -- GPT thinking mode may defer tool calls otherwise
- Use `strict: true` for reliable schema adherence
- With thinking enabled and Responses API, reasoning persistence significantly improves tool selection across multi-step workflows

---

## 8. Vision

GPT-5.4 with thinking is **best-in-class for document understanding**:
- DocVQA: 95% (best of any frontier model)
- ScreenSpot-Pro: 86.3% (best UI element detection)

| Detail Setting | Tokens | Use Case |
|---------------|:------:|----------|
| `low` | 85 fixed | Quick classification, cost optimization |
| `high` | 170 + 129/tile | OCR, fine detail, small text |
| `auto` (default) | Model decides | General use |

- Max input: 50 MB, 10 images per call
- For text in images: spell out tricky names letter by letter
- Video and audio input supported natively

---

## 9. Key Differences from Claude/Gemini

| Aspect | GPT-5.4 (thinking) | Claude 4.6 | Gemini 3.1 |
|--------|---------|-----------|-----------|
| Structured Outputs | Native, guaranteed | Tool_use workaround | Via function calling |
| Prompt caching | Automatic, 90% off | Manual markers | Automatic, 75% off |
| Thinking control | `reasoning.effort` (none/low/med/high/xhigh) | `output_config.effort` (low-max) | `thinkingLevel` (minimal-high) |
| CoT prompting | **Hurts** when thinking on | Helps (`<thinking>` tags) | Replace with thinkingLevel |
| Reasoning persistence | `previous_response_id` | Adaptive interleaved | Thought signatures |
| Hallucination | ~72% SimpleQA (tied) | Best tied (72%) | Best tied (72.1%) |
| Refusal rate | Almost never refuses (2%) | More selective | More selective |
| Math | **Best** (MATH 98%, AIME 100%) | 93% | 91.1% |
| Vision/OCR | **Best** (DocVQA 95%) | Good (93%) | Good |
| Medical reasoning | **Best** (1.6% HealthBench error) | Good | Good |
| Web search grounding | Available (SimpleQA -> 95.1%) | Not available | Google Search native |
