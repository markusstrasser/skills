# Modal — version baselines and platform changelog

> Moved verbatim from modal/SKILL.md (2026-10-21, context-cost reduction). SKILL.md keeps a short current-baseline summary; dated platform notes, the historical 1.5.2 baseline and the 1.5.1/1.5.2 feature tables live here. Append new dated entries at the top of the dated list.

## Current genomics baseline: Modal 1.5.5, parity required

**2026-09-08 correction:** genomics requires `modal[api-proxy-support]>=1.5.5,<1.6`
and locks 1.5.5. Align the shell-global CLI with
`uv tool install 'modal[api-proxy-support]==1.5.5' --force`, then run the parity
checks below. Preserve the proxy extra. This supersedes the 1.5.2 genomics pin
and installation example in the historical baseline below.

The supported update repairs `ModalChannel._connected`: a closing Connection is
unusable even before its handler receives connection-lost notification. Real
library controls fail on 1.5.2 and pass on 1.5.5. Prefer that fix to custom client
renewal; `_Client._close` can still clear another cached client. This host SDK
change leaves the declared genomics toolchain identities unchanged. It does not
establish a fix for Volume block-HTTP 404s or replace live rehearsal evidence.

## Platform note 2026-10-12: faster grep on Volumes v2

Modal prefetches metadata and content for small files on **Volumes v2**: grep from a
Sandbox runs ~10x faster cold and ~6x warm. It does nothing for a v1 volume.
`genomics-data` is v1 (`modal.Volume.from_name("genomics-data").hydrate()._get_metadata().version`
returned 1 on 2026-10-14), so genomics receipt/manifest crawls see no change. Weigh it
only if a v2 migration is ever proposed for small-file-heavy reads.

## Debugging DX update (verified 2026-10-18)

