# Plan-Close Review Packet

- Repo: `/Users/alien/Projects/skills`
- Mode: `worktree`
- Ref: `HEAD vs current worktree`

## Scope

- Target users: FILL ME
- Scale: FILL ME
- Rate of change: FILL ME

## Touched Files

### Touched Files

- `.claude/overview-marker-source`
- `.claude/overviews/source-overview.md`
- `_archive/architect/SKILL.md`
- `brainstorm/SKILL.md`
- `brainstorm/references/llmx-dispatch.md`
- `hooks/epistemic-domain-router.sh`
- `hooks/generate-overview-batch.sh`
- `hooks/generate-overview.sh`
- `hooks/overview-staleness-cron.sh`
- `hooks/permission-auto-allow.sh`
- `hooks/postmerge-overview.sh`
- `hooks/pretool-llmx-guard.sh`
- `hooks/sessionend-overview-trigger.sh`
- `improve/SKILL.md`
- `llmx-guide/SKILL.md`
- `observe/SKILL.md`
- `research-ops/SKILL.md`
- `research-ops/scripts/run-cycle.sh`
- `review/SKILL.md`
- `review/lenses/plan-close-review.md`
- `review/scripts/build_plan_close_context.py`
- `review/scripts/model-review.py`
- `review/scripts/test_model_review.py`
- `upgrade/SKILL.md`

## Git Status

### git status --short

```text
M .claude/overview-marker-source
 M .claude/overviews/source-overview.md
 M _archive/architect/SKILL.md
 M brainstorm/SKILL.md
 M brainstorm/references/llmx-dispatch.md
 M hooks/epistemic-domain-router.sh
 M hooks/generate-overview-batch.sh
 M hooks/generate-overview.sh
 M hooks/overview-staleness-cron.sh
 M hooks/permission-auto-allow.sh
 M hooks/postmerge-overview.sh
 M hooks/pretool-llmx-guard.sh
 M hooks/sessionend-overview-trigger.sh
 M improve/SKILL.md
 M llmx-guide/SKILL.md
 M observe/SKILL.md
 M research-ops/SKILL.md
 M research-ops/scripts/run-cycle.sh
 M review/SKILL.md
 M review/lenses/plan-close-review.md
 M review/scripts/build_plan_close_context.py
 M review/scripts/model-review.py
 M review/scripts/test_model_review.py
 M upgrade/SKILL.md
```

### git diff --stat

```text
.claude/overview-marker-source             |   2 +-
 .claude/overviews/source-overview.md       | 107 ++++----
 _archive/architect/SKILL.md                |   8 +
 brainstorm/SKILL.md                        |   8 +
 brainstorm/references/llmx-dispatch.md     |  37 +--
 hooks/epistemic-domain-router.sh           |   2 +-
 hooks/generate-overview-batch.sh           | 345 +-------------------------
 hooks/generate-overview.sh                 | 281 +--------------------
 hooks/overview-staleness-cron.sh           |  20 +-
 hooks/permission-auto-allow.sh             |   2 +-
 hooks/postmerge-overview.sh                |   5 -
 hooks/pretool-llmx-guard.sh                |  41 +++-
 hooks/sessionend-overview-trigger.sh       |  13 +-
 improve/SKILL.md                           |  30 ++-
 llmx-guide/SKILL.md                        |  31 ++-
 observe/SKILL.md                           |  50 ++--
 research-ops/SKILL.md                      |  26 +-
 research-ops/scripts/run-cycle.sh          |  52 ++--
 review/SKILL.md                            |  10 +-
 review/lenses/plan-close-review.md         |   4 +
 review/scripts/build_plan_close_context.py | 309 ++++++++---------------
 review/scripts/model-review.py             | 380 +++++++++++++----------------
 review/scripts/test_model_review.py        |  19 +-
 upgrade/SKILL.md                           |   8 +
 24 files changed, 561 insertions(+), 1229 deletions(-)
```

### Unified Diff

