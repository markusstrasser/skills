#!/usr/bin/env python3
"""Deterministic DAG validation for regression specifications.

Checks whether a proposed adjustment set satisfies the back-door criterion
for estimating the causal effect of treatment on outcome. Does NOT do causal
discovery — the caller provides the DAG.

Usage:
    echo '{"treatment":"X", "outcome":"Y", "edges":[["X","Y"]], "proposed_controls":[]}' | uv run python3 dag_check.py
    uv run python3 dag_check.py --treatment X --outcome Y --edges "X->M,M->Y,X->Y,C->X,C->Y" --controls "C"
    uv run python3 dag_check.py --test
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from typing import Any


# ---------------------------------------------------------------------------
# Graph primitives (pure-Python, no dependencies)
# ---------------------------------------------------------------------------

def build_graph(edges: list[list[str]]) -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    """Return (children, parents, all_nodes) from an edge list."""
    children: dict[str, set[str]] = {}
    parents: dict[str, set[str]] = {}
    nodes: set[str] = set()
    for src, dst in edges:
        children.setdefault(src, set()).add(dst)
        parents.setdefault(dst, set()).add(src)
        nodes.update((src, dst))
    return children, parents, nodes


def descendants(node: str, children: dict[str, set[str]]) -> set[str]:
    """All nodes reachable from *node* following directed edges (excludes node)."""
    visited: set[str] = set()
    queue = deque(children.get(node, set()))
    while queue:
        n = queue.popleft()
        if n in visited:
            continue
        visited.add(n)
        queue.extend(children.get(n, set()) - visited)
    return visited


def ancestors(node: str, parents: dict[str, set[str]]) -> set[str]:
    """All nodes that can reach *node* following directed edges (excludes node)."""
    visited: set[str] = set()
    queue = deque(parents.get(node, set()))
    while queue:
        n = queue.popleft()
        if n in visited:
            continue
        visited.add(n)
        queue.extend(parents.get(n, set()) - visited)
    return visited


def has_cycle(children: dict[str, set[str]], nodes: set[str]) -> bool:
    """Detect cycles via Kahn's algorithm (topological sort). Returns True if cycle exists."""
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    for src in children:
        for dst in children[src]:
            in_degree[dst] = in_degree.get(dst, 0) + 1
    queue = deque(n for n, d in in_degree.items() if d == 0)
    count = 0
    while queue:
        n = queue.popleft()
        count += 1
        for child in children.get(n, set()):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    return count != len(nodes)


# ---------------------------------------------------------------------------
# Path enumeration (DFS, bounded by node count — fine for small DAGs)
# ---------------------------------------------------------------------------

def _all_directed_paths(src: str, dst: str, children: dict[str, set[str]]) -> list[list[str]]:
    """All directed paths from src to dst."""
    results: list[list[str]] = []
    stack: list[tuple[str, list[str]]] = [(src, [src])]
    while stack:
        node, path = stack.pop()
        if node == dst and len(path) > 1:
            results.append(path)
            continue
        for nxt in children.get(node, []):
            if nxt not in path:  # acyclic guard
                stack.append((nxt, path + [nxt]))
    return results


MAX_PATHS = 200


def _all_undirected_paths(src: str, dst: str, children: dict[str, set[str]],
                          parents: dict[str, set[str]], max_paths: int = MAX_PATHS) -> list[list[str]]:
    """All undirected paths (ignoring arrow direction) between src and dst.

    Each path is a list of nodes. We also track edge directions so callers
    can classify path segments.  Returns at most *max_paths* to stay bounded.
    """
    results: list[list[str]] = []
    # neighbors in either direction
    neighbors: dict[str, set[str]] = {}
    for n in children:
        neighbors.setdefault(n, set()).update(children[n])
    for n in parents:
        neighbors.setdefault(n, set()).update(parents[n])

    stack: list[tuple[str, list[str]]] = [(src, [src])]
    while stack and len(results) < max_paths:
        node, path = stack.pop()
        if node == dst and len(path) > 1:
            results.append(path)
            continue
        for nxt in neighbors.get(node, []):
            if nxt not in path:
                stack.append((nxt, path + [nxt]))
    return results


