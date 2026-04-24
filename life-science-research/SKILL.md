---
name: life-science-research
description: Route biomedical questions across ClinVar, gnomAD, Ensembl, GWAS, GTEx, Open Targets, ChEMBL, PharmGKB, UniProt, AlphaFold, PDB, PubMed, ClinicalTrials, bioRxiv, and related public APIs. Use for source lookup or multi-lane evidence synthesis.
argument-hint: "[question] [--lane genetics|variant|expression|pathway|structure|chemistry|clinical|literature|omics] [--personal]"
effort: high
---

# Life-Science Research Router

This is a portable routing skill for Claude Code, Codex, Gemini CLI, and other
agents. It distills the useful pattern from Codex's Life Science Research plugin:
a small router plus many source-specific lookup recipes. Do not treat it as a
single monolithic "biomed answer engine."

Concrete source-specific skills are nested under `sources/` inside this skill.
Do not expose them all as top-level skills; that blows the Claude Code skill
description budget. When a narrow source lookup matches the request, open only
that source's `sources/<source-skill>/SKILL.md` and run its local helper script.

## Lessons From Codex's Life Science Plugin

Copy the architecture, not the package.

What is worth copying:

- **Router first:** classify the question into 1-3 evidence lanes before
  searching.
- **Normalize entities before evidence:** gene/protein, variant, disease,
  compound, pathway, and dataset identifiers decide which source is valid.
- **Thin source recipes:** each database wrapper is small, explicit, and biased
  toward compact JSON summaries rather than broad dumps.
- **Small windows by default:** start with 5-10 records, then expand only after
  seeing signal.
- **Raw payload escape hatch:** save large raw responses to a file/path when
  needed; do not paste source dumps into the agent context.
- **Freshness discipline:** re-run important external lookups in long sessions
  instead of trusting stale context.
- **Output contract:** synthesize around the user's question, then separate
  database facts, literature claims, inference, caveats, and next checks.

What not to copy:

- 50 source wrappers as a default local dependency.
- Plugin-specific tool names in portable instructions.
- A monolithic answer engine that hides which sources were checked.
- Advisory behavior buried behind an MCP call that agents may forget to make.

## Agent-Infra Placement Rule

Use the lowest durable layer that solves the problem:

| Need | Best Home | Reason |
|---|---|---|
| Domain routing and source choice | Shared skill | Skills are portable and use progressive disclosure. |
| Repeated structured lookup against one source | MCP tool or CLI wrapper | Gives typed inputs, compact outputs, and testable failures. |
| Cross-project advisory knowledge | agent-infra MCP search or docs | Low-frequency reference material should stay on demand. |
| Must-not-violate behavior | Hook / always-loaded rule | Agents cannot reliably remember to query advisory tools. |
| Cross-session learning by a specialized worker | Custom subagent | Skills do not keep persistent memory; subagents can. |
| External distribution bundle | Plugin | Distribution mechanism, not capability; skip for local use. |

For this skill, the right shape is: one visible shared router plus nested source
wrappers. Do not expose every source wrapper as a top-level skill unless a
specific agent cannot reliably discover the router and the benefit is measured.

## Core Rule

Start by deciding the evidence lane, normalize entities, then call the smallest
set of authoritative sources that can answer the question. Synthesize the answer
around the user's question, not around the tools.

For personal health/genomics projects, local curated state wins over fresh web
search:

1. repo-owned entity pages, clinical maps, claim stores, and WGS artifacts
2. typed MCP / CLI views over those artifacts
3. external biomedical databases
4. literature and web search

Old AI-chat recall is not evidence unless confirmed by a stronger source.

## Routing Lanes

Pick 1-3 lanes. Expanding beyond that is usually a landscape review.

