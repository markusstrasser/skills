---
name: strchive-skill
description: STRchive — curated catalog of disease-associated short tandem repeat (STR) loci with motif, inheritance, pathogenic thresholds, and gnomAD allele frequencies. Use when interpreting ExpansionHunter / TRGT / LongTR output against known repeat-expansion disease loci.
---

## Operating rules
- Use `scripts/strchive.py`.
- STRchive ships a curated JSON (one entry per disease-locus) on GitHub. There is no dynamic REST API; this skill fetches the JSON (cached per session) and filters locally.
- Entries carry: motif, reference coordinates (hg19 + hg38), gene symbol, inheritance, pathogenic / benign / intermediate ranges, gnomAD allele-frequency stats, OMIM disease links, and recommended caller formats (TRGT / ExpansionHunter / LongTR).
- Use STRchive as the **first lookup** for "is locus X pathogenic?" before ClinVar, since ClinVar coverage of STR loci is sparse.
- Do NOT use STRchive for novel STR discovery — it is a curated disease catalog, not a population scan.

## Execution behavior
- `mode=list`: dump all loci (compacted to disease + gene + motif + inheritance).
- `mode=gene`: filter by gene symbol.
- `mode=disease`: substring match on disease label.
- `mode=region`: locus overlap by `chrom` + `start` + `stop` (hg38).

## Input
- One JSON object on stdin.
- Required: `mode` ∈ {`list`, `gene`, `disease`, `region`}.
- `mode=gene`: `gene` (HGNC symbol).
- `mode=disease`: `disease` (substring; case-insensitive).
- `mode=region`: `chrom`, `start`, `stop` (hg38).
- Optional: `source_url` (override the GitHub raw URL), `max_items`, `timeout_sec`, `save_raw`, `raw_output_path`.

## Output
- Success: `{ok: true, source: "strchive", mode, count, summary, raw_output_path?}`.
- Failure: `{ok: false, error: {code, message}}`.

## Execution
```bash
echo '{"mode":"gene","gene":"HTT"}'  | python3 scripts/strchive.py
echo '{"mode":"disease","disease":"ataxia"}' | python3 scripts/strchive.py
echo '{"mode":"region","chrom":"chr4","start":3074000,"stop":3076000}' | python3 scripts/strchive.py
```

## References
- Repo: https://github.com/dashnowlab/STRchive
- Default data URL: `https://raw.githubusercontent.com/dashnowlab/STRchive/main/data/STRchive-loci.json`
