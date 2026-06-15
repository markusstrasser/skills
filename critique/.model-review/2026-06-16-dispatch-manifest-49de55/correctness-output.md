## 1. Confirmed or Likely Bugs
file:line | severity | claim | evidence

.model-review/dispatch-manifest-design.md:22 | high | “Explicit CLI overrides when set” is likely buggy for booleans/defaulted args unless the implementation can distinguish “absent” from “default value.” | If argparse defaults are `False`, `None`, empty list, or preset defaults, `model-review.py` may accidentally override manifest policy even when the caller did not explicitly set anything.

.model-review/dispatch-manifest-design.md:23 | high | `model-review.py` exiting 1 on manifest `blockers` risks creating a second, non-obvious enforcement point with unclear semantics. | The dispatch tool now interprets triage validity. If blocker schema, meaning, or severity changes, dispatch can fail closed or fail inconsistently unless this contract is versioned and strict.

.model-review/dispatch-manifest-design.md:24 | high | Axis resolution has an underspecified fallback path and can silently run the wrong review set. | “`--axes` omitted → from manifest `layers.design.axes` or `preset`” does not define precedence between `axes` and `preset`, behavior when both are absent, behavior when both conflict, or behavior on unknown axis names.

.model-review/dispatch-manifest-design.md:17 | medium | Path-reference inference can misclassify packet-only reviews as repo reviews and vice versa. | “Packet with path refs → `repo` + scout on” relies on detecting “path refs,” but design admits regex brittleness in the open questions.

.model-review/dispatch-manifest-design.md:18 | medium | “Self-contained packet, no refs → packet + scout off” is unsafe as a correctness default. | A packet may omit explicit paths while still depending on repository invariants, current implementation behavior, or architectural context.

.model-review/dispatch-manifest-design.md:19 | high | `review_targets.design_target.*` overrides can mask bad inference without specifying validation or conflict reporting. | Overrides “win,” but the design does not say whether triage records why the inferred policy was overridden, whether contradictory inputs are warned, or whether invalid override values block dispatch.

.model-review/dispatch-manifest-design.md:25 | medium | Budget gate based on `_resolved_axis_timeout()` can skip useful axes because configured timeout is a worst-case envelope, not expected runtime. | “llmx high=600s scale” means a remaining budget below the profile timeout may skip an axis that would likely complete quickly.

.model-review/dispatch-manifest-design.md:28 | high | “Skip axis if remaining wall clock < resolved profile timeout” can produce successful no-op reviews unless the exit/report contract defines skipped-all as non-success. | The design says never truncate, but does not define whether skipped axes are reported as neutral, failure, or incomplete.

.model-review/dispatch-manifest-design.md:12-14 | medium | `dispatch_policy` lacks schema/version/provenance fields, making compatibility and stale-manifest bugs likely. | Only three top-level fields are listed: `premise_scout`, `context_scope`, and `budget_seconds`.

.model-review/dispatch-manifest-design.md:30-33 | medium | Open questions are not peripheral; they affect core correctness of dispatch. | Extract/verify flags, brittle scope inference, budget-driven axis dropping, and manifest requirement all change what review actually runs.

## 2. Structural Risks to Correctness
Design choices that will breed bugs even if no bug exists yet.

1. **Manifest-first is sound only if the manifest is a typed contract, not a loose JSON blob.**  
   The design moves policy into deterministic triage output, which is directionally correct. But correctness depends on having a strict schema, version, validation, and fail-closed handling for unknown or missing fields. Without those, the manifest becomes another implicit CLI surface.

2. **Dual source of truth remains.**  
   The design says `--dispatch-manifest` reads policy, but explicit CLI overrides still win. That is operationally useful, but architecturally dangerous unless every override is recorded in output. Otherwise a run cannot be reconstructed from the manifest alone.

3. **Boolean `premise_scout` is too coarse.**  
   Scout behavior is likely not binary. There are at least several distinct cases:
   - no scout needed,
   - scout required before critique,
   - scout required only for repository context,
   - scout required because packet has unresolved references,
   - scout forbidden because review must be packet-confined.  
   Collapsing this to `true/false` invites incorrect dispatch.

4. **Binary `context_scope` is too coarse.**  
   `repo | packet` does not capture hybrid scopes, bounded repo scopes, allowlisted paths, forbidden paths, generated files, vendored files, or dependency-level context. Reviews often need “packet plus named files” rather than full repo or packet-only.

5. **Budget is being treated as dispatch policy rather than completeness policy.**  
   `budget_seconds` decides whether axes are skipped, but skipped axes affect review completeness. That should be represented explicitly in results, not only in scheduling behavior.

6. **Budget skip semantics can silently weaken review quality.**  
   “Never truncate” is good. But “skip if remaining wall clock < timeout” can degrade from multi-axis review to partial or empty review. Correctness requires an explicit incomplete status, not just omitted axes.

