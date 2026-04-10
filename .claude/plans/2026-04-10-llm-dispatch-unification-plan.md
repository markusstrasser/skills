# LLM Dispatch Unification Plan

Date: 2026-04-10
Repo: `~/Projects/skills`
Status: implemented
Decision type: breaking refactor, full migration

## Problem

The skills repo currently has three conflicting stories about how agents should call models:

1. Some paths already use `llmx.api.chat()` and explicitly forbid CLI subprocess dispatch.
2. Some skills and hooks still teach or execute `llmx chat ...` shell commands.
3. `llmx-guide` is trying to be both a maintainer reference and an everyday agent execution guide.

That split-brain is now worse than either side alone. Agents see contradictory norms, copy examples from the wrong layer, and trigger the exact failure modes the guard is trying to block.

Concrete contradictions in the current repo:

- `hooks/pretool-llmx-guard.sh` blocks `llmx chat` CLI and tells agents to use Python API.
- `observe/SKILL.md`, `improve/SKILL.md`, and `review/scripts/model-review.py` already use the Python API pattern.
- `research-ops/SKILL.md` and `research-ops/scripts/run-cycle.sh` still route rate-limited work through raw `llmx chat`.
- `hooks/generate-overview.sh` still pipes prompt text into `llmx chat`.
- `brainstorm/references/llmx-dispatch.md` says "Python API, not CLI" but still shows CLI templates as the operative examples.
- `llmx-guide/SKILL.md` still reads like a primary execution manual for raw `llmx` usage rather than a low-level transport/debugging reference.

This repo needs one canonical dispatch path.

## Scope

- Target users: Claude/Codex agents operating through skills and repo hooks
- Scale:
  - current: ~18 active skills, ~33 hooks, a handful of scripts with model dispatch
  - designed-for: many projects importing these skills, repeated automated use, multiple dispatch surfaces
- Rate of change: high; skill and hook dispatch patterns are still evolving weekly

## Decision

Adopt one canonical architecture:

1. Agents do not compose raw `llmx chat` commands for normal workflows.
2. Skills and hooks call a shared Python dispatch helper.
3. The helper uses `llmx.api.chat()` with `api_only=True` by default.
4. Model choice is expressed as named profiles, not arbitrary model strings.
5. Outputs are artifacts plus typed metadata, not stdout scraping.
6. `llmx-guide` is demoted from "how most agents should call models" to "low-level maintainer/debugging reference."

This is a full migration. No compatibility wrappers, no dual path, no "temporary" CLI fallback inside ordinary skills.

Additional constraint:

- GPT must remain a first-class backend in the dispatch spine. This plan does not permit a Gemini-only helper with ad hoc GPT exceptions bolted on later.

## Why This Is The Right Boundary

The current evidence already converges on this:

- The guard blocks `llmx chat` CLI because agent-context failures were recurring, not theoretical.
- The review stack already escaped the CLI path and uses the Python API.
- The llmx repo itself has repeatedly patched CLI edge cases: stdin hangs, multi-file `-f`, shell redirect confusion, transport surprises, deprecated model names.
- Agents are bad at shell transport details and good at calling one stable local interface.

So the correct abstraction is not "teach every agent llmx better." It is "stop requiring most agents to know llmx transport rules at all."

## Target Architecture

### 1. Shared dispatch core + thin wrappers

Use an importable core module plus thin script entrypoints.

Suggested structure:

- core module: `shared/llm_dispatch.py`
- shell-facing wrapper: `scripts/llm-dispatch.py`

The core owns dispatch logic. The wrapper owns argument parsing and exit codes.

Responsibilities:

- import/bootstrap `llmx.api.chat`
- resolve a named dispatch profile into provider/model/timeout/schema/search defaults
- load context from a single file path or provided string
- execute one request
- write deterministic artifacts
- return typed metadata and typed error outcomes

The core module owns llmx bootstrap quirks. Individual skills do not repeat them.

Because this repo is not currently a normal Python package with declared runtime dependencies, the wrapper must also define an explicit bootstrap strategy. For v1, the simplest acceptable answer is:

- `uv run python3 scripts/llm-dispatch.py ...`
- PEP 723 inline script metadata on the wrapper so `llmx` and any schema/runtime dependencies resolve deterministically

No hidden "works if your machine already has the right uv tool installed" contract.

### 2. Named dispatch profiles

Agents and skills ask for profiles, not raw model IDs.

Initial profile set:

- `fast_extract`
  - default: `google / gemini-3-flash-preview`
  - low-cost extraction and classification
