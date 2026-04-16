---
name: claude-api
description: "Build apps with the Claude API or Anthropic SDK. TRIGGER when: code imports `anthropic`/`@anthropic-ai/sdk`/`claude_agent_sdk`, or user asks to use Claude API, Anthropic SDKs, or Agent SDK. DO NOT TRIGGER when: code imports `openai`/other AI SDK, general programming, or ML/data-science tasks."
license: Complete terms in LICENSE.txt
effort: medium
---

# Building LLM-Powered Applications with Claude

This skill helps you build LLM-powered applications with Claude. Choose the right surface based on your needs, detect the project language, then read the relevant language-specific documentation.

## Defaults

Unless the user requests otherwise:

Use Claude Opus 4.7 via the exact model string `claude-opus-4-7`. Set `thinking: {type: "adaptive"}` explicitly when you want thinking — adaptive is off by default on Opus 4.7. Set `output_config: {effort: "xhigh"}` for coding and agentic tasks (the new recommended effort level on 4.7); use `high` for other intelligence-sensitive work. Default to streaming for any request that may involve long input, long output, or high `max_tokens` — it prevents hitting request timeouts. Use the SDK's `.get_final_message()` / `.finalMessage()` helper to get the complete response if you don't need to handle individual stream events.

---

## Language Detection

Before reading code examples, determine which language the user is working in:

1. **Look at project files** to infer the language:

   - `*.py`, `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` → **Python** — read from `python/`
   - `*.ts`, `*.tsx`, `package.json`, `tsconfig.json` → **TypeScript** — read from `typescript/`
   - `*.js`, `*.jsx` (no `.ts` files present) → **TypeScript** — JS uses the same SDK, read from `typescript/`
   - `*.java`, `pom.xml`, `build.gradle` → **Java** — read from `java/`
   - `*.kt`, `*.kts`, `build.gradle.kts` → **Java** — Kotlin uses the Java SDK, read from `java/`
   - `*.scala`, `build.sbt` → **Java** — Scala uses the Java SDK, read from `java/`
   - `*.go`, `go.mod` → **Go** — read from `go/`
   - `*.rb`, `Gemfile` → **Ruby** — read from `ruby/`
   - `*.cs`, `*.csproj` → **C#** — read from `csharp/`
   - `*.php`, `composer.json` → **PHP** — read from `php/`

2. **If multiple languages detected** (e.g., both Python and TypeScript files):

   - Check which language the user's current file or question relates to
   - If still ambiguous, ask: "I detected both Python and TypeScript files. Which language are you using for the Claude API integration?"

3. **If language can't be inferred** (empty project, no source files, or unsupported language):

   - Use AskUserQuestion with options: Python, TypeScript, Java, Go, Ruby, cURL/raw HTTP, C#, PHP
   - If AskUserQuestion is unavailable, default to Python examples and note: "Showing Python examples. Let me know if you need a different language."

4. **If unsupported language detected** (Rust, Swift, C++, Elixir, etc.):

   - Suggest cURL/raw HTTP examples from `curl/` and note that community SDKs may exist
   - Offer to show Python or TypeScript examples as reference implementations

5. **If user needs cURL/raw HTTP examples**, read from `curl/`.

### Language-Specific Feature Support

| Language   | Tool Runner | Agent SDK | Notes                                 |
| ---------- | ----------- | --------- | ------------------------------------- |
| Python     | Yes (beta)  | Yes       | Full support — `@beta_tool` decorator |
| TypeScript | Yes (beta)  | Yes       | Full support — `betaZodTool` + Zod    |
| Java       | Yes (beta)  | No        | Beta tool use with annotated classes  |
| Go         | Yes (beta)  | No        | `BetaToolRunner` in `toolrunner` pkg  |
| Ruby       | Yes (beta)  | No        | `BaseTool` + `tool_runner` in beta    |
| cURL       | N/A         | N/A       | Raw HTTP, no SDK features             |
| C#         | No          | No        | Official SDK                          |
| PHP        | No          | No        | Official SDK                          |

---

## Which Surface Should I Use?

> **Start simple.** Default to the simplest tier that meets your needs. Single API calls and workflows handle most use cases — only reach for agents when the task genuinely requires open-ended, model-driven exploration.

