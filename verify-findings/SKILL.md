---
name: verify-findings
description: Verify LLM-generated codebase findings against actual code. Use after model-review, dispatch-research, project-upgrade, or any automated audit that produces file-specific claims. Grades each finding as Confirmed/Hallucinated/Corrected before allowing fixes.
user-invocable: true
argument-hint: '<report path or paste findings inline>'
effort: high
---

# Verify Findings

Standalone verification of LLM-generated audit findings. Extracted from dispatch-research Phase 3 for use after ANY audit source — Codex, Gemini, model-review, project-upgrade, or manual paste.

## When to Use

- After `/model-review` produces codebase critique
- After `/dispatch-research` generates audit findings
- After `/project-upgrade` suggests changes
- After receiving external audit output (Codex, Gemini, GPT)
- When someone pastes a list of "bugs found" from any LLM
- Before implementing ANY fix list from an LLM source

## When NOT to Use

- For verifying scientific/factual claims (use `/researcher` or `/epistemics`)
- For verifying a single specific bug (just read the code directly)
- When findings are already human-verified

## Phase 1: Extract Claims

Parse the report (file or inline text). Extract every **file-specific, verifiable claim**:

```
For each finding, extract:
- File path cited
- Line number(s) cited (if any)
- The specific assertion ("function X does Y", "variable Z is unused", "missing error handling")
- Severity claimed
```

Skip vague observations ("code could be cleaner") — only extract concrete, falsifiable claims.

Number each claim for tracking.

## Phase 2: Ground Truth Verification

For each extracted claim, verify against actual code. Use this checklist:

### Verification checklist

1. **File exists** — Glob/Grep for the cited path. Reject invented paths.
2. **Line numbers are accurate** — Read the cited file:line, confirm the claim matches.
3. **Logic matches description** — Read the surrounding context. Does the code actually do what the finding claims?
4. **Counts are correct** — Re-run any counting logic yourself (`wc -l`, `grep -c`, etc.).
5. **Severity is defensible** — Is a "critical bug" actually critical, or is it a style preference?
6. **Not already fixed** — Check `git log --oneline -10 -- <file>` for recent changes.

### Common LLM hallucination patterns

| Signal | Example | How to catch |
|--------|---------|-------------|
| Invented file paths | `src/auth/middleware.py` when no `auth/` exists | Glob for the path |
| Wrong counts | "17 orphan files" when actual is 10 | Re-count yourself |
| Phantom features | "missing error handling" when try/except exists | Read the actual code |
| Inflated severity | "critical security bug" for a missing docstring | Evaluate actual impact |
| Stale references | Citing code that was refactored | `git log -- <file>` |
| False fix claims | "This was already fixed in commit X" | `git log --grep` |
| Wrong line numbers | Off by 10-50 lines due to stale index | Read file, search for the pattern |
| Conflated files | Attributes of file A applied to file B | Read both files |

### Calibration note

Error rates vary by source and claim type:
- **Codex/GPT file-reading claims** (file:line citations): ~5% error rate — generally reliable
- **Codex/GPT counts and severity**: ~28% error rate — always re-verify
- **Gemini structural observations**: variable — check paths exist
- **Any LLM's external knowledge claims** (API behavior, library features): ~30-50% — verify against docs

## Phase 3: Synthesis Table

Produce a verification summary in this format:

```markdown
## Verification Synthesis

| # | Claim | File:Line | Verdict | Notes |
|---|-------|-----------|---------|-------|
| 1 | "X function missing null check" | `api.py:45` | CONFIRMED | Guard clause absent |
| 2 | "17 orphan files in tests/" | — | CORRECTED | Actually 10 orphan files |
| 3 | "Critical SQL injection in query()" | `db.py:112` | HALLUCINATED | Input is parameterized |
| 4 | "Unused import on line 3" | `utils.py:3` | CONFIRMED | `os` imported, never used |

**Summary:** N findings. X confirmed, Y corrected, Z hallucinated.
**Hallucination rate:** Z/N (compare to expected ~28% for Codex, varies by source)
```

Verdict categories:
- **CONFIRMED** — claim matches reality, proceed to fix
- **CORRECTED** — directionally right but details wrong (wrong count, wrong line, wrong severity). Note the correction.
- **HALLUCINATED** — claim doesn't match reality. Drop it.
- **INCONCLUSIVE** — can't verify without running the code or deeper investigation. Flag for human.

## Phase 4: Action

- **Fix only CONFIRMED and CORRECTED findings.** Never fix HALLUCINATED claims.
- Commit each fix separately with the finding number in the commit message.
- If hallucination rate exceeds 40%, warn the user that the audit source is unreliable and suggest re-running with a different model or approach.
- Write the synthesis table to `docs/audit/verification-YYYY-MM-DD.md` (or the project's audit directory) for the record.

## Output Convention

If total findings > 10, write the synthesis table to a file and return the path. Don't dump 30-row tables inline.
