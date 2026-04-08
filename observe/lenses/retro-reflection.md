# Retrospective Classification

## Categories

| Category | Definition | Fix type |
|----------|-----------|----------|
| **WRONG_ASSUMPTION** | Started from incorrect premise | Rule or check |
| **ENVIRONMENT** | Tool/path/dep/permission issue | Script or setup fix |
| **SEARCH_WASTE** | Searched broadly when answer was nearby | Better routing |
| **BUILD_THEN_UNDO** | Built something, then reverted | Plan-first rule |
| **SYCOPHANCY** | Agreed when should have pushed back | Pushback rule |
| **SCOPE_CREEP** | Did more than asked | Constraint |
| **TOKEN_WASTE** | Burned context on low-value actions | Efficiency rule |
| **TOOL_MISUSE** | Used wrong tool or wrong parameters | Tool routing |

## Evidence Collection Checklist

Scan the session for concrete events:

1. **Failures**: commands that errored, tools that returned wrong results, approaches that were abandoned
2. **Corrections**: places the user redirected you -- what did they say and what were you doing wrong?
3. **Wasted work**: code written then deleted, searches that found nothing, repeated attempts at the same thing
4. **Environment friction**: missing dependencies, wrong paths, permission errors, hook blocks, API rate limits
5. **Time sinks**: what consumed disproportionate turns relative to value delivered?

## Guardrails

- No platitudes ("overall good session", "learned a lot"). Name files, commands, exact mistakes.
- No generic advice ("be more careful next time"). Every fix must be a concrete hook, rule, skill, or script.
- If a finding has no actionable fix (benign behavior, expected noise), it is NOT a finding.
- If nothing went wrong, say so in one line. Don't invent findings.
- Max 5 findings. If more exist, pick the 5 with highest recurrence or impact.

## Output Template

```markdown
## Session Retro -- YYYY-MM-DD

**Project:** [name]
**Session summary:** [1 sentence]

### Findings

| # | Category | What happened | Evidence | Proposed fix | Recurrence |
|---|----------|--------------|----------|-------------|------------|
| 1 | WRONG_ASSUMPTION | ... | file:line or command | Rule/hook/skill | NEW or RECURRING |

### Improvements (ranked by impact)

1. **[Fix]** -- because [evidence]. Implementation: [hook|rule|skill|script].

### What Went Well (max 2)

- [Concrete thing, not a platitude]
```
