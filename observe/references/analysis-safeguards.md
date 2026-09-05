# Observe analysis safeguards

Load for codebase audits, discovery, prospective improvement, or longitudinal findings. These checks apply to claims being triaged, not to unrelated small tasks.

**Analysis.** "Top N" triage — every APPLY finding gets implemented, don't self-select a subset ·
batch apply without verification — each change is verified independently · trusting model file paths
(~15% hallucinated) · trusting "this function is never called" — grep it, dynamic dispatch is
invisible to static analysis · rubber-stamping model findings as triage — you hold context the models
don't (vetoed decisions, deliberate exclusions, runtime environment, dead-code status), so cross-check
every finding before presenting a disposition · sending the whole codebase to Flash — it is a
classifier, not a reviewer (focused slices, 10-20 file heads per axis, <50KB) · skipping the
mechanical phase, which catches 60-70% of consistency findings for $0 with zero hallucination risk.

**Design and scope.** Collapsing the general to one axis — the biggest gap is often *better*, *more*,
or *unnecessary*, not *faster* · error-driven blindness — only learning from corrections leaves
success-far-short-of-possible invisible · history-bound blindness — you cannot retro your way to an
unused tool, model, or idea · measurement without consumption — telemetry collected and never acted
on · plan-without-pilot — quoting an improvement you never measured · over-scaffolding — no
monitoring, CI/CD, auth, or enterprise patterns on personal projects · omitting project context from
model prompts — without CLAUDE.md purpose + recent git history, models flag theoretical bugs that
cannot happen here · maintaining a manual concept registry — infer from git history and
improvement-log, manual upkeep rots · counting dev effort as cost — filter by *maintenance* burden ·
fabricating instances — every failure class cites a commit hash or an improvement-log entry.

**Default migration stance:** unless the user names a live external boundary, assume a proposed
improvement is a breaking refactor with full migration. Prefer replacing the old path cleanly over
wrappers, adapters, or dual paths; treat compatibility scaffolding as a smell to verify, not a
default to preserve; spend `discover` idea budget on cleaner end states, not phased coexistence.

## Known limitations

**Dynamic dispatch** — `getattr()`, `importlib.import_module()`, CLI `entry_points` are invisible to
static analysis. **No tests** — verification degrades to syntax and import checks only. **Monorepos**
— >500K tokens need splitting, run per package. **Semantic failures are unhookable** — cross-model
review is the only mitigation.
