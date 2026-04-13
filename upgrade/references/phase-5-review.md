<!-- Reference file for novel-expansion skill. Loaded on demand. -->

# Phase 5: Model Review (~15% of effort)

Invoke the shared review surface on the plan packet. Depth depends on blast
radius:

| Plan scope | Review depth | Axes |
|-----------|-------------|------|
| 1-2 narrow additions | `standard` | `arch,formal` |
| 3-5 new analyses | `standard` | `arch,formal` |
| 6+ analyses or domain-dense | `deep` | `arch,formal,domain,mechanical` |
| Shared infrastructure changes | `full` | `arch,formal,domain,mechanical,alternatives` |

Do not route user-facing upgrade review through the removed Gemini-only
`simple` preset.

## Context Size Gate (F3)

Before dispatch:

- build one bounded packet or context artifact
- prefer the shared packet builder over ad hoc stuffing
- inspect the packet manifest if the context had to be trimmed

`coverage.json` and the sidecar manifest are the source of truth for what the
review actually saw. Do not reason from the nominal input set alone.

## Preferred Invocation

Use the shared review flow with extraction enabled. For high-stakes closeout or
implementation follow-through, add verification:

- review packet only: `--extract`
- plan-close or high-trust review: `--extract --verify`

## Review Integration

After review completes:

1. Read `findings.json` and `coverage.json`.
2. For each finding: ACCEPT (amend plan), REJECT (with reason), or NOTE.
3. Update the plan with a `## Model Review Amendments` section.
4. If `coverage.json` shows dropped packet blocks or missing axes, fix the packet
   and rerun before trusting the verdict.
