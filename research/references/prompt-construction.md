<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Prompt Construction

## Target selection

Look for these categories of useful work:

| Category | Example | Good Codex target? |
|----------|---------|-------------------|
| **Wiring** | Does data flow correctly between components? | Yes — cross-file tracing |
| **Drift** | Do configs/docs match code? Counts match reality? | Yes — counting/comparing |
| **Completeness** | Are all expected outputs produced? | Yes — checklist verification |
| **Impact** | What downstream effects do recent changes have? | Yes — grep + trace |
| **Hygiene** | Dead code, orphan files, stale state? | Yes — existence checks |
| **Integration** | Do cross-module consumers still work? | Yes — interface matching |
| **Correctness** | Do algorithms match their cited sources? | Partial — logic only |

Don't generate prompts for things obvious from reading the code. Target things requiring **cross-referencing multiple files**, **counting/comparing**, or **tracing data flow**.

## Prompt structure

Every prompt must be self-contained and file-output-oriented:

```
Read [2-5 specific file paths]. For each [concrete thing], check:
(a) [specific verifiable property]
(b) [specific verifiable property]
Cross-reference [A] against [B]. Categorize findings as: [defined categories].
Cite file:line for every finding.
Save to [specific output path].
```

## Good patterns

- "Read X and Y, compare field Z" — grounded comparison
- "For each item in X, verify it exists in Y" — completeness check
- "Trace the data flow from A through B to C" — wiring audit
- "Count/rank/compute" — plays to GPT-5.4 math strength

## Bad patterns

- "Investigate X" — too vague, produces slop
- "Research best practices" — needs web, Codex can't
- "Fix the code" — audits should REPORT, not MODIFY
- "Check if everything works" — no specific properties