```diff
.claude/overview-marker-source --- Text
1 756fea8b3e66629e00000a0c7425ecc44750a  1 e858f7e178f3944813a98780e72f0952d90dd
. 5d5                                    . c8c

.claude/overviews/source-overview.md --- Text
 1 <!-- Generated: 2026-04-08T07:09:32Z   1 <!-- Generated: 2026-04-09T16:29:53Z
 .  | git: 756fea8 | model: gemini-3-fl   .  | git: e858f7e | model: gemini-3-fl
 . ash-preview -->                        . ash-preview -->
 2                                        2 
 3 <!-- INDEX                             3 <!-- INDEX
 4 [SCRIPT] add-mcp.sh — Adds MCP serve   4 [SCRIPT] hooks/generate-overview.sh 
 . rs (chrome-devtools, exa, anki, etc.   . — Core generator: extracts codebase 
 . ) to project configuration             . via repomix and updates overviews vi
 .                                        . a Gemini
 5 [SCRIPT] generate-overview.sh — Core   . 
 .  generator that runs repomix and LLM   . 
 .  calls to create markdown overviews    . 
 6 [SCRIPT] generate-overview-batch.sh    5 [SCRIPT] hooks/generate-overview-bat
 . — Batch processes multiple project o   . ch.sh — Batch processor for multiple
 . verviews via Gemini Batch API for co   .  project overviews using Gemini Batc
 . st efficiency                          . h API (50% cost reduction)
 7 [SCRIPT] agent-coord.py — Manages mu   6 [SCRIPT] hooks/overview-staleness-cr
 . lti-session agent coordination and c   . on.sh — Daily maintenance script tha
 . onflict detection via a shared statu   . t regenerates overviews if they are 
 . s file                                 . >7 days old
 8 [SCRIPT] hook-trigger-log.sh — Centr   7 [SCRIPT] hooks/add-mcp.sh — CLI util
 . alized telemetry for logging hook ac   . ity to add MCP server presets (exa, 
 . tions (warn, block, allow) to JSONL    . anki, svelte, etc.) to project confi
 .                                        . guration
 9 [MODULE] commit-check-parse.py — Log   8 [SCRIPT] hooks/agent-coord.py — Mult
 . ic for validating git commit message   . i-session coordinator that prevents 
 .  formats and suggesting trailers       . file conflicts between concurrent ag
 .                                        . ents
 .                                        9 [MODULE] hooks/commit-check-parse.py
 .                                        .  — Logic for validating git commit m
 .                                        . essage structure, scopes, and traile
 .                                        . rs
10 [MODULE] posttool_research_reformat.  10 [MODULE] hooks/posttool_research_ref
.. py — Rewrites and archives noisy res  .. ormat.py — Content transformation en
.. earch/search MCP outputs              .. gine for cleaning and archiving nois
..                                       .. y research tool outputs
11 [MODULE] precompact-extract.py — Ext  11 [MODULE] hooks/precompact-extract.py
.. racts epistemic content (hedging, de  ..  — Epistemic extractor that preserve
.. cisions, questions) before conversat  .. s hedging, decisions, and open quest
.. ion compaction                        .. ions before context compaction
12 [MODULE] source-check-validator.py —  12 [MODULE] hooks/source-check-validato
..  Validates provenance tag density an  .. r.py — Structural validator for prov
.. d structural correctness in research  .. enance tags ([SOURCE:], [DATA], etc.
..  files                                .. ) in research prose
13 [FLOW] tool_output → posttool_resear  13 [FLOW] codebase → repomix → Gemini →
.. ch_reformat.py → ~/.claude/tool-outp  ..  markdown — The transformation of so
.. ut-archive/ — Archives raw search da  .. urce code into functional overviews
.. ta                                    .. 
14 [FLOW] transcript → precompact-extra  14 [FLOW] transcript → precompact-extra
.. ct.py → .claude/checkpoint.md — Pres  .. ct.py → checkpoint.md — Extraction o
.. erves state across compaction         .. f epistemic state to survive context
..                                       ..  window compaction
15 [FLOW] hook_events → hook-trigger-lo  15 [FLOW] tool_output → research_reform
.. g.sh → ~/.claude/hook-triggers.jsonl  .. at.py → archive/ — Quarantine and no
..  — Telemetry for ROI analysis         .. rmalization of high-volume research 
..                                       .. data
16 [LIB] repomix — Used to pack codebas  16 [LIB] repomix — Codebase packing for
.. e context for LLM processing          ..  LLM consumption
17 [LIB] llmx — CLI tool used for model  17 [LIB] llmx — CLI/Python interface fo
.. -agnostic LLM chat and batch operati  .. r multi-model chat and batch process
.. ons                                   .. ing
18 [LIB] jq — Required for robust JSON   18 [LIB] jq — JSON processing for confi
.. parsing in shell scripts              .. guration and hook data
19 -->                                   19 -->
20                                       20 
21 ### Code inventory                    21 ### Code inventory
22                                       22 
23 #### Overview Generation              23 #### Overview Generation
24 Automated systems for maintaining co  24 Automated system for maintaining hig
.. debase and tooling documentation.     .. h-level documentation of the codebas
..                                       .. e.
25 * `generate-overview.sh`: The primar  25 * `hooks/generate-overview.sh`: The 
.. y engine that uses `repomix` to gath  .. primary entry point for generating a
.. er context and `llmx` to generate ma  ..  single or auto-configured set of ov
.. rkdown overviews based on templates   .. erviews.
.. in `hooks/overview-prompts/`.         .. 
26 * `generate-overview-batch.sh`: A wr  26 * `hooks/generate-overview-batch.sh`
.. apper for `generate-overview.sh` tha  .. : Orchestrates multiple overview req
.. t bundles multiple requests into a s  .. uests into a single Batch API job fo
.. ingle Gemini Batch API job to reduce  .. r efficiency.
..  costs by 50%.                        .. 
27 * `overview-staleness-cron.sh`: A ma  27 * `hooks/overview-staleness-cron.sh`
.. intenance script that checks project  .. : Monitors `overview-marker` files a
..  markers and regenerates overviews i  .. nd triggers updates based on age and
.. f they are older than 7 days and the  ..  git activity.
..  code has changed.                    .. 
..                                       28 * `hooks/postmerge-overview.sh`: Git
..                                       ..  hook to refresh overviews automatic
..                                       .. ally after a pull or merge.
28 * `postmerge-overview.sh`: A git hoo  29 * `hooks/sessionend-overview-trigger
.. k that triggers background regenerat  .. .sh`: Analyzes session changes (LOC,
.. ion after a pull or merge.            ..  structural changes) to decide if a 
..                                       .. refresh is warranted.
29                                       30 
30 #### Epistemic & Research Guardrails  31 #### Epistemic & Research Governance
31 Tools to ensure data provenance, cit  32 Tools for enforcing citation standar
.. ation quality, and "thinking" integr  .. ds and preserving "soft" knowledge (
.. ity in research-heavy projects.       .. uncertainty, rationale).
32 * `source-check-validator.py`: Valid  33 * `hooks/source-check-validator.py`:
.. ates that research files contain suf  ..  Validates that factual claims in re
.. ficient provenance tags (e.g., `[SOU  .. search paths have appropriate proven
.. RCE: url]`, `[DATA]`) relative to th  .. ance tags.
.. e number of claims made.              .. 
33 * `posttool_research_reformat.py`: I  34 * `hooks/posttool_research_reformat.
.. ntercepts noisy MCP outputs from sea  .. py`: Intercepts noisy MCP outputs (l
.. rch engines (Exa, Brave, Semantic Sc  .. ike paper text or search results) to
.. holar), reformats them for readabili  ..  normalize them for the LLM.
.. ty, and archives the raw data to `~/  .. 
.. .claude/tool-output-archive/`.        .. 
34 * `postwrite-frontier-timeliness.sh`  35 * `hooks/precompact-extract.py`: Sca
.. : Scans for citations of "pre-fronti  .. ns conversation transcripts before c
.. er" models (like GPT-4 or Claude 3)   .. ompaction to save "epistemic content
.. and warns if a staleness disclaimer   .. " (hedged claims, negative results) 
.. is missing.                           .. into `checkpoint.md`.
35 * `subagent-epistemic-gate.sh`: Insp  36 * `hooks/postwrite-frontier-timeline
.. ects subagent outputs for factual cl  .. ss.sh`: Detects citations of obsolet
.. aims that lack proper sourcing befor  .. e models (e.g., GPT-3.5) without sta
.. e they are merged into the main sess  .. leness disclaimers.
.. ion.                                  .. 
36                                       37 
37 #### Session & State Management       38 #### Agent Coordination & Safety
38 Infrastructure for handling conversa  39 Infrastructure for managing multiple
.. tion compaction, session logging, an  ..  agents and preventing common failur
.. d multi-agent coordination.           .. e modes.
39 * `precompact-extract.py`: A critica  .. 
.. l module that parses conversation tr  .. 
.. anscripts before compaction to save   .. 
.. "epistemic content" (hedged claims,   .. 
.. negative results, open questions) in  .. 
.. to a `.claude/checkpoint.md` file.    .. 
40 * `agent-coord.py`: A CLI tool and m  40 * `hooks/agent-coord.py`: Uses a sha
.. odule that uses a shared `.claude/ag  .. red `.claude/agent-work.md` file and
.. ent-work.md` file to prevent multipl  ..  process tracking to prevent agents 
.. e agents from conflicting on the sam  .. from editing the same files.
.. e files.                              .. 
41 * `sessionend-log.sh`: Generates "fl  41 * `hooks/pretool-subagent-gate.sh`: 
.. ight receipts" at the end of a sessi  .. Blocks subagent spawning under high 
.. on, logging duration, cost, and git   .. memory pressure or when runaway dele
.. commits to `~/.claude/session-receip  .. gation is detected.
.. ts.jsonl`.                            .. 
..                                       42 * `hooks/pretool-llmx-guard.sh`: Pre
..                                       .. vents "spin loops" and catches hallu
..                                       .. cinated model flags or forbidden mod
..                                       .. el versions.
42 * `prepare-commit-msg-session-id.sh`  43 * `hooks/pretool-multiagent-commit-g
.. : Automatically appends the current   .. uard.sh`: Prevents global git operat
.. session ID to git commit trailers fo  .. ions (like `git add .`) when multipl
.. r traceability.                       .. e agents are active in the same repo
..                                       .. .
43                                       44 
44 #### Safety & Automation Hooks        45 #### Git & Workflow Automation
45 A suite of Claude Code hooks that gu  46 Hooks that enforce project-specific 
.. ard against common failure modes.     .. conventions during the development l
..                                       .. ifecycle.
46 * `pretool-subagent-gate.sh`: Blocks  47 * `hooks/commit-check-parse.py`: Val
..  subagent spawning if system memory   .. idates commit messages against the `
.. is low or if the dispatch prompt lac  .. [scope] Verb — why` format and sugge
.. ks a "synthesis budget" (to prevent   .. sts trailers.
.. turn exhaustion).                     .. 
47 * `posttool-bash-failure-loop.sh`: D  48 * `hooks/prepare-commit-msg-session-
.. etects consecutive bash errors and i  .. id.sh`: Automatically appends the cu
.. njects targeted diagnostic advice in  .. rrent `Session-ID` to git commit tra
.. stead of allowing blind retries.      .. ilers.
48 * `pretool-llmx-guard.sh`: Validates  49 * `hooks/stop-plan-gate.sh`: Blocks 
..  `llmx` CLI calls, blocking invalid   .. session termination if acceptance cr
.. model names or flags and detecting p  .. iteria in a plan's `verify` block ar
.. otential spin loops.                  .. e failing.
49 * `pretool-commit-check.sh`: Enforce  50 * `hooks/postcommit-propagate-check.
.. s project-specific git commit standa  .. sh`: Warns when a commit touches fil
.. rds (prefixes, trailers, and body re  .. es that have downstream consumers li
.. quirements).                          .. sted in a dependency manifest.
50                                       51 
51 ### Data flow                         52 ### Data flow
52                                       53 
53 1.  **Telemetry Flow**: Every signif  54 1.  **Codebase to Overview**: `repom
.. icant hook event (warning, block, or  .. ix` packs source files based on `OVE
..  auto-allow) is piped into `hook-tri  .. RVIEW_DIRS` config → `generate-overv
.. gger-log.sh`, which appends a JSON e  .. iew.sh` wraps this in a prompt → `ll
.. ntry to `~/.claude/hook-triggers.jso  .. mx` sends to Gemini → Output is save
.. nl`. This data is used for ROI and "  .. d to `.claude/overviews/`.
.. Agent Drift" analysis.                .. 
54 2.  **Compaction Recovery**: When a   55 2.  **Epistemic Preservation**: `Ses
.. conversation reaches the context lim  .. sionEnd` or `PreCompact` triggers → 
.. it, `precompact-log.sh` triggers `pr  .. `precompact-extract.py` parses the J
.. ecompact-extract.py`. It reads the `  .. SONL transcript → Epistemic items (q
.. transcript_path`, extracts key decis  .. uestions, hedges) are written to `.c
.. ions and uncertainties, and writes t  .. laude/checkpoint.md` → Agent reads c
.. hem to `.claude/checkpoint.md`. Upon  .. heckpoint to resume state.
..  restart, `postcompact-verify.sh` re  .. 
.. minds the agent to read this checkpo  .. 
.. int to recover lost context.          .. 
55 3.  **Research Archiving**: Raw MCP   56 3.  **Research Archiving**: Research
.. tool results from search tools flow   ..  MCP tool returns raw data → `postto
.. through `posttool_research_reformat.  .. ol_research_reformat.py` hashes the 
.. py`. The script calculates a content  .. content → Raw data is saved to `~/.c
..  hash, saves the full raw text to `~  .. laude/tool-output-archive/` → A trun
.. /.claude/tool-output-archive/<tool_n  .. cated, normalized summary is returne
.. ame>/<hash>.txt`, and returns a shor  .. d to the agent's context.
.. tened, reformatted version to the ag  .. 
.. ent.                                  .. 
56 4.  **Cost Tracking**: Session costs  57 4.  **Telemetry**: Hooks pipe JSON m
..  are persisted by the status line in  .. etadata to `hook-trigger-log.sh` → A
.. to `/tmp/claude-cockpit-<session>`.   .. ppended to `~/.claude/hook-triggers.
.. At session end, `sessionend-log.sh`   .. jsonl` → Used for ROI and failure ra
.. moves this data into the permanent `  .. te analysis.
.. ~/.claude/session-receipts.jsonl` lo  .. 
.. g.                                    .. 
57                                       58 
58 ### Key abstractions                  59 ### Key abstractions
59                                       60 
60 *   **Provenance Tags**: A shared vo  61 *   **Provenance Tags**: A shared vo
.. cabulary (e.g., `[SOURCE: ]`, `[INFE  .. cabulary (`[SOURCE:]`, `[DATA]`, `[I
.. RENCE]`, `[DATA]`, `[TRAINING-DATA]`  .. NFERENCE]`, `[TRAINING-DATA]`) used 
.. ) used across 5+ files (`source-chec  .. across 5+ files to track the origin 
.. k-validator.py`, `pretool-source-rem  .. of factual claims.
.. ind.sh`, `subagent-epistemic-gate.sh  .. 
.. `, etc.) to track the origin of fact  .. 
.. ual claims.                           .. 
61 *   **Advisory Wrapper**: The patter  62 *   **Session-ID**: A unique identif
.. n implemented in `advisory-wrapper.s  .. ier stored in `.claude/current-sessi
.. h` which allows blocking hooks to be  .. on-id` used to link git commits, log
..  converted into non-blocking "adviso  .. s, and temporary state files across 
.. ry" hooks that log issues to `~/.cla  .. different hooks.
.. ude/hook-advisory.log` while allowin  .. 
.. g the tool call to proceed.           .. 
..                                       63 *   **Advisory Wrapper**: The patter
..                                       .. n of exiting `0` while providing `ad
..                                       .. ditionalContext` in JSON, allowing h
..                                       .. ooks to guide the agent without hard
..                                       .. -blocking the workflow.
62 *   **Session Baseline**: A pattern   64 *   **Plan Verify Blocks**: Executab
.. where the state of the repository is  .. le bash snippets inside markdown pla
..  recorded at the start of a session   .. ns (` ```verify `) used by `stop-ver
.. (e.g., `/tmp/session-base-sha-<id>.t  .. ify-plan.sh` to mechanically confirm
.. xt`) so that hooks like `stop-uncomm  ..  task completion.
.. itted-warn.sh` can distinguish betwe  .. 
.. en pre-existing dirty files and chan  .. 
.. ges made specifically during the cur  .. 
.. rent session.                         .. 
63                                       65 
64 ### Dependencies                      66 ### Dependencies
65                                       67 
66 | Package | Usage |                   68 *   `repomix`: Used for packing code
..                                       .. base subsets into a single context f
..                                       .. or overview generation.
67 | :--- | :--- |                       .. 
68 | `repomix` | Packs codebase files i  .. 
.. nto a single document for overview g  .. 
.. eneration. |                          .. 
69 | `llmx` | Handles LLM chat interact  69 *   `llmx`: The primary interface fo
.. ions and batch API submissions. |     .. r interacting with LLMs (Gemini, GPT
..                                       .. ) via CLI or Python API for batch jo
..                                       .. bs and reviews.
70 | `jq` | Used throughout shell hooks  70 *   `jq`: Heavily utilized in shell 
..  for reliable JSON extraction and ma  .. scripts for robust parsing of the JS
.. nipulation. |                         .. ON objects passed by Claude Code hoo
..                                       .. ks.
71 | `pyright` | Invoked by `posttool-p  71 *   `pyright`: Used by `posttool-pyr
.. yright-check.sh` to provide static a  .. ight-check.sh` to provide immediate 
.. nalysis feedback on edited Python fi  .. feedback on Python syntax and type e
.. les. |                                .. rrors after a write.
72 | `uv` | Used to manage Python envir  72 *   `uv`: Used for fast execution of
.. onments and run scripts like `sessio  ..  Python scripts and managing tool en
.. ns.py`. |                             .. vironments (e.g., `uv run llmx`).
73 | `ed` | Used in `append-skill-memen     
.. to.sh` for atomic, portable file edi  .. 
.. ting. |                               .. 

