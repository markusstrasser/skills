<!-- Reference file for observe skill (audit + harness modes). Loaded on demand. -->
# `audit` / `harness` pipeline

Feed the codebase to two model families in parallel, get structured findings, triage with a
disposition table, execute with per-finding verification and rollback. **Each verified change gets
its own git commit.**

Follow the phases and tiers below. [Analysis safeguards](analysis-safeguards.md) apply before triage or implementation.

**Why dual-model:** cross-family review catches 31pp more errors than single-model (FINCH-ZK).
Same-model review is a martingale. Gemini brings pattern detection + 1M context; GPT brings formal
reasoning + type-system depth.

**Triage evidence requirements** — a disposition without evidence is a guess. DEFER with "no
incidents" → must `grep -i KEYWORD CLAUDE.md` and show zero matches. REJECT with "already exists" →
must cite the specific `file:line` or test name. DEFER at all → grep for callers first; "needs canary
validation" for zero-caller dead code is overcautious.

**Finding categories, priority order:** BROKEN_REFERENCE > ERROR_SWALLOWED > IMPORT_ISSUE >
DUPLICATION > PATTERN_INCONSISTENCY > MISSING_SHARED_UTIL > DEAD_CODE > NAMING_INCONSISTENCY >
HARDCODED > COUPLING.

**Scorecard:** finding correctness ≥60% verified (fail <40%) · apply success ≥80% retained (fail
<60%) · zero unreviewed changes (any violation fails) · no test regression · static errors after ≤ before.

## Pipeline

`harness` runs the same phases with [harness prompts](model-prompts-harness.md) at phase 2.

| Phase | What | Reference |
|-------|------|-----------|
| 0 | Pre-flight: env, backlog gate, language detect, baseline | [preflight-scripts.md](preflight-scripts.md) |
| 1 | Dump codebase (diff-aware or full) | [codebase-dump.md](codebase-dump.md) |
| 2 | Parallel Gemini + GPT analysis | [model-prompts-standard.md](model-prompts-standard.md) |
| 3 | Cross-validation (`--thorough` only) | [cross-validation.md](cross-validation.md) |
| 4 | Extract, auto-validate, triage | [triage-procedures.md](triage-procedures.md) |
| 5 | Execute with per-finding verify + rollback | [execution-loop.md](execution-loop.md) |
| 6 | Report, MAINTAIN.md integration, baseline SHA | [report-template.md](report-template.md) |

**Tiers:** `--quick` = phases 0-2, findings only, ~2 min · default = full, ~15-30 min ·
`--thorough` adds cross-validation, ~30-60 min · `--deferred` re-triages prior deferrals, skipping
phases 1-3 ([deferred-retriage.md](deferred-retriage.md)). Route through the shared dispatch surfaces and the
packet contract in `shared/context_packet.py`; consume `coverage.json` + `findings.json`. **Do not
rebuild provider flags, packet manifests, or raw model recipes here.**

Phase 4 consumes the structured findings artifacts the shared review/dispatch path emits —
parsing rules and the fallbacks when a model returns prose instead of JSON are in
[json-parsing.md](json-parsing.md).

## Harness mode

Architecture-focused deep analysis for agent-developed codebases. Finds **enforcement gaps, not
current bugs** — it prevents future bug *categories*. Same pipeline as `audit` with the prompts in
[model-prompts-harness.md](model-prompts-harness.md).

**Use when:** the codebase is primarily agent-developed (enforcement > convention) · a standard audit
already cleaned the obvious bugs · the goal is "fewer categories of future bugs" · the codebase has
grown past ~50 files with shared modules.

**What it finds that `audit` misses:** Pydantic roundtrips (models immediately `.model_dump()`'d back
to dicts) · open vocabularies (strings that should be StrEnum) · missing Protocols (duck-typed
interfaces with no structural contract) · duplicate definitions (constants/sets defined in N files
instead of imported from one) · `dict[str, Any]` returns from high-traffic functions · missing
import-time checks and runtime invariants.

**Triage differs.** Standard triage asks "is this a real bug?" Harness triage asks: does the
enforcement already exist (models hallucinate missing features at ~40%)? how many callers (grep the
function/type, count importers)? is the "duplicate" intentional variation? what is the injection
point — one function, or N file edits? **Apply threshold:** affects <3 files or prevents <1 known bug
class → DEFER.