| Use Case                                        | Tier            | Recommended Surface       | Why                                     |
| ----------------------------------------------- | --------------- | ------------------------- | --------------------------------------- |
| Classification, summarization, extraction, Q&A  | Single LLM call | **Claude API**            | One request, one response               |
| Batch processing or embeddings                  | Single LLM call | **Claude API**            | Specialized endpoints                   |
| Multi-step pipelines with code-controlled logic | Workflow        | **Claude API + tool use** | You orchestrate the loop                |
| Custom agent with your own tools                | Agent           | **Claude API + tool use** | Maximum flexibility                     |
| AI agent with file/web/terminal access          | Agent           | **Agent SDK**             | Built-in tools, safety, and MCP support |
| Agentic coding assistant                        | Agent           | **Agent SDK**             | Designed for this use case              |
| Want built-in permissions and guardrails        | Agent           | **Agent SDK**             | Safety features included                |

> **Note:** The Agent SDK is for when you want built-in file/web/terminal tools, permissions, and MCP out of the box. If you want to build an agent with your own tools, Claude API is the right choice — use the tool runner for automatic loop handling, or the manual loop for fine-grained control (approval gates, custom logging, conditional execution).

### Decision Tree

```
What does your application need?

1. Single LLM call (classification, summarization, extraction, Q&A)
   └── Claude API — one request, one response

2. Does Claude need to read/write files, browse the web, or run shell commands
   as part of its work? (Not: does your app read a file and hand it to Claude —
   does Claude itself need to discover and access files/web/shell?)
   └── Yes → Agent SDK — built-in tools, don't reimplement them
       Examples: "scan a codebase for bugs", "summarize every file in a directory",
                 "find bugs using subagents", "research a topic via web search"

3. Workflow (multi-step, code-orchestrated, with your own tools)
   └── Claude API with tool use — you control the loop

4. Open-ended agent (model decides its own trajectory, your own tools)
   └── Claude API agentic loop (maximum flexibility)
```

### Should I Build an Agent?

Before choosing the agent tier, check all four criteria:

- **Complexity** — Is the task multi-step and hard to fully specify in advance? (e.g., "turn this design doc into a PR" vs. "extract the title from this PDF")
- **Value** — Does the outcome justify higher cost and latency?
- **Viability** — Is Claude capable at this task type?
- **Cost of error** — Can errors be caught and recovered from? (tests, review, rollback)

If the answer is "no" to any of these, stay at a simpler tier (single call or workflow).

---

## Architecture

Everything goes through `POST /v1/messages`. Tools and output constraints are features of this single endpoint — not separate APIs.

**User-defined tools** — You define tools (via decorators, Zod schemas, or raw JSON), and the SDK's tool runner handles calling the API, executing your functions, and looping until Claude is done. For full control, you can write the loop manually.

**Server-side tools** — Anthropic-hosted tools that run on Anthropic's infrastructure. Code execution is fully server-side (declare it in `tools`, Claude runs code automatically). Computer use can be server-hosted or self-hosted.

**Structured outputs** — Constrains the Messages API response format (`output_config.format`) and/or tool parameter validation (`strict: true`). The recommended approach is `client.messages.parse()` which validates responses against your schema automatically. Use `output_config: {format: {...}}` on `messages.create()`.

**Supporting endpoints** — Batches (`POST /v1/messages/batches`), Files (`POST /v1/files`), and Token Counting feed into or support Messages API requests.

---

## Current Models (cached: 2026-04-16)

| Model             | Model ID            | Context        | Input $/1M | Output $/1M |
| ----------------- | ------------------- | -------------- | ---------- | ----------- |
| Claude Opus 4.7   | `claude-opus-4-7`   | 1M             | $5.00      | $25.00      |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 200K (1M beta) | $3.00      | $15.00      |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K           | $1.00      | $5.00       |

**ALWAYS use `claude-opus-4-7` unless the user explicitly names a different model.** Never downgrade for cost — that's the user's decision, not yours.

**Use only the exact model ID strings from the table above.** Do not append date suffixes. If the user requests a model not in the table, read `shared/models.md` or WebFetch the Anthropic Models Overview — do not construct an ID yourself.

A note: if any of the model strings above look unfamiliar to you, that's to be expected — that just means they were released after your training data cutoff. Rest assured they are real models; we wouldn't mess with you like that.

---

## Thinking & Effort (Quick Reference)

**Adaptive thinking is off by default on Opus 4.7.** Set it explicitly: `thinking: {type: "adaptive"}`. Claude then decides when and how much to think. Adaptive thinking also automatically enables interleaved thinking (no beta header needed). `budget_tokens` returns a 400 error on Opus 4.7 — do not use it; do not fall back to an older model just because the user asks for a "thinking budget."

**Effort levels (GA, no beta header):** `output_config: {effort: "low"|"medium"|"high"|"xhigh"|"max"}`. Opus 4.7 added `xhigh` between `high` and `max`.

