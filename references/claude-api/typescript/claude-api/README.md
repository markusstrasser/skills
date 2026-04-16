# Claude API — TypeScript

## Installation

```bash
npm install @anthropic-ai/sdk
```

## Client Initialization

```typescript
import Anthropic from "@anthropic-ai/sdk";

// Default (uses ANTHROPIC_API_KEY env var)
const client = new Anthropic();

// Explicit API key
const client = new Anthropic({ apiKey: "your-api-key" });
```

---

## Basic Message Request

```typescript
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  messages: [{ role: "user", content: "What is the capital of France?" }],
});
console.log(response.content[0].text);
```

---

## System Prompts

```typescript
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  system:
    "You are a helpful coding assistant. Always provide examples in Python.",
  messages: [{ role: "user", content: "How do I read a JSON file?" }],
});
```

---

## Vision (Images)

> **Opus 4.7 high-resolution support:** Images up to 2576px on the long edge (≈3.75 MP) are processed at full fidelity. Full-resolution images can use up to ~4,784 tokens each (up from ~1,600 on prior models) — re-budget `max_tokens` for image-heavy workloads, or downsample before sending if you don't need the extra detail. Pointing and bounding-box coordinates returned by 4.7 are 1:1 with actual image pixels; remove any scale-factor conversion from earlier versions.

### URL

```typescript
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  messages: [
    {
      role: "user",
      content: [
        {
          type: "image",
          source: { type: "url", url: "https://example.com/image.png" },
        },
        { type: "text", text: "Describe this image" },
      ],
    },
  ],
});
```

### Base64

```typescript
import fs from "fs";

const imageData = fs.readFileSync("image.png").toString("base64");

const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  messages: [
    {
      role: "user",
      content: [
        {
          type: "image",
          source: { type: "base64", media_type: "image/png", data: imageData },
        },
        { type: "text", text: "What's in this image?" },
      ],
    },
  ],
});
```

---

## Prompt Caching

### Automatic Caching (Recommended)

Use top-level `cache_control` to automatically cache the last cacheable block in the request:

```typescript
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  cache_control: { type: "ephemeral" }, // auto-caches the last cacheable block
  system: "You are an expert on this large document...",
  messages: [{ role: "user", content: "Summarize the key points" }],
});
```

### Manual Cache Control

For fine-grained control, add `cache_control` to specific content blocks:

```typescript
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  system: [
    {
      type: "text",
      text: "You are an expert on this large document...",
      cache_control: { type: "ephemeral" }, // default TTL is 5 minutes
    },
  ],
  messages: [{ role: "user", content: "Summarize the key points" }],
});

// With explicit TTL (time-to-live)
const response2 = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  system: [
    {
      type: "text",
      text: "You are an expert on this large document...",
      cache_control: { type: "ephemeral", ttl: "1h" }, // 1 hour TTL
    },
  ],
  messages: [{ role: "user", content: "Summarize the key points" }],
});
```

---

## Extended Thinking

Use `thinking: {type: "adaptive"}` on Opus 4.7 and Sonnet 4.6. Adaptive is OFF by default on Opus 4.7 — set it explicitly. `budget_tokens` returns a 400 error on Opus 4.7.

`thinking.display` defaults to `"omitted"` on Opus 4.7 — thinking blocks appear but their `thinking` field is empty. Set `display: "summarized"` to restore visible reasoning progress in UIs.

```typescript
// Opus 4.7: adaptive thinking with visible summary
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 64000, // headroom for xhigh effort
  thinking: { type: "adaptive", display: "summarized" },
  output_config: { effort: "xhigh" }, // low | medium | high | xhigh | max
  messages: [
    { role: "user", content: "Solve this math problem step by step..." },
  ],
});

for (const block of response.content) {
  if (block.type === "thinking") {
    console.log("Thinking:", block.thinking);
  } else if (block.type === "text") {
    console.log("Response:", block.text);
  }
}
```

---

## Error Handling

Use the SDK's typed exception classes — never check error messages with string matching:

