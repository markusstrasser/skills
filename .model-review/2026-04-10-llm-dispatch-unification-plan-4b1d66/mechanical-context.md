# DEVELOPMENT CONTEXT
All code, plans, and features in this project are developed by AI agents, not human developers. Dev creation time is effectively zero. Therefore:
- NEVER recommend trading stability, composability, or robustness for dev time savings
- NEVER recommend simpler/hacky approaches because they're 'faster to implement'
- Cost-benefit analysis should filter on: maintenance burden, supervision cost, complexity budget, blast radius — not creation effort
- 'Effort to implement' is not a meaningful cost dimension — only ongoing drag matters

# Review Context: LLM Dispatch Unification Plan

## Scope
- Target users: agent infrastructure maintainers and agents using skills/hooks
- Scale: currently ~18 active skills and ~33 hooks; designed for repeated cross-project reuse
- Rate of change: high; dispatch patterns still evolving weekly

## Project Identity
This repo defines reusable skills and hooks for Claude/Codex agent workflows.
It is not an app product. Its main job is to provide reliable execution patterns,
prompts, hooks, and helper scripts that other repos consume.

## Review Target
Path: `.claude/plans/2026-04-10-llm-dispatch-unification-plan.md`

---

## Plan
# LLM Dispatch Unification Plan

Date: 2026-04-10
Repo: `~/Projects/skills`
Status: proposed
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

## Why This Is The Right Boundary

The current evidence already converges on this:

- The guard blocks `llmx chat` CLI because agent-context failures were recurring, not theoretical.
- The review stack already escaped the CLI path and uses the Python API.
- The llmx repo itself has repeatedly patched CLI edge cases: stdin hangs, multi-file `-f`, shell redirect confusion, transport surprises, deprecated model names.
- Agents are bad at shell transport details and good at calling one stable local interface.

So the correct abstraction is not "teach every agent llmx better." It is "stop requiring most agents to know llmx transport rules at all."

## Target Architecture

### 1. Shared dispatch module

Add one shared helper module under this repo, for example:

- `scripts/llm_dispatch.py`

Responsibilities:

- import/bootstrap `llmx.api.chat`
- resolve a named dispatch profile into provider/model/timeout/schema/search defaults
- load context from a single file path or provided string
- execute one request
- write deterministic artifacts
- return typed metadata and typed error outcomes

This module owns llmx bootstrap quirks. Individual skills do not repeat them.

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
- `search_grounded`
  - default: provider/model chosen for search-backed answer
- `cheap_tick`
  - low-cost synthesis for maintenance/research cycle ticks

Profiles are the contract. Underlying models can change centrally.

### 3. Artifact-first results

Every dispatch writes:

- markdown/text output
- `meta.json`
- optional `error.json`

`meta.json` must include:

- requested profile
- resolved provider
- resolved model
- `api_only`
- timeout
- schema used or null
- success/failure
- failure type
- latency
- output path

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
- `dispatch_error`

Never collapse these into generic `ERROR`.

### 5. Single-context rule

The shared helper accepts:

- `context_path`, or
- `context_text`

But the caller presents one assembled context unit.

The helper does not support agent-level multi-`-f` orchestration as a public contract.

### 6. Human vs agent boundary

Two explicit layers:

- **Agent path:** shared Python dispatch helper only
- **Human terminal path:** raw `llmx` CLI allowed for ad hoc work, debugging, subcommands, and manual probing

This preserves useful CLI access without making it the automation substrate.

## What Changes

### A. Add the shared helper

Create:

- `scripts/llm_dispatch.py`

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
    schema: dict | None = None,
    api_only: bool = True,
    extra_kwargs: dict | None = None,
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
- update warnings to point to the shared helper, not inline bootstrap snippets
- keep low-level llmx CLI warnings for maintainers/debuggers

## Migration Plan

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

- `scripts/llm_dispatch.py`
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