_archive/architect/SKILL.md --- Text
 7  7 
 8  8 Minimal-linear review workflow for architectural decision-making: **proposals → tournament → ADR**
 9  9 
 . 10 ## Default Migration Stance
 . 11 
 . 12 Unless the user explicitly asks for compatibility, evaluate proposals as breaking refactors with full migration.
 . 13 
 . 14 - Prefer architectures that replace old paths cleanly over ones that preserve them via wrappers, adapters, or phased coexistence.
 . 15 - Treat compatibility layers as costs that require explicit justification, not default prudence.
 . 16 - If a compatibility boundary must remain, proposals should name the live boundary and its removal condition.
 . 17 
10 18 ## Quick Start
11 19 
12 20 ```bash

brainstorm/SKILL.md --- Text
23 23 
24 24 **Late-stage warning:** When a frontier is mature, this skill should produce fewer, sharper ideas, not preserve the same idea count with weaker variants. One strong perturbation survivor is enough. If forced-domain rounds only yield reframings, stop and hand back to convergent filtering.
25 25 
.. 26 ## Default Architectural Stance
.. 27 
.. 28 Unless the user explicitly asks for compatibility, generate ideas as breaking refactors with full migration.
.. 29 
.. 30 - Do not spend idea budget on wrappers, adapters, transitional bridges, or phased coexistence by default.
.. 31 - Prefer ideas that delete obsolete paths and collapse complexity.
.. 32 - Only keep a compatibility boundary in the design space when a live external dependency is explicitly named.
.. 33 
26 34 ## Parameters
27 35 
28 36 Parse `$ARGUMENTS` for these optional flags (order doesn't matter, remaining text is the topic):

brainstorm/references/llmx-dispatch.md --- 1/2 --- Text
  1 <!-- Reference file for brainstorm     1 <!-- Reference file for brainstorm 
  . skill. Loaded on demand. -->           . skill. Loaded on demand. -->
  2 # llmx Dispatch Templates              2 # llmx Dispatch Templates
  3                                        3 
  4 > **DISPATCH VIA PYTHON API, NOT CL    4 > **Automation path:** use `uv run 
  . I.** Use `from llmx.api import chat    . python3 ~/Projects/skills/scripts/l
  .  as llmx_chat` and call                . lm-dispatch.py` or the shared Pytho
  .                                        . n module in `shared/llm_dispatch.py
  .                                        . `.
  5 > `llmx_chat(prompt=..., provider=.    . 
  . .., model=..., timeout=...)`. Read     . 
  . context files with                     . 
  6 > `Path(...).read_text()` and write    . 
  .  outputs with `Path(...).write_text    . 
  . (response.content)`.                   . 
  7 > The CLI commands below are templa    5 > The CLI commands below are manual
  . te references for the prompt conten    .  prompt templates only. Do not past
  . t — adapt them to Python API calls.    . e them into agent automation unchan
  .                                        . ged.
  8 > Bootstrap: `sys.path.insert(0, gl    . 
  . ob.glob(str(Path.home() / ".local/s    . 
  . hare/uv/tools/llmx/lib/python*/site    . 
  . -packages"))[0])`                      . 
  9                                        6 
 10 All templates assume `$BRAINSTORM_D    7 All templates assume `$BRAINSTORM_D
 .. IR`, `$N_IDEAS`, `$CONSTITUTION`, a    . IR`, `$N_IDEAS`, `$CONSTITUTION`, a
 .. nd `$TOPIC` are set.                   . nd `$TOPIC` are set.
 11 Date injection: `$(date +%Y-%m-%d)`    8 Date injection: `$(date +%Y-%m-%d)`
 ..  in every system prompt.               .  in every system prompt.
 12                                        9 
 13 ## Initial Generation (Step 2)        10 ## Initial Generation (Step 2)
 14                                       11 
 15 **With llmx (and not `--no-llmx`):*   12 **With external dispatch (and not `
 .. * Dispatch to an external model for   .. --no-llmx`):** Dispatch to an exter
 ..  parallel volume while you also gen   .. nal model for parallel volume while
 .. erate your own set.                   ..  you also generate your own set.
 16                                       13 
 17 ```bash                               14 ```bash
 18 llmx chat -m gemini-3.1-pro-preview   15 cat > "$BRAINSTORM_DIR/external-gen
 ..  \                                    .. eration.prompt.md" <<'EOF'
 19   ${CONSTITUTION:+-f "$BRAINSTORM_D   .. 
 .. IR/context.md"} \                     .. 
 20   --max-tokens 65536 --timeout 300    .. 
 .. \                                     .. 
 21   -o "$BRAINSTORM_DIR/external-gene   .. 
 .. ration.md" "                          .. 
 22 <system>                              16 <system>
 23 Generate approaches to the design s   17 Generate approaches to the design s
 .. pace below. Maximize breadth — $N_I   .. pace below. Maximize breadth — $N_I
 .. DEAS genuinely different approaches   .. DEAS genuinely different approaches
 .. , not variations on a theme. No fea   .. , not variations on a theme. No fea
 .. sibility filtering yet. It is $(dat   .. sibility filtering yet. It is $(dat
 .. e +%Y-%m-%d).                         .. e +%Y-%m-%d).
 24 </system>                             18 </system>
 25                                       19 
 26 [Design space + constraints + user-   20 [Design space + constraints + user-
 .. provided seeds if any]                .. provided seeds if any]
 ..                                       21 
 ..                                       22 For each approach: one paragraph on
 ..                                       ..  the mechanism and why it differs f
 ..                                       .. rom the others.
 ..                                       23 EOF
 27                                       24 
 28 For each approach: one paragraph on   25 uv run python3 ~/Projects/skills/sc
 ..  the mechanism and why it differs f   .. ripts/llm-dispatch.py \
 .. rom the others."                      .. 
 ..                                       26   --profile deep_review \
 ..                                       27   --context "$BRAINSTORM_DIR/contex
 ..                                       .. t.md" \
 ..                                       28   --prompt-file "$BRAINSTORM_DIR/ex
 ..                                       .. ternal-generation.prompt.md" \
 ..                                       29   --output "$BRAINSTORM_DIR/externa
 ..                                       .. l-generation.md"
 29 ```                                   30 ```
 30                                       31 
 31 Simultaneously, generate your own `   32 Simultaneously, generate your own `
 .. $N_IDEAS` approaches. Write to `$BR   .. $N_IDEAS` approaches. Write to `$BR
 .. AINSTORM_DIR/claude-generation.md`.   .. AINSTORM_DIR/claude-generation.md`.

brainstorm/references/llmx-dispatch.md --- 2/2 --- Text
130     > "$BRAINSTORM_DIR/all-raw.md"   131     > "$BRAINSTORM_DIR/all-raw.md" 
... 2>/dev/null                          ... 2>/dev/null
131 ```                                  132 ```
132                                      133 
133 If llmx available, dispatch extract  134 If shared dispatch is available, se
... ion to a fast model:                 ... nd extraction to a fast profile:
134                                      135 
135 ```bash                              136 ```bash
136 llmx chat -m gemini-3-flash-preview  137 uv run python3 ~/Projects/skills/sc
...  --timeout 120 \                     ... ripts/llm-dispatch.py \
...                                      138   --profile fast_extract \
137   -f "$BRAINSTORM_DIR/all-raw.md" \  139   --context "$BRAINSTORM_DIR/all-ra
...                                      ... w.md" \
138   -o "$BRAINSTORM_DIR/extraction.md  140   --prompt "
... " "                                  ... 
139 <system>                             141 <system>
140 Extract every discrete idea, approa  142 Extract every discrete idea, approa
... ch, or insight as a numbered list.   ... ch, or insight as a numbered list. 
... One per line. Tag the source (initi  ... One per line. Tag the source (initi
... al/denial-r1/denial-r2/domain/const  ... al/denial-r1/denial-r2/domain/const
... raint). Do not evaluate — extract m  ... raint). Do not evaluate — extract m
... echanically.                         ... echanically.
141 </system>                            143 </system>
142                                      144 
143 Extract all discrete ideas from the  145 Extract all discrete ideas from the
...  brainstorm artifacts."              ...  brainstorm artifacts." \
...                                      146   --output "$BRAINSTORM_DIR/extract
...                                      ... ion.md"
144 ```                                  147 ```
145                                      148 
146 If no llmx, extract yourself.        149 If no shared dispatch is available,
...                                      ...  extract yourself.

hooks/epistemic-domain-router.sh --- Bash
26     /Users/alien/Projects/selve|/Use  26     /Users/alien/Projects/selve|/Use
.. rs/alien/Projects/selve/*)            .. rs/alien/Projects/selve/*)
27       DOMAIN="research"               27       DOMAIN="research"
28       ;;                              28       ;;
29     /Users/alien/Projects/meta/exper  29     /Users/alien/Projects/agent-infr
.. iments|/Users/alien/Projects/meta/ex  .. a/experiments|/Users/alien/Projects/
.. periments/*)                          .. agent-infra/experiments/*)
30       DOMAIN="engineering"            30       DOMAIN="engineering"
31       ;;                              31       ;;
32     *)                                32     *)

hooks/generate-overview-batch.sh --- Bash
File permissions changed from 100755 to 100644.
  1 #!/usr/bin/env bash                  1 #!/usr/bin/env bash
  2 # generate-overview-batch.sh — Batc  . 
  . h all project overviews into one Ge  . 
  . mini Batch API job                   . 
  3 #                                    . 
  4 # Runs repomix for each project×typ  . 
  . e, builds JSONL, submits via llmx b  . 
  . atch.                                . 
  5 # 50% cost discount vs individual c  . 
  . alls. Results distributed to each p  . 
  . roject's output dir.                 . 
  6 #                                    . 
  7 # Usage:                             . 
  8 #   generate-overview-batch.sh       . 
  .                # Submit and wait     . 
  9 #   generate-overview-batch.sh --su  . 
  . bmit-only      # Submit, print job   . 
  . ID, exit                             . 
 10 #   generate-overview-batch.sh --ge  . 
 .. t JOB_NAME     # Fetch results from  . 
 ..  prior job                           . 
 11 #   generate-overview-batch.sh --dr  . 
 .. y-run          # Show what would be  . 
 ..  submitted                           . 
 12                                      . 
 13 set -euo pipefail                    2 set -euo pipefail
 14                                      3 
 15 SCRIPT_DIR="$(cd "$(dirname "${BASH  4 SCRIPT_DIR="$(cd "$(dirname "${BASH
 .. _SOURCE[0]}")" && pwd)"              . _SOURCE[0]}")" && pwd)"
 16 PROMPT_DIR="$SCRIPT_DIR/overview-pr  5 SKILLS_ROOT="$(cd "$SCRIPT_DIR/.." 
 .. ompts"                               . && pwd)"
 17 PROJECTS_DIR="$HOME/Projects"        6 
 18                                      . 
 19 # Projects with overview.conf        . 
 20 PROJECTS=(meta intel selve genomics  . 
 .. )                                    . 
 21                                      . 
 22 # Temp workspace                     . 
 23 WORK_DIR=$(mktemp -d /tmp/overview-  . 
 .. batch-XXXXXX)                        . 
 24 JSONL_FILE="$WORK_DIR/batch-input.j  . 
 .. sonl"                                . 
 25 MANIFEST="$WORK_DIR/manifest.json"   . 
 26                                      . 
 27 # --- Parse arguments ---            . 
 28 MODE="submit-wait"  # submit-wait |  . 
 ..  submit-only | get | dry-run         . 
 29 JOB_NAME=""                          . 
 30                                      . 
 31 while [[ $# -gt 0 ]]; do             . 
 32   case "$1" in                       . 
 33     --submit-only) MODE="submit-onl  . 
 .. y"; shift ;;                         . 
 34     --get) MODE="get"; JOB_NAME="$2  . 
 .. "; shift 2 ;;                        . 
 35     --dry-run) MODE="dry-run"; shif  . 
 .. t ;;                                 . 
 36     -h|--help)                       . 
 37       echo "Usage: generate-overvie  . 
 .. w-batch.sh [--submit-only|--get JOB  . 
 .. _NAME|--dry-run]"                    . 
 38       exit 0 ;;                      . 
 39     *) echo "Unknown option: $1" >&  . 
 .. 2; exit 1 ;;                         . 
 40   esac                               . 
 41 done                                 . 
 42                                      . 
 43 # --- Parse a project's overview.co  . 
 .. nf ---                               . 
 44 parse_conf() {                       . 
 45   local conf_file="$1"               . 
 46   # Reset to defaults                . 
 47   OVERVIEW_TYPES="source"            . 
 48   OVERVIEW_MODEL="gemini-3-flash-pr  . 
 .. eview"                               . 
 49   OVERVIEW_OUTPUT_DIR=".claude/over  . 
 .. views"                               . 
 50   OVERVIEW_PROMPT_DIR="$PROMPT_DIR"  . 
 51   OVERVIEW_EXCLUDE=""                . 
 52   OVERVIEW_NO_GITIGNORE=""           . 
 53   OVERVIEW_SOURCE_DIRS=""            . 
 54   OVERVIEW_TOOLING_DIRS=""           . 
 55                                      . 
 56   if [[ -f "$conf_file" ]]; then     . 
 57     while IFS='=' read -r key value  . 
 .. ; do                                 . 
 58       [[ "$key" =~ ^[[:space:]]*# ]  . 
 .. ] && continue                        . 
 59       [[ -z "$key" ]] && continue    . 
 60       key=$(echo "$key" | xargs)     . 
 61       value=$(echo "$value" | xargs  . 
 ..  | sed 's/^"//;s/"$//')              . 
 62       # Only set known variables     . 
 63       case "$key" in                 . 
 64         OVERVIEW_TYPES|OVERVIEW_MOD  . 
 .. EL|OVERVIEW_OUTPUT_DIR|OVERVIEW_PRO  . 
 .. MPT_DIR|\                            . 
 65         OVERVIEW_EXCLUDE|OVERVIEW_N  . 
 .. O_GITIGNORE|OVERVIEW_SOURCE_DIRS|OV  . 
 .. ERVIEW_TOOLING_DIRS)                 . 
 66           eval "$key=\"$value\""     . 
 67           ;;                         . 
 68       esac                           . 
 69     done < "$conf_file"              . 
 70   fi                                 . 
 71 }                                    . 
 72                                      . 
 73 # --- Run repomix and build prompt   . 
 .. for one project×type ---             . 
 74 build_prompt() {                     . 
 75   local project="$1"                 . 
 76   local type="$2"                    . 
 77   local project_root="$PROJECTS_DIR  . 
 .. /$project"                           . 
 78                                      . 
 79   # Read config                      . 
 80   parse_conf "$project_root/.claude  . 
 .. /overview.conf"                      . 
 81                                      . 
 82   # Get type-specific dirs           . 
 83   local dirs_var="OVERVIEW_$(echo "  . 
 .. $type" | tr '[:lower:]' '[:upper:]'  . 
 .. )_DIRS"                              . 
 84   local dirs="${!dirs_var:-}"        . 
 85   if [[ -z "$dirs" ]]; then          . 
 86     echo "SKIP: $project/$type — no  . 
 ..  dirs configured ($dirs_var)" >&2    . 
 87     return 1                         . 
 88   fi                                 . 
 89                                      . 
 90   # Resolve prompt file              . 
 91   local prompt_file                  . 
 92   if [[ "$OVERVIEW_PROMPT_DIR" = /*  . 
 ..  ]]; then                            . 
 93     prompt_file="$OVERVIEW_PROMPT_D  . 
 .. IR/${type}.md"                       . 
 94   else                               . 
 95     prompt_file="$project_root/$OVE  . 
 .. RVIEW_PROMPT_DIR/${type}.md"         . 
 96   fi                                 . 
 97   if [[ ! -f "$prompt_file" ]]; the  . 
 .. n                                    . 
 98     echo "SKIP: $project/$type — pr  . 
 .. ompt not found: $prompt_file" >&2    . 
 99     return 1                         . 
100   fi                                 . 
101                                      . 
102   # Build repomix include pattern    . 
103   local include_pattern=""           . 
104   IFS=',' read -ra DIR_ARRAY <<< "$  . 
... dirs"                                . 
105   for d in "${DIR_ARRAY[@]}"; do     . 
106     d=$(echo "$d" | xargs)           . 
107     if [[ -n "$include_pattern" ]];  . 
...  then                                . 
108       include_pattern="${include_pa  . 
... ttern},${d}**"                       . 
109     else                             . 
110       include_pattern="${d}**"       . 
111     fi                               . 
112   done                               . 
113                                      . 
114   local repomix_args=(--stdout --in  . 
... clude "$include_pattern")            . 
115   if [[ "${OVERVIEW_NO_GITIGNORE:-}  . 
... " == "true" ]]; then                 . 
116     repomix_args+=(--no-gitignore)   . 
117   fi                                 . 
118   if [[ -n "$OVERVIEW_EXCLUDE" ]];   . 
... then                                 . 
119     repomix_args+=(--ignore "$OVERV  . 
... IEW_EXCLUDE")                        . 
120   fi                                 . 
121                                      . 
122   # Run repomix from project root    . 
123   local temp_prompt="$WORK_DIR/${pr  . 
... oject}-${type}-prompt.txt"           . 
124   {                                  . 
125     echo '<instructions>'            . 
126     cat "$prompt_file"               . 
127     echo '</instructions>'           . 
128     echo ''                          . 
129     echo '<codebase>'                . 
130     (cd "$project_root" && repomix   . 
... "${repomix_args[@]}" 2>/dev/null)    . 
131     echo '</codebase>'               . 
132   } > "$temp_prompt"                 . 
133                                      . 
134   local prompt_size=$(wc -c < "$tem  . 
... p_prompt")                           . 
135   local prompt_tokens=$((prompt_siz  . 
... e / 4))                              . 
136   echo "  $project/$type: ~${prompt  . 
... _tokens} tokens" >&2                 . 
137                                      . 
138   echo "$temp_prompt"                . 
139 }                                    . 
140                                      . 
141 # --- Build JSONL from all project×  . 
... type combinations ---                . 
142 build_jsonl() {                      . 
143   echo "Building prompts..." >&2     . 
144                                      . 
145   # Track manifest for result distr  . 
... ibution: array of {key, project, ty  . 
... pe, output_path}                     . 
146   echo "[" > "$MANIFEST"             . 
147   local first=true                   . 
148   local count=0                      . 
149                                      . 
150   for project in "${PROJECTS[@]}";   . 
... do                                   . 
151     local project_root="$PROJECTS_D  . 
... IR/$project"                         . 
152     [[ -f "$project_root/.claude/ov  . 
... erview.conf" ]] || continue          . 
153                                      . 
154     parse_conf "$project_root/.clau  . 
... de/overview.conf"                    . 
155     IFS=',' read -ra TYPES <<< "$OV  . 
... ERVIEW_TYPES"                        . 
156                                      . 
157     for type in "${TYPES[@]}"; do    . 
158       type=$(echo "$type" | xargs)   . 
159       local key="${project}-${type}  . 
... "                                    . 
160                                      . 
161       local prompt_file              . 
162       prompt_file=$(build_prompt "$  . 
... project" "$type" 2>/dev/null) || co  . 
... ntinue                               . 
163                                      . 
164       # Resolve output path          . 
165       local output_dir               . 
166       if [[ "$OVERVIEW_OUTPUT_DIR"   . 
... = /* ]]; then                        . 
167         output_dir="$OVERVIEW_OUTPU  . 
... T_DIR"                               . 
168       else                           . 
169         output_dir="$project_root/$  . 
... OVERVIEW_OUTPUT_DIR"                 . 
170       fi                             . 
171       local output_path="$output_di  . 
... r/${type}-overview.md"               . 
172                                      . 
173       # Write JSONL line             . 
174       python3 -c "                   . 
175 import json, sys                     . 
176 obj = {                              . 
177     'key': sys.argv[1],              . 
178     'prompt': open(sys.argv[2]).rea  . 
... d(),                                 . 
179 }                                    . 
180 print(json.dumps(obj))               . 
181 " "$key" "$prompt_file" >> "$JSONL_  . 
... FILE"                                . 
182                                      . 
183       # Write manifest entry         . 
184       if ! $first; then echo "," >>  . 
...  "$MANIFEST"; fi                     .
... [diff truncated] ...
```

## Current File Excerpts

### .claude/overview-marker-source

```text
e858f7e178f3944813a98780e72f0952d90ddc8c
```

### .claude/overviews/source-overview.md

```text
<!-- Generated: 2026-04-09T16:29:53Z | git: e858f7e | model: gemini-3-flash-preview -->

<!-- INDEX
[SCRIPT] hooks/generate-overview.sh — Core generator: extracts codebase via repomix and updates overviews via Gemini
[SCRIPT] hooks/generate-overview-batch.sh — Batch processor for multiple project overviews using Gemini Batch API (50% cost reduction)
[SCRIPT] hooks/overview-staleness-cron.sh — Daily maintenance script that regenerates overviews if they are >7 days old
[SCRIPT] hooks/add-mcp.sh — CLI utility to add MCP server presets (exa, anki, svelte, etc.) to project configuration
[SCRIPT] hooks/agent-coord.py — Multi-session coordinator that prevents file conflicts between concurrent agents
[MODULE] hooks/commit-check-parse.py — Logic for validating git commit message structure, scopes, and trailers
[MODULE] hooks/posttool_research_reformat.py — Content transformation engine for cleaning and archiving noisy research tool outputs
[MODULE] hooks/precompact-extract.py — Epistemic extractor that preserves hedging, decisions, and open questions before context compaction
[MODULE] hooks/source-check-validator.py — Structural validator for provenance tags ([SOURCE:], [DATA], etc.) in research prose
[FLOW] codebase → repomix → Gemini → markdown — The transformation of source code into functional overviews
[FLOW] transcript → precompact-extract.py → checkpoint.md — Extraction of epistemic state to survive context window compaction
[FLOW] tool_output → research_reformat.py → archive/ — Quarantine and normalization of high-volume research data
[LIB] repomix — Codebase packing for LLM consumption
[LIB] llmx — CLI/Python interface for multi-model chat and batch processing
[LIB] jq — JSON processing for configuration and hook data
-->

### Code inventory

#### Overview Generation
Automated system for maintaining high-level documentation of the codebase.
* `hooks/generate-overview.sh`: The primary entry point for generating a single or auto-configured set of overviews.
* `hooks/generate-overview-batch.sh`: Orchestrates multiple overview requests into a single Batch API job for efficiency.
* `hooks/overview-staleness-cron.sh`: Monitors `overview-marker` files and triggers updates based on age and git activity.
* `hooks/postmerge-overview.sh`: Git hook to refresh overviews automatically after a pull or merge.
* `hooks/sessionend-overview-trigger.sh`: Analyzes session changes (LOC, structural changes) to decide if a refresh is warranted.

#### Epistemic & Research Governance
Tools for enforcing citation standards and preserving "soft" knowledge (uncertainty, rationale).
* `hooks/source-check-validator.py`: Validates that factual claims in research paths have appropriate provenance tags.
* `hooks/posttool_research_reformat.py`: Intercepts noisy MCP outputs (like paper text or search results) to normalize them for the LLM.
* `hooks/precompact-extract.py`: Scans conversation transcripts before compaction to save "epistemic content" (hedged claims, negative results) into `checkpoint.md`.
* `hooks/postwrite-frontier-timeliness.sh`: Detects citations of obsolete models (e.g., GPT-3.5) without staleness disclaimers.

#### Agent Coordination & Safety
Infrastructure for managing multiple agents and preventing common failure modes.
* `hooks/agent-coord.py`: Uses a shared `.claude/agent-work.md` file and process tracking to prevent agents from editing the same files.
* `hooks/pretool-subagent-gate.sh`: Blocks subagent spawning under high memory pressure or when runaway delegation is detected.
* `hooks/pretool-llmx-guard.sh`: Prevents "spin loops" and catches hallucinated model flags or forbidden model versions.
* `hooks/pretool-multiagent-commit-guard.sh`: Prevents global git operations (like `git add .`) when multiple agents are active in the same repo.

#### Git & Workflow Automation
Hooks that enforce project-specific conventions during the development lifecycle.
* `hooks/commit-check-parse.py`: Validates commit messages against the `[scope] Verb — why` format and suggests trailers.
* `hooks/prepare-commit-msg-session-id.sh`: Automatically appends the current `Session-ID` to git commit trailers.
* `hooks/stop-plan-gate.sh`: Blocks session termination if acceptance criteria in a plan's `verify` block are failing.
* `hooks/postcommit-propagate-check.sh`: Warns when a commit touches files that have downstream consumers listed in a dependency manifest.

### Data flow

1.  **Codebase to Overview**: `repomix` packs source files based on `OVERVIEW_DIRS` config → `generate-overview.sh` wraps this in a prompt → `llmx` sends to Gemini → Output is saved to `.claude/overviews/`.
2.  **Epistemic Preservation**: `SessionEnd` or `PreCompact` triggers → `precompact-extract.py` parses the JSONL transcript → Epistemic items (questions, hedges) are written to `.claude/checkpoint.md` → Agent reads checkpoint to resume state.
3.  **Research Archiving**: Research MCP tool returns raw data → `posttool_research_reformat.py` hashes the content → Raw data is saved to `~/.claude/tool-output-archive/` → A truncated, normalized summary is returned to the agent's context.
4.  **Telemetry**: Hooks pipe JSON metadata to `hook-trigger-log.sh` → Appended to `~/.claude/hook-triggers.jsonl` → Used for ROI and failure rate analysis.

### Key abstractions

*   **Provenance Tags**: A shared vocabulary (`[SOURCE:]`, `[DATA]`, `[INFERENCE]`, `[TRAINING-DATA]`) used across 5+ files to track the origin of factual claims.
*   **Session-ID**: A unique identifier stored in `.claude/current-session-id` used to link git commits, logs, and temporary state files across different hooks.
*   **Advisory Wrapper**: The pattern of exiting `0` while providing `additionalContext` in JSON, allowing hooks to guide the agent without hard-blocking the workflow.
*   **Plan Verify Blocks**: Executable bash snippets inside markdown plans (` ```verify `) used by `stop-verify-plan.sh` to mechanically confirm task completion.

### Dependencies

*   `repomix`: Used for packing codebase subsets into a single context for overview generation.
*   `llmx`: The primary interface for interacting with LLMs (Gemini, GPT) via CLI or Python API for batch jobs and reviews.
*   `jq`: Heavily utilized in shell scripts for robust parsing of the JSON objects passed by Claude Code hooks.
*   `pyright`: Used by `posttool-pyright-check.sh` to provide immediate feedback on Python syntax and type errors after a write.
*   `uv`: Used for fast execution of Python scripts and managing tool environments (e.g., `uv run llmx`).
```

### _archive/architect/SKILL.md

```text
---
name: Architect
description: Architectural decision-making workflow using tournament-based proposal generation and ranking. Generates proposals from multiple LLM providers (google, openai, xai) via llmx unified CLI, ranks them via tournament evaluation, optionally refines with feedback loops, and records decisions as ADRs. Use when exploring architectural alternatives, comparing implementation approaches, or making significant design decisions. Requires API keys, Python 3.10+.
---

# Architect Skill

Minimal-linear review workflow for architectural decision-making: **proposals → tournament → ADR**

## Default Migration Stance

Unless the user explicitly asks for compatibility, evaluate proposals as breaking refactors with full migration.

- Prefer architectures that replace old paths cleanly over ones that preserve them via wrappers, adapters, or phased coexistence.
- Treat compatibility layers as costs that require explicit justification, not default prudence.
- If a compatibility boundary must remain, proposals should name the live boundary and its removal condition.

## Quick Start

```bash
# Full cycle (generate → rank → optionally decide)
skills/architect/run.sh review "How should we implement event sourcing?"

# Step-by-step workflow with source context (RECOMMENDED)
cat proposal.md src/core/*.cljc | \
  skills/architect/run.sh propose "Should we add fourth kernel operation?"

skills/architect/run.sh rank <run-id>
skills/architect/run.sh decide <run-id> approve <proposal-id> "Best approach"
```

## Critical: Provide Full Context

**Lesson learned:** LLMs need complete context to understand architectural decisions correctly.

**Best prompt (95% success) - Include vision, overview, AND source:**

```bash
cat VISION.md \
    dev/overviews/AUTO-SOURCE-OVERVIEW.md \
    src/core/*.cljc | \
  skills/architect/run.sh propose "Review this architecture from first principles. \
  If the current design is already solid and elegant, say so - we don't want to \
  change unnecessarily."
```

**Good prompt (80% success):**

```bash
cat .architect/analysis/proposal.md \
    src/core/ops.cljc \
    src/plugins/selection/core.cljc | \
  skills/architect/run.sh propose "Evaluate this specific proposal"
```

**Bad prompt (0% success):**

```bash
skills/architect/run.sh propose "Should we add a fourth operation?"
# → LLMs guess what you mean, usually incorrectly
```

**Why this matters:**

- Generic descriptions → misunderstanding
- Source code context → accurate evaluation
- Vision/overview docs → understanding project goals and philosophy
- Explicit "if current is good, say so" → prevents unnecessary spiraling
- Explicit framing → focused analysis

**Context checklist:**

- [ ] Project vision/philosophy (VISION.md, CLAUDE.md, etc.)
- [ ] Architecture overview (AUTO-SOURCE-OVERVIEW.md, etc.)
- [ ] Relevant source code (use repomix for full context)
- [ ] Explicit evaluation criteria in prompt
- [ ] Permission to recommend "keep as-is"

## Commands

### `review` - Full Cycle

One-shot review: generate proposals → rank → present results

```bash
skills/architect/run.sh review "problem description"
```

**Options:**

- `--auto-decide` - Automatically approve if confidence > threshold
- `--confidence 0.85` - Confidence threshold for auto-decision (default: 0.85)
- `--constraints-file <path>` - Project constraints file (default: `.architect/project-constraints.md`)

### `propose` - Generate Proposals

Generate proposals from multiple LLM providers in parallel via llmx

```bash
skills/architect/run.sh propose "problem description"
```

**Options:**

- `--providers gemini,codex,grok,kimi2` - Specify providers (default: gemini,codex,grok)
- `--constraints-file <path>` - Project constraints file

Providers: `gemini`, `codex` (with reasoning-effort high), `grok`, `kimi2`

**Output:**

- `.architect/review-runs/{run-id}/run.json` - Run metadata
- `.architect/review-runs/{run-id}/proposal-{provider}.json` - Individual proposals
- Returns `run_id` f

... [truncated for review packet] ...

un-id}

# Decide
skills/architect/run.sh decide {run-id} approve {winner-id} "Clear and simple"
```

### Quick Decision

```bash
# Full cycle with auto-decision if confidence > 85%
skills/architect/run.sh review "State management approach" --auto-decide --confidence 0.85
```

### Refine Before Deciding

```bash
# Generate and rank
skills/architect/run.sh propose "API design patterns"
skills/architect/run.sh rank {run-id}

# Refine winner with feedback
skills/architect/run.sh refine {run-id} {winner-id} "Add error handling examples"

# Then decide
skills/architect/run.sh decide {run-id} approve {winner-id} "Complete after refinement"
```

### With Project Constraints

```bash
# Create constraints file
cat > .architect/project-constraints.md <<EOF
# Project Constraints

## Hard Requirements
- ClojureScript only
- REPL-friendly (no hidden state)
- Event sourcing architecture

## Soft Preferences
- Prefer core.async over callbacks
- Minimize dependencies
EOF

# Use constraints in review
skills/architect/run.sh review "How to handle async operations?" \
  --constraints-file .architect/project-constraints.md
```

## Integration

### With Tournament-MCP

The skill can use tournament-mcp for ranking when called from Claude Code:

```bash
# Generate proposals
skills/architect/run.sh propose "problem description"

# Then ask Claude Code to rank them
# "Use tournament MCP to rank proposals from run <run-id>"
```

**Two use cases:**

1. **Validation:** Same prompt, multiple providers → check consensus (INVALID = good!)
2. **Comparison:** Different architectures → rank by quality

### With Research Skill

Combine with research for comprehensive analysis:

```bash
# Research existing approaches
skills/research/run.sh explore re-frame "state management patterns"

# Generate proposals informed by research
skills/architect/run.sh propose "State management: re-frame vs reagent"
```

### Utility Commands

```bash
# List all review runs
skills/architect/run.sh list

# Show run details
skills/architect/run.sh show <run-id>

# View provenance ledger
skills/architect/run.sh ledger
```

## Storage Paths

| Path                             | Contents                       |
| -------------------------------- | ------------------------------ |
| `.architect/review-runs/`        | Individual review workflows    |
| `.architect/adr/`                | Architectural Decision Records |
| `.architect/review-ledger.jsonl` | Append-only provenance log     |
| `.architect/specs/`              | Refined specifications         |

## Templates

| Template | Path                              | Use                    |
| -------- | --------------------------------- | ---------------------- |
| ADR      | `data/templates/adr-template.md`  | Decision records       |
| Spec     | `data/templates/spec-template.md` | Refined specifications |

## Troubleshooting

**No API keys:**

- Set `GEMINI_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` in `.env`
- Or export in shell: `export GEMINI_API_KEY="your-key"`

**Tournament-mcp not found:**

- Ranking will use simplified comparison mode
- Install tournament-mcp for full tournament evaluation

**Empty proposals:**

- Check API key validity
- Check CLI tool is in PATH: `which llmx`
- Check `.env` is sourced

**Run not found:**

- Verify run ID: `ls .architect/review-runs/`
- Check file exists: `cat .architect/review-runs/{run-id}/run.json`

**Python command not found:**

- Install Python 3.10+ or uv
- Skill auto-detects: uv > python3 > python

## Resources (Level 3)

- `run.sh` - Main CLI wrapper
- `lib/architect.py` - Python implementation
- `data/templates/` - ADR and spec templates
- `.architect/` - All outputs and logs
- `test-variant-a.sh` - Test script for variant-a prompts
- `GPT5_IMPROVEMENTS.md` - GPT-5 integration notes

## See Also

- Project docs: `../../CLAUDE.md#agent-skills-overview`
- GPT-5 prompting: `../gpt5-prompting/SKILL.md`
- Research skill: `../research/SKILL.md`
- Tournament MCP: `~/Projects/tournament-mcp/`
```

### brainstorm/SKILL.md

```text
---
name: brainstorm
description: Divergent ideation via systematic perturbation — denial cascades, domain forcing, constraint inversion. Multi-model dispatch optional (volume, not diversity). For convergent critique, use /model-review.
argument-hint: "[--quick|--deep] [--axes denial,domain,constraint] [--domains 'jazz, geology, ...'] [--n-ideas N] design space to explore"
effort: high
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
---

# Divergent Ideation via Perturbation

You are orchestrating divergent ideation. The goal is ideas that escape the default attractor basin — the high-probability outputs that any model (including you) produces first.

**Core mechanism:** Systematic perturbation of the search space (denial, domain forcing, constraint inversion), not model diversity. Models trained on similar data converge on similar ideas regardless of vendor. The prompting structure does the work.

**This skill is DIVERGENT only.** For convergent critique, use `/model-review`.

**Late-stage warning:** When a frontier is mature, this skill should produce fewer, sharper ideas, not preserve the same idea count with weaker variants. One strong perturbation survivor is enough. If forced-domain rounds only yield reframings, stop and hand back to convergent filtering.

## Default Architectural Stance

Unless the user explicitly asks for compatibility, generate ideas as breaking refactors with full migration.

- Do not spend idea budget on wrappers, adapters, transitional bridges, or phased coexistence by default.
- Prefer ideas that delete obsolete paths and collapse complexity.
- Only keep a compatibility boundary in the design space when a live external dependency is explicitly named.

## Parameters

Parse `$ARGUMENTS` for these optional flags (order doesn't matter, remaining text is the topic):

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--quick` | — | off | 1 denial round, 2 domains, skip constraint inversion. ~5 ideas. |
| `--deep` | — | off | 3 denial rounds, 4 domains, 4 inversions. Maximum divergence. |
| `--axes` | comma-separated: `denial`, `domain`, `constraint` | all three | Run only specified perturbation axes |
| `--domains` | quoted comma-separated domain names | auto-select | Override domain forcing domains (e.g., `--domains "jazz, geology, packet switching"`) |
| `--n-ideas` | integer | 15 | Target idea count per generation round |
| `--no-llmx` | — | off | Run everything locally, no external model dispatch |

**Effort presets:** default (2 denial, 3 domains, 3 inversions, ~15/round), `--quick` (1 denial, 2 domains, no inversions, ~5/round), `--deep` (3 denial, 4 domains, 4 inversions, ~20/round).

## Prerequisites

- `llmx` CLI optional — skill works without it (you run all rounds). With llmx, perturbation rounds run in parallel for speed. Use `--no-llmx` to force local-only.

## Pre-Flight

1. **Dedup check:** Search `.brainstorm/` for synthesis.md files < 24h old on same topic. Check `git log` for cross-session brainstorms. If space already explored, target "one non-duplicate survivor or clean exhaustion proof."
2. **Constitutional check:** Find CONSTITUTION.md or constitution section in CLAUDE.md + GOALS.md. Inject as preamble so generation stays within project principles.
3. **Output setup:** Create `$BRAINSTORM_DIR` with date-slug-id naming.

See `references/synthesis-templates.md` for pre-flight scripts.

## The Process

### Step 1: Define the Design Space

State clearly: the question, current approach (if any), hard constraints vs soft preferences, evaluation criteria.

### Step 2: Initial Generation

Generate `$N_IDEAS` approaches. Cast wide — no evaluation yet. Optimize for volume and diversity over individual brilliance — research confirms LLMs are competitive with humans on creative volume but not at distribution extremes (Nature Human Behaviour 2025). More seeds = more raw material for perturbation. If user included seed ideas, diversify fr

... [truncated for review packet] ...

nt paradigms, force genuinely different approaches. Novelty rises continuously with denial depth (NEOGAUGE, NAACL 2025). This is the primary divergence mechanism. See `references/llmx-dispatch.md` for prompt templates.

**3b: Domain Forcing** — Map the problem to distant, unrelated domains. Pick from domain pools in `references/domain-pools.md`. Distant domains, not adjacent ones — the discomfort is the mechanism.

**3c: Constraint Inversion** — Flip key assumptions (e.g., "compute free but storage costs $1/byte"). Design optimal solutions under altered constraints, then identify what transfers back to reality. Skipped in `--quick` mode.

**Knowledge injection:** Before perturbation, query 2-3 tangential domain examples via Exa to prime the search space with real-world mechanisms.

**Mature frontier cutoff:** After one forced-domain pass on a mature frontier, discard duplicates/no-caller ideas, don't keep forcing more domains.

### Step 4: Extract & Enumerate (Anti-Loss Protocol)

**Do this BEFORE synthesis.** Single-pass synthesis drops ideas.

Mechanically extract every discrete idea from all artifacts into a numbered list tagged by source. Then build a disposition table: `EXPLORE`, `PARK`, `REJECT`, or `MERGE WITH [ID]`. Every extracted item must have a disposition. See `references/synthesis-templates.md` for table format and extraction scripts.

### Step 5: Synthesize

Produce ranked synthesis with: Ideas to Explore (novelty x feasibility), Parked, Rejected, Paradigm Gaps, Suggested Next Step. Save to `$BRAINSTORM_DIR/synthesis.md`. See `references/synthesis-templates.md` for output template.

### Step 5.5: Pain-Point Gate (MANDATORY before implementation)

Before offering to plan or implement ANY explore item, verify it solves a real problem:

1. `git log --oneline --all | grep -i "<topic keywords>"` — actual incidents
2. `grep -r "<topic>" ~/.claude/projects/*/memory/` — session pain moments
3. For each EXPLORE item: "This would have prevented [specific incident] on [date]"
4. If no incident: mark `SPECULATIVE` in disposition. Default to PARK, not EXPLORE.

**Why this exists:** Brainstorm session (2026-03-26) generated 47 ideas, 12 explored, 7 planned, 1 built. 6/7 layers defended against hypothetical problems with zero incident history. Absence of a feature ≠ presence of a problem.

### Step 6: Bridge to Action

If EXPLORE items survive the pain-point gate:

> "Brainstorm identified N ideas worth exploring (M survived pain-point gate). Want a plan for the top 1-2, or `/model-review` to stress-test a specific idea?"

Don't auto-implement — divergent ideas need convergent validation first.

## Anti-Patterns

- **Evaluating during generation.** Steps 2-3 generate. Steps 4-5 evaluate. Don't mix.
- **Skipping denial rounds.** Initial generation IS the attractor basin. Denial is how you escape it.
- **"Related" domains for domain forcing.** Adjacent fields converge to the same basin. Pick distant domains.
- **Implementing brainstorm output directly.** Prototype cheaply or stress-test with `/model-review` first.
- **Synthesizing without extracting.** Drops ideas silently. Always extract first.
- **Treating model choice as the diversity mechanism.** The prompting structure (denial, domains, inversions) produces divergence. Model choice is for volume and availability.

## Reference Files

| File | Contents |
|------|----------|
| `references/llmx-dispatch.md` | Prompt templates for all llmx calls (generation, denial, domain, constraint, extraction) |
| `references/domain-pools.md` | Domain forcing pools, perturbation axis presets, knowledge injection details |
| `references/synthesis-templates.md` | Disposition table format, synthesis output template, pre-flight bash scripts |

$ARGUMENTS

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] Duplicate runs — brainstorm dispatched 3x to same model when parallel subagent calls failed silently. Check subagent output before re-dispatching.**
```

### brainstorm/references/llmx-dispatch.md

```text
<!-- Reference file for brainstorm skill. Loaded on demand. -->
# llmx Dispatch Templates

> **Automation path:** use `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py` or the shared Python module in `shared/llm_dispatch.py`.
> The CLI commands below are manual prompt templates only. Do not paste them into agent automation unchanged.

All templates assume `$BRAINSTORM_DIR`, `$N_IDEAS`, `$CONSTITUTION`, and `$TOPIC` are set.
Date injection: `$(date +%Y-%m-%d)` in every system prompt.

## Initial Generation (Step 2)

**With external dispatch (and not `--no-llmx`):** Dispatch to an external model for parallel volume while you also generate your own set.

```bash
cat > "$BRAINSTORM_DIR/external-generation.prompt.md" <<'EOF'
<system>
Generate approaches to the design space below. Maximize breadth — $N_IDEAS genuinely different approaches, not variations on a theme. No feasibility filtering yet. It is $(date +%Y-%m-%d).
</system>

[Design space + constraints + user-provided seeds if any]

For each approach: one paragraph on the mechanism and why it differs from the others.
EOF

uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile deep_review \
  --context "$BRAINSTORM_DIR/context.md" \
  --prompt-file "$BRAINSTORM_DIR/external-generation.prompt.md" \
  --output "$BRAINSTORM_DIR/external-generation.md"
```

Simultaneously, generate your own `$N_IDEAS` approaches. Write to `$BRAINSTORM_DIR/claude-generation.md`.

**Without llmx (or `--no-llmx`):** Generate `$N_IDEAS` approaches yourself. Write to `$BRAINSTORM_DIR/initial-generation.md`.

## Denial Cascade (Step 3a)

Default: 2 rounds. `--quick`: 1 round. `--deep`: 3 rounds.

```bash
# Round 1
llmx chat -m gemini-3.1-pro-preview \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-r1.md" "
<system>
DENIAL ROUND. The approaches below are FORBIDDEN — you cannot use them or their variants. Propose 5 fundamentally different approaches that share no paradigm with the forbidden list. It is $(date +%Y-%m-%d).
</system>

## Forbidden Paradigms
[List 3-5 dominant paradigms from initial generation with brief descriptions]

## Design Space
[Original design space description]

For each: the mechanism, why it differs from ALL forbidden paradigms, one reason it might work."
```

```bash
# Round 2
llmx chat -m gemini-3.1-pro-preview \
  -f "$BRAINSTORM_DIR/denial-r1.md" \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-r2.md" "
<system>
DENIAL ROUND 2. Everything above is now ALSO forbidden. Go deeper — what paradigm hasn't been touched at all? What would someone from a completely unrelated field propose? 3+ approaches. It is $(date +%Y-%m-%d).
</system>

## Also Forbidden Now
[Paradigms from Round 1]

3+ approaches sharing no paradigm with anything above."
```

## Domain Forcing (Step 3b)

If `--domains` specified, use those. Otherwise pick 3 domains **unrelated** to the problem (`--quick`: 2, `--deep`: 4).

```bash
llmx chat -m gpt-5.4 \
  --reasoning-effort medium --stream --timeout 600 \
  -o "$BRAINSTORM_DIR/domain-forcing.md" "
<system>
Map a design challenge to three unrelated domains. For each domain: what's the analogous problem, how does that domain solve it, what transfers back. It is $(date +%Y-%m-%d).
</system>

## Design Challenge
[Original design space description]

## Domain 1: [chosen domain]
Analogous problem? How does this domain solve it? What transfers back?

## Domain 2: [chosen domain]
Same.

## Domain 3: [chosen domain]
Same."
```

## Constraint Inversion (Step 3c)

**Skipped in `--quick` mode.** Default: 3 inversions. `--deep`: 4 inversions.

```bash
llmx chat -m gpt-5.4 \
  --reasoning-effort medium --stream --timeout 600 \
  -o "$BRAINSTORM_DIR/constraint-inversion.md" "
<system>
For each inverted assumption, design the best solution under that altered constraint. Then identify what transfers back to reality. It is $(date +%Y-%m-%d).
</system>

## Design Space
[Original description]

## Inversion 1: [e.g., 'What if compute were free but storage cost \$1/byte?']
Best design under this constraint. What transfers back?

## Inversion 2: [e.g., 'What if we had 1000x the data but couldn't iterate?']
Best design. What transfers?

## Inversion 3: [e.g., 'What if this had to work for 50 years without updates?']
Best design. What transfers?"
```

## Extraction (Step 4)

```bash
cat "$BRAINSTORM_DIR"/*generation*.md \
    "$BRAINSTORM_DIR"/denial-r*.md \
    "$BRAINSTORM_DIR"/domain-forcing.md \
    "$BRAINSTORM_DIR"/constraint-inversion.md \
    > "$BRAINSTORM_DIR/all-raw.md" 2>/dev/null
```

If shared dispatch is available, send extraction to a fast profile:

```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile fast_extract \
  --context "$BRAINSTORM_DIR/all-raw.md" \
  --prompt "
<system>
Extract every discrete idea, approach, or insight as a numbered list. One per line. Tag the source (initial/denial-r1/denial-r2/domain/constraint). Do not evaluate — extract mechanically.
</system>

Extract all discrete ideas from the brainstorm artifacts." \
  --output "$BRAINSTORM_DIR/extraction.md"
```

If no shared dispatch is available, extract yourself.
```

### hooks/epistemic-domain-router.sh

```text
#!/usr/bin/env bash
# SessionStart / PreToolUse — detect epistemic domain from project path
# Writes domain to session-scoped temp file for other scripts to read.
# Runs once per session (skips if state file already exists).
# No user-visible output — purely sets state.

STATE_FILE="/tmp/claude-epistemic-domain-${CLAUDE_SESSION_ID:-default}"

# Already routed this session — skip
[ -f "$STATE_FILE" ] && exit 0

DOMAIN="general"
# CLAUDE_PROJECT_DIR may or may not be set; fall back to CWD
PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# 1. Override: check for explicit domain file in project root
if [ -n "$PROJECT" ] && [ -f "$PROJECT/.claude/epistemic-domain" ]; then
  DOMAIN=$(cat "$PROJECT/.claude/epistemic-domain" | tr -d '[:space:]')
else
  # 2. Path-based detection
  case "$PROJECT" in
    /Users/alien/Projects/intel|/Users/alien/Projects/intel/*)
      DOMAIN="trading"
      ;;
    /Users/alien/Projects/genomics|/Users/alien/Projects/genomics/*|\
    /Users/alien/Projects/selve|/Users/alien/Projects/selve/*)
      DOMAIN="research"
      ;;
    /Users/alien/Projects/agent-infra/experiments|/Users/alien/Projects/agent-infra/experiments/*)
      DOMAIN="engineering"
      ;;
    *)
      # Check for autoresearch context (tool input or env hint)
      if [ "${CLAUDE_TOOL_INPUT:-}" != "" ]; then
        if echo "$CLAUDE_TOOL_INPUT" | grep -qiE 'autoresearch|evolutionary.search|experiment.config' 2>/dev/null; then
          DOMAIN="engineering"
        fi
      fi
      ;;
  esac
fi

# Validate domain is one of the known values
case "$DOMAIN" in
  trading|research|engineering|general) ;;
  *) DOMAIN="general" ;;
esac

echo "$DOMAIN" > "$STATE_FILE"
exit 0
```

### hooks/generate-overview-batch.sh

```text
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec uv run python3 "$SKILLS_ROOT/scripts/generate_overview.py" batch "$@"
```

### hooks/generate-overview.sh

```text
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec uv run python3 "$SKILLS_ROOT/scripts/generate_overview.py" live "$@"
```

### hooks/overview-staleness-cron.sh

```text
#!/usr/bin/env bash
# overview-staleness-cron.sh — Daily check for stale overviews.
# Run via launchd. For each opted-in project in live mode, regenerates
# overviews if marker is >7 days old and there are changes since.

set -euo pipefail

GENERATE_SCRIPT="$HOME/Projects/skills/hooks/generate-overview.sh"
MAX_AGE_DAYS=7

# Projects to check (add more as they opt in)
PROJECTS=(
  "$HOME/Projects/intel"
  "$HOME/Projects/selve"
  "$HOME/Projects/genomics"
  "$HOME/Projects/meta"
)

for project_dir in "${PROJECTS[@]}"; do
  conf="$project_dir/.claude/overview.conf"
  [[ -f "$conf" ]] || continue

  # Read mode from config
  mode=$(grep -E '^OVERVIEW_MODE=' "$conf" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"' | xargs)
  [[ "$mode" == "live" ]] || continue

  mapfile -t configured_types < <(grep -E '^OVERVIEW_TYPES=' "$conf" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '"' | tr ',' '\n' | xargs -n1)
  if [[ ${#configured_types[@]} -eq 0 ]]; then
    continue
  fi

  marker=""
  for overview_type in "${configured_types[@]}"; do
    candidate="$project_dir/.claude/overview-marker-${overview_type}"
    if [[ -f "$candidate" ]]; then
      marker="$candidate"
      break
    fi
  done

  if [[ -z "$marker" ]]; then
    cd "$project_dir"
    "$GENERATE_SCRIPT" --auto --project-root "$project_dir" 2>/dev/null || true
    continue
  fi

  # Check marker age
  if [[ "$(uname)" == "Darwin" ]]; then
    marker_mtime=$(stat -f %m "$marker")
  else
    marker_mtime=$(stat -c %Y "$marker")
  fi
  now=$(date +%s)
  age_days=$(( (now - marker_mtime) / 86400 ))

  [[ $age_days -ge $MAX_AGE_DAYS ]] || continue

  # Check if there are changes since marker
  marker_hash=$(cat "$marker")
  cd "$project_dir"
  if ! git diff --quiet "$marker_hash"..HEAD 2>/dev/null; then
    "$GENERATE_SCRIPT" --auto --project-root "$project_dir" 2>/dev/null || true
  fi
done
```

### hooks/permission-auto-allow.sh

```text
#!/usr/bin/env bash
# permission-auto-allow.sh — PermissionRequest hook.
# Auto-approves known-safe read-only tools to reduce permission fatigue.
# Deployed disabled (not in settings.json) until hook telemetry confirms
# permission prompt frequency justifies it. Constitution principle #3.
#
# Exit 0 with JSON {"hookSpecificOutput":{"hookEventName":"PermissionRequest",
#   "decision":{"behavior":"allow"}}} to auto-allow.
# Exit 0 with no output to fall through to normal permission prompt.

trap 'exit 0' ERR

INPUT=$(cat)

TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null) || exit 0

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

allow_tool() {
    "$HOOK_DIR/hook-trigger-log.sh" "permission-auto-allow" "allow" "$1" 2>/dev/null || true
    echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
    exit 0
}

case "$TOOL" in
    Read|Glob|Grep|WebSearch|WebFetch)
        allow_tool "$TOOL"
        ;;
    Write|Edit)
        # Auto-allow writes to .claude/checkpoint.md (context-save before compaction)
        FPATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null) || true
        case "$FPATH" in
            */.claude/checkpoint.md) allow_tool "$TOOL:checkpoint" ;;
        esac
        ;;
    mcp__context7__*|mcp__research__search_papers|mcp__research__list_*|mcp__research__get_*)
        allow_tool "$TOOL"
        ;;
    mcp__brave-search__*|mcp__perplexity__*|mcp__paper-search__search_*|mcp__agent-infra__*)
        allow_tool "$TOOL"
        ;;
    Bash)
        CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null) || exit 0
        case "$CMD" in
            git\ log*|git\ diff*|git\ status*|git\ branch*|git\ show*|ls*|wc\ *|pwd|date|which\ *)
                allow_tool "Bash:${CMD:0:50}"
                ;;
        esac
        ;;
