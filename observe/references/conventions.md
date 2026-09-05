# Observe: conventions

Apply [analysis safeguards](analysis-safeguards.md). This workflow may produce verified fixes within the requested scope; do not upgrade a consistency sweep into a full correctness audit.

**"Is this code consistent with itself?"** — the opposite cost profile to `audit`. Mechanical and
structural analysis covers 60-80% of consistency issues for $0; Flash classifies only the ambiguous
residue. `audit` asks *is this correct*; `conventions` asks *does this match the rest*. ~$0 vs $2-5,
5-10 min vs 15-30, different failure-mode coverage.

1. **Scope (git-driven, ~30s).** `git log --oneline --stat --no-merges -${DEPTH:-40}` plus a churn
   count (`--format="" --name-only | sort | uniq -c | sort -rn`). Identifies bulk-change commits
   (10+ files, highest drift risk), fix-wave commits ("Fix N failures" — residuals likely), and churn
   hotspots (repeatedly-changed files indicate instability).
2. **Structural checks (mechanical, ~3 min).** Deterministic per-axis scripts in
   [axes.md](axes.md). One block per check: `AXIS / CHECK / FOUND / SEVERITY / FILES`. Collect them
   all before dispatching anything.
3. **Classify the ambiguous residue (~1 min).** Default Flash (`fast_extract`) with the prompts in
   [flash-prompts.md](flash-prompts.md); **repo-grounded ambiguous cases → Composer** (`composer_review`),
   which reads the workspace and follows tight contracts better on structural "does this actually
   match?" questions (slower ~25s, higher contract fidelity). **One combined context file per axis**
   (`awk 'FNR==1{print "\n=== FILE: " FILENAME " ===\n"}1' …`), not multiple `-f` flags. Full files
   for modules <500 lines, first 80 lines for large ones.
4. **Verify (~2 min).** Flash hallucinates specifics. Before any finding enters the report: check
   file/function existence, read the actual lines for copy-paste claims, grep for claimed-missing
   functions, read both the model and the JSON for schema-mismatch claims. Measured: 5/6 specific
   findings correct; the one miss was a scan-script bug misread as a data bug. **Drop anything that
   fails verification.**
5. **Synthesize (~2 min).** Write `docs/audit/sweep-{date}/findings.md` per
   [findings-template.md](findings-template.md), grouped by tier — **CRITICAL** semantic data errors (wrong
   business/biological facts) · **HIGH** structural inconsistency blocking orchestration · **MEDIUM**
   pattern drift causing confusion or silent bug risk · **LOW** cosmetic tech debt. Each finding gets
   ID, tier, one-line what, the grep/script output as evidence, affected files, and a **concrete**
   fix (not "should be fixed"). End with a phased remediation plan; deferred items get explicit
   justification.

The seven axes (`config` · `conventions` · `duplication` · `registration` · `ir` · `lifecycle` ·
`paths`), what each checks, and whether it needs a model are in [axes.md](axes.md) alongside the
mechanical check scripts. Default is all axes; pass axis names as positional args to filter.
