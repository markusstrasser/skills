#!/usr/bin/env python3
"""Trace-equivalence proof: outer-loop skill + hutter's LOOP.md contract reproduces the
OUTER-LOOP.md Dreamer's safety-critical autonomy decisions across 8 scenarios.

What this proves DETERMINISTICALLY (the router, driven by the real hutter contract):
  - every safety-critical decision routes the same as the OUTER-LOOP oracle: an ACCEPT verdict
    ratchets unattended; a REJECT does not ratchet; a discovery/model-class move is human-gated even
    with an ACCEPT verdict; a gate ERROR or an absent verdict fails closed (never accepts).
  - routine bookkeeping (refill, triage reads, restart-enqueue) stays unattended — no spurious human
    gate that would stall the loop.

What this does NOT prove (explicitly out of scope — policy, not routing; covered by SKILL.md text
fidelity, not this test): the triage ORDER (diagnose before refill), WHICH divergence move to fire,
WHICH parent to restart from, whether a proposal is buildable. Those are irreducible LLM judgment.

`oracle_source` labels each row honestly:
  OUTER-LOOP / eval.py  → behavioural equivalence with the running loop (a regression would be a bug).
  design                → NEW robustness the outer loop adds where the old loop had no defined
                          behaviour (it would crash); strictly better, no behaviour to regress.

Run directly (`uv run python3 tests/test_route_trace_equivalence.py`) for the table, or via pytest.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from route import (  # noqa: E402
    Context, route,
    UNATTENDED, REJECT, HUMAN_REQUIRED, FAIL_CLOSED,
)


def _load_contract() -> dict:
    """Load the hutter example contract's frontmatter — the test is driven by the REAL contract,
    not by values re-typed here (that is what makes it trace-equivalence, not a route() unit test)."""
    import yaml
    text = (ROOT / "references" / "examples" / "hutter-LOOP.md").read_text()
    body = text.lstrip()[3:]
    block = body[: body.find("\n---")]
    return yaml.safe_load(block)


CONTRACT = _load_contract()
REGIME = CONTRACT["verifier"]["regime"]                          # clean-cheap
ACCEPT_VERDICTS = frozenset(CONTRACT["accept_gate"]["accept_verdicts"])  # {ACCEPT,BASELINE,GATE_PASS}


def _ctx(**kw) -> Context:
    kw.setdefault("regime", REGIME)
    kw.setdefault("accept_verdicts", ACCEPT_VERDICTS)
    return Context(**kw)


# (name, oracle_source, action, ctx, expected_decision, why)
SCENARIOS = [
    ("1 idea-starved", "OUTER-LOOP §on_each_fire/4", "enqueue_idea",
     _ctx(gate_required=False),
     UNATTENDED, "Dreamer refills queue/ unattended once triage 1-3 are clean"),

    ("2 grinder-stalled", "OUTER-LOOP triage", "run_candidate",
     _ctx(gate_required=False),
     UNATTENDED, "a STALL triggers unattended diagnosis (gate-honesty / slice-size reads), never an auto-accept"),

    ("3 candidate-accepted", "eval.py:357 ACCEPT", "accept_candidate",
     _ctx(gate_verdict="ACCEPT"),
     UNATTENDED, "clean + reversible + local + ACCEPT verdict → auto-ratchet"),

    ("4 candidate-rejected", "eval.py:360 REJECT", "accept_candidate",
     _ctx(gate_verdict="REJECT"),
     REJECT, "non-accept verdict → no ratchet (the gate is consumed, not the proposer's say-so)"),

    ("5 human-gated-discovery", "OUTER-LOOP discovery gate", "model_class_change",
     _ctx(gate_required=False),
     HUMAN_REQUIRED, "model-class move is PROTECTED → human; Dreamer prepares cross-lab critique, never greenlights"),

    ("5b discovery accept-attempt", "OUTER-LOOP discovery gate", "accept_candidate",
     _ctx(gate_verdict="ACCEPT", is_discovery=True),
     HUMAN_REQUIRED, "even an ACCEPT verdict on a discovery move stays human-gated (rule 2 beats rule 6)"),

    ("6 dead-end-restart", "OUTER-LOOP move 9", "enqueue_idea",
     _ctx(gate_required=False),
     UNATTENDED, "restart-from-fertile-parent enqueues an arc unattended (parent SELECTION is policy; routing is unattended)"),

    ("7 gate-command-failure", "eval.py:337 ERROR", "accept_candidate",
     _ctx(gate_verdict="ERROR"),
     FAIL_CLOSED, "gate ERROR → never accept; eval.py records ERROR, never a valid S — fail-closed"),

    ("8 ledger-write-failure", "design + OUTER-LOOP standing rule", "accept_candidate",
     _ctx(gate_verdict=None),
     FAIL_CLOSED, "no durable verdict → a claimed win with no ledger row is void → fail-closed (old loop crashed here)"),
]


def _run():
    rows, failures = [], []
    for name, oracle, action, ctx, expected, why in SCENARIOS:
        got = route(action, ctx)
        ok = got == expected
        rows.append((name, oracle, action, expected, got, ok, why))
        if not ok:
            failures.append((name, action, expected, got))
    return rows, failures


def test_trace_equivalence():
    _, failures = _run()
    assert not failures, "trace-equivalence FAILED:\n" + "\n".join(
        f"  {n}: action={a} expected={e} got={g}" for n, a, e, g in failures
    )
    # Guard the protected boundary explicitly: no PROTECTED action ever routes unattended, in any regime.
    for prot in ("modify_the_gate", "model_class_change", "update_goals"):
        for regime in ("clean-cheap", "clean-expensive", "partial", "principal", "mixed"):
            assert route(prot, Context(regime=regime, gate_required=False)) == HUMAN_REQUIRED, \
                f"protected boundary breached: {prot} routed non-human in {regime}"


def main() -> int:
    rows, failures = _run()
    w = max(len(r[0]) for r in rows)
    print(f"{'scenario':<{w}}  {'oracle':<28}  {'action':<19}  {'expect':<14}  {'got':<14}  ok")
    print("-" * (w + 92))
    for name, oracle, action, expected, got, ok, why in rows:
        mark = "✅" if ok else "❌"
        print(f"{name:<{w}}  {oracle:<28}  {action:<19}  {expected:<14}  {got:<14}  {mark}")
    print()
    for name, oracle, action, expected, got, ok, why in rows:
        print(f"  {name}: {why}")
    print()
    if failures:
        print(f"❌ {len(failures)}/{len(rows)} scenarios FAILED trace-equivalence")
        return 1
    print(f"✅ all {len(rows)} scenarios trace-equivalent to the OUTER-LOOP oracle "
          f"(safety-critical routing reproduced; policy judgments out of scope by design)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
