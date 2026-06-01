---
name: entity-management
description: Versioned, sourced entity dossiers across repos. Use when creating/updating company, stock, person, gene, drug, self, contract, or filing pages; routes intel public-company entities to analysis/entities and selve/general entities to docs/entities.
user-invocable: true
argument-hint: [entity name - person, company, gene, drug, stock]
effort: medium
---

# Entity Management

Track durable knowledge about one entity with full provenance. The first job is
to choose the repo-local entity surface and schema; wrong path/schema is worse
than no file.

## First: Route By Project

Before editing, inspect the current repo and load its local rules:

- **`/Users/alien/Projects/intel` public companies / stocks:** use
  `analysis/entities/{TICKER}.md` or `analysis/entities/{TICKER}/index.md`.
  Read `docs/entity-evaluation-checklist.md` and
  `.claude/rules/conviction-template.md` before material edits.
- **`selve` / personal health / genomics / general knowledge:** use
  `docs/entities/<category>/<entity-name>.md` with search-elevation
  frontmatter.
- **Unknown repo:** search for existing entity directories and templates first
  (`rg --files | rg '(^|/)entities/'`). If no local convention exists, use the
  generic `docs/entities/<category>/<entity-name>.md` template below.

Do not create a second entity surface because search was lazy. Existing entity
files outrank new files.

## Universal Rules

- Every load-bearing claim cites a source, database ID, local artifact, command
  output, or explicit derivation chain.
- Inferred claims are labeled `[INFERRED]`; unchecked claims are
  `[UNVERIFIED]`; corrected claims are `[CORRECTED]` and left visible.
- Do not copy claims between entity files without checking whether the source
  and date still apply.
- Cross-link related entities when the relationship is durable.
- If key facts are older than 6 months and the domain drifts quickly, flag them
  for refresh before relying on them.
- When a file is long, keep a compact top summary / key facts surface so future
  agents can answer obvious questions without rereading the whole dossier.

Primary sources include paper DOIs/PMIDs, ClinVar/gnomAD/OMIM/PharmGKB, FDA
labels, CPIC guidelines, SEC/foreign filings, court records, government
reports, and reproducible local data queries.

## Intel Public Companies

Use this path only in the `intel` repo.

### Discovery and path

- Find existing files before creating anything. Valid paths are:
  - `analysis/entities/{TICKER}.md`
  - `analysis/entities/{TICKER}/index.md`
- **In the intel repo, run `uvx python3 tools/entity_exists.py "<ticker or name>"` FIRST.**
  It resolves ticker / name-form / `alt_tickers` / frontmatter-`name` across the
  mixed-convention corpus (e.g. `SKHYNIX.md` carries `ticker: 000660.KS`). A
  single-form grep like `000660` misses name-form files and risks a duplicate
  (the SK Hynix near-miss, 2026-05-28). Exit 0 = exists (UPDATE it); exit 1 =
  safe to create.
- If `tools/lib/entity_paths.py` exists, use tooling that imports it for flat
  and folder-form discovery. Any migration to folder form must update or verify
  discovery tooling in the same slice; tools that glob only
  `analysis/entities/*.md` miss folder-form entities.
- Folder form is preferred when the entity has substantial primary-source
  corpus, parsed filings, models, or model-review history.

#### Flat vs folder reconciliation

If both `{TICKER}.md` and `{TICKER}/index.md` exist, they have diverged. The
operator may have re-created the flat file after a folder move, leaving the
folder stale (SNDK 2026-05-25 incident). Before editing either:

1. `git log --oneline -- analysis/entities/{TICKER}.md analysis/entities/{TICKER}/index.md` — newer commits = canonical.
2. Check for archived-rule references in the older file: `edge_score`,
   `asymmetry_score`, `convexity_score`, `mcap-veto`, `breakeven_threshold`,
   `E[24mo] =`, scenario tables with probability columns, citations of
   `.claude/rules/_archived/*` — any of these means the file is on a retired
   framework and is not safe to update in place. Reconcile to the form
   matching the current `.claude/rules/conviction-template.md`.
3. If folder form has no unique primary-source corpus beyond the flat file,
   delete the folder and keep flat. If flat is a stale stub and folder is
   maintained, delete flat and keep folder. Never edit both in parallel.

