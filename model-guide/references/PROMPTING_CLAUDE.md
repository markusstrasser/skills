# Claude Prompting Guide

Specific to Claude Opus 4.7 and Sonnet 4.6. Updated 2026-04-16.

**Sources:** Anthropic official docs (platform.claude.com/docs), Claude Code system prompt analysis.

---

## 1. XML Tags -- Claude's Signature Technique

Claude was specifically trained to parse and respect XML structure. This is the single most important Claude-specific technique.

```xml
<documents>
  <document index="1">
    <source>filename.pdf</source>
    <document_content>{{CONTENT}}</document_content>
  </document>
</documents>

<instructions>
Your task is to analyze the documents above.
</instructions>
```

**Patterns that work:**
- `<instructions>`, `<context>`, `<input>`, `<example>`, `<documents>` for content types
- `<thinking>` and `<answer>` to separate reasoning from output
- `<example>` / `<examples>` to distinguish examples from instructions
- Nested tags for hierarchy: `<documents>` > `<document index="1">` > `<source>` + `<document_content>`
- Steering formatting: `"Write in <smoothly_flowing_prose> tags"` works better than `"Don't use markdown"`

---

## 2. Thinking & Reasoning Modes

### Adaptive Thinking

Adaptive thinking is **off by default** on Opus 4.7 — set it explicitly. `budget_tokens` returns a 400 error on Opus 4.7. `thinking.display` defaults to `"omitted"`; add `"display": "summarized"` to restore visible reasoning in UIs.

```python
client.messages.create(
    model="claude-opus-4-7",
    max_tokens=64000,
    thinking={"type": "adaptive", "display": "summarized"},
    output_config={"effort": "xhigh"},  # max, xhigh, high, medium, low
    messages=[...]
)
```

| Effort | Behavior |
|--------|----------|
| `max` | Deepest reasoning. Can overthink simple tasks. Test before committing. |
| `xhigh` | **Recommended for coding and agentic work** (new level on 4.7). |
| `high` | Minimum for intelligence-sensitive tasks. |
| `medium` | Cost-sensitive; acceptable intelligence tradeoff. |
| `low` | Strictly scopes to what was asked. May under-think complex problems — raise effort rather than prompt around it. |

Adaptive mode automatically enables **interleaved thinking** (thinking between tool calls). No beta header needed. Works the same on Sonnet 4.6.

### Prompt-Level Chain-of-Thought (when thinking is off)

- Use `<thinking>` and `<answer>` tags
- Say "think thoroughly" rather than prescribing steps -- Claude's reasoning often exceeds prescriptions
- Include `<thinking>` tags in few-shot examples -- Claude generalizes the pattern
- Add self-check: `"Before finishing, verify your answer against [criteria]"`

---

## 3. System Prompts & Role Setting

- Set roles in the **system prompt**, not user message
- Opus 4.7 follows instructions literally and is highly responsive to system prompts. Keep instructions precise and drop forceful scaffolding:
  - Bad: `"CRITICAL: You MUST use this tool when..."`
  - Good: `"Use this tool when..."`
- **Explain the why** behind constraints:
  - Bad: `"Never use ellipses"`
  - Good: `"Your response will be read aloud by TTS, so never use ellipses since the engine can't pronounce them"`
  - Claude generalizes from explanations better than from bare rules

---

## 4. Long Context Best Practices

1M context native on Opus 4.7 at standard pricing. 1M on Sonnet 4.6 via `context-1m-2025-08-07` beta header. MRCR v2: 78.3% at 1M tokens (4.6 baseline; 4.7 improves per announcement).

**Critical rule:** Put **long documents at the TOP**, query/instructions at the **BOTTOM**. Measured 30% improvement.

```xml
<documents>
  <!-- Long content here -->
</documents>

<!-- Query and instructions at the end -->
Based on the documents above, analyze...
```

**Ground responses in quotes:** For long docs, ask Claude to extract relevant quotes first:

```
Find relevant quotes from the documents. Place these in <quotes> tags.
Then, based on these quotes, provide your analysis in <info> tags.
```

---

## 5. Prefilling — not supported

Prefilled responses on the last assistant turn are not supported on Opus 4.6+ (return a 400 error on Opus 4.7).

**Use instead:**
- Format control: system prompt instructions or structured output via `output_config.format`
- Eliminating preambles: `"Respond directly without preamble. Do not start with 'Here is...', 'Based on...'"`
- Continuations: move to user message: `"Your previous response ended with [text]. Continue from where you left off."`

---

## 6. Tool Use

### Description Quality
Write **detailed, specific descriptions** for each tool and parameter. Short descriptions reduce accuracy. Include examples in parameter descriptions.