- `deep_review`
  - default: `google / gemini-3.1-pro-preview`
  - long-context structural critique
- `formal_review`
  - default: `openai / gpt-5.4`
  - `reasoning_effort=high`, long timeout
- `gpt_general`
  - default: `openai / gpt-5.4`
  - general-purpose OpenAI path for workflows that want GPT semantics outside formal review
- `search_grounded`
  - default: provider/model chosen for search-backed answer
- `cheap_tick`
  - low-cost synthesis for maintenance/research cycle ticks

Profiles are the contract. Underlying models can change centrally.

Each profile must have:

- stable profile name
- human-readable intent
- allowed overrides
- resolved provider/model/default kwargs
- `profile_version` or `profile_fingerprint`

`meta.json` records both the requested profile and the resolved implementation so downstream repos do not experience silent drift with no audit trail.

GPT-specific requirement:

- v1 must ship with at least one GPT-backed default profile beyond the formal-review path.
- Review and other cross-model workflows must continue to use GPT as a peer model, not as an emergency-only backend.

### 3. Artifact-first results

Every dispatch writes:

- markdown/text output
- `meta.json`
- optional `error.json`

Writes are atomic. The helper writes temp artifacts and only moves final outputs into place on success. Failure must never leave stale success output masquerading as current output.

`meta.json` must include:

- requested profile
- `profile_version` or `profile_fingerprint`
- resolved provider
- resolved model
- resolved kwargs
- `api_only`
- timeout
- schema used or null
- success/failure
- failure type
- latency
- `started_at`
- `finished_at`
- `context_sha256`
- `prompt_sha256`
- `llmx_version`
- `helper_version`
- output path

When schema-driven parsing is requested, the helper also writes a parsed artifact or explicit parse/validation failure metadata. Raw output is always preserved.

Do not rely on stdout as the primary contract.

### 4. Typed error taxonomy

The shared helper returns one of:

- `ok`
- `timeout`
- `rate_limit`
- `quota`
- `model_error`
- `schema_error`
- `parse_error`
- `empty_output`
- `config_error`
- `dependency_error`
- `dispatch_error`

Never collapse these into generic `ERROR`.

Each result also carries:

- `retryable: true|false`
- stable shell-facing exit code mapping for wrappers/hooks

### 5. Single-context rule

The shared helper accepts:

- `context_path`, or
- `context_text`

But the caller presents one assembled context unit.

The helper does not support agent-level multi-`-f` orchestration as a public contract.

To avoid pushing brittle text concatenation back into every caller, v1 also includes a tiny context assembly utility with a stable format:

- ordered source blocks
- clear file-boundary headers
- stable truncation/max-size rules

### 6. Human vs agent boundary

Two explicit layers:

- **Agent path:** shared Python dispatch helper only
- **Human terminal path:** raw `llmx` CLI allowed for ad hoc work, debugging, subcommands, and manual probing

This preserves useful CLI access without making it the automation substrate.

## What Changes

### A. Add the shared helper

Create:

- core: `shared/llm_dispatch.py`
- wrapper: `scripts/llm-dispatch.py`

Suggested public interface:

```python
dispatch(
    *,
    profile: str,
    prompt: str,
    context_path: Path | None = None,
    context_text: str | None = None,
    output_path: Path,
    meta_path: Path | None = None,
    error_path: Path | None = None,
    schema: dict | None = None,
    api_only: bool = True,
    overrides: DispatchOverrides | None = None,
) -> DispatchResult
```

Where `DispatchResult` is a small typed object or dict with:

- `status`
- `provider`
- `model`
- `latency`
- `output_path`
- `meta_path`
- `error_type`
- `error_message`

The wrapper CLI must support at minimum:

- `--profile`
- `--prompt`
- `--context-path`
- `--output`
- `--meta`
- `--error`
- `--schema-path`
- `--list-profiles`

### B. Move bootstrap code into one place

Today bootstrap logic is repeated in several places. The helper should own:

- uv tool venv import path probing
- optional local repo fallback for `~/Projects/llmx`
- clear failure if llmx is unavailable

No other skill or hook should hand-roll this import bootstrap after migration.

### C. Migrate existing Python-API users onto the shared helper

These are already aligned conceptually and should be first:

- `observe/SKILL.md`
- `improve/SKILL.md`
- `review/scripts/model-review.py`

For these, the migration is mostly deduplication:

- remove local bootstrap duplication
- route through profiles
- adopt shared artifact metadata shape

### D. Replace remaining CLI-executed agent paths

High-priority migration targets:

1. `research-ops/SKILL.md`
2. `research-ops/scripts/run-cycle.sh`
3. `hooks/generate-overview.sh`
4. `brainstorm/references/llmx-dispatch.md`

For shell-heavy hooks:

- either call a Python wrapper script that uses `scripts/llm_dispatch.py`
- or replace the hook’s llmx section with `uv run python3 ...` against the helper

Do not keep direct `llmx chat` in operational agent paths.

### E. Reposition `llmx-guide`

`llmx-guide` should remain, but with a narrower purpose.

New role:

- low-level debugging reference for llmx behavior
- maintainer reference for anyone editing `scripts/llm_dispatch.py`
- manual CLI usage guide for human terminal work
- reference for subcommands (`research`, `image`, `vision`, `svg`)

What it should stop being:

- the normal path by which agents learn how to do routine dispatch
- the place that teaches raw `llmx chat` as standard execution

Top-of-file rewrite needed:

- "Most agents should not call llmx directly."
- "Use the shared dispatch helper unless debugging or doing manual terminal work."

### F. Make the guard match the architecture cleanly

The current guard is directionally right, but the repo still contains sanctioned counterexamples.

After migration:

- keep blocking `llmx chat` in agent-triggered Bash
- update warnings to point to the shared wrapper/helper, not inline bootstrap snippets
- keep low-level llmx CLI warnings for maintainers/debuggers

## Immediate contradiction reduction

Before the helper rollout finishes, add short warning banners to the most misleading docs:

- `llmx-guide/SKILL.md`
- `brainstorm/references/llmx-dispatch.md`
- any live skill section still showing raw `llmx chat` as the normal agent path

This is not the full rewrite. It is a short-lived hygiene patch so the repo stops teaching the old path while the migration is in progress.

## Migration Plan

## Implementation Close

Implemented on 2026-04-10.

Delivered:

- `shared/llm_dispatch.py` as the shared profile-driven dispatch core
- `scripts/llm-dispatch.py` as the shell-facing wrapper
- direct helper tests in `scripts/test_llm_dispatch.py`
- guard regression tests in `hooks/test_pretool_llmx_guard.py`
- `review/scripts/model-review.py` migrated onto shared profile-driven dispatch
- live shell callers migrated off raw `llmx chat`:
  - `research-ops/scripts/run-cycle.sh`
  - `hooks/generate-overview.sh`
- active skill/docs updated to point at the shared helper first

Named live compatibility boundary kept intentionally:

- `hooks/generate-overview.sh` still accepts sibling repos' existing `OVERVIEW_MODEL` config and maps it to profiles.
- Removal condition: once sibling repos migrate overview configs to `OVERVIEW_PROFILE`, delete the legacy mapping.

### Phase 0: Write the contract

Deliverables:

- this plan
- one short design note for the helper contract
- final profile list
- final result schema

Exit condition:

- shared interface is stable enough that multiple skills can adopt it without inventing variants

### Phase 1: Build the helper

Deliverables:

- `shared/llm_dispatch.py`
- `scripts/llm-dispatch.py`
- tests for dispatch success/failure classification
- minimal example script

Required tests:

- successful text response
- timeout classification
- quota/rate-limit classification
- empty-output classification
- schema handling path
- metadata file emission
- profile resolution
- shell exit code mapping
- atomic write behavior / stale-output protection

Exit condition:

- helper can replace one real skill path without custom glue

### Phase 2: Migrate the review stack

Targets:

- `review/scripts/model-review.py`

Why first:

- high leverage
- already Python API based
- existing tests
- central to cross-model review discipline
- guarantees GPT is in the first real proving ground for the helper

Exit condition:

- review dispatch no longer owns its own llmx bootstrap or ad hoc result envelope

### Phase 3: Migrate observe and improve

Targets:

- `observe/SKILL.md`
- `improve/SKILL.md`

Why:

- already conceptually aligned
- repetitive boilerplate
- easy wins for consistency

Exit condition:

- no repeated bootstrap snippets remain in those skill instructions

### Phase 4: Kill CLI dispatch in agent workflows

Targets:

- `research-ops/SKILL.md`
- `research-ops/scripts/run-cycle.sh`
- `hooks/generate-overview.sh`
- any remaining live `llmx chat` operational paths

Why:

- these are the highest-value contradiction removals
- they are exactly what the guard says not to do

Exit condition:

- no live agent workflow in the skills repo depends on raw `llmx chat`

### Phase 5: Rewrite `llmx-guide`

Targets:

- `llmx-guide/SKILL.md`
- selected references under `llmx-guide/references/`

