## 1. Logical Inconsistencies

| Issue | Why it is inconsistent | Likely consequence |
|---|---|---|
| **Overview is declared in-scope, but v1 only specifies Markdown rendering** | The plan says `hooks/generate-overview.sh` and batch must migrate onto the shared engine, but also says “Markdown + manifest JSON is enough for v1.” Current overview input is not a Markdown packet; it is a tagged prompt with `<instructions>` and `<codebase>`. | Either overview becomes a behavior-changing migration, or the shared engine immediately needs a second renderer. As written, Phase 4 cannot be completed without violating Phase 1’s stated output scope. |
| **“Shared mechanics, not semantics” is violated by the proposed selector set** | `context_selectors.py` is supposed to be mechanical, but its responsibilities include constitution/goals discovery and repomix capture. Those are not neutral mechanics; they encode repo policy and skill semantics. | The “selectors” module risks becoming a grab-bag of task-specific policy, exactly what the plan says to avoid. |
| **Stable hashing and created timestamps are underspecified together** | The plan requires deterministic rendering and stable hashing, but also requires manifest fields including `created timestamp`. If the hash covers the manifest, it cannot be stable across runs. If it excludes the timestamp, that needs to be explicit. | Tests for determinism will either fail or become meaningless because “same inputs” still produce different manifests. |
| **Budgeting is a success criterion but not part of the object contract** | The plan stresses truncation, token budgets, and dispatch fit, but `ContextPacket`/`PacketSection` have no budget policy, no token-estimate field, and no truncation contract. | Builders will reintroduce ad hoc limit logic outside the shared layer, especially overview, recreating the current duplication. |
| **“No duplicated constitutional preamble assembly” is a success criterion, but no shared preamble API is actually specified** | The plan mentions constitution/goals discovery in selectors, but not a canonical `build_preamble()` or equivalent. | Model-review will likely keep bespoke preamble composition even after nominal migration, producing a migration lie. |
| **The proposed block model does not capture current live edge cases** | Current plan-close behavior includes absent/deleted file markers, tracked-vs-untracked filtering, diff placeholders like `(no tracked unified diff available)`, and excerpt truncation markers. The block schema does not model error states/provenance states explicitly. | Either the renderer becomes full of special-case strings, or behavior regresses during migration. |
| **The plan treats plan-close, model-review, and overview as the same class of problem, but only two of the three actually share a document shape** | Plan-close and model-review produce review context documents. Overview produces an extraction-wrapped generation prompt. The sharedality is in source capture and provenance, not necessarily packet AST shape. | Wrong abstraction boundary: a universal packet object may be more coupling than reuse. |

### Unstated assumptions that need to be made explicit

1. **Assumption:** overview prompt behavior is insensitive to packet syntax changes.  
   **Not justified** by current code or docs.

2. **Assumption:** constitution/goals discovery rules are repo-global rather than skill-specific.  
   That may be false; some skills may want goals but not constitution, or vice versa.

3. **Assumption:** one manifest schema can represent both review packets and repomix-based overview prompts without distortion.  
   Possible, but not shown.

4. **Assumption:** deterministic ordering exists for all source sets.  
   For git-derived paths and repomix output, ordering must be pinned or hashes are unstable.

---

## 2. Cost-Benefit Analysis

Scoring formula used here:

**Adjusted Value = 2×Impact + Composability − Maintenance Drag − Blast Radius Risk**

Scale is heuristic; higher is better.  
Creation effort is intentionally excluded.

