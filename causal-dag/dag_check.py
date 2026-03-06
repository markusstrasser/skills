#!/usr/bin/env python3
"""Deterministic DAG validation for regression specifications.

Checks whether a proposed adjustment set satisfies the back-door criterion
for estimating the causal effect of treatment on outcome. Does NOT do causal
discovery — the caller provides the DAG.

Usage:
    echo '{"treatment":"X", "outcome":"Y", "edges":[["X","Y"]], "proposed_controls":[]}' | uv run python3 dag_check.py
    uv run python3 dag_check.py --treatment X --outcome Y --edges "X->M,M->Y,X->Y,C->X,C->Y" --controls "C"
    uv run python3 dag_check.py --test
    uv run python3 dag_check.py --consensus --test

Edge formats (both accepted):
    Old: [["A","B"], ["B","C"]]
    New: [{"from":"A","to":"B","temporal_justification":"A precedes B"}, ...]

In --strict mode, the new format with temporal_justification is required.
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
# Edge normalization
# ---------------------------------------------------------------------------

def normalize_edges(raw_edges: list, strict: bool = False) -> tuple[list[list[str]], list[str], list[str]]:
    """Normalize edge input to [src, dst] pairs. Returns (edges, warnings, uncertain_edges).

    Accepts two formats:
      Old: [["A", "B"], ...]
      New: [{"from": "A", "to": "B", "temporal_justification": "..."}, ...]

    In strict mode, rejects edges missing temporal_justification.
    Edges with "?" in justification are flagged as uncertain.
    """
    edges: list[list[str]] = []
    warnings: list[str] = []
    uncertain: list[str] = []

    for e in raw_edges:
        if isinstance(e, dict):
            src = e.get("from", "")
            dst = e.get("to", "")
            justification = e.get("temporal_justification", "")
            if strict and not justification:
                raise ValueError(
                    f"Edge {src}->{dst} missing temporal_justification (required in strict mode)"
                )
            if justification and "?" in justification:
                uncertain.append(f"{src}->{dst}")
            edges.append([src, dst])
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            if strict:
                raise ValueError(
                    f"Edge {e[0]}->{e[1]} uses old format. "
                    f"Strict mode requires {{\"from\", \"to\", \"temporal_justification\"}} format."
                )
            warnings.append(
                f"Edge {e[0]}->{e[1]} uses old [src, dst] format. "
                f"Consider using {{\"from\", \"to\", \"temporal_justification\"}} for metacognitive audit."
            )
            edges.append([e[0], e[1]])
        else:
            raise ValueError(f"Unrecognized edge format: {e}")

    return edges, warnings, uncertain


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def validate(spec: dict[str, Any], strict: bool = False) -> dict[str, Any]:
    """Validate a proposed adjustment set against the back-door criterion."""
    treatment = spec["treatment"]
    outcome = spec["outcome"]

    # Normalize edges (supports old and new format)
    try:
        edges, edge_warnings, uncertain_edges = normalize_edges(spec["edges"], strict=strict)
    except ValueError as exc:
        return {
            "valid": False,
            "error": str(exc),
            "problems": [],
            "paths": {},
        }

    proposed = set(spec.get("proposed_controls", []))
    unobserved = set(spec.get("unobserved", []))

    children, parents, nodes = build_graph(edges)

    # Attach edge metadata to result
    _edge_warnings = edge_warnings
    _uncertain_edges = uncertain_edges

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

    # Edge metadata
    if _uncertain_edges:
        result["uncertain_edges"] = _uncertain_edges
    if _edge_warnings:
        result["edge_warnings"] = _edge_warnings

    # Bug 7: Warn on path truncation
    if path_truncated:
        result["warning"] = "Path enumeration truncated at 200. Results may be incomplete for dense graphs."

    return result


# ---------------------------------------------------------------------------
# Consensus mode: edge-structure voting across N specifications
# ---------------------------------------------------------------------------

def consensus(specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Vote on edge structure across N independently generated specifications.

    Instead of filtering on adjustment-set validity (which rewards under-specified
    DAGs), we vote on edge agreement. The consensus DAG is then validated.
    """
    if len(specs) < 2:
        return {"error": "Consensus requires at least 2 specifications."}

    # Verify all specs share treatment/outcome
    treatments = {s["treatment"] for s in specs}
    outcomes = {s["outcome"] for s in specs}
    if len(treatments) > 1 or len(outcomes) > 1:
        return {"error": f"All specs must share treatment/outcome. Got treatments={treatments}, outcomes={outcomes}"}

    treatment = specs[0]["treatment"]
    outcome = specs[0]["outcome"]
    n = len(specs)

    # Extract edge sets from each spec
    edge_counts: dict[tuple[str, str], int] = {}
    for spec in specs:
        edges, _, _ = normalize_edges(spec["edges"])
        seen: set[tuple[str, str]] = set()
        for src, dst in edges:
            key = (src, dst)
            if key not in seen:
                edge_counts[key] = edge_counts.get(key, 0) + 1
                seen.add(key)

    # Compute agreement
    threshold = 0.6
    edge_agreement: dict[str, dict[str, Any]] = {}
    consensus_edges: list[list[str]] = []
    contested_edges: list[list[str]] = []

    for (src, dst), count in sorted(edge_counts.items()):
        agreement = count / n
        label = f"{src}->{dst}"
        edge_agreement[label] = {"present_in": count, "agreement": round(agreement, 2)}
        if agreement >= threshold:
            consensus_edges.append([src, dst])
        else:
            contested_edges.append([src, dst])

    # Collect proposed controls across specs (union for analysis)
    all_controls: set[str] = set()
    for spec in specs:
        all_controls.update(spec.get("proposed_controls", []))
    all_unobserved: set[str] = set()
    for spec in specs:
        all_unobserved.update(spec.get("unobserved", []))

    # Validate the consensus DAG
    consensus_spec = {
        "treatment": treatment,
        "outcome": outcome,
        "edges": consensus_edges,
        "proposed_controls": sorted(all_controls),
    }
    if all_unobserved:
        consensus_spec["unobserved"] = sorted(all_unobserved)

    consensus_result = validate(consensus_spec)

    # Classify adjustment sets: must-adjust / optional / forbidden
    children, parents, nodes = build_graph(consensus_edges)
    treat_desc = descendants(treatment, children)

    must_adjust: list[str] = []
    forbidden: list[str] = []
    optional: list[str] = []

    for var in sorted(nodes - {treatment, outcome}):
        if var in treat_desc:
            forbidden.append(var)
        elif var in all_unobserved:
            forbidden.append(var)
        else:
            # Check if needed to block any backdoor path
            causal_paths, backdoor_paths = classify_paths(treatment, outcome, children, parents)
            test_controls = {v for v in nodes - {treatment, outcome} - treat_desc - all_unobserved}
            without = test_controls - {var}
            all_blocked_without = all(_is_path_blocked(p, without, children) for p in backdoor_paths)
            all_blocked_with = all(_is_path_blocked(p, test_controls, children) for p in backdoor_paths)
            if all_blocked_with and not all_blocked_without:
                must_adjust.append(var)
            else:
                optional.append(var)

    # Agreement summary
    agreed_count = len(consensus_edges)
    total_count = len(edge_counts)
    pct = round(agreed_count / total_count * 100) if total_count > 0 else 0

    recommendation_parts: list[str] = []
    if pct >= 80:
        recommendation_parts.append(f"High structural consensus ({pct}% edges agreed).")
    elif pct >= 50:
        recommendation_parts.append(f"Moderate structural consensus ({pct}% edges agreed).")
    else:
        recommendation_parts.append(f"Low structural consensus ({pct}% edges agreed). Consider more discussion before proceeding.")

    if contested_edges:
        contested_labels = [f"{s}->{d}" for s, d in contested_edges]
        recommendation_parts.append(f"Contested edges: {', '.join(contested_labels)} — review before including.")

    return {
        "n_specs": n,
        "edge_agreement": edge_agreement,
        "consensus_edges": consensus_edges,
        "contested_edges": contested_edges,
        "consensus_dag_valid": consensus_result["valid"],
        "consensus_adjustment_set": consensus_result.get("adjustment_set", []),
        "adjustment_categories": {
            "must_adjust": must_adjust,
            "optional": optional,
            "forbidden": forbidden,
        },
        "recommendation": " ".join(recommendation_parts),
    }


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
    parser.add_argument("--strict", action="store_true",
                        help="Require temporal_justification for each edge")
    parser.add_argument("--consensus", action="store_true",
                        help="Run consensus mode (vote on edge structure across N specs)")
    parser.add_argument("--test", action="store_true", help="Run built-in test cases")
    args = parser.parse_args()

    if args.test and args.consensus:
        run_consensus_tests()
        return

    if args.test:
        run_tests()
        return

    if args.consensus:
        raw = sys.stdin.read().strip()
        if not raw:
            print("Consensus mode requires JSON array of specs on stdin", file=sys.stderr)
            sys.exit(1)
        specs = json.loads(raw)
        result = consensus(specs)
        json.dump(result, sys.stdout, indent=2)
        print()
        sys.exit(0)

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

    result = validate(spec, strict=args.strict)
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

    # --- Phase 4: Expanded test suite (50+ cases) ---

    # 16-20. Multiple minimal adjustment sets
    # Two independent confounders each create their own backdoor path — both must be controlled
    check(
        "Two independent confounders — controlling only one is insufficient",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C1", "X"], ["C1", "Y"], ["C2", "X"], ["C2", "Y"]],
            "proposed_controls": ["C1"],
        },
        expect_valid=False,
    )
    check(
        "Two independent confounders — controlling both is valid",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C1", "X"], ["C1", "Y"], ["C2", "X"], ["C2", "Y"]],
            "proposed_controls": ["C1", "C2"],
        },
        expect_valid=True,
    )
    # Multiple minimal sets: C1->C2->X, C1->Y. Either {C1} or {C2} blocks the single backdoor
    check(
        "Multiple minimal sets — controlling upstream C1 sufficient",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C1", "C2"], ["C2", "X"], ["C1", "Y"]],
            "proposed_controls": ["C1"],
        },
        expect_valid=True,
    )
    check(
        "Multiple minimal sets — controlling downstream C2 also sufficient",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["C1", "C2"], ["C2", "X"], ["C1", "Y"]],
            "proposed_controls": ["C2"],
        },
        expect_valid=True,
    )
    check(
        "Three independent confounders — all must be controlled",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "Y"], ["C1", "X"], ["C1", "Y"],
                ["C2", "X"], ["C2", "Y"], ["C3", "X"], ["C3", "Y"],
            ],
            "proposed_controls": ["C1", "C2", "C3"],
        },
        expect_valid=True,
    )
    check(
        "Chain confounders: A->B->X, A->Y (must control A, not B)",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["A", "B"], ["B", "X"], ["A", "Y"]],
            "proposed_controls": ["A"],
        },
        expect_valid=True,
    )

    # 21-25. Dense graphs (>10 nodes)
    check(
        "Dense graph — 12 nodes, proper adjustment",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "Y"], ["C1", "X"], ["C1", "Y"],
                ["C2", "X"], ["C2", "Y"], ["C3", "C1"], ["C3", "C2"],
                ["N1", "N2"], ["N2", "N3"], ["N3", "N4"],
                ["N4", "Y"], ["N5", "X"], ["N5", "N1"],
            ],
            "proposed_controls": ["C1", "C2", "N5"],
        },
        expect_valid=True,
    )
    check(
        "Dense graph — mediator in long chain",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "M1"], ["M1", "M2"], ["M2", "M3"], ["M3", "Y"],
                ["C", "X"], ["C", "Y"],
            ],
            "proposed_controls": ["C", "M1"],
        },
        expect_valid=False,
        expect_issues=["mediator"],
    )
    check(
        "Wide graph — 10 independent confounders",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"]] + [[f"C{i}", "X"] for i in range(10)]
                     + [[f"C{i}", "Y"] for i in range(10)],
            "proposed_controls": [f"C{i}" for i in range(10)],
        },
        expect_valid=True,
    )
    check(
        "Wide graph — missing one confounder",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"]] + [[f"C{i}", "X"] for i in range(10)]
                     + [[f"C{i}", "Y"] for i in range(10)],
            "proposed_controls": [f"C{i}" for i in range(9)],  # missing C9
        },
        expect_valid=False,
    )
    check(
        "Diamond graph: C->X, C->M, M->Y, X->Y",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["C", "X"], ["C", "M"], ["M", "Y"], ["X", "Y"]],
            "proposed_controls": ["C"],
        },
        expect_valid=True,
    )

    # 26-28. M-bias / butterfly
    check(
        "M-bias: U1->X, U1->Z, U2->Z, U2->Y — controlling Z is wrong",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U1", "X"], ["U1", "Z"], ["U2", "Z"], ["U2", "Y"]],
            "proposed_controls": ["Z"],
        },
        expect_valid=False,
        expect_issues=["collider"],
    )
    check(
        "M-bias: not controlling Z is correct",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U1", "X"], ["U1", "Z"], ["U2", "Z"], ["U2", "Y"]],
            "proposed_controls": [],
        },
        expect_valid=True,
    )
    check(
        "Butterfly: two M-bias structures sharing treatment",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "Y"],
                ["U1", "X"], ["U1", "Z1"], ["U2", "Z1"], ["U2", "Y"],
                ["U3", "X"], ["U3", "Z2"], ["U4", "Z2"], ["U4", "Y"],
            ],
            "proposed_controls": [],
        },
        expect_valid=True,
    )

    # 29-31. Mediator decomposition
    check(
        "Direct + indirect: controlling M gives direct effect only",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "M"], ["M", "Y"], ["X", "Y"], ["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C", "M"],
        },
        expect_valid=False,
        expect_issues=["mediator"],
    )
    check(
        "Parallel mediators: X->M1->Y, X->M2->Y",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "M1"], ["M1", "Y"], ["X", "M2"], ["M2", "Y"],
                       ["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C"],
        },
        expect_valid=True,
    )
    check(
        "Serial mediators: X->M1->M2->Y",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "M1"], ["M1", "M2"], ["M2", "Y"], ["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C", "M2"],
        },
        expect_valid=False,
        expect_issues=["mediator"],
    )

    # 32-34. Instrumental variable structures
    check(
        "IV: Z->X->Y, controlling Z is harmless but unnecessary",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["Z", "X"], ["X", "Y"]],
            "proposed_controls": ["Z"],
        },
        expect_valid=True,
    )
    check(
        "IV with confounder: Z->X, X->Y, U->X, U->Y",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["Z", "X"], ["X", "Y"], ["U", "X"], ["U", "Y"]],
            "unobserved": ["U"],
            "proposed_controls": [],
        },
        expect_valid=False,
        expect_unidentifiable=True,
    )
    check(
        "Invalid IV: Z->X, Z->Y (violates exclusion)",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["Z", "X"], ["Z", "Y"], ["X", "Y"]],
            "proposed_controls": ["Z"],
        },
        expect_valid=True,  # Z is a valid confounder control here
    )

    # 35-38. Latent confounders
    check(
        "Two latent confounders — fully unidentifiable",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U1", "X"], ["U1", "Y"], ["U2", "X"], ["U2", "Y"]],
            "unobserved": ["U1", "U2"],
            "proposed_controls": [],
        },
        expect_valid=False,
        expect_unidentifiable=True,
    )
    check(
        "One latent, one observed — partial identification",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U", "X"], ["U", "Y"], ["C", "X"], ["C", "Y"]],
            "unobserved": ["U"],
            "proposed_controls": ["C"],
        },
        expect_valid=False,
        expect_unidentifiable=True,
    )
    check(
        "Latent confounder with proxy: U->P, U->X, U->Y",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["U", "X"], ["U", "Y"], ["U", "P"]],
            "unobserved": ["U"],
            "proposed_controls": ["P"],
        },
        expect_valid=False,  # P doesn't block U->X or U->Y
    )
    check(
        "Latent on non-backdoor path — not a problem",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["X", "M"], ["U", "M"], ["U", "D"]],
            "unobserved": ["U"],
            "proposed_controls": [],
        },
        expect_valid=True,
    )

    # 39-49. Edge cases
    check(
        "Single edge X->Y, no controls",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"]],
            "proposed_controls": [],
        },
        expect_valid=True,
    )
    check(
        "Treatment equals outcome",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"]],
            "proposed_controls": ["X"],
        },
        expect_valid=False,
        expect_issues=["treatment_or_outcome"],
    )
    check(
        "Outcome proposed as control",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"]],
            "proposed_controls": ["Y"],
        },
        expect_valid=False,
        expect_issues=["treatment_or_outcome"],
    )
    check(
        "Self-loop detection",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["X", "X"]],
            "proposed_controls": [],
        },
        expect_valid=False,
        expect_error=True,
    )
    check(
        "Disconnected confounder (no path to treatment or outcome)",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "Y"], ["A", "B"]],
            "proposed_controls": ["A"],
        },
        expect_valid=True,  # A doesn't cause problems, just unnecessary
    )
    check(
        "Long chain: X->A->B->C->D->Y with confounder",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "A"], ["A", "B"], ["B", "C"], ["C", "D"], ["D", "Y"],
                ["E", "X"], ["E", "Y"],
            ],
            "proposed_controls": ["E"],
        },
        expect_valid=True,
    )
    check(
        "Long chain — controlling intermediate blocks causal path",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                ["X", "A"], ["A", "B"], ["B", "C"], ["C", "D"], ["D", "Y"],
                ["E", "X"], ["E", "Y"],
            ],
            "proposed_controls": ["E", "B"],
        },
        expect_valid=False,
        expect_issues=["mediator"],
    )
    check(
        "Multiple treatments sharing confounder",
        {
            "treatment": "X1", "outcome": "Y",
            "edges": [["X1", "Y"], ["X2", "Y"], ["C", "X1"], ["C", "X2"], ["C", "Y"]],
            "proposed_controls": ["C"],
        },
        expect_valid=True,
    )
    check(
        "Descendant of treatment that's also ancestor of outcome",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["X", "D"], ["D", "Y"]],
            "proposed_controls": ["D"],
        },
        expect_valid=False,
        expect_issues=["mediator"],
    )
    check(
        "Fork structure: C->X, C->Y (pure confounding, no direct effect)",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["C", "X"], ["C", "Y"]],
            "proposed_controls": ["C"],
        },
        expect_valid=True,
    )
    check(
        "Fork structure: not controlling C leaves path open",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [["C", "X"], ["C", "Y"]],
            "proposed_controls": [],
        },
        expect_valid=False,
    )

    # 50. New-format edges work correctly for validation
    check(
        "New-format edges with justifications",
        {
            "treatment": "X", "outcome": "Y",
            "edges": [
                {"from": "X", "to": "Y", "temporal_justification": "Treatment precedes outcome"},
                {"from": "C", "to": "X", "temporal_justification": "C measured before treatment"},
                {"from": "C", "to": "Y", "temporal_justification": "C affects outcome"},
            ],
            "proposed_controls": ["C"],
        },
        expect_valid=True,
    )

    # --- Phase 1 tests (strict mode / uncertain edges) ---

    # 51. Strict mode rejects old-format edges
    strict_old_format = {
        "treatment": "X",
        "outcome": "Y",
        "edges": [["X", "Y"], ["C", "X"], ["C", "Y"]],
        "proposed_controls": ["C"],
    }
    result_strict = validate(strict_old_format, strict=True)
    if "error" in result_strict and "old format" in result_strict["error"].lower():
        passed += 1
        print("  [PASS] Strict mode rejects old-format edges")
    else:
        failed += 1
        print("  [FAIL] Strict mode rejects old-format edges")
        print(f"         result: {json.dumps(result_strict, indent=4)}")

    # 14. Uncertain edges flagged (justification contains "?")
    uncertain_spec = {
        "treatment": "X",
        "outcome": "Y",
        "edges": [
            {"from": "X", "to": "Y", "temporal_justification": "Treatment precedes outcome"},
            {"from": "C", "to": "X", "temporal_justification": "C measured before X?"},
            {"from": "C", "to": "Y", "temporal_justification": "C affects Y"},
        ],
        "proposed_controls": ["C"],
    }
    result_uncertain = validate(uncertain_spec)
    if result_uncertain.get("uncertain_edges") == ["C->X"]:
        passed += 1
        print("  [PASS] Uncertain edge flagged (justification contains '?')")
    else:
        failed += 1
        print("  [FAIL] Uncertain edge flagged (justification contains '?')")
        print(f"         uncertain_edges: {result_uncertain.get('uncertain_edges')}")

    # 15. Old-format edges accepted in non-strict mode with warning
    non_strict_old = {
        "treatment": "X",
        "outcome": "Y",
        "edges": [["X", "Y"]],
        "proposed_controls": [],
    }
    result_non_strict = validate(non_strict_old)
    if result_non_strict["valid"] and result_non_strict.get("edge_warnings"):
        passed += 1
        print("  [PASS] Old-format edges accepted in non-strict mode with warning")
    else:
        failed += 1
        print("  [FAIL] Old-format edges accepted in non-strict mode with warning")
        print(f"         valid={result_non_strict['valid']}, warnings={result_non_strict.get('edge_warnings')}")

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)