### Model-Tier Differences
- **Opus** asks for missing required parameters
- **Sonnet/Haiku** may **guess** values -- add this for Sonnet/Haiku:
  ```
  Before calling a tool, think about whether the user has provided enough
  information for all required parameters. If missing, ask instead of guessing.
  ```

### Parallel Tool Calls
Claude excels at parallel execution. Boost to ~100% with:
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between
the calls, make all independent calls in parallel.
</use_parallel_tool_calls>
```

### Opus 4.7: Fewer Tools by Default
Opus 4.7 uses tools less often than prior Opus versions and relies more on reasoning. To increase tool usage, raise effort to `xhigh` — don't prompt-engineer around the default.

### Action vs. Suggestion
Claude interprets "Can you suggest changes?" as a request for suggestions, not action.
- For action: use imperative language: `"Change this function to improve performance"`
- For proactive tool use: `"By default, implement changes rather than only suggesting them"`
- For conservative behavior: `"Do not jump into implementation unless clearly instructed"`

---

## 7. Output Formatting

- Tell Claude what **TO do**, not what **NOT to do**:
  - Bad: `"Do not use markdown"`
  - Good: `"Compose your response in smoothly flowing prose paragraphs"`
- Match your prompt style to desired output — if your prompt has no markdown, Claude produces less
- Opus 4.7 is direct and concise; it calibrates response length to task complexity. For longer, fuller responses: `"Give a thorough, multi-paragraph answer with examples"`

---

## 8. Known Pitfalls

| Pitfall | Solution |
|---------|----------|
| Overengineering code (speculative abstraction, hypothetical futures) | `"Don't build speculative abstractions for hypothetical futures. The right amount of complexity is what the task actually requires. Incidental cleanup adjacent to the work is fine."` |
| Hallucinating about unread code | `"Never speculate about code you have not opened. Read the file before answering."` |
| Hard-coding test values | `"Implement a solution that works for all valid inputs, not just test cases."` |
| Excessive file creation | `"If you create temporary files, clean them up at the end."` |
| Shallow reasoning at low/medium effort on complex task | Raise effort to `high` or `xhigh`. Opus 4.7 respects effort levels strictly — don't prompt around it. |
| Literal interpretation dropping old scaffolding | Remove "after every N tool calls, summarize" style prompts. Opus 4.7 handles progress updates natively. |

---

## 9. Opus vs. Sonnet Selection

| Model | Best For | Effort Setting |
|-------|----------|---------------|
| **Opus 4.7** | Agentic coding, large-scale migrations, deep research, extended autonomous work, highest reasoning, 128K output, 1M native context | `xhigh` for coding/agentic; `high` for most |
| **Sonnet 4.6** | Tool-heavy workflows, most applications (best speed/intelligence ratio) | `medium` for most; `low` for high-volume |

**Upgrade to Opus when:** large-scale code migrations, deep research, extended autonomous work, problems requiring highest reasoning quality, or when you need >64K output.

**Sonnet tip:** Set `max_tokens` to 64K at medium/high effort to give room for thinking.

---

## 10. Agentic Patterns

### Context Awareness
Claude tracks remaining context. Tell it about infrastructure:
```
Your context window will be automatically compacted as it approaches its limit.
Do not stop tasks early due to token budget concerns. Save progress to memory
before context refreshes.
```

### Multi-Context-Window Workflows
1. First window: set up framework (write tests, setup scripts)
2. Subsequent windows: iterate on todo-list
3. Write tests in structured format before starting work
4. Use git for state tracking across sessions
5. Starting fresh often beats compacting — Claude rediscovers state from filesystem

### Safety Guardrails
For high-autonomy tasks, explicitly ask Claude to pause on irreversible actions:
```
For actions that are hard to reverse, affect shared systems, or could be
destructive, ask the user before proceeding.
```

### Prompt Chaining
Most useful pattern: **generate → review against criteria → refine**. Each step as a separate API call lets you inspect, log, or branch.

---

## 11. Vision

- Opus 4.7 supports high-resolution images up to 2576px / 3.75 MP on the long edge.
- Full-resolution images can use up to ~4,784 tokens each (up from ~1,600 on prior models) — re-budget `max_tokens` for image-heavy workloads, or downsample before sending.
- Bounding-box coordinates returned by 4.7 are 1:1 with actual image pixels; no scale-factor conversion needed.
- Give Claude a "crop tool" to zoom into image regions — consistent uplift measured.
- Analyze videos by breaking into frames.

---

## 12. Frontend Design

Claude defaults to generic aesthetics. Counter with:
```xml
<frontend_aesthetics>
Avoid generic fonts (Inter, Roboto, Arial). Choose distinctive typography.
Commit to a cohesive color palette. Use CSS animations for micro-interactions.
Avoid purple gradients on white backgrounds.
</frontend_aesthetics>
```
