---
name: life-science-research
description: Biomedical source routing — ClinVar, gnomAD, Ensembl, GTEx, OpenTargets, ChEMBL, PharmGKB, UniProt, PDB, PubMed, bioRxiv. Source lookup + multi-lane synthesis.
argument-hint: "[question] [--lane genetics|variant|expression|pathway|structure|chemistry|clinical|literature|omics] [--personal]"
effort: high
---

# Life-Science Research Router

This is a portable routing skill for Claude Code, Codex, Gemini CLI, and other
agents. It distills the useful pattern from Codex's Life Science Research plugin:
a small router plus many source-specific lookup recipes. Do not treat it as a
single monolithic "biomed answer engine."

Concrete source-specific recipes are nested under `sources/` inside this skill.
Each is a directory with an `INSTRUCTIONS.md` (renamed from SKILL.md so harness
skill-discovery does not surface all 50 as top-level skills — that blows the
skill-description budget in Claude Code and Codex). When a narrow source lookup
matches the request, open only that source's `sources/<source-skill>/INSTRUCTIONS.md`
and run its local helper script.

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

## Quick Route (start here)

Before anything else, decide which entry point fits the question shape. This
table compresses the lane + tool tables below into a single decision.

| Question shape | First move |
|---|---|
| Personal genome / variant in this user's WGS | `genomics-consumer` MCP → `gene_profile` / `variant_lookup` / `explain_finding` |
| Public variant annotation (ClinVar / gnomAD / AF) | `biomedical` MCP `variants_lookup`, `variants_clinvar`, `population_variant_frequency`; or BioMCP |
| Variant regulatory effect prediction | `biomcp get variant <id> predict` (AlphaGenome) |
| Gene → disease / panel / dosage | `biomedical` MCP `curation_*`, `panels_*`, `phenotype_*`, `targets_disease_associations` |
| Drug / PGx / mechanism / labels | `biomedical` MCP `drugs_*`, `supplements_pharmgkb_lookup`, `targets_pharmacogenetics`; PharmGKB skill |
| Pathway / interaction / GO | `biomedical` MCP `pathways_*`, `proteins_interactions`; Reactome / STRING skills |
| Structure / domain | UniProt / AlphaFold / RCSB skills |
| Locus → gene (GWAS, noncoding) | `locus-to-gene-mapper` skill; eQTL Catalogue / Open Targets |
| Structural variants / CNV / STR / MEI | dedicated SV lane below — none of the 50 source skills are SV-aware |
| Clinical trials | `biomedical` MCP `clinical_*`; ClinicalTrials.gov skill |
| Literature search | `research` MCP, scite, NCBI Entrez/PMC, bioRxiv skills — and **always check retraction status (see Output Contract)** |

Do NOT scan the full Source Index until the route above falls through.

## Biomedical MCP coverage hint

If the host agent has the `biomedical` MCP loaded, the following sources are
already wrapped — prefer the MCP tool over opening the source skill:
HPO / OMIM / Orphanet / Monarch (`phenotype_*`, `rare_disease_*`),
PanelApp (`panels_*`), ClinGen gene validity + dosage (`curation_*`),
KEGG (`pathways_kegg_*`), CPIC (folded into `supplements_pharmgkb_lookup` /
`targets_pharmacogenetics`), DGIdb (via `targets_*`), LitVar2
(`literature_variant_publications`), ISBT blood groups (`bloodgroups_*`),
GTEx eQTL (`expression_eqtl`), USDA FoodData (`nutrition_*`).
Open the per-source skill only if (a) the MCP isn't loaded, (b) the MCP
wrapper is too coarse for the question, or (c) you need a query the wrapper
doesn't expose.

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
| Genetics / variant interpretation (SNV/indel) | rsID, HGVS, ClinVar, allele frequency, ACMG style questions | local WGS/claim store if available; ClinVar; gnomAD; Ensembl; BioMCP |
| Structural variation / CNV / STR / MEI | DEL/DUP/INV/BND, repeat-expansion locus, mobile-element insertion, large CNV | gnomAD-SV v4 (GraphQL on same `gnomad.broadinstitute.org/api`, query type `structural_variant`); dbVar (NCBI Entrez); DGV (UCSC BigBed); STRchive (GitHub JSON, repeat-expansion loci); AnnotSV (web UI / local install); local `annotsv` skill for project pipeline output |
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

## Source Index

Open only the `sources/<name>/INSTRUCTIONS.md` you need. Each source has a local
helper script under `sources/<name>/scripts/`.

