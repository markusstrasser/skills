#!/usr/bin/env python3
"""gnomAD-SV v4 GraphQL client. JSON-on-stdin, compact JSON-on-stdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError as exc:  # pragma: no cover
    requests = None
    REQUESTS_IMPORT_ERROR = exc
else:
    REQUESTS_IMPORT_ERROR = None

ENDPOINT = "https://gnomad.broadinstitute.org/api"
MODES = {"variant", "region", "gene", "raw"}

VARIANT_QUERY = """
query SV($variantId: String!, $dataset: StructuralVariantDatasetId!) {
  structural_variant(variantId: $variantId, dataset: $dataset) {
    variantId chrom pos end length type filters
    ac an af homozygote_count
    populations { id ac an af }
    consequences { consequence gene_symbol }
  }
}
""".strip()

REGION_QUERY = """
query Region($chrom: String!, $start: Int!, $stop: Int!,
             $referenceGenome: ReferenceGenomeId!,
             $dataset: StructuralVariantDatasetId!) {
  region(chrom: $chrom, start: $start, stop: $stop,
         reference_genome: $referenceGenome) {
    structural_variants(dataset: $dataset) {
      variantId type chrom pos end length ac an af filters
    }
  }
}
""".strip()

GENE_QUERY = """
query Gene($symbol: String!, $referenceGenome: ReferenceGenomeId!,
           $dataset: StructuralVariantDatasetId!) {
  gene(gene_symbol: $symbol, reference_genome: $referenceGenome) {
    gene_id symbol
    structural_variants(dataset: $dataset) {
      variantId type chrom pos end length ac an af filters
      consequences { consequence }
    }
  }
}
""".strip()


def error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _compact(value: Any, max_items: int, max_depth: int) -> Any:
    if isinstance(value, str):
        return value if len(value) <= 240 else value[:240] + "..."
    if max_depth <= 0:
        return "..." if isinstance(value, (dict, list)) else value
    if isinstance(value, list):
        list_out: list[Any] = [_compact(v, max_items, max_depth - 1) for v in value[:max_items]]
        if len(value) > max_items:
            list_out.append(f"... (+{len(value) - max_items} more)")
        return list_out
    if isinstance(value, dict):
        items = list(value.items())
        dict_out: dict[str, Any] = {}
        for k, v in items[:max_items]:
            dict_out[str(k)] = _compact(v, max_items, max_depth - 1)
        if len(items) > max_items:
            dict_out["_truncated_keys"] = len(items) - max_items
        return dict_out
    return value


def parse_input(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input must be one JSON object.")
    mode = payload.get("mode")
    if mode not in MODES:
        raise ValueError(f"`mode` must be one of {sorted(MODES)}.")
    args: dict[str, Any] = {
        "mode": mode,
        "variantId": payload.get("variantId"),
        "chrom": payload.get("chrom"),
        "start": payload.get("start"),
        "stop": payload.get("stop"),
        "gene": payload.get("gene"),
        "query": payload.get("query"),
        "variables": payload.get("variables") or {},
        "dataset": payload.get("dataset", "gnomad_sv_r4"),
        "referenceGenome": payload.get("referenceGenome", "GRCh38"),
        "max_items": int(payload.get("max_items", 5)),
        "max_depth": int(payload.get("max_depth", 4)),
        "timeout_sec": int(payload.get("timeout_sec", 60)),
        "save_raw": bool(payload.get("save_raw", False)),
        "raw_output_path": payload.get("raw_output_path"),
    }
    if mode == "variant" and not args["variantId"]:
        raise ValueError("`variant` mode requires `variantId`.")
    if mode == "region" and not (args["chrom"] and args["start"] is not None and args["stop"] is not None):
        raise ValueError("`region` mode requires `chrom`, `start`, `stop`.")
    if mode == "gene" and not args["gene"]:
        raise ValueError("`gene` mode requires `gene`.")
    if mode == "raw" and not args["query"]:
        raise ValueError("`raw` mode requires `query`.")
    return args


def fetch(args: dict[str, Any]) -> dict[str, Any]:
    mode = args["mode"]
    if mode == "variant":
        body = {"query": VARIANT_QUERY, "variables": {"variantId": args["variantId"], "dataset": args["dataset"]}}
    elif mode == "region":
        body = {
            "query": REGION_QUERY,
            "variables": {
                "chrom": str(args["chrom"]),
                "start": int(args["start"]),
                "stop": int(args["stop"]),
                "referenceGenome": args["referenceGenome"],
                "dataset": args["dataset"],
            },
        }
    elif mode == "gene":
        body = {
            "query": GENE_QUERY,
            "variables": {
                "symbol": args["gene"],
                "referenceGenome": args["referenceGenome"],
                "dataset": args["dataset"],
            },
        }
    else:
        body = {"query": args["query"], "variables": args["variables"]}
    r = requests.post(ENDPOINT, json=body, timeout=args["timeout_sec"])
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(json.dumps(payload["errors"]))
    return payload.get("data", {})


def main() -> int:
    if REQUESTS_IMPORT_ERROR is not None:
        print(json.dumps(error("import_error", f"requests missing: {REQUESTS_IMPORT_ERROR}")))
        return 1
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        print(json.dumps(error("invalid_json", str(exc))))
        return 1
    try:
        args = parse_input(payload)
    except ValueError as exc:
        print(json.dumps(error("invalid_input", str(exc))))
        return 1
    try:
        data = fetch(args)
    except RuntimeError as exc:
        print(json.dumps(error("graphql_error", str(exc))))
        return 1
    except requests.RequestException as exc:
        print(json.dumps(error("network_error", str(exc))))
        return 1

    out = {
        "ok": True,
        "source": "gnomad-sv",
        "mode": args["mode"],
        "dataset": args["dataset"],
        "summary": _compact(data, args["max_items"], args["max_depth"]),
    }
    if args["save_raw"]:
        path = Path(args["raw_output_path"] or "/tmp/gnomad_sv_raw.json")
        path.write_text(json.dumps(data, indent=2))
        out["raw_output_path"] = str(path)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
