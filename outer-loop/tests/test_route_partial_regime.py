#!/usr/bin/env python3
"""Partial-regime trace-equivalence: outer-loop skill + science's LOOP.md contract reproduces the
research-ops cycle Lane A/B autonomy split — AND proves the route.py partial-accept fix.

The load-bearing assertion: a partial accept routes to ATTENDED, NOT the clean-regime unattended
auto-ratchet. A noisy/partial verifier cannot be trusted to auto-commit — auto-accepting on a
partial verdict is the intel/genomics report-not-gate failure inverted. hutter's clean-cheap test
never exercised this branch; the science ground truth (research-ops Lane B is attended) exposed it.

Oracle = research-ops/SKILL.md cycle mode:
  Lane A (Generate) = unattended drafts to queue/ · Lane B (Execute/verify) = ATTENDED ·
  "never autonomous" set (clinical / new verifier tooling / GOALS) = human → decisions-pending/ ·
  verify FAIL (claim contradicted >0.7) = revert flow.

Resolves each action's autonomy the way the skill would: a literal in the contract is taken as-is;
`autonomy: route()` defers to scripts/route.py with the action's typed properties.

Run directly (`uv run python3 tests/test_route_partial_regime.py`) for the table, or via pytest.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from route import (  # noqa: E402
    Context, route,
    UNATTENDED, ATTENDED, REJECT, HUMAN_REQUIRED,
)


def _load_contract() -> dict:
    import yaml
    text = (ROOT / "references" / "examples" / "science-LOOP.md").read_text()
    body = text.lstrip()[3:]
    block = body[: body.find("\n---")]
    return yaml.safe_load(block)


CONTRACT = _load_contract()
REGIME = CONTRACT["verifier"]["regime"]                                  # partial
ACCEPT_VERDICTS = frozenset(CONTRACT["accept_gate"]["accept_verdicts"])  # {VERIFIED, PASS}
ACTIONS = CONTRACT["actions"]


def effective_autonomy(action_name: str, *, gate_verdict=None) -> str:
    """How the skill resolves an action's autonomy: contract literal, or defer to route()."""
    spec = ACTIONS[action_name]
    auto = spec["autonomy"]
    if auto != "route()":
        return auto                                                     # contract literal
    ctx = Context(
        regime=REGIME,
        reversible=spec.get("reversible", True),
        blast_radius=spec.get("blast_radius", "local"),
        gate_verdict=gate_verdict,
        accept_verdicts=ACCEPT_VERDICTS,
        gate_required=(action_name == "accept_candidate"),
    )
    return route(action_name, ctx)


# (name, action, gate_verdict, expected, why)
SCENARIOS = [
    ("1 generate (Lane A)", "generate_finding", None, UNATTENDED,
     "unattended idea-generation → reversible drafts to queue/, never executes"),
    ("2 execute (Lane B)", "execute_finding", None, ATTENDED,
     "ships a greenlit change → attended; the partial verifier sits in this lane, can't auto-trust"),
    ("3 accept, verify PASSED", "accept_candidate", "VERIFIED", ATTENDED,
     "THE FIX: a partial accept is ATTENDED, never the clean auto-ratchet (no auto-commit on a noisy gate)"),
    ("4 accept, verify CONTRADICTED", "accept_candidate", "CONTRADICTED", REJECT,
     "claim contradicted >0.7 → non-accept verdict → REJECT → revert flow (archive + git revert)"),
    ("5 clinical threshold", "flag_clinical", None, HUMAN_REQUIRED,
     "'never autonomous' clinical-implication set → human, written to decisions-pending/"),
    ("6 new verifier tooling", "new_verifier_tooling", None, HUMAN_REQUIRED,
     "new verification tooling is a gate change → protected boundary → human"),
    ("7 modify the gate", "modify_the_gate", None, HUMAN_REQUIRED,
     "protected verifier boundary → human, in every regime"),
    ("8 update GOALS", "update_goals", None, HUMAN_REQUIRED,
     "GOALS direction is human-owned → human"),
]


def _run():
    rows, failures = [], []
    for name, action, gv, expected, why in SCENARIOS:
        got = effective_autonomy(action, gate_verdict=gv)
        ok = got == expected
        rows.append((name, action, expected, got, ok, why))
        if not ok:
            failures.append((name, action, expected, got))
    return rows, failures


def test_partial_regime():
    _, failures = _run()
    assert not failures, "partial-regime trace-equivalence FAILED:\n" + "\n".join(
        f"  {n}: action={a} expected={e} got={g}" for n, a, e, g in failures
    )
    # The regression guard: a partial accept on a PASSED verify must NOT be unattended. This is the
    # exact bug the science ground truth caught — auto-committing on a noisy verifier.
    assert effective_autonomy("accept_candidate", gate_verdict="VERIFIED") != UNATTENDED, \
        "REGRESSION: partial accept auto-ratcheted — a noisy gate must never auto-commit"
    # route() enforces the protected boundary even if a contract tried to soften it.
    assert route("modify_the_gate", Context(regime="partial", gate_required=False)) == HUMAN_REQUIRED


def main() -> int:
    rows, failures = _run()
    w = max(len(r[0]) for r in rows)
    print(f"{'scenario':<{w}}  {'action':<20}  {'expect':<14}  {'got':<14}  ok")
    print("-" * (w + 70))
    for name, action, expected, got, ok, why in rows:
        print(f"{name:<{w}}  {action:<20}  {expected:<14}  {got:<14}  {'✅' if ok else '❌'}")
    print()
    for name, action, expected, got, ok, why in rows:
        print(f"  {name}: {why}")
    print()
    if failures:
        print(f"❌ {len(failures)}/{len(rows)} partial-regime scenarios FAILED")
        return 1
    print(f"✅ all {len(rows)} partial-regime scenarios match the research-ops cycle oracle "
          f"(partial accept = ATTENDED, the fix proven)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