| Proposed change | Impact | Composability | Maintenance drag | Blast radius risk | Adjusted value | Assessment |
|---|---:|---:|---:|---:|---:|---|
| **Shared file/range parsing + excerpt extraction** | 5 | 5 | 1 | 1 | **13** | Best immediate payoff. This duplication is real and already active in multiple paths. |
| **Shared constitutional/goals preamble composer** | 4 | 4 | 1 | 1 | **10** | High value, but only if separated from packet rendering. Today this is concentrated in model-review; likely to spread. |
| **Migrate plan-close onto shared primitives** | 4 | 3 | 1 | 2 | **8** | Good proving ground. Existing behavior is explicit and testable. |
| **Add manifest/provenance surface** | 4 | 4 | 2 | 2 | **8** | Worth it, but only if content-hash vs run-metadata is defined cleanly. |
| **Tight enforcement against new ad hoc builders** | 3 | 3 | 1 | 1 | **7** | Valuable after migration stabilizes. Premature enforcement can freeze a bad abstraction. |
| **Migrate model-review context assembly fully onto packet engine** | 3 | 3 | 2 | 2 | **5** | Moderate value. Real reuse is mainly preamble + file-spec assembly, not necessarily packet AST. |
| **Migrate overview live + batch to one Python builder** | 4 | 4 | 3 | 4 | **5** | Worth doing, but only if it preserves current prompt format and config semantics exactly. High blast radius. |
| **Shared generic packet core with `TextBlock/FileBlock/DiffBlock/CommandBlock/ListBlock`** | 3 | 4 | 4 | 3 | **3** | Risk of speculative generalization. The current commonality may not justify a universal AST yet. |
| **General shell-facing CLI (`scripts/context-packet.py`)** | 2 | 2 | 3 | 2 | **1** | Low value now. Adds another public surface to support before the importable API is proven. |

### Rank by value adjusted for ongoing cost

1. Shared file/range parsing + excerpt extraction  
2. Shared preamble composer  
3. Plan-close migration  
4. Manifest/provenance surface  
5. Enforcement, but only after stabilization  
6. Overview Python helper, with strict compatibility gate  
7. Model-review full packetization  
8. Generic universal packet AST  
9. General CLI

### Net judgment

The plan is strongest when it targets **shared source acquisition and provenance**.  
It is weakest when it jumps to **one canonical packet object model** across workflows that do not currently share a stable rendering contract.

---

## 3. Testable Predictions

| Claim in plan | Falsifiable prediction | Verification method | Pass threshold |
|---|---|---|---|
| “One shared packet engine exists and is used by plan-close, model-review, overview” | All three active entrypoints import the same shared library module(s) for source acquisition and provenance emission. | Static import check + integration tests. | 3/3 entrypoints share the same modules for the promised functions. |
| “No duplicated active-path helpers remain for file-range parsing” | There is exactly one production implementation of file-spec parsing in active codepaths. | Repo grep / AST check for `parse_file_spec`-equivalent logic. | 1 active implementation; wrappers allowed only if delegating. |
| “No duplicated constitutional preamble assembly remains” | Context preamble bytes are identical across all axes and all callsites for the same repo inputs. | Fixture repo with constitution + goals; compare outputs from all builders that use preamble. | Byte-identical preamble section across builders. |
| “Deterministic rendering from same inputs” | Running the same builder twice on unchanged sources produces identical packet bytes and identical content hash. | Repeat build in fixture repo. | 100% identical bytes/hash across 2+ runs. |
| “Packet manifests make provenance inspectable” | Modifying one source file changes only that block hash plus packet content hash; manifest lists the source path and truncation events. | Controlled single-file mutation test. | Exactly one source entry changes, plus packet aggregate hash. |
| “Overview live and batch share one packet-construction path” | For the same project/type/config, live and batch produce identical context/prompt payloads before dispatch. | Golden prompt test comparing builder outputs. | Byte-identical after normalizing temp-path metadata if any. |
| “Truncation is unified” | All truncation markers and manifest truncation entries come from shared code, not builder-specific strings. | Grep plus oversize-fixture tests. | 1 truncation marker implementation; 100% manifest coverage of truncation events. |
| “The shared engine reduces drift” | Diff in packet structure across builders decreases measurably relative to baseline. | Compare number of distinct section-label formats / truncation markers / provenance schemes before vs after. | At least 50% reduction in distinct packet-formatting conventions. |

### Claims that are currently too vague

1. **“build me a good context packet”**  
   Not testable. Needs measurable criteria: max size, provenance completeness, deterministic order, and allowed truncation rate.

2. **“many packet-producing skills”**  
   Not a present requirement unless there is an adoption forecast or at least two imminent follow-on users.

