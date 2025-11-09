---
name: llmx Guide
description: Critical gotchas when calling llmx from Python. Non-obvious bugs and incompatibilities.
---

# llmx CLI Gotchas

## Bug: shell=True breaks with parentheses

**Wrong:**

```python
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)  # BREAKS if prompt has ()
```

**Right:**

```python
subprocess.run(['llmx', '--provider', 'google'], input=prompt, ...)
```

## Bug: --reasoning-effort only works with OpenAI

```python
# Works:
['llmx', '--provider', 'openai', '--reasoning-effort', 'high']

# Silently ignored or errors:
['llmx', '--provider', 'google', '--reasoning-effort', 'high']  # WRONG
['llmx', '--model', 'kimi-k2-thinking', '--reasoning-effort', 'high']  # WRONG
```

## Model names: hyphens not dots

| Right               | Wrong               |
| ------------------- | ------------------- |
| `claude-sonnet-4-5` | `claude-sonnet-4.5` |
| `kimi-k2-thinking`  | `kimi2-thinking`    |

## Testing: test small before full pipeline

```bash
# Don't wait for full pipeline to discover API key is wrong
llmx --provider google <<< "2+2?"
```

## Judge names ≠ model names

| Context               | Name             |
| --------------------- | ---------------- |
| llmx CLI              | `gemini-2.5-pro` |
| tournament MCP judges | `gemini25-pro`   |
