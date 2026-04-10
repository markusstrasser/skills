## 1. Logical Inconsistencies

| ID | Finding | Evidence | Why it is formally inconsistent | Impact |
|---|---|---|---|---|
| L1 | **“Oldest marker” logic is not implemented** | `hooks/sessionend-overview-trigger.sh` says `# Use the oldest per-type marker as diff baseline`, but code sets `oldest_marker` to the **first** existing marker, then `break`s. | The comment and the implementation are not equivalent. “Oldest” is an ordering property over all candidate markers; “first existing in configured_types order” is not. | False negatives/positives in trigger decisions for multi-type repos. |
| L2 | **Staleness check is wrong for multi-type projects** | `hooks/overview-staleness-cron.sh` scans configured types, picks the first existing `overview-marker-*`, and computes age from that single file. | The intended question is “is any configured overview stale?” or “which types are stale?” The implemented predicate is “is the first marker in config order stale?” These are different functions. | A stale type can remain stale indefinitely if an earlier type has a fresh marker. |
| L3 | **Shared overview contract is not actually centralized** | `scripts/generate_overview.py` uses `shared.overview_config.read_overview_config`, but `hooks/overview-staleness-cron.sh` uses `grep/cut/xargs`, and `hooks/sessionend-overview-trigger.sh` has its own inline parser for `.claude/overview.conf`. | The plan says the repo now has a shared packet/config spine. But the operational overview contract still exists in at least 3 parsers. A change to config semantics is not single-source-of-truth. | Contract drift risk remains high; migration claim is overstated. |
| L4 | **Plan-close budget metadata under-specifies the actual packet size** | In `review/scripts/build_plan_close_context.py`, `BudgetPolicy(limit=max_diff_chars, metric="chars")` is attached to a packet that also includes git status, diff stat, scope, and up to `max_files * max_file_chars` of excerpts. With defaults: `40k + 12*8k = 136k` chars before overhead. | The manifest’s stated limit is for only one component (`diff`), not the packet. So the budget object does not describe the artifact it is attached to. | Downstream tooling can believe a packet is within budget when actual payload is ~3.4× larger. |
| L5 | **“Status: implemented” is not backed by the shown verification for key success criteria** | The plan file claims `Status: implemented`. But shown tests only include a basic payload-shape check in `scripts/test_generate_overview.py`; no shown test enforces live-vs-batch payload hash equivalence, marker semantics, or plan-close golden output. | “Implemented” for a migration with explicit success criteria requires evidence that those criteria are enforced. The available test surface does not establish that. | High risk of migration drift hidden behind a “done” label. |
| L6 | **Project enumeration remains hardcoded despite “many repos” framing** | `scripts/generate_overview.py` has `DEFAULT_PROJECTS = ("meta", "intel", "selve", "genomics")`; `hooks/overview-staleness-cron.sh` has a separate hardcoded project list. | A scalable shared mechanism should not require code edits in multiple files to add a repo. The current implementation still encodes repo membership as source code. | Ongoing maintenance drag; easy to forget one list and get silent non-coverage. |

### Highest-confidence correctness bug: marker selection
This is the clearest correctness issue because it is directly visible and reproducible.

#### Reproduction condition
Project has:
- `OVERVIEW_TYPES=source,tooling`
- `.claude/overview-marker-source` mtime = 1 day ago
- `.claude/overview-marker-tooling` mtime = 14 days ago

#### Expected
Tooling overview should be considered stale.

#### Actual in current cron hook
The script picks `overview-marker-source` first, sees age `< 7`, and exits. Tooling is never evaluated.

That is not a style issue; it is a wrong predicate.

---

## 2. Cost-Benefit Analysis

Ranked by value adjusted for ongoing cost.

| Rank | Change | Expected impact | Maintenance burden | Composability | Risk if not done |
|---|---|---:|---:|---:|---:|
| 1 | **Centralize marker/config semantics in shared Python and delete hook-local parsers** | Very high: removes 2-3 duplicated contract surfaces and fixes future drift | Low-medium | High | High |
| 2 | **Fix per-type marker selection/staleness logic** | Very high: restores correctness of auto-regeneration | Low | High | High |
| 3 | **Add live/batch payload-hash equivalence tests and marker regression tests** | High: converts migration claims into enforced invariants | Low | High | High |
| 4 | **Make packet budget metadata describe full packet size, not just diff slice** | Medium-high: improves dispatch safety and provenance correctness | Low | High | Medium |
| 5 | **Replace hardcoded project lists with discovery/config input** | Medium: reduces operational drift as repo count grows | Medium | Medium-high | Medium |

