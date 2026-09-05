<!-- Lens file for review skill: verify mode procedure. Loaded on demand. -->

# Verification — Fact-Checking Procedure

Use for a report or list of file-specific LLM findings, including model review or an external audit. A single specific bug needs direct inspection; already human-verified findings need no repeat pass. Scientific and external factual claims belong to `/research`.

`model-review.py --verify` checks paths, symbols, line anchors and local corroboration. That artifact is useful input, not proof of the described behavior. Semantic confirmation still requires the code, authoritative declaration, or an empirical run.

## Claim Extraction

Parse the report (file or inline text). Prefer structured findings (`findings.json`)
when present; fall back to prose only when no structured artifact exists. Extract
every **file-specific, verifiable claim**:

```
For each finding, extract:
- File path cited
- Line number(s) cited (if any)
- The specific assertion ("function X does Y", "variable Z is unused", "missing error handling")
- Severity claimed
```

Skip vague observations ("code could be cleaner") — only extract concrete, falsifiable claims. Number each claim for tracking.

## Ground Truth Verification Checklist

For each extracted claim, verify against actual code:

1. **File exists** — Resolve exact relative paths first, then basename fallback. Reject invented paths.
2. **Line numbers are accurate** — Read the cited file:line. If the line is stale but the file/symbol is right, mark `CORRECTED`.
3. **Local anchors corroborate the claim** — Look for cited symbols, function names, or code anchors in the resolved file/context.
4. **Logic matches description** — Read the surrounding context. Does the code actually do what the finding claims?
5. **Counts are correct** — Re-run any counting logic yourself (`wc -l`, `rg -c`, etc.).
6. **Severity is defensible** — Is a "critical bug" actually critical, or is it a style preference?
7. **Not already fixed** — Check `git log --oneline -10 -- <file>` for recent changes.

## Common LLM Hallucination Patterns

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

## Calibration by Source

Historical calibration below is retained from prior runs; it is not a measured error rate for a new model or this report. Re-verify the claims rather than grading by model identity:
- **Codex/GPT file-reading claims** (file:line citations): ~5% error rate — generally reliable
- **Codex/GPT counts and severity**: ~28% error rate — always re-verify
- **Gemini structural observations**: variable — check paths exist
- **Any LLM's external knowledge claims** (API behavior, library features): ~30-50% — verify against docs

## Verdict Categories

- **CONFIRMED** — claim matches reality, proceed to fix
- **CORRECTED** — directionally right but details wrong (wrong count, wrong line, wrong severity). Note the correction.
- **HALLUCINATED** — claim doesn't match reality. Drop it.
- **INCONCLUSIVE** — the claim has some anchor, but local evidence is too weak or ambiguous to confirm/correct confidently.

## Synthesis Table Format

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

## Action Rules

- **Fix ALL CONFIRMED and CORRECTED findings within the authorized scope.** Never implement a HALLUCINATED finding. Don't self-select "top N."
- If a specific finding must be deferred (blocked, needs human input, out of scope), state the reason per item.
- Commit each fix separately with the finding number in the commit message.
- If hallucination rate exceeds 40%, warn user the source is unreliable — suggest re-running with a different model.
- For more than 10 findings, write the synthesis table to `docs/audit/verification-YYYY-MM-DD.md` (or the project's audit directory) and return the path. Keep smaller reports concise.
