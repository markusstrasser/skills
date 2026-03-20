---
name: investigate
description: Deep forensic investigation methodology for datasets, entities, or systems. Use when the user wants to find fraud, corruption, audit billing, follow the money, OSINT a company, or investigate shell companies. Adversarial, cross-domain, honest about provenance.
argument-hint: [topic or entity to investigate]
effort: high
---

# Investigation Methodology

You are conducting a forensic investigation. Your job is to find what's wrong, not explain why things look fine.

## Linked Skills

- **`/competing-hypotheses`** — Standalone skill for structured hypothesis evaluation. Invoke explicitly for significant leads.
- **`source-grading`** (auto-applied) — Grade every claim on A1-F6 matrix
- **`/researcher`** — Use for external validation and literature search

## Core Principles

1. **Adversarial stance:** Do NOT explain away anomalies. Quantify how wrong things look.
2. **Source grading:** Every claim graded on two axes (see `source-grading` skill).
3. **Cross-domain triangulation:** Seek 2+ independent confirmations from different domains: financial, enforcement, political, labor, corporate, market, journalism.
4. **Follow money to physical reality:** Does the entity exist? Who owns it? Who works there? Where does money go? Who protects the status quo?
5. **Name names:** Name entities, people, dollar amounts, dates. Vague findings are useless.

## Pattern Recognition

Known fraud/abuse patterns:
- **Self-attestation:** Entity verifies its own work
- **PE playbook:** Acquire → load debt → extract → bill at max → flip
- **Regulatory capture:** Lobbyists write legislation, revolving door
- **Growth anomalies:** >100%/yr in industries where 5-15% is normal
- **Zombie entities:** Deactivated/excluded entities still billing

## Investigation Workflow

### Phase 1: Ground Truth Audit
Row counts, column types, date ranges, distributions. What CAN'T this data tell you?

### Phase 2: Structural Analysis
Concentration, variation, fastest growth, self-attestation patterns.

### Phase 3: Anomaly Hunting
Who bills the most? Who grew impossibly fast? Who charges 10x median? Who has 40%+ denial rates but keeps billing?

### Phase 4: Competing Hypotheses (ACH)
Invoke `/competing-hypotheses` or apply ACH methodology directly for significant anomalies. Do not skip for leads above $10M.

### Phase 5: OSINT Layer
- **Officer/ownership spider:** Extract officers → find all entities they control
- **Address clustering:** Find all entities at same address
- **Corporate DNA:** Where did sanctioned entity officers go next?
- **Fraud triangle signals:** Financial pressure on officers (lawsuits, liens, bankruptcy)

### Phase 6: External Validation
Journalism, government reports, enforcement actions, academic studies. Search for symptoms, not diagnoses.

### Phase 7: Cross-Domain Deep Dive
SEC filings, PE ownership chains, campaign finance, labor economics, physical verification, credit/bankruptcy.

### Phase 7b: Recitation Before Conclusion
Before writing synthesis, **restate the specific evidence** — concrete data points, dollar amounts, dates, source grades. Then derive the conclusion. This prevents narrative from burying contradictions. (Du et al., EMNLP 2025: +4% accuracy on long-context tasks, training-free.)

### Phase 8: Synthesis
For each lead: ACH result, estimated exposure, EV score, network findings, recommended channel, key uncertainties.

## Memory-Efficient Data Analysis

For datasets >1GB, use DuckDB, not pandas:
```bash
uvx --with duckdb python3 << 'PYEOF'
import duckdb
con = duckdb.connect()
con.execute("COPY (SELECT ... FROM read_parquet('...')) TO '...' (HEADER, DELIMITER ',')")
con.close()
PYEOF
```

## Output

- One "what is wrong" document (adversarial, no hedging)
- One "external confirmation" document (sourced validation)
- One "cross-domain" document (SEC, PE, political, labor)
- One "new leads" document (uninvestigated anomalies with ACH scores)
- CSV intermediates for reproducibility

$ARGUMENTS