esac

# All other tools — fall through to normal permission prompt
exit 0
```

### hooks/postmerge-overview.sh

```text
#!/usr/bin/env bash
# postmerge-overview.sh — Regenerate overviews after pull/merge.
# Install as .git/hooks/post-merge in opted-in projects.
#
# Runs generation in background so it doesn't block the terminal.

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CONF="$PROJECT_ROOT/.claude/overview.conf"
GENERATE="$HOME/Projects/skills/hooks/generate-overview.sh"

[[ -f "$CONF" ]] || exit 0
[[ -x "$GENERATE" ]] || exit 0

export OVERVIEW_MODEL="gemini-3-flash-preview"

echo "Regenerating overviews after pull (background)..."
nohup "$GENERATE" --auto --project-root "$PROJECT_ROOT" > /tmp/overview-pull-$(basename "$PROJECT_ROOT").log 2>&1 &

exit 0
```

### hooks/pretool-llmx-guard.sh

```text
#!/usr/bin/env bash
# PreToolUse:Bash — catch common llmx dispatch mistakes
# Advisory (exit 0) for warnings, BLOCK (exit 2) for Gemini 2.5 and invalid flags

if [ "$CLAUDE_TOOL_NAME" != "Bash" ]; then exit 0; fi

INPUT="$CLAUDE_TOOL_INPUT"
CMD=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Only check commands that invoke llmx
echo "$CMD" | grep -q 'llmx' || exit 0

