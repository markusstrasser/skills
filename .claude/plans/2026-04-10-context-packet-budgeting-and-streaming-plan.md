# Context Packet Budgeting And Streaming Plan

Date: 2026-04-10
Repo: `~/Projects/skills`
Status: implemented
Decision type: breaking refactor, full migration

## Problem

The shared context-packet layer exists now, but it still has one major architectural gap:

- packet budgeting is mostly descriptive, not enforceable

Today:

- `shared/context_packet.py` records `BudgetPolicy` and manifest metadata
- truncation still happens in caller-specific helpers like `shared/file_specs.py` and `shared/git_context.py`
- `review/scripts/build_plan_close_context.py` still decides truncation up front using static character caps
- `scripts/generate_overview.py` builds whole payloads in memory, then dispatches them as giant strings

That means the new layer unified representation and provenance, but not the actual control point that decides:

1. what fits into a model input budget
2. what gets truncated or dropped first
3. how to handle very large source inputs without wasteful buffering

The result is a half-finished abstraction:

- packet manifests are better
- packet reuse is better
- but packet budget behavior is still fragmented

This is the next design stage.

## Why This Stage Exists

The current system has three distinct needs that should not be conflated:

1. **Truthful packet accounting**
   Manifests and dispatch metadata must describe what was actually sent.

2. **Deterministic budget enforcement**
   A caller should be able to say:
   - use profile `formal_review`
   - fit this packet into that profile's safe input budget
   - truncate or drop lower-priority material in a predictable way

3. **Efficient handling of large source blobs**
   Some payloads, especially overview generation, should avoid unnecessary disk-memory-disk churn.

The previous integration stage solved mostly (1).
This stage should solve (2), and only then solve the efficient path for (3).

## Direct Answer: Why Streaming?

Streaming is not the core design goal. It is an implementation tactic for one narrow class of payloads.

It makes sense because overview generation currently does this:

1. write repomix output to `.overview-*-codebase.txt`
2. read that entire file back with `read_text()`
3. embed it into a packet
4. write the packet to `.overview-*-payload.txt`
5. read the payload again for dispatch or batch JSONL assembly

That is extra I/O and extra RAM for data that is already materialized on disk.

Streaming is useful when:

- one block is huge
- the block is already on disk
- we mostly want to splice it into a larger artifact without transforming it much

Streaming is **not** needed for:

- plan-close packets
- review packets
- ordinary file excerpts
- most preamble/context assembly

So the correct stance is:

- do **not** redesign the whole packet system around streaming
- do add a bounded streaming-capable block or renderer path for large overview/codebase payloads

## Decision

Implement a second-stage packet architecture with:

1. **functional budget enforcement**
2. **priority-aware truncation/drop policy**
3. **optional large-block streaming for overview/codebase paths**

Do this without turning `ContextPacket` into a magical all-knowing engine.

The right boundary is:

- packet model remains a data structure
- packet builder/enforcer performs budgeting
- renderers stay deterministic
- streaming is an optimization path for specific block types

## Non-Goals

Do not do these in this stage:

- no fake tokenization precision claims beyond the existing estimator contract
- no attempt to make every block type streamable
- no universal semantic ranking of blocks across all tasks
- no model-specific prompt-caching optimization layer
- no mixed partial-dispatch protocol where models consume manifests plus out-of-band file pointers

This stage is still about one concrete thing:

- produce one truthful, bounded artifact for dispatch

## Current Failure Modes

### 1. Budgets are selected too early and too locally

`build_plan_close_context.py` still truncates diff and file excerpts before packet assembly.

Consequence:

- callers own budget logic
- packet layer cannot reason about tradeoffs across sections
- packet manifests are downstream of truncation, not the controller of it

### 2. Character caps are not model budgets

The current review/plan-close flow still thinks in terms of:

- `max_diff_chars`
- `max_file_chars`
- `max_files`

Those are useful controls, but they are not the same as:

- safe input budget for `formal_review`
- safe input budget for `deep_review`

### 3. Large-block handling is inefficient

Overview generation reads entire repomix captures into RAM and rewrites them.

Consequence:

- avoidable memory pressure
- extra disk churn
- harder future support for truly large repos

### 4. Block priority is implicit instead of encoded

Right now the system has no shared concept of:

- preamble is highest priority
- instructions are highest priority
- touched-file list is cheap and useful
- diff is usually more valuable than full file tails
- omitted-file notices are expendable

Without this, any future truncation engine will be ad hoc.

## Target Architecture

### 1. Add a packet budgeting layer

Add a new shared module:

- `shared/context_budget.py`

Responsibilities:

- estimate rendered packet cost
- enforce profile or explicit budget limits
- apply ordered truncation/drop rules
- emit truncation events and omission events

Core API shape:

```python
enforced = enforce_budget(
    packet,
    policy=BudgetPolicy(...),
    strategy=BudgetStrategy(...),
)
```

Return value:

- a new `ContextPacket`
- normalized truncation/omission metadata
- final estimate info

Do not mutate packets in place.

### 2. Add explicit block priority / budget hints

Extend `PacketBlock` or section/block metadata with:

- `priority`: integer or enum
- `min_chars`: optional lower bound if truncatable
- `preferred_chars`: optional target
- `drop_if_needed`: boolean

Example defaults:

- `PreambleBlock`: highest priority, non-droppable
- overview instructions: highest priority, non-droppable
- touched-file list: medium priority
- diff block: high priority, truncatable
- full file excerpts: medium priority, truncatable/droppable after diff
- omitted-file notices: low priority, droppable