def format_path(path: list[str], children: dict[str, set[str]]) -> str:
    """Pretty-print a path with arrow directions."""
    parts: list[str] = [path[0]]
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        if b in children.get(a, set()):
            parts.append(f" \u2192 {b}")
        else:
            parts.append(f" \u2190 {b}")
    return "".join(parts)


# ---------------------------------------------------------------------------
# d-separation / path blocking
# ---------------------------------------------------------------------------

def _is_collider(path: list[str], idx: int, children: dict[str, set[str]]) -> bool:
    """Is path[idx] a collider on this path?  A -> C <- B pattern."""
    if idx == 0 or idx == len(path) - 1:
        return False
    prev, node, nxt = path[idx - 1], path[idx], path[idx + 1]
    return (node in children.get(prev, set())) and (node in children.get(nxt, set()))


def _is_path_blocked(path: list[str], conditioned: set[str],
                     children: dict[str, set[str]]) -> bool:
    """Check if a path is blocked (d-separated) given conditioned variables.

    A path is blocked if ANY intermediate node satisfies:
      - Non-collider AND conditioned on, OR
      - Collider AND neither it nor any descendant is conditioned on.
    """
    for i in range(1, len(path) - 1):
        node = path[i]
        if _is_collider(path, i, children):
            # Collider: path blocked UNLESS node or descendant is conditioned
            desc = descendants(node, children)
            if node not in conditioned and not (desc & conditioned):
                return True
        else:
            # Non-collider: path blocked IF conditioned
            if node in conditioned:
                return True
    return False