WARNINGS=""

# --- SPIN-LOOP detection (per-session llmx call counter) ---
LLMX_COUNTER="/tmp/claude-llmx-count-${PPID:-0}"
LLMX_COUNT=0
[ -f "$LLMX_COUNTER" ] && LLMX_COUNT=$(cat "$LLMX_COUNTER" 2>/dev/null || echo 0)
LLMX_COUNT=$((LLMX_COUNT + 1))
echo "$LLMX_COUNT" > "$LLMX_COUNTER"

if [ "$LLMX_COUNT" -ge 6 ]; then
  echo "[llmx-guard] BLOCKED: $LLMX_COUNT llmx calls this session. This looks like a spin loop." >&2
  echo "  - Diagnose WHY previous calls failed (check stderr, exit code)" >&2
  echo "  - Don't retry the same command — try a different model or approach" >&2
  echo "  - If rate-limited, wait or use a different provider" >&2
  # Log trigger for ROI analysis
  ~/Projects/skills/hooks/hook-trigger-log.sh "llmx-spin-loop" "block" "$LLMX_COUNT calls" 2>/dev/null || true
  exit 2
fi

if [ "$LLMX_COUNT" -ge 4 ]; then
  WARNINGS="${WARNINGS}[llmx-guard] WARNING: $LLMX_COUNT llmx calls this session. Approaching spin-loop territory.\n"
  WARNINGS="${WARNINGS}  - After 2 failures: diagnose before retrying (check stderr/exit code)\n"
  WARNINGS="${WARNINGS}  - Use --fallback for automatic model fallback on rate limits\n"
  WARNINGS="${WARNINGS}  - Blocked at 6 calls.\n"
