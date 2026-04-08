<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 5: Model Review (~15% of effort)

Invoke `/model-review` on the plan. Depth depends on blast radius:

| Plan scope | Review depth | Axes |
|-----------|-------------|------|
| 1-2 simple additions | `--axes simple` | 1 query (Gemini Pro combined) |
| 3-5 new analyses | `--axes arch,formal` | 2 queries (standard) |
| 6+ analyses or domain-dense | `--axes deep` | 4 queries (arch + formal + domain + mechanical) |
| Shared infrastructure changes | `--axes full` | 5 queries |

## Context size gate (F3 gate)

Before dispatching:

```bash
wc -c context.md
# If > 15KB: summarize before sending to Gemini Pro
# If > 50KB: summarize before sending to GPT-5.4
# The model-review.py script handles this automatically with --extract
```

**Why 15KB for Gemini:** model-review.py dispatches Gemini via CLI transport (free tier,
`--timeout 300`, no `--stream`, no `--max-tokens`). CLI transport can handle 1M context
in theory but thinking models timeout at ~15KB within the 300s window. The script falls
back to Flash on failure, but Flash is shallow — you lose deep review. Summarize instead.

**To force API transport** (paid, handles larger context): add `--stream` to the axis flags
in model-review.py. But this costs money — prefer summarizing to <15KB.

**Preferred:** Use `model-review.py --extract` (auto-extracts claims cross-family).

## Review integration

After review completes:
1. Read all outputs (formal, domain, mechanical, arch)
2. For each finding: ACCEPT (amend plan), REJECT (with reason), or NOTE (track but don't change)
3. Update the plan with a "## Model Review Amendments" section at top
4. Adjust tiers based on review (things may get demoted)