1. Should the shared helper live in `scripts/` or in a dedicated `shared/` package path?
2. Should artifact metadata be plain JSON dicts or a small typed Pydantic model?
3. Should hooks call the helper directly or via tiny task-specific wrapper scripts?
4. Do we want one unified helper for all llmx subcommands later, or only for chat-style dispatch?

## Recommended First Move

Do not start by rewriting `llmx-guide`.

Start by building `scripts/llm_dispatch.py` and migrating `review/scripts/model-review.py` onto it. That proves the interface on the highest-value existing Python-API path. After that, kill the CLI-heavy paths one by one.

---

## Relevant Current Files

### hooks/pretool-llmx-guard.sh excerpt
# 0. BLOCK llmx chat CLI — use Python API instead
# The CLI has 5 known failure modes in agent context (multi-file drops, 0-byte -o,
# rate limit loops, stdin EOF, pipe masking). The Python API bypasses all of them.
if echo "$CMD" | grep -qE 'llmx\s+chat'; then
  echo "[llmx-guard] BLOCKED: Do not use 'llmx chat' CLI. Use the Python API instead:" >&2
  echo "  from llmx.api import chat as llmx_chat" >&2
  echo "  r = llmx_chat(prompt=..., provider='google', model='gemini-3.1-pro-preview', api_only=True, timeout=300)" >&2
  echo "  Bootstrap: sys.path.insert(0, glob.glob(str(Path.home() / '.local/share/uv/tools/llmx/lib/python*/site-packages'))[0])" >&2
  ~/Projects/skills/hooks/hook-trigger-log.sh "llmx-chat-blocked" "block" "$(echo "$CMD" | head -c 200)" 2>/dev/null || true
  exit 2
fi

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

### observe/SKILL.md excerpt
Send full-fidelity transcript + coverage digest + operational context to Gemini 3.1 Pro. Full prompt in `references/gemini-dispatch-prompt.md`.

Dispatch via llmx Python API (not CLI subprocess). Write the dispatch as a short inline script:

```bash
uv run python3 << 'PYEOF'
import sys, glob
from pathlib import Path

# Bootstrap llmx from uv tool venv
_site = glob.glob(str(Path.home() / ".local/share/uv/tools/llmx/lib/python*/site-packages"))
if _site: sys.path.insert(0, _site[0])
sys.path.insert(0, str(Path.home() / "Projects/llmx"))
from llmx.api import chat as llmx_chat

artifact_dir = Path("$HOME/Projects/meta/artifacts/observe").expanduser()
context = (artifact_dir / "input.md").read_text()
coverage = (artifact_dir / "coverage-digest.txt").read_text()
prompt = Path("$CLAUDE_SKILL_DIR/references/gemini-dispatch-prompt.md").read_text()

response = llmx_chat(
    prompt=context + "\n\n" + coverage + "\n\n" + prompt,
    provider="google",
    model="gemini-3.1-pro-preview",
    temperature=1.0,
    timeout=300,
)
(artifact_dir / "gemini-output.md").write_text(response.content)
print(f"✓ Gemini output: {len(response.content)} chars, {response.latency:.1f}s")
PYEOF
```

Substitute `$HOME` and `$CLAUDE_SKILL_DIR` with actual paths before running.

### Step 3: Stage Findings

### review/scripts/model-review.py excerpt
    provider: str,
    model: str,
    context_path: Path,
    prompt: str,
    output_path: Path,
    schema: dict | None = None,
    **kwargs,
) -> dict:
    """Call llmx Python API, write output to file, return result dict."""
    context = context_path.read_text()
    full_prompt = context + "\n\n---\n\n" + prompt
    # Reasoning models (GPT-5.x, Gemini 3.x) require temperature=1.0
    temperature = 1.0 if any(m in model for m in ("gpt-5", "gemini-3")) else 0.7
    api_kwargs: dict = {**kwargs}
    if schema:
        # OpenAI strict mode requires additionalProperties:false; Google rejects it
        if provider == "openai":
            api_kwargs["response_format"] = _add_additional_properties(schema)
        else:
            api_kwargs["response_format"] = _strip_additional_properties(schema)
    try:
        response = llmx_chat(
            prompt=full_prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            api_only=True,
            **api_kwargs,
        )
        output_path.write_text(response.content)
        return {
            "exit_code": 0,
            "size": output_path.stat().st_size,
            "latency": response.latency,
            "error": None,
        }
    except Exception as e:
        error_msg = str(e)[:500]
        print(f"warning: llmx call failed ({model}): {error_msg}", file=sys.stderr)
        return {
            "exit_code": 1,
            "size": 0,
            "latency": 0,
            "error": error_msg,
        }