3. **“generalizes packet construction mechanics”**  
   Needs an explicit list of mechanics guaranteed by the shared layer and a list intentionally excluded.

### Missing tests that should be mandatory

- **Golden output compatibility tests** for:
  - `build_plan_close_context.py`
  - overview live prompt payload
  - overview batch prompt payload

- **Git fixture tests** covering:
  - renamed files
  - deleted files
  - untracked files
  - tracked-only mode
  - clean repo
  - commit-range mode vs worktree mode

- **File-spec parser tests** covering:
  - `path`
  - `path:7`
  - `path:7-12`
  - invalid ranges
  - out-of-range lines
  - filenames containing `:` if supported

- **Hash semantics tests**
  - content hash stable across reruns
  - manifest run metadata may differ without changing content hash

- **Budget tests**
  - per-block truncation
  - total packet truncation
  - token estimate generated before dispatch
  - fail-closed behavior when over profile limit

---

## 4. Constitutional Alignment (Quantified)

No constitution provided, so this is an internal-consistency scorecard.

| Dimension | Score / 100 | Rationale |
|---|---:|---|
| **Abstraction honesty** | 55 | The plan says “mechanics not semantics,” but proposed selectors already mix in semantic policy. |
| **Migration verifiability** | 68 | Phases and exit conditions exist, but compatibility criteria are not strict enough for overview and manifest semantics. |
| **Complexity discipline** | 50 | There is visible risk of introducing a generic AST before proving that renderers are truly shared. |
| **Workflow safety** | 46 | Overview migration is under-specified relative to current shell behavior and prompt format. |
| **Determinism/provenance rigor** | 60 | Good intent, but hash/timestamp contract is incomplete. |
| **Budget-awareness** | 44 | The plan identifies the problem but does not encode budget policy in the contract. |

### Weighted overall score: **54 / 100**

This is a **promising but under-specified refactor plan**.

### What would raise it above 75

1. Narrow the shared boundary to **source acquisition + provenance + preamble composition**.
2. Add a formal **artifact bundle contract** including token estimate and content hash.
3. Make **overview prompt-format preservation** a hard compatibility requirement.
4. Separate **content hash** from **run metadata**.
5. Add **golden compatibility fixtures** before any migration starts.

---

## 5. My Top 5 Recommendations (different from the originals)

### 1. Replace the “one canonical packet object model” goal with a narrower shared contract: **source fragments + provenance + preamble + budgets**
**What:**  
Do not force plan-close, model-review, and overview onto one `ContextPacket` AST initially. Instead standardize:
- `SourceFragment`
- `PreambleBundle`
- `ArtifactManifest`
- `BudgetPolicy`
- `BuildArtifact {context_path, manifest_path, token_estimate, content_hash}`

**Why:**  
The actual overlap across current systems is strongest in **input gathering and provenance**, not in output document syntax. Quantitatively, **2 of the 3 active paths do not share the same rendering format**:
- plan-close: markdown review packet
- model-review: concatenated review context with preamble
- overview: tagged prompt wrapper around repomix output

A universal AST now increases maintenance drag without proven renderer reuse.

**How to verify:**  
- After migration, each builder owns at most one thin renderer adapter.
- Shared modules contain zero builder-specific section names like “Plan-Close Review Packet”.
- Overview prompt payload remains byte-identical to current output in fixture tests.

---

### 2. Extract **shared preamble composition** as a first-class module independent of packet rendering
**What:**  
Add one canonical function for:
- constitution discovery
- goals discovery
- development-context injection
- ordered preamble assembly

**Why:**  
This is already a real duplication hotspot and an easy source of drift. It has low maintenance cost and high correctness value. The current plan names the problem but does not define the API. This is a more stable seam than a universal packet model.

**Quantitative justification:**  
It removes one whole class of duplicated policy logic from active review paths with near-zero blast radius. It also gives a clear measurable outcome: **1 preamble implementation instead of N**.

**How to verify:**  
- All builders that use constitutions/goals import the same preamble module.
- For a fixture repo with constitution + goals, the preamble bytes are identical across outputs.
- Grep shows exactly one production implementation of the development-context block.

---

### 3. Introduce a **strict compatibility harness** before migrating any live path
**What:**  
Capture golden fixtures for:
- plan-close output
- overview live prompt payload
- overview batch prompt payload
- model-review `--context-files` behavior

**Why:**  
The dominant cost here is not implementation; it is **supervision cost from silent behavior drift**. Without golden tests, “migration complete” is not falsifiable. Overview is especially vulnerable because shell behavior, repomix invocation, config parsing, token estimation, and freshness metadata are spread across scripts.

**Quantitative justification:**  
A 10-fixture compatibility suite will detect almost all blast-radius regressions at near-zero runtime cost, while preventing hard-to-observe prompt-shape drift.

**How to verify:**  
- Minimum 10 fixtures covering renamed/deleted/untracked/tracked-only/commit-range/range-spec cases.
- Before/after outputs must be byte-identical or differ only in approved metadata fields.
- CI rejects any prompt-shape drift without an explicit fixture update.

---

### 4. Define **content hash semantics** and **budget policy** before writing the shared engine
**What:**  
Specify:
- `content_hash`: hash of normalized rendered content only
- `source_hashes`: per-source normalized hashes
- `run_metadata`: timestamp, builder version, runtime info, excluded from content hash
- `BudgetPolicy`: byte limit, token estimate method, block truncation behavior, fail-open vs fail-closed

**Why:**  
Right now the plan asks for deterministic rendering, stable hashing, provenance, truncation, and dispatch-fit, but leaves the contract ambiguous. That ambiguity will force each builder to invent its own exceptions.

**Quantitative justification:**  
This eliminates an entire future class of flaky tests and cache misses. Success criterion becomes crisp:
- Same sources => same content hash
- Same sources, different time => same content hash, different run metadata
- Over-limit artifact => either deterministic truncation record or deterministic failure

**How to verify:**  
- Repeat-run test: same inputs produce identical `content_hash`.
- Timestamp-only difference changes no content hash.
- Oversize fixtures generate exactly recorded truncation events or deterministic hard failure.

---

### 5. Treat overview as a **format-preservation migration**, not as proof that Markdown packetization is universal
**What:**  
Move overview assembly to Python, but preserve the existing tagged prompt structure unless and until A/B tests prove a new format is neutral or better. Live and batch should call the same Python builder that emits:
- prompt/context file path
- manifest path
- token estimate
- content hash

**Why:**  
Overview has the highest workflow blast radius:
- repomix invocation
- config parsing
- include/exclude semantics
- token limit checks
- batch JSONL distribution
- freshness metadata and marker files

The plan currently underestimates this by implying overview is just “another packet.”

**Quantitative justification:**  
This path affects both single-run and batched generation. A format drift here multiplies supervision cost across all configured projects and overview types. It should be gated by exact prompt equivalence.

**How to verify:**  
- For the same project/type/conf, live and batch builder payloads match byte-for-byte.
- Token estimate from builder matches shell-side estimate within ±5%.
- Marker/update behavior remains unchanged in integration tests.
- No shell script contains direct prompt assembly after migration.

---

## 6. Where I'm Likely Wrong

1. **I may be overweighting exact prompt-format stability for overview.**  
   The models may handle a Markdown packet just as well as the current tagged structure, making my caution conservative.

2. **I may be underestimating future reuse of a universal packet AST.**  
   If many more skills are about to land and they really do want shared section/block rendering, the generic core could amortize well.

3. **I’m inferring some risks from partial code excerpts.**  
   There may already be hidden helpers for config parsing, budget policy, or manifest handling elsewhere in the repo.

4. **My scoring is heuristic, not empirical.**  
   The value rankings reflect maintenance-risk reasoning, not measured defect or churn data.

5. **I may be too strict about separating mechanics from semantics.**  
   In practice, repo-local constitution/goals discovery may be stable enough that centralizing it is worth the impurity.

6. **I may be recommending more production-grade invariants than this repo needs.**  
   The counterargument is that all code is AI-authored and dev time is cheap, so strong invariants are unusually affordable here. Still, I could be overshooting on formalization.