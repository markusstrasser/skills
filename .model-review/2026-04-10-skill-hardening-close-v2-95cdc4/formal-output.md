## 1. Logical Inconsistencies

| ID | Severity | File(s) | Issue | Evidence | Consequence |
|---|---|---|---|---|---|
| F1 | high | `scripts/lint_skill_manifests.py` | `--manifest` selective mode is path-unstable and can crash on normal relative inputs | The script accepts `--manifest` as raw `Path`, passes it through unchanged, then prints `manifest_path.relative_to(ROOT)`. A relative path like `brainstorm/skill.json` is not under absolute `ROOT`, so `relative_to()` raises `ValueError`. | Common operator path usage fails hard instead of linting one manifest. This makes the advertised selective mode unreliable. |
| F2 | high | `shared/skill_manifest.py` | Manifest validator can raise `TypeError` on malformed `uses.*` entries instead of reporting validation issues | `dispatch_profiles`, `packet_builders`, and `artifact_schemas` are only checked as arrays, then each item is tested with membership (`if profile_name not in PROFILES`, etc.). Non-string unhashable items such as `{}` or `[]` will crash membership checks. | The linter is supposed to tolerate malformed manifests and emit issues; instead, some invalid manifests take down the validator. |
| F3 | medium | `review/scripts/model-review.py` | Review artifacts are anchored to current working directory, not `--project` | `project_dir` is resolved from `--project`/cwd, but `review_dir = Path(".model-review/...")` is built from process cwd rather than `project_dir`. | Running the script from outside the target repo writes `.model-review` to the wrong tree, breaking caller expectations and downstream artifact discovery. |
| F4 | medium | `shared/skill_manifest.py`, `brainstorm/SKILL.md`, `brainstorm/references/*.md` | Shared brainstorm schema registry underspecifies the new canonical artifact contract | Docs now define `matrix.json` as canonical and require fields like `domain_row`, `domain`, `transfer_mechanism`, `merged_into`, `caller_evidence`, `speculative`, `notes`; registry entry `brainstorm.matrix.v1` requires only `idea_id`, `source_artifact`, `axis`, `dominant_paradigm_escaped`, `disposition`. Similar under-specification exists for `brainstorm.coverage.v1`. | If this registry is treated as the shared contract, malformed brainstorm artifacts can pass contract checks while violating the docs. That is caller drift between declared schema and documented behavior. |
| F5 | low | `review/lenses/adversarial-review.md` | Docs contradict the implemented fallback policy | One section says “**NEVER downgrade models on failure**,” while a later section explicitly documents automatic Gemini Pro → Flash fallback, and tests in `review/scripts/test_model_review.py` assert that behavior. | Operators following docs manually will get contradictory instructions; automation and documentation no longer describe the same workflow. |

### Notes on confidence

- **F1** is highly reproducible: the `relative_to(ROOT)` call on a relative `Path` is deterministically unsafe.
- **F2** is also strong: Python membership against a dict/set with an unhashable probe raises immediately.
- **F3** is straightforward caller drift from path construction.
- **F4/F5** are contract/documentation mismatches rather than runtime crashes, but they matter because this repo is increasingly using shared manifests/docs as operational interfaces.

## 2. Cost-Benefit Analysis

| Rank | Change | Expected impact | Ongoing burden | Risk if unfixed | Value |
|---|---|---|---|---|---|
| 1 | Fix manifest CLI path normalization + nonexistent-file handling (`lint_skill_manifests.py`) | Restores selective linting, removes avoidable operator failures | Low | High: advertised CLI mode is brittle | Very high |
| 2 | Make `validate_manifest()` robust to non-string array members in `uses.*` | Converts crashers into proper lint findings; improves validator trustworthiness | Low | High: malformed manifests can take down CI/manual lint | Very high |
| 3 | Anchor `.model-review` output to `project_dir` or add explicit `--output-dir` | Eliminates artifact placement drift across automation contexts | Low-medium | Medium: tools may silently write into wrong repo/session | High |
| 4 | Align brainstorm schema registry with the documented matrix/coverage contract | Prevents future false-valid artifacts and keeps shared contracts honest | Medium | Medium: downstream validators can green-light incomplete artifacts | Medium-high |
| 5 | Resolve review fallback documentation contradiction | Reduces operator confusion and manual/automated drift | Low | Low-medium: misleading docs, not code breakage | Medium |

### Cost-adjusted assessment

These are all cheap to maintain once fixed because they reduce supervision cost:

- **F1/F2** directly lower CI/operator babysitting.
- **F3** lowers blast radius in multi-repo/tooling contexts.
- **F4** reduces long-term schema entropy.
- **F5** is mostly documentation debt, but it matters because this project relies heavily on docs as executable operator guidance.

## 3. Testable Predictions

