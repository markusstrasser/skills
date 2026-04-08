# Supervision Waste Classification

## Categories

| Category | Definition | Automatable? |
|----------|-----------|-------------|
| **NEW_AGENCY** | Genuinely new direction or information from the user | No -- this is real supervision |
| **CORRECTION** | User corrects agent mistake that a check could have caught | Yes -- hook or validation |
| **BOILERPLATE** | User repeats standard instruction already in CLAUDE.md/rules | Yes -- rule enforcement or default change |
| **RUBBER_STAMP** | User approves without adding information ("yes", "go ahead", "looks good") | Yes -- change approval flow or default |
| **RE_ORIENT** | User re-provides context lost to compaction or session boundary | Yes -- better checkpointing |

## Fix Types

For each non-NEW_AGENCY pattern, classify the fix:

| Fix type | When to use | Maintenance |
|----------|------------|-------------|
| **HOOK** | Deterministic shell/Python check (PreToolUse, PostToolUse, Stop) | NONE (fire-and-forget) |
| **RULE** | CLAUDE.md instruction (only if checkable and not already covered) | LOW |
| **DEFAULT** | Change a default behavior (e.g., research depth, commit flow) | NONE |
| **SKILL** | New or modified skill to handle the pattern | LOW-MEDIUM |
| **ARCHITECTURAL** | Structural change (new script, registry, checkpoint system) | MEDIUM |

## Metrics

- **Wasted supervision %** = (CORRECTION + BOILERPLATE + RUBBER_STAMP + RE_ORIENT) / total user messages
- **Target:** <15% wasted supervision
- **Ranking:** occurrences x maintenance-adjusted automation potential. Dev time is ~free -- rank by ongoing cost, not creation effort.

## Constraints

- The extraction script (`scripts/extract_supervision.py`) is DETERMINISTIC -- no LLM judgment in classification. False positives/negatives are consistent and tunable.
- The Gemini pass is for SYNTHESIS only -- finding non-obvious connections, proposing fixes, filtering noise. Raw data is source of truth.
- Do not propose fixes that duplicate existing hooks or CLAUDE.md rules.
- Fixes must be TESTABLE. "Add a rule that says X" alone is not testable (instructions = 0% reliable).
