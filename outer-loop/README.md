# outer-loop — executable decision record (NOT a loaded skill)

This directory is **not an invocable skill** (no `SKILL.md`, not symlinked into `~/.claude/skills/`).
It is the **executable record** behind the RSI outer-loop decision arc.

> Full reasoning: `agent-infra/decisions/2026-06-13-rsi-outer-loop-skill.md` (FINDINGS 1–5).

## What happened (the short version)

The arc set out to extract hutter's RSI Dreamer loop into ONE shared, regime-parameterized
"outer-loop" skill across hutter / intel / genomics / science / agent-infra. Reading the ground truth
collapsed that premise in five findings:

- **F4** — exactly ONE standalone autonomous loop exists (hutter, clean verifier). intel/genomics/
  science are **partial-verifier** systems with no standalone auto-loop; the verifier regime *determines*
  whether a standalone loop is even possible.
- **F5** — the two surviving "consumers" (hutter, `/improve maintain`) **already implement the pattern
  in their own prose** and **nothing loads this directory** (grep-verified, zero callers). The extraction
  was the *union* of three loops' rules; the genuine *intersection* is a 2-liner both already have. By
  the project's own proven-common-≥2 bar, the shared skill was **not earned**, and F4 left it with no
  taker. → **Decision: do not deploy the platform.** Ship the knowledge, keep the executable spec.

## What's kept here, and why

| Path | Why kept |
|------|----------|
| `scripts/route.py` | The deterministic autonomy router — the one novel + correct piece. Encodes the **partial-accept fix**: never auto-ratchet on a noisy gate (a partial verdict routes to *attended*, not the clean-regime unattended auto-commit). Pure stdlib; importable + a CLI probe. |
| `tests/test_route_trace_equivalence.py` | Proves `route.py` reproduces hutter's clean-cheap routing — 10/10. |
| `tests/test_route_partial_regime.py` | Proves the partial-accept fix against science's contract — 8/8. |
| `references/examples/hutter-LOOP.md` | Test fixture — what a **clean-cheap** filled contract looks like. |
| `references/examples/science-LOOP.md` | Test fixture — what a **partial-regime** filled contract looks like. |

Run the record: `cd ~/Projects/skills && uv run python3 outer-loop/tests/test_route_trace_equivalence.py`
(and `…/test_route_partial_regime.py`), or `uv run pytest outer-loop/tests`.

## What was pruned (over-extraction — see ADR)

`SKILL.md` (generalization restating the two loops' prose), `references/ledger-schema.sql` (hutter's
`ledger.db` views are richer; science is git-native; no shared SQL consumer), `references/loop-contract.md`
(typed-schema design — captured in the ADR), `scripts/lint_ledger_conformance.py` (zero callers).

## If you're tempted to revive the shared skill

The resurrection trigger is a **real second clean-verifier standalone loop** (a new repo that genuinely
needs a propose→gate→ratchet loop and would *load* this) — not "it might be reusable." Re-read F4/F5
first; the demand did not exist as of 2026-06-13.