def axis_output_failed(info: object) -> bool:
    """Return True when an axis failed to produce a usable review artifact."""
    if not isinstance(info, dict):
        return False
    return int(info.get("exit_code", 0)) != 0 or int(info.get("size", 0)) == 0


def collect_dispatch_failures(
    dispatch_result: dict,
    ctx_files: dict[str, Path],
) -> list[dict[str, object]]:
    """Summarize failed axes for machine-readable failure artifacts."""
    failures: list[dict[str, object]] = []
    skip_keys = {"review_dir", "axes", "queries", "elapsed_seconds"}

### research-ops/SKILL.md excerpt
```bash
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
```

**If rate-limited (CLAUDE_PROCS >= 6):** Route LLM-heavy phases (discover, gap-analyze, plan) through llmx instead of Claude subagents:
- Use `llmx chat -m gemini-3-flash-preview` for discover/gap-analyze (search + synthesis — Flash is free via CLI)
- Use `model-review.py` for review (already routes through llmx)
- Execute and verify phases use tools, not LLM reasoning — run inline regardless
- Write `[rate-limited: used llmx]` tag in CYCLE.md log entries for tracking

**If not rate-limited:** Normal operation (Claude subagents preferred).

## Each Tick

If "NO STATE CHANGE" -> one-line noop, stop.

Otherwise, pick the highest-priority phase and run it. **Chain phases** if confident — don't wait for the next tick when the next phase has no blockers. Stop chaining when: rate-limited, context is heavy (>60% used), or the next phase needs external data you don't have yet.

### Phase Priority (first match wins)

1. **Recent execution without verification** -> run verify (always verify before executing more)
2. **Items in queue** (CYCLE.md `## Queue`) -> run execute. The queue IS the approval — items land there via human steering or gap-analyze. No `[x] APPROVE` gate needed.
3. **Active plan not yet reviewed** -> run review (probe claims + cross-model via `model-review.py`)
4. **Gaps exist without plan** -> run plan phase (write plan for top gap)
5. **Discoveries exist without gap analysis** -> run gap-analyze
6. **Verification done without improve** -> run improve (includes retro + archival)
7. **Nothing pending** -> run discover (includes brainstorm if discover returns empty)

### Running a Phase

**Route by task type, not line count:**
- Docstring, config, research_only field changes -> **inline** (fast, reliable)
- Logic changes, even 1-line -> **subagent** (fresh context for reasoning about consequences)
- If subagent returns empty (no edit), retry inline once