| Lane | Use When | First Sources |
|---|---|---|
| Genetics / variant interpretation | rsID, HGVS, ClinVar, allele frequency, ACMG style questions | local WGS/claim store if available; ClinVar; gnomAD; Ensembl; BioMCP |
| Locus-to-gene | GWAS locus, credible set, noncoding variant mechanism | GWAS Catalog; Open Targets; GTEx/eQTL Catalogue; locus-to-gene mapper |
| Expression / tissue context | tissue, cell type, disease expression, protein localization | GTEx; Human Protein Atlas; Bgee; CELLxGENE; ENCODE |
| Pathway / network biology | mechanism, pathway membership, protein interaction | Reactome; STRING; QuickGO; UniProt |
| Structure / protein mechanism | domain, structure, mutation mechanism, PDB evidence | UniProt; AlphaFold; RCSB PDB |
| Chemistry / pharmacology | compound, target, binding, mechanism, PGx | ChEMBL; BindingDB; PubChem; PharmGKB; Open Targets drug info |
| Clinical / translational | trials, cancer variant actionability, disease-target evidence | ClinicalTrials.gov; cBioPortal; CIViC; Open Targets |
| Literature / preprints / datasets | paper discovery, preprints, PMC, study accessions | PubMed/Entrez; PMC; bioRxiv/medRxiv; BioStudies/ArrayExpress; PRIDE; MetaboLights |
| Omics / microbiome | proteomics, metabolomics, microbiome public studies | PRIDE; ProteomeXchange; MetaboLights; MGnify |

## Entity Normalization

Normalize before deep retrieval.

| Entity | Normalize With |
|---|---|
| Gene/protein | HGNC symbol, Ensembl ID, NCBI Gene, UniProt accession |
| Variant | rsID plus GRCh37/GRCh38 coordinate, ref/alt, transcript/HGVS when relevant |
| Disease/phenotype | EFO, HPO, MONDO/OMIM/Orphanet, ICD only for billing/clinical labels |
| Drug/compound | RxNorm for clinical drugs, ChEMBL/PubChem/ChEBI for chemistry |
| Pathway/function | Reactome stable ID, GO term, EC/Rhea where enzymatic |
| Dataset | accession and repository, not just study title |

If identifiers disagree, stop and resolve the conflict before interpretation.

## Tool Preference By Agent Surface

Use whichever surface exists in the current agent. Do not assume all tools are
available everywhere.

| Need | Preferred Surface | Fallback |
|---|---|---|
| Personal corpus / current beliefs | project MCP claim store, entity pages, `./phenome search` | grep repo docs first, then semantic search |
| Personal genome interpretation | genomics-consumer MCP, stable `results/` artifacts, `gene_profile` | read clinical maps / registry files |
| Variant public annotation | BioMCP or biomedical MCP variant lookup | MyVariant.info, ClinVar, gnomAD web/API |
| PGx | PharmGKB/CPIC via MCP or BioMCP | PharmGKB, CPIC guideline/API, FDA labels |
| Literature | research MCP, scite, PubMed/PMC, paperclip where configured | PubMed + PMC + DOI landing pages |
| Broad web-grounded biomedical search | Exa, Perplexity, Brave | ordinary web search with primary-source preference |
| Cross-project agent patterns | agent-infra MCP `search` | read `~/Projects/agent-infra/research/*.md` |

When no MCP is exposed, use local CLIs or direct APIs. State the fallback in the
answer if it affects confidence.

## Source-Specific Recipes

These are request recipes, not mandatory tools.

| Source | Good First Query |
|---|---|
| ClinVar | gene or exact variant; separate star/review status from significance |
| gnomAD | exact variant with build and ref/alt; population AF before pathogenicity claims |
| Ensembl | gene/transcript/variant normalization and assembly coordinates |
| Open Targets | disease-target or target-disease evidence; distinguish genetics from literature/mining |
| GWAS Catalog | trait associations and ancestry/study context |
| GTEx / eQTL Catalogue | tissue-specific eQTLs; report tissue and variant build |
| Human Protein Atlas / Bgee | tissue expression; do not infer causality from expression alone |
| Reactome / QuickGO | pathway/function labels; verify species and evidence code where available |
| STRING | network topology; treat as interaction/context, not proof of mechanism |
| UniProt | canonical protein function, domains, isoforms, variants |
| AlphaFold / RCSB PDB | structure availability and confidence; do not overstate low-confidence regions |
| ChEMBL / BindingDB | target activity; report assay type, organism, units, and relation where available |
| PharmGKB / CPIC | clinical PGx annotations; report evidence/guideline level |
| ClinicalTrials.gov | trial existence/status; do not treat as efficacy evidence |
| cBioPortal / CIViC | cancer variant context; keep tumor type and evidence level attached |
| PubMed / PMC / bioRxiv | discovery and full-text support; preprints are provisional |

