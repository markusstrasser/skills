# Plan-Close Review Packet

- Repo: `/Users/alien/Projects/skills`
- Mode: `worktree`
- Ref: `HEAD vs current worktree`
- Profile: `formal_review`
- diff_char_cap: `40000`
- file_char_cap: `8000`
- max_file_count: `12`

## Scope

Scope: close review for the skill hardening migration. Review only the listed files. Focus on correctness regressions, caller drift, contract/runtime mismatches, missing tests, and misleading docs. Ignore unrelated dirty files and generated artifacts.

## Touched Files

### Touched Files

- `shared/skill_manifest.py`
- `scripts/lint_skill_manifests.py`
- `scripts/test_skill_manifest.py`
- `review/scripts/model-review.py`
- `review/scripts/test_model_review.py`
- `review/SKILL.md`
- `review/references/dispatch.md`
- `review/references/extraction.md`
- `review/references/prompts.md`
- `review/references/biases-and-antipatterns.md`
- `review/lenses/adversarial-review.md`
- `observe/scripts/observe_artifacts.py`
- `observe/scripts/session-shape.py`
- `observe/scripts/session_shape.py`
- `observe/scripts/validate_session_ids.py`
- `observe/tests/test_observe_artifacts.py`
- `observe/SKILL.md`
- `brainstorm/SKILL.md`
- `brainstorm/references/llmx-dispatch.md`
- `brainstorm/references/synthesis-templates.md`
- `brainstorm/tests/test_brainstorm_contract.py`
- `modal/SKILL.md`
- `modal/references/status-reconciliation.md`
- `upgrade/SKILL.md`
- `upgrade/references/model-prompts-standard.md`
- `upgrade/references/cross-validation.md`
- `upgrade/references/phase-5-review.md`
- `research-ops/SKILL.md`

## Git Status

### git status --short

```text
M .claude/telemetry/llm-dispatch.jsonl
 M _archive/code-review/code-review
 M brainstorm/SKILL.md
 M brainstorm/references/domain-pools.md
 M brainstorm/references/llmx-dispatch.md
 M brainstorm/references/synthesis-templates.md
 M hooks/stop-plan-gate.sh
 M modal/SKILL.md
 M modal/references/resources.md
 M observe/SKILL.md
 M observe/references/corrections-mode.md
 M observe/references/existing-infra-checks.md
 M observe/references/findings-staging.md
 M observe/references/gemini-dispatch-prompt.md
 M observe/references/gemini-prompt.md
 M observe/references/loop-mode.md
 M observe/references/output-template.md
 M observe/references/transcript-extraction.md
 M observe/scripts/session-shape.py
 M observe/scripts/validate_session_ids.py
 M references/data-acquisition/data-acquisition
 M references/source-grading/source-grading
 M research-ops/SKILL.md
 M review/SKILL.md
 M review/lenses/adversarial-review.md
 M review/lenses/plan-close-review.md
 M review/references/biases-and-antipatterns.md
 M review/references/dispatch.md
 M review/references/extraction.md
 M review/references/prompts.md
 M review/scripts/model-review.py
 M review/scripts/test_model_review.py
 M upgrade/SKILL.md
 M upgrade/references/cross-validation.md
 M upgrade/references/json-parsing.md
 M upgrade/references/model-prompts-harness.md
 M upgrade/references/model-prompts-standard.md
 M upgrade/references/operational-discipline.md
 M upgrade/references/phase-3-research.md
 M upgrade/references/phase-5-review.md
?? .model-review/2026-04-10-skill-hardening-close-context.manifest.json
?? .model-review/2026-04-10-skill-hardening-close-context.md
?? .model-review/2026-04-10-skill-hardening-close-ea836b/arch-extraction.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/arch-extraction.meta.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/arch-extraction.parsed.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/arch-output.md
?? .model-review/2026-04-10-skill-hardening-close-ea836b/arch-output.meta.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/coverage.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/disposition.md
?? .model-review/2026-04-10-skill-hardening-close-ea836b/findings.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/formal-extraction.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/formal-extraction.meta.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/formal-extraction.parsed.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/formal-output.md
?? .model-review/2026-04-10-skill-hardening-close-ea836b/formal-output.meta.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/shared-context.manifest.json
?? .model-review/2026-04-10-skill-hardening-close-ea836b/shared-context.md
?? .model-review/2026-04-10-skill-hardening-close-ea836b/verified-disposition.md
?? brainstorm/skill.json
?? brainstorm/tests/test_brainstorm_contract.py
?? hooks/pretool-genomics-mcp-routing.sh
?? modal/references/attribution.md
?? modal/references/status-reconciliation.md
?? modal/skill.json
?? observe/references/artifact-contract.md
?? observe/scripts/observe_artifacts.py
?? observe/scripts/session_shape.py
?? observe/skill.json
?? observe/tests/test_observe_artifacts.py
?? review/skill.json
?? scripts/lint_skill_manifests.py
?? scripts/test_modal_attribution_contract.py
?? scripts/test_skill_manifest.py
?? shared/skill_manifest.py
?? upgrade/skill.json
```

### git diff --stat

```text
brainstorm/SKILL.md                          |  37 ++--
 brainstorm/references/llmx-dispatch.md       |  86 +++++----
 brainstorm/references/synthesis-templates.md |  73 +++++++-
 modal/SKILL.md                               | 216 ++++++++++++++--------
 observe/SKILL.md                             |  92 ++++++----
 observe/scripts/session-shape.py             |  90 +++++++++-
 observe/scripts/validate_session_ids.py      |  28 +--
 research-ops/SKILL.md                        |   6 +-
 review/SKILL.md                              |  28 ++-
 review/lenses/adversarial-review.md          |  31 ++--
 review/references/biases-and-antipatterns.md |   4 +-
 review/references/dispatch.md                | 180 ++++++-------------
 review/references/extraction.md              |  70 ++++----
 review/references/prompts.md                 |  58 +++---
 review/scripts/model-review.py               | 239 +++++++++++++++++++++---
 review/scripts/test_model_review.py          | 259 +++++++++++++++++++++++++++
 upgrade/SKILL.md                             |   6 +-
 upgrade/references/cross-validation.md       |  79 ++++----
 upgrade/references/model-prompts-standard.md | 218 ++++++++--------------
 upgrade/references/phase-5-review.md         |  54 +++---
 20 files changed, 1213 insertions(+), 641 deletions(-)
```

### Unified Diff