7. **Manifest generation heuristics encode policy in fragile text detection.**  
   Deterministic does not mean correct. Regex/path-reference detection is reproducible, but it can reproducibly make the wrong call.

8. **Blockers are overloaded.**  
   A manifest field named `blockers` sounds like triage validation state, not dispatch policy. Having `model-review.py` consume it couples review execution to triage internals.

9. **Preset-to-axes expansion is under-specified.**  
   If axes can come from `layers.design.axes` or `preset`, then preset resolution must be deterministic, versioned, and visible. Otherwise two runs with the same manifest may diverge after preset definitions change.

10. **No stated invariant that dispatch output records effective policy.**  
   The effective policy should include manifest values plus CLI overrides plus resolved axes plus skipped axes plus budget state. Without this, auditing failures will be hard.

## 3. Boundary / Error-Path Gaps
Unchecked return codes, fail-open paths, missing guards.

1. **Missing manifest behavior is undefined.**
   - If `--dispatch-manifest` points to a missing file, dispatch should fail closed.
   - If the flag is omitted, it is unclear whether legacy CLI behavior continues.
   - If manifest-first is the desired architecture, optional manifest mode is a migration risk.

2. **Malformed manifest behavior is undefined.**
   - Invalid JSON/YAML.
   - Wrong top-level type.
   - Missing `dispatch_policy`.
   - Unknown `context_scope`.
   - Negative or non-integer `budget_seconds`.
   - Unknown axes.
   - Unknown preset.
   - `blockers` field has unexpected type.

3. **Unknown-field handling is unspecified.**
   For correctness, unknown fields under policy-bearing sections should probably be rejected or at least warned with schema versioning. Silent ignore creates migration hazards.

4. **No schema version is described.**
   Once `review_gate.py` and `model-review.py` are independently changed, old manifests may be interpreted incorrectly.

5. **No manifest provenance or freshness check.**
   The dispatch manifest should identify:
   - source packet,
   - repo root,
   - commit/worktree fingerprint if repo context is used,
   - triage tool version,
   - generated timestamp,
   - target files or packet hash.  
   Otherwise stale manifests can dispatch the wrong review.

6. **No guard for all axes skipped.**
   If every axis is skipped due to budget, the process should not look like a successful review. It should exit with a distinct incomplete status or produce an explicit incomplete result.

7. **No guard for partially skipped required axes.**
   If `arch,correctness` are requested and `correctness` is skipped, the final review must say that required coverage is incomplete.

8. **Budget clock source is unspecified.**
   Wall-clock budgeting should use monotonic time for elapsed computation. System clock changes can produce negative or inflated remaining budget.

9. **Budget start point is unspecified.**
   Is `budget_seconds` measured from triage start, dispatch start, model-review start, or full session start? Different interpretations change skip behavior.

10. **`budget_seconds: null` is ambiguous.**
   It could mean unlimited, unspecified, inherited from CLI, or disabled. The manifest contract should define it exactly.

11. **CLI override serialization is missing.**
   If CLI overrides are allowed, final output should include the effective resolved policy and indicate which fields came from CLI instead of manifest.

12. **`blockers` handling may fail open if absent.**
   If old manifests lack `blockers`, does dispatch assume no blockers? That would be dangerous unless old manifests are versioned and rejected.

13. **`blockers` handling may fail closed on non-review blockers.**
   If blockers include advisory or non-dispatch issues, `model-review.py` may refuse valid dispatches.

14. **No path-reference validation.**
   If triage infers `repo` because of path refs, those refs should be checked for existence, normalization, symlink safety, repo containment, and case sensitivity.

15. **No packet isolation guarantee.**
   If `context_scope=packet`, model-review should guarantee it does not load repo context through default behavior, scout side effects, extraction, verification, or prompt assembly.

16. **Open question about extract/verify flags is a correctness gap.**
   If extract/verify materially changes the review input, leaving them outside the manifest means the manifest is not actually the dispatch contract.

17. **No clear behavior on manifest/CLI conflict.**
   “Explicit CLI overrides when set” defines precedence, but not whether conflict is reported. Silent override is a traceability failure.

18. **No distinct exit codes.**
   Everything described appears to collapse to exit 1 for blockers. There should be separable outcomes for malformed manifest, blocked triage, all axes skipped, model failure, and review findings.

## 4. Goals & Principles Alignment

Manifest-first dispatch is the right architectural direction. Moving scout, scope, axes, and budget policy out of ad hoc session CLI flags and into deterministic triage output improves reproducibility, auditability, and composability.

The design aligns with correctness goals in these ways:

- **Policy becomes explicit.**
  Dispatch behavior is no longer hidden in the session agent’s invocation.

- **Triage becomes deterministic.**
  Heuristic policy generation avoids LLM drift at the dispatch-decision layer.

