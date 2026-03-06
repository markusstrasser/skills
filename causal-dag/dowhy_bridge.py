#!/usr/bin/env python3
"""DoWhy comparison bridge for dag_check.py.

Runs both our validator and DoWhy's identification on the same specs,
producing a comparison report. This is an ASSESSMENT tool — it determines
whether DoWhy adds value beyond our validator.

Usage:
    uv run --with dowhy python3 dowhy_bridge.py --test
    echo '{"treatment":"X","outcome":"Y","edges":[["C","X"],["C","Y"],["X","Y"]],"proposed_controls":["C"]}' | \
        uv run --with dowhy python3 dowhy_bridge.py

Decision gate (after running):
- If DoWhy agrees on all simple cases AND provides meaningful extras: recommend optional backend
- If DoWhy adds nothing beyond our validator: keep standalone
- If DoWhy disagrees on cases where it's right and we're wrong: fix our validator
"""

from __future__ import annotations

import json
import sys
import warnings
from typing import Any

import dag_check


def run_dowhy_identify(spec: dict[str, Any]) -> dict[str, Any]:
    """Run DoWhy identification on a spec."""
    try:
        import dowhy
        from dowhy import CausalModel
    except ImportError:
        return {"error": "DoWhy not installed. Run with: uv run --with dowhy"}

    treatment = spec["treatment"]
    outcome = spec["outcome"]

    # Normalize edges
    edges, _, _ = dag_check.normalize_edges(spec["edges"])

    # Build DoWhy graph in GML format
    gml_nodes = set()
    gml_edges = []
    for src, dst in edges:
        gml_nodes.add(src)
        gml_nodes.add(dst)
        gml_edges.append(f'edge [ source "{src}" target "{dst}" ]')

    gml_node_strs = [f'node [ id "{n}" label "{n}" ]' for n in sorted(gml_nodes)]
    gml = "graph [ directed 1 " + " ".join(gml_node_strs) + " " + " ".join(gml_edges) + " ]"

    # DoWhy needs data to create a CausalModel, but we only need identification
    # Create minimal dummy data
    import pandas as pd
    import numpy as np
    np.random.seed(0)
    dummy_data = pd.DataFrame({n: np.random.normal(0, 1, 10) for n in gml_nodes})

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = CausalModel(
                data=dummy_data,
                treatment=treatment,
                outcome=outcome,
                graph=gml,
            )

            # Try backdoor identification
            estimand = model.identify_effect(proceed_when_unidentifiable=True)

            # Extract results
            result: dict[str, Any] = {
                "identified": estimand.estimands is not None,
                "identification_method": None,
                "backdoor_sets": [],
                "all_estimands": {},
            }

            if estimand.estimands:
                for method_name, est in estimand.estimands.items():
                    if est is not None:
                        result["all_estimands"][method_name] = str(est)
                        if "backdoor" in method_name.lower():
                            result["identification_method"] = "backdoor"
                            # Extract variables from the estimand
                            if hasattr(estimand, "backdoor_variables"):
                                result["backdoor_sets"] = [sorted(estimand.backdoor_variables)]
                        elif "frontdoor" in method_name.lower():
                            if result["identification_method"] is None:
                                result["identification_method"] = "frontdoor"
                        elif "iv" in method_name.lower():
                            if result["identification_method"] is None:
                                result["identification_method"] = "iv"

            return result

    except Exception as e:
        return {"error": f"DoWhy failed: {e}"}


def compare(spec: dict[str, Any]) -> dict[str, Any]:
    """Compare our validator with DoWhy on the same spec."""
    our_result = dag_check.validate(spec)
    dowhy_result = run_dowhy_identify(spec)

    # Determine agreement
    # Key semantic difference: DoWhy answers "is the effect identifiable?" (any valid set exists)
    # Our validator answers "is THIS specific proposed set valid?"
    # So: ours=False + dowhy=True means "effect is identifiable but proposed set is wrong" (expected)
    # Real disagreement is: ours=True + dowhy=False, or ours=False + dowhy=False when ours has no problems
    if "error" in dowhy_result:
        agrees = None
        note = f"DoWhy error: {dowhy_result['error']}"
    elif "error" in our_result:
        agrees = None
        note = f"Our validator error: {our_result['error']}"
    else:
        our_valid = our_result["valid"]
        dowhy_identified = dowhy_result.get("identified", False)

        if our_valid and dowhy_identified:
            agrees = True
            note = "Both agree: valid/identified"
        elif our_valid and not dowhy_identified:
            agrees = False
            note = "REAL DISAGREE: ours=valid but DoWhy says unidentifiable"
        elif not our_valid and dowhy_identified:
            # Expected: proposed set is wrong but effect IS identifiable
            agrees = True
            note = "Compatible: proposed set invalid but effect identifiable (different questions)"
        else:
            # Both say no — but for different reasons
            agrees = True
            note = "Both agree: invalid/unidentifiable"

    return {
        "treatment": spec["treatment"],
        "outcome": spec["outcome"],
        "our_valid": our_result.get("valid"),
        "our_adjustment_set": our_result.get("adjustment_set", []),
        "our_problems": [p["issue"] for p in our_result.get("problems", [])],
        "dowhy_identified": dowhy_result.get("identified"),
        "dowhy_method": dowhy_result.get("identification_method"),
        "dowhy_backdoor_sets": dowhy_result.get("backdoor_sets", []),
        "dowhy_extras": {
            k: v for k, v in dowhy_result.items()
            if k not in ("identified", "identification_method", "backdoor_sets", "error")
        },
        "agrees": agrees,
        "note": note,
    }