```diff
brainstorm/SKILL.md --- 1/6 --- Text
 19                                       19 
 20 **Core mechanism:** Systematic pert   20 **Core mechanism:** Systematic pert
 .. urbation of the search space (denia   .. urbation of the search space (denia
 .. l, domain forcing, constraint inver   .. l, domain forcing, constraint inver
 .. sion), not model diversity. Models    .. sion), not model diversity. Models 
 .. trained on similar data converge on   .. trained on similar data converge on
 ..  similar ideas regardless of vendor   ..  similar ideas regardless of vendor
 .. . The prompting structure does the    .. . The prompting structure does the 
 .. work.                                 .. work.
 21                                       21 
 22 **This skill is DIVERGENT only.** F   22 **This skill is DIVERGENT only.** I
 .. or convergent critique, use `/model   .. t produces candidate space and cove
 .. -review`.                             .. rage artifacts, not final selection
 ..                                       .. s or implementation plans. For conv
 ..                                       .. ergent critique, use `/model-review
 ..                                       .. `.
 23                                       23 
 24 **Late-stage warning:** When a fron   24 **Late-stage warning:** When a fron
 .. tier is mature, this skill should p   .. tier is mature, this skill should p
 .. roduce fewer, sharper ideas, not pr   .. roduce fewer, sharper ideas, not pr
 .. eserve the same idea count with wea   .. eserve the same idea count with wea
 .. ker variants. One strong perturbati   .. ker variants. One strong perturbati
 .. on survivor is enough. If forced-do   .. on survivor is enough. If forced-do
 .. main rounds only yield reframings,    .. main rounds only yield reframings, 
 .. stop and hand back to convergent fi   .. stop and hand back to convergent fi
 .. ltering.                              .. ltering.
 25                                       25 

brainstorm/SKILL.md --- 2/6 --- Text
 42 | `--axes` | comma-separated: `deni   42 | `--axes` | comma-separated: `deni
 .. al`, `domain`, `constraint` | all t   .. al`, `domain`, `constraint` | all t
 .. hree | Run only specified perturbat   .. hree | Run only specified perturbat
 .. ion axes |                            .. ion axes |
 43 | `--domains` | quoted comma-separa   43 | `--domains` | quoted comma-separa
 .. ted domain names | auto-select | Ov   .. ted domain names | auto-select | Ov
 .. erride domain forcing domains (e.g.   .. erride domain forcing domains (e.g.
 .. , `--domains "jazz, geology, packet   .. , `--domains "jazz, geology, packet
 ..  switching"`) |                       ..  switching"`) |
 44 | `--n-ideas` | integer | 15 | Targ   44 | `--n-ideas` | integer | 15 | Targ
 .. et idea count per generation round    .. et idea count per generation round 
 .. |                                     .. |
 45 | `--no-llmx` | — | off | Run every   45 | `--no-llmx` | — | off | Run every
 .. thing locally, no external model di   .. thing locally, no external dispatch
 .. spatch |                              ..  |
 46                                       46 
 47 **Effort presets:** default (2 deni   47 **Effort presets:** default (2 deni
 .. al, 3 domains, 3 inversions, ~15/ro   .. al, 3 domains, 3 inversions, ~15/ro
 .. und), `--quick` (1 denial, 2 domain   .. und), `--quick` (1 denial, 2 domain
 .. s, no inversions, ~5/round), `--dee   .. s, no inversions, ~5/round), `--dee
 .. p` (3 denial, 4 domains, 4 inversio   .. p` (3 denial, 4 domains, 4 inversio
 .. ns, ~20/round).                       .. ns, ~20/round).
 48                                       48 
 49 ## Prerequisites                      49 ## Prerequisites
 50                                       50 
 51 - `llmx` CLI optional — skill works   51 - Shared external-dispatch helper o
 ..  without it (you run all rounds). W   .. ptional — skill works without it (y
 .. ith llmx, perturbation rounds run i   .. ou run all rounds). With external d
 .. n parallel for speed. Use `--no-llm   .. ispatch, perturbation rounds run in
 .. x` to force local-only.               ..  parallel for speed. Use `--no-llmx
 ..                                       .. ` to force local-only.
 52                                       52 
 53 ## Pre-Flight                         53 ## Pre-Flight
 54                                       54 
 55 1. **Dedup check:** Search `.brains   55 1. **Dedup check:** Search `.brains
 .. torm/` for synthesis.md files < 24h   .. torm/` for synthesis.md files < 24h
 ..  old on same topic. Check `git log`   ..  old on same topic. Check `git log`
 ..  for cross-session brainstorms. If    ..  for cross-session brainstorms. If 
 .. space already explored, target "one   .. space already explored, target "one
 ..  non-duplicate survivor or clean ex   ..  non-duplicate survivor or clean ex
 .. haustion proof."                      .. haustion proof."
 56 2. **Constitutional check:** Find C   56 2. **Constitutional check:** Find C
 .. ONSTITUTION.md or constitution sect   .. ONSTITUTION.md or constitution sect
 .. ion in CLAUDE.md + GOALS.md. Inject   .. ion in CLAUDE.md + GOALS.md. Inject
 ..  as preamble so generation stays wi   ..  as preamble so generation stays wi
 .. thin project principles.              .. thin project principles.
 57 3. **Output setup:** Create `$BRAIN   57 3. **Packet setup:** Reuse the shar
 .. STORM_DIR` with date-slug-id naming   .. ed packet spine for topic, constitu
 .. .                                     .. tion/goals, recent incidents, and p
 ..                                       .. rior brainstorm artifacts. Do not h
 ..                                       .. and-roll an unbounded context blob 
 ..                                       .. when the packet builder exists.
 ..                                       58 4. **Output setup:** Create `$BRAIN
 ..                                       .. STORM_DIR` with date-slug-id naming
 ..                                       .. .
 58                                       59 
 59 See `references/synthesis-templates   60 See `references/synthesis-templates
 .. .md` for pre-flight scripts.          .. .md` for pre-flight scripts.
 60                                       61 

brainstorm/SKILL.md --- 3/6 --- Text
 66                                       67 
 67 ### Step 2: Initial Generation        68 ### Step 2: Initial Generation
 68                                       69 
 69 Generate `$N_IDEAS` approaches. Cas   70 Generate `$N_IDEAS` approaches. Cas
 .. t wide — no evaluation yet. Optimiz   .. t wide — no evaluation yet. Optimiz
 .. e for volume and diversity over ind   .. e for volume and diversity over ind
 .. ividual brilliance — research confi   .. ividual brilliance. More seeds = mo
 .. rms LLMs are competitive with human   .. re raw material for perturbation. I
 .. s on creative volume but not at dis   .. f user included seed ideas, diversi
 .. tribution extremes (Nature Human Be   .. fy from there.
 .. haviour 2025). More seeds = more ra   .. 
 .. w material for perturbation. If use   .. 
 .. r included seed ideas, diversify fr   .. 
 .. om there.                             .. 
 70                                       71 
 71 With llmx: dispatch external model    72 With external dispatch: dispatch a 
 .. in parallel while generating your o   .. parallel external pass while genera
 .. wn set. See `references/llmx-dispat   .. ting your own set. See `references/
 .. ch.md` for templates.                 .. llmx-dispatch.md` for prompt payloa
 ..                                       .. ds and artifact contracts.
 72                                       73 
 73 ### Step 3: Perturbation Rounds (Th   74 ### Step 3: Perturbation Rounds (Th
 .. e Core Mechanism)                     .. e Core Mechanism)
 74                                       75 
 75 Run axes specified by `--axes` (def   76 Run axes specified by `--axes` (def
 .. ault: all three). With llmx, dispat   .. ault: all three). With external dis
 .. ch active axes in parallel (multipl   .. patch, fan out active axes in paral
 .. e Bash calls, `timeout: 360000`). W   .. lel. Without it, run sequentially.
 .. ithout llmx, run sequentially.        .. 
 76                                       77 
 77 First: identify the 3-5 dominant pa   78 First: identify the 3-5 dominant pa
 .. radigms from Step 2. These are what   .. radigms from Step 2. These are what
 ..  we're escaping.                      ..  we're escaping.
 78                                       79 
 79 **3a: Denial Cascade** — Ban domina   80 **3a: Denial Cascade** — Ban domina
 .. nt paradigms, force genuinely diffe   .. nt paradigms, force genuinely diffe
 .. rent approaches. Novelty rises cont   .. rent approaches. Novelty rises cont
 .. inuously with denial depth (NEOGAUG   .. inuously with denial depth (NEOGAUG
 .. E, NAACL 2025). This is the primary   .. E, NAACL 2025). This is the primary
 ..  divergence mechanism. See `referen   ..  divergence mechanism. See `referen
 .. ces/llmx-dispatch.md` for prompt te   .. ces/llmx-dispatch.md` for prompt pa
 .. mplates.                              .. yloads.
 80                                       81 
 81 **3b: Domain Forcing** — Map the pr   82 **3b: Domain Forcing** — Map the pr
 .. oblem to distant, unrelated domains   .. oblem to distant, unrelated domains
 .. . Pick from domain pools in `refere   .. . Pick from domain pools in `refere
 .. nces/domain-pools.md`. Distant doma   .. nces/domain-pools.md`. Distant doma
 .. ins, not adjacent ones — the discom   .. ins, not adjacent ones — the discom
 .. fort is the mechanism.                .. fort is the mechanism.
 82                                       83 

brainstorm/SKILL.md --- 4/6 --- Text
 86                                       87 
 87 **Mature frontier cutoff:** After o   88 **Mature frontier cutoff:** After o
 .. ne forced-domain pass on a mature f   .. ne forced-domain pass on a mature f
 .. rontier, discard duplicates/no-call   .. rontier, discard duplicates/no-call
 .. er ideas, don't keep forcing more d   .. er ideas, don't keep forcing more d
 .. omains.                               .. omains.
 88                                       89 
 ..                                       90 ### Step 3.5: Build Coverage Artifa
 ..                                       .. cts
 ..                                       91 
 ..                                       92 Before synthesis, create the struct
 ..                                       .. ured coverage artifacts first, then
 ..                                       ..  render the operator views:
 ..                                       93 
 ..                                       94 - `$BRAINSTORM_DIR/matrix.json` — o
 ..                                       .. ne row per idea/cell with axis, dom
 ..                                       .. ain row, paradigm escaped, transfer
 ..                                       ..  mechanism, and disposition fields.
 ..                                       95 - `$BRAINSTORM_DIR/matrix.md` — ren
 ..                                       .. dered coverage table for operator r
 ..                                       .. eview.
 ..                                       96 - `$BRAINSTORM_DIR/coverage.json` —
 ..                                       ..  requested axes, executed axes, cou
 ..                                       .. nts, uncovered cells, merge counts,
 ..                                       ..  and mature-frontier stop reason.
 ..                                       97 
 ..                                       98 If you cannot populate `matrix.json
 ..                                       .. ` without hand-waving, stop. The fr
 ..                                       .. ontier is not covered enough to syn
 ..                                       .. thesize yet.
 ..                                       99 
 89 ### Step 4: Extract & Enumerate (An  100 ### Step 4: Extract & Enumerate (An
 .. ti-Loss Protocol)                    ... ti-Loss Protocol)
 90                                      101 
 91 **Do this BEFORE synthesis.** Singl  102 **Do this BEFORE synthesis.** Singl
 .. e-pass synthesis drops ideas.        ... e-pass synthesis drops ideas.
 92                                      103 
 93 Mechanically extract every discrete  104 Mechanically extract every discrete
 ..  idea from all artifacts into a num  ...  idea from all artifacts into a num
 .. bered list tagged by source. Then b  ... bered list tagged by source and mat
 .. uild a disposition table: `EXPLORE`  ... rix cell. Then build a disposition 
 .. , `PARK`, `REJECT`, or `MERGE WITH   ... table: `EXPLORE`, `PARK`, `REJECT`,
 .. [ID]`. Every extracted item must ha  ...  or `MERGE WITH [ID]`. Every extrac
 .. ve a disposition. See `references/s  ... ted item must have a disposition, a
 .. ynthesis-templates.md` for table fo  ... nd the disposition table should ren
 .. rmat and extraction scripts.         ... der from the same `matrix.json` row
 ..                                      ... s rather than becoming a second sou
 ..                                      ... rce of truth. See `references/synth
 ..                                      ... esis-templates.md` for the matrix, 
 ..                                      ... coverage, and extraction templates.
 94                                      105 
 95 ### Step 5: Synthesize               106 ### Step 5: Synthesize
 96                                      107 

brainstorm/SKILL.md --- 5/6 --- Text
104 115 2. `grep -r "<topic>" ~/.claude/projects/*/memory/` — session pain moments
105 116 3. For each EXPLORE item: "This would have prevented [specific incident] on [date]"
106 117 4. If no incident: mark `SPECULATIVE` in disposition. Default to PARK, not EXPLORE.
... 118 
... 119 This gate exists to populate `caller_evidence`, `speculative`, and final disposition support. It is not a convergent review pass and should not turn brainstorm into a findings engine.
107 120 
108 121 **Why this exists:** Brainstorm session (2026-03-26) generated 47 ideas, 12 explored, 7 planned, 1 built. 6/7 layers defended against hypothetical problems with zero incident history. Absence of a feature ≠ presence of a problem.
109 122 

brainstorm/SKILL.md --- 6/6 --- Text
121 - **Skipping denial rounds.** Initi  134 - **Skipping denial rounds.** Initi
... al generation IS the attractor basi  ... al generation IS the attractor basi
... n. Denial is how you escape it.      ... n. Denial is how you escape it.
122 - **"Related" domains for domain fo  135 - **"Related" domains for domain fo
... rcing.** Adjacent fields converge t  ... rcing.** Adjacent fields converge t
... o the same basin. Pick distant doma  ... o the same basin. Pick distant doma
... ins.                                 ... ins.
123 - **Implementing brainstorm output   136 - **Implementing brainstorm output 
... directly.** Prototype cheaply or st  ... directly.** Prototype cheaply or st
... ress-test with `/model-review` firs  ... ress-test with `/model-review` firs
... t.                                   ... t.
...                                      137 - **Skipping coverage artifacts.** 
...                                      ... If you cannot name the matrix cells
...                                      ...  you covered, you do not yet know w
...                                      ... hat was actually explored.
...                                      138 - **Using brainstorm as a decision 
...                                      ... memo.** It produces candidate space
...                                      ...  plus coverage, not the final call.
124 - **Synthesizing without extracting  139 - **Synthesizing without extracting
... .** Drops ideas silently. Always ex  ... .** Drops ideas silently. Always ex
... tract first.                         ... tract first.
125 - **Treating model choice as the di  140 - **Treating model choice as the di
... versity mechanism.** The prompting   ... versity mechanism.** The prompting 
... structure (denial, domains, inversi  ... structure (denial, domains, inversi
... ons) produces divergence. Model cho  ... ons) produces divergence. Model cho
... ice is for volume and availability.  ... ice is for volume and availability.
126                                      141 
127 ## Reference Files                   142 ## Reference Files
128                                      143 
129 | File | Contents |                  144 | File | Contents |
130 |------|----------|                  145 |------|----------|
131 | `references/llmx-dispatch.md` | P  146 | `references/llmx-dispatch.md` | S
... rompt templates for all llmx calls   ... hared dispatch prompt payloads, pac
... (generation, denial, domain, constr  ... ket expectations, and artifact cont
... aint, extraction) |                  ... ract |
132 | `references/domain-pools.md` | Do  147 | `references/domain-pools.md` | Do
... main forcing pools, perturbation ax  ... main forcing pools, perturbation ax
... is presets, knowledge injection det  ... is presets, knowledge injection det
... ails |                               ... ails |
133 | `references/synthesis-templates.m  148 | `references/synthesis-templates.m
... d` | Disposition table format, synt  ... d` | Matrix, coverage, disposition 
... hesis output template, pre-flight b  ... table, synthesis output template, p
... ash scripts |                        ... re-flight bash scripts |
134                                      149 
135 $ARGUMENTS                           150 $ARGUMENTS
136                                      151 

brainstorm/references/llmx-dispatch.md --- 1/5 --- Text
  1 <!-- Reference file for brainstorm     1 <!-- Reference file for brainstorm 
  . skill. Loaded on demand. -->           . skill. Loaded on demand. -->
  2 # llmx Dispatch Templates              2 # Shared Dispatch Prompt Payloads
  3                                        3 
  4 > **Automation path:** use `uv run     4 > **Automation path:** use `uv run 
  . python3 ~/Projects/skills/scripts/l    . python3 ~/Projects/skills/scripts/l
  . lm-dispatch.py` or the shared Pytho    . lm-dispatch.py` or the shared Pytho
  . n module in `shared/llm_dispatch.py    . n module in `shared/llm_dispatch.py
  . `.                                     . `.
  5 > The CLI commands below are manual    5 > This file defines prompt payloads
  .  prompt templates only. Do not past    .  and artifact contracts. It does no
  . e them into agent automation unchan    . t teach raw CLI transport use.
  . ged.                                   . 
  6                                        6 
  7 All templates assume `$BRAINSTORM_D    7 All templates assume `$BRAINSTORM_D
  . IR`, `$N_IDEAS`, `$CONSTITUTION`, a    . IR`, `$N_IDEAS`, `$CONSTITUTION`, a
  . nd `$TOPIC` are set.                   . nd `$TOPIC` are set.
  .                                        8 If the shared packet builder is ava
  .                                        . ilable, use its output as `context.
  .                                        . md` instead of assembling an ad hoc
  .                                        .  context blob.
  8 Date injection: `$(date +%Y-%m-%d)`    9 Date injection: `$(date +%Y-%m-%d)`
  .  in every system prompt.               .  in every system prompt.
  9                                       10 
 10 ## Initial Generation (Step 2)        11 ## Initial Generation (Step 2)

brainstorm/references/llmx-dispatch.md --- 2/5 --- Text
 26   --profile deep_review \             27   --profile deep_review \
 27   --context "$BRAINSTORM_DIR/contex   28   --context "$BRAINSTORM_DIR/contex
 .. t.md" \                               .. t.md" \
 28   --prompt-file "$BRAINSTORM_DIR/ex   29   --prompt-file "$BRAINSTORM_DIR/ex
 .. ternal-generation.prompt.md" \        .. ternal-generation.prompt.md" \
 29   --output "$BRAINSTORM_DIR/externa   30   --output "$BRAINSTORM_DIR/externa
 .. l-generation.md"                      .. l-generation.md" \
 ..                                       31   --meta "$BRAINSTORM_DIR/dispatch.
 ..                                       .. meta.json"
 30 ```                                   32 ```
 31                                       33 
 32 Simultaneously, generate your own `   34 Simultaneously, generate your own `
 .. $N_IDEAS` approaches. Write to `$BR   .. $N_IDEAS` approaches. Write to `$BR
 .. AINSTORM_DIR/claude-generation.md`.   .. AINSTORM_DIR/claude-generation.md`.
 33                                       35 
 34 **Without llmx (or `--no-llmx`):**    36 **Without external dispatch (or `--
 .. Generate `$N_IDEAS` approaches your   .. no-llmx`):** Generate `$N_IDEAS` ap
 .. self. Write to `$BRAINSTORM_DIR/ini   .. proaches yourself. Write to `$BRAIN
 .. tial-generation.md`.                  .. STORM_DIR/initial-generation.md`.
 35                                       37 
 ..                                       38 ## Artifact Contract
 ..                                       39 
 ..                                       40 Every brainstorm run should emit th
 ..                                       .. ese files before synthesis:
 ..                                       41 
 ..                                       42 - `matrix.json` — canonical row sto
 ..                                       .. re for ideas, source rounds, axes, 
 ..                                       .. domains, paradigms escaped, transfe
 ..                                       .. r mechanisms, and dispositions.
 ..                                       43 - `matrix.md` — rendered coverage m
 ..                                       .. atrix for operator review.
 ..                                       44 - `coverage.json` — aggregate count
 ..                                       .. s, uncovered cells, duplicate/merge
 ..                                       ..  counts, and stop reason.
 ..                                       45 - `extraction.md` — mechanically ex
 ..                                       .. tracted idea list with source tags.
 ..                                       46 - `synthesis.md` — ranked dispositi
 ..                                       .. on after the coverage gate.
 ..                                       47 
 ..                                       48 If a file cannot be populated, the 
 ..                                       .. run is incomplete.
 ..                                       49 
 36 ## Denial Cascade (Step 3a)           50 ## Denial Cascade (Step 3a)
 37                                       51 
 38 Default: 2 rounds. `--quick`: 1 rou   52 Default: 2 rounds. `--quick`: 1 rou
 .. nd. `--deep`: 3 rounds.               .. nd. `--deep`: 3 rounds.
 39                                       53 
 40 ```bash                               .. 
 41 # Round 1                             54 Send the prompt below through the s
 ..                                       .. hared dispatch helper. The payload 
 ..                                       .. is the contract; the transport is a
 ..                                       .. n implementation detail.
 42 llmx chat -m gemini-3.1-pro-preview   55 
 ..  \                                    .. 
 43   --max-tokens 65536 --timeout 300    .. 
 .. \                                     .. 
 44   -o "$BRAINSTORM_DIR/denial-r1.md"   56 ```md
 ..  "                                    .. 
 45 <system>                              57 <system>
 46 DENIAL ROUND. The approaches below    58 DENIAL ROUND. The approaches below 
 .. are FORBIDDEN — you cannot use them   .. are FORBIDDEN - you cannot use them
 ..  or their variants. Propose 5 funda   ..  or their variants. Propose 5 funda
 .. mentally different approaches that    .. mentally different approaches that 
 .. share no paradigm with the forbidde   .. share no paradigm with the forbidde
 .. n list. It is $(date +%Y-%m-%d).      .. n list. It is $(date +%Y-%m-%d).
 47 </system>                             59 </system>
 48                                       60 
 49 ## Forbidden Paradigms                61 ## Forbidden Paradigms

brainstorm/references/llmx-dispatch.md --- 3/5 --- Text
 52 ## Design Space                       64 ## Design Space
 53 [Original design space description]   65 [Original design space description]
 54                                       66 
 55 For each: the mechanism, why it dif   67 For each: the mechanism, why it dif
 .. fers from ALL forbidden paradigms,    .. fers from ALL forbidden paradigms, 
 .. one reason it might work."            .. one reason it might work.
 56 ```                                   68 ```
 57                                       69 
 58 ```bash                               .. 
 59 # Round 2                             70 For a second pass, feed the prior d
 ..                                       .. enial output back through the same 
 ..                                       .. helper with every prior paradigm ma
 ..                                       .. rked forbidden and request 3+ new a
 ..                                       .. pproaches. Do not reuse the same tr
 ..                                       .. ansport-specific prompt in the docs
 ..                                       .. ; keep the payload stable and let t
 ..                                       .. he dispatcher route it.
 60 llmx chat -m gemini-3.1-pro-preview   .. 
 ..  \                                    .. 
 61   -f "$BRAINSTORM_DIR/denial-r1.md"   .. 
 ..  \                                    .. 
 62   --max-tokens 65536 --timeout 300    .. 
 .. \                                     .. 
 63   -o "$BRAINSTORM_DIR/denial-r2.md"   .. 
 ..  "                                    .. 
 64 <system>                              .. 
 65 DENIAL ROUND 2. Everything above is   .. 
 ..  now ALSO forbidden. Go deeper — wh   .. 
 .. at paradigm hasn't been touched at    .. 
 .. all? What would someone from a comp   .. 
 .. letely unrelated field propose? 3+    .. 
 .. approaches. It is $(date +%Y-%m-%d)   .. 
 .. .                                     .. 
 66 </system>                             .. 
 67                                       71 
 68 ## Also Forbidden Now                 .. 
 69 [Paradigms from Round 1]              .. 
 70                                       .. 
 71 3+ approaches sharing no paradigm w   .. 
 .. ith anything above."                  .. 
 72 ```                                   .. 
 73                                       .. 
 74 ## Domain Forcing (Step 3b)           72 ## Domain Forcing (Step 3b)
 75                                       73 
 76 If `--domains` specified, use those   74 If `--domains` specified, use those
 .. . Otherwise pick 3 domains **unrela   .. . Otherwise pick 3 domains **unrela
 .. ted** to the problem (`--quick`: 2,   .. ted** to the problem (`--quick`: 2,
 ..  `--deep`: 4).                        ..  `--deep`: 4).
 77                                       75 
 78 ```bash                               76 ```md
 79 llmx chat -m gpt-5.4 \                .. 
 80   --reasoning-effort medium --strea   .. 
 .. m --timeout 600 \                     .. 
 81   -o "$BRAINSTORM_DIR/domain-forcin   .. 
 .. g.md" "                               .. 
 82 <system>                              77 <system>
 83 Map a design challenge to three unr   78 Map a design challenge to three unr
 .. elated domains. For each domain: wh   .. elated domains. For each domain: wh
 .. at's the analogous problem, how doe   .. at's the analogous problem, how doe
 .. s that domain solve it, what transf   .. s that domain solve it, what transf
 .. ers back. It is $(date +%Y-%m-%d).    .. ers back. It is $(date +%Y-%m-%d).
 84 </system>                             79 </system>

brainstorm/references/llmx-dispatch.md --- 4/5 --- Text
 93 Same.                                 88 Same.
 94                                       89 
 95 ## Domain 3: [chosen domain]          90 ## Domain 3: [chosen domain]
 96 Same."                                91 Same.
 97 ```                                   92 ```
 98                                       93 
 99 ## Constraint Inversion (Step 3c)     94 ## Constraint Inversion (Step 3c)
100                                       95 
101 **Skipped in `--quick` mode.** Defa   96 **Skipped in `--quick` mode.** Defa
... ult: 3 inversions. `--deep`: 4 inve   .. ult: 3 inversions. `--deep`: 4 inve
... rsions.                               .. rsions.
102                                       97 
103 ```bash                               98 ```md
104 llmx chat -m gpt-5.4 \                .. 
105   --reasoning-effort medium --strea   .. 
... m --timeout 600 \                     .. 
106   -o "$BRAINSTORM_DIR/constraint-in   .. 
... version.md" "                         .. 
107 <system>                              99 <system>
108 For each inverted assumption, desig  100 For each inverted assumption, desig
... n the best solution under that alte  ... n the best solution under that alte
... red constraint. Then identify what   ... red constraint. Then identify what 
... transfers back to reality. It is $(  ... transfers back to reality. It is $(
... date +%Y-%m-%d).                     ... date +%Y-%m-%d).
109 </system>                            101 </system>
110                                      102 
111 ## Design Space                      103 ## Design Space
112 [Original description]               104 [Original description]
113                                      105 
114 ## Inversion 1: [e.g., 'What if com  106 ## Inversion 1: [e.g., 'What if com
... pute were free but storage cost \$1  ... pute were free but storage cost $1/
... /byte?']                             ... byte?']
115 Best design under this constraint.   107 Best design under this constraint. 
... What transfers back?                 ... What transfers back?
116                                      108 
117 ## Inversion 2: [e.g., 'What if we   109 ## Inversion 2: [e.g., 'What if we 
... had 1000x the data but couldn't ite  ... had 1000x the data but couldn't ite
... rate?']                              ... rate?']
118 Best design. What transfers?         110 Best design. What transfers?
119                                      111 
120 ## Inversion 3: [e.g., 'What if thi  112 ## Inversion 3: [e.g., 'What if thi
... s had to work for 50 years without   ... s had to work for 50 years without 
... updates?']                           ... updates?']
121 Best design. What transfers?"        113 Best design. What transfers?
122 ```                                  114 ```
123                                      115 
124 ## Extraction (Step 4)               116 ## Extraction (Step 4)

brainstorm/references/llmx-dispatch.md --- 5/5 --- Text
139   --context "$BRAINSTORM_DIR/all-ra  131   --context "$BRAINSTORM_DIR/all-ra
... w.md" \                              ... w.md" \
140   --prompt "                         132   --prompt "
141 <system>                             133 <system>
142 Extract every discrete idea, approa  134 Extract every discrete idea, approa
... ch, or insight as a numbered list.   ... ch, or insight as a numbered list. 
... One per line. Tag the source (initi  ... One per line. Tag the source (initi
... al/denial-r1/denial-r2/domain/const  ... al/denial-r1/denial-r2/domain/const
... raint). Do not evaluate — extract m  ... raint), axis, domain row if present
... echanically.                         ... , and the matrix cell if available.
...                                      ...  Do not evaluate - extract mechanic
...                                      ... ally.
143 </system>                            135 </system>
144                                      136 
145 Extract all discrete ideas from the  137 Extract all discrete ideas from the
...  brainstorm artifacts." \            ...  brainstorm artifacts." \
146   --output "$BRAINSTORM_DIR/extract  138   --output "$BRAINSTORM_DIR/extract
... ion.md"                              ... ion.md"
147 ```                                  139 ```
148                                      140 
149 If no shared dispatch is available,  141 If no shared dispatch is available,
...  extract yourself.                   ...  extract yourself.
                                         142 
                                         143 ## Matrix Row Contract
                                         144 
                                         145 `matrix.json` rows should include a
...                                      ... t least:
                                         146 
                                         147 - `idea_id`
                                         148 - `short_name`
                                         149 - `source_artifact`
                                         150 - `axis`
                                         151 - `domain_row`
                                         152 - `domain`
                                         153 - `dominant_paradigm_escaped`
                                         154 - `transfer_mechanism`
                                         155 - `disposition`
                                         156 - `merged_into`
                                         157 - `caller_evidence`
                                         158 - `speculative`
                                         159 - `notes`

brainstorm/references/synthesis-templates.md --- 1/4 --- Text
 1   1 <!-- Reference file for brainstorm skill. Loaded on demand. -->
 2   2 # Synthesis & Extraction Templates
 3   3 
 .   4 ## Coverage Matrix (Step 3.5)
 .   5 
 .   6 Use this after perturbation and before extraction/synthesis. `matrix.json` is the coverage
 .   7 contract. `matrix.md` is a rendered operator view over the same rows.
 .   8 
 .   9 ### `matrix.json` row example
 .  10 
 .  11 ```json
 .  12 [
 .  13   {
 .  14     "idea_id": "D1",
 .  15     "short_name": "event-sourced memory",
 .  16     "source_artifact": "denial-r1.md",
 .  17     "axis": "denial",
 .  18     "domain_row": null,
 .  19     "domain": null,
 .  20     "dominant_paradigm_escaped": "append-only log",
 .  21     "transfer_mechanism": "replace ad hoc writes with replayable state deltas",
 .  22     "cell_status": "covered",
 .  23     "disposition": "EXPLORE",
 .  24     "merged_into": null,
 .  25     "caller_evidence": null,
 .  26     "speculative": false,
 .  27     "notes": "Strong denial survivor"
 .  28   }
 .  29 ]
 .  30 ```
 .  31 
 .  32 ### `matrix.md` rendered view
 .  33 
 .  34 ```markdown
 .  35 ## Coverage Matrix
 .  36 | Idea | Source / Round | Dominant Paradigm Escaped | Axis | Domain Row | Cell Status | Disposition | Notes |
 .  37 |------|----------------|---------------------------|------|------------|-------------|-------------|-------|
 .  38 | I1   | Initial        | append-only log           | initial | -        | Covered     | PARK        | Baseline basin |
 .  39 | D1   | Denial R1      | append-only log           | denial  | -        | Covered     | EXPLORE     | Explicitly banned |
 .  40 | F3   | Domain         | queue semantics           | domain  | Natural systems | Partial | PARK | Analogy only |
 .  41 | C2   | Constraint     | offline-first             | constraint | -     | Missed      | REJECT      | No useful transfer |
 .  42 ```
 .  43 
 .  44 Cell statuses: `Covered`, `Partial`, `Missed`, `Duplicate`, `Questionable`.
 .  45 
 .  46 ## Coverage Summary (`coverage.json`)
 .  47 
 .  48 Record the matrix summary structurally before prose:
 .  49 
 .  50 ```json
 .  51 {
 .  52   "requested_axes": ["denial", "domain", "constraint"],
 .  53   "executed_axes": ["denial", "domain"],
 .  54   "idea_count_by_axis": {"initial": 12, "denial": 8, "domain": 6},
 .  55   "distinct_paradigms_escaped": 5,
 .  56   "domain_row_coverage": {
 .  57     "Natural systems": 1,
 .  58     "Human institutions": 1,
 .  59     "Engineering": 0
 .  60   },
 .  61   "duplicate_count": 3,
 .  62   "merge_count": 2,
 .  63   "uncovered_cells": ["constraint:offline-first", "engineering:domain"],
 .  64   "mature_frontier_stop_reason": "forced-domain rounds collapsed into reframings"
 .  65 }
 .  66 ```
 .  67 
 .  68 If the summary cannot explain why synthesis is safe, run another perturbation pass or stop.
 .  69 
 4  70 ## Disposition Table (Step 4)
 5  71 
 6  72 After extracting all ideas, build this table. Every extracted item must have a disposition.
 .  73 The table should render from `matrix.json`, not diverge from it.
 7  74 
 8  75 ```markdown
 9  76 ## Disposition Table

brainstorm/references/synthesis-templates.md --- 2/4 --- Text
17  84 ```
18  85 
19  86 Dispositions: `EXPLORE` (pursue), `PARK` (not now), `REJECT` (bad fit), `MERGE WITH [ID]` (dedup).
..  87 After pain-point gating, add `caller_evidence` and `speculative` to the underlying row.
20  88 
21  89 For EXPLORE items, note which technique generated it (initial/denial/domain/constraint/knowledge-injection) to track which methods produce the most useful ideas across sessions.
22  90 

brainstorm/references/synthesis-templates.md --- 3/4 --- Text
29 **Date:** YYYY-MM-DD                  97 **Date:** YYYY-MM-DD
30 **Perturbation:** Denial xN, Domain   98 **Perturbation:** Denial xN, Domain
..  forcing xN, Constraint inversion x   ..  forcing xN, Constraint inversion x
.. N                                     .. N
31 **Human seeds:** [yes/no]             99 **Human seeds:** [yes/no]
32 **Extraction:** N items total → E e  100 **Extraction:** N items total → E e
.. xplore, P parked, R rejected         ... xplore, P parked, R rejected, M mer
..                                      ... ged
..                                      101 **Coverage:** axes [list], paradigm
..                                      ... s escaped N, uncovered cells [count
..                                      ... ]
33                                      102 
34 ### Ideas to Explore (ranked by nov  103 ### Ideas to Explore (ranked by nov
.. elty x feasibility)                  ... elty x feasibility)
35 | Rank | ID(s) | Idea | Why Non-Obv  104 | Rank | ID(s) | Idea | Why Non-Obv
.. ious | Maintenance | Composability   ... ious | Maintenance | Composability 
.. |                                    ... |

brainstorm/references/synthesis-templates.md --- 4/4 --- Text
82 ### Output Setup                     151 ### Output Setup
83                                      152 
84 ```bash                              153 ```bash
85 LLMX_AVAILABLE=$(which llmx 2>/dev/  154 EXTERNAL_DISPATCH_AVAILABLE=$(test 
.. null && echo "yes" || echo "no")     ... -f ~/Projects/skills/scripts/llm-di
..                                      ... spatch.py && echo "yes" || echo "no
..                                      ... ")
86 TOPIC_SLUG=$(echo "$TOPIC" | tr '[:  155 TOPIC_SLUG=$(echo "$TOPIC" | tr '[:
.. upper:]' '[:lower:]' | tr -cs '[:al  ... upper:]' '[:lower:]' | tr -cs '[:al
.. num:]' '-' | sed 's/^-//;s/-$//' |   ... num:]' '-' | sed 's/^-//;s/-$//' | 
.. cut -c1-40)                          ... cut -c1-40)
87 BRAINSTORM_ID=$(openssl rand -hex 3  156 BRAINSTORM_ID=$(openssl rand -hex 3
.. )                                    ... )
88 BRAINSTORM_DIR=".brainstorm/$(date   157 BRAINSTORM_DIR=".brainstorm/$(date 
.. +%Y-%m-%d)-${TOPIC_SLUG}-${BRAINSTO  ... +%Y-%m-%d)-${TOPIC_SLUG}-${BRAINSTO
.. RM_ID}"                              ... RM_ID}"

modal/SKILL.md --- 1/3 --- Text
  6                                        6 
  7 # Modal (v1.4.x, March 2026)           7 # Modal (v1.4.x, March 2026)
  8                                        8 
  9 ## Critical Breaking Changes (v1.0+    9 Use this skill for Modal as an oper
  . )                                      . ational system, not just an SDK ref
```

## Current File Excerpts

### shared/skill_manifest.py

```text
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.llm_dispatch import PROFILES

KNOWN_KINDS = {"worker", "orchestrator", "operator", "reference"}
KNOWN_INTENT_CLASSES = {
    "divergent",
    "convergent",
    "observational",
    "operator",
    "reference",
    "verification",
}
KNOWN_ENTRYPOINT_TYPES = {"script", "skill_doc", "manual"}
KNOWN_PACKET_BUILDERS = {
    "shared_context_packet",
    "plan_close_packet",
    "observe_transcript_packet",
    "brainstorm_context_packet",
    "overview_packet",
    "status_reconciliation_packet",
}
ARTIFACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "review-coverage.v1": {
        "required_fields": [
            "schema",
            "topic",
            "mode",
            "axes",
            "claims",
            "verification",
            "packet",
        ]
    },
    "observe.signal.v1": {
        "required_fields": ["schema", "kind", "signal_id", "project", "source", "status"]
    },
    "observe.candidate.v1": {
        "required_fields": [
            "schema",
            "kind",
            "candidate_id",
            "project",
            "source_signal_ids",
            "state",
            "promoted",
            "checkable",
            "summary",
        ]
    },
    "brainstorm.matrix.v1": {
        "required_fields": [
            "idea_id",
            "source_artifact",
            "axis",
            "dominant_paradigm_escaped",
            "disposition",
        ]
    },
    "brainstorm.coverage.v1": {
        "required_fields": [
            "requested_axes",
            "executed_axes",
            "idea_count_by_axis",
            "uncovered_cells",
        ]
    },
    "status-reconciliation.v1": {
        "required_fields": [
            "stage",
            "mismatch_class",
            "live_state",
            "control_plane_state",
            "local_state",
        ]
    },
}


@dataclass(frozen=True)
class ManifestIssue:
    manifest_path: Path
    message: str


def iter_manifest_paths(root: Path) -> list[Path]:
    return sorted(root.glob("*/skill.json"))


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text())