- **Dashboard log search:** [October 16 update](https://modal.com/changelog/logs-search-v2)
  supports exclusions (`-function:my_func`) and grouped call IDs
  (`function_call_id:(fc-123 OR fc-456)`). Use actual recorded identities. These
  are dashboard queries; verify installed CLI help before assuming flag parity.
- **Expose the right channel:** app logs capture stdout/stderr, while a project's
  structured logger may write only Volume files. In genomics, read that narrative
  with `just stage-log <stage>`; `just stage-progress` already identifies calls.
  Prefer extending existing status output with app links, queries and log commands.
  Label app links as stdout/stderr; call-ID filters are copyable dashboard queries.
  Logs/profiling diagnose execution; terminal receipts still decide completion.
- **Live hangs:** Modal offers [live container profiling and debug shells](https://modal.com/docs/guide/developing-debugging#live-container-profiling).
  Distinguish attaching to a running container from launching a fresh image shell.
- **Feedback before new infrastructure:** use an existing authenticated collector
  to expose published attempt results while a run is active, retaining explicit
  partial coverage, immutable artifact versions and final completion validation.
  Trace the producer's publication checkpoint first: prefetch cannot expose unpublished
  results, and ordered waits may delay publication independently of host collection.
  Genomics' pending implementation is P3.9 in its post-ship plan; it is not shipped.
- **Volume v2 scope:** the advertised grep gains concern mounted small-file reads.
  They do not establish faster SDK downloads or whole-suite execution. The
  [current docs](https://modal.com/docs/guide/volumes#volumes-v2-overview) still label
  v2 Beta and advise against mission-critical data; traversal can also be slower.
  Consider a measured rebuildable-workspace experiment separately from production.

## Platform changelog 2026-08-14 → 09-17 (reviewed 2026-09-29)

Dashboard/product changes only; no SDK release. PyPI stable is still 1.5.5
(1.5.6 exists only as `.dev` builds), and `modal changelog --newer` is empty.
The genomics pin stays unchanged.

| Change | Relevance here |
|---|---|
| Usage page: network egress **per app** (09-17) | Use it to attribute egress cost (B2 publish, `volume get` relays) to a specific app before guessing. It is a dashboard view; no SDK/billing-report field has been verified. |
| Container Metrics: custom-range zoom (09-11), synced time cursor (09-10) | Makes it easier to line up memory/CPU charts across stages when a worker dies. It still does not show worker progress; see the worker-written-surface rule. |
| Container inputs view: filter by date/status, shareable URLs (09-02) | Quick way to find failed/preempted inputs for one app. Receipts remain the authority. |
| Sandboxes: Exit Reasons chart separating memory-limit OOM from memory-manager OOM (08-26); per-Sandbox CPU/mem/pressure charts (09-02); Sidecars public alpha (08-28); `MODAL_SANDBOX_V2=1` opt-in to V2 (08-14) | Genomics uses `modal.Sandbox` only in the image-proof scripts (`genome_kernel_*_proof.py`, `modal_probe.py`), so V2 has not been tested there. Before flipping V2 globally, run one image proof with the variable set. Stages are Functions, so none of these charts cover them. |
| Unauthenticated web endpoint controls (filter, audit, per-env block) (09-15) | Genomics has no web endpoints. This matters only if an `@app.server` status endpoint ships later. |
| RBAC user groups/SCIM (09-15), SSO XML metadata (09-14), configurable default roles in Restricted Envs (08-19), per-app/env Slack notification routing (09-02), Proxy region choice (08-31), "Last deployed by" filter (08-19), usage-limit/threshold-billing UI redesign (08-27) | Workspace admin/UI only; no pipeline action. |

## Historical 1.5.2 baseline (genomics pin superseded above)

**Shell-global CLI** is a `uv tool` install (`~/.local/bin/modal` →
`uv tool install 'modal==1.5.2'`). That is what **arc-agi** uses: it does
**not** pin Modal in `pyproject.toml`; scripts are launched with `modal run`
(the tool env), and local `import modal` is guarded so project-venv
`--help` / tests still work.

**Genomics** pins the project venv: `pyproject.toml` has
`modal>=1.5.1,<1.6`, `uv.lock` resolves `modal==1.5.2`, and
`uv run python3 scripts/modal_version_parity.py` must pass. Bumping the
global tool without refreshing genomics (or vice versa) reopens C4.

Verify both planes:

```bash
modal --version
# genomics only:
uv run python3 -m modal --version
uv run python3 scripts/modal_version_parity.py
```

Modal 1.5.x normalizes CLI JSON keys differently from the old 1.4.x output.
Consumers should use the repo's normalizer where one exists and should still
avoid raw `.get("App ID")` / `.get("app_id")` parsing.

## Modal 1.5.2 Features (2026-07-10)

Ops/DX patch — not an architecture power-up. Prefer unfinished **1.5.1**
adoption (billing → named images) over chasing these.

| Feature | Use when | Do not use for |
|---|---|---|
| `modal.Workspace.settings.list()` / `.set()` · `modal workspace settings …` | Read/set workspace-level knobs. As of 1.5.2 the live keys are `default-environment` and `image-builder-version` only (manager/owner). | Budget/spend caps, admission control, or stage readiness — **budget is not exposed here**. |
| `modal.types` | Type-annotate wrappers around Modal return dataclasses. | Constructing these types in user code (they are API return shapes). |
| `Function.with_options(..., routing_region=…)` | Invoke-time regional routing. Best fit for **arc-agi** GPU train/farm/serve paths that already use `with_options`. | Substituting for capacity/budget diagnosis; still check spend vs cap first. |
| `modal container stop --graceful` | Drain: stop fetching new inputs, finish in-flight Function inputs (not cancel+reschedule). Useful for long train steps or served endpoints. | App-wide halt (`modal app stop`); budget kill; Sandbox stop. Graceful is Function/Server containers only. |
| `modal container logs` includes startup | Debug cold-start / import crash-loops (vLLM serve, detached import failures). | Liveness or completion — still join receipts / `task_count`. |
| `Workspace.members.list()` role `user` → `member` | Match UI/docs for lowest-privilege role when auditing membership. | Pipeline readiness. Update any code that compared role == `"user"`. |
| `Sandbox.reload_volumes(timeout=…)` (default 55s) | Blocking reload until volumes are current; raises `modal.exception.TimeoutError` on stall. Narrow win for probe/canary sandboxes. | Stage hot path — that remains `vol.reload()` (still C2/C9; no per-call timeout on Volume.reload). |

**Arc-agi lean-in (optional):** `--graceful` drain, startup logs, `routing_region` on existing `with_options` call sites.
**Genomics lean-in (optional):** settings only if you need image-builder/default-env automation; Sandbox reload timeout on probe paths. Do not treat settings as budget API.

## Modal 1.5.1 Features: How Genomics Should Use Them

Verified against `modal changelog --since 1.4.9` on 2026-06-30. Still the
adoption priority over 1.5.2.

| Feature | Use in genomics | Do not use for |
|---|---|---|
| `modal.Workspace.billing.report()` / `modal.Environment.billing.report()` and `modal billing report --show-resources` | Stage telemetry and budget admission. Join rows by `run_id`, `stage`, `attempt_id`; keep CPU, memory, and GPU resource breakdown separate from planning projections. Environment-scoped reports are useful if genomics gets its own Modal environment. | Completion, liveness, or substituting missing billing with `$0`. |
| Named Images: `Image.publish()`, `Image.from_name()` | Canonical stage images (`genomics/base`, `genomics/deepvariant`, etc.) so many one-stage Apps stop rebuilding divergent images. Pin names/tags in stage metadata and fail loud on missing image. | Implicit build fallback. `Image.from_name()` is a lookup, not a builder. |
| `Image.from_id(...).publish()` | Promote a known-good build ID after a probe/canary without rebuilding. Useful for overnight stage-image rollouts. | Re-publishing unverified images or hiding changed dependencies behind the same tag. |
| Version-pinned `Function.from_name(..., version=...)` / `Cls.from_name(..., version=...)` | Deployed helper functions or a future long-lived controller can call a consistent deployed version during one run. Store the version in the run manifest. | Ephemeral one-stage `just dispatch` apps unless they are first deployed and versioned. |
| `@app.server()` / `modal.Server` | Low-latency HTTP diagnostics or a future status/control endpoint with proxy-token auth. Could serve read-only progress/status without cold-starting a CLI. | Batch WGS stages. Stages remain `@app.function`/`@app.cls` jobs with receipts. |
| `modal endpoint` | Production LLM inference endpoints, if a future interpretation model needs a served endpoint. | The pipeline controller itself; do not add an endpoint just to avoid receipts. |
| Proxy tokens + `modal curl` | Authenticated checks against future Modal Servers/Endpoints without manually handling headers. Keep tokens out of logs. | Stage identity or sample authorization inside batch jobs. |
| Sandbox `outbound_domain_allowlist=[...]` | Network-restricted probes, external-tool canaries, and testsample/fake-DAG sandboxes where only declared domains should be reachable. | Normal WGS stages that need broad DB/reference access unless the allowlist is complete. |
| `sandbox.filesystem.watch()` | Fast feedback from sandbox-based experiments: watch log/result files without polling whole directories. | Volume receipt completion; still write terminal receipts and payload summaries. |
| Sandbox connect tokens scoped by `port=` | Safer interactive debugging of a known service port in a Sandbox. | Long-running production control-plane auth. |
| `modal app rollback --strategy rolling|recreate` | Deployed diagnostic/status services. Prefer `recreate` only when stale containers are unsafe. | Ephemeral per-stage apps; stop/reconcile via run identity instead. |
| `modal workspace members` | Operator/audit check for who can see or mutate the workspace. | Pipeline readiness or sample completion. |

Adoption order for this repo:

1. **Billing first:** migrate `stage-telemetry` internals to the 1.5.1
   Workspace/Environment billing APIs or `modal billing report --show-resources`,
   then keep projections visibly separate.
2. **Named images second:** publish canonical, tagged images for high-churn stage
   families and make stage specs reference tags explicitly.
3. **Version-pinned functions third:** only for deployed helper/controller
   surfaces where a run needs one stable function version.
4. **Servers/endpoints only if needed:** useful for a read-only status plane, not
   for replacing batch-stage receipts.