- `xhigh` — **start here for coding and agentic use cases.**
- `high` — minimum for most intelligence-sensitive work.
- `medium` — cost-sensitive tasks where intelligence tradeoff is acceptable.
- `low` — short, scoped, latency-sensitive tasks only. Opus 4.7 respects low strictly — it will under-think on complex problems at this level. If you see shallow reasoning, raise effort; don't prompt around it.
- `max` — deepest reasoning; can overthink on simpler tasks. Test before committing.

With `xhigh` or `max` effort, start with `max_tokens: 64000` or higher — 4.7 uses more output tokens at these levels.

**Thinking display:** `thinking.display` defaults to `"omitted"` on Opus 4.7 — thinking blocks appear in the stream but their `thinking` field is empty. Set `thinking: {type: "adaptive", display: "summarized"}` to restore visible reasoning progress. Important for UIs that show thinking to users — otherwise the UI appears frozen until first output token.

**Sampling parameters are removed.** `temperature`, `top_p`, and `top_k` return 400 on Opus 4.7. Omit them from request payloads. Use prompting to guide behavior.

**Task budgets (beta):** For agentic loops, set an advisory token cap the model uses to pace itself:
```
output_config = {"effort": "high", "task_budget": {"type": "tokens", "total": 128000}}
```
Beta header: `task-budgets-2026-03-13`. Minimum 20,000 tokens. Don't set for open-ended tasks where quality matters more than speed. `task_budget` is advisory (the model sees it and paces itself); `max_tokens` is a hard per-request ceiling.

**Assistant-message prefills return a 400 error on Opus 4.7.** Use structured outputs (`output_config.format`), system prompt instructions, or continuation-as-user-turn patterns instead.

---

## Compaction (Quick Reference)

**Beta.** For long-running conversations that may exceed the context window, enable server-side compaction. The API automatically summarizes earlier context when it approaches the trigger threshold. Requires beta header `compact-2026-01-12`.

**Critical:** Append `response.content` (not just the text) back to your messages on every turn. Compaction blocks in the response must be preserved — the API uses them to replace the compacted history on the next request. Extracting only the text string and appending that will silently lose the compaction state.

See `{lang}/claude-api/README.md` (Compaction section) for code examples. Full docs via WebFetch in `shared/live-sources.md`.

---

## Reading Guide

After detecting the language, read the relevant files based on what the user needs:

### Quick Task Reference

**Single text classification/summarization/extraction/Q&A:**
→ Read only `{lang}/claude-api/README.md`

**Chat UI or real-time response display:**
→ Read `{lang}/claude-api/README.md` + `{lang}/claude-api/streaming.md`

**Long-running conversations (may exceed context window):**
→ Read `{lang}/claude-api/README.md` — see Compaction section

**Function calling / tool use / agents:**
→ Read `{lang}/claude-api/README.md` + `shared/tool-use-concepts.md` + `{lang}/claude-api/tool-use.md`

**Batch processing (non-latency-sensitive):**
→ Read `{lang}/claude-api/README.md` + `{lang}/claude-api/batches.md`

**File uploads across multiple requests:**
→ Read `{lang}/claude-api/README.md` + `{lang}/claude-api/files-api.md`

**Agent with built-in tools (file/web/terminal):**
→ Read `{lang}/agent-sdk/README.md` + `{lang}/agent-sdk/patterns.md`

### Claude API (Full File Reference)

Read the **language-specific Claude API folder** (`{language}/claude-api/`):

1. **`{language}/claude-api/README.md`** — **Read this first.** Installation, quick start, common patterns, error handling.
2. **`shared/tool-use-concepts.md`** — Read when the user needs function calling, code execution, memory, or structured outputs. Covers conceptual foundations.
3. **`{language}/claude-api/tool-use.md`** — Read for language-specific tool use code examples (tool runner, manual loop, code execution, memory, structured outputs).
4. **`{language}/claude-api/streaming.md`** — Read when building chat UIs or interfaces that display responses incrementally.
5. **`{language}/claude-api/batches.md`** — Read when processing many requests offline (not latency-sensitive). Runs asynchronously at 50% cost.
6. **`{language}/claude-api/files-api.md`** — Read when sending the same file across multiple requests without re-uploading.
7. **`shared/error-codes.md`** — Read when debugging HTTP errors or implementing error handling.
8. **`shared/live-sources.md`** — WebFetch URLs for fetching the latest official documentation.

> **Note:** For Java, Go, Ruby, C#, PHP, and cURL — these have a single file each covering all basics. Read that file plus `shared/tool-use-concepts.md` and `shared/error-codes.md` as needed.

### Agent SDK

Read the **language-specific Agent SDK folder** (`{language}/agent-sdk/`). Agent SDK is available for **Python and TypeScript only**.

