Overall: **strong direction, but the contract is still too loose in a few places to safely make this the repo-wide dispatch spine.** I’d approve the architectural direction, but I would **revise the plan before implementation** to lock down the parts that otherwise re-fragment.

## What the plan gets right

The core decision is correct:

- **one canonical agent dispatch path**
- **Python API only for automation**
- **profiles instead of raw model strings**
- **artifact-first results**
- **demoting `llmx-guide` from primary path to low-level reference**

Given the current repo state, this is the right boundary. The repo should stop asking agents to understand transport quirks at all.

The migration ordering is also mostly right: starting with `review/scripts/model-review.py` is a good proving ground because it already contains the hardest useful bits: schema handling, provider differences, artifact writing, and real operational use.

---

## The main gaps I’d fix before Phase 1

## 1. Profiles need governance, not just names

Right now the plan says “profiles are the contract” and “underlying models can change centrally.” That’s directionally good, but not sufficient for a reusable infra repo.

### Why this matters
If `formal_review` points to one model this week and another next week, downstream behavior can shift silently across many repos. That’s fine **only if the profile contract is explicit** and metadata captures what resolved.

### Add this to the plan
Define profile semantics at three levels:

- **profile name**: stable human-facing handle (`formal_review`)
- **profile intent**: latency/cost/quality/search/schema/reasoning guarantees
- **resolved implementation**: provider/model/default kwargs at runtime

And include in `meta.json`:

- `profile`
- `profile_version` or `profile_fingerprint`
- `resolved_provider`
- `resolved_model`
- `resolved_kwargs`
- `config_source` (default / repo override / env override)

### Also decide override policy now
Because this repo is reused across projects, you need a sanctioned override layer. Otherwise people will bypass profiles and hardcode models again.

Recommended resolution order:

1. built-in repo defaults
2. optional repo-local config override
3. optional env override for emergency/operator control

But keep overrides constrained to **profile mapping**, not arbitrary caller-level provider/model strings.

---

## 2. The artifact contract is underspecified

“markdown/text output + meta.json + optional error.json” is good, but not enough yet.

### Missing pieces that matter operationally

#### Atomicity
`hooks/generate-overview.sh` currently depends on atomic final move behavior. The helper contract should explicitly define whether it:

- writes directly to final paths, or
- writes temp artifacts then atomically renames

Without that, callers will reimplement their own safety logic, and the unification will leak.

#### Stale-output behavior
On failure, what happens if `output_path` already exists from a previous success?

You need a hard rule:
- either remove stale output before dispatch
- or never touch final output until success and always write failure separately

Otherwise callers can mistake old success for current success.

#### Reproducibility / diagnosability
`meta.json` should include more than the currently proposed fields. At minimum add:

- `started_at`, `finished_at`
- `profile`, `profile_version/fingerprint`
- `provider`, `model`
- `timeout`
- `api_only`
- `schema_present`
- `status`
- `error_type`
- `error_message`
- `latency_ms`
- `output_path`
- `context_sha256`
- `prompt_sha256`
- `llmx_version`
- `helper_version`

If the helper assembles context from sources indirectly, also record source provenance somehow.

### Recommendation
Define the artifact layout as a stable contract now, not later.

---

## 3. `scripts/llm_dispatch.py` is probably the wrong place for the core library

This is one of the most important unresolved questions in the plan.

For a repo whose whole job is reusable execution patterns, the dispatch core should not live only as a script-shaped file path.

### Why
You need:

- stable imports from multiple scripts/tests/hooks
- a clean place for types, profiles, schema normalization, error classification
- thin task-specific wrappers without duplicating logic

### Recommendation
Use:

- a **real importable package/module** for the core
- thin wrappers in `scripts/` for shell-facing use

For example:

- `shared/llm_dispatch.py` or `skills_lib/llm_dispatch.py` as core
- `scripts/llm-dispatch` or `scripts/dispatch_once.py` as wrapper

That gives you one implementation and multiple safe entrypoints.

This also helps with the agent UX: skills/hooks can call a stable wrapper command instead of pasting inline Python.

---

## 4. `extra_kwargs` is an architecture leak unless tightly constrained

The plan is right to keep the public surface small, but `extra_kwargs` is where drift will re-enter.

