# Claude Prompting Guide

Specific to Claude Opus 4.6 and Sonnet 4.6. Updated 2026-02-27.

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

### Adaptive Thinking (Recommended for Opus 4.6)

```python
client.messages.create(
    model="claude-opus-4-6",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # max, high, medium, low
    messages=[...]
)
```

| Effort | Behavior |
|--------|----------|
| `max` | Opus 4.6 only. Always thinks, no constraints |
| `high` | Always thinks, deep reasoning (default) |
| `medium` | Moderate thinking, may skip on simple queries |
| `low` | Minimizes thinking, skips on simple tasks |

Adaptive mode automatically enables **interleaved thinking** (thinking between tool calls). Manual extended thinking on Opus 4.6 does NOT support interleaved thinking -- always use adaptive for agentic workflows.

### Manual Extended Thinking (Sonnet 4.6 only)

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 16384},
    messages=[...]
)
```

For Sonnet 4.6 interleaved thinking, use the `interleaved-thinking-2025-05-14` beta header.

### Prompt-Level Chain-of-Thought (when thinking is off)

- Use `<thinking>` and `<answer>` tags
- Say "think thoroughly" rather than prescribing steps -- Claude's reasoning often exceeds prescriptions
- Include `<thinking>` tags in few-shot examples -- Claude generalizes the pattern
- Add self-check: `"Before finishing, verify your answer against [criteria]"`

### Controlling Overthinking

Opus 4.6 does significantly more upfront exploration than previous models. Counter with:

```
When deciding how to approach a problem, choose an approach and commit to it.
Avoid revisiting decisions unless you encounter new information that directly
contradicts your reasoning.
```

---

## 3. System Prompts & Role Setting

- Set roles in the **system prompt**, not user message
- Claude 4.6 is **more responsive to system prompts** than older models -- soften forceful language:
  - Bad: `"CRITICAL: You MUST use this tool when..."`
  - Good: `"Use this tool when..."`
- **Explain the why** behind constraints:
  - Bad: `"Never use ellipses"`
  - Good: `"Your response will be read aloud by TTS, so never use ellipses since the engine can't pronounce them"`
  - Claude generalizes from explanations better than from bare rules

---

## 4. Long Context Best Practices

200K standard, 1M beta for Opus/Sonnet 4.6.

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

## 5. Prefilling -- DEPRECATED on 4.6

Starting with Claude 4.6, prefilled responses on the last assistant turn are no longer supported.

**Migration paths:**
- Format control: Use system prompt instructions or structured output via tool schemas
- Eliminating preambles: `"Respond directly without preamble. Do not start with 'Here is...', 'Based on...'"`
- Continuations: Move to user message: `"Your previous response ended with [text]. Continue from where you left off."`

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
Claude 4.6 excels at parallel execution. Boost to ~100% with:
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between
the calls, make all independent calls in parallel.
</use_parallel_tool_calls>
```

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
- Match your prompt style to desired output -- if your prompt has no markdown, Claude produces less
- **Opus 4.6 defaults to LaTeX** for math. Prevent with: `"Format in plain text only. Do not use LaTeX."`
- **4.6 is more concise** than previous models. May skip summaries after tool calls. For verbosity: `"After completing tool use, provide a quick summary"`

---

## 8. Known Pitfalls

| Pitfall | Solution |
|---------|----------|
| Overtriggering on tools/skills | Soften forceful instructions -- 4.6 is more responsive |
| Overengineering code | `"Only make changes that are directly requested. Don't add features beyond what was asked."` |
| Hallucinating about unread code | `"Never speculate about code you have not opened. Read the file before answering."` |
| Hard-coding test values | `"Implement a solution that works for all valid inputs, not just test cases."` |
| Excessive subagent spawning (Opus 4.6) | `"For simple tasks, single-file edits, or sequential operations, work directly."` |
| Excessive file creation | `"If you create temporary files, clean them up at the end."` |
| Opus 4.5 sensitivity to "think" | Use "consider", "evaluate", "reason through" when thinking is disabled (4.5 only) |

---

## 9. Opus vs. Sonnet Selection

| Model | Best For | Effort Setting |
|-------|----------|---------------|
| **Opus 4.6** | Large-scale migrations, deep research, extended autonomous work, highest reasoning, 128K output | `max` or `high` |
| **Sonnet 4.6** | Agentic coding, tool-heavy workflows, most applications (best speed/intelligence ratio) | `medium` for most; `low` for high-volume |

**Upgrade to Opus when:** large-scale code migrations, deep research, extended autonomous work, problems requiring highest reasoning quality, or when you need >64K output.

**Sonnet tip:** Set max_tokens to 64K at medium/high effort to give room for thinking. Sonnet's GDPval (1633) actually beats Opus (1606) on expert preference -- it's not always a downgrade.

---

## 10. Agentic Patterns

### Context Awareness
Claude 4.5+ tracks remaining context. Tell it about infrastructure:
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
5. Starting fresh often beats compacting -- 4.6 rediscovers state from filesystem

### Safety Guardrails
Opus 4.6 may take irreversible actions without asking:
```
For actions that are hard to reverse, affect shared systems, or could be
destructive, ask the user before proceeding.
```

### Prompt Chaining
Most useful pattern: **generate -> review against criteria -> refine**. Each step as a separate API call lets you inspect, log, or branch.

---

## 11. Vision

- 4.5+ and 4.6 have improved multi-image processing
- Give Claude a "crop tool" to zoom into image regions -- consistent uplift measured
- Analyze videos by breaking into frames

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