fi

# --- BLOCKING checks (exit 2) ---

# Gemini 2.5 forbidden — user mandate: always use gemini-3.1-pro
if echo "$CMD" | grep -qiE 'gemini.?2\.5'; then
  echo "[llmx-guard] BLOCKED: Gemini 2.5 is forbidden. Use gemini-3.1-pro-preview instead." >&2
  exit 2
fi

# Invalid/hallucinated flags — these don't exist in llmx
# Known valid long flags (from `llmx chat --help`):
# --model --provider --temperature --reasoning-effort --stream --no-stream
# --compare --providers --timeout --debug --json --list-providers --no-thinking
# --use-old --fast --search --system --file --schema --max-tokens --output --fallback
INVALID_FLAGS=""
for flag in $(echo "$CMD" | grep -oE -- '--[a-z][-a-z]*' | sort -u); do
  case "$flag" in
    --model|--timeout|--max-tokens|--reasoning-effort|--fallback) ;;
    --stream|--schema|--search|--output|--fast|--use-old|--no-thinking|--debug) ;;
    --provider|--providers|--no-stream|--mini|--help|--version) ;;
    --compare|--json|--temperature|--system|--file|--list-providers) ;;
    *) INVALID_FLAGS="${INVALID_FLAGS} ${flag}" ;;
  esac