def classify_paths(treatment: str, outcome: str,
                   children: dict[str, set[str]], parents: dict[str, set[str]]):
    """Classify all paths between treatment and outcome."""
    causal = _all_directed_paths(treatment, outcome, children)
    all_paths = _all_undirected_paths(treatment, outcome, children, parents)

    causal_node_sets = [set(p) for p in causal]
    backdoor: list[list[str]] = []
    for p in all_paths:
        # A path is backdoor if the first edge points INTO treatment
        if len(p) >= 2 and treatment in children.get(p[1], set()):
            backdoor.append(p)
        # Also backdoor if first edge is treatment <- p[1] (p[1] is parent of treatment)
        elif len(p) >= 2 and p[0] in children.get(p[1], set()):
            backdoor.append(p)

    # Deduplicate: only keep truly non-causal paths as backdoor
    causal_tuples = {tuple(p) for p in causal}
    backdoor = [p for p in backdoor if tuple(p) not in causal_tuples]

    return causal, backdoor


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def validate(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate a proposed adjustment set against the back-door criterion."""
    treatment = spec["treatment"]
    outcome = spec["outcome"]
    edges = spec["edges"]
    proposed = set(spec.get("proposed_controls", []))
    unobserved = set(spec.get("unobserved", []))

    children, parents, nodes = build_graph(edges)

    # Bug 2: Acyclicity check
    if has_cycle(children, nodes):
        return {
            "valid": False,
            "error": "Graph contains a cycle. Input must be a DAG (directed acyclic graph).",
            "problems": [],
            "paths": {},
        }

    treat_desc = descendants(treatment, children)
    outcome_desc = descendants(outcome, children)

    # Classify paths
    causal_paths, backdoor_paths = classify_paths(treatment, outcome, children, parents)
    path_truncated = len(_all_undirected_paths(treatment, outcome, children, parents)) >= MAX_PATHS

    # Identify nodes on causal paths (mediators)
    mediator_nodes: set[str] = set()
    for p in causal_paths:
        mediator_nodes.update(p[1:-1])  # exclude treatment and outcome

    # Bug 1 fix: Two-pass classification. First pass identifies clear violations.
    # Second pass checks collider opening for the full remaining set.
    problems: list[dict[str, str]] = []
    remaining: set[str] = set()  # controls that survive first pass

    for var in sorted(proposed):  # sorted for determinism
        # Bug 3: Variable not in DAG
        if var not in nodes:
            problems.append({
                "variable": var,
                "issue": "not_in_dag",
                "explanation": f"{var} is not present in the DAG. Cannot assess its causal role.",
                "severity": "ERROR",
            })
            continue

        if var == treatment or var == outcome:
            problems.append({
                "variable": var,
                "issue": "treatment_or_outcome",
                "explanation": f"{var} is the treatment or outcome itself. Cannot condition on it.",
                "severity": "ERROR",
            })
            continue

        # Bug 6: Unobserved nodes cannot be in adjustment set
        if var in unobserved:
            problems.append({
                "variable": var,
                "issue": "unobserved",
                "explanation": f"{var} is unobserved and cannot be conditioned on.",
                "severity": "ERROR",
            })
            continue

        # Bug 4: Descendants of outcome (check before treatment descendants —
        # a node downstream of Y via X->Y->D is more specifically an outcome issue)
        if var in outcome_desc:
            problems.append({
                "variable": var,
                "issue": "descendant_of_outcome",
                "explanation": (
                    f"{var} is a descendant of {outcome}. "
                    f"Conditioning on it can induce bias."
                ),
                "severity": "ERROR",
            })
            continue

        if var in treat_desc:
            if var in mediator_nodes:
                problems.append({
                    "variable": var,
                    "issue": "mediator",
                    "explanation": (
                        f"{var} lies on a causal path from {treatment} to {outcome}. "
                        f"Conditioning on it blocks part of the causal effect."
                    ),
                    "severity": "ERROR",
                })
            else:
                problems.append({
                    "variable": var,
                    "issue": "descendant_of_treatment",
                    "explanation": (
                        f"{var} is caused by {treatment} "
                        f"({treatment} \u2192 {var}). "
                        f"Conditioning on it can induce collider bias."
                    ),
                    "severity": "ERROR",
                })
            continue

        remaining.add(var)

    # Second pass: check if the full remaining set opens any collider paths
    all_paths = _all_undirected_paths(treatment, outcome, children, parents)
    collider_victims: set[str] = set()
    for p in all_paths:
        for i in range(1, len(p) - 1):
            node = p[i]
            if node not in remaining:
                continue
            if not _is_collider(p, i, children):
                continue
            # Would conditioning on remaining open this previously-blocked path?
            blocked_without = _is_path_blocked(p, remaining - {node}, children)
            blocked_with = _is_path_blocked(p, remaining, children)
            if blocked_without and not blocked_with:
                collider_victims.add(node)
                problems.append({
                    "variable": node,
                    "issue": "collider",
                    "explanation": (
                        f"{node} is a collider on path {format_path(p, children)}. "
                        f"Conditioning on it opens a spurious association."
                    ),
                    "severity": "ERROR",
                })

    clean_controls = remaining - collider_victims

    # Check if clean controls block all backdoor paths
    blocked_paths: list[str] = []
    unblocked_paths: list[str] = []
    for p in backdoor_paths:
        if _is_path_blocked(p, clean_controls, children):
            blocked_paths.append(format_path(p, children))
        else:
            unblocked_paths.append(format_path(p, children))

    # Bug 6: Check for unidentifiable paths (only blockable via unobserved nodes)
    unidentifiable_paths: list[str] = []
    if unobserved and unblocked_paths:
        for p in backdoor_paths:
            if _is_path_blocked(p, clean_controls, children):
                continue
            # Try blocking with all nodes including unobserved
            all_possible = (clean_controls | unobserved) - {treatment, outcome}
            if _is_path_blocked(p, all_possible, children):
                unidentifiable_paths.append(format_path(p, children))

    # Also check: does the proposed set (including bad controls) open any paths?
    opened_paths: list[str] = []
    for p in all_paths:
        if tuple(p) in {tuple(cp) for cp in causal_paths}:
            continue
        # Was blocked without conditioning, now open?
        if _is_path_blocked(p, set(), children) and not _is_path_blocked(p, proposed, children):
            opened_paths.append(format_path(p, children))

    valid = len(problems) == 0 and len(unblocked_paths) == 0

    # Suggest a valid adjustment set: all proposed minus problematic, check sufficiency
    suggested = clean_controls.copy()
    # If there are unblocked backdoor paths, try adding available pre-treatment nodes
    if unblocked_paths:
        for var in sorted(nodes - {treatment, outcome} - treat_desc - unobserved):
            test_set = suggested | {var}
            all_blocked = all(
                _is_path_blocked(p, test_set, children) for p in backdoor_paths
            )
            if all_blocked:
                suggested = test_set
                break

    result: dict[str, Any] = {
        "valid": valid,
        "adjustment_set": sorted(suggested) if not valid else sorted(proposed),
        "problems": problems,
        "paths": {
            "causal": [format_path(p, children) for p in causal_paths],
            "backdoor": [format_path(p, children) for p in backdoor_paths],
            "blocked_by_controls": blocked_paths,
        },
    }
    if unblocked_paths:
        result["paths"]["unblocked"] = unblocked_paths
    if opened_paths:
        result["paths"]["opened_by_conditioning"] = opened_paths
    if unidentifiable_paths:
        result["paths"]["unidentifiable"] = unidentifiable_paths
        result["unidentifiable"] = True

    # Bug 7: Warn on path truncation
    if path_truncated:
        result["warning"] = "Path enumeration truncated at 200. Results may be incomplete for dense graphs."

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_edge_string(s: str) -> list[list[str]]:
    """Parse 'A->B,B->C' into [['A','B'],['B','C']]."""
    edges = []
    for part in s.split(","):
        part = part.strip()
        if "->" in part:
            src, dst = part.split("->", 1)
            edges.append([src.strip(), dst.strip()])
        else:
            raise ValueError(f"Edge '{part}' must use '->' format (e.g., 'X->Y')")
    return edges


def main():
    parser = argparse.ArgumentParser(description="DAG adjustment-set validator")
    parser.add_argument("--treatment", "-t", help="Treatment variable")
    parser.add_argument("--outcome", "-o", help="Outcome variable")
    parser.add_argument("--edges", "-e", help="Edges as 'A->B,B->C,...'")
    parser.add_argument("--controls", "-c", help="Proposed controls as 'X,Y,...'")
    parser.add_argument("--unobserved", "-u", help="Unobserved nodes as 'U1,U2,...'")
    parser.add_argument("--test", action="store_true", help="Run built-in test cases")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    if args.treatment and args.outcome and args.edges:
        spec = {
            "treatment": args.treatment,
            "outcome": args.outcome,
            "edges": parse_edge_string(args.edges),
            "proposed_controls": [c.strip() for c in args.controls.split(",")] if args.controls else [],
        }
        if args.unobserved:
            spec["unobserved"] = [u.strip() for u in args.unobserved.split(",")]
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            parser.print_help()
            sys.exit(1)
        spec = json.loads(raw)

    result = validate(spec)
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(0 if result["valid"] else 1)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def run_tests():
    passed = 0
    failed = 0

    def check(name: str, spec: dict, expect_valid: bool,
              expect_issues: list[str] | None = None,
              expect_error: bool = False,
              expect_unidentifiable: bool = False,
              expect_warning: str | None = None):
        nonlocal passed, failed
        result = validate(spec)

        ok = True
        if expect_error:
            ok = ok and "error" in result
        else:
            ok = ok and result["valid"] == expect_valid
        if expect_issues:
            found_issues = {p["issue"] for p in result["problems"]}
            ok = ok and all(i in found_issues for i in expect_issues)
        if expect_unidentifiable:
            ok = ok and result.get("unidentifiable", False)
        if expect_warning:
            ok = ok and expect_warning in result.get("warning", "")

        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        else:
            passed += 1
        print(f"  [{status}] {name}")
        if not ok:
            print(f"         expected valid={expect_valid}, error={expect_error}")
            print(f"         result: {json.dumps(result, indent=4)}")

    print("Running DAG validation tests...\n")

    # 1. NLSY97 bad-control: items_complete is descendant of treatment
    check(
        "NLSY97 bad control (descendant of treatment)",
        {
            "treatment": "sex",
            "outcome": "quant_score",
            "edges": [
                ["sex", "items_complete"],
                ["items_complete", "quant_score"],
                ["sex", "quant_score"],
                ["education", "sex"],
                ["education", "quant_score"],
                ["room_conditions", "quant_score"],
            ],
            "proposed_controls": ["education", "items_complete", "room_conditions"],
        },
        expect_valid=False,
        expect_issues=["mediator"],  # items_complete is on causal path
    )

    # 2. Clean specification: only pre-treatment confounders
    check(
        "Clean specification (pre-treatment confounders only)",
        {
            "treatment": "sex",
            "outcome": "quant_score",
            "edges": [
                ["sex", "items_complete"],
                ["items_complete", "quant_score"],
                ["sex", "quant_score"],
                ["education", "sex"],
                ["education", "quant_score"],
                ["room_conditions", "quant_score"],
            ],
            "proposed_controls": ["education"],
        },
        expect_valid=True,
    )

    # 3. Mediator as control: M sits on the only causal path
    check(
        "Mediator as control (blocks causal effect)",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "M"],
                ["M", "Y"],
                ["C", "X"],
                ["C", "Y"],
            ],
            "proposed_controls": ["C", "M"],
        },
        expect_valid=False,
        expect_issues=["mediator"],
    )

    # 4. Collider bias: conditioning on Z opens X <- U1 -> Z <- U2 -> Y
    check(
        "Collider bias (conditioning opens spurious path)",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["U1", "X"],
                ["U1", "Z"],
                ["U2", "Z"],
                ["U2", "Y"],
            ],
            "proposed_controls": ["Z"],
        },
        expect_valid=False,
        expect_issues=["collider"],
    )

    # 5. No backdoor paths, no controls needed
    check(
        "No confounding (empty controls valid)",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [["X", "Y"]],
            "proposed_controls": [],
        },
        expect_valid=True,
    )

    # 6. Unblocked backdoor (forgot to control for confounder)
    check(
        "Unblocked backdoor path (missing confounder control)",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["C", "X"],
                ["C", "Y"],
            ],
            "proposed_controls": [],
        },
        expect_valid=False,
    )

    # --- New tests ---

    # 7. Acyclicity rejection
    check(
        "Cycle detection (A->B->C->A)",
        {
            "treatment": "A",
            "outcome": "C",
            "edges": [
                ["A", "B"],
                ["B", "C"],
                ["C", "A"],
            ],
            "proposed_controls": [],
        },
        expect_valid=False,
        expect_error=True,
    )

    # 8. Unknown variable flagging
    check(
        "Unknown variable not in DAG",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["C", "X"],
                ["C", "Y"],
            ],
            "proposed_controls": ["C", "GHOST"],
        },
        expect_valid=False,
        expect_issues=["not_in_dag"],
    )

    # 9. Outcome descendant flagging
    check(
        "Descendant of outcome flagged",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["Y", "D"],
                ["C", "X"],
                ["C", "Y"],
            ],
            "proposed_controls": ["C", "D"],
        },
        expect_valid=False,
        expect_issues=["descendant_of_outcome"],
    )

    # 10. Unobserved node blocking
    check(
        "Unobserved confounder (unidentifiable)",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["U", "X"],
                ["U", "Y"],
            ],
            "unobserved": ["U"],
            "proposed_controls": [],
        },
        expect_valid=False,
        expect_unidentifiable=True,
    )

    # 11. Unobserved node proposed as control
    check(
        "Unobserved node proposed as control",
        {
            "treatment": "X",
            "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["U", "X"],
                ["U", "Y"],
            ],
            "unobserved": ["U"],
            "proposed_controls": ["U"],
        },
        expect_valid=False,
        expect_issues=["unobserved"],
    )

    # 12. Order-independence: collider detection same with sorted vs reverse-sorted controls
    # X <- A -> C <- B -> Y with proposed {A, C}
    # A is a valid control (blocks A->X), C is a collider. Must get same answer regardless of order.
    spec_collider_order = {
        "treatment": "X",
        "outcome": "Y",
        "edges": [
            ["A", "X"],
            ["A", "C"],
            ["B", "C"],
            ["B", "Y"],
            ["X", "Y"],
        ],
        "proposed_controls": ["A", "C"],
    }
    result_sorted = validate(spec_collider_order)

    spec_collider_order_rev = dict(spec_collider_order)
    spec_collider_order_rev["proposed_controls"] = ["C", "A"]
    result_rev = validate(spec_collider_order_rev)

    order_ok = (
        result_sorted["valid"] == result_rev["valid"]
        and set(v["variable"] for v in result_sorted["problems"])
        == set(v["variable"] for v in result_rev["problems"])
    )
    if order_ok:
        passed += 1
        print("  [PASS] Order-independence (sorted vs reverse-sorted controls)")
    else:
        failed += 1
        print("  [FAIL] Order-independence (sorted vs reverse-sorted controls)")
        print(f"         sorted result:  valid={result_sorted['valid']}, problems={[p['variable'] for p in result_sorted['problems']]}")
        print(f"         reverse result: valid={result_rev['valid']}, problems={[p['variable'] for p in result_rev['problems']]}")

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
