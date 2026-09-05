# Observe: architecture

Read [transcript preparation](transcript-extraction.md), [analysis dispatch](analysis-dispatch.md), and [candidate lifecycle](candidate-lifecycle.md) for this mode. The result is a proposal memo; implementation requires a separate authorized step.

Better abstractions, missing tools, repeated workflows that should be pipelines, cross-project
patterns that should be shared infra. Pattern types in [architectural-patterns.md](../lenses/architectural-patterns.md) · output
template in [output-template.md](output-template.md) · prompt in [gemini-prompt.md](gemini-prompt.md) · loop-mode
JSONL format in [loop-mode.md](loop-mode.md).

**Mindset: the best proposals are ones nobody asked for.** A pattern in 3 sessions is coincidence.
A pattern in 8 sessions across 3 projects is an abstraction waiting to be born.

Gather all active projects unless `--project`, merge to `all.md`, verify <500KB → extract patterns
([analysis dispatch](analysis-dispatch.md); output is DATA, verify every claim) → **creative synthesis**: cross-reference
existing infra first ([existing-infra-checks.md](existing-infra-checks.md)), then for each verified pattern
generate 3+ genuinely different approaches — **denial cascade** ("what if we COULDN'T use
hooks/skills/pipelines?"), **cross-domain forcing** (the analogous problem in another field),
**inversion** ("what if we made X unnecessary?") — and converge with the lens filters. Write
`$ARTIFACT_DIR/YYYY-MM-DD.md`, proposals sorted by priority.

**Do NOT** implement, write to `improvement-log.md`, modify GOALS.md, or propose a backlog item
without marking it KNOWN. **DO** include one wild card challenging a current assumption, name the
system's trajectory, and flag the single highest-leverage abstraction.