Changes:

- demote routine CLI guidance
- emphasize dispatch-helper-first usage
- keep low-level llmx failure/transport/debugging details
- separate "manual CLI" examples from "automation architecture"

Exit condition:

- the skill no longer teaches agents a path they are expected not to use

### Phase 6: Tighten enforcement

Add or update:

- hook checks for `subprocess.*llmx`
- hook checks for raw `llmx chat` examples in live skill execution sections
- tests around helper/profile usage in central scripts

Exit condition:

- future regressions toward raw CLI dispatch are caught automatically

## Specific File-Level Recommendations

### `review/scripts/model-review.py`

- keep the overall architecture
- replace local llmx bootstrap with shared helper import
- centralize result envelope and metadata writing
- avoid helper logic divergence from other skills
- move provider-specific schema normalization into the shared core

### `observe/SKILL.md`

- stop showing inline bootstrap snippets
- show one short helper call pattern instead

### `improve/SKILL.md`

- same as observe
- refer to the helper and profiles, not direct `llmx_chat(...)` boilerplate

### `research-ops/SKILL.md`

- remove raw `llmx chat` fallback examples
- replace with helper-driven `uv run python3` invocation

### `research-ops/scripts/run-cycle.sh`

- either replace with a Python script or shell out only to a Python dispatch wrapper
- remove `2>/dev/null` swallowing of diagnostics
- stop using stdout emptiness as the main success test

### `hooks/generate-overview.sh`

- this should be refactored hardest, not papered over
- replace pipe-to-CLI generation with a helper-backed wrapper that writes output and metadata atomically
- preserve the atomic final move behavior, but not the dispatch mechanism
- likely end state: rewrite as Python, not shell + inline Python + llm helper indirection

### `brainstorm/references/llmx-dispatch.md`

- make examples actually Python API based
- if CLI examples remain at all, mark them explicitly as manual/human-only

### `llmx-guide/SKILL.md`

- rewrite intro and checklist around the new boundary:
  - "Should you be calling llmx directly at all?"
  - "If this is a skill or hook, use the shared helper."
- "Use this guide only when editing the helper or debugging low-level llmx behavior."

## Success Criteria

The migration is successful when:

1. The repo has one obvious answer to "how should an agent dispatch to a model?"
2. No live agent workflow uses raw `llmx chat`.
3. `llmx-guide` no longer conflicts with the guard.
4. New skills can dispatch through one profile-based interface without re-learning transport internals.
5. Failures become diagnosable from artifacts and typed status, not shell transcripts.
6. Hooks and shell callers have a stable wrapper contract with defined exit codes.
7. GPT remains part of the default supported dispatch surface, not a niche or fallback-only path.

## Non-Goals

- making all human terminal llmx usage disappear
- wrapping every possible llmx subcommand behind the helper on day one
- supporting both CLI and Python dispatch as coequal long-term architectures
- preserving existing CLI snippets for compatibility

## Risks

1. The helper becomes too magical.
   Mitigation: keep it narrow; one-shot text dispatch first, not a universal orchestration framework.

2. Skills lose useful flexibility.
   Mitigation: expose `extra_kwargs` and named profiles, but keep the public surface small.

3. Hooks become more complex if they must call Python wrappers.
   Mitigation: complexity is already present; centralizing it is an improvement, not a net increase.

4. `llmx-guide` becomes redundant.
   Mitigation: that is acceptable if its remaining audience is maintainers/debuggers rather than everyday agent execution.

## Open Questions

1. Should artifact metadata use plain JSON schema only or also an internal typed model?
2. Should hooks call the shared wrapper directly or via tiny task-specific wrapper scripts?
3. Do we want one unified helper for all llmx subcommands later, or only for chat-style dispatch?

## Resolved Choices

These are now fixed for v1:

1. Core logic lives in an importable module, not only a script file.
2. A thin shell-facing wrapper exists because some callers are hooks/scripts.
3. The wrapper owns explicit exit-code mapping.
4. Bootstrap/dependency resolution must be deterministic via the wrapper, not ambient machine state.
5. Per-call overrides are constrained; callers do not supply arbitrary provider/model kwargs.

## Recommended First Move

Do not start by rewriting `llmx-guide`.

Start by building `shared/llm_dispatch.py` plus `scripts/llm-dispatch.py`, then migrate `review/scripts/model-review.py` onto it. That proves the interface on the highest-value existing Python-API path. In parallel, land the short contradiction-reduction banners so the repo stops teaching the old path while the migration is underway.
