#!/usr/bin/env python3
"""route.py — the outer-loop autonomy router (the deterministic spine).

Given a classified action + its context, decide the autonomy level. This is CODE, not LLM
judgment, on purpose: the protected-verifier-boundary and fail-closed invariants are RSI safety
properties (a loop that can silently auto-accept after editing its own gate p-hacks itself —
PACE arXiv:2606.08106, 30-42% false commits), so they must not be able to drift with prompt wording.

The split: the LLM (the skill's policy) CLASSIFIES the action — is it reversible? what blast radius?
is it a discovery/model-class move? what did the gate emit? The router MAPS that classification to
an autonomy level. Classification is the irreducible judgment; routing is structure that transfers.

The six rules (in priority order — earlier wins):
  1. PROTECTED action            → HUMAN_REQUIRED   (gate self-edit, model-class change, GOALS/constitution)
  2. discovery / irreversible / non-local blast → HUMAN_REQUIRED  (the human-gate boundary)
  3. gate ERROR / missing required verdict → FAIL_CLOSED  (consumed gate: never accept on a failed/absent gate)
  4. accept with an ERROR/absent verdict → FAIL_CLOSED, with any other non-accept → REJECT
                                          (the gate is consumed; an un-judged accept is never a reject)
  5. budget-gated action          → BUDGETED/HUMAN       (rate-limited resource; spend only within budget)
  6. clean + reversible + local + accept-verdict → UNATTENDED  (the auto-ratchet); else by regime.

Stdlib only. Importable (the trace-equivalence harness drives it) and runnable as a CLI probe.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass, field

# ── Autonomy levels (the decision space) ──────────────────────────────────────────────────────
UNATTENDED = "unattended"          # the loop does it + records it, no human
ATTENDED = "attended"              # the loop does it in an open/driven session, human in the room
BUDGETED = "budgeted"              # allowed, but spends a rate-limited resource — only if budget remains
HUMAN_REQUIRED = "human_required"  # prepare the decision (cross-lab critique → human_queue), never greenlight
REJECT = "reject"                  # gate said no — no ratchet, record for dedup
FAIL_CLOSED = "fail_closed"        # gate errored / verdict absent where required — quarantine, never accept

# ── The protected verifier boundary — these actions are NEVER unattended, in any regime ──────────
# The loop must not be the authority that greenlights changing what counts as success, the model
# class, or the goals. This set is hard-coded structure, not contract data: a repo's LOOP.md can
# ADD protected actions but cannot remove these.
PROTECTED_ACTIONS = frozenset({
    "modify_the_gate",        # editing the accept-gate itself — the canonical RSI p-hack hole
    "model_class_change",     # paradigm / architecture / model-class swap (hutter: discovery tier)
    "update_goals",           # GOALS.md / constitution
})

# Verdicts that authorize a ratchet. A repo's contract may override via accept_verdicts, but the
# default accept-class is these three (matches hutter eval.py).
DEFAULT_ACCEPT_VERDICTS = frozenset({"ACCEPT", "BASELINE", "GATE_PASS"})
ERROR_VERDICTS = frozenset({"ERROR"})

CLEAN_REGIMES = frozenset({"clean-cheap", "clean-expensive"})
ALL_REGIMES = frozenset({"clean-cheap", "clean-expensive", "partial", "principal", "mixed"})


@dataclass
class Context:
    """Everything the router needs. The skill's policy fills this from the contract + its judgment."""
    regime: str                              # one of ALL_REGIMES (the picked item's regime, not the repo's)
    reversible: bool = True
    blast_radius: str = "local"              # "local" | "shared" | "irreversible"
    is_discovery: bool = False               # model-class / paradigm move flagged for the human gate
    gate_verdict: str | None = None          # the STRUCTURED verdict the accept_gate emitted (None = not run)
    gate_required: bool = True               # does this action require a fresh gate verdict to proceed?
    accept_verdicts: frozenset = field(default_factory=lambda: DEFAULT_ACCEPT_VERDICTS)
    budget_remaining: float | None = None    # rate-limited resource left (None = not budgeted / infinite)
    extra_protected: frozenset = field(default_factory=frozenset)  # contract-added protected actions

    def __post_init__(self):
        if self.regime not in ALL_REGIMES:
            raise ValueError(f"unknown regime {self.regime!r}; expected one of {sorted(ALL_REGIMES)}")
        if self.blast_radius not in ("local", "shared", "irreversible"):
            raise ValueError(f"unknown blast_radius {self.blast_radius!r}")


