# Observe known issues

<!-- Append-only. Record new evidence or corrections below; preserve earlier entries. -->

- **[2026-09-05] Source-contract audit: prep helpers converted extractor faults to empty output and drift discarded Codex-only evidence. Producers now return success for healthy empty windows; consumers propagate source errors. Regression checks cover empty versus missing/broken stores and source-presence combinations.**

- **[2026-09-05] Maintain health-status correction:** the SWEEP examples piped health producers through display filters and used `|| true`, hiding failed checks. They now run as separate full-output calls with their own statuses; listing output is checked for reported failures and `DUE` work before a green/noop verdict.
- **[2026-09-05] Maintain authority and finish-order correction:** “Reversible + single-project” was broader than self-directed agent-infra-local authority, and the workflow stopped before mandatory logging while also demanding Top-N on every noop. Self-directed work now uses the canonical local/one-clear-approach boundary, existing user approval persists, and one stop follows logging/reporting. Unchanged green noops do not repeat priorities.
- **[2026-09-05] Superseded promotion exception:** “Novel high-severity may promote immediately” contradicted the recurrence requirement in agent-infra's Self-Improvement Governance and the default path through `observe_gates.py` → `promote_check()` → `verdict_for_candidate()`. The prose exception is removed; severity grants no gate bypass. The owned invocation also puts global `--artifact-root` before the `preflight` subcommand, matching argparse.