1. **`{language}/agent-sdk/README.md`** — Installation, quick start, built-in tools, permissions, MCP, hooks.
2. **`{language}/agent-sdk/patterns.md`** — Custom tools, hooks, subagents, MCP integration, session resumption.
3. **`shared/live-sources.md`** — WebFetch URLs for current Agent SDK docs.

---

## When to Use WebFetch

Use WebFetch to get the latest documentation when:

- User asks for "latest" or "current" information
- Cached data seems incorrect
- User asks about features not covered here

Live documentation URLs are in `shared/live-sources.md`.

## Common Pitfalls

- Don't truncate inputs when passing files or content to the API. If the content is too long to fit in the context window, notify the user and discuss options (chunking, summarization, etc.) rather than silently truncating.
- **Thinking:** Use `thinking: {type: "adaptive"}` on Opus 4.7 and Sonnet 4.6. `budget_tokens` returns a 400 error on Opus 4.7.
- **Opus 4.7 prefill removed:** Assistant message prefills return a 400 error. Use structured outputs (`output_config.format`), system prompt instructions, or continuation-as-user-turn patterns instead.
- **Opus 4.7 sampling parameters removed:** `temperature`, `top_p`, `top_k` return 400 on Opus 4.7. Omit them. Use prompting to guide behavior.
- **Opus 4.7 thinking.display default is "omitted":** Thinking field is empty unless you set `display: "summarized"`. UIs showing thinking progress need the explicit opt-in or they appear frozen.
- **Opus 4.7 tokenizer shift:** The same text maps to 1.0–1.35× more tokens than Opus 4.6. Re-baseline `max_tokens`, compaction triggers, and any client-side token estimators. Use `/v1/messages/count_tokens` on 4.7 specifically.
- **Opus 4.7 is more literal:** It follows instructions precisely and won't silently generalize. Remove scaffolding like "summarize after every 3 tool calls" — 4.7 gives higher-quality built-in progress updates. It also spawns fewer subagents and uses tools less often by default; raise effort to `xhigh` if you need more tool usage.
- **Opus 4.7 effort calibration is strict:** `low` and `medium` strictly scope work to what was asked — good for latency and cost, but can under-think on complex problems. If you see shallow reasoning, raise effort rather than prompting around it.
- **128K output tokens:** Opus 4.7 supports up to 128K `max_tokens`, but SDKs require streaming for large `max_tokens` to avoid HTTP timeouts. Use `.stream()` with `.get_final_message()` / `.finalMessage()`. At `xhigh` or `max`, start with `max_tokens: 64000` or higher.
- **Tool call JSON parsing:** Claude may produce different JSON string escaping in tool call `input` fields (Unicode or forward-slash escaping). Always parse tool inputs with `json.loads()` / `JSON.parse()` — never raw string matching on the serialized input. Opus 4.5+ preserves trailing newlines in tool string parameters.
- **Structured outputs:** Use `output_config: {format: {...}}` on `messages.create()`. The `output_format` parameter is deprecated.
- **High-resolution images (Opus 4.7):** Full-resolution images can use up to ~3× more image tokens than on prior models (up to 4784 per image, up from ~1600). Re-budget `max_tokens` for image-heavy workloads or downsample before sending. Pointing and bounding-box coordinates from the model are 1:1 with actual image pixels — remove any scale-factor conversion from prior versions.
- **New stop reasons:** Handle `refusal` (safety refusal — output may not match your schema) and `model_context_window_exceeded` (hit context window, not `max_tokens`) in addition to standard values.
- **Don't reimplement SDK functionality:** The SDK provides high-level helpers — use them instead of building from scratch. Specifically: use `stream.finalMessage()` instead of wrapping `.on()` events in `new Promise()`; use typed exception classes (`Anthropic.RateLimitError`, etc.) instead of string-matching error messages; use SDK types (`Anthropic.MessageParam`, `Anthropic.Tool`, `Anthropic.Message`, etc.) instead of redefining equivalent interfaces.
- **Don't define custom types for SDK data structures:** The SDK exports types for all API objects. Use `Anthropic.MessageParam` for messages, `Anthropic.Tool` for tool definitions, `Anthropic.ToolUseBlock` / `Anthropic.ToolResultBlockParam` for tool results, `Anthropic.Message` for responses. Defining your own `interface ChatMessage { role: string; content: unknown }` duplicates what the SDK already provides and loses type safety.
- **Report and document output:** For tasks that produce reports, documents, or visualizations, the code execution sandbox has `python-docx`, `python-pptx`, `matplotlib`, `pillow`, and `pypdf` pre-installed. Claude can generate formatted files (DOCX, PDF, charts) and return them via the Files API — consider this for "report" or "document" type requests instead of plain stdout text.