done
if [ -n "$INVALID_FLAGS" ]; then
  echo "[llmx-guard] BLOCKED: Unknown llmx flags:${INVALID_FLAGS}. Check llmx-guide skill for valid flags." >&2
  exit 2
fi

# Invalid model names — catch common hallucinations
MODEL=$(echo "$CMD" | grep -oE '(-m|--model)\s+[a-zA-Z0-9._-]+' | head -1 | sed -E 's/^(-m|--model)[[:space:]]+//; s/^[[:space:]]+//; s/[[:space:]]+$//')
if [ -n "$MODEL" ]; then
  case "$MODEL" in
    gemini-3.1-pro-preview|gemini-3-flash-preview|gemini-3.1-flash-image-preview) ;;
    gpt-5.4|gpt-5.2|gpt-5.3-chat-latest|gpt-5-codex|o4-mini) ;;
    gemini-3.1-flash-lite-preview) ;;
    claude-sonnet-4-6|claude-opus-4-6|claude-haiku-4-5) ;;
    *gemini-3.1-pro*|*gemini-3-flash*) ;; # close enough variants
    *)
      # Catch common hallucinations
      if echo "$MODEL" | grep -qE '^gemini-3\.1-pro$'; then
        echo "[llmx-guard] BLOCKED: Model 'gemini-3.1-pro' needs '-preview' suffix. Use gemini-3.1-pro-preview." >&2
        exit 2
      elif echo "$MODEL" | grep -qE '^gemini-3-flash$|^gemini-flash-3'; then
        echo "[llmx-guard] BLOCKED: Model '$MODEL' is wrong. Use gemini-3-flash-preview." >&2
        exit 2
      elif echo "$MODEL" | grep -qE '^gpt-5\.3$'; then
        echo "[llmx-guard] BLOCKED: Model 'gpt-5.3' needs '-chat-latest' suffix. Use gpt-5.3-chat-latest." >&2
        exit 2
     