### Notes per change

#### 1. Centralize marker/config semantics
- **Impact:** Eliminates repeated parsing logic in `generate_overview.py`, `overview-staleness-cron.sh`, and `sessionend-overview-trigger.sh`.
- **Why high value:** Every future config-key change currently has multiple edit sites. That is recurring supervision cost.
- **Burden:** Low-medium because the shared modules already exist (`shared.overview_config.py`); this is mainly migration completion, not greenfield.

#### 2. Fix marker selection/staleness logic
- **Impact:** Directly fixes missed overview refreshes.
- **Why high value:** This is a correctness bug in production automation, not a refactor nicety.
- **Burden:** Low. The current logic is localized.

#### 3. Add equivalence/regression tests
- **Impact:** Prevents silent prompt drift and false “migration complete” claims.
- **Why high value:** This migration’s main promise is unification without behavior drift. That promise is only real if CI enforces it.
- **Burden:** Low. Fixture-based tests are cheap to maintain relative to the risk reduced.

#### 4. Correct budget metadata
- **Impact:** Improves trustworthiness of manifests and dispatch decisions.
- **Why value-adjusted:** The current metadata is misleading enough to cause bad downstream decisions once someone relies on it.
- **Burden:** Low; either track packet-total chars/tokens or rename the budget object to reflect component scope.

#### 5. Remove hardcoded repo lists
- **Impact:** Moderate today, higher later.
- **Why not rank higher:** It is a maintenance issue, not the most acute correctness bug.
- **Burden:** Medium because you need a discovery source or explicit manifest.

---

## 3. Testable Predictions

| Prediction | How to test | Success criterion | Current likely result |
|---|---|---|---|
| P1 | Multi-type staleness is currently under-triggering | Create two marker files with different mtimes; place fresh marker first in `OVERVIEW_TYPES` order | Cron should regenerate if **any** configured type is stale | It will incorrectly skip regeneration |
| P2 | Session-end diff baseline is wrong for mixed-age markers | Create per-type markers at different commits; make changes only relevant since the older marker | Trigger logic should use the proper baseline per type or an explicit aggregate rule | It will use the first marker found, not the correct one |
| P3 | Packet budget manifests for plan-close underreport actual payload | Build a packet with defaults and 12 large touched files; compare `manifest` budget vs actual file size/token estimate | Reported budget should upper-bound or accurately characterize the artifact | Manifest limit will be materially below real payload size |
| P4 | Live and batch overview payloads can drift without test failure | Intentionally change one rendering path or batch request assembly detail; run shown tests | CI should fail on payload hash mismatch | Shown tests would likely still pass |
| P5 | Adding a new repo requires edits in multiple places | Add a fifth repo with `.claude/overview.conf`; run batch + cron flows without code changes | New repo should be discoverable automatically | It will be missed unless hardcoded lists are updated |
| P6 | Config contract changes can silently diverge between hooks and generator | Add/change a config key with whitespace/quoting edge cases | All entrypoints should interpret config identically | Shell `grep/cut/xargs` and Python parser can diverge |

### Strongest falsifiable claim
If you add this regression test, it should fail today:

- Fixture:
  - `OVERVIEW_TYPES=source,tooling`
  - `source` marker fresh
  - `tooling` marker stale
- Expected:
  - staleness logic returns “needs refresh”
- Current code:
  - returns “no refresh”

If that test passes today, then my reading of the hook is wrong.

---

## 4. Constitutional Alignment (Quantified)

No constitution was provided, so this is an internal-consistency score.

### Quantified score: **5.5 / 10**

Breakdown:

| Dimension | Score | Basis |
|---|---:|---|
| Single-source-of-truth | 4/10 | `shared.overview_config.py` exists, but hook-local config parsers remain |
| Behavioral equivalence proof | 4/10 | No shown live-vs-batch hash-equivalence enforcement |
| Correctness of automation predicates | 5/10 | Marker-selection logic has at least one visible correctness bug |
| Artifact/provenance honesty | 6/10 | Packet manifests exist, but budget semantics are incomplete/misleading |
| Entry-point compatibility | 8/10 | Thin shell wrappers are good; path compatibility preserved |

### Specific quantified inconsistencies
- **2 direct comment/implementation mismatches**
  1. “oldest marker” vs “first existing marker”
  2. “implemented” vs lack of shown verification for explicit success criteria