### Adversarial-first ordering (mandatory)

For any NEW entity at conviction RESEARCH/WATCHLIST/BUY with sizing > 0%, OR
any flip from AVOID → RESEARCH/WATCHLIST/BUY:

1. **`/disqualify TICKER`** first — Phase 1 kill-switch sweep. Produces a
   `disqualification_sweep:` frontmatter block (CLEAN / MIXED / FLAGGED) that
   `pretool-disqualification-required-gate.py` requires before any deployment
   language ships.
2. Primary-source verification — SEC EDGAR direct (not aggregators), foreign
   regulator equivalent (EDINET / SEDAR+ / RNS / DART / MOPS / KRX).
3. Bull thesis writing — only after 1 and 2.

Reversing this order is the documented 2026-05-23 failure mode: ATOM / EOS.AX /
IQE.L basket — 3 of 4 names had load-bearing problems that surfaced only on
round 4 because the bull thesis was written first.

For sizing UP an existing position at `sizing_pct ≤ 1.0%`: run
**`/confirm TICKER`** — symmetric upside sweep. Produces a `confirmation_sweep:`
block that `pretool-upside-trigger-gate.py` consumes. Documented under-exposure
failures (AAOI / AMD / MU / NBIS / HIMS) traced to skipping this phase.

### Before material ticker work

Run or verify the repo-local evidence setup:

```bash
uv run python3 tools/onboard_ticker.py TICKER
uvx --with edgartools --with markdownify python3 tools/build_entity_dossier.py TICKER
```

Check `.scratch/onboarding/<TICKER>/` for:

- `dilution.md`
- `litigation.md`
- `auditor.md`

For non-trivial BUY / HOLD / AVOID workups, include or refresh:

- `## Historical Dilution Pattern`
- `## Litigation History`
- `## Auditor`

If the bundle is missing, regenerate with `tools/onboard_ticker.py`. This is
the AAOI lesson: current-cycle dilution alone missed the longer refi,
litigation, and auditor risk pattern.

### Active intel decision schema

Follow the live repo docs, not this skill, for exact schema:

- `docs/entity-evaluation-checklist.md`
- `.claude/rules/conviction-template.md`
- `.claude/rules/investments.md`

The current pattern includes:

- `ai_relationship` classification.
- `conviction`, `trade_stance`, `sizing_pct`, `last_reviewed`.
- `forward_signal` for BUY compounder / bottleneck-rentier names.
- `benchmark_expression` for BUYs and trade-stance demotions.
- `anchor_customer_capex_trajectory` for supplier-class names with named
  anchor customers (HLIT 2026-05-23 — supplier "AI capex cycle" was
  contradicted by Comcast/Charter buyer-side capex peak).
- Evidence boxes: primary-source mechanism, falsifier date, edge pairing,
  best-expression route, liquidity, and adversarial review when size matters.
- Structured conviction-journal transition blocks for conviction or
  `trade_stance` changes.

Do not revive archived score math: no `edge_score`, `asymmetry_score`,
`convexity_score`, Kelly sizing, Brier sizing, automatic score-to-size caps,
probability-weighted scenario tables, or `E[24mo]` computation from
`[ESTIMATED]` inputs. The `pretool-archived-score-field-gate.py` hook blocks
revivals; `pretool-evidence-quality-gate.py` blocks the math.

### Source-grade ontology (two-axis)

For any third-party analyst / Twitter / Substack / podcast / newsletter
citation that propagates to an entity file, use the two-axis form:

```
[citation_id=<source_slug>, artifact=<A1-F6>, claim=<A1-F6>]
```

- `artifact` = source proximity (we have the recording / filing)
- `claim` = epistemic weight of the assertion in the source
  - `A1` primary fact about speaker's own knowledge
  - `C3` forward forecast / analyst projection (default for third-party
    forecasts until independently corroborated)
  - `C3-REFUTED` / `C3-CONTRADICTED` after primary-source fact-check fails

