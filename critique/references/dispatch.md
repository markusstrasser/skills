<!-- Dispatch contract. Load for model dispatch, closeout design review, or transport debugging. -->

# Dispatch Mechanics

The maintained authorities are `critique/scripts/model-review.py` (`AXES`, `PRESETS`, prompts and CLI), `critique/scripts/review_gate.py` (triage policy), and `shared/llm_dispatch.py` (`PROFILES`, providers, transport, retries and timeouts). Use their `--help` or declarations before changing a dispatch. Historical model/pricing claims are in [History](history.md).

## Choose the panel before dispatch

| Preset | Axes | Selection |
|---|---|---|
| `cross2` / `lens2` | `arch,correctness` | Triage recommendation for routine design |
| `cross4` / `lens4` | `arch,gaps,correctness,contracts` | Triage escalates for governance, multiple repos, ≥3 inconclusive findings, or contradictory anchors |
| `standard` | Same four axes as cross4 | CLI fallback without a manifest; also declared by the plan-close packet builder |
| `deep` | standard + `domain,mechanical` | Explicit structural/domain-dense review |
| `full` | deep + `alternatives` | Explicit review plus divergent alternatives; keep the two outputs separate |

The four standard axes have overlapping full-review mandates: their lenses differ, their territories do not. `arch` and `correctness` include folded gaps/contracts checks so cross2 remains a meaningful smaller panel. Read the manifest's `preset_reasons`; its explicit design axes override triage's recommendation.

Optional axes are outside the presets:

| Axis | Use and contract |
|---|---|
| `formal` | Math, Bayes/stats, proofs or formal invariants; `formal_review` profile at high effort |
| `composer` | Third lineage for a plan/design packet; neutral empty cwd, packet-only; never a duplicate diff review or closeout design axis |
| `claude` | Third-family review for a load-bearing subpart; `claude_review` subscription profile |
| `glm` | Explicit additional model family; metered profile |
| `grok` | Repo-grounded premise falsification; exact Cursor registry and repo canary required |

User-facing review normally requires a GPT-backed axis. Pair a lone opt-in cosigner with a GPT axis; `--allow-non-gpt` is an explicit specialized exception, not a default. Do not increase effort merely because a topic feels important.

## Packet and manifest contract

Use one context file per independently reviewed subpart. The packet builder emits a markdown file plus a sidecar `<packet>.manifest.json`, including `payload_hash` and `review_targets`:

- `diff_target`: code-review owns the git ref/range and files.
- `design_target`: critique owns the packet and design review axes.

For committed work, specify `--since <first-session-commit>` (inclusive through HEAD), `--base <old-ref> --head <new-ref>`, or repeated `--file` selections. A clean worktree is not evidence that the review scope is empty. See [Plan close](../lenses/plan-close-review.md) for range examples and [Context assembly](context-assembly.md) for scope content.

Run triage for the exact packet:

```bash
uv run python3 ${CLAUDE_SKILL_DIR}/scripts/review_gate.py triage \
  --repo "$(pwd)" --packet .model-review/packet.md --mode model

uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py \
  --dispatch-manifest .model-review/dispatch.json \
  --context .model-review/packet.md \
  --topic "$TOPIC" --project "$(pwd)" \
  --question "Find design flaws and false premises in the proposed caller migration."
```

`review_gate triage` accepts `--mode model|close|auto` and writes `schema_version: dispatch.v1`, layer ownership, blockers, preset/reasons and `dispatch_policy`. The policy includes `premise_scout`, `context_scope`, `budget_seconds`, `irreversible` and `cross_talk`; design-layer settings include `extract` and `verify`.

**Stop on blockers.** Triage exits 1 for blockers; an invalid budget below the resolved axis floor exits 2 without writing a new dispatch manifest. Dead references block closeout but are warnings for plan/design review. Close mode additionally requires an existing `verified-disposition.md`: use model mode for the initial design dispatch and close mode for the final readiness check. Do not send a blocked close manifest to the model and expect it to repair the blocker.

Pass `--dispatch-manifest` explicitly and keep it paired with the packet just triaged. Explicit CLI flags win over manifest settings. Auto-discovery only loads a manifest matching the packet hash or recorded path; an explicitly passed manifest is honored, so the caller remains responsible for its freshness. Re-triage after changing packet content.

The close gate rejects a `composer` design axis because the diff layer owns Composer via `/code-review`. Neither a broader preset nor another lineage licenses a second critique of the same diff.

## Repo scope and premise scout

`--context-scope` accepts only `repo` and `packet`.

| Option | Meaning |
|---|---|
| `--context-scope repo` | Scout may inspect the workspace; standalone script default |
| `--context-scope packet` | Self-contained packet; no repo scout |
| `--scout` / `--no-scout` | Enable/disable premise scout; standalone default on |
| `--fork` | Named design fork for the scout; defaults to topic |
| `--irreversible` | Block adjudication when an executed scout returns `conviction=low` |
| `--force-scout` | Explicitly proceed despite that low-conviction gate |

Triage can infer packet-only scope when the text has no repo premises, or take explicit `design_target.context_scope` and `premise_scout` fields. A skipped scout is not a low-conviction finding. A plan that depends on live callers, schemas, or join keys still needs repo-grounded evidence before packet-only criticism. The scout tests a named fork; it does not replace the inventory lanes of [Audit-plan](../lenses/repo-audit-plan-review.md).

