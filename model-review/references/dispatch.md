<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Dispatch Mechanics

## Script Dispatch (Always Prefer This)

The dispatch script handles: output directory creation, constitutional preamble injection, context splitting, parallel llmx dispatch, and waiting.

```bash
# Standard review (2 queries -- default)
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  "What's wrong with this [thing being reviewed]"

# Simple review (1 query -- for low-stakes changes)
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --axes simple \
  "Review this change"

# Deep review (4 queries -- structural/domain-dense)
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --axes deep \
  --project "$(pwd)" \
  "Review this plan"

# Custom axes (mix and match)
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --axes arch,domain,mechanical \
  "Review this"
```

The script fires all queries in parallel and prints JSON with output paths per axis.

### `--extract` Flag (Recommended)

With `--extract`, the script auto-extracts claims from each output using cross-family models (Flash extracts GPT output, GPT-Instant extracts Gemini output) and merges them into `disposition.md`. The JSON output includes a `"disposition"` key with the path. You then:
1. Read `disposition.md` -- merged numbered claims from all reviewers
2. Proceed to Step 4 (fact-check the extracted claims)
3. Skip Step 5 (already done by the script)

Without `--extract`, you must manually extract claims (Step 5).

**Add `--extract` to all standard and deep reviews.** Only skip it for simple reviews where you'll read the output directly.

```bash
# Standard review WITH auto-extraction (preferred)
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "What's wrong with this [thing being reviewed]"
```

### `--questions` Flag (Per-Axis Questions)

Use `--questions` to customize the review question per axis. Pass a JSON file mapping axis names to questions:

```bash
echo '{"arch": "Focus on the DAG wiring", "formal": "Verify the cost model assumptions"}' > questions.json
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md --topic "$TOPIC" --project "$(pwd)" --extract \
  --questions questions.json \
  "Default question for axes not in the JSON"
```

Axes not present in the JSON file fall back to the positional `question` argument.

### `--context-files` Flag (Auto-Assembly)

Use `--context-files` to skip manual assembly. The script reads each file spec and concatenates with headers:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context-files docs/plan.md scripts/finding_ir.py:86-110 scripts/hard_locus_report.py:93-185 \
  --topic "expansion-plan" --project "$(pwd)" --extract \
  "Review this plan against the code it references"
```

File spec formats: `path/file.py` (entire file), `path/file.py:100-150` (line range), `path/file.py:100` (single line). Each file gets a header showing its path and range.

### Bash Timeout

Set `timeout: 660000` on the Bash tool call (script waits for both models + extraction, up to 11 min). The script never falls back to weaker models -- diagnose failures from the JSON output's `stderr` field.

## Manual Dispatch (Non-Standard Prompts)

Only use when you need custom context assembly or non-standard prompts. See `references/prompts.md` for the full prompt templates.

### Pre-Dispatch Checklist

- [ ] `--stream` on GPT (needed for streaming output with reasoning)
- [ ] Output dir: `.model-review/YYYY-MM-DD-{topic-slug}/` (NOT /tmp/)
- [ ] Context bundle < 15KB per model (summarize if larger)

**CRITICAL: Fire both Bash calls in a SINGLE message (two parallel tool calls).** Do NOT wait for one model before calling the other. Both models run independently -- dispatch them simultaneously to halve wall-clock time.

### Model Selection

```bash
# Gemini -- Pro only. No fallback.
GEMINI_MODEL="gemini-3.1-pro-preview"
# No --stream: routes through Gemini CLI (free tier).
# Hang bug on thinking models + stdin was fixed in gemini-cli 0.32.1.
# If CLI hits rate limits, add --stream to force API transport.

# GPT -- 5.4 with deep reasoning, no fallback
GPT_MODEL="gpt-5.4"
GPT_EFFORT="--reasoning-effort high --stream"  # --stream needed for GPT reasoning output
GPT_TIMEOUT="--timeout 600"
# Note: --stream forces API transport (CLI doesn't support streaming).
# GPT-5.x max_completion_tokens includes reasoning tokens -- 32K required for high reasoning effort.
# 16K causes empty output (all tokens consumed by thinking). Use 16K only for medium reasoning.
```

### Bash Timeout (Manual)

Always set `timeout: 660000` (11 minutes -- must exceed llmx --timeout value) on the Bash tool call. The default 120s Bash timeout kills the process before llmx finishes. llmx's own `--timeout` handles the real deadline.

### Output Capture

Use `--output FILE` (or `-o FILE`) to write output to a file. This writes directly via Python (no shell buffering) -- the file has content immediately on completion, not 0 bytes until process exit like `> file` redirects. Never use `> file` shell redirects with llmx. Never use `PYTHONUNBUFFERED` -- the buffering is in the shell redirect, not Python.

## Uncalibrated Threshold Flagging

Automatic with `--extract`: the script post-processes extracted claims and tags lines containing numeric thresholds (e.g., `>=20% AUPRC`, `PPV >=0.8`) that lack a cited source (paper, benchmark, table reference) with `[UNCALIBRATED]`. This catches a common GPT failure mode: fabricating plausible-sounding numeric thresholds with no calibration data. During synthesis, treat `[UNCALIBRATED]` claims as requiring your own threshold derivation -- don't adopt the number.
