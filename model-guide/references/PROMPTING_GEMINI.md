# Gemini 3.1 Pro Prompting Guide

Specific to Gemini 3.1 Pro (and Gemini 3 Flash where noted). Updated 2026-03-20.

**Sources:** Google AI official docs (ai.google.dev, cloud.google.com/vertex-ai).

---

## 1. Temperature -- DO NOT LOWER IT

The single biggest behavioral difference from every other frontier model:

> **Keep temperature at the default value of 1.0.**

Lowering temperature on Gemini causes **looping, degraded performance, and broken reasoning** -- especially on math and complex tasks. This is the opposite of Claude/GPT convention.

If you need deterministic output, use structured output with response schemas instead.

---

## 2. Query and Constraint Placement

Two critical rules that differ from other models:

1. **Put your query at the END** of the prompt, after all context. Use transition phrases: `"Based on the information above..."`
2. **Put critical constraints at the END** too -- Gemini 3 may drop early constraints in complex prompts

This is the opposite of Claude (where instructions can go at top) and matters more for Gemini than any other model.

---

## 3. Output Token Pitfall

**The default `maxOutputTokens` is only 8,192.** You must explicitly raise it:

```python
generation_config = {"max_output_tokens": 65536}
```

Without this, responses **silently truncate** at ~8K tokens. Check `finishReason`:
- `STOP` = model decided it was done
- `MAX_TOKENS` = hit the limit (increase maxOutputTokens)
- `SAFETY` = content filtered

**Thinking tokens consume your output budget.** At `thinkingLevel: "high"`, 18,000-30,000 tokens go to internal reasoning, leaving only ~35,000-47,000 for visible output. Use `thinkingLevel: "low"` if you need maximum visible output.

---

## 4. Thinking Mode

### Default Behavior (Confirmed from API)

**Gemini 3.1 Pro defaults to `thinkingLevel: high` when not specified.** Thinking **cannot be disabled** on Pro -- the lowest available is `low`. The `minimal` level is Flash-only.

### `thinkingLevel` (Gemini 3 series)

| Level | Gemini 3.1 Pro | Gemini 3 Flash | Use Case |
|-------|:-:|:-:|----------|
| `minimal` | Not supported | Supported | Approximates no thinking (Flash only) |
| `low` | **Supported** | Supported | Minimize latency/cost for straightforward tasks |
| `medium` | Not supported | Supported | Balanced reasoning (Flash only) |
| `high` | **Default** | **Default** | Complex math, multi-step coding, advanced reasoning |

### API Parameter

```python
# Google SDK
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="low")
)

# Via llmx (maps --reasoning-effort to thinkingConfig internally)
llmx -m gemini-3.1-pro-preview --reasoning-effort low "simple query"
llmx -m gemini-3.1-pro-preview "complex query"  # Defaults to high server-side
```

### Best Practices
- **Replace explicit chain-of-thought prompting** with `thinkingLevel: "high"` -- model handles decomposition internally
- For lengthy outputs, use `thinkingLevel: "low"` to reserve tokens for visible output
- Include verification: `"Verify your sources, review your reasoning, identify errors, check your final answer"`
- Access thought summaries with `includeThoughts: true`
- **Thought signatures** (Gemini 3): encrypted tokens that must be passed back in multi-turn conversations to maintain reasoning context
- **Do NOT use `thinkingBudget`** (Gemini 2.5 parameter) with Gemini 3.x -- use `thinkingLevel` instead. Mixing them returns a 400 error.

---

## 5. System Instructions

Gemini 3 favors structured system instructions. XML tags work well:

```xml
<role>
You are a specialized assistant for [Domain].
</role>

<instructions>
1. Plan: Break tasks into sub-tasks
2. Execute: Carry out plans, reflecting before tool calls
3. Validate: Review output against requirements
</instructions>

<constraints>
- Verbosity: [Low/Medium/High]
- Tone: [Formal/Casual/Technical]
</constraints>
```

### Gemini-Specific Tips
- Add: `"Remember it is 2026 this year"` -- Gemini benefits from explicit date anchoring
- Add: `"Your knowledge cutoff date is [date]"` to prevent hallucination
- For grounded responses: `"The provided context is the only source of truth for this session"`
- **Gemini 3 is less verbose by default** -- explicitly request chattier tone if needed

---

## 6. Grounding with Google Search

Unique Gemini capability -- no equivalent in Claude, GPT, or Kimi APIs.

```python
grounding_tool = types.Tool(google_search=types.GoogleSearch())
config = types.GenerateContentConfig(tools=[grounding_tool])
```

- Model auto-generates and executes search queries
- Returns `groundingMetadata` with `webSearchQueries`, `groundingChunks` (sources), `groundingSupports` (inline citations)
- Reduces hallucinations by ~40%
- Use temperature 1.0 with grounding
- Gemini 3: billed per search query executed
- **Cannot combine built-in tools (Google Search, Code Execution) with custom function calling in the same request**