- **3 contract surfaces for overview config**
  1. shared config reader
  2. shell `grep/cut/xargs`
  3. inline Python parser
- **1 budget-spec mismatch**
  - packet budget attached to total artifact but parameterized by diff-only limit

So the refactor direction is good, but the closeout state is not yet logically clean.

---

## 5. My Top 5 Recommendations (different from the originals)

### 1. Fix marker semantics first
- **What:** Replace “first existing marker” logic with explicit per-type state evaluation.
- **Why:** This is the highest-confidence correctness bug. In multi-type repos, current logic can suppress needed regenerations. Impact is binary: overview refresh either happens or not.
- **How to verify:** Add integration tests covering:
  - fresh/stale mixed marker mtimes
  - mixed commit hashes
  - different `OVERVIEW_TYPES` orders  
  Metric: 100% pass on 6–8 matrix cases; current code should fail at least 2.

### 2. Move all overview config parsing and marker-state decisions into `shared/`
- **What:** Introduce one shared function for:
  - reading `overview.conf`
  - enumerating types
  - resolving marker paths
  - computing staleness / diff baselines
- **Why:** Right now the overview contract is duplicated across at least 3 entrypoints. Each duplicate multiplies drift probability. Centralization lowers long-run supervision cost more than any local cleanup.
- **How to verify:** Delete all direct `grep/cut/xargs` and inline config parsing from hooks.  
  Metric: number of config parsers in active paths goes from 3 to 1.

### 3. Add exact live-vs-batch payload equivalence tests
- **What:** For a fixed fixture repo, assert identical payload text and/or identical payload hash between:
  - `generate_overview.py live`
  - `generate_overview.py batch` request construction
- **Why:** The migration’s main claim is unification. Without exact equivalence tests, prompt drift remains undetectable.
- **How to verify:** CI test that compares:
  - payload bytes
  - manifest hash
  - model/profile metadata  
  Metric: byte-for-byte equality on fixture input.

### 4. Make packet budget metadata honest
- **What:** Change `build_plan_close_context.py` budget policy to reflect the full packet, or encode per-section budgets separately.
- **Why:** Current default envelope is approximately:
  - diff: 40k chars
  - file excerpts: up to 96k chars
  - overhead: status/stat/scope/title  
  So declared limit can understate actual artifact by ~3×.
- **How to verify:** Emit `actual_chars` and `estimated_tokens` in the manifest and assert `declared_limit >= actual_chars` if the limit is meant as a bound. Otherwise rename it to `component_limit`.
- **Metric:** 0 cases where manifest implies safety while actual artifact exceeds it.

### 5. Replace hardcoded repo lists with discovery or explicit input
- **What:** Remove `DEFAULT_PROJECTS` and cron’s separate `PROJECTS` array in favor of:
  - CLI-provided project roots, or
  - discovery of repos containing `.claude/overview.conf`
- **Why:** Hardcoded membership is low-signal ongoing maintenance. Every new repo requires source edits in multiple places, which is exactly the kind of drift this refactor is meant to reduce.
- **How to verify:** Add a temp fifth repo fixture and prove batch/cron pick it up without code changes.
- **Metric:** onboarding a repo requires config only, not code edits.

---

## 6. Where I'm Likely Wrong

1. **The omitted portions may already contain some of the missing tests.**  
   I only saw excerpts of `scripts/test_generate_overview.py` and `review/scripts/test_model_review.py`. If there are additional unshown tests for marker semantics or payload-hash equivalence, my “verification gap” claim weakens.

2. **`shared.file_specs.py` may already handle some edge cases I’m worried about indirectly.**  
   I avoided making strong claims about binary/range-spec handling because the shared helper implementation was not shown.

3. **Some “drift” points may be deliberate operational boundaries rather than unfinished migration.**  
   For example, keeping hook logic lightweight and separate from shared Python may be intentional. My criticism is that this preserves duplicated contract logic, not that it is impossible to justify.

4. **The batch path may already be closer to live-path equivalence than the shown tests imply.**  
   The code structure suggests both use `build_overview_packet`, which is good. My concern is specifically that this equivalence is not visibly enforced by tests.

5. **Hardcoded project lists may be acceptable if this tool is intentionally private and fixed-scope.**  
   I still think it conflicts with the stated “many repos” design target, but if operational scope is intentionally capped at four repos, this is more of a roadmap inconsistency than an immediate defect.