Single-tag `[A1]` is only acceptable for primary filings (SEC, EDINET, etc.),
reproducible DuckDB queries, or direct factual disclosure by the speaker
about their own firm. Background: 2026-05-18 Patel IltB propagation incident
— three forward forecasts tagged `[A1]` propagated to 10+ files; two later
refuted, one partial.

**Third-party forward forecasts** (Twitter/X, Substack, podcast, newsletter)
must land in `research/iltb/claim_resolution/<source>.md` with primary-source
verification BEFORE propagating to entity / theme files. Enforced by
`pretool-claim-propagation-gate.py`. See `.claude/rules/claim-propagation-workflow.md`.

### Source registry (canonical opinion-source identity)

Every named opinion source — 13F filers, Twitter accounts, Substack authors,
analyst firms, newsletters, conference pitchers, podcast hosts — routes
through `analysis/sources/source_registry.csv` (canonical 2026-05-24).

- New entries default to `epistemic_tier=3` (uncalibrated context-only). Do
  NOT assign tier 1 or 2 from narrative prior; promotion requires empirical
  backtest CSV at `analysis/sources/track_record/<class>/<source_id>.csv` +
  a grading-log entry summarizing N / hit rate / alpha.
- Use the CRUD library, not direct CSV edits:

```python
from tools.source_registry import SourceRow, add_source, update_grading

add_source(SourceRow(source_id="...", source_class="13f_filer", ...),
           evidence_summary="...", session_id="...")
```

- `pretool-source-registry-gate.py` enforces schema + audit-trail discipline
  (changes to grading fields require append to `source_grading_log.jsonl`).

### Intel decision questions that must be answerable

- What is the thesis, falsifier, and horizon?
- What is the asset's job: compounder, bottleneck rent, ballast, optionality,
  income, hedge, etc.?
- What is the best expression: common stock, starter, option, ETF, basket,
  waitlist, or explicit 0%?
- If the answer is no exposure, why does 0% beat a tiny starter?
- If a source event was early, specific, and tradable, what is the
  `## Source Conviction Disposition`?
- If a social, Substack, newsletter, or source-account claim is load-bearing,
  what is the `## Source Chain / Admission Check`?
- If the next proof event is earnings, customer acceptance, capacity
  energization, regulatory decision, or first revenue conversion, is it an
  entry gate or only a scale gate?
- If the user owns a large winner, is there a written trim/re-underwrite
  trigger before the next guidance or earnings reset?
- For supplier-class names: what is the named anchor customer's most recent
  capex guide direction (`peak | accelerating | flat | declining | mixed`)
  and 2026 envelope? (HLIT 2026-05-23 — buyer-side capex IS the demand
  denominator for equipment suppliers.)
- For "international / ROW diversification" claims: which axis does the
  filer's disclosure use (customer-count vs geographic-revenue vs reporting-
  segment)? Quote the actual definition before propagating. (HLIT 2026-05-23
  — "ROW +78%" was customer-taxonomy, not geographic.)

When an entity miss reveals a missing search prompt or checklist question, add
or update the prompt/checklist replay surfaces:

- `analysis/evals/prompt_checklist_registry.yaml`
- `tools/prompt_checklist_replay.py`
- `docs/prompts/upstream_search_prompts.md`

For Intel public-company work sourced from X/Twitter, Reddit, Substack,
newsletters, or named source accounts, entity files must include:

```markdown
## Source Chain / Admission Check

- source_claim_id: <stable local/source id>
- source_account_outcome: <starter|scale gate|entry gate|waitlist|avoid|re-underwrite>
- resolving evidence route: <10-K/10-Q/8-K, transcript, price artifact, DuckDB query, etc.>
```

The repo hook `.claude/hooks/pretool-source-chain-admission-gate.py` blocks
social/newsletter-driven entity writes that omit this section or its required
fields.

For misses or near-misses, append the durable admission-failure row with
`tools/append_admission_failure.py` (see usage below in Tooling section).

### Failure-mode replay surface

The hook fleet enforces these on Write/Edit to `analysis/entities/*.md`.
Read this list before dispatching a workup — it saves a round-trip per BLOCK.

**Before any entity write, run the gauntlet in ONE pass** instead of discovering
blocks one Write at a time (the 2026-06-01 5-bounce session). Draft to a temp
file, then:

