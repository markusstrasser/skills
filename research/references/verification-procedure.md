<!-- Reference file for dispatch-research skill. Loaded on demand. -->
# Verification Procedure

This is the critical phase. Codex findings have a ~28% error rate. Every finding must be checked.

## Verification checklist

For each audit output:
1. **Exists and has substance** — file exists, >50 lines, not truncated
2. **File paths are real** — grep/glob the cited paths, reject invented ones
3. **Line numbers are accurate** — read the cited file:line, confirm the claim
4. **Counts are correct** — re-run the counting logic yourself (e.g., `wc -l`, `jq length`, `grep -c`)
5. **Classifications are defensible** — a "bug" claim should be a real bug, not a style preference

## Common Codex hallucination patterns

| Signal | Example | Fix |
|--------|---------|-----|
| Invented file paths | `src/auth/middleware.py` when no auth/ exists | Grep for the actual location |
| Wrong counts | "17 orphan files" when actual is 10 | Re-count yourself |
| Phantom features | "missing error handling in X" when X has try/except | Read the actual code |
| Inflated severity | "critical security bug" for a missing docstring | Downgrade or drop |
| Stale references | Citing code that was refactored away | Check git log for the file |
| False fix claims | "This was already fixed" when git log shows no such commit | Verify with `git log --grep` |
| Wrong DOIs | Agent "corrects" a DOI to a different paper | Verify DOI resolves to the claimed paper |

**2026-03-18 session note:** In a 13-tool paper audit, GPT-5.4 had **zero hallucinations** in critical findings (bugs, threshold mismatches, config errors). All verified correct. The ~28% error rate is concentrated in counts, severity grading, and external knowledge claims — not in code-reading accuracy. Code-grounded findings (file:line citations) were consistently reliable.

## Verification output

Produce a verified findings summary:
- **Confirmed findings** (with corrected details where needed)
- **Rejected findings** (with reason: hallucinated path, wrong count, etc.)
- **Corrected findings** (finding was directionally right but details were wrong)

Example from this project's audit session:
```
Audit claimed: "5% test coverage, 17 orphan files, 3 missing parsers"
Verified:       14% test coverage, ~10 orphan files, 12 missing parsers
```