def _expect_dict(value: Any, label: str, issues: list[ManifestIssue], manifest_path: Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    issues.append(ManifestIssue(manifest_path, f"{label} must be an object"))
    return {}


def _expect_list(value: Any, label: str, issues: list[ManifestIssue], manifest_path: Path) -> list[Any]:
    if isinstance(value, list):
        return value
    issues.append(ManifestIssue(manifest_path, f"{label} must be an array"))
    return []


def validate_manifest(manifest_path: Path, repo_root: Path) -> list[ManifestIssue]:
    issues: list[ManifestIssue] = []
    try:
        manifest = load_manifest(manifest_path)
    except json.JSONDecodeError as exc:
        return [ManifestIssue(manifest_path, f"invalid JSON: {exc}")]

    if not isinstance(manifest, dict):
        return [ManifestIssue(manifest_path, "manifest root must be an object")]

    skill_dir = manifest_path.parent.name
    name = manifest.get("name")
    if not isinstance(name, str) or not name:
        issues.append(ManifestIssue(manifest_path, "name must be a non-empty string"))
    elif name != skill_dir:
        issues.append(ManifestIssue(manifest_path, f"name must match skill dir '{skill_dir}'"))

    kind = manifest.get("kind")
    if kind not in KNOWN_KINDS:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"kind must be one of {sorted(KNOWN_KINDS)}",
            )
        )

    intent_class = manifest.get("intent_class")
    if intent_class not in KNOWN_INTENT_CLASSES:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"intent_class must be one o