```bash
uvx --with pyyaml python3 tools/preflight_entity_write.py \
    --file analysis/entities/TICKER.md --content-file /tmp/draft_TICKER.md
```

It auto-discovers and runs every live gate below from `settings.json` (so it can
never drift from the fleet) and returns the complete missing-list. Exit 0 =
clears the gauntlet. See `docs/entity-write-gauntlet.md`.

| Failure mode | Triggering incident | Hook / rule | What the file must include |
|---|---|---|---|
| Bull thesis before adversarial sweep | ATOM/EOS.AX/IQE.L 2026-05-23 | `pretool-disqualification-required-gate.py` | `disqualification_sweep:` frontmatter block |
| WATCHLIST as turn-budget fallback | ALAB 2026-05-10 (+48% in 14d) | `pretool-watchlist-completeness-gate.py` + `buy-workup-terminal-state.md` | `## Workup Completeness` attest OR convert to RESEARCH with `## P0 Fetches Queued` |
| One-sided downside-only WATCHLIST trigger | ARM 2026-05-07 (+25.7% in 15d); ALAB/ASTS/RKLB/PL cohort (+22–64% in 14d, 2026-05-24) | `pretool-asymmetric-falsifier-gate.py` — **BLOCK** mode as of 2026-05-24 (was WARN); subagent prompts must state this so the bidirectional falsifier is treated as required, not optional | `## Bidirectional Falsifier` with both downside re-entry AND upside escalation |
| Stale conviction vs tape | 21-name cohort 2026-05-24 (+15–42%) | `/divergence-update` skill + `tools/coverage_gap_scanner.py` (divergence scan) — no pretool hook | `## Conviction Divergence Acknowledged` section |
| AVOID/WATCHLIST without observable falsifier | (many) | `pretool-falsifier-required-gate.py` | concrete price / % / event / ISO date in falsifier section |
| Sycophantic same-session conviction flip | (multiple) | `pretool-unevidenced-flip-gate.py` (persisted unevidenced flips); in-chat same-session flips are instruction-level only per `.claude/rules/stance-stability.md` (`pretool-conviction-flip-gate.py` was never built — archived) | `## Stable View` section on second flip |
| Probability-weighted scenario tables / `E[X]` math | SNDK folder 2026-05-25, ARM 2026-05-22 | `pretool-evidence-quality-gate.py` | prose scenarios + bidirectional falsifier + plain operator call |
| AI-compute bear thesis with no denominator mechanism | ARM 2026-05-22 | instruction-level (the `pretool-ai-compute-bear-mechanism-gate.py` shadow hook was removed; discipline now lives in the workup, not a gate) | named denominator attack (agent ROI plateau, energy ceiling, named customer substitution, regulatory cap, etc.) |
| Supplier-class file with no anchor-customer capex check | HLIT 2026-05-23 | `pretool-anchor-customer-capex-trajectory-gate.py` | `anchor_customer_capex_trajectory:` frontmatter (or override section) |
| "ROW / international" claim without axis-definition quote | HLIT 2026-05-23 | `pretool-taxonomy-axis-gate.py` | inline-quote of filer's actual axis definition |
| Third-party analyst forecast cited as `[A1]` | Patel IltB 2026-05-18 | `pretool-claim-propagation-gate.py` | `research/iltb/claim_resolution/<source>.md` first; two-axis citation form |
| `[B2]` aggregator in primary-source-mechanism evidence box | (2026-05-10 finding #5) | `pretool-aggregator-in-load-bearing-section.py` | `[A1]` SEC / foreign-regulator filing for load-bearing claims |
| Stale entity vs recent news | META 2026-05-15 layoff miss | `pretool-recent-news-scan-gate.py` | `## Recent News Scan` section with 30d WebSearch/Perplexity output — never copy a prior scan section verbatim; always write a fresh scan dated today (NVDA 2026-05-24 stale-date recurrence) |
| Missing source-grade tag on factual claim line | (recurring) | `pretool-source-grade-line-linter.py` (shadow, 51 fires/14d) | inline `[A1]`-`[F6]` or `[DATA]` on factual claims |
| Live blocker (Form 4 / CFPB / dilution / covenant) gone stale | (recurring) | `pretool-live-blocker-freshness-gate.py` | refresh evidence or remove the "live blocker" framing |
| Falsifier trigger HIT without disposition | (recurring) | `pretool-falsifier-disposition-gate.py` | same-file `## Disposition` section explaining hold/flip/exit |
| Material adverse risk surfaced without conviction review | (recurring) | `pretool-material-risk-conviction-review.py` | `## Conviction Disposition` block addressing the new risk |
| Near-term tape-risk silent on high-convexity no-buy | (recurring) | `pretool-near-term-tape-risk-gate.py` | `## Near-Term Tape Risk` section |
| Insurer/bank FCF cited like product company | (recurring) | (instruction-level) | use owner earnings, not FCF, for financial-sector names |
| PEG / forward-P/E on cyclical | (recurring) | (instruction-level) | through-cycle EPS / P/B / EV-Sales for cyclicals |
| Stale analyst target from corporate action | POWL 2026-04-26 (3:1 split) | `data-freshness-corporate-actions.md` | refreshed target with cache-date inline citation |

#### Known regex collisions and full-file scan behavior

`pretool-disqualification-required-gate.py` `DEPLOYMENT_INTENT_RE` historically
matched the bare word `starter`, colliding with the Near-Term Tape Risk
route-label "Starter / option / waitlist / 0% route:" (2026-05-24 finding).
**FIXED:** the regex now uses `starter(?!\s*[/,(])`, which excludes the
route-label form, AND the gate bypasses pure-coverage frontmatter
(`sizing_pct: 0` + `trade_stance ∈ {TRACKING, NO_POSITION}`). The "Starter /
…" label form no longer trips it, so the "Exposure route" rename workaround is
no longer required (the rename remains harmless). Still avoid the literal
phrase "starter position" / "starter add" in a NO_POSITION file — those forms
(no `/,(` after `starter`) still match by design.

The gate scans the **full post-edit content**, not just the diff. A pre-
existing "starter" or "deploy" token elsewhere in the file blocks unrelated
section appends (SMTC 2026-05-24). When dispatching a subagent to append to
an existing file, instruct it: if `disqualification_sweep:` frontmatter is
absent and any of `{starter, deploy, size into, monday open}` appears
anywhere in the file body, run `/disqualify TICKER` first or rename the
pre-existing tokens before attempting any Edit.

### Divergence-acknowledgment pattern (5/24 standard)

When a coverage-gap-scanner divergence flag hits an entity file and the
operator decides to hold conviction, the acknowledgment commit format
codified across the 21-name 2026-05-24 cohort is:

```
[entities] TKR — divergence ack +X.X%, <CONVICTION> held; <one-line finding>
```

The file gains four sections (in addition to existing content):

1. `## Conviction Divergence Acknowledged YYYY-MM-DD`
2. `## Workup Completeness YYYY-MM-DD` (attest load-bearing primary docs were fetched)
3. `## Bidirectional Falsifier YYYY-MM-DD` (downside re-entry + upside escalation triggers)
4. `## P0 Fetches Queued` (ONLY if turn budget exhausted mid-fetch; non-empty list forbids WATCHLIST per `buy-workup-terminal-state.md`)

`pretool-disqualification-required-gate.py` has an exemption (commit
`f6439ed1` 2026-05-24) for divergence-ack rework on entities with
`sizing_pct=0` AND `trade_stance ∈ {TRACKING, NO_POSITION}` — the body-text
"starter" / "deploy" scan skips when frontmatter confirms no deployment.

## Tooling and APIs

Repo-local tools that touch entity files. Prefer these over ad-hoc scripts;
they handle path discovery, frontmatter, and provenance correctly.

| Tool | Purpose |
|---|---|
| `tools/onboard_ticker.py TICKER` | Initial dossier setup: fundamentals, dilution, litigation, auditor under `.scratch/onboarding/<TICKER>/` |
| `tools/build_entity_dossier.py TICKER` | Parse 10-K/10-Q/8-Ks into `analysis/dossiers/TICKER/filings/` via edgartools |
| `tools/build_entity_file.py` | Scaffold a new entity file with current frontmatter contract |
| `tools/onboard_from_primary_source.py --source themes --execute` | Auto-extract foreign tickers from substacks/themes; pipes through `onboard_ticker.py` (closes ABF/CCL +471% foreign-listing coverage gap) |
| `tools/source_registry.py` | CRUD library for `analysis/sources/source_registry.csv` (atomic registry + grading-log appends) |
| `tools/append_admission_failure.py` | Durable miss/near-miss row for admission-failure log |
| `tools/coverage_gap_scanner.py` | Daily cron (6 scans): boom-miss, rocket-exit, theme-mention gap, divergence, foreign-listing, cycle-inflection |
| `tools/high_convexity_replay_lanes.py` | Validate `analysis/high_convexity_replay_lanes.csv` (rejected-name anti-portfolio, survival options, weird-enabler lanes) |

### Skills that gate or assist entity work

- **`/disqualify TICKER`** — adversarial Phase 1 (mandatory before BUY/RESEARCH/WATCHLIST with sizing > 0). Confirm the sweep includes named short-seller archives (Muddy Waters, Grizzly, Hindenburg, SCAS, Bonitas, Citron, Spruce Point, Wolfpack, J Capital, Culper); IQE.L/EOS.AX 2026-05-23 — Grizzly short report + ASIC penalty + going-concern note surfaced only on Round 4 because the first-pass sweep skipped the short-seller stream
- **`/confirm TICKER`** — symmetric upside Phase 1 (before sizing up at ≤ 1.0%)
- **`/asset-decision TICKER`** — full 7-phase orchestrator wrapping the above
- **`/social-thread`** — pasted social/substack/reddit pipeline (8 steps incl. generator extraction)
- **`/ingest-article`** — pasted trade-press pipeline (6 steps)
- **`/thesis-check TICKER`** — adversarial stress-test of existing thesis vs local datasets
- **`/forecast TICKER`** — 3-layer forecast packet (breakeven prob, reference class, options-implied, prediction markets)
- **`/standalone-asset TICKER`** — suppress portfolio anchoring for fresh-look evaluation
- **`/x-api`** — pay-per-use X/Twitter v2 client (probe / pull, $100/mo cap). Use for monitoring curated finance accounts; outputs digest with ticker-coverage delta against `analysis/entities/`. Required env: `X_API_BEARER_TOKEN`. Pattern: `python3 ~/Projects/skills/x-api/scripts/pull.py --config .claude/config/x_curated_accounts.json --tracked-tickers-file /tmp/intel_tracked.txt --themes-dir analysis/themes`.

### MCP servers (`.mcp.json`)

- **`duckdb`** — read-only SQL against `intel.duckdb` (~590 views). Always
  `DESCRIBE table_name` before first query — column landmines exist even in
  documented tables.
- **`fmp`** — real-time quotes, profiles, financials. Rate limit: 4 quotes
  then 402. Use `company_profiles` view (Yahoo Finance snapshot) for fundamentals;
  reserve `get_quote` for one-at-a-time intraday checks.
- **`intel-theses`** — query the thesis graph at `intel/indexed/theses.duckdb`.
  Tools include `entry_readiness(file_path)` (12-axis Closure FSM),
  `monitoring_state(file_path)` (6-axis), `evidence_for_thesis`,
  `contradictions`, `stale_theses`, `belief_history`. Read-only.
- **`intelligence`** — `resolve_entity`, `search_entities`, `find_connections`,
  `get_dossier`, `flag_anomalies`.
- **`corpus`** — local scientific corpus store (`corpus_lookup`,
  `corpus_graph_query`, `corpus_annotations_query`, `corpus_ingest`,
  `corpus_dashboard`). Read-only for annotations. Attestation is automatic:
  each repo's mutation gateway emits to corpus via a transactional outbox when
  a verdict/cert/contradiction is written — no agent ritual. (The old v1
  `record_verdict` + `corpus_attest` two-call flow is retired.)
- **`research`** — Semantic Scholar paper discovery, claim verification,
  preprint surveillance, deep research.
- **`brave-search` / `exa` / `perplexity`** — web search tiers. Default to
  Brave/Exa for cheap recency; Perplexity for multi-source synthesis.

### Live data discipline

- **Live price queries:** ALWAYS query FMP `get_quote` first → Stooq fallback
  on 402. Never quote `datasets/prices/*.csv` as if current — it's overnight
  end-of-day. State the timestamp on every quote.
- **Mcap from `profiles.csv`:** stale by fetch date, not spot-current. Re-
  derive `mcap = spot × shares_outstanding` for high-stakes paths.
- **FINRA short interest:** `high_short_interest` view is Finviz top-2400
  scrape only. For our universe use `read_csv('datasets/finra_short_interest/shrt*.csv', delim='|', union_by_name=true)`.
- **Substack body fetch:** `substack.sid` is HttpOnly — run
  `tools/substack_auth_diagnostic.py <pub> --probe-slug <real-paywall-post>`
  before scraping. If wrong account, use Chrome MCP `fetch('/api/v1/posts/<slug>')`
  with `credentials: 'include'` from page context; strip image/iframe URLs
  before returning across MCP boundary (auth tokens trigger the filter).
- **Revenue claims for biotech with collab accounting / insurers / banks /
  newly-listed:** `profiles.csv` is structurally unreliable. Cite the 10-Q
  income-statement line directly with SEC accession.

## Subagent dispatch contract for entity workups

When dispatching researcher / general-purpose subagents to build or refresh an
entity file, include the **skeleton-first contract** in the dispatch prompt
(per `.claude/rules/subagent-skeleton-first.md` — LITE 2026-05-15 failure
mode: agent found primary fact but exited without writing file):

```
SKELETON-FIRST CONTRACT:
1. Within first 3-5 tool calls: Write the file skeleton (frontmatter only +
   empty sections). Use Write tool. Don't research first.
2. Append findings via Edit as research returns.
3. At 70% of turn budget, STOP researching and write final synthesis.
4. Return the file path. Not contents. Not a summary. Path.
```

For divergence-ack rework specifically, the four-section contract is also
required (Conviction Divergence Acknowledged + Workup Completeness +
Bidirectional Falsifier + P0 Fetches Queued).

For BUY-workup specifically, the **terminal-state contract** binds (per
`.claude/rules/buy-workup-terminal-state.md`): if any load-bearing primary
doc is "located but not fetched" within turn budget, terminal state is
RESEARCH with `## P0 Fetches Queued`, NOT WATCHLIST.

## Selve / General Entity Files

Use `docs/entities/<category>/<entity-name>.md` unless local docs say
otherwise.

Required frontmatter for search elevation:

```yaml
---
title: "Entity Name - Short Description"
date: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
tags: category, entity-type, topic1, topic2, key-person-name
summary: "One-line summary covering the entity's domain vocabulary"
---
```

Tags should include search vocabulary, not only the entity type. Missing tags
make entities invisible in retrieval.

Health/genomics confidence tiers:

- **T3:** lab-confirmed, guideline-backed, database-verified.
- **T2:** multiple independent sources agree.
- **T1:** single source confirmed.
- **T0:** claimed but unchecked; mark `[UNVERIFIED]`.

## Generic Template

```markdown
# Entity Name

> One-line description. Category: <type>.

## Key Facts

| Fact | Source | Date Verified |
|------|--------|---------------|
| ... | DOI/URL/database ID | YYYY-MM-DD |

## Narrative Summary

Sourced prose. Every paragraph ends with citations.

## Open Questions

- What remains unresolved?
- What would change the assessment?

## Cross-References

- Related: [entity](../category/entity.md)

## Changelog

- YYYY-MM-DD: Created with initial findings from [source].
- YYYY-MM-DD: [CORRECTED] claim X based on [new source].
```

## Git

- Do not mix entity edits with unrelated changes.
- Follow the current repo's commit convention. If none exists, use:
  `entities/<category>/<name>: <what changed>`.
- For intel divergence-ack commits the standard subject is:
  `[entities] TKR — divergence ack +X.X%, <CONVICTION> held; <one-line finding>`.
- For commits that delete or merge folder/flat splits, include an
  `Evidence:` trailer naming the stale-stub finding and active-maintenance
  contrast.
