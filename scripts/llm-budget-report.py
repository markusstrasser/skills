#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.llm_dispatch import DEFAULT_TELEMETRY_PATH, PROFILES


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def usage_value(row: dict[str, object], key: str) -> float | None:
    usage = row.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if value in (None, 0, 0.0):
        return None
    return float(value)


def recommend_budget(current_limit: int | None, observed_prompt_tokens: list[float], observed_context_estimates: list[float]) -> int | None:
    if current_limit is None:
        return None
    if not observed_prompt_tokens:
        return current_limit
    p95_prompt = percentile(observed_prompt_tokens, 0.95)
    p99_prompt = percentile(observed_prompt_tokens, 0.99)
    observed_peak = max(max(observed_prompt_tokens), max(observed_context_estimates) if observed_context_estimates else 0)
    recommended = max(int(p95_prompt * 1.5), int(p99_prompt * 1.2), int(observed_peak * 1.1))
    recommended = max(4_000, recommended)
    return min(current_limit, recommended)


def build_report(entries: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for entry in entries:
        grouped[str(entry.get("requested_profile") or "unknown")].append(entry)

    profiles: dict[str, object] = {}
    for profile_name, rows in grouped.items():
        prompt_tokens = [
            value
            for row in rows
            for value in [usage_value(row, "prompt_tokens")]
            if value is not None
        ]
        completion_tokens = [
            value
            for row in rows
            for value in [usage_value(row, "completion_tokens")]
            if value is not None
        ]
        context_estimates = [
            float(row["context_token_estimate"])
            for row in rows
            if row.get("context_token_estimate") is not None
        ]
        status_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            status_counts[str(row.get("status") or "unknown")] += 1

        configured_limit = PROFILES.get(profile_name).input_token_limit if profile_name in PROFILES else None
        profiles[profile_name] = {
            "samples": len(rows),
            "usage_samples": len(prompt_tokens),
            "configured_input_limit": configured_limit,
            "status_counts": dict(sorted(status_counts.items())),
            "prompt_tokens": {
                "p50": round(percentile(prompt_tokens, 0.50), 1) if prompt_tokens else None,
                "p95": round(percentile(prompt_tokens, 0.95), 1) if prompt_tokens else None,
                "p99": round(percentile(prompt_tokens, 0.99), 1) if prompt_tokens else None,
                "max": round(max(prompt_tokens), 1) if prompt_tokens else None,
            },
            "context_token_estimate": {
                "p50": round(percentile(context_estimates, 0.50), 1) if context_estimates else None,
                "p95": round(percentile(context_estimates, 0.95), 1) if context_estimates else None,
                "p99": round(percentile(context_estimates, 0.99), 1) if context_estimates else None,
                "max": round(max(context_estimates), 1) if context_estimates else None,
            },
            "completion_tokens": {
                "p50": round(percentile(completion_tokens, 0.50), 1) if completion_tokens else None,
                "p95": round(percentile(completion_tokens, 0.95), 1) if completion_tokens else None,
                "max": round(max(completion_tokens), 1) if completion_tokens else None,
            },
            "recommended_safe_input_budget": recommend_budget(configured_limit, prompt_tokens, context_estimates),
        }

    return {
        "telemetry_path": str(DEFAULT_TELEMETRY_PATH),
        "profile_count": len(profiles),
        "profiles": profiles,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize llm dispatch telemetry and recommend safe profile budgets")
    parser.add_argument("--telemetry", type=Path, default=DEFAULT_TELEMETRY_PATH)
    parser.add_argument("--json", action="store_true", help="Emit raw JSON summary")
    args = parser.parse_args()

    if not args.telemetry.exists():
        print(f"telemetry file not found: {args.telemetry}")
        return 1

    entries = [json.loads(line) for line in args.telemetry.read_text().splitlines() if line.strip()]
    report = build_report(entries)
    report["telemetry_path"] = str(args.telemetry)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(f"Telemetry: {args.telemetry}")
    for profile_name, stats in sorted(report["profiles"].items()):
        print(f"\n[{profile_name}]")
        print(f"  samples: {stats['samples']}")
        print(f"  configured_input_limit: {stats['configured_input_limit']}")
        print(f"  recommended_safe_input_budget: {stats['recommended_safe_input_budget']}")
        print(f"  status_counts: {stats['status_counts']}")
        print(f"  prompt_tokens: {stats['prompt_tokens']}")
        print(f"  context_token_estimate: {stats['context_token_estimate']}")
        print(f"  completion_tokens: {stats['completion_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