... [truncated for review packet] ...

e(entrypoint_path, str) or not entrypoint_path:
        issues.append(ManifestIssue(manifest_path, "entrypoint.path must be a non-empty string"))
    else:
        resolved = repo_root / entrypoint_path
        if not resolved.exists():
            issues.append(
                ManifestIssue(manifest_path, f"entrypoint.path does not exist: {entrypoint_path}")
            )

    modes = _expect_dict(manifest.get("modes"), "modes", issues, manifest_path)
    if not modes:
        issues.append(ManifestIssue(manifest_path, "modes must declare at least one mode"))
    for mode_name, raw_mode in sorted(modes.items()):
        mode = _expect_dict(raw_mode, f"modes.{mode_name}", issues, manifest_path)
        mode_intent = mode.get("intent_class")
        if mode_intent not in KNOWN_INTENT_CLASSES:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"modes.{mode_name}.intent_class must be one of {sorted(KNOWN_INTENT_CLASSES)}",
                )
            )
        artifacts = _expect_list(mode.get("artifacts"), f"modes.{mode_name}.artifacts", issues, manifest_path)
        if not artifacts:
            issues.append(ManifestIssue(manifest_path, f"modes.{mode_name} must declare artifacts"))
        elif not all(isinstance(item, str) and item for item in artifacts):
            issues.append(
                ManifestIssue(manifest_path, f"modes.{mode_name}.artifacts must contain strings")
            )

    uses = _expect_dict(manifest.get("uses"), "uses", issues, manifest_path)
    dispatch_profiles = _expect_list(uses.get("dispatch_profiles", []), "uses.dispatch_profiles", issues, manifest_path)
    for profile_name in dispatch_profiles:
        if profile_name not in PROFILES:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown dispatch profile '{profile_name}'",
                )
            )

    packet_builders = _expect_list(uses.get("packet_builders", []), "uses.packet_builders", issues, manifest_path)
    for builder_name in packet_builders:
        if builder_name not in KNOWN_PACKET_BUILDERS:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown packet builder '{builder_name}'",
                )
            )

    artifact_schemas = _expect_list(uses.get("artifact_schemas", []), "uses.artifact_schemas", issues, manifest_path)
    for schema_name in artifact_schemas:
        if schema_name not in ARTIFACT_SCHEMAS:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown artifact schema '{schema_name}'",
                )
            )

    follow_on = _expect_list(manifest.get("follow_on", []), "follow_on", issues, manifest_path)
    if follow_on and not all(isinstance(item, str) and item for item in follow_on):
        issues.append(ManifestIssue(manifest_path, "follow_on must contain non-empty strings"))

    references = _expect_list(manifest.get("references", []), "references", issues, manifest_path)
    for reference_path in references:
        if not isinstance(reference_path, str) or not reference_path:
            issues.append(ManifestIssue(manifest_path, "references must contain non-empty strings"))
            continue
        resolved = repo_root / reference_path
        if not resolved.exists():
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"reference does not exist: {reference_path}",
                )
            )

    return issues


