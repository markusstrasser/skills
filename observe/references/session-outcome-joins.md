<!-- Reference file for evolution-forensics skill. Loaded on demand. -->

# Session→Commit→Outcome Joins (Phase 1c)

Build the causal chain. For commits with Session-ID trailers:

1. Group commits by Session-ID → "what did this session produce?"
2. For each session's commits, check: were any files subsequently touched by a FIX or FIX-OF-FIX? → "did this session's work need correction?"
3. For fix-of-fix chains, trace back: which session introduced the original code?

Output a session outcome table:

```markdown
## Session Outcomes
| Session-ID | Project | Commits | Files | Fix-of-fix within 3d? | Subsequent corrections |
|-----------|---------|---------|-------|----------------------|----------------------|
```

Sessions with high correction rates are producing fragile code. Sessions with zero corrections are producing durable code. The *difference* between them is the learning signal.