... [truncated for review packet] ...

ts/skills/scripts/llm-dispatch.py \\" >&2
      echo "    --profile fast_extract \\" >&2
      echo "    --context context.md \\" >&2
      echo "    --prompt 'Analyze this' \\" >&2
      echo "    --output /tmp/result.md" >&2
      ~/Projects/skills/hooks/hook-trigger-log.sh "llmx-chat-blocked" "block" "$(echo "$CMD" | head -c 200)" 2>/dev/null || true
      exit 2
    fi
    ;;
esac

# 0a. Gemini Pro without --stream — CLI transport hangs on thinking models + piped input, hits capacity limits
#    Flash/Lite on CLI is fine (non-thinking, better capacity) — no warning needed
if echo "$CMD" | grep -qiE 'gemini-3\.1-pro|gemini-3-pro' && ! echo "$CMD" | grep -qE -- '--stream'; then
  WARNINGS="${WARNINGS}[llmx-guard] Gemini Pro without --stream. CLI transport hangs on thinking models and hits capacity limits. Add --stream for API transport. (Flash on CLI is fine.)\n"
fi

# 0b. --fallback used — model should be the model, no silent switching
if echo "$CMD" | grep -qE -- '--fallback'; then
  WARNINGS="${WARNINGS}[llmx-guard] --fallback silently switches models on failure. Prefer --stream (API transport) over --fallback (model downgrade). Diagnose failures, don't mask them.\n"
fi

# 1. Shell redirect with llmx output
if echo "$CMD" | grep -qE 'llmx\s+(chat|research|image|svg|vision)?.*[^2]>\s*["\$\./~a-zA-Z]'; then
  WARNINGS="${WARNINGS}[llmx-guard] Shell redirect detected. Use --output/-o instead of > file — shell redirects buffer until process exit.\n"
fi

# 2. PYTHONUNBUFFERED cargo cult
if echo "$CMD" | grep -qE 'PYTHONUNBUFFERED.*llmx|llmx.*PYTHONUNBUFFERED'; then
  WARNINGS="${WARNINGS}[llmx-guard] PYTHONUNBUFFERED does nothing for llmx output capture. Use --output/-o flag instead.\n"
fi

# 3. stdbuf/script with llmx
if echo "$CMD" | grep -qE '(stdbuf|script\s+-q).*llmx'; then
  WARNINGS="${WARNINGS}[llmx-guard] stdbuf/script won't fix output buffering. Use --output/-o flag instead.\n"
fi

# 4. max_tokens with GPT-5.x reasoning models — warn about small values
if echo "$CMD" | grep -qE 'gpt-5\.[234]' && echo "$CMD" | grep -qE -- '--max-tokens\s+[0-9]{1,4}(\s|$)'; then
  WARNINGS="${WARNINGS}[llmx-guard] Small --max-tokens with GPT-5.x reasoning model. max_completion_tokens includes reasoning tokens — use 16384+ to avoid truncated output.\n"
fi

# 5. Old LiteLLM model prefixes (deprecated in v0.6.0)
if echo "$CMD" | grep -qE 'llmx.*(-m|--model)\s+(gemini/|openai/|xai/|moonshot/)'; then
  WARNINGS="${WARNINGS}[llmx-guard] LiteLLM-style model prefix detected. Prefixes are deprecated in v0.6.0 — use bare model names.\n"
fi

# 6. Stdin pipe + prompt arg (stdin silently dropped — use -f instead)
if echo "$CMD" | grep -qE '(\||cat\s).*llmx' && echo "$CMD" | grep -qE 'llmx\s+chat\s' && echo "$CMD" | grep -vqE '\s-f\s'; then
  # Only warn if there's a trailing prompt argument (not just piped input)
  if echo "$CMD" | grep -qE 'llmx\s+chat\s.*"'; then
    WARNINGS="${WARNINGS}[llmx-guard] Piping stdin + prompt argument — stdin is silently dropped. Use -f FILE instead of cat FILE | llmx. (Fixed in gemini-cli 0.32.1: -f works now.)\n"
  fi
fi

# 7. Background dispatch without -o (output lost)
if echo "$CMD" | grep -qE 'llmx.*&\s*$' && ! echo "$CMD" | grep -qE -- '--output|-o\s'; then
  WARNINGS="${WARNINGS}[llmx-guard] Background llmx (&) without --output/-o. Output will be lost. Add -o file.md.\n"
fi

# 8. Suppressing llmx stderr hides the real failure cause
if echo "$CMD" | grep -qE 'llmx.*2>\s*/dev/null|2>/dev/null.*llmx'; then
  WARNINGS="${WARNINGS}[llmx-guard] llmx stderr is redirected to /dev/null. This hides transport/quota diagnostics; capture stderr to a file instead.\n"
fi

# 9. Downstream shell consumers can mask llmx exit codes
if echo "$CMD" | grep -qE 'llmx.*\|\s*(head|tail|sed|awk)\b'; then
  WARNINGS="${WARNINGS}[llmx-guard] llmx output is piped into a shell consumer. Without 'set -o pipefail', the shell reports the consumer's exit code, not llmx's.\n"
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS" >&2
fi
exit 0
```

### Omitted Files

```text
(Omitted 12 additional touched files from excerpts.)
```