def validate_repo_manifests(repo_root: Path, manifest_paths: list[Path] | None = None) -> list[ManifestIssue]:
    paths = manifest_paths or iter_manifest_paths(repo_root)
    issues: list[ManifestIssue] = []
    for manifest_path in paths:
        issues.extend(validate_manifest(manifest_path, repo_root))
    return issues
```

### scripts/lint_skill_manifests.py

```text
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.skill_manifest import iter_manifest_paths, validate_repo_manifests


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill manifests")
    parser.add_argument(
        "--manifest",
        action="append",
        type=Path,
        help="Validate only the given manifest path(s)",
    )
    args = parser.parse_args()

    manifest_paths = args.manifest
    if manifest_paths is None:
        manifest_paths = iter_manifest_paths(ROOT)
    issues = validate_repo_manifests(ROOT, manifest_paths)
    if issues:
        for issue in issues:
            rel_path = issue.manifest_path.relative_to(ROOT)
            print(f"{rel_path}: {issue.message}", file=sys.stderr)
        return 1

    for manifest_path in manifest_paths:
        rel_path = manifest_path.relative_to(ROOT)
        print(f"OK {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### scripts/test_skill_manifest.py

```text
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from shared.skill_manifest import validate_manifest


class SkillManifestTest(unittest.TestCase):
    def test_validate_manifest_accepts_known_profile_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "foo").mkdir()
            (root / "foo" / "SKILL.md").write_text("# Foo\n")
            (root / "foo" / "run.py").write_text("print('ok')\n")
            (root / "foo" / "skill.json").write_text(
                """
                {
                  "name": "foo",
                  "kind": "worker",
                  "intent_class": "convergent",
                  "summary": "x",
                  "entrypoint": {"type": "script", "path": "foo/run.py"},
                  "modes": {
                    "main": {
                      "intent_class": "convergent",
                      "requires_packet": true,
                      "requires_gpt": true,
                      "artifacts": ["out.md"]
                    }
                  },
                    "uses": {
                        "dispatch_profiles": ["formal_review"],
                        "packet_builders": ["shared_context_packet"],
                        "artifact_schemas": ["review-coverage.v1"]
                    },
                  "follow_on": ["upgrade"],
                  "references": ["foo/SKILL.md"]
                }
                """.strip()
            )
            issues = validate_manifest(root / "foo" / "skill.json", root)
            self.assertEqual(issues, [])

    def test_validate_manifest_rejects_unknown_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "foo").mkdir()
            (root / "foo" / "SKILL.md").write_text("# Foo\n")
            (root / "foo" / "run.py").write_text("print('ok')\n")
            manifest_path = root / "foo" / "skill.json"
            manifest_path.write_text(
                """
                {
                  "name": "foo",
                  "kind": "worker",
                  "intent_class": "convergent",
                  "summary": "x",
                  "entrypoint": {"type": "script", "path": "foo/run.py"},
                  "modes": {"main": {"intent_class": "convergent", "artifacts": ["out.md"]}},
                  "uses": {"dispatch_profiles": ["not_real"], "packet_builders": [], "artifact_schemas": []},
                  "follow_on": [],
                  "references": ["foo/SKILL.md"]
                }
                """.strip()
            )
            issues = validate_manifest(manifest_path, root)
            self.assertTrue(any("unknown dispatch profile" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
```

### review/scripts/model-review.py

```text
#!/usr/bin/env python3
"""Model-review dispatch — context assembly + parallel llmx dispatch + output collection.

Replaces the 10-tool-call manual ceremony in the model-review skill with one script call.
Agent provides context + topic + question; script handles plumbing; agent reads outputs.

Usage:
    # Standard review (2 queries: arch + formal)
    model-review.py --context plan.md --topic "hook architecture" "Review for gaps"

    # Deep review (4 queries: arch + formal + domain + mechanical)
    model-review.py --context plan.md --topic "classification logic" --axes arch,formal,domain,mechanical "Review this"

    # With project dir for constitution discovery
    model-review.py --context plan.md --topic "data wiring" --project ~/Projects/intel "Review this plan"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import shared.llm_dispatch as dispatch_core
from shared.context_budget import enforce_budget
from shared.context_packet import BudgetPolicy, ContextPacket, FileBlock, PacketSection, TextBlock
from shared.context_preamble import build_review_preamble_blocks, find_constitution as shared_find_constitution
from shared.context_renderers import write_packet_artifact
from shared.file_specs import parse_file_spec, read_file_excerpt

# --- Structured output schema (both models return this) ---

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["bug", "logic", "architecture", "missing", "performance", "security", "style", "constitutional"],
                    },
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "title": {"type": "string", "description": "One-line summary"},
                    "description": {"type": "string", "description": "Detailed explanation with evidence"},
                    "file": {"type": "string", "description": "File path if cited, empty if architectural"},
                    "line": {"type": "integer", "description": "Line number if cited, 0 if N/A"},
                    "fix": {"type": "string", "description": "Proposed fix, empty if unclear"},
                    "confidence": {"type": "number", "description": "0.0-1.0 confidence in this finding"},
                },
                "required": ["category", "severity", "title", "description", "file", "line", "fix", "confidence"],
            },
        },
    },
    "required": ["findings"],
}

# --- Axis definitions: model + prompt + api kwargs ---

AXES = {
    "arch": {
        "label": "Gemini (architecture/patterns)",
        "profile": "deep_review",
        "prompt": """\
<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code, configs, and findings. It is {date}.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

{question}

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
{con

... [truncated for review packet] ...

age.json.",
    )
    parser.add_argument(
        "--no-extract", action="store_true",
        help="Disable extraction for internal or debugging-only runs.",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After extraction, verify cited files/symbols exist. Implies --extract.",
    )
    parser.add_argument(
        "--questions", type=Path,
        help="JSON file mapping axis names to custom questions (overrides positional question per-axis)",
    )
    parser.add_argument(
        "question", nargs="?",
        default="Review this for logical gaps, missed edge cases, and constitutional alignment.",
        help="Review question for all models",
    )

    args = parser.parse_args()

    project_dir = args.project or Path.cwd()
    if not project_dir.is_dir():
        print(f"error: project dir {project_dir} not found", file=sys.stderr)
        return 1

    if args.context and not args.context.exists():
        print(f"error: context file {args.context} not found", file=sys.stderr)
        return 1

    # Resolve axes
    try:
        axis_names = resolve_axes(args.axes, allow_non_gpt=bool(args.allow_non_gpt))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.no_extract and args.verify:
        print("error: --verify cannot be combined with --no-extract", file=sys.stderr)
        return 1

    print(f"Dispatching {len(axis_names)} queries: {', '.join(axis_names)}", file=sys.stderr)

    # Create output directory
    slug = slugify(args.topic)
    hex_id = os.urandom(3).hex()
    review_dir = Path(f".model-review/{date.today().isoformat()}-{slug}-{hex_id}")
    review_dir.mkdir(parents=True, exist_ok=True)

    # Assemble context
    ctx_files = build_context(
        review_dir, project_dir, args.context, axis_names,
        context_file_specs=args.context_files,
    )

    constitution, _ = find_constitution(project_dir)

    # Load per-axis question overrides
    question_overrides = None
    if args.questions:
        if not args.questions.exists():
            print(f"error: questions file {args.questions} not found", file=sys.stderr)
            return 1
        question_overrides = json.loads(args.questions.read_text())

    # Dispatch and wait
    result = dispatch(review_dir, ctx_files, axis_names, args.question, bool(constitution), question_overrides)
    failures = collect_dispatch_failures(result, ctx_files)
    if failures:
        failure_path = review_dir / "dispatch-failures.json"
        failure_path.write_text(json.dumps({"failures": failures}, indent=2) + "\n")
        result["dispatch_failures"] = str(failure_path)
        result["failed_axes"] = [failure["axis"] for failure in failures]
        print(
            f"error: model-review dispatch produced unusable outputs for "
            f"{', '.join(result['failed_axes'])}; see {failure_path}",
            file=sys.stderr,
        )
        print(json.dumps(result, indent=2))
        return 2

    do_extract = not args.no_extract or args.verify

    # Optional extraction phase
    if do_extract:
        disposition_path = extract_claims(review_dir, result)
        coverage_path = review_dir / "coverage.json"
        if coverage_path.exists():
            result["coverage"] = str(coverage_path)
            print(f"Coverage written to {coverage_path}", file=sys.stderr)
        if disposition_path:
            result["disposition"] = disposition_path
            print(f"Disposition written to {disposition_path}", file=sys.stderr)

            # Optional verification phase
            if args.verify:
                verified_path = verify_claims(review_dir, disposition_path, project_dir)
                result["verified_disposition"] = verified_path
                print(f"Verified disposition written to {verified_path}", file=sys.stderr)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### review/scripts/test_model_review.py

```text
from __future__ import annotations

import importlib.util
import contextlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_REVIEW_PATH = SCRIPT_DIR / "model-review.py"
SPEC = importlib.util.spec_from_file_location("model_review_script", MODEL_REVIEW_PATH)
assert SPEC is not None and SPEC.loader is not None
model_review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model_review)