**Subagent dispatch (normal mode):**
```
Agent(
  prompt="[phase prompt with project context]",
  subagent_type="general-purpose",
  description="research-cycle: [phase]",
  mode="bypassPermissions"
)

### research-ops/scripts/run-cycle.sh excerpt
#!/usr/bin/env bash
# Rate-limit-aware research cycle runner.
# If Claude is rate-limited (>=6 processes), runs via llmx (Gemini Flash)
# instead of loading the skill into a Claude session.
#
# Usage: run-cycle.sh [project_dir]
#   Or from Claude Code: ! ~/Projects/skills/research-cycle/scripts/run-cycle.sh

set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
CYCLE_FILE="$PROJECT_DIR/CYCLE.md"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

MAX_PROCS="${RATE_LIMIT_THRESHOLD:-6}"
CLAUDE_PROCS=$(pgrep claude 2>/dev/null | wc -l | tr -d ' ')
echo "Claude processes: $CLAUDE_PROCS (threshold: $MAX_PROCS)"

if [ "$CLAUDE_PROCS" -ge "$MAX_PROCS" ]; then
    echo "Rate-limited mode: routing through Gemini Flash via llmx"

    # Gather state (same script the skill uses)
    STATE=$("$SKILL_DIR/scripts/gather-cycle-state.sh" "$PROJECT_DIR" 2>&1 | head -80)

    if echo "$STATE" | grep -q "NO STATE CHANGE"; then
        echo "No state change — noop."
        exit 0
    fi

    # Build prompt from CYCLE.md + state
    CYCLE_CONTENT=""
    if [ -f "$CYCLE_FILE" ]; then
        CYCLE_CONTENT=$(head -200 "$CYCLE_FILE")
    fi

    cat > /tmp/cycle-llmx-prompt.md << PROMPT_EOF
# Research Cycle Tick (rate-limited mode via Gemini Flash)

Project: $PROJECT_DIR
Project name: $(basename "$PROJECT_DIR")

## Current State
$STATE

## CYCLE.md (current)
$CYCLE_CONTENT

## Instructions
You are running one tick of the research cycle. Pick the highest-priority phase:
1. Recent execution without verification → verify
2. Approved items in queue → execute (skip — can't execute code via llmx)
3. Active plan not yet reviewed → review
4. Gaps without plan → plan
5. Discoveries without gap analysis → gap-analyze
6. Verification done without improve → improve
7. Nothing pending → discover

For discover: search for new developments relevant to this project.
For gap-analyze: analyze discoveries and write gaps.
For plan/review: analyze and write recommendations.

Output your findings as markdown that should be appended to CYCLE.md.
Start with "## [Phase]: [description]" and include a date.
Be concise — this will be appended to a file.
PROMPT_EOF

    OUTPUT=$(llmx chat -m gemini-3-flash-preview \
        -f /tmp/cycle-llmx-prompt.md \
        --timeout 120 \
        "Run one research cycle tick. Output markdown for CYCLE.md." 2>/dev/null)

    if [ -n "$OUTPUT" ]; then
        echo "" >> "$CYCLE_FILE"
        echo "$OUTPUT" >> "$CYCLE_FILE"
        echo "---"
        echo "Appended to CYCLE.md via Gemini Flash (rate-limited mode)"
        echo "$OUTPUT" | head -5
    else
        echo "llmx returned empty output — skipping this tick"
    fi
else
    echo "Normal mode: running via Claude skill"
    echo "Use /research cycle in your Claude session instead."
    echo "(This script is for rate-limited fallback only)"
fi

### hooks/generate-overview.sh excerpt
  # Step 5: Generate via llmx (atomic write — temp file, mv on success)
  local llmx_stderr llmx_output
  llmx_stderr=$(mktemp /tmp/overview-llmx-stderr-XXXXXX)
  llmx_output=$(mktemp "${output_dir}/.overview-tmp-${type}-XXXXXX")

  # Disable errexit to capture exit code (set -e would skip cleanup on failure)
  set +e
  cat "$temp_prompt" | timeout 300 llmx chat -m "$OVERVIEW_MODEL" 2>"$llmx_stderr" > "$llmx_output"
  local llmx_exit=$?
  set -e

  # Cleanup prompt (no longer needed)
  rm -f "$temp_prompt"

  # Check for failure: non-zero exit or empty output
  if [[ $llmx_exit -ne 0 ]] || [[ ! -s "$llmx_output" ]]; then
    echo "[$type] ERROR: llmx failed (exit=$llmx_exit). stderr:" >&2
    cat "$llmx_stderr" >&2
    rm -f "$llmx_stderr" "$llmx_output"

### brainstorm/references/llmx-dispatch.md excerpt
<!-- Reference file for brainstorm skill. Loaded on demand. -->
# llmx Dispatch Templates

> **DISPATCH VIA PYTHON API, NOT CLI.** Use `from llmx.api import chat as llmx_chat` and call
> `llmx_chat(prompt=..., provider=..., model=..., timeout=...)`. Read context files with
> `Path(...).read_text()` and write outputs with `Path(...).write_text(response.content)`.
> The CLI commands below are template references for the prompt content — adapt them to Python API calls.
> Bootstrap: `sys.path.insert(0, glob.glob(str(Path.home() / ".local/share/uv/tools/llmx/lib/python*/site-packages"))[0])`

All templates assume `$BRAINSTORM_DIR`, `$N_IDEAS`, `$CONSTITUTION`, and `$TOPIC` are set.
Date injection: `$(date +%Y-%m-%d)` in every system prompt.

## Initial Generation (Step 2)

**With llmx (and not `--no-llmx`):** Dispatch to an external model for parallel volume while you also generate your own set.

```bash
llmx chat -m gemini-3.1-pro-preview \
  ${CONSTITUTION:+-f "$BRAINSTORM_DIR/context.md"} \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/external-generation.md" "
