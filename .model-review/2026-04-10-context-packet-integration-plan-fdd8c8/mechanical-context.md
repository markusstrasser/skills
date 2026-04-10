# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler/hacky approaches because they're 'faster to implement'
- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort
- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters

# .claude/plans/2026-04-10-context-packet-integration-plan.md

# Context Packet Integration Plan

Date: 2026-04-10
Repo: `~/Projects/skills`
Status: proposed
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

### 2. Shared selection helpers

Add:

- `shared/context_selectors.py`

Responsibilities:

- file path parsing (`path`, `path:start`, `path:start-end`)
- excerpt extraction
- touched-file resolution from git
- diff collection
- status collection
- constitution/goals discovery
- optional `repomix` capture helper

Important: these are helpers, not a monolithic builder.

### 3. Shared renderers

Add:

- `shared/context_renderers.py`

Responsibilities:

- markdown rendering
- optional JSON manifest emission
- section headers and block labels
- file-boundary labeling
- truncation markers

Do not add multiple output formats unless a live caller needs them. Markdown + manifest JSON is enough for v1.

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

## Canonical Contract

### `ContextPacket`

Suggested minimal shape:

```python
ContextPacket(
    title: str,
    scope: str | None,
    sections: list[PacketSection],
    metadata: dict[str, Any],
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
- `FileBlock(path, text, range_spec=None)`
- `DiffBlock(label, diff_text)`
- `CommandBlock(command, output_text)`
- `ListBlock(title, items)`

### Manifest fields

Every rendered packet should be able to emit a manifest with:

- packet title
- builder name/version
- created timestamp
- source block list
- source paths
- block hashes
- total rendered bytes
- truncation events

This becomes the provenance surface for context creation.

## What “Generalized” Means

This plan deliberately separates three layers:

### Layer A: packet mechanics

Shared:

- render markdown
- compute hashes
- truncate
- label sections
- label source provenance

### Layer B: selectors

Shared helpers, caller-specific composition:

- touched files
- file excerpts
- git diff/stat
- constitution/goals
- repomix output

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
- `shared/context_selectors.py`
- `shared/context_renderers.py`
- tests for rendering, truncation, hashing, and file-range parsing

Required tests:

- file path parsing
- single-line and range excerpt extraction
- diff block rendering
- packet manifest emission
- truncation markers
- deterministic rendering from same inputs
- touched-file resolution helpers

Exit condition:

- one real packet builder can migrate without keeping private copies of core mechanics

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

Exit condition:

- model-review no longer owns a second packet-assembly subsystem

### Phase 4: migrate overview packet construction

Targets:

- `hooks/generate-overview.sh`
- `hooks/generate-overview-batch.sh`

Changes:

- move prompt/context assembly into a shared Python overview packet builder
- keep shell orchestration only for process control if still needed
- unify live and batch packet shape

Exit condition:

- live and batch overview generation share one packet-construction path

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
- grep-based checks for duplicated file-range parsing helpers
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

### `hooks/generate-overview.sh`

- stop assembling packet text directly in shell
- shell remains orchestration only
- call a Python packet builder that returns:
  - context file path
  - manifest path
  - estimated token size

### `hooks/generate-overview-batch.sh`

- reuse the same overview packet builder as the live path
- keep only batch submission/distribution logic in shell

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

### 2. Over-shelling

If shell scripts keep owning most of the packet logic, the new core becomes decorative.

Mitigation:

- move assembly into Python for overview paths
- leave shell only for orchestration/process control

### 3. Drift between packet engine and dispatch budgets

If packet truncation is unaware of practical model limits, callers will still hand overly large packets to dispatch.

Mitigation:

- support profile-aware truncation budgets or at least builder-provided limits
- emit packet size metadata in the manifest

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

## Recommended First Implementation Slice

Do not start by trying to generalize everything.

Start here:

1. build `shared/context_packet.py`
2. migrate `build_plan_close_context.py`
3. reuse the same file/range parsing in `model-review.py`

That is the 1/10-code proof.

If that does not materially reduce duplication and drift, stop there.



# review/scripts/build_plan_close_context.py

#!/usr/bin/env python3
"""Build a single markdown review packet for plan-close / post-implementation review.

The packet is intentionally single-file because llmx multi-file `-f` transport
has recurring loss/truncation failures in critical review flows.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def log_progress(message: str) -> None:
    print(f"[build-plan-close-context] {message}", file=sys.stderr)


def run_git(repo: Path, args: list[str], *, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def diff_ref(base: str | None, head: str | None) -> str | None:
    if base and head:
        return f"{base}..{head}"
    if base:
        return f"{base}..HEAD"
    if head:
        return f"HEAD..{head}"
    return None


def parse_status_paths(status_text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for raw_line in status_text.splitlines():
        line = raw_line.rstrip()
        if len(line) < 4:
            continue
        path_field = line[3:]
        if " -> " in path_field:
            path_field = path_field.split(" -> ", 1)[1]
        if path_field and path_field not in seen:
            seen.add(path_field)
            paths.append(path_field)
    return paths


def unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def resolve_touched_files(
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
) -> list[str]:
    if files:
        return unique_paths(files)

    ref = diff_ref(base, head)
    if ref:
        names = run_git(repo, ["diff", "--name-only", ref, "--"]).splitlines()
        return [name for name in names if name.strip()]

    if tracked_only:
        names = run_git(repo, ["diff", "--name-only", "HEAD", "--"], check=False).splitlines()
        return [name for name in names if name.strip()]

    status_text = run_git(repo, ["status", "--short", "--untracked-files=all"])
    return parse_status_paths(status_text)


def current_status(repo: Path, *, tracked_only: bool) -> str:
    args = ["status", "--short"]
    args.append("--untracked-files=no" if tracked_only else "--untracked-files=all")
    return run_git(repo, args, check=False).strip()


def untracked_paths(repo: Path) -> set[str]:
    raw = run_git(repo, ["ls-files", "--others", "--exclude-standard"], check=False)
    return {line.strip() for line in raw.splitlines() if line.strip()}


def collect_diff_stat(repo: Path, *, ref: str | None, files: list[str]) -> str:
    tracked_files = [path for path in files if path not in untracked_paths(repo)]
    if not tracked_files:
        return "(no tracked diff stat available)"
    args = ["diff", "--stat"]
    if ref:
        args.append(ref)
    else:
        args.append("HEAD")
    args.append("--")
    args.extend(tracked_files)
    return run_git(repo, args, check=False).strip() or "(empty diff stat)"


def collect_diff(repo: Path, *, ref: str | None, files: list[str]) -> str:
    tracked_files = [path for path in files if path not in untracked_paths(repo)]
    if not tracked_files:
        return "(no tracked unified diff available)"
    args = ["diff", "--unified=3"]
    if ref:
        args.append(ref)
    else:
        args.append("HEAD")
    args.append("--")
    args.extend(tracked_files)
    return run_git(repo, args, check=False).strip() or "(empty diff)"


def read_excerpt(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(errors="replace")
    except OSError as exc:
        return f"[read failed: {exc}]"

    if len(text) <= max_chars:
        return text

    head = max_chars // 2
    tail = max_chars - head
    return (
        text[:head]
        + "\n\n... [truncated for review packet] ...\n\n"
        + text[-tail:]
    )


def file_section(repo: Path, rel_path: str, *, max_chars: int) -> str:
    path = repo / rel_path
    if not path.exists():
        return f"### {rel_path}\n\n(deleted or absent in current worktree)\n"

    return (
        f"### {rel_path}\n\n"
        f"```text\n{read_excerpt(path, max_chars)}\n```\n"
    )


def build_packet(
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
    scope_text: str | None,
    scope_file: Path | None,
    max_diff_chars: int,
    max_file_chars: int,
    max_files: int,
) -> str:
    log_progress("resolving touched files")
    touched = resolve_touched_files(repo, base=base, head=head, files=files, tracked_only=tracked_only)
    ref = diff_ref(base, head)
    log_progress("collecting git status")
    status_text = current_status(repo, tracked_only=tracked_only) or "(clean)"
    log_progress(f"collecting diffs for {len(touched)} touched files")
    diff_stat = collect_diff_stat(repo, ref=ref, files=touched) if touched else "(no touched files)"
    diff_text = collect_diff(repo, ref=ref, files=touched) if touched else "(no touched files)"
    if len(diff_text) > max_diff_chars:
        diff_text = diff_text[:max_diff_chars] + "\n\n... [diff truncated] ..."

    if scope_file is not None:
        scope_block = scope_file.read_text()
    elif scope_text:
        scope_block = scope_text
    else:
        scope_block = (
            "- Target users: FILL ME\n"
            "- Scale: FILL ME\n"
            "- Rate of change: FILL ME\n"
        )

    packet = [
        "# Plan-Close Review Packet",
        "",
        f"- Repo: `{repo}`",
        f"- Mode: `{'commit-range' if ref else 'worktree'}`",
        f"- Ref: `{ref or 'HEAD vs current worktree'}`",
        "",
        "## Scope",
        "",
        scope_block.strip(),
        "",
        "## Touched Files",
        "",
    ]

    if touched:
        packet.extend(f"- `{path}`" for path in touched)
    else:
        packet.append("- (none)")

    packet.extend(
        [
            "",
            "## Git Status",
            "",
            "```text",
            status_text,
            "```",
            "",
            "## Diff Stat",
            "",
            "```text",
            diff_stat,
            "```",
            "",
            "## Unified Diff",
            "",
            "```diff",
            diff_text,
            "```",
            "",
            "## Current File Excerpts",
            "",
        ]
    )

    display_files = touched[:max_files]
    log_progress(f"reading excerpts for {len(display_files)} files")
    for rel_path in display_files:
        packet.append(file_section(repo, rel_path, max_chars=max_file_chars))

    omitted = len(touched) - len(display_files)
    if omitted > 0:
        packet.append(f"\n(Omitted {omitted} additional touched files from excerpts.)\n")

    return "\n".join(packet)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Git repo to inspect")
    parser.add_argument("--output", type=Path, required=True, help="Markdown packet path")
    parser.add_argument("--base", help="Base git ref for commit-range review")
    parser.add_argument("--head", help="Head git ref for commit-range review")
    parser.add_argument("--file", action="append", dest="files", help="Specific file to include; may repeat")
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help=(
            "In worktree mode, limit touched files and git status to tracked changes only. "
            "Use this on dirty repos with large .scratch/ or other untracked trees."
        ),
    )
    parser.add_argument("--scope-text", help="Inline scope block for the packet")
    parser.add_argument("--scope-file", type=Path, help="File containing the scope block")
    parser.add_argument("--max-diff-chars", type=int, default=40_000)
    parser.add_argument("--max-file-chars", type=int, default=8_000)
    parser.add_argument("--max-files", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        print(f"not a git repo: {repo}", file=sys.stderr)
        return 2

    packet = build_packet(
        repo,
        base=args.base,
        head=args.head,
        files=args.files,
        tracked_only=args.tracked_only,
        scope_text=args.scope_text,
        scope_file=args.scope_file,
        max_diff_chars=args.max_diff_chars,
        max_file_chars=args.max_file_chars,
        max_files=args.max_files,
    )

    log_progress(f"writing packet to {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(packet)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



# review/scripts/model-review.py (lines 430-560)

        except (ValueError, IndexError):
            pass
    elif range_spec:
        try:
            line_no = int(range_spec) - 1
            lines = text.splitlines()
            text = lines[line_no] if 0 <= line_no < len(lines) else text
        except (ValueError, IndexError):
            pass

    return f"# {file_path}" + (f" (lines {range_spec})" if range_spec else "") + f"\n\n{text}\n\n"


def assemble_context_files(specs: list[str]) -> str:
    """Assemble content from multiple file:range specs into one context string."""
    parts = []
    for spec in specs:
        parts.append(parse_file_spec(spec.strip()))
    return "\n".join(parts)


def build_context(
    review_dir: Path,
    project_dir: Path,
    context_file: Path | None,
    axis_names: list[str],
    *,
    context_file_specs: list[str] | None = None,
) -> dict[str, Path]:
    """Assemble per-axis context files with constitutional preamble.

    Context sources (in order of precedence):
      1. --context FILE — single pre-assembled context file
      2. --context-files spec1 spec2 ... — auto-assembled from file:range specs
    """
    constitution, goals_path = find_constitution(project_dir)

    preamble = ""
    if constitution:
        # Always include full constitution verbatim — summaries lose nuance
        # that causes reviewers to over-apply or misapply principles
        preamble += "# PROJECT CONSTITUTION (verbatim — review against these, not your priors)\n\n"
        preamble += constitution + "\n\n"
    if goals_path:
        preamble += "# PROJECT GOALS\n\n"
        preamble += Path(goals_path).read_text() + "\n\n"

    # Agent economics framing — always included so reviewers don't
    # recommend trading quality for dev time (which is ~free with agents)
    preamble += "# DEVELOPMENT CONTEXT\n"
    preamble += "All code, plans, and features in this project are developed by AI agents, not human developers. "
    preamble += "Dev creation time is effectively zero. Therefore:\n"
    preamble += "- NEVER recommend trading stability, composability, or robustness for dev time savings\n"
    preamble += "- NEVER recommend simpler/hacky approaches because they're 'faster to implement'\n"
    preamble += "- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort\n"
    preamble += "- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters\n\n"

    # Assemble content from the right source
    if context_file:
        content = context_file.read_text()
    elif context_file_specs:
        content = assemble_context_files(context_file_specs)
    else:
        content = ""

    ctx_files = {}
    for axis in axis_names:
        ctx_path = review_dir / f"{axis}-context.md"
        ctx_path.write_text(preamble + content)
        ctx_files[axis] = ctx_path

    # Warn on size
    for axis, path in ctx_files.items():
        size = path.stat().st_size
        if size > 15_000:
            print(f"warning: {axis} context {size} bytes > 15KB — consider summarizing", file=sys.stderr)

    return ctx_files


def dispatch(
    review_dir: Path,
    ctx_files: dict[str, Path],
    axis_names: list[str],
    question: str,
    has_constitution: bool,
    question_overrides: dict[str, str] | None = None,
) -> dict:
    """Fire N llmx API calls in parallel (one per axis), wait, return results."""
    today = date.today().isoformat()

    const_instruction = {
        "arch": (
            "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?"
            if has_constitution
            else "No constitution provided — assess internal consistency only."
        ),
        "formal": (
            "For each constitutional principle: coverage score (0-100%), specific gaps, suggested fixes."
            if has_constitution
            else "No constitution provided — assess internal logical consistency."
        ),
    }

    prompts: dict[str, str] = {}
    t0 = time.time()

    for axis in axis_names:
        axis_def = AXES[axis]
        axis_question = (question_overrides or {}).get(axis, question)
        prompts[axis] = axis_def["prompt"].format(
            date=today,
            question=axis_question,
            constitution_instruction=const_instruction.get(axis, ""),
        )

    def _run_axis(axis: str) -> tuple[str, dict]:
        axis_def = AXES[axis]
        profile_name = str(axis_def["profile"])
        profile_def = dispatch_core.PROFILES[profile_name]
        out_path = review_dir / f"{axis}-output.md"
        result = _call_llmx(
            provider=profile_def.provider,
            model=profile_def.model,
            context_path=ctx_files[axis],
            prompt=prompts[axis],
            output_path=out_path,
        )
        entry = {
            "label": axis_def["label"],
            "requested_model": profile_def.model,


# review/references/context-assembly.md

<!-- Reference file for model-review skill. Loaded on demand, not auto-loaded into context. -->

# Context Assembly

Detailed instructions for assembling review context. SKILL.md covers the anti-patterns table (the judgment calls); this file covers the mechanical "how to gather context" instructions.

## Narrow Reviews (Manual Assembly)

The review target (plan, design doc, code) plus enough surrounding context for models to understand the decision space. Use Read/Grep to gather, then Write to a single `context.md`.

**Context sources to check** (not all required -- pick what's relevant to *this* review):

| Source | When to include | How to get it |
|--------|----------------|---------------|
| The artifact itself | Always | Read the file |
| Code it references | When reviewing a plan or design that names specific files | Read the referenced files, or summarize signatures |
| Tests for that code | When reviewing implementation correctness | Grep for test files, include relevant cases |
| Recent git history | When reviewing a change or refactor | `git log --oneline -10 -- <path>` or `git diff` |
| Related CLAUDE.md sections | When the review involves conventions or architecture | Read the relevant section, not the whole file |
| Project operational context | When the review touches code with deliberate constraints | `.claude/rules/vetoed-decisions.md`, key rules files, data-sources docs. Models that don't know about vetoes and deliberate exclusions will propose re-enabling them. Include as context, not binding constraints — the model may correctly argue a prior decision is outdated. |
| Upstream constraints | When the review depends on external APIs, schemas, or specs | Include the relevant spec snippet |

**What NOT to include:** unrelated code, full CLAUDE.md dumps, entire test suites, historical context that doesn't inform the decision. Noise dilutes the review -- models spend tokens on irrelevant material instead of finding real problems.

## Broad Reviews (Codebase/Architecture)

For whole-repo or multi-file architectural reviews, you need a compressed representation of the codebase.

**Options (check in order):**
1. **`.claude/rules/codebase-map.md`** -- already auto-loaded in your context if it exists. File map with descriptions + import edges. Available in: meta, intel, genomics, research-mcp, selve. If present, you already have it -- just include it in the context file.
2. **`repo-summary.py --compact`** -- generate on-demand if no codebase-map exists. Good for "what does this repo do" reviews.
3. **`repo-outline.py outline`** -- function/class signatures. Good for API surface or coupling reviews.
4. **`.context/` views** -- if the project has them (`make -C .context all 2>/dev/null`).
5. **Manual assembly** -- Read key files (entry points, config, core logic), summarize the rest. Most flexible but slowest.

For broad reviews, always include: entry points, the files under question, and the project's stated architecture (CLAUDE.md relevant sections). Omit: tests, generated files, vendored deps.

## Constitutional Preamble (Script Handles This)

The dispatch script auto-injects constitutional preamble. For manual dispatch, find and inject it yourself:

```bash
# Check for project principles
CONSTITUTION=$(find . -maxdepth 3 -name "CONSTITUTION.md" 2>/dev/null | head -1)
if [ -z "$CONSTITUTION" ]; then
  CLAUDE_MD=$(find . -maxdepth 1 -name "CLAUDE.md" | head -1)
  if [ -n "$CLAUDE_MD" ] && grep -q "^## Constitution" "$CLAUDE_MD"; then
    CONSTITUTION="$CLAUDE_MD"  # Constitution is inline
  fi
fi
GOALS=$(find . -maxdepth 3 -name "GOALS.md" 2>/dev/null | head -1)
```

- **If constitution found:** Inject as preamble into ALL context bundles.
- **If GOALS.md exists:** Inject into GPT context (quantitative alignment check) and Gemini context (strategic coherence).
- **If neither exists:** Proceed anyway -- cross-model review still has value without constitutional grounding.



# hooks/generate-overview.sh (lines 180-320)

  temp_prompt=$(mktemp /tmp/overview-prompt-$$-${type}-XXXXXX)
  dispatch_profile=$(resolve_overview_profile) || return 1

  # Step 1: Extract content with repomix (--stdout avoids clipboard races)
  local include_pattern=""
  IFS=',' read -ra DIR_ARRAY <<< "$dirs"
  for d in "${DIR_ARRAY[@]}"; do
    d=$(echo "$d" | xargs)  # trim
    if [[ -n "$include_pattern" ]]; then
      include_pattern="${include_pattern},${d}**"
    else
      include_pattern="${d}**"
    fi
  done

  local repomix_args=(--stdout --include "$include_pattern")
  # Some projects blanket-gitignore .claude/ — opt in via OVERVIEW_NO_GITIGNORE=true
  if [[ "${OVERVIEW_NO_GITIGNORE:-}" == "true" ]]; then
    repomix_args+=(--no-gitignore)
  fi
  if [[ -n "$OVERVIEW_EXCLUDE" ]]; then
    repomix_args+=(--ignore "$OVERVIEW_EXCLUDE")
  fi

  # Step 2: Build prompt (instructions + repomix output)
  {
    echo '<instructions>'
    cat "$prompt_file"
    echo '</instructions>'
    echo ''
    echo '<codebase>'
    repomix "${repomix_args[@]}" 2>/dev/null
    echo '</codebase>'
  } > "$temp_prompt"

  # Step 3: Token estimate
  local prompt_size prompt_tokens
  prompt_size=$(wc -c < "$temp_prompt")
  prompt_tokens=$((prompt_size / 4))

  echo "[$type] Generating (~${prompt_tokens} tokens, profile: $dispatch_profile)..."

  # Step 4: Check token estimate against model limits
  local token_limit
  token_limit=$(profile_token_limit "$dispatch_profile")
  if [[ $prompt_tokens -gt $token_limit ]]; then
    echo "[$type] ERROR: prompt (~${prompt_tokens} tokens) exceeds safe limit (${token_limit}) for $dispatch_profile. Tighten OVERVIEW_EXCLUDE or dirs." >&2
    rm -f "$temp_prompt"
    return 1
  fi

  # Step 5: Generate via shared dispatch (atomic write — temp file, mv on success)
  local dispatch_meta dispatch_error llm_output dispatch_exit resolved_model
  dispatch_meta=$(mktemp /tmp/overview-dispatch-meta-XXXXXX)
  dispatch_error=$(mktemp /tmp/overview-dispatch-error-XXXXXX)
  llm_output=$(mktemp "${output_dir}/.overview-tmp-${type}-XXXXXX")

  # Disable errexit to capture exit code (set -e would skip cleanup on failure)
  set +e
  uv run --project "$SKILLS_ROOT" python3 "$SKILLS_ROOT/scripts/llm-dispatch.py" \
    --profile "$dispatch_profile" \
    --context "$temp_prompt" \
    --prompt "Write the requested codebase overview in markdown." \
    --output "$llm_output" \
    --meta "$dispatch_meta" \
    --error-output "$dispatch_error" \
    >/dev/null
  dispatch_exit=$?
  set -e

  # Cleanup prompt (no longer needed)
  rm -f "$temp_prompt"

  # Check for failure: non-zero exit or empty output
  if [[ $dispatch_exit -ne 0 ]] || [[ ! -s "$llm_output" ]]; then
    echo "[$type] ERROR: dispatch failed (exit=$dispatch_exit)." >&2
    [[ -f "$dispatch_error" ]] && cat "$dispatch_error" >&2
    [[ -f "$dispatch_meta" ]] && cat "$dispatch_meta" >&2
    rm -f "$dispatch_error" "$dispatch_meta" "$llm_output"
    return 1
  fi
  resolved_model=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("resolved_model","unknown"))' "$dispatch_meta" 2>/dev/null || echo "unknown")
  rm -f "$dispatch_error"

  # Step 6: Prepend freshness metadata to temp output, then atomic mv
  local git_sha gen_ts meta_line
  git_sha=$(echo "$COMMIT_HASH" | head -c 7)
  gen_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  meta_line="<!-- Generated: ${gen_ts} | git: ${git_sha} | profile: ${dispatch_profile} | model: ${resolved_model} -->"

  local tmp_final
  tmp_final=$(mktemp "${output_dir}/.overview-final-${type}-XXXXXX")
  { echo "$meta_line"; echo ""; cat "$llm_output"; } > "$tmp_final"
  rm -f "$llm_output" "$dispatch_meta"

  # Atomic move — old overview preserved until this succeeds
  mv "$tmp_final" "$output_file"

  # Step 7: Write per-type success marker
  echo "$COMMIT_HASH" > "$PROJECT_ROOT/.claude/overview-marker-${type}"

  echo "[$type] Done → $output_file (marker: ${COMMIT_HASH:0:7})"
}

# --- Main ---
if ! $DRY_RUN; then
  check_deps
fi

if $AUTO; then
  # Generate types with capped concurrency (avoid Gemini CLI rate limits)
  # For cross-project refresh, prefer generate-overview-batch.sh (Batch API, 50% discount)
  MAX_CONCURRENT=2
  IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"
  active_pids=()
  active_names=()
  failures=0

  for t in "${TYPES[@]}"; do
    t=$(echo "$t" | xargs)
    # Skip types whose per-type marker already matches target commit
    marker_file="$PROJECT_ROOT/.claude/overview-marker-${t}"
    if [[ -f "$marker_file" ]] && [[ "$(cat "$marker_file" 2>/dev/null)" == "$COMMIT_HASH" ]]; then
      echo "[$t] Already current (marker matches ${COMMIT_HASH:0:7}), skipping"
      continue
    fi
    generate_one "$t" &
    active_pids+=($!)
    active_names+=("$t")
    if [ "${#active_pids[@]}" -ge "$MAX_CONCURRENT" ]; then
      pid="${active_pids[0]}"
      name="${active_names[0]}"
      if ! wait "$pid"; then
        echo "FAILED: $name" >&2
        ((failures++))
      fi
      active_pids=("${active_pids[@]:1}")
      active_names=("${active_names[@]:1}")
    fi
  done



# hooks/generate-overview-batch.sh (lines 1-220)

#!/usr/bin/env bash
# generate-overview-batch.sh — Batch all project overviews into one Gemini Batch API job
#
# Runs repomix for each project×type, builds JSONL, submits via llmx batch.
# 50% cost discount vs individual calls. Results distributed to each project's output dir.
#
# Usage:
#   generate-overview-batch.sh                    # Submit and wait
#   generate-overview-batch.sh --submit-only      # Submit, print job ID, exit
#   generate-overview-batch.sh --get JOB_NAME     # Fetch results from prior job
#   generate-overview-batch.sh --dry-run          # Show what would be submitted

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_DIR="$SCRIPT_DIR/overview-prompts"
PROJECTS_DIR="$HOME/Projects"

# Projects with overview.conf
PROJECTS=(meta intel selve genomics)

# Temp workspace
WORK_DIR=$(mktemp -d /tmp/overview-batch-XXXXXX)
JSONL_FILE="$WORK_DIR/batch-input.jsonl"
MANIFEST="$WORK_DIR/manifest.json"

# --- Parse arguments ---
MODE="submit-wait"  # submit-wait | submit-only | get | dry-run
JOB_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --submit-only) MODE="submit-only"; shift ;;
    --get) MODE="get"; JOB_NAME="$2"; shift 2 ;;
    --dry-run) MODE="dry-run"; shift ;;
    -h|--help)
      echo "Usage: generate-overview-batch.sh [--submit-only|--get JOB_NAME|--dry-run]"
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# --- Parse a project's overview.conf ---
parse_conf() {
  local conf_file="$1"
  # Reset to defaults
  OVERVIEW_TYPES="source"
  OVERVIEW_MODEL="gemini-3-flash-preview"
  OVERVIEW_OUTPUT_DIR=".claude/overviews"
  OVERVIEW_PROMPT_DIR="$PROMPT_DIR"
  OVERVIEW_EXCLUDE=""
  OVERVIEW_NO_GITIGNORE=""
  OVERVIEW_SOURCE_DIRS=""
  OVERVIEW_TOOLING_DIRS=""

  if [[ -f "$conf_file" ]]; then
    while IFS='=' read -r key value; do
      [[ "$key" =~ ^[[:space:]]*# ]] && continue
      [[ -z "$key" ]] && continue
      key=$(echo "$key" | xargs)
      value=$(echo "$value" | xargs | sed 's/^"//;s/"$//')
      # Only set known variables
      case "$key" in
        OVERVIEW_TYPES|OVERVIEW_MODEL|OVERVIEW_OUTPUT_DIR|OVERVIEW_PROMPT_DIR|\
        OVERVIEW_EXCLUDE|OVERVIEW_NO_GITIGNORE|OVERVIEW_SOURCE_DIRS|OVERVIEW_TOOLING_DIRS)
          eval "$key=\"$value\""
          ;;
      esac
    done < "$conf_file"
  fi
}

# --- Run repomix and build prompt for one project×type ---
build_prompt() {
  local project="$1"
  local type="$2"
  local project_root="$PROJECTS_DIR/$project"

  # Read config
  parse_conf "$project_root/.claude/overview.conf"

  # Get type-specific dirs
  local dirs_var="OVERVIEW_$(echo "$type" | tr '[:lower:]' '[:upper:]')_DIRS"
  local dirs="${!dirs_var:-}"
  if [[ -z "$dirs" ]]; then
    echo "SKIP: $project/$type — no dirs configured ($dirs_var)" >&2
    return 1
  fi

  # Resolve prompt file
  local prompt_file
  if [[ "$OVERVIEW_PROMPT_DIR" = /* ]]; then
    prompt_file="$OVERVIEW_PROMPT_DIR/${type}.md"
  else
    prompt_file="$project_root/$OVERVIEW_PROMPT_DIR/${type}.md"
  fi
  if [[ ! -f "$prompt_file" ]]; then
    echo "SKIP: $project/$type — prompt not found: $prompt_file" >&2
    return 1
  fi

  # Build repomix include pattern
  local include_pattern=""
  IFS=',' read -ra DIR_ARRAY <<< "$dirs"
  for d in "${DIR_ARRAY[@]}"; do
    d=$(echo "$d" | xargs)
    if [[ -n "$include_pattern" ]]; then
      include_pattern="${include_pattern},${d}**"
    else
      include_pattern="${d}**"
    fi
  done

  local repomix_args=(--stdout --include "$include_pattern")
  if [[ "${OVERVIEW_NO_GITIGNORE:-}" == "true" ]]; then
    repomix_args+=(--no-gitignore)
  fi
  if [[ -n "$OVERVIEW_EXCLUDE" ]]; then
    repomix_args+=(--ignore "$OVERVIEW_EXCLUDE")
  fi

  # Run repomix from project root
  local temp_prompt="$WORK_DIR/${project}-${type}-prompt.txt"
  {
    echo '<instructions>'
    cat "$prompt_file"
    echo '</instructions>'
    echo ''
    echo '<codebase>'
    (cd "$project_root" && repomix "${repomix_args[@]}" 2>/dev/null)
    echo '</codebase>'
  } > "$temp_prompt"

  local prompt_size=$(wc -c < "$temp_prompt")
  local prompt_tokens=$((prompt_size / 4))
  echo "  $project/$type: ~${prompt_tokens} tokens" >&2

  echo "$temp_prompt"
}

# --- Build JSONL from all project×type combinations ---
build_jsonl() {
  echo "Building prompts..." >&2

  # Track manifest for result distribution: array of {key, project, type, output_path}
  echo "[" > "$MANIFEST"
  local first=true
  local count=0

  for project in "${PROJECTS[@]}"; do
    local project_root="$PROJECTS_DIR/$project"
    [[ -f "$project_root/.claude/overview.conf" ]] || continue

    parse_conf "$project_root/.claude/overview.conf"
    IFS=',' read -ra TYPES <<< "$OVERVIEW_TYPES"

    for type in "${TYPES[@]}"; do
      type=$(echo "$type" | xargs)
      local key="${project}-${type}"

      local prompt_file
      prompt_file=$(build_prompt "$project" "$type" 2>/dev/null) || continue

      # Resolve output path
      local output_dir
      if [[ "$OVERVIEW_OUTPUT_DIR" = /* ]]; then
        output_dir="$OVERVIEW_OUTPUT_DIR"
      else
        output_dir="$project_root/$OVERVIEW_OUTPUT_DIR"
      fi
      local output_path="$output_dir/${type}-overview.md"

      # Write JSONL line
      python3 -c "
import json, sys
obj = {
    'key': sys.argv[1],
    'prompt': open(sys.argv[2]).read(),
}
print(json.dumps(obj))
" "$key" "$prompt_file" >> "$JSONL_FILE"

      # Write manifest entry
      if ! $first; then echo "," >> "$MANIFEST"; fi
      first=false
      python3 -c "
import json, sys
entry = {'key': sys.argv[1], 'project': sys.argv[2], 'type': sys.argv[3], 'output': sys.argv[4]}
print(json.dumps(entry))
" "$key" "$project" "$type" "$output_path" >> "$MANIFEST"

      count=$((count + 1))
    done
  done

  echo "]" >> "$MANIFEST"
  echo "Built $count requests → $JSONL_FILE" >&2
  echo "$count"
}

# --- Distribute results to project output dirs ---
distribute_results() {
  local results_file="$1"

  # Load manifest
  local manifest_json
  manifest_json=$(cat "$MANIFEST")

  # Parse results JSONL and match to manifest by key
  python3 - "$results_file" "$MANIFEST" <<'PYEOF'
import json, sys, os

results_file = sys.argv[1]
manifest_file = sys.argv[2]

# Load manifest
with open(manifest_file) as f:
    manifest = json.load(f)
manifest_by_key = {m["key"]: m for m in manifest}