@contextlib.contextmanager
def patched_llmx_chat(mock_chat):
    with patch.object(model_review.dispatch_core, "_LLMX_CHAT", mock_chat), patch.object(
        model_review.dispatch_core, "_LLMX_VERSION", "test"
    ):
        yield


class ModelReviewDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.review_dir = Path(self.temp_dir.name)
        self.ctx_files = {}
        for axis in ("arch", "formal", "domain"):
            ctx = self.review_dir / f"{axis}-context.md"
            ctx.write_text("context")
            self.ctx_files[axis] = ctx

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dispatch_calls_both_models_and_writes_output(self) -> None:
        call_log: list[dict] = []

        def mock_chat(**kwargs):
            call_log.append(kwargs)
            resp = MagicMock()
            resp.content = f"output for {kwargs.get('model', '?')}"
            resp.latency = 1.0
            return resp

        with patched_llmx_chat(mock_chat):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal"],
                "Review this",
                has_constitution=False,
            )

        self.assertEqual(result["arch"]["exit_code"], 0)
        self.assertGreater(result["arch"]["size"], 0)
        self.assertEqual(result["formal"]["exit_code"], 0)
        self.assertGreater(result["formal"]["size"], 0)
        # Both models called
        models_called = {c["model"] for c in call_log}
        self.assertIn("gemini-3.1-pro-preview", models_called)
        self.assertIn("gpt-5.4", models_called)

    def test_dispatch_falls_back_after_gemini_rate_limit(self) -> None:
        call_count = {"arch": 0}

        def mock_chat(**kwargs):
            model = kwargs.get("model", "")
            if model == model_review.GEMINI_PRO_MODEL and call_count["arch"] == 0:
                call_count["arch"] += 1
                raise Exception("503 resource_exhausted")
            if model == model_review.GEMINI_FLASH_MODEL:
                resp = MagicMock()
                resp.content = "flash fallback"
                resp.latency = 0.5
                return resp
            resp = MagicMock()
            resp.content = "ok"
            resp.latency = 1.0
            return resp

        with patched_llmx_chat(mock_chat):
            result = model_review.dispatch(
                self.review_dir,
                self.ctx_files,
                ["arch", "formal"],
                "Review this",
                has_constitution=False,
            )

        # arch should have fallen back to Flash
        self.assertEqual(result["arch"]["model"], model_review.GEMINI_FLASH_MODEL)
        self.assertEqual(result["arch"]["fallback_reason"], "gemini_rate_limit")
        self.assertGreater(result["arch"]["size"], 0)
        # formal should succeed normally
        self.assertEqual(result["formal"]["exit_code"], 0)

    def test_collect_dispatch_failures_flags_zero_byte_outputs(self) -> None:
        dispatch_result = {
            "review_dir": str(self.review_dir),
            "axes": ["formal"],
            "queries": 1,
            "elapsed_seconds": 1.0,
            "formal": {
                "label": "Formal",
                "model": "gpt-5.4",
                "requested_model": "gpt-5.4",
           

... [truncated for review packet] ...

             "--topic", "empty-axis", "--project", str(project_dir),
                     ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 2)

    def test_main_rejects_verify_with_no_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")
            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "invalid",
                    "--project", str(project_dir),
                    "--verify",
                    "--no-extract",
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)

    def test_main_rejects_non_gpt_axes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            context_path = project_dir / "context.md"
            context_path.write_text("context")

            old_cwd = Path.cwd()
            os.chdir(project_dir)
            try:
                with patch.object(model_review.sys, "argv", [
                    "model-review.py",
                    "--context", str(context_path),
                    "--topic", "non-gpt",
                    "--project", str(project_dir),
                    "--axes", "arch,domain,mechanical",
                ]):
                    rc = model_review.main()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(rc, 1)


