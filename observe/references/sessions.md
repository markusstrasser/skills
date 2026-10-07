# Observe: sessions

Read [transcript preparation](transcript-extraction.md), [analysis dispatch](analysis-dispatch.md), and [candidate lifecycle](candidate-lifecycle.md) for this mode.

Behavioral anti-patterns no linter can detect. Rubric + 20-item taxonomy in
[behavioral-antipatterns.md](../lenses/behavioral-antipatterns.md) · grounding examples in [grounding-examples.md](grounding-examples.md) ·
prompt in [gemini-dispatch-prompt.md](gemini-dispatch-prompt.md) · staging procedure and JSON template in
[findings-staging.md](findings-staging.md) · digest format in [digest-template.md](digest-template.md).

1. **Run manifest** — record mode, project filter, session ids, artifact root, whether dispatch ran.
   If the same session set already exists in the manifest and `--force` was not passed, **stop**;
   do not append another narrative-only run.
2. **Extract + pre-filter** ([transcript preparation](transcript-extraction.md)). Operational context per [transcript-extraction.md](transcript-extraction.md)
   Step 1.3.
3. **Classify** ([analysis dispatch](analysis-dispatch.md)), then **precision-pass**: in Cursor the subagent analysis *is* the
   precision pass; headless, run a `fast_extract` (gpt-6-astra low) screen on HIGH-severity candidates only (max 3
   clusters, ~20 lines of evidence each) demanding `VERDICT promote|drop|needs_more_evidence` plus a
   cited transcript line or `MISSING`. Skip entirely when headless returned zero candidates.
4. **Stage + summarize** — sessions analyzed, shape anomalies, signals staged, candidates by
   category, ready-for-promotion, new failure modes, proposed fixes.

**`--corrections`** mines user correction patterns over the same pipeline
([corrections-mode.md](corrections-mode.md)).