<system>
Generate approaches to the design space below. Maximize breadth — $N_IDEAS genuinely different approaches, not variations on a theme. No feasibility filtering yet. It is $(date +%Y-%m-%d).
</system>

[Design space + constraints + user-provided seeds if any]

For each approach: one paragraph on the mechanism and why it differs from the others."
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

### llmx-guide/SKILL.md excerpt
---
name: llmx-guide
description: Critical gotchas when calling llmx from Python or Bash. Non-obvious bugs and incompatibilities. Use when writing code that calls llmx, debugging llmx failures, or choosing llmx model/provider options.
user-invocable: true
argument-hint: '[model name or issue description]'
effort: medium
---

# llmx Quick Reference

> Detail files in `references/`: [models.md](references/models.md) | [error-codes.md](references/error-codes.md) | [transport-routing.md](references/transport-routing.md) | [codex-dispatch.md](references/codex-dispatch.md) | [subcommands.md](references/subcommands.md)

## Before You Call llmx — Checklist

1. **Model name correct?** Hyphens not dots (`claude-sonnet-4-6` not `claude-sonnet-4.6`)
2. **Timeout set?** Reasoning models need `--timeout 600` or `--stream`. Max allowed: **900s**. If dispatching from an agent shell, set the outer shell timeout above this (for Claude Code, use at least `1200000` ms).
3. **Using `shell=True`?** Don't — parentheses in prompts break it. Use list args + `input=`
4. **Using `-o FILE`?** Never use `> file` shell redirects — they buffer until exit
5. **No provider prefixes needed.** `gemini-3.1-pro-preview` not `gemini/gemini-3.1-pro-preview`.
6. **Know the transport triggers:** `google` prefers `gemini` CLI (free). Gemini falls back to API for: `--schema`, `--search`, `--stream`, `--max-tokens`. Codex CLI also falls back for `--search` and `--stream`, but can keep `--schema` via `codex exec --output-schema`. GPT goes direct to API unless you explicitly force `-p codex-cli`.
7. **Hangs in agent context?** Claude Code's Bash tool pipes stdin without EOF. Fixed in current llmx (skips stdin when prompt provided).
8. **Prompt is positional, context is `-f`.** `llmx "analyze this" -f context.md` — prompt as first positional arg, context files as `-f`. Two `-f` flags with no positional = no prompt = model invents a task from the context. (Evidence: 2026-04-05 — Gemini received two `-f` files, hallucinated a script implementation instead of analysis.)
9. **For critical reviews, use one combined context file.** Multi-file `-f` has recurring failure modes with Gemini/CLI transport, including silently dropping earlier files. Pre-concatenate first, but preserve file boundaries in the combined file.

## When llmx Fails — Diagnose, Don't Downgrade

**Never swap to a weaker model as a "fix."** The problem is the dispatch, not the model.