```typescript
import Anthropic from "@anthropic-ai/sdk";

try {
  const response = await client.messages.create({...});
} catch (error) {
  if (error instanceof Anthropic.BadRequestError) {
    console.error("Bad request:", error.message);
  } else if (error instanceof Anthropic.AuthenticationError) {
    console.error("Invalid API key");
  } else if (error instanceof Anthropic.RateLimitError) {
    console.error("Rate limited - retry later");
  } else if (error instanceof Anthropic.APIError) {
    console.error(`API error ${error.status}:`, error.message);
  }
}
```

All classes extend `Anthropic.APIError` with a typed `status` field. Check from most specific to least specific. See [shared/error-codes.md](../../shared/error-codes.md) for the full error code reference.

---

## Multi-Turn Conversations

The API is stateless — send the full conversation history each time. Use `Anthropic.MessageParam[]` to type the messages array:

```typescript
const messages: Anthropic.MessageParam[] = [
  { role: "user", content: "My name is Alice." },
  { role: "assistant", content: "Hello Alice! Nice to meet you." },
  { role: "user", content: "What's my name?" },
];

const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  messages: messages,
});
```

**Rules:**

- Messages must alternate between `user` and `assistant`
- First message must be `user`
- Use SDK types (`Anthropic.MessageParam`, `Anthropic.Message`, `Anthropic.Tool`, etc.) for all API data structures — don't redefine equivalent interfaces

---

### Compaction (long conversations)

> **Beta.** When conversations approach the context window, compaction automatically summarizes earlier context server-side. The API returns a `compaction` block; you must pass it back on subsequent requests — append `response.content`, not just the text. Requires beta header `compact-2026-01-12`.

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const messages: Anthropic.Beta.BetaMessageParam[] = [];

async function chat(userMessage: string): Promise<string> {
  messages.push({ role: "user", content: userMessage });

  const response = await client.beta.messages.create({
    betas: ["compact-2026-01-12"],
    model: "claude-opus-4-7",
    max_tokens: 4096,
    messages,
    context_management: {
      edits: [{ type: "compact_20260112" }],
    },
  });

  // Append full content — compaction blocks must be preserved
  messages.push({ role: "assistant", content: response.content });

  const textBlock = response.content.find((block) => block.type === "text");
  return textBlock?.text ?? "";
}

// Compaction triggers automatically when context grows large
console.log(await chat("Help me build a Python web scraper"));
console.log(await chat("Add support for JavaScript-rendered pages"));
console.log(await chat("Now add rate limiting and error handling"));
```

---

## Stop Reasons

The `stop_reason` field in the response indicates why the model stopped generating:

| Value                           | Meaning                                                                   |
| ------------------------------- | ------------------------------------------------------------------------- |
| `end_turn`                      | Claude finished its response naturally                                    |
| `max_tokens`                    | Hit the `max_tokens` limit — increase it or use streaming                 |
| `stop_sequence`                 | Hit a custom stop sequence                                                |
| `tool_use`                      | Claude wants to call a tool — execute it and continue                     |
| `pause_turn`                    | Model paused and can be resumed (agentic flows)                           |
| `refusal`                       | Claude refused for safety reasons — output may not match schema           |
| `model_context_window_exceeded` | Generation stopped at the context window limit (distinct from max_tokens) |

---

## Cost Optimization Strategies

### 1. Use Prompt Caching for Repeated Context

```typescript
// Automatic caching (simplest — caches the last cacheable block)
const response = await client.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  cache_control: { type: "ephemeral" },
  system: largeDocumentText, // e.g., 50KB of context
  messages: [{ role: "user", content: "Summarize the key points" }],
});

// First request: full cost
// Subsequent requests: ~90% cheaper for cached portion
```

### 2. Use Token Counting Before Requests

```typescript
const countResponse = await client.messages.countTokens({
  model: "claude-opus-4-7",
  messages: messages,
  system: system,
});

const estimatedInputCost = countResponse.input_tokens * 0.000005; // $5/1M tokens
console.log(`Estimated input cost: $${estimatedInputCost.toFixed(4)}`);
```
