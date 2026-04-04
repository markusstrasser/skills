---
name: retro
description: End-of-session retrospective. Extracts failure modes, environment struggles, and tooling proposals. Use after completing a work session, when asked to reflect on what happened, or when the user says "retro" or "retrospective".
user-invocable: true
argument-hint: '[project or focus area]'
effort: medium
---

# Session Retrospective

Review this session systematically. The goal is error correction — turning observations into hooks, rules, or architectural fixes.

## Phase 1 — Evidence Collection ← Procedural

Scan the session for concrete events:

1. **Failures**: commands that errored, tools that returned wrong results, approaches that were abandoned
2. **Corrections**: places the user redirected you — what did they say and what were you doing wrong?
3. **Wasted work**: code written then deleted, searches that found nothing, repeated attempts at the same thing
4. **Environment friction**: missing dependencies, wrong paths, permission errors, hook blocks, API rate limits
5. **Time sinks**: what consumed disproportionate turns relative to value delivered?

## Phase 2 — Classification ← Criteria

Classify each finding into exactly one category:

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

## Phase 3 — Prior Art Check ← Procedural

Before proposing fixes:

1. Run: `grep -c "^### " ~/Projects/meta/improvement-log.md` to confirm file is accessible
2. Search for similar findings: `grep -i "KEYWORD" ~/Projects/meta/improvement-log.md | head -5` (use the most distinctive word from each finding)
3. Check if finding matches an existing entry → mark "RECURRING: matches entry from YYYY-MM-DD"
4. Check if a hook, rule, or skill already addresses this → note it

## Phase 4 — Output ← Template

```markdown
## Session Retro — YYYY-MM-DD

**Project:** [name]
**Session summary:** [1 sentence]

### Findings

| # | Category | What happened | Evidence | Proposed fix | Recurrence |
|---|----------|--------------|----------|-------------|------------|
| 1 | WRONG_ASSUMPTION | ... | file:line or command | Rule/hook/skill | NEW or RECURRING |

### Improvements (ranked by impact)

1. **[Fix]** — because [evidence]. Implementation: [hook|rule|skill|script].
2. ...
(list all actionable improvements — don't cap at 3)

### What Went Well (max 2)

- [Concrete thing, not a platitude]
```

## Phase 5 — Persist Findings

Write findings as JSON to `~/Projects/meta/artifacts/session-retro/`:

```bash
mkdir -p ~/Projects/meta/artifacts/session-retro
```

Compute a session-scoped filename to avoid overwrites from concurrent agents:

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
```

Write `{date}-{SID}-manual.json` using `Bash` + `cat << 'EOF'` (the Write tool requires a prior Read, but retro JSONs are always new files):
```json
{"findings": [{"category": "...", "summary": "...", "severity": "high|medium|low", "evidence": "...", "project": "...", "proposed_fix": "..."}], "source": "manual-retro"}
```

This feeds into `finding-triage.py ingest` for deduplication and auto-promotion.

## Guardrails

- No platitudes ("overall good session", "learned a lot"). Name files, commands, exact mistakes.
- No generic advice ("be more careful next time"). Every fix must be a concrete hook, rule, skill, or script.
- If a finding has no actionable fix (benign behavior, expected noise), it is NOT a finding. Don't waste a slot on it.
- If nothing went wrong, say so in one line. Don't invent findings.
- Max 5 findings. If more exist, pick the 5 with highest recurrence or impact.

$ARGUMENTS
