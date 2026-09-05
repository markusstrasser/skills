# Observe: all

Use [transcript preparation](transcript-extraction.md) and the [artifact contract](artifact-contract.md). Read each lane workflow only when interpreting that lane; [candidate lifecycle](candidate-lifecycle.md) governs merged findings.

Deterministic Tier-0 for every lane in one timestamped run dir, with **cross-mode triangulation**
(supervision vector + blindspot + failures reinforcing one theme = higher confidence).
`just observe-run all [project] [days]` writes `artifacts/observe/{run-id}/`. Then in Cursor
`--multitask`, fan out subagents on the **prep artifacts** — do not re-extract by hand; read the
triangulation section of `digest.md` first.

**Scope-aware triangulation.** `observe_run.py` tags lanes with scope and sensitivity and only
triangulates within compatible scope: supervision is `project-filter`/strict; blindspot, drift,
failures, architecture are `fleet`/loose.

- A **zero reading from a strict project-scoped lane is NOT corroboration** for a fleet alarm.
- Fleet-only signals get `confidence: low`; they must not drive RAISE_AUTONOMY on a filtered project.
- Both lanes non-zero → `confidence: high`.

Merged candidates get `existing_coverage_match` at emit time (improvement-log + steward-proposals
join) so known-open items surface as `lifecycle: modify`, not a fresh `[ ]` row. Verdicts carry
`lifecycle: add|modify|suppress` (L1 anti-accretion).
