# Context Packet Integration Plan

Date: 2026-04-10
Repo: `~/Projects/skills`
Status: implemented
Decision type: breaking refactor, full migration

## Problem

The repo now has a shared model-dispatch spine, but context creation is still fragmented.

Today there are at least three separate packet/context assembly paths:

1. `review/scripts/build_plan_close_context.py`
   - builds a review packet from git status, diff, and file excerpts
   - owns touched-file resolution, truncation, and markdown packet rendering

2. `review/scripts/model-review.py`
   - owns `parse_file_spec()`, `assemble_context_files()`, constitutional preamble injection, goals injection, and per-axis context file construction

3. `hooks/generate-overview.sh` / `hooks/generate-overview-batch.sh`
   - build prompt/context packets from prompt templates plus `repomix` output
   - own their own source selection, prompt wrapping, token estimation, and rendering

These are all solving versions of the same mechanical problem:

- gather heterogeneous inputs
- order them into sections
- label provenance
- truncate to a budget
- write stable artifacts for models to consume

But they currently do so with different ad hoc code paths, different rendering styles, and different truncation logic.

The result:

- packet drift across skills
- repeated file/range parsing logic
- repeated preamble injection logic
- no single manifest/hash surface for context provenance
- no reusable way for new skills to say “build me a good context packet”

The repo now needs one canonical context-packet layer, analogous to what `shared/llm_dispatch.py` became for model calls.

Important integration reality:

- `shared/llm_dispatch.py` is not a passive downstream consumer today
- it still owns a small context-assembly helper and only publishes output-token limits
- this plan therefore has to include a small `llm_dispatch.py` contract cleanup, not just new packet modules

## Scope

- Target users: agents and hooks consuming `~/Projects/skills` across local repos
- Scale:
  - current: review packets, plan-close packets, overview prompts, skill-local context snippets
  - designed-for: many packet-producing skills across many repos, repeated automated review/research/overview runs
- Rate of change: high; new skills and review surfaces are still being added and modified weekly

## Decision

Build a shared **context packet engine** that generalizes packet construction mechanics, not task semantics.

Concretely:

1. Add a shared library for packet primitives, section composition, truncation, hashing, and rendering.
2. Add builder-specific adapters for plan-close, model-review, and overview generation.
3. Migrate current packet-producing code onto the shared engine.
4. Keep selection logic task-specific; do not force one universal packet schema.
5. Preserve a thin compatibility wrapper where callers already use a specific script path, but move the real logic into shared code.

This is a breaking refactor in the implementation layer:

- shared mechanics move into one module
- duplicated local assembly logic is deleted
- old scripts survive only as thin wrappers if they are already a live entrypoint

## Non-Goal

This is **not** a universal “one packet format for every repo and every task.”

The thing that generalizes is:

- file blocks
- diff blocks
- text blocks
- command/output blocks
- ordering
- truncation
- hashing
- rendering

The thing that does **not** generalize is:

- which files matter for a given task
- how a repo selects those files
- what sections are semantically relevant
- what “good context” means for a review vs an overview vs a research packet

The correct abstraction boundary is:

- shared packet mechanics
- task-specific builders/selectors

not:

- one giant schema with dozens of optional branches

Additional non-goal:

- do not force overview generation into the same markdown packet renderer used by review/plan-close if the live prompt-wrapped format (`<instructions>`, `<codebase>`) is materially part of its behavior

## Evidence From Current Code

### 1. Plan-close already has a packet renderer

`review/scripts/build_plan_close_context.py` already implements:

- touched file resolution
- diff and diff-stat collection
- scope block insertion
- excerpt truncation
- markdown packet rendering

This is clearly reusable machinery.

### 2. Model-review already has a second context-assembly path

`review/scripts/model-review.py` separately implements:

- `parse_file_spec()`
- `assemble_context_files()`
- constitution/goals preamble injection
- per-axis context file writing

This overlaps strongly with the plan-close builder but is not sharing code.

### 3. Overview generation has a third packet path

`hooks/generate-overview.sh` and `hooks/generate-overview-batch.sh` both:

- collect source trees via `repomix`
- wrap prompt instructions and source content into structured sections
- estimate token size
- write prompt/context artifacts

That is packet assembly, but done in shell and duplicated across live and batch paths.

### 4. Review docs already assume a single-file context packet is better

`review/references/context-assembly.md` and `review/lenses/plan-close-review.md` already converge on the same discipline:

- one assembled context file
- explicit scope
- constitutional preamble when relevant
- avoid multi-file transport loss

The architecture is already implicit in the docs. The code just hasn’t been unified yet.

### 5. Dispatch still owns context assembly and incomplete budget metadata

`shared/llm_dispatch.py` currently still:

- has `assemble_context(...)`
- computes its own `context_sha256`
- publishes `max_tokens` for output, but not explicit input-budget metadata

That means the packet layer cannot be truly canonical unless dispatch consumes packet artifacts and exposes model-facing input-budget data.

## Target Architecture

### 1. Shared packet core

Add:

- `shared/context_packet.py`

Core responsibilities:

- block types
- packet composition
- deterministic rendering
- manifest metadata
- size budgeting / truncation
- stable hashing

Suggested block types:

- `TextBlock`
- `FileBlock`
- `DiffBlock`
- `CommandBlock`
- `ListBlock`

Suggested packet types:

- `PacketSection`
- `ContextPacket`
- `PacketManifest`

### 2. Shared source helpers

Do not create one ambiguous `context_selectors.py`. Split by concern:

- `shared/file_specs.py`
  - file path parsing (`path`, `path:start`, `path:start-end`)
  - excerpt extraction
  - non-text / binary / symlink policy

- `shared/git_context.py`
  - touched-file resolution from git
  - diff collection
  - status collection
  - commit-range and worktree helpers
  - NUL-delimited parsing only (`--porcelain -z`, `--name-status -z`), not ad hoc line scraping

- `shared/repomix_source.py`
  - `repomix` capture
  - source-file staging for overview builders
  - large-output handling strategy

- `shared/context_preamble.py`
  - constitution/goals discovery
  - agent-economics / development-context text
  - deterministic preamble assembly

Important: these are bounded helpers, not a monolithic builder.

### 3. Shared renderers

Add:

- `shared/context_renderers.py`

Responsibilities:

- markdown rendering
- tagged prompt rendering for overview-style packets
- optional JSON manifest emission
- section headers and block labels
- file-boundary labeling
- truncation markers

Do not add arbitrary output formats. v1 needs exactly:

- markdown packet rendering for review/plan-close
- tagged prompt rendering for overview-style contexts
- manifest JSON

### 4. Thin builder wrappers

Add or refactor into:

- `review/scripts/build_plan_close_context.py`
  - becomes a thin plan-close builder using the shared packet engine

- `review/scripts/model-review.py`
  - reuses shared packet helpers for `--context-files`, constitutional preamble, and axis packet creation

- `hooks/generate-overview.sh`
  - keeps shell orchestration if needed, but packet construction moves to a Python helper

- `hooks/generate-overview-batch.sh`
  - eventually reuses the same overview packet builder as live generation

### 5. Optional shell-facing helper

If shell consumers proliferate, add:

- `scripts/context-packet.py`

But do not start there. The core should be importable first.

### 6. Shared budget and normalization policy

The packet engine needs an explicit normalization and budget contract.

Minimum contract:

- newline normalization policy
- path normalization policy
- section ordering rules
- truncation marker rendering rules
- budget metric (`chars`, `tokens`)
- estimate method (`exact`, `heuristic:<name>`)
- profile-aware token budget lookup for model-facing builders
- normalization version recorded in manifests

Do not call hashes or budgets “shared” without this.

## Canonical Contract

### `ContextPacket`

Suggested minimal shape:

```python
ContextPacket(
    title: str,
    scope: str | None,
    sections: list[PacketSection],
    metadata: dict[str, Any],
    budget_policy: BudgetPolicy | None,
)
```

### `PacketSection`

```python
PacketSection(
    title: str,
    blocks: list[PacketBlock],
)
```

### `PacketBlock`

One of:

- `TextBlock(title, text)`
- `PreambleBlock(title, text)`
- `FileBlock(path, text, range_spec=None)`
- `DiffBlock(label, diff_text)`
- `CommandBlock(command, output_text)`
- `ListBlock(title, items)`

`PreambleBlock` exists so constitutional / goals context can be treated as first-class packet material and protected from ordinary truncation rules.

### Manifest fields

Every rendered packet should be able to emit a manifest with:

- packet title
- builder name/version
- created timestamp
- source block list
- source paths
- block hashes
- rendered content hash
- payload hash
- total rendered bytes
- token estimate
- estimate method
- budget metric
- budget limit used
- normalization version
- truncation events

This becomes the provenance surface for context creation.

Important distinction:

- `content_hash` covers normalized rendered content only
- manifest metadata may include timestamps and builder runtime metadata

Do not mix those two or deterministic hashing will be fake.

### `BuildArtifact`

Builders should return an explicit artifact, not just raw text:

```python
BuildArtifact(
    content_path: Path,
    manifest_path: Path,
    content_hash: str,
    payload_hash: str,
    rendered_bytes: int,
    token_estimate: int | None,
    estimate_method: str,
    budget_metric: str,
    truncated: bool,
)
```

`content_path` must point at the exact model-consumable payload, not a helper intermediate.
That keeps overview generation inside the same artifact contract instead of relying on hidden prompt glue.