| Prediction | How to test | Success / failure criterion |
|---|---|---|
| P1: selective manifest lint currently crashes on relative paths | From repo root: `python scripts/lint_skill_manifests.py --manifest brainstorm/skill.json` | **Current expected failure:** traceback/`ValueError` from `relative_to(ROOT)`. **Fixed behavior:** clean `OK brainstorm/skill.json` or lint issue output, exit 0/1 only. |
| P2: validator currently crashes on unhashable `uses.dispatch_profiles` entries | Feed a manifest containing `"dispatch_profiles": [{}]` to `validate_manifest()` | **Current expected failure:** `TypeError: unhashable type: 'dict'`. **Fixed behavior:** returned issue like `uses.dispatch_profiles must contain strings`. |
| P3: model-review writes artifacts outside target repo when invoked from another cwd | `cd /tmp && python /path/to/review/scripts/model-review.py --project /repo --topic t --context /repo/context.md` | **Current expected behavior:** `/tmp/.model-review/...` created. **Fixed behavior:** `/repo/.model-review/...` or explicit output dir. |
| P4: brainstorm schema registry currently accepts docs-invalid matrix rows | Add a downstream validation test using `ARTIFACT_SCHEMAS["brainstorm.matrix.v1"]` against a row missing `transfer_mechanism`/`caller_evidence` | **Current expected result:** row still considered valid by required-field list. **Fixed behavior:** contract rejects it or docs are narrowed to match. |
| P5: docs are self-contradictory about fallback | Text search `NEVER downgrade models on failure` and `Gemini Rate Limit Fallback` in `review/lenses/adversarial-review.md` | **Current expected result:** both statements coexist. **Fixed behavior:** one coherent policy only. |

## 4. Constitutional Alignment (Quantified)

No constitution provided, so this is an internal-consistency scorecard.

| Principle inferred from repo | Score | Rationale |
|---|---:|---|
| Shared contracts should be machine-checkable | 55% | Good direction with `skill.json`, packet builders, artifact schema registry. But brainstorm docs now exceed what the registry actually enforces. |
| Tooling should fail closed with actionable diagnostics, not traceback | 45% | `validate_manifest()` and `lint_skill_manifests.py` still have malformed-input/path cases that can raise exceptions instead of emitting structured issues. |
| Artifacts should live in deterministic repo-local locations | 60% | Review docs assume `.model-review/...` inside the project, but `model-review.py` ties output to process cwd. |
| Documentation should describe actual runtime behavior | 65% | Review docs improved substantially, but fallback instructions are internally inconsistent. |
| Migration hardening should reduce caller drift | 70% | The work is moving toward explicit manifests and shared contracts, but F3/F4 are exactly the kind of caller/contract drift this migration is supposed to remove. |

**Overall internal consistency:** **59/100**

Main drag is not algorithmic; it is interface reliability: path contracts, malformed-input behavior, and doc/schema fidelity.

## 5. My Top 5 Recommendations (different from the originals)

1. **Normalize all manifest CLI inputs to repo-rooted absolute paths before validation/output**
   - **What:** In `scripts/lint_skill_manifests.py`, convert each `--manifest` to `(ROOT / path).resolve()` when relative; reject paths outside `ROOT`; handle missing files as lint issues.
   - **Why:** This removes a 100% reproducible failure mode for normal relative-path usage and makes selective linting operationally trustworthy.
   - **How to verify:** Add CLI tests for:
     - relative repo-local path
     - absolute repo-local path
     - missing file
     - outside-repo path  
     Metrics: 0 uncaught exceptions; deterministic exit codes 0/1 only.

2. **Make `shared/skill_manifest.validate_manifest()` type-safe for list members**
   - **What:** Before membership checks, validate that each `uses.dispatch_profiles`, `uses.packet_builders`, and `uses.artifact_schemas` entry is a non-empty string.
   - **Why:** A validator that crashes on malformed input defeats its purpose. This is a hard correctness issue, not a nicety.
   - **How to verify:** Add unit tests with `[]`, `{}`, `1`, `""`, and valid strings in each array. Success metric: every malformed case returns issues; none raise.

3. **Anchor review output directories to the target project**
   - **What:** Change `review_dir` creation to `project_dir / ".model-review" / ...` or add `--output-dir` with sane default = `project_dir/.model-review/...`.
   - **Why:** Repo-local artifact placement is part of the tool contract. Current cwd-relative behavior creates silent drift in automation.
   - **How to verify:** Integration test that runs `main()` from a different cwd with `--project <repo>` and asserts the created directory is under `<repo>/.model-review`.

4. **Unify brainstorm’s schema contract in one place**
   - **What:** Either expand `ARTIFACT_SCHEMAS["brainstorm.matrix.v1"]` / `brainstorm.coverage.v1` to match docs, or narrow docs to the truly required minimum and mark other fields as recommended/derived.
   - **Why:** Shared schema names should not understate a canonical contract. Underspecified contracts increase supervision cost because reviewers must manually infer completeness.
   - **How to verify:** Add contract tests with minimally valid and intentionally incomplete matrix/coverage artifacts. Success metric: docs and registry agree exactly on required fields.

5. **Resolve the fallback-policy contradiction in review docs**
   - **What:** Replace “NEVER downgrade models on failure” with the actual policy: automated fallback is allowed only as implemented by the shared dispatch layer, and operators should inspect coverage/fallback metadata.
   - **Why:** Contradictory instructions create operator variance and bad postmortems.
   - **How to verify:** Grep-based doc test or snapshot asserting only one fallback policy statement exists across `review/SKILL.md`, `review/references/dispatch.md`, and `review/lenses/adversarial-review.md`.

## 6. Where I'm Likely Wrong

- I’m strongest on the **path-handling and validator crash** findings because they follow directly from shown code.
- I’m less certain on **F4’s operational impact** because the excerpt shows schema registration, not downstream artifact validation code. If the registry is currently name-only metadata, the bug is contractual/documentational rather than runtime today.
- I may be somewhat **over-weighting CLI robustness** because the repo seems operator/tool driven; if these scripts are only invoked from tightly controlled wrappers, blast radius is smaller. Still, the current interfaces advertise broader use.
- I did not inspect the omitted observe/session files, so there may be **higher-severity runtime issues elsewhere** outside the provided excerpts. My ranking is therefore confidence-weighted by visible evidence, not by total repo risk.