### Why this matters
If every caller can slip in arbitrary kwargs, then profile discipline erodes and you’re back to many micro-dialects of dispatch.

Also, the current `model-review.py` already contains provider-specific schema normalization:

- OpenAI requires `additionalProperties: false`
- Google rejects it

That logic must move into the shared helper or profile layer, not remain caller-owned.

### Recommendation
Replace “raw `extra_kwargs` escape hatch” with one of:

- a validated override allowlist, or
- explicit typed optional fields

Examples of acceptable per-call overrides:
- `schema`
- `search`
- `reasoning_effort`
- `temperature` only if profile allows
- maybe `max_tokens`

Examples that should remain profile-owned:
- `provider`
- `model`
- `api_only`

Also: define schema behavior explicitly:
- when schema is used, does the helper write raw text only?
- parsed JSON only?
- both?

Given your error taxonomy includes `schema_error` and `parse_error`, I’d recommend:
- always write raw output artifact
- optionally write parsed JSON artifact when schema is expected
- classify parse/validation separately

---

## 5. The migration plan leaves split-brain documentation alive for too long

I agree with “don’t start by rewriting `llmx-guide`.” But the plan still needs an **immediate contradiction-reduction step**.

### Problem
Until late phases, agents will continue to encounter legacy CLI examples in a repo whose guard blocks them.

That is the exact failure mode this plan is meant to eliminate.

### Recommendation
Add a **Phase 0.5 / immediate hygiene patch**:

- top-banner warning in `llmx-guide/SKILL.md`
- top-banner warning in `brainstorm/references/llmx-dispatch.md`
- guard message updated to point to the new helper contract doc as soon as that doc exists

Not a full rewrite—just a prominent “not the normal agent path” banner.

That keeps the migration from remaining contradictory while work is in flight.

---

## Additional recommendations

## Standardize context assembly, not just context acceptance

The single-context rule is correct, but callers still need to build that one context. If every skill assembles its own combined file differently, you’ll recreate inconsistency one layer up.

Add either:

- a helper utility for assembling multiple sources with stable headers, or
- a documented canonical format for assembled context blocks

For example:
- source marker format
- ordering rules
- max-size trimming rules

This is especially relevant for review flows.

---

## Define shell-facing exit codes and stdout behavior

Some callers are shell scripts. They need a contract too.

I’d add:

- stable exit code mapping for `ok`, `timeout`, `rate_limit`, etc.
- stdout reserved for a tiny machine-readable summary or output path JSON
- never emit model content on stdout from the wrapper by default

That prevents a return to stdout scraping.

This is particularly important for replacing `research-ops/scripts/run-cycle.sh`.

---

## Add one more error class: dependency/bootstrap/config

Your taxonomy is good, but `dispatch_error` is too broad for one important class:
- helper cannot import `llmx`
- invalid profile
- missing credentials/config

Those are operationally different from model/provider failures.

At minimum distinguish:
- `config_error` or `dependency_error`

Also add a `retryable` boolean in metadata. That reduces supervision cost for hooks and loops.

---

## Recommended answers to the open questions

### 1. `scripts/` or dedicated package?
**Dedicated package/module for core logic; thin scripts for entrypoints.**

### 2. Plain JSON dicts or Pydantic?
**Stable JSON schema externally; lightweight Python dataclass/TypedDict internally.**
Avoid making Pydantic a hard runtime dependency unless there is a strong existing reason.

### 3. Hooks call helper directly or via tiny wrappers?
**Tiny task-specific wrappers.**
Shell hooks want a stable CLI-shaped contract. Keep them thin and logic-free.

### 4. Unified helper for all llmx subcommands later?
**No. Chat-style dispatch only for now.**
The plan is strongest when it stays narrow.

---

## Suggested approval status

**Approve direction, request plan revision before implementation.**

If you add the following, the plan becomes solid enough to execute:

1. profile governance + override/version policy
2. full artifact/atomicity/stale-output contract
3. package-vs-wrapper decision
4. constrained override surface + centralized schema/provider quirks
5. immediate doc/banner patch to reduce contradictions during migration

With those in place, this becomes a very strong refactor plan. Without them, the repo will likely converge on “one helper, many unofficial dialects,” which is exactly what you’re trying to eliminate.