## Transport, billing, and timeouts

Use the shared script for normal model/close design dispatch. The audit-plan lens documents its bounded two-critic exception. Do not replace a failed transport with an unrequested paid route.

- `claude_review` uses the current Opus profile through llmx `anthropic` with `auth=subscription` (claude-cli). Never switch to `anthropic-direct`/API by default. The profile locks overrides to `timeout`; API-only output knobs can force billing or fail.
- General and mechanical GPT profiles use subscription transport. Subscription extraction uses a strict JSON prompt and local parsing because that transport cannot enforce JSON Schema. Do not add API-only `max_tokens` or search controls.
- The Composer profile is usage-metered through Cursor. It has no reasoning-effort tiers and accepts only its supported timeout override; `max_tokens`, search and stream are not supported.
- The Grok axis pins `grok-4.7-high` (no `cursor-` prefix, verified live 2026-09-23) in a read-only repo workspace and fails closed on exact-registry or unrevealed HEAD-canary drift. Bare `grok-4.7` means xAI / Grok Build; llmx Cursor is packet-only. Probe the intended repo with `model-review.py --preflight --axes grok --project "$(pwd)"`.
- Plain `--preflight` performs import/routing checks plus a cached live subscription entitlement call; it makes no Grok call unless `--axes grok` is supplied.
- Fable is not a script axis. Historical `fable-subagent` instructions are superseded. A Fable-specific request needs the current [model guide](../../model-guide/SKILL.md) and its verified transport/billing procedure; do not treat an Agent model pin as proof of the served model.

The executor derives its internal collection wait from the longest selected profile. Set the outer tool timeout above it: `660000` ms for standard, `1230000` ms with Grok, `3630000` ms with Opus Max. When the tool cannot wait that long, launch asynchronously and inspect the running task/output. A zero-byte artifact or timeout is transport failure, not reviewer evidence.

There is **no wall-clock budget by default**. Use `--budget-seconds SEC` only for a requested time box. It covers parallel axis dispatch plus extraction; the premise scout has a separate fixed timeout. The full selected profile must fit in the remaining budget: calls are skipped, never truncated. A cap below the largest resolved timeout is a triage configuration error. Dispatch records `budget_exhausted` / `budget_insufficient_for_profile` and partial or `incomplete_all_skipped` receipts (exit 2); do not report that as a completed review.

Never shell-redirect review artifacts or pipe model-review output through `tail`. The script writes artifacts directly. Debug using [Known issues](known-issues.md), shared dispatch metadata, and the recorded axis errors; do not silently change the model.

## Questions, context, and extraction

- `--context` is the main narrative file; repeated `--context-file` is additive and accepts `file.py`, `file.py:100-150`, or `file.py:100`.
- `--questions FILE` takes JSON mapping axis names to specific questions; unmapped axes use `--question`.
- Ask a concrete question about the target. Bare verbs such as `--question "close"`, `"review"`, or `"verify"` trigger a warning and generic replacement template.
- The script owns default prompts. For manual customization, consult [Prompts](prompts.md) and only the relevant model-guide section. The historical formatting advice is XML document sections for GPT and query/critical constraints last for Gemini.
- `--charter-anchor` injects the full goals/governance charter only for an explicitly selected compliance review. Otherwise curate current, relevant constraints as described in [Context assembly](context-assembly.md).
- `--extract` defaults on. `--verify` implies extraction and checks cited paths, symbols, line anchors and local corroboration. Triage supplies extraction/verification settings for design review; explicit flags override them.
- Cross-repo verification needs `--sibling-roots /path/to/repo-a /path/to/repo-b` so sibling anchors are actually resolved. A missing root is not evidence a claim is hallucinated.
- Optional `--cross-talk` runs structure lenses first and injects `structural-assumptions.json` into mechanism passes for cross2/cross4; ordinary dispatch remains independent and parallel.
- Extraction tags unsourced numeric thresholds `[UNCALIBRATED]`; derive or source them before use.

## Artifacts and completion

The script writes `shared-context.md`, `shared-context.manifest.json`, `<axis>-output.md`, `findings.json`, `disposition.md`, `coverage.json`, `execution-receipt.json`, and `verified-disposition.md` when verification runs.

`coverage.json` is the machine-readable contract with `schema_version`, `artifacts`, `context_packet`, `dispatch`, `extraction`, and `verification`. Inspect actual packet provenance/drops, axis/model coverage and extraction/verification counts before completion. Read every axis output; no finding disappears because it falls below a summary cutoff.

`verified-disposition.md` establishes anchors and local corroboration, not semantic truth. Source inspection or execution must establish whether the claimed behavior is real. Use [Verification](../lenses/verification.md).

After extraction/verification, `review_gate.py rank` writes `orchestrator-top.json`, `anchor-contradictions.json`, and an escalation recommendation when applicable. The top eight are a reading order, not permission to omit confirmed findings. Contradictory anchors mean cross-family opposite stances on an overlapping topic; different issues in the same file do not qualify. Follow the recommendation on the same packet, then disposition every item.

Closeout's [plan-close lens](../lenses/plan-close-review.md) owns the inconclusive pass, integration audit before the closeout commit, and outcome links after fix commits. `linked_anchor` is evidence-grade; file-touch-only `linked_file` is a weak candidate.
