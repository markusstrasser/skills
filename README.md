# Agent Skills

Shared skills following the [Agent Skills open standard](https://github.com/anthropics/agent-skills). Compatible with Claude Code, OpenAI Codex, and Gemini CLI.

## Cross-Tool Discovery

All three tools discover skills via user-level symlinks pointing here:

| Tool | Discovery path | Status |
|------|---------------|--------|
| Claude Code | `~/.claude/skills/` or per-project `.claude/skills/` | Per-project symlinks (selective) |
| OpenAI Codex | `~/.agents/skills/` or per-project `.agents/skills/` | `~/.agents/skills → ~/Projects/skills` |
| Gemini CLI | `~/.gemini/skills/` or `~/.agents/skills/` | `~/.gemini/skills → ~/Projects/skills` |

## Skills

<!-- GENERATED — mirrors active, non-private skills in skill_manifest.jsonl (the source of truth).
     Do NOT hand-maintain these rows: this table had drifted to list 13 deleted skills
     (agent-pliability, model-review, researcher, project-upgrade, …) because it was edited by
     hand after the 2026-04-08 consolidation. Refresh from the manifest, not by editing rows. -->

| Skill | What it does |
|-------|--------------|
| `analyze` | Reusable reasoning lenses: null/base-rate, causal attribution, DAG adjustment, ACH hypotheses, weakest-link audit, and decision-impact stop. Use for why/root-cause/regression/confounder/anomaly questions when a project workflow needs sharper reasoning. Local only. |
| `bio-verify` | Verify hardcoded bio constants (coords, genes, ratios) vs Ensembl/ClinVar/ISBT/gnomAD/PanelApp. |
| `brainstorm` | Divergent ideation via systematic perturbation — denial cascades, domain forcing, constraint inversion. Multi-model dispatch optional (volume, not diversity). For convergent critique, use /model-review. |
| `census-data` | Census Data API + IPUMS extract patterns (ACS, CPS, SIPP, QWI, decennial, USA microdata). Use for state/county aggregates, microdata extracts, immigrant shares, earnings-by-group, Card/Borjas-style panels. |
| `corpus` | Canonical local store for source bytes + parses + citation graph + annotations. 'check corpus store', 'cite something', 'find contradicting citations', 'has any repo already seen this DOI'. |
| `critique` | Adversarial review. Modes: model (Gemini+GPT), verify (fact-check), close (post-impl tests). 'review plan', 'what's wrong', 'fact-check'. |
| `data-acquisition` | Probe→stage→register for external datasets (research: Census/NCES/PSID; intel: `tools/download_*`, DATA_INVENTORY) |
| `dataset-register` | Register staged dataset in per-topic catalog with provenance, variables, access state, quirks. Use after /data-acquisition, adding a source to a topic, or formalizing an ad-hoc entry. |
| `de-slop` | Adversarial editor that hunts AI-prose patterns (vocabulary tells, structural padding, false authority). Use for "de-slop", "clean up prose", "check for AI writing" before publishing. |
| `emil-design-eng` | Emil Kowalski's philosophy on UI polish, component design, animation decisions, and the invisible details that make software feel great. |
| `entity-management` | Versioned, sourced entity dossiers across repos. Use when creating/updating company, stock, person, gene, drug, self, contract, or filing pages; routes intel public-company entities to analysis/entities and selve/general entities to docs/entities. |
| `goals` | Elicit or revise project goals and operating principles into docs/GOALS.md (mission, strategy, metrics, autonomy boundaries). Use when starting a project, pivoting strategy, or governance feels unclear. |
| `google-workspace` | Automate Google Workspace via gws CLI — Drive uploads, Sheets logs, Gmail alerts, Calendar. Use for session logs to sheets, artifact uploads, pipeline notifications. Not for general HTTP or interactive workflows. |
| `illustration-gen` | Generate designer-style SVGs from text prompts via Quiver Arrow API (paid). Use when: 'make a logo', 'generate an icon', 'illustrate this concept as SVG'. NOT for precise scientific/technical diagrams — use scientific-drawing instead. |
| `improve` | Use when: 'what should I fix next', 'suggest improvements', 'run maintenance'. Modes: harvest (gather+rank findings), suggest (repeated workflows → skills), maintain (quality checks + implement), tick (one orchestrator cycle). |
| `life-science-research` | Biomedical source routing — ClinVar, gnomAD, Ensembl, GTEx, OpenTargets, ChEMBL, PharmGKB, UniProt, PDB, PubMed, bioRxiv. Source lookup + multi-lane synthesis. |
| `llmx-guide` | llmx CLI gotchas (Python/Bash). Use when writing llmx calls, debugging llmx failures, or choosing model/provider options. |
| `manim-animations` | Create mathematical animations using Manim. Use when the user mentions animations, mathematical visualizations, 3Blue1Brown-style videos, explaining math concepts visually, animating equations, or working with manim files. |
| `modal` | Modal serverless Python. Writing/debugging Modal scripts, deploying, or choosing GPU/resource configs. |
| `model-guide` | Frontier model selection and prompting for Claude Opus 4.8, GPT-5.5, and GPT-5.5 Pro. |
| `neurokit2` | NeuroKit2 biosignal proc: ECG/PPG/EDA/EEG/RSP/EMG/EOG/HRV. HRV analysis, Oura data, sleep studies, wearables. |
| `observe` | Session retros. Modes: sessions/architecture/supervision/retro. 'what went wrong', 'session quality', 'wasted time'. |
| `oura-ring` | Oura Ring v2 API: sleep, HRV, readiness, activity, stress, SpO2. Analysis, dashboards, wearable→NeuroKit2. |
| `research` | 'find papers about', 'research X', 'what's known about'. One-shot research with source grading. /research-ops for cycles/compile/diff. |
| `research-ops` | Use when: 'run research cycle', 'compile memos into article', 'what's not in training data', 'dispatch parallel audit'. Autonomous research loops, knowledge compilation, training-data diff. For one-shot research questions use /research. |
| `scientific-drawing` | Use when: 'draw a diagram', 'scientific figure', 'visualize this', 'architecture diagram', 'plot this function'. Typst/CeTZ (fast, default), TikZ (math/circuits/chemistry), D2 (architecture/ERD), Asymptote (3D). |
| `sweep` | Codebase consistency scan (Flash classifier). Pattern/convention/config drift, function divergence. 'sweep', 'inconsistencies'. |
| `trending-scout` | Scan for new agent/AI ecosystem developments, filtered against what we already know. Use for "what's new", vendor updates, trending repos, "check for updates", weekly landscape scans. |
| `upgrade` | Full codebase audit, Gemini+GPT (inventory→plan→review→implement). 'audit codebase', 'find bugs'. Not /critique or /observe. |
| `verify-before` | Probe before acting, check status before claiming, predict before seeing outcomes. Modes: probe (validate on tiny slice), status (query live ground truth), preregister (lock prediction + decision rule before an experiment/eval reveals its result). |
| `writing-style` | Write emails, texts, outreach, scheduling notes, or any short prose on behalf of Markus Strasser in his voice. Embeds hard rules, register reference, and banned vocabulary; deeper guide lives in phenome. |
| `x-api` | X (Twitter) API v2 pay-per-use client — paginated user-tweets pull, cost-tracked Bearer auth, server-side cashtag extraction. Use when monitoring a curated set of finance/research accounts for ticker mentions and material claims. |
| `youtube-transcript` | Fetch YouTube transcripts via yt-dlp (auto-captions or subs, .vtt → plain text). Use when citing a podcast/video, quoting a speaker, or building a searchable video corpus. Transcript-only. |

## Life Science Source Skills

The Life Science Research bundle is hierarchical to stay inside Claude Code's
skill-description budget. `life-science-research` is the only top-level skill.
Its source-specific lookup recipes live under
`life-science-research/sources/*-skill/` and are loaded on demand for AlphaFold,
Bgee, BindingDB, BioBank Japan PheWAS, bioRxiv/medRxiv,
BioStudies/ArrayExpress, cBioPortal, CELLxGENE, ChEBI, ChEMBL, CIViC,
ClinicalTrials.gov, ClinVar, EFO, ENCODE, Ensembl, EpiGraphDB, eQTL Catalogue,
EVA, FinnGen, Genebass, gnomAD, GTEx, GWAS Catalog, HMDB, Human Protein Atlas,
IPD, MetaboLights, MGnify, NCBI BLAST, NCBI Clinical Tables, NCBI Datasets,
NCBI Entrez, NCBI PMC, Open Targets, PharmGKB, PRIDE, ProteomeXchange,
PubChem, QuickGO, RCSB PDB, Reactome, Rhea, RNAcentral, STRING, TPMI,
UKB-TOPMed, and UniProt.

## Hooks

`hooks/` contains shared hooks for Claude Code — bash loop guards, search burst detection, source attribution checks, epistemic gates, session logging. Referenced by absolute path from each project's `settings.json`.

## Portability Notes

- **Portable**: Pure reasoning frameworks — work identically in any agent.
- **Mostly portable**: Reference Claude Code tool names (Bash, Grep, Glob, etc.) but core logic is prose. Other agents can follow the instructions even if tool names differ.
- **Claude-heavy**: Deep tool routing, embedded hooks, MCP orchestration. Need per-tool variants for full functionality elsewhere.
- **Claude-only**: Entirely dependent on Claude Code internals.

## Usage

Skills are discovered automatically via the symlinks above. For per-project selection in Claude Code, symlink individual skills:

```bash
ln -s ~/Projects/skills/researcher /your-project/.claude/skills/researcher
```

For this machine, sync the intended user-level symlink layout with:

```bash
uv run python3 scripts/sync_skill_links.py --dry-run
uv run python3 scripts/sync_skill_links.py
```

Codex uses one full-tree symlink at `~/.agents/skills`. Claude Code and Gemini
use budget-safe core top-level skill symlinks so large nested source bundles and
low-frequency skills do not consume the skills context budget. Use
`--full` only for a session profile where discovery matters more than context.

## Archive

`archive/` contains superseded skill versions.