This becomes the handoff boundary into `shared/llm_dispatch.py` or other consumers.

Dispatch integration requirements:

- `shared/llm_dispatch.py` should consume packet `payload_hash` / manifest metadata rather than recomputing a parallel context hash
- dispatch profiles need explicit model-facing input budget metadata
- the old `assemble_context(...)` helper in dispatch should be deleted once callers migrate to packet artifacts

## What “Generalized” Means

This plan deliberately separates three layers:

### Layer A: packet mechanics

Shared:

- render markdown
- compute hashes
- truncate
- label sections
- label source provenance

### Layer B: source helpers

Shared helpers, caller-specific composition:

- touched files
- file excerpts
- git diff/stat
- repomix output

Shared preamble helpers live separately; they are not just another selector.

### Layer C: builder semantics

Task-specific:

- plan-close builder
- review packet builder
- overview builder
- research packet builder (later)

This is the only way the abstraction stays honest.

## What Should Migrate First

### Phase 0: write the contract

Deliverables:

- this plan
- final packet object model
- final builder list
- explicit non-goals

Exit condition:

- shared boundary is clear enough to implement without rediscovering the abstraction each time

### Phase 1: build the core

Deliverables:

- `shared/context_packet.py`
- `shared/file_specs.py`
- `shared/git_context.py`
- `shared/repomix_source.py`
- `shared/context_renderers.py`
- `shared/context_preamble.py`
- tests for rendering, truncation, hashing, normalization, and file-range parsing

Required tests:

- file path parsing
- single-line and range excerpt extraction
- diff block rendering
- packet manifest emission
- content-hash excludes timestamp metadata
- normalization contract is stable across repeated renders
- truncation markers
- deterministic rendering from same inputs
- touched-file resolution helpers
- NUL-delimited git parsing coverage for paths with spaces and renames
- git fixture coverage for renamed, deleted, and untracked files
- commit-range vs worktree coverage
- binary, symlink, and submodule policy coverage
- overview payload-hash equivalence fixtures
- golden packet equivalence fixtures for plan-close before and after migration

Exit condition:

- one real packet builder can migrate without keeping private copies of core mechanics

### Phase 1.5: align dispatch with packet artifacts

Targets:

- `shared/llm_dispatch.py`

Changes:

- add explicit input-budget metadata to dispatch profiles
- accept packet-artifact / manifest-aware handoff rather than only raw text paths
- consume packet `payload_hash` / manifest metadata instead of recomputing a parallel context hash where possible
- delete or deprecate dispatch-local `assemble_context(...)`

Exit condition:

- packet builders and dispatch agree on one payload hash and one input-budget contract

### Phase 2: migrate plan-close

Targets:

- `review/scripts/build_plan_close_context.py`
- `review/scripts/test_build_plan_close_context.py`

Why first:

- most explicit packet builder already exists
- low ambiguity
- current tests already provide a baseline

Exit condition:

- plan-close packet builder becomes a thin wrapper over shared packet primitives and selectors

### Phase 3: migrate model-review context assembly

Targets:

- `review/scripts/model-review.py`

Changes:

- delete local `parse_file_spec()`
- delete local `assemble_context_files()`
- delete local preamble-building duplication where possible
- reuse shared packet helpers for `--context-files` and per-axis packet creation
- share one payload artifact across axes when the underlying packet content is identical

Exit condition:

- model-review no longer owns a second packet-assembly subsystem

### Phase 4: migrate overview packet construction

Targets:

- `hooks/generate-overview.sh`
- `hooks/generate-overview-batch.sh`

Changes:

- move prompt/context assembly into a shared Python overview packet builder
- move config parsing and include-pattern construction into the same Python path
- move `repomix` argument construction into the same Python path
- move atomic write and generated-metadata injection into the same Python path
- target one Python entrypoint for live and batch overview generation
- keep a shell wrapper only if a named live caller still requires the script path
- unify live and batch source assembly, payload rendering, and manifest logic
- handle `repomix` capture as a staged file or streamed source, not mandatory in-memory text
- preserve the tagged prompt output format unless equivalence tests prove a renderer change is safe

Exit condition:

- live and batch overview generation share one packet-construction path
- prompt output and payload hash stay equivalent for identical inputs
- no active overview path still parses config or builds prompt payloads in shell

### Phase 5: add a general builder surface

Optional, only if justified by real callers:

- `scripts/context-packet.py`

Capabilities:

- render packet from file specs
- emit manifest
- support named builders (`plan-close`, `overview`, later `review`)

Exit condition:

- at least two live callers use the CLI surface without custom glue

### Phase 6: tighten enforcement

Add:

- tests preventing new ad hoc packet builders in active scripts
- import-boundary checks for active entrypoints
- guidance updates in `review` docs and any skill that assembles large context blobs

Exit condition:

- future packet drift gets caught automatically

## Specific File-Level Recommendations

### `review/scripts/build_plan_close_context.py`

- keep script path
- delete private packet rendering logic
- convert into `PlanClosePacketBuilder`
- keep CLI contract if users/scripts already call it

### `review/scripts/model-review.py`

- keep review-specific prompts and axis orchestration
- move packet mechanics out
- keep constitutional anchoring, but source the preamble assembly from shared selectors/helpers
- stop writing N semantically identical context payloads when one shared payload hash would suffice

### `shared/llm_dispatch.py`

- stop owning packet assembly
- publish input-budget metadata needed by packet builders
- prefer packet manifest / payload hash as the provenance source
- keep model/provider dispatch, retries, and output artifact ownership

### `hooks/generate-overview.sh`

- stop assembling packet text directly in shell
- stop parsing config and building include patterns in shell
- stop injecting generated metadata in shell
- target removal in favor of a Python entrypoint; keep only as a thin wrapper if the path still has live callers
- call a Python packet builder that returns:
  - context file path
  - manifest path
  - estimated token size
  - payload hash

### `hooks/generate-overview-batch.sh`

- reuse the same overview packet builder as the live path
- target deletion in favor of the same Python entrypoint as live mode, unless batch submission mechanics force a temporary wrapper

## Compatibility Boundaries

Default target: zero duplicated packet builders remain in active paths.

Possible temporary live boundary:

- `review/scripts/build_plan_close_context.py` remains as a stable script path while its internals migrate to shared code.

This is acceptable because the live external contract is the script path, not the private packet logic.

Removal condition for any remaining private packet helper:

- all active callers are using the shared packet engine
- tests cover the migrated path

## Risks

### 1. Fake abstraction

If the packet engine tries to own task semantics, it will turn into a bloated universal document schema.

Mitigation:

- keep selection logic builder-specific
- keep block types small and mechanical

### 1.5. Format overreach

If overview rendering is forced into the markdown packet path, the migration will silently change model-facing prompts while pretending only mechanics changed.

Mitigation:

- keep renderer choice explicit
- gate overview migration on prompt equivalence tests

### 2. Over-shelling

If shell scripts keep owning most of the packet logic, the new core becomes decorative.

Mitigation:

- move assembly into Python for overview paths
- leave shell only for orchestration/process control

### 3. Drift between packet engine and dispatch budgets

If packet truncation is unaware of practical model limits, callers will still hand overly large packets to dispatch.

Mitigation:

- support profile-aware token budgets for model-facing builders
- replace shell `bytes/4` heuristics with a Python-owned estimator tied to dispatch profiles
- emit metric and estimate method in the manifest
- require dispatch profiles to publish the input-budget data those estimators depend on

### 3.5. Silent migration drift

If old and new builders are not compared against golden outputs, packet migrations may change prompts or review packets without anybody noticing.

Mitigation:

- golden fixture tests for plan-close packets
- exact payload-hash equivalence tests for overview live vs batch on identical inputs

### 3.75. Non-text source mishandling

If binary files, symlinks, or submodules get rendered as if they were normal text inputs, packets will silently lie about source content.

Mitigation:

- explicit non-text policy in `shared/file_specs.py`
- fixture coverage for binary, symlink, and submodule inputs

### 4. Hidden migration claims

If a builder still owns private assembly code after “migration complete,” the repo will drift again.

Mitigation:

- name remaining boundaries explicitly in the plan and closeout

## Success Criteria

1. One shared packet engine exists and is used by:
   - plan-close builder
   - model-review context assembly
   - overview builder

2. No duplicated active-path helpers remain for:
   - file-range parsing
   - constitutional preamble assembly
   - packet rendering
   - truncation markers

3. Live and batch overview generation share one packet-construction path.

4. Packet manifests make context provenance inspectable.

5. New skills can adopt packet creation without inventing another custom assembler.

6. Overview migration preserves prompt shape or proves the deliberate change with explicit tests.

7. Golden fixtures catch packet drift during migration.

8. Live and batch overview modes produce the same payload hash for identical repo inputs.

9. Active entrypoints import shared packet helpers instead of re-implementing parsing/rendering locally.

10. `shared/llm_dispatch.py` no longer owns a separate context-assembly path or parallel context hash contract.

## Recommended First Implementation Slice

Do not start by trying to generalize everything.

Start here:

1. align `shared/llm_dispatch.py` with packet-artifact handoff
2. build `shared/context_packet.py`
3. migrate `build_plan_close_context.py`
4. reuse the same file/range parsing in `model-review.py`

That is the 1/10-code proof.

If that does not materially reduce duplication and drift, stop there.