1. Check exit code: 3=rate-limit, 4=timeout, 5=model-error, 6=billing-exhausted (permanent, don't retry)
2. Check stderr JSON diagnostics
3. Check for transport switch / truncation warnings
4. Re-run with `--debug` on a small prompt
5. Common fixes: increase `--timeout`, add `--stream`, reduce context, check API key
6. **When transport matters, probe it.** Run one tiny `--debug` smoke test before assuming CLI vs API routing from docs or memory.

See [error-codes.md](references/error-codes.md) for full exit code table and Python patterns.

## The Five Footguns

### 1. Gemini CLI Transport — Free Tier

No `--stream` needed for Gemini. Without it, llmx routes through CLI (free tier). Add `--stream` only if CLI hits rate limits (forces paid API fallback).

```bash
# FREE — routes through Gemini CLI:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 "Review this"

# FORCES API (costs money) — only use if CLI rate-limited:
llmx chat -m gemini-3.1-pro-preview -f context.md --timeout 300 --stream "Review this"
```

**What still forces API:** `--max-tokens` (CLI caps at 8K), `--schema`, `--search`, `--stream`.

### 1.5. Multi-File `-f` Is Not Reliable Enough For Critical Review Flows

If the task is high-stakes or review-oriented, do this:

```bash
awk 'FNR==1{print "\n# File: " FILENAME "\n"}1' overview.md diff.md touched-files.md > combined-context.md
llmx chat -m gemini-3.1-pro-preview -f combined-context.md --timeout 300 "Review this"
```

Do **not** assume this is equivalent:

```bash
llmx chat -m gemini-3.1-pro-preview -f overview.md -f diff.md -f touched-files.md --timeout 300 "Review this"
```

Known failure mode: earlier `-f` files may be silently dropped or incompletely
forwarded. This is acceptable for casual exploration, not for plan-close or
adversarial review.

### 2. GPT-5.x Timeouts

GPT-5.4 with reasoning burns time BEFORE producing output. Non-streaming holds the connection idle during reasoning. Default timeout: 300s. Max: **900s** (hard cap). GPT-5.4 xhigh on domain-heavy prompts can exceed 900s; for those, chunk the task, stream, or switch to an async/batch path if available. Do not punt operational work to a GUI tool.

**`max_completion_tokens` includes reasoning tokens.** If you set `--max-tokens 4096` on GPT-5.4 with reasoning, the model may exhaust the budget on thinking. Use 16K+ for reasoning models.

### 3. Output Capture — Use `-o FILE`, Never `> file`

```bash
# CORRECT — llmx writes the output file itself:
llmx -m gpt-5.4 -f context.md --timeout 600 -o output.md "query"

# BROKEN — 0 bytes until exit:
llmx -m gpt-5.4 "query" > output.md
```

`-o` does not imply `--stream`. Current llmx preserves the requested transport and writes the returned result itself when needed. If the file is still 0 bytes, llmx emits `[llmx:WARN]` to stderr.

For GPT specifically:

- default `llmx -m gpt-5.4` routes to the OpenAI API in current llmx
- `-o` preserves that transport; it does not force a transport switch
- if you explicitly use `-p codex-cli`, diagnose any failure from stderr and output size, not shell exit alone

If you need to verify the actual route, run:

```bash
llmx chat -p codex-cli -m gpt-5.4 --debug -o /tmp/probe.txt "Reply with exactly OK."
```

Then inspect the debug line for `transport`.

### 3.5. Shell Pipelines Can Hide llmx Failures

These are bad diagnostic patterns:

```bash
llmx chat -m gpt-5.4 "query" 2>/dev/null | head -200
llmx chat -m gpt-5.4 "query" | sed -n '1,80p'
```

Why:

- `2>/dev/null` discards llmx's real diagnostics
- without `set -o pipefail`, the shell returns the last consumer's exit code (`head`, `sed`), not llmx's
- an empty llmx response can look like success if the downstream command exits 0

Safer pattern:
