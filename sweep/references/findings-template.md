# Sweep Findings Template

Use this structure for `docs/audit/sweep-{date}/findings.md`.

```markdown
# Codebase Consistency Sweep — {DATE}

**Scope:** git log -{DEPTH}, {N} commits, {AXES} axes
**Method:** structural analysis + Gemini Flash classification
**Verified:** {N_VERIFIED}/{N_TOTAL} Flash findings confirmed against source

## CRITICAL — Semantic Data Errors

### F1. {Title}
- **Evidence:** {grep output or script result proving the issue}
- **Files:** `path/to/file.json`
- **Fix:** {concrete fix, not "should be fixed"}

## HIGH — Structural Inconsistencies

### F2. {Title}
- **Evidence:** {counts, cross-check results}
- **Files:** {file list or count}
- **Fix:** {migration plan or one-liner}

## MEDIUM — Pattern Drift

### F3. {Title}
- **Evidence:** {hash comparison, adoption counts}
- **Files:** {affected scripts}
- **Fix:** {extract/unify/migrate}

## LOW — Tech Debt

### F4. {Title}
- **Evidence:** {counts}
- **Files:** {scope}
- **Fix:** {codemod or defer}

---

## Remediation Plan

### Phase 1: {Name} ({effort}, {value})
| # | Fix | Files |
|---|-----|-------|
| 1a | {specific fix} | `file.py` |

### Phase 2: ...

### Deferred
| Finding | Reason |
|---------|--------|
| F{N} | {why deferred} |

---

## Verification Log

| Finding | Flash claimed | Verified | Result |
|---------|-------------|----------|--------|
| F1 | Copy-paste in trait_panels | grep confirmed | TRUE |
| FX | Missing function Y | grep found Y exists | FALSE — dropped |
```
