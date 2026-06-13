# Provenance Tag Taxonomy — the canonical home (SSOT)

Every claim in research/analysis prose carries a provenance tag, or an enforcer flags it as
unsourced. This file is the **single source of truth** for what tags exist. Enforcers do NOT
re-state the list — they load the machine regex from `hooks/provenance_tags.re` (bash hooks
`source`/`cat` it; Python reads it). Adding/renaming a tag = edit `provenance_tags.re` + this
doc, once. `hooks/test_provenance_tags.py` fails if any enforcer drifts from it.

> Why this exists: the tag set had drifted across 5 enforcers — engine tags lived in 2, the
> genomics-DB tags in 1, `[A-F][1-6]` carried `(:reason)?` in some and not others — so two gates
> *disagreed on what counts as sourced*. One home + a drift-test ends that. This is the worked
> exemplar of the **concern-homing** principle (CLAUDE.md `<epistemic_discipline>`): a cross-cutting
> concern gets ONE canonical home that defines its core + extensions; consumers reference it.

## Tiers (the regex is their union — over-accepting a real provenance tag is harmless;
## under-accepting causes false "unsourced" flags, which was the drift bug)

### Core — universal, every enforcer
| Tag | Meaning |
|---|---|
| `[SOURCE: <url/citation>]` | external source, named inline |
| `[DATABASE: <name>]` | a queried database/dataset |
| `[DATA]` | derived from local data the author holds |
| `[INFERENCE]` | the author's reasoning, not a lookup |
| `[SPEC]` | a specification/standard/contract |
| `[CALC]` | a computation shown |
| `[QUOTE]` | a verbatim quote |
| `[TRAINING-DATA]` | recalled from model training (lower trust) |
| `[PREPRINT]` | a non-peer-reviewed preprint |
| `[FRONTIER]` | a frontier/uncertain claim flagged as such |
| `[UNVERIFIED]` | explicitly marked unverified (honest gap — counts as disciplined provenance) |
| `[A1]`–`[F6]` (opt. `:reason`) | source-grade (authority × directness); `[B2: industry whitepaper]` |

### Engine extension — research retrieval context
`[Exa]` `[S2]` (Semantic Scholar) `[PubMed]` `[arXiv]`

### Genomics-DB extension — clinical/genomics context
`[ClinGen]` `[CPIC]` `[gnomAD]` `[OMIM]`

## Consumers (the enforcers that load this, not re-state it)
- `hooks/pretool-source-remind.sh`, `hooks/postwrite-source-check-semantic.sh`,
  `hooks/subagent-source-check-stop.sh`, `hooks/subagent-epistemic-gate.sh` — bash gates
- `~/Projects/agent-infra/scripts/epistemic-lint.py` — cross-repo static lint (reads this regex)
- (`hooks/source-check-validator.py` is NOT a consumer — it parses `[SOURCE:]` payloads, a
  different job than tag-presence; it stays independent.)