def run_tests():
    """Run comparison on all dag_check test cases."""
    print("DoWhy Bridge Assessment\n")
    print("=" * 70)

    # Define all test specs (subset of dag_check's 51 tests — the interesting ones)
    test_specs = [
        ("Simple confounding (valid)", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C"],
        }),
        ("Unblocked backdoor", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C", "X"], ["C", "Y"]],
            "proposed_controls": [],
        }),
        ("No confounding", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"]],
            "proposed_controls": [],
        }),
        ("Mediator as control", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "M"], ["M", "Y"], ["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C", "M"],
        }),
        ("Collider bias", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U1", "X"], ["U1", "Z"], ["U2", "Z"], ["U2", "Y"]],
            "proposed_controls": ["Z"],
        }),
        ("M-bias", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U1", "X"], ["U1", "Z"], ["U2", "Z"], ["U2", "Y"]],
            "proposed_controls": [],
        }),
        ("Unobserved confounder", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U", "X"], ["U", "Y"]],
            "unobserved": ["U"],
            "proposed_controls": [],
        }),
        ("Two independent confounders — both controlled", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C1", "X"], ["C1", "Y"], ["C2", "X"], ["C2", "Y"]],
            "proposed_controls": ["C1", "C2"],
        }),
        ("Chain confounders (A->B->X, A->Y)", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["A", "B"], ["B", "X"], ["A", "Y"]],
            "proposed_controls": ["A"],
        }),
        ("Diamond graph", {
            "treatment": "X", "outcome": "Y",
            "edges": [["C", "X"], ["C", "M"], ["M", "Y"], ["X", "Y"]],
            "proposed_controls": ["C"],
        }),
        ("Front-door candidate: X->M->Y, U->X, U->Y", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "M"], ["M", "Y"], ["U", "X"], ["U", "Y"]],
            "unobserved": ["U"],
            "proposed_controls": [],
        }),
        ("IV structure: Z->X->Y, U->X, U->Y", {
            "treatment": "X", "outcome": "Y",
            "edges": [["Z", "X"], ["X", "Y"], ["U", "X"], ["U", "Y"]],
            "unobserved": ["U"],
            "proposed_controls": [],
        }),
        ("Fork (pure confounding)", {
            "treatment": "X", "outcome": "Y",
            "edges": [["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C"],
        }),
        ("Parallel mediators", {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "M1"], ["M1", "Y"], ["X", "M2"], ["M2", "Y"], ["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C"],
        }),
        ("Dense graph (12 nodes)", {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "Y"], ["C1", "X"], ["C1", "Y"],
                ["C2", "X"], ["C2", "Y"], ["C3", "C1"], ["C3", "C2"],
                ["N1", "N2"], ["N2", "N3"], ["N3", "N4"],
                ["N4", "Y"], ["N5", "X"], ["N5", "N1"],
            ],
            "proposed_controls": ["C1", "C2", "N5"],
        }),
    ]

    total = len(test_specs)
    agree_count = 0
    disagree_count = 0
    error_count = 0
    dowhy_extras_found: list[str] = []

    for name, spec in test_specs:
        result = compare(spec)
        status = "AGREE" if result["agrees"] else ("ERROR" if result["agrees"] is None else "DISAGREE")

        if result["agrees"] is True:
            agree_count += 1
        elif result["agrees"] is False:
            disagree_count += 1
        else:
            error_count += 1

        # Check for DoWhy extras our validator doesn't provide
        method = result.get("dowhy_method")
        if method and method != "backdoor":
            dowhy_extras_found.append(f"{name}: DoWhy found {method} identification")

        icon = {"AGREE": "+", "DISAGREE": "!", "ERROR": "?"}[status]
        print(f"  [{icon}] {name}")
        if status == "DISAGREE":
            print(f"      Ours: valid={result['our_valid']}, adj_set={result['our_adjustment_set']}")
            print(f"      DoWhy: identified={result['dowhy_identified']}, method={result['dowhy_method']}")
            if result["dowhy_backdoor_sets"]:
                print(f"      DoWhy backdoor sets: {result['dowhy_backdoor_sets']}")
        elif status == "ERROR":
            print(f"      {result['note']}")

    print(f"\n{'=' * 70}")
    print(f"Summary: {agree_count} agree, {disagree_count} disagree, {error_count} errors out of {total}")

    if dowhy_extras_found:
        print(f"\nDoWhy extras (beyond our validator):")
        for e in dowhy_extras_found:
            print(f"  - {e}")
    else:
        print(f"\nNo DoWhy extras found — our validator covers all tested cases.")

    # Decision output
    print(f"\n{'=' * 70}")
    print("DECISION GATE:")
    if disagree_count == 0 and len(dowhy_extras_found) > 0:
        print("  -> DoWhy agrees on all cases AND provides extras. RECOMMEND optional backend.")
    elif disagree_count == 0 and len(dowhy_extras_found) == 0:
        print("  -> DoWhy agrees but adds nothing. KEEP dag_check.py standalone.")
    elif disagree_count > 0:
        print(f"  -> {disagree_count} disagreements. INVESTIGATE which is correct.")

    sys.exit(1 if disagree_count > 0 else 0)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DoWhy bridge assessment")
    parser.add_argument("--test", action="store_true", help="Run comparison on test cases")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    # Single spec from stdin
    raw = sys.stdin.read().strip()
    if not raw:
        parser.print_help()
        sys.exit(1)
    spec = json.loads(raw)
    result = compare(spec)
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