This should be mechanical, not semantic. Builders choose the priorities.

### 3. Move plan-close onto profile-aware budgeting

Refactor `review/scripts/build_plan_close_context.py` to accept:

- `--profile formal_review` or equivalent

Behavior:

- look up profile input budget from `shared/llm_dispatch.py`
- build packet with raw-ish blocks and local safety caps
- run packet through budget enforcement
- write bounded artifact and truthful manifest

Keep local hard caps as guardrails, not final truth:

- per-file safety ceiling
- diff safety ceiling
- max files

But the final packet fit decision belongs to the budget enforcer.

### 4. Add a streamed large-file block for overview payloads

Add a bounded type such as:

- `SourceFileBlock`
- or `FileReferenceBlock`

Properties:

- source path on disk
- optional prefix/suffix text
- optional precomputed size/hash
- renderer knows how to splice file contents directly into the output artifact

This block exists only for cases like:

- repomix output
- possibly very large generated corpus snapshots later

Do not generalize it beyond that unless a second caller appears.

### 5. Keep dispatch contract unchanged at the top

`shared/llm_dispatch.py` should still receive:

- a concrete prompt string or prompt artifact path
- a manifest path

Do not make dispatch understand packet internals.

The packet system should still collapse to:

- one payload file
- one manifest file

That is the contract worth preserving.

## Streaming Design

### What “streaming” should mean here

Not network streaming. Not token streaming.

It means:

- writing the final artifact by incrementally copying large block contents from disk into the destination file
- without first loading the whole large block into a Python string

### Where it should apply

Only to renderers that can benefit:

- overview tagged renderer
- possibly future markdown packet generation for giant source snapshots

### Where it should not apply

- ordinary text blocks
- most review packets
- model-review context assembly

### Minimal viable streaming implementation

Do not overbuild.

Stage 1:

- keep current `ContextPacket` for normal blocks
- add one renderer path that accepts a `FileReferenceBlock`
- write prefix
- copy file bytes/text chunkwise
- write suffix
- continue rendering other blocks

Stage 2, only if needed:

- support chunk-aware token estimation for streamed blocks

Until then, token estimate for streamed blocks can remain:

- file size derived
- or whole-file text length estimated from stat/read during manifest construction

## Implementation Stages

### Phase 1: Budget semantics

Deliverables:

- `shared/context_budget.py`
- priority/drop metadata on blocks
- packet enforcement function
- tests for deterministic truncation/drop ordering

Success criteria:

- packet builder can produce an over-budget packet
- enforcer shrinks it to fit budget
- manifest reflects actual truncation/omission events

### Phase 2: Plan-close migration

Deliverables:

- `build_plan_close_context.py` accepts profile-based budgeting
- static char args become guardrails or advanced overrides
- manifests report truthful final budget estimate

Success criteria:

- same repo input with same profile yields stable packet hash
- final packet estimate is within configured profile budget
- tests cover over-budget cases

### Phase 3: Overview streaming path

Deliverables:

- `FileReferenceBlock` or equivalent
- tagged renderer support for streamed codebase block
- overview payload builder uses streamed repomix block

Success criteria:

- no full `read_text()` of repomix output in overview path
- payload hash remains deterministic
- live and batch payload hashes remain equal for same input state

### Phase 4: Optional review migration

Deliverables:

- `model-review.py` can optionally enforce profile-aware budget on shared context packets

This is optional because current review paths may already fit within practical limits, and forcing this too early risks unnecessary churn.

## Tests Required

### Budget enforcement tests

- over-budget packet drops lowest-priority block first
- non-droppable blocks survive
- truncatable blocks shrink before non-truncatable blocks are dropped
- final estimate is `<= limit`
- repeated runs are deterministic

### Plan-close tests

- profile-aware path produces bounded packet
- manifest truncation events match actual dropped/truncated blocks
- legacy safety cap overrides still work when explicitly set

### Overview tests

- prompt template path and repomix source path remain in manifest
- live and batch payload hashes match
- streaming renderer produces same payload bytes as non-streamed reference path for the same inputs

## Risks

### 1. Fake token precision

If this stage pretends to know exact token counts, it will create false confidence.

Mitigation:

- keep estimate method explicit
- use “safe input budget” language, not exact limit language
- continue storing estimator method in manifest/meta

### 2. Overgeneralized budget engine

A too-clever engine will become hard to reason about.

Mitigation:

- simple deterministic ordering
- builder chooses priorities
- no hidden semantic heuristics

### 3. Streaming complexity creep

If every block becomes streamable, the renderer becomes ugly fast.

Mitigation:

- only one streamed block type in v1
- only one concrete caller required: overview codebase block

## What I Would Not Do

- Do not redesign dispatch around multi-file or out-of-band source passing.
- Do not wait for “perfect tokenizer-aware budgeting” before building enforcement.
- Do not treat streaming as mandatory infrastructure for all packets.
- Do not move all truncation logic into renderers; keep policy in a budget layer, rendering in renderers.

## Recommended First Slice

Build the 1/10-code version first:

1. `context_budget.enforce_budget(packet, policy)`
2. support only dropping whole low-priority blocks plus existing block-local truncation
3. wire it into `build_plan_close_context.py`
4. add determinism tests

Only after that works:

5. add streamed overview codebase blocks

This is the right order because budget enforcement is the architectural need. Streaming is just the optimization that becomes worthwhile once the budget path is correct.
