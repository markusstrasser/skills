<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Dispatch Mechanics

## Shared Dispatch Contract

The review script owns transport, context packing, output files, extraction, and
verification. Prefer the script over ad hoc model calls:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "What's wrong with this [thing being reviewed]"
```

Use `--verify` when the review is a plan-close packet or when you want the script
to check file/symbol references after extraction:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context .model-review/plan-close-context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract --verify \
  "Review this plan closeout"
```

Other useful forms:

```bash
# Deep review with per-axis overrides
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context-files docs/plan.md scripts/finding_ir.py:86-110 \
  --topic "$TOPIC" \
  --axes arch,formal,domain,mechanical \
  --questions questions.json \
  --extract \
  "Review this plan"
```

## Contract Boundaries

Transport/model choices live in `shared/llm_dispatch.PROFILES`. Update that shared
contract rather than duplicating provider flags in skill docs.

Relevant profiles:
- `deep_review` for Gemini pattern review
- `formal_review` for GPT-5.4 reasoning
- `fast_extract` for mechanical extraction

The script writes these artifacts:
- `shared-context.md` / `shared-context.manifest.json`
- `<axis>-output.md`
- `findings.json`
- `disposition.md`
- `verified-disposition.md`
- `coverage.json`

`coverage.json` is the stable machine-readable summary. Current top-level fields:
- `schema_version`
- `artifacts`
- `context_packet`
- `dispatch`
- `extraction`
- `verification`

## Context Assembly

`--context-files` accepts file specs of the form `path/file.py`,
`path/file.py:100-150`, or `path/file.py:100`.

For plan-close review packets, prefer:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

## Context Formatting

Before assembling context, check `/model-guide` for per-model prompting rules.
Key points:

- GPT-5.4 context should use XML `<doc id="..." title="...">` tags for document sections
- Gemini does better when the question and constraints come last
- Keep prompts direct; the shared review script handles the rest

## Extraction Defaults

Use `--extract` for normal user-facing reviews. Use `--extract --verify` for
plan-close packets or any review that needs an auditable coverage trail with
checked references. The user-facing presets are `standard`, `deep`, and `full`;
each includes GPT-5.4. Non-GPT axis sets are internal-only.