---

## 7. Function Calling / Tool Use

### Tool Configuration Modes

| Mode | Behavior |
|------|----------|
| `AUTO` (default) | Model decides between text or function calls |
| `ANY` | Always generates function calls; restrict with `allowed_function_names` |
| `NONE` | Disables function calling |
| `VALIDATED` (Preview) | Ensures schema adherence |

### Best Practices
- Description quality is paramount -- model relies on descriptions to choose functions
- Use `enum` for fixed value sets (dramatically improves accuracy)
- **10-20 tools maximum** -- more causes confusion
- Parallel and chained calling both supported
- Pass thought signatures back in multi-turn function calling
- MCP support built into Python and JavaScript SDKs

---

## 8. Long Context (1M Tokens Native)

All three frontier families now support 1M natively (Claude GA March 13, GPT-5.4, Gemini).

### Structure
- **Query at the END** after all context (critical for Gemini)
- Use transition: `"Based on the information above..."`
- **Favor direct inclusion over RAG** -- Gemini's in-context learning is powerful with complete materials
- Place instructions at both **beginning and end** (boundary effect)

### Performance
- ~99% accuracy on single needle-in-haystack retrieval
- Accuracy degrades when searching for **multiple** pieces simultaneously
- Use structured formats (JSON, XML, Markdown headers) to organize large contexts
- Explicitly name the document or section when asking about specific content

---

## 9. Context Caching (75% Discount)

### Two Types

| Type | Setup | Savings |
|------|-------|---------|
| **Implicit** (automatic) | Enabled by default | Automatic, no guarantees |
| **Explicit** (manual) | Developer creates and references caches | Guaranteed reduced rate |

### Minimum Tokens
- Gemini 3.1 Pro: 4,096 tokens
- Gemini 3 Flash: 1,024 tokens

### Structure for Maximum Savings
- Cached content works as a **prompt prefix** -- stable content at front
- Variable content (user query) goes after cached prefix
- Default TTL: 1 hour; customizable
- Cacheable: system instructions, video/PDF/text files, tool definitions

---

## 9b. Inference Service Tiers

| Tier | Discount | Latency | When to use |
|------|----------|---------|-------------|
| Standard | 0% | seconds | Interactive, default |
| Flex | 50% | 1-15 min | Background/cron dispatch, non-interactive chains |
| Priority | +75-100% | sub-second | User-facing production apps |
| Batch (async) | 50% | up to 24h | Bulk eval/embedding jobs |

Pass `service_tier` parameter in generation calls. Flex is synchronous (no async rewrite) and "sheddable" (preempted under load). For scheduled agent dispatch (reviews, analysis), Flex is the default choice when API is needed.

---

## 10. Structured Output / JSON

```python
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=your_schema
)
```

### Key Rules
- Use clear `description` fields for every property -- guides model output
- Use `enum` for any field with fixed values
- **Syntactic correctness is guaranteed; semantic correctness is NOT** -- validate in app code
- Can combine with Google Search, URL Context, Code Execution, Function Calling

---

## 11. Multimodal

### Media Ordering
- Place media (images, video, audio) **before** text instructions
- Reference specific modalities explicitly

### Capacity
- Up to 8.4 hours of audio per prompt (~1M tokens)
- Up to 3,600 images per prompt (~1M tokens)

### Media Resolution Control
`media_resolution` parameter: `low`, `medium`, `high`, `ultra_high`
- Use `high` for document parsing
- Ask model to describe the image first, then perform analysis (pre-analysis step)

---

## 12. Few-Shot Examples

Official Gemini guidance emphasizes few-shot more strongly than other models:
- **Always include few-shot examples** for complex tasks
- 3-5 diverse, relevant examples
- Show both input and expected output format
- Include edge cases in examples

---

## 13. Key Differences from Claude/GPT/Kimi

| Aspect | Gemini 3.1 | Claude 4.6 | GPT-5.4 | Kimi K2.5 |
|--------|-----------|-----------|---------|-----------|
| Temperature | Keep at 1.0 (lowering degrades) | Lower OK | Lower OK | 1.0 thinking, 0.6 instant |
| Query placement | END (critical) | Bottom (30% better) | End preferred | Flexible |
| Output default | 8,192 (must raise!) | Higher | Higher | 4,096 (must raise) |
| Grounding | Native Google Search | Not available | Web search available | Not available |
| Context | **1M native** | 1M (GA March 13) | 1M | 256K |
| Instruction following | Weakest (89.2%) | Strong (94%) | Best (95%) | Strong (94%) |
| Expert preference | Lower (1317) | Highest (1606) | Middle | -- |
| Constraint placement | END of prompt | Flexible | Both beginning and end | Flexible |
| Few-shot importance | Strongly recommended | Helpful | Helpful | Helpful |
