# Kimi K2.5 Prompting Guide

Specific to Kimi K2.5 (Moonshot AI). Updated 2026-02-27.

**Sources:** Moonshot AI official docs (platform.moonshot.ai), Hugging Face model card, community benchmarks.

---

## 1. Two Modes: Thinking vs. Instant

Kimi K2.5 has two distinct operating modes with different optimal settings:

### Thinking Mode (default -- for hard problems)

```python
response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=messages,
    temperature=1.0,
    top_p=0.95,
    max_tokens=4096
)
# Reasoning trace: response.choices[0].message.reasoning_content
# Final answer: response.choices[0].message.content
```

- Budget 2-4x the tokens of a standard response for reasoning
- AIME/MATH benchmarks used a 96K token completion budget
- Best for: math, science reasoning, complex analysis

### Instant Mode (for speed/cost)

```python
response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=messages,
    temperature=0.6,
    top_p=0.95,
    max_tokens=4096,
    extra_body={'thinking': {'type': 'disabled'}}
)
```

- Best for: simple queries, code generation, high-volume work

**Important:** Non-thinking mode is often **better for code** than thinking mode. Moonshot's own guidance says this. Test both for your use case.

---

## 2. API Compatibility

Kimi K2.5 uses the **OpenAI-compatible** `chat.completions` format:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-key",
    base_url="https://api.moonshot.ai/v1"  # Official
    # Or: "https://openrouter.ai/api/v1" (OpenRouter)
    # Or: "https://api.together.xyz/v1" (Together AI)
)
```

Model ID: `kimi-k2.5` (official) or `moonshotai/kimi-k2.5` (third-party providers)

---

## 3. Output Token Defaults

Like Gemini, Kimi has a **low default max output**:
- General chat: 4,096 tokens
- Vision tasks: 8,192-64K tokens
- Thinking mode: up to 96K tokens (completion budget)

**Always set `max_tokens` explicitly** for non-trivial tasks. The 256K context window is shared between input and output.

---

## 4. Verbosity Problem

Kimi K2.5 generates **excessively long responses**. This inflates real-world costs 2-4x beyond what token pricing suggests.

**Mitigation:**
- Add explicit length constraints: `"Answer in 3 sentences"` or `"Respond concisely"`
- Use structured output (JSON schema) to constrain response format
- For bulk work, factor in 2-4x cost multiplier when budgeting

---

## 5. Hallucination -- The Biggest Risk

**SimpleQA: 36.9%** -- Kimi hallucinates 63% of factual questions. This is the worst of any current frontier model.

### Mitigation
1. **Never use for unsourced factual claims** -- always ground with tool calls or documents
2. **Pair with tool augmentation** -- Kimi gains +20.1pp with tools (more than any competitor)
3. **Cross-validate** with Claude or Gemini (both at 72% SimpleQA) for fact-sensitive work
4. **Structured output** with mandatory source/confidence fields

Kimi is excellent for **reasoning over provided data** but dangerous for **generating facts from memory**.

---

## 6. Tool / Function Calling

OpenAI-compatible `tools` array format:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
}]
```

- Strict function calling supported
- JSON schema response format supported (`response_format` with `json_schema` type)
- Kimi gains the most from tool augmentation of any frontier model (+20.1pp)
- Include system prompts emphasizing `"deep and proactive tool use"` for agentic tasks

---

## 7. Agent Swarm (Unique Capability)

No other frontier model has this natively:

- Up to **100 parallel sub-agents** per session
- Up to **1,500 tool calls** per session
- Trained via Parallel-Agent Reinforcement Learning (PARL)
- 4.5x faster than single-agent on long-horizon tasks
- 80% runtime reduction on complex tasks

Available via the Moonshot platform (not raw API). Best for:
- Large-scale data gathering
- Multi-source research
- Long-horizon tasks with many independent subtasks

---

## 8. Vision & Video

Kimi K2.5 was pre-trained from scratch on 15T mixed visual+text tokens (not bolted on post-hoc).

### Images
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        # or {"url": "https://example.com/image.png"}
        {"type": "text", "text": "Describe this image"}
    ]
}]
```

### Video (Experimental)
- Only available via official API (not third-party providers)
- Use `video_url` content type with base64 encoding
- VideoMMMU: 86.6% -- best-in-class video understanding

### Tips
- Set `max_tokens=64000` for vision tasks
- Average over multiple runs for consistency
- MMMU-Pro 78.5%, OCRBench 92.3%

---

## 9. Coding

- HumanEval: 99% (best of any frontier model)
- LiveCodeBench: 85% (best of any frontier model)
- SWE-bench: 76.8% (trails Claude/GPT/Gemini by 3-4pp)

**Key insight:** Instant mode (thinking disabled) often produces **better code** than thinking mode. Test both.

For complex multi-file coding tasks, SWE-bench gap matters -- prefer Claude Opus/Sonnet for real-world codebase work.

---

## 10. Architecture Notes

Understanding the architecture helps with prompting:

- **MoE (Mixture of Experts):** 1T total params, only 32B activated per token
- **384 experts, 8 selected per token** -- fast inference despite massive parameter count
- **MoonViT vision encoder:** 400M params, native multimodal
- **Modified MIT License:** Free for commercial use; attribution required above 100M MAU or $20M/month revenue

---

## 11. Gotchas

| Gotcha | Detail |
|--------|--------|
| Thinking API parameter differs by deployment | Official API: `extra_body={'thinking': {'type': 'disabled'}}`. Self-hosted vLLM: `extra_body={'chat_template_kwargs': {"thinking": False}}`. Confusing them silently fails. |
| Verbose outputs inflate costs | Budget 2-4x the per-token price for real-world usage |
| Self-hosting is impractical | 1T MoE requires all 384 expert weights in memory. Consumer hardware runs ~100x slower than H100 clusters |
| Video is experimental | Only via official API, not third-party providers |
| Attribution required | Must display "Kimi K2.5" in UI built on the model |
| SimpleQA is 37% | Worst factual accuracy of any frontier model. Never trust unsourced claims |
| Limited production track record | Minimal real-world deployments, smaller developer ecosystem vs Claude/GPT/Gemini |

---

## 12. Key Differences from Claude/GPT/Gemini

| Aspect | Kimi K2.5 | Claude 4.6 | GPT-5.4 | Gemini 3.1 |
|--------|-----------|-----------|---------|-----------|
| Price (in/out MTok) | **$0.60/$2.50** | $5/$25 | $2.50/$15 | $2/$12 |
| Thinking control | On/off toggle | Adaptive effort | Integrated | thinkingLevel |
| Code (thinking off) | Often better | N/A | N/A | N/A |
| Factual accuracy | Worst (37%) | Best tied (72%) | ~72% (tied) | Best tied (72%) |
| Tool augmentation gain | **+20.1pp** (biggest) | Moderate | Moderate | Moderate |
| Agent swarm | **Native (100 agents)** | Not native | Not native | Not native |
| Video | **Native** | Not supported | Supported | Supported |
| API format | OpenAI-compatible | Anthropic SDK | OpenAI native | Google SDK |
| Open weights | **Yes** (modified MIT) | No | No | No |
| Writing quality | Weakest | Best | Good | Good |