class ModelReviewContextBuildTest(unittest.TestCase):
    def test_build_context_drops_file_specs_when_budget_is_tiny(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            context_file = project_dir / "context.txt"
            context_file.write_text("A" * 4000)

            ctx_files = model_review.build_context(
                review_dir,
                project_dir,
                context_file=None,
                axis_names=["formal"],
                context_file_specs=[str(context_file)],
                budget_limit_override=120,
            )

            shared_ctx = ctx_files["formal"]
            manifest = json.loads(shared_ctx.manifest_path.read_text())
            dropped = manifest["packet_metadata"]["budget_enforcement"]["dropped_blocks"]
            self.assertTrue(dropped)
            self.assertEqual(dropped[0]["block_title"], str(context_file))

    def test_build_context_keeps_explicit_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            review_dir = root / "review"
            review_dir.mkdir()
            project_dir = root / "project"
            project_dir.mkdir()
            context_file = project_dir / "assembled.md"
            context_file.write_text("B" * 4000)

            ctx_files = model_review.build_context(
                review_dir,
                project_dir,
                context_file=context_file,
                axis_names=["formal"],
                budget_limit_override=120,
            )

            shared_ctx = ctx_files["formal"]
            manifest = json.loads(shared_ctx.manifest_path.read_text())
            dropped = manifest["packet_metadata"]["budget_enforcement"]["dropped_blocks"]
            self.assertEqual(dropped, [])
            self.assertIn(str(context_file), shared_ctx.content_path.read_text())


if __name__ == "__main__":
    unittest.main()
```

### review/SKILL.md

```text
---
name: review
description: "Use when: 'what's wrong with this', 'review the plan', 'close out the implementation', 'fact-check these findings'. Modes: /review model (Gemini+GPT adversarial), /review verify (fact-check LLM output), /review close (post-implementation tests+review)."
user-invocable: true
argument-hint: <mode> [target]
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
effort: high
---

# Cross-Model Review Workflow

Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

## Default Migration Stance

Unless the user explicitly says compatibility matters, treat the target change as a breaking refactor with full migration.

- Challenge wrappers, adapters, dual-read/dual-write paths, fallback reads, and "temporary" bridges as liabilities, not prudent defaults.
- Prefer direct caller migration and old-path deletion over coexistence plans.
- If compatibility is genuinely required, name the live boundary, why it must remain, and the removal condition. Unnamed future-proofing is design noise.

## Modes

| Mode | Trigger | What it does |
|------|---------|-------------|
| `model` | Default, or explicit `/review model [topic]` | Adversarial cross-model review via Gemini + GPT |
| `verify` | `/review verify <report>` | Fact-check LLM findings against actual code |
| `close` | `/review close` | Post-implementation: tests, review, caught-red-handed loop |

**Auto-routing (when no mode specified):**
- Recent plan in `.claude/plans/` with commits since plan start → `close`
- Recent findings/audit output in context → `verify`
- Otherwise → `model`

---

## Mode: model — Cross-Model Adversarial Review

**Purpose:** Convergent/critical only — find what's wrong. For divergent ideation, use `/brainstorm`.

See `lenses/adversarial-review.md` for full dispatch methodology, axis descriptions, depth presets, per-model prompts, and known issues.

### 1. Assemble Context

Write review material to a single context file.

**Pre-flight — scope declaration (mandatory):** Include a `## Scope` block near the top:
- **Target users:** personal / team / multi-tenant / public
- **Scale:** current entity counts AND designed-for scale (e.g., "currently 40 compounds, designed for thousands of subjects")
- **Rate of change:** how often does new data arrive?

This prevents the #1 review failure mode: models optimizing for the wrong scale. Evidence: selve UMLS review (2026-04-06) — GPT scored a plan 27/100 as "over-engineered for 105 personal entities" when the actual scope was multi-user scalable.

**Constitutional anchoring:** Check for constitution (`## Constitution` in CLAUDE.md) and GOALS.md. Include as preamble if found.

See `references/context-assembly.md` for detailed context gathering (narrow, broad, auto-assembled).

#### Context Anti-Patterns

Common review biases — check your context for these before analysis:

| Anti-pattern | How it biases | Fix |
|-------------|--------------|-----|
| **Scale ambiguity** — large number without clarifying which ops touch it | Models optimize for the large number even when the change affects a small boundary | Include concrete volumes at the decision boundary |
| **Priming alternatives** — listing tools/packages in the prompt | Models evaluate named alternatives favorably instead of finding flaws | For convergent: "find what's wrong" only. For alternatives: use `/brainstorm` or the `alternatives` axis |
| **Framing incumbents as limited** — describing existing tools by narrow current use | Models treat incumbent as constrained | Frame by capability: "Pydantic v2 is established (13 models, 100% typed). Question: extend to output schemas?" |
| **Missing boundary volumes** — not stating how many objects schemas will process | Models default to optimizing for largest number in context | Always inc

... [truncated for review packet] ...

e

After a plan's implementation is committed, there's a gap between "code works" and "code is correct." Regression tests verify existing behavior doesn't change — but they're blind to bugs in new code paths. This mode closes that gap.

See `lenses/plan-close-review.md` for full workflow, bug class table, and migration checklist.

### Why This Exists

Three independent lines of evidence:

1. **Empirical (suspense accounts, 2026-04-07):** GPT-5.4 found 6 confirmed bugs in freshly committed code. All 74 canary tests and 11 IR invariants passed. The bugs were in new functions with zero test coverage.

2. **Failure Mode 15 — Silent Semantic Failures** (MAS-FIRE, arXiv:2602.19843): Reasoning drift, wrong buckets, misleading diagnostics propagate without runtime exceptions.

3. **Failure Mode 16 — Reward Hacking** (TRACE, arXiv:2601.20103): Agents evaluated by test passage may hack the test rather than solve the task.

### Workflow

**Phase 0: Pre-Close Discipline** — Normalize closeout: separate code/data validation, sync generated docs, prove migration completion. Build review packet:
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

**Phase 1: Write Tests for New Code** — Identify new functions from plan commits. Write unit tests covering happy path, edge cases, error paths, and contract invariants.

**Phase 2: Cross-Model Review** — Run `/review model` on the plan-close review packet (not a hand-written summary). Use `--context .model-review/plan-close-context.md --extract --verify`. Fact-check and disposition every finding. Inspect `coverage.json` before closing so you can see packet drops, axis coverage, and verification totals.

**Phase 3: The Caught-Red-Handed Loop** — For each confirmed finding: would any Phase 1 tests have caught this? If yes, fix the test gap. If no, write a new test. Verify against pre-fix code:
```bash
git stash
pytest tests/test_<new>.py -x  # should FAIL
git stash pop
pytest tests/test_<new>.py -x  # should PASS
```

**Phase 4: Close the Plan** — Commit tests, update plan status, run `validate-code`, summarize findings.

### When NOT to Use

- Trivial plans (< 30 lines, single function, obvious correctness)
- Research/analysis plans that don't produce code
- Plans that only modify config/data with no logic changes

---

## References

- `references/context-assembly.md` — detailed context gathering patterns
- `references/dispatch.md` — shared dispatch contract, context formatting, extraction defaults
- `references/extraction.md` — extraction/disposition coverage rules
- `references/prompts.md` — prompt bodies used by the shared review script
- `references/biases-and-antipatterns.md` — known model biases, per-model failure modes, common mistakes

## Known Issues
<!-- Append-only. Session-analyst may suggest additions. -->
- **[2026-03-27] shared dispatch output — never use shell redirects (> file) for review artifacts; the shared review script writes directly to files. Shell redirects buffer until process exit, producing 0-byte files.**
- **[2026-04-09] GPT-5.4 xhigh timeout — shared dispatch timeout is 300s by default; xhigh needs 900s. Set `--timeout 900` for xhigh, `--timeout 600` for high. Three parallel xhigh calls may hit rate limits — run sequentially or use high effort instead.**
- **[2026-04-09] xhigh vs high for architectural review — marginal quality delta. High-effort adversarial review (4 min) found the sharpest insight across 6 reviews. xhigh (15 min each) had more words, similar signal density. Reserve xhigh for formal math only. For deep dives: 2-3 parallel high queries with focused questions > 1 xhigh mega-query.**
- **[2026-04-09] Context formatting matters — GPT-5.4 performs better with XML `<doc>` tags around context sections. Gemini needs query at END, critical constraints at END. Consult /model-guide before assembling context for manual dispatch.**

$ARGUMENTS
```

### review/references/dispatch.md

```text
<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Dispatch Mechanics

## Shared Dispatch Contract

The review script owns transport, context packing, output files, extraction, and
verification. Prefer the script over ad hoc model calls:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "What's wrong with this [thing being reviewed]"
```

Use `--verify` when the review is a plan-close packet or when you want the script
to check file/symbol references after extraction:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context .model-review/plan-close-context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract --verify \
  "Review this plan closeout"
```

Other useful forms:

```bash
# Deep review with per-axis overrides
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context-files docs/plan.md scripts/finding_ir.py:86-110 \
  --topic "$TOPIC" \
  --axes arch,formal,domain,mechanical \
  --questions questions.json \
  --extract \
  "Review this plan"
```

## Contract Boundaries

Transport/model choices live in `shared/llm_dispatch.PROFILES`. Update that shared
contract rather than duplicating provider flags in skill docs.

Relevant profiles:
- `deep_review` for Gemini pattern review
- `formal_review` for GPT-5.4 reasoning
- `fast_extract` for mechanical extraction

The script writes these artifacts:
- `shared-context.md` / `shared-context.manifest.json`
- `<axis>-output.md`
- `findings.json`
- `disposition.md`
- `verified-disposition.md`
- `coverage.json`

`coverage.json` is the stable machine-readable summary. Current top-level fields:
- `schema_version`
- `artifacts`
- `context_packet`
- `dispatch`
- `extraction`
- `verification`

## Context Assembly

`--context-files` accepts file specs of the form `path/file.py`,
`path/file.py:100-150`, or `path/file.py:100`.

For plan-close review packets, prefer:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/build_plan_close_context.py \
  --repo "$(pwd)" \
  --output .model-review/plan-close-context.md
```

## Context Formatting

Before assembling context, check `/model-guide` for per-model prompting rules.
Key points:

- GPT-5.4 context should use XML `<doc id="..." title="...">` tags for document sections
- Gemini does better when the question and constraints come last
- Keep prompts direct; the shared review script handles the rest

## Extraction Defaults

Use `--extract` for normal user-facing reviews. Use `--extract --verify` for
plan-close packets or any review that needs an auditable coverage trail with
checked references. The user-facing presets are `standard`, `deep`, and `full`;
each includes GPT-5.4. Non-GPT axis sets are internal-only.
```

### review/references/extraction.md

```text
<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Extraction Mechanics (Step 5)

Use this only when `--extract` was not passed to the review script and you need to
run extraction manually. In the normal closeout flow, the shared review script
handles extraction for you and emits `disposition.md` plus `coverage.json`.

## Why This Step Exists

Single-pass synthesis is lossy. The agent biases toward recent, vivid, or
structurally convenient ideas and silently drops others. In observed sessions,
users had to ask "did you include everything?" 3+ times — each time recovering
omissions. The EVE framework (Chen & Fleming, arXiv:2602.06103) shows that
separating extraction from synthesis improves recall +24% and precision +29%.

## Cross-Family Extraction

The review script already dispatches extraction to a different model family from
the reviewer and writes the extracted findings to `findings.json`.

If you customize the extraction prompt, keep it mechanical:

- extract every discrete recommendation, finding, or claim as a numbered list
- one item per line
- do not evaluate or filter

The source of truth for the extraction prompt is `review/scripts/model-review.py`.

## Anonymize During Disposition

Use anonymous labels (A1-An, B1-Bn) in the disposition table — not model names.
This prevents identity-driven bias during synthesis (Choi et al. arXiv:2510.07517
found model identity biases peer evaluation). Reveal model identities only in the
"Model Errors" section where you need to know which model to distrust.

```markdown
## Extraction: Reviewer A
A1. [Prediction ledger needed -- no structured tracking exists]
A2. [Signal scanner has silent except blocks -- masks failures]
A3. [DuckDB FTS preserves provenance better than vector DB]
...

## Extraction: Reviewer B
B1. [Universe survivorship bias -- S:5, D:5]
B2. [first_seen_date needed on all records for PIT safety]
B3. [FDR control mandatory -- 5000-50000 implicit hypotheses/month]
...
```

## Disposition Table

Every extracted item gets a verdict. No item left undispositioned.

```markdown
## Disposition Table
| ID  | Claim (short) | Disposition | Reason |
|-----|--------------|-------------|--------|
| G1  | Prediction ledger | INCLUDE -- Tier 1 | Both models, verified gap |
| G2  | Silent except blocks | INCLUDE -- Tier 6 | Verified in signal_scanner.py |
| G3  | DuckDB > vector DB | INCLUDE -- YAGNI | Constitutional alignment |
| P1  | Universe survivorship | INCLUDE -- Tier 4 | Verified, no PIT table exists |
| P2  | first_seen_date | INCLUDE -- Tier 1 | Verified, downloads lack it |
| P3  | FDR control | DEFER | Needs experiment registry first |
| P7  | Kubernetes deployment | REJECT | Scale mismatch (personal project) |
| ... | ... | ... | ... |
```

Valid dispositions: `INCLUDE`, `DEFER (reason)`, `REJECT (reason)`,
`MERGE WITH [ID]` (dedup).

## Coverage Check

Before proceeding to synthesis:

- count total extracted, included, deferred, rejected, merged
- if any ID has no disposition, stop and fix
- save extraction + disposition table to `$REVIEW_DIR/extraction.md`
- inspect `coverage.json` when the review came from the shared script; it records
  how many axes produced usable findings

This file is the checklist. If the user asks "did you include everything?" point
them here, not the prose.

## Multi-Round Extraction

When running multiple dispatch rounds (e.g., Round 1 architecture + Round 2 red
team):

1. Extract per round, not per synthesis.
2. Merge disposition tables across rounds before writing the final synthesis.
3. Never synthesize a synthesis. The final prose is written once from the merged
   disposition table.
4. Total coverage count in the final output should report round-level and merged
   totals.
```

### review/references/prompts.md

```text
<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Prompt Templates

Prompt bodies for manual customization. The shared review script owns transport,
output files, extraction, and verification. If you need to customize dispatch,
edit `review/scripts/model-review.py` or the shared dispatch contract in
`shared/llm_dispatch.py`; do not teach raw CLI invocation here.

## Gemini -- Architectural/Pattern Review

<system>
You are reviewing a codebase. Be concrete. No platitudes. Reference specific code,
configs, and findings. It is $(date +%Y-%m-%d).
All code and features are developed by AI agents, not humans. Dev creation time is
zero. Never recommend trading stability, composability, or robustness for
implementation speed. Filter recommendations by maintenance burden, supervision
cost, and complexity — not creation effort.
Budget: ~2000 words. Dense tables and lists over prose.
</system>

[Describe what's being reviewed]

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Assessment of Strengths and Weaknesses
What holds up and what doesn't. Reference actual code/config. Be specific about errors AND what's correct.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
$([ -n "$CONSTITUTION" ] && echo "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?" || echo "No constitution provided — assess internal consistency only.")

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?

## GPT -- Quantitative/Formal Analysis

<system>
You are performing QUANTITATIVE and FORMAL analysis. Gemini is handling qualitative
pattern review separately. Focus on what Gemini can't do well. Be precise. Show your
reasoning. No hand-waving.
All code and features are developed by AI agents, not humans. Dev creation time is
zero. Never recommend trading stability, composability, or robustness for
implementation speed. Filter recommendations by maintenance burden, supervision
cost, and complexity — not creation effort.
Budget: ~2000 words. Tables over prose. Source-grade claims.
</system>

[Describe what's being reviewed]

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: expected impact, maintenance burden, composability, risk. Rank by value adjusted for ongoing cost. Creation effort is irrelevant (agents build everything). Only ongoing drag matters: maintenance, supervision, complexity budget.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
$([ -n "$CONSTITUTION" ] && echo "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes." || echo "No constitution provided — assess internal logical consistency.")

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.4) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.

## Flash -- Optional Mechanical Audit Pass

Mechanical-only passes should use the `mechanical` axis in `review/scripts/model-review.py`.
Keep them flat and specific:

- Duplicated content across files
- Inconsistent naming (model names, paths, conventions)
- Stale references (wrong versions, deprecated APIs)
- Missing cross-references between related documents
```

### review/references/biases-and-antipatterns.md

```text
<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Known Model Biases & Anti-Patterns

## Systematic Biases

| Bias | Effect | Countermeasure |
|------|--------|----------------|
| **Correlated errors** | ~60% shared wrong answers when both err (Kim ICML 2025, pre-reasoning) | Never same-family reviewer + synthesizer |
| **Self-preference** | 74.9% demographic parity bias (Wataoka NeurIPS 2024) | Different-family synthesis; weight cross-family disagreements |
| **Judge inflation** | Same-provider accuracy inflation (Kim ICML 2025) | Cross-family only (this skill already does this) |
| **Debate = martingale** | Sequential discussion: no correctness improvement (Choi 2025, formal proof) | Independent parallel reviews, never let models respond to each other |

**Per-model:**
- **Gemini Pro:** Production-pattern bias (enterprise for personal projects), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.4:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep
- **Flash/GPT-5.3:** Shallow analysis (extraction only), recency bias. Never use for architectural judgment.

**Dispatch specifics:** the shared review contract owns provider routing,
timeouts, fallback, and artifact emission. This reference should track reviewer
biases and workflow anti-patterns, not raw transport flags.

## Anti-Patterns

- **Synthesizing without extracting.** #1 information loss. Always extract + disposition before prose.
- **Synthesizing a synthesis.** Each compression drops ideas. Merge raw extractions, not prior syntheses.
- **Adopting without code verification.** Both models hallucinated "missing" features that already existed.
- **Model agreement = proof.** Agreement is evidence, not proof — verify against source code.
- **Debate workflow.** Martingale. Independent parallel + voting beats sequential discussion.
- **Same-family reviewers.** Same-model correction: 59.1%. Cross-family: 90.4% (FINCH-ZK).
- **"Top N" triage.** If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section.** Most valuable part of each review.
- **Same prompt to both models.** Gemini = patterns, GPT = quantitative/formal. Different strengths need different prompts.
- **Writing to /tmp.** Persist to `.model-review/YYYY-MM-DD-topic/`.
- **Bare date directories.** Always append topic slug to avoid same-day collisions.
- **Skipping constitutional check.** Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming.** Convergent only. Use `/brainstorm` for divergent.
- **Priming tool names in review prompt.** Turns critique into evaluation. Use `alternatives` axis separately.
- **Scale-ambiguous context.** Both models converge on the same wrong answer from shared misleading context.
```

### review/lenses/adversarial-review.md

```text
<!-- Lens file for review skill: model mode dispatch methodology. Loaded on demand. -->

# Adversarial Review — Dispatch Methodology

## Axis Descriptions

| Axis | Model | What it checks | When to include |
|------|-------|---------------|-----------------|
| `arch` | Gemini 3.1 Pro | Patterns, architecture, cross-reference, constitutional alignment | Always (default) |
| `formal` | GPT-5.4 (high reasoning) | Math, logic, cost-benefit, testable predictions, quantified constitutional coverage | Always (default) |
| `domain` | Gemini 3.1 Pro | Domain fact correctness — citations, API endpoints, schemas, biological claims, numbers | Domain-dense plans; skip for pure code reviews |
| `mechanical` | Gemini Flash | Stale refs, wrong paths, naming inconsistencies, duplicated content | Large codebases; include grep results — Flash hallucinates about fixed state (~13%) |
| `alternatives` | Kimi K2.5 | 3-5 genuinely different approaches with different mechanisms | Architecture decisions; SEPARATE from convergent review (never mix critique + brainstorm) |

## Depth Presets

| Preset | Axes | Blast radius | Cost |
|--------|------|-------------|------|
| `standard` | arch + formal | User-facing default; most features | ~$2-4 |
| `deep` | arch + formal + domain + mechanical | User-facing; structural/domain-dense | ~$4-6 |
| `full` | all 5 | User-facing; shared infra, clinical, high-stakes | ~$6-10 |

Classify by blast radius, not file count. `standard` is the default.
The user-facing presets are `standard`, `deep`, and `full`; each includes GPT-5.4.
Gemini-only passes are internal-only and should not be documented to users as review presets.

## Per-Model Prompts

### Gemini — Architectural/Pattern Review (arch axis)

System: Concrete, no platitudes. Reference specific code/configs. Agent-built codebase (dev time = free). Budget ~2000 words, dense tables/lists.

Required sections:
1. Assessment of Strengths and Weaknesses — reference actual code
2. What Was Missed — cite files, line ranges, gaps
3. Better Approaches — Agree (refine) / Disagree (alternative) / Upgrade
4. What I'd Prioritize Differently — top 5, testable criteria
5. Constitutional Alignment — violations and well-served principles (or internal consistency if no constitution)
6. Blind Spots In My Own Analysis — where to distrust Gemini

### GPT-5.4 — Quantitative/Formal Analysis (formal axis)

System: Quantitative and formal ONLY. Other reviewers handle qualitative. Precise, show reasoning. Agent-built codebase. Budget ~2000 words, tables, source-graded claims.

Required sections:
1. Logical Inconsistencies — contradictions, assumptions, invalid inferences, math verification
2. Cost-Benefit Analysis — impact, maintenance burden, composability, risk. Filter on ongoing drag, NOT creation effort
3. Testable Predictions — falsifiable predictions with success criteria
4. Constitutional Alignment (Quantified) — per-principle coverage 0-100%, gaps, fixes
5. My Top 5 Recommendations — measurable impact, quantitative justification, verification metrics
6. Where I'm Likely Wrong — GPT-5.4 known biases: confident fabrication, overcautious scope-limiting, production-grade creep

### Gemini Pro — Domain Correctness (domain axis)

System: Domain-specific claim verification only. Per-claim verdict: CORRECT / WRONG / UNVERIFIABLE. Flag URLs, API endpoints, version numbers needing probes. Budget ~1500 words.

### Gemini Flash — Mechanical Audit (mechanical axis)

System: Mechanical audit only, no analysis. Find: stale refs, inconsistent naming, missing cross-refs, duplicates, wrong paths. Flat numbered list.

### Kimi K2.5 — Alternative Approaches (alternatives axis)

System: Generate 3-5 genuinely different approaches (different mechanisms, not variations). Per approach: core mechanism, advantages, disadvantages, maintenance burden. Do NOT critique the existing plan.

## Full prompt templates

See `references/prompts.md` for copy-paste manual dispatch templates. The `model-review.py` script handles these automatically.

## Dispatch Mechanics

**Always use the script:**
```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --context context.md \
  --topic "$TOPIC" \
  --project "$(pwd)" \
  --extract \
  "$QUESTION"
```

Set `timeout: 660000` on the Bash tool call (11 min). The script fires all queries in parallel.

### Script Flags

- `--extract` — Auto-extract claims via cross-family models, merge into `disposition.md`, and emit `coverage.json`. Add to all standard/deep/full reviews.
- `--verify` — After extraction, verify cited files/symbols exist. Implies `--extract`.
- `--questions FILE` — JSON mapping axis names to custom questions. Unmapped axes use positional question.
- `--context-files spec1 spec2` — Auto-assemble from `file.py`, `file.py:100-150`, `file.py:100` specs.
- `--axes NAME` — Preset name or comma-separated axes.

### Model Selection Contract

```
Gemini Pro:  architecture / pattern pass
GPT-5.4:     quantitative / formal pass
Flash:       fallback or extraction-only pass
Kimi K2.5:   alternatives-only pass when configured
```

The shared dispatch layer owns providers, transport, retries, and timeout
policy. This lens should describe review responsibilities, not raw model flags.

**NEVER downgrade models on failure.** Diagnose via shared dispatch metadata and
coverage artifacts instead of teaching transport-specific debugging here.

### Gemini Rate Limit Fallback

Script auto-detects Gemini Pro 503/rate-limit (exit 3 or stderr markers). On first failure, retries that axis with Flash. All subsequent Gemini Pro axes in the same dispatch also fall back to Flash (session-level). GPT axes are unaffected.

### Uncalibrated Threshold Flagging

Automatic with `--extract`: the script tags numeric thresholds (e.g., `>=20% AUPRC`) lacking cited sources with `[UNCALIBRATED]`. Common GPT failure mode: fabricating plausible thresholds. Treat as requiring your own derivation.

## Known Issues

- **Gemini Pro:** Production-pattern bias (enterprise for personal), self-recommendation (Google services), instruction dropping in long context
- **GPT-5.4:** Confident fabrication (invents numbers/paths), overcautious scope, production-grade creep
- **Flash/GPT-5.3:** Shallow analysis (extraction only), recency bias. Never use for architectural judgment.
- **Correlated errors:** ~60% shared wrong answers when both err (Kim ICML 2025, pre-reasoning). Never same-family reviewer + synthesizer.
- **Self-preference:** 74.9% demographic parity bias (Wataoka NeurIPS 2024). Different-family synthesis.
- **Debate = martingale:** Sequential discussion has no correctness improvement (Choi 2025). Independent parallel reviews only.
- **Shared dispatch output:** Never rely on shell redirects for review artifacts;
  the shared script writes directly to files.

## Anti-Patterns

- **Synthesizing without extracting** — #1 information loss. Always extract + disposition before prose.
- **Synthesizing a synthesis** — Each compression drops ideas. Merge raw extractions, not prior syntheses.
- **Adopting without code verification** — Both models hallucinated "missing" features that already existed.
- **Model agreement = proof** — Agreement is evidence, not proof. Verify against source code.
- **Same prompt to both models** — Gemini = patterns, GPT = quantitative/formal. Different strengths need different prompts.
- **Writing to /tmp** — Persist to `.model-review/YYYY-MM-DD-topic/`.
- **Skipping constitutional check** — Unanchored reviews drift into generic advice.
- **Mixing review and brainstorming** — Convergent only. Use `/brainstorm` for divergent.
- **Priming tool names** — Turns critique into evaluation. Use `alternatives` axis separately.
- **Scale-ambiguous context** — Both models converge on the same wrong answer from shared misleading context.
- **"Top N" triage** — If INCLUDE, implement. DEFER needs explicit reason per item.
- **Skipping self-doubt section** — Most valuable part of each review.
```

### observe/scripts/observe_artifacts.py

```text
#!/usr/bin/env python3
"""Shared paths and JSONL helpers for observe artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path.home() / "Projects" / "meta"
ARTIFACT_SUBDIR = Path("artifacts") / "observe"

MANIFEST_JSON = "manifest.json"
INPUT_MD = "input.md"
CODEX_MD = "codex.md"
COVERAGE_DIGEST_TXT = "coverage-digest.txt"
OPERATIONAL_CONTEXT_TXT = "operational-context.txt"
GEMINI_OUTPUT_MD = "gemini-output.md"
GEMINI_OUTPUT_META_JSON = "gemini-output.meta.json"
GEMINI_OUTPUT_ERROR_JSON = "gemini-output.error.json"
DISPATCH_META_JSON = "dispatch.meta.json"
SIGNALS_JSONL = "signals.jsonl"
CANDIDATES_JSONL = "candidates.jsonl"
PATTERNS_JSONL = "patterns.jsonl"
LAST_SYNTHESIS_MD = "last-synthesis.md"
DIGEST_MD = "digest.md"

OBSERVE_ARTIFACT_ROOT_ENV = "OBSERVE_ARTIFACT_ROOT"
OBSERVE_PROJECT_ROOT_ENV = "OBSERVE_PROJECT_ROOT"


def project_root() -> Path:
    """Resolve the canonical workspace root for observe outputs."""
    env_root = os.environ.get(OBSERVE_PROJECT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()

    env_artifact_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_artifact_root:
        artifact_dir = Path(env_artifact_root).expanduser()
        if len(artifact_dir.parents) >= 2:
            return artifact_dir.parents[1]
        return artifact_dir.parent

    return DEFAULT_PROJECT_ROOT


def artifact_root() -> Path:
    """Resolve the canonical observe artifact directory."""
    env_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()
    return project_root() / ARTIFACT_SUBDIR


def artifact_path(*parts: str) -> Path:
    """Join a path under the canonical artifact root."""
    return artifact_root().joinpath(*parts)


def improvement_log_path() -> Path:
    """Canonical improvement log used by sessions and supervision modes."""
    return project_root() / "improvement-log.md"


def stable_id(prefix: str, *parts: str, length: int = 12) -> str:
    """Create a stable short identifier from a sequence of string parts."""
    digest_input = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha1(digest_input).hexdigest()[:length]
    return f"{prefix}_{digest}"


def jsonl_line(record: dict[str, Any]) -> str:
    """Serialize one JSONL record with stable key ordering."""
    return json.dumps(record, sort_keys=True, ensure_ascii=True)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSONL record, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(jsonl_line(record))
        handle.write("\n")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write a full JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(jsonl_line(record))
            handle.write("\n")
```

### Omitted Files

```text
(Omitted 16 additional touched files from excerpts.)
```
