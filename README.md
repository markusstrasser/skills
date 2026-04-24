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

| Skill | What it does | Portability |
|-------|-------------|-------------|
| `causal-check` | Causal inference discipline. Shape-match explanations to observations, define the null. | Portable |
| `epistemics` | Bio/medical/scientific evidence hierarchy and anti-hallucination rules. | Portable |
| `life-science-research` | Route biomedical questions across genetics, expression, pathways, structure, pharmacology, clinical evidence, literature, and omics sources. | Portable |
| `source-grading` | NATO Admiralty System (A-F reliability, 1-6 credibility). For OSINT, forensic, legal work. | Portable |
| `goals` | Elicit, clarify, or revise project goals AND operating principles through structured questioning. Produces or updates docs/GOALS.md (one source of truth for goals + governance). | Portable |
| `investigate` | Deep forensic investigation. Fraud detection, OSINT, billing audits. Adversarial, cross-domain. | Portable |
| `competing-hypotheses` | Analysis of Competing Hypotheses (ACH). Bayesian LLR scoring. | Mostly portable |
| `entity-management` | Versioned knowledge files for entities (people, companies, genes, drugs). | Mostly portable |
| `model-guide` | Frontier model selection and prompting guide. Which model for which task, known pitfalls. | Mostly portable |
| `retro` | End-of-session retrospective. Extracts failure modes and tooling proposals. | Mostly portable |
| `supervision-audit` | Audit sessions for wasted supervision. Outputs concrete automation fixes. | Mostly portable |
| `agent-pliability` | Make project files more discoverable for agents. Renames, splits, builds indexes. | Mostly portable |
| `llmx-guide` | Gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. | Mostly portable |
| `model-review` | Cross-model adversarial review via llmx. Dispatches to Gemini and GPT for critique. | Claude-heavy |
| `researcher` | Autonomous multi-source research. Orchestrates Exa, Brave, Perplexity, Semantic Scholar. | Claude-heavy |
| `session-analyst` | Analyzes session transcripts for behavioral anti-patterns. Dispatches to Gemini. | Claude-heavy |
| `project-upgrade` | Autonomous codebase improvement via Gemini structured analysis. | Claude-heavy |
| `debug-mcp-servers` | Debug MCP server loading issues in Claude Code. | Claude-only |

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