- **Review execution can become replayable.**
  A manifest could allow the same critique to be rerun later with the same policy.

- **Budget behavior avoids truncation.**
  Skipping before starting an axis is safer than killing a model call halfway through.

But the current design is not yet complete enough to be a correctness boundary. It needs to be treated as a formal interface between `review_gate.py` and `model-review.py`.

Key principle gaps:

1. **Correctness over convenience requires fail-closed schema validation.**  
   Do not accept loose, partial, or stale manifests.

2. **Reproducibility requires effective-policy output.**  
   The final run artifact must record resolved axes, scope, scout decision, budget, skips, blockers, CLI overrides, and manifest version.

3. **Determinism is insufficient without conservative defaults.**  
   Regex-based triage can be deterministic and still wrong. Ambiguous packets should probably become `repo` plus scout, or block for explicit target metadata, depending on desired safety.

4. **Manifest-first should not mean manifest-optional forever.**  
   A dual path is acceptable during migration, but the target state should require a manifest or produce a deliberately legacy-marked run.

5. **Budget should not silently reduce required coverage.**  
   If axes are skipped, the run should be marked incomplete, not successful.

## 5. Where I'm Likely Wrong

1. The implementation may already use argparse mechanisms such as `default=argparse.SUPPRESS` or explicit sentinel values, which would make CLI override detection safe.

2. `review_gate.py` may already emit a schema version, provenance fields, and full validation not mentioned in this design packet.

3. `model-review.py` may already produce a final effective-policy artifact, including skipped axes and override sources.

4. The `blockers` contract may already be stable elsewhere, and line 23 may simply be enforcing an existing formal triage result.

5. `_resolved_axis_timeout()` may be calibrated to expected runtime rather than maximum timeout despite the wording, reducing the risk of over-skipping.

6. The path-reference heuristic may not be a regex-only system in implementation; it may parse structured packet metadata or target declarations.

7. `review_targets.design_target.*` may already be mandatory for ambiguous packets, making heuristic misclassification less important.

8. The project may intentionally allow legacy no-manifest dispatch during migration, with external orchestration ensuring correctness.

## 6. Contract & migration completeness (mechanism view)
Interface breaks, dual paths, orphaned consumers, fail-open error semantics.

The mechanism is promising but incomplete unless the following contract is made explicit.

Required manifest contract:

```text
manifest_version: required
generated_by: required
generated_at: required
source_packet_hash: required or strongly preferred
repo_identity: required when context_scope=repo
dispatch_policy:
  premise_scout: required boolean or richer enum
  context_scope: required enum
  budget_seconds: required integer|null with defined null semantics
layers.design.axes or preset: required unless CLI axes explicitly override
blockers: required list with versioned schema
```

Required dispatch behavior:

1. **If `--dispatch-manifest` is present and manifest cannot be read: fail closed.**

2. **If manifest schema version is missing or unsupported: fail closed.**

3. **If `blockers` is missing: fail closed for manifest-mode.**

4. **If `blockers` is non-empty: fail with a distinct blocked-dispatch status.**

5. **If axes cannot be resolved exactly once: fail closed.**
   - Both `axes` and `preset` present should have defined precedence or be rejected unless equivalent.
   - Unknown axes should fail.
   - Empty axes should fail unless explicitly allowed.

6. **If CLI overrides manifest fields: record every override.**
   Silent override undermines manifest-first dispatch.

7. **If all axes are skipped by budget: exit incomplete, not success.**

8. **If some axes are skipped: final output must mark review incomplete and list skipped axes with reason.**

9. **If `context_scope=packet`: enforce packet-only input.**
   Do not merely omit scout. Ensure no repo reads occur.

10. **If `context_scope=repo`: validate repo availability and target references.**

Migration risks:

- **Dual path drift.**  
  Legacy CLI flags and manifest-driven policy can diverge. During migration, every run should identify whether it was `manifest-mode` or `legacy-mode`.

- **Orphaned consumers.**  
  Any tools that call `model-review.py` directly may unknowingly bypass triage policy. Either require manifest by default or emit a strong legacy-mode warning/artifact.

- **Preset drift.**  
  If manifests reference `preset` instead of expanded axes, future preset changes alter old dispatches. Prefer materializing resolved axes into the manifest, with preset as provenance.

- **Blocker schema drift.**  
  If triage changes blocker representation, dispatch may mis-handle it. Version blocker schema or reduce dispatch dependency to a simple `dispatch_allowed: true|false` plus reasons.

- **Budget semantics drift.**  
  `budget_seconds` should define start time, null meaning, units, monotonic computation, and incomplete-run behavior.

Overall: manifest-first dispatch is sound as an architectural direction, but only if the manifest becomes a strict, versioned, audited execution contract. In its current described form, the biggest correctness risks are silent CLI override, loose heuristic scope inference, ambiguous axis resolution, and budget-driven partial reviews that may appear successful.