| Source | Covers |
|---|---|
| alphafold-skill | AlphaFold structure predictions; UniProt/sequence/annotation lookups |
| bgee-skill | Bgee expression SPARQL — healthy wild-type tissue |
| bindingdb-skill | BindingDB ligand-target binding (PDB/UniProt/similarity search) |
| biobankjapan-phewas-skill | BioBank Japan PheWAS — single variant, GRCh37 resolve |
| biorxiv-skill | bioRxiv/medRxiv preprint metadata, DOI publication linkage |
| biostudies-arrayexpress-skill | BioStudies/ArrayExpress study text search + accession |
| cbioportal-skill | cBioPortal — studies, profiles, mutations, clinical data, samples |
| cellxgene-skill | CELLxGENE Discover — single-cell collection/dataset metadata |
| chebi-skill | ChEBI 2.0 — chemical search, compound, ontology, structure |
| chembl-skill | ChEMBL — activity, molecule, target, mechanism, text-search |
| civic-skill | CIViC GraphQL — cancer variant interpretation evidence |
| clingen-allele-registry-skill | ClinGen Allele Registry — canonical allele IDs (CAids) and cross-references for variant normalization |
| clinicaltrials-skill | ClinicalTrials.gov API v2 — study search, metadata, field stats |
| clinvar-variation-skill | ClinVar + NCBI Variation — VCV/RCV/SCV/RefSNP lookups |
| dgidb-skill | DGIdb v5 — drug-gene interactions aggregated across 40+ sources (GraphQL) |
| efo-ontology-skill | EFO OLS4 — search, term lookup, children/descendants |
| encode-skill | ENCODE — object lookups, portal search, metadata |
| ensembl-skill | Ensembl REST — lookup, overlap, xref, variation |
| epigraphdb-skill | EpiGraphDB — ontology, literature, MR, gene-drug, support paths |
| eqtl-catalogue-skill | eQTL Catalogue — association retrieval + metadata endpoints |
| eva-skill | European Variation Archive — species metadata, archived variants |
| finngen-phewas-skill | FinnGen PheWAS — single variant, GRCh38 resolve |
| genebass-gene-burden-skill | Genebass gene burden — one Ensembl gene + one burden set |
| gnomad-graphql-skill | gnomAD GraphQL — frequency, gene constraint, variant context (SNV/indel) |
| gnomad-sv-skill | gnomAD-SV v4 GraphQL — population frequencies for DEL/DUP/INV/INS/BND/CPX |
| gtex-eqtl-skill | GTEx v2 single-tissue eQTLs — GRCh38 variant |
| gwas-catalog-skill | GWAS Catalog REST v2 — studies, associations, SNPs, EFO, loci |
| hmdb-skill | HMDB — metabolites, proteins, diseases, pathways |
| human-protein-atlas-skill | Human Protein Atlas — gene JSON, tissue/cell-line pages |
| ipd-skill | IPD REST — HLA allele + cell-level metadata |
| locus-to-gene-mapper-skill | GWAS locus→candidate gene chain (EFO→GWAS→OT L2G→eQTL→burden) |
| mavedb-skill | MaveDB — multiplexed assay variant-effect (MAVE / DMS) score sets |
| metabolights-skill | MetaboLights — study discovery + metabolomics metadata |
| mgnify-skill | MGnify — microbiome studies, samples, biome metadata |
| ncbi-blast-skill | NCBI BLAST Common URL — submit/poll/summarize BLAST jobs |
| ncbi-clinicaltables-skill | NCBI Clinical Tables — human gene autocomplete search |
| ncbi-datasets-skill | NCBI Datasets v2 — assembly, genome, taxonomy metadata |
| ncbi-entrez-skill | NCBI Entrez (E-Utilities) — PubMed/Gene/Protein/PMC/GEO |
| ncbi-pmc-skill | NCBI PMC Open Access — article/file availability |
| opentargets-skill | Open Targets GraphQL — target/disease/drug/variant, L2G heatmaps |
| pharmgkb-skill | PharmGKB — genes, variants, clinical annotations, guidelines |
| pride-skill | PRIDE Archive — proteomics project discovery + metadata |
| proteomexchange-skill | ProteomeXchange PROXI — datasets, peptides, PSMs, spectra, USI |
| pubchem-pug-skill | PubChem PUG REST — compound properties, descriptions, assays |
| quickgo-skill | QuickGO — GO terms, annotations, ontology traversal |
| rcsb-pdb-skill | RCSB PDB — core metadata, Search API, FASTA |
| reactome-skill | Reactome ContentService — pathway/event/participant/search |
| research-router-skill | Internal router — normalize entities, fan out sub-skills, synthesize |
| rhea-skill | Rhea — biochemical reaction search, reaction IDs |
| rnacentral-skill | RNAcentral — RNA entries, single-entry lookup, cross-references |
| strchive-skill | STRchive — curated disease-associated STR loci, motif, thresholds, gnomAD AF |
| string-skill | STRING — network, interaction partners, enrichment |
| tpmi-phewas-skill | TPMI PheWAS — single variant, GRCh38 resolve |
| ukb-topmed-phewas-skill | UKB-TOPMed PheWAS — single variant, GRCh38 resolve |
| uniprot-skill | UniProt REST — UniProtKB/UniRef/UniParc, FASTA stream |

