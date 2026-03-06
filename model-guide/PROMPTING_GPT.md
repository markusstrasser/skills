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
| `xhigh` | Maximum compute — hardest problems, Pro-lite behavior | 600s (10 min) |
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

## 9. Key Differences from Claude/Gemini/Kimi

| Aspect | GPT-5.4 (thinking) | Claude 4.6 | Gemini 3.1 | Kimi K2.5 |
|--------|---------|-----------|-----------|-----------|
| Structured Outputs | Native, guaranteed | Tool_use workaround | Via function calling | OpenAI-compatible |
| Prompt caching | Automatic, 90% off | Manual markers | Automatic, 75% off | None |
| Thinking control | `reasoning.effort` (none/low/med/high/xhigh) | `output_config.effort` (low-max) | `thinkingLevel` (minimal-high) | On/off toggle |
| CoT prompting | **Hurts** when thinking on | Helps (`<thinking>` tags) | Replace with thinkingLevel | Use thinking mode |
| Reasoning persistence | `previous_response_id` | Adaptive interleaved | Thought signatures | Not available |
| Hallucination | ~72% SimpleQA (tied) | Best tied (72%) | Best tied (72.1%) | Worst (37%) |
| Refusal rate | Almost never refuses (2%) | More selective | More selective | Moderate |
| Math | **Best** (MATH 98%, AIME 100%) | 93% | 91.1% | 98%, AIME 96% |
| Vision/OCR | **Best** (DocVQA 95%) | Good (93%) | Good | Good (MMMU-Pro 78.5%) |
| Medical reasoning | **Best** (1.6% HealthBench error) | Good | Good | -- |
| Web search grounding | Available (SimpleQA -> 95.1%) | Not available | Google Search native | Not available |