def route(action: str, ctx: Context) -> str:
    """Map a classified action + context → an autonomy level. Pure function. See module docstring."""
    protected = PROTECTED_ACTIONS | ctx.extra_protected

    # Rule 1 — protected verifier boundary. Highest priority; nothing overrides it.
    if action in protected:
        return HUMAN_REQUIRED

    # Rule 2 — the human-gate boundary: discovery moves, irreversible, or non-local blast.
    if ctx.is_discovery or ctx.blast_radius == "irreversible" or not ctx.reversible:
        return HUMAN_REQUIRED
    if ctx.blast_radius == "shared":
        return HUMAN_REQUIRED

    # Rule 3 — consumed gate, fail-closed. A gate that errored, or is absent where required, must
    # never resolve to accept. This is the intel/genomics failure inverted: the verdict GATES.
    if ctx.gate_required:
        if ctx.gate_verdict is None:
            return FAIL_CLOSED
        if ctx.gate_verdict in ERROR_VERDICTS:
            return FAIL_CLOSED

    # Rule 4 — acceptance is decided by the structured verdict, not by the proposer's say-so.
    if action == "accept_candidate":
        # An accept with no CLEAN verdict is never a REJECT — even if the caller set
        # gate_required=False. A gate that errored or produced no verdict has not JUDGED the
        # candidate, so it must not enter the reject/dead-end dedup bucket (hutter's own rule:
        # "a crash is not a gate-measured death — asserting it forecloses families the gate never
        # judged", ledger_schema.sql v_dead_ends). Fail closed, unconditionally, for accepts.
        if ctx.gate_verdict is None or ctx.gate_verdict in ERROR_VERDICTS:
            return FAIL_CLOSED
        if ctx.gate_verdict not in ctx.accept_verdicts:
            return REJECT
        # accept-verdict present → autonomy by regime:
        if ctx.regime == "principal":
            return HUMAN_REQUIRED          # the human IS the gate (taste) — amplify, don't auto-accept
        if ctx.regime == "clean-expensive" and ctx.budget_remaining is not None:
            return UNATTENDED if ctx.budget_remaining > 0 else HUMAN_REQUIRED
        if ctx.regime in CLEAN_REGIMES:
            return UNATTENDED              # the auto-ratchet (reversible + local already checked)
        # partial: per-action unattended IS allowed when reversible + local (already true here);
        # otherwise the broad default is attended.
        # A bare "mixed" regime reaching an accept means the policy did not stamp the picked item's
        # own regime on the action (mixed loops route per-item) — fall back to the CONSERVATIVE
        # attended (human in the room), never to unattended.
        return UNATTENDED if ctx.regime == "partial" else ATTENDED

    # Rule 5 — budget-gated actions (spend a rate-limited resource, e.g. arc-agi ground-truth submit).
    if ctx.budget_remaining is not None:
        return BUDGETED if ctx.budget_remaining > 0 else HUMAN_REQUIRED

    # Rule 6 — the default for low-stakes loop bookkeeping (enqueue idea, mark dead-end, run a
    # local candidate): reversible + local → unattended in every non-principal regime.
    if ctx.regime == "principal":
        return HUMAN_REQUIRED
    return UNATTENDED


def _cli() -> int:
    ap = argparse.ArgumentParser(description="probe the outer-loop autonomy router for one action")
    ap.add_argument("action")
    ap.add_argument("--regime", default="clean-cheap")
    ap.add_argument("--reversible", default="true")
    ap.add_argument("--blast-radius", default="local")
    ap.add_argument("--discovery", action="store_true")
    ap.add_argument("--gate-verdict", default=None)
    ap.add_argument("--no-gate-required", action="store_true")
    ap.add_argument("--budget-remaining", type=float, default=None)
    a = ap.parse_args()
    ctx = Context(
        regime=a.regime,
        reversible=a.reversible.lower() not in ("false", "0", "no"),
        blast_radius=a.blast_radius,
        is_discovery=a.discovery,
        gate_verdict=a.gate_verdict,
        gate_required=not a.no_gate_required,
        budget_remaining=a.budget_remaining,
    )
    decision = route(a.action, ctx)
    print(json.dumps({"action": a.action, "decision": decision}))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