Local source skill paths:

- `sources/alphafold-skill`
- `sources/bgee-skill`
- `sources/bindingdb-skill`
- `sources/biobankjapan-phewas-skill`
- `sources/biorxiv-skill`
- `sources/biostudies-arrayexpress-skill`
- `sources/cbioportal-skill`
- `sources/cellxgene-skill`
- `sources/chebi-skill`
- `sources/chembl-skill`
- `sources/civic-skill`
- `sources/clinicaltrials-skill`
- `sources/clinvar-variation-skill`
- `sources/efo-ontology-skill`
- `sources/encode-skill`
- `sources/ensembl-skill`
- `sources/epigraphdb-skill`
- `sources/eqtl-catalogue-skill`
- `sources/eva-skill`
- `sources/finngen-phewas-skill`
- `sources/genebass-gene-burden-skill`
- `sources/gnomad-graphql-skill`
- `sources/gtex-eqtl-skill`
- `sources/gwas-catalog-skill`
- `sources/hmdb-skill`
- `sources/human-protein-atlas-skill`
- `sources/ipd-skill`
- `sources/locus-to-gene-mapper-skill`
- `sources/metabolights-skill`
- `sources/mgnify-skill`
- `sources/ncbi-blast-skill`
- `sources/ncbi-clinicaltables-skill`
- `sources/ncbi-datasets-skill`
- `sources/ncbi-entrez-skill`
- `sources/ncbi-pmc-skill`
- `sources/opentargets-skill`
- `sources/pharmgkb-skill`
- `sources/pride-skill`
- `sources/proteomexchange-skill`
- `sources/pubchem-pug-skill`
- `sources/quickgo-skill`
- `sources/rcsb-pdb-skill`
- `sources/reactome-skill`
- `sources/research-router-skill`
- `sources/rhea-skill`
- `sources/rnacentral-skill`
- `sources/string-skill`
- `sources/tpmi-phewas-skill`
- `sources/ukb-topmed-phewas-skill`
- `sources/uniprot-skill`

## Execution Discipline

1. Write the retrieval plan in one short paragraph if the task is broad.
2. Prefer direct lookups before expensive multi-step chains.
3. Use small result windows first: 5-10 records, then expand only if needed.
4. Save or cite raw payload paths when results are large; do not paste dumps.
5. Re-run important external lookups in long sessions instead of trusting old context.
6. Separate database facts, literature findings, inference, and advice.
7. Attach caveats for ancestry, cohort, tissue, assay, model organism, and study design.
8. Never turn mechanistic plausibility into treatment advice.

## Parallelization

Parallelize only independent lanes. Keep entity normalization, scope decisions,
conflict resolution, and final synthesis with the coordinating agent.

Good parallel splits:

- genetics vs expression vs structure vs pharmacology for one gene
- multiple variants using the same output schema
- literature review vs database annotation
- clinical trials vs molecular mechanism

Bad splits:

- one narrow lookup
- tasks where later queries depend on unresolved identifiers
- broad fan-out before deciding what entity is being studied

Each worker should return:

- what it checked
- key findings
- caveats
- tools/sources used
- whether the result is database fact, literature claim, or inference

## Output Contract

Default answer shape:

1. direct answer or working conclusion
2. evidence by lane
3. conflicts or missing evidence
4. next useful lookup or validation step

For personal health/genomics answers, add:

- what local artifact was used
- whether external evidence updates or weakens the local state
- whether the conclusion is action-grade, research-only, or null

## When To Stop

Stop early when:

- identifier normalization fails
- local curated docs already contain a newer reviewed answer
- external evidence is only associative and the user's question asks for causality
- the remaining sources are lower tier than what has already been checked
- the likely next step is a repo-owned contract update, not more searching