def run_consensus_tests():
    """Test cases for --consensus mode."""
    passed = 0
    failed = 0

    print("Running consensus tests...\n")

    # CT1: 5 specs, 3 agree on M->Y edge, 2 don't
    base_edges = [["C", "X"], ["C", "Y"], ["X", "Y"]]
    specs_agree = [
        {"treatment": "X", "outcome": "Y", "edges": base_edges + [["M", "Y"]], "proposed_controls": ["C"]},
        {"treatment": "X", "outcome": "Y", "edges": base_edges + [["M", "Y"]], "proposed_controls": ["C"]},
        {"treatment": "X", "outcome": "Y", "edges": base_edges + [["M", "Y"]], "proposed_controls": ["C"]},
        {"treatment": "X", "outcome": "Y", "edges": base_edges, "proposed_controls": ["C"]},
        {"treatment": "X", "outcome": "Y", "edges": base_edges, "proposed_controls": ["C"]},
    ]
    result = consensus(specs_agree)
    m_y_agreement = result["edge_agreement"].get("M->Y", {}).get("agreement", 0)
    # M->Y is in 3/5 = 0.6 => exactly at threshold, should be consensus
    if m_y_agreement == 0.6 and ["M", "Y"] in result["consensus_edges"]:
        passed += 1
        print("  [PASS] CT1: 3/5 agree on M->Y (60% = threshold)")
    else:
        failed += 1
        print(f"  [FAIL] CT1: M->Y agreement={m_y_agreement}, in consensus={['M','Y'] in result.get('consensus_edges', [])}")

    # CT2: All-identical specs → 100% agreement
    identical = [
        {"treatment": "X", "outcome": "Y", "edges": [["C", "X"], ["C", "Y"], ["X", "Y"]], "proposed_controls": ["C"]},
    ] * 4
    result2 = consensus(identical)
    all_100 = all(v["agreement"] == 1.0 for v in result2["edge_agreement"].values())
    if all_100 and len(result2["contested_edges"]) == 0:
        passed += 1
        print("  [PASS] CT2: Identical specs → 100% agreement, no contested")
    else:
        failed += 1
        print(f"  [FAIL] CT2: all_100={all_100}, contested={result2['contested_edges']}")

    # CT3: Completely different specs → low agreement
    diff_specs = [
        {"treatment": "X", "outcome": "Y", "edges": [["X", "Y"], ["A", "X"], ["A", "Y"]], "proposed_controls": ["A"]},
        {"treatment": "X", "outcome": "Y", "edges": [["X", "Y"], ["B", "X"], ["B", "Y"]], "proposed_controls": ["B"]},
        {"treatment": "X", "outcome": "Y", "edges": [["X", "Y"], ["D", "X"], ["D", "Y"]], "proposed_controls": ["D"]},
    ]
    result3 = consensus(diff_specs)
    # X->Y is in all 3, but A/B/D edges are unique → each 33% agreement → contested
    n_contested = len(result3["contested_edges"])
    if n_contested >= 6 and "Low" in result3["recommendation"]:
        passed += 1
        print("  [PASS] CT3: Different specs → low agreement, many contested")
    else:
        failed += 1
        print(f"  [FAIL] CT3: contested={n_contested}, recommendation={result3['recommendation']}")

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