### Endpoints without a local wrapper yet

These have public APIs / downloads but no `sources/<name>/INSTRUCTIONS.md`
recipe in this skill yet. Use the endpoint directly until a wrapper lands.

| Need | Endpoint | Notes |
|---|---|---|
| dbVar (NCBI SV archive) | `eutils.ncbi.nlm.nih.gov` Entrez against `dbvar` | 6M+ SVs; FTP bulk at `ftp.ncbi.nlm.nih.gov/pub/dbVar/data/`. Use `ncbi-entrez-skill` with `db=dbvar`. |
| AnnotSV (SV annotation) | `lbgi.fr/AnnotSV/` web UI or local Tcl install | No REST API. Project pipelines use the local install via the `annotsv` skill. |
| AlphaMissense bulk scores | Zenodo `10.5281/zenodo.8360242` | Precomputed table, ~70M variants; download-only, no API. |
| ProteinGym DMS benchmarks | `marks.hms.harvard.edu/proteingym/` | Precomputed; download-only. |
| Retraction / correction status of a DOI | `api.crossref.org/v1/works/{DOI}` → `update-to[]` | CrossRef ingests Retraction Watch since 2025-01; no auth (set `mailto`). Single GET, no wrapper needed. |

### Retrieval Discipline (per-source)

Request-time cautions that matter more than source identity:

- **ClinVar:** separate star/review status from clinical significance.
- **gnomAD:** report population AF with build + ref/alt *before* any pathogenicity claim.
- **Open Targets:** distinguish genetics evidence from literature/mining scores.
- **GWAS Catalog:** carry ancestry and study context into the answer.
- **GTEx / eQTL Catalogue:** report tissue and variant build.
- **Human Protein Atlas / Bgee:** tissue expression is not causality.
- **Reactome / QuickGO:** verify species and evidence code where available.
- **STRING:** network topology = interaction context, not proof of mechanism.
- **AlphaFold / RCSB PDB:** check confidence; do not overstate low-confidence regions.
- **ChEMBL / BindingDB:** report assay type, organism, units, relation.
- **PharmGKB / CPIC:** attach evidence/guideline level.
- **ClinicalTrials.gov:** trial existence ≠ efficacy evidence.
- **cBioPortal / CIViC:** carry tumor type and evidence level.
- **PubMed / PMC / bioRxiv:** preprints are provisional. **Always check retraction / correction status** for any paper that drives a clinical or mechanistic claim — query `api.crossref.org/v1/works/{DOI}` and inspect `update-to[]` for `type: retraction` or `type: correction`. Retrieval can otherwise launder retracted sources into confident answers.
- **Guideline currency:** when citing CPIC / ACMG / professional-society guidance, name the version and year — older guideline versions are routinely superseded (e.g., ACMG 2015 → 2023, CPIC v1 → v2 per gene). Don't anchor on a guideline number without checking PharmGKB/CPIC for the current revision.

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

For any literature-anchored claim, also surface:

- publication year + retraction/correction status (CrossRef `update-to[]`)
- guideline version where applicable (ACMG / CPIC / professional society)
- whether the cited evidence is on **current frontier models** when the
  claim is about LLM behavior — pre-frontier findings (GPT-3.5/4, Claude 3,
  Gemini 1.x) don't transfer unless the result is scale-independent.

## When To Stop

Stop early when:

- identifier normalization fails
- local curated docs already contain a newer reviewed answer
- external evidence is only associative and the user's question asks for causality
- the remaining sources are lower tier than what has already been checked
- the likely next step is a repo-owned contract update, not more searching
