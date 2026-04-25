#!/usr/bin/env python3
"""MaveDB REST client. JSON-on-stdin, compact JSON-on-stdout."""

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

BASE = "https://api.mavedb.org/api/v1"
MODES = {"search", "score_set", "variants"}


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
        "gene": payload.get("gene"),
        "uniprot": payload.get("uniprot"),
        "urn": payload.get("urn"),
        "limit": int(payload.get("limit", 20)),
        "max_items": int(payload.get("max_items", 8)),
        "max_depth": int(payload.get("max_depth", 3)),
        "timeout_sec": int(payload.get("timeout_sec", 60)),
        "save_raw": bool(payload.get("save_raw", False)),
        "raw_output_path": payload.get("raw_output_path"),
    }
    if mode == "search" and not (args["gene"] or args["uniprot"]):
        raise ValueError("`search` mode requires `gene` or `uniprot`.")
    if mode in {"score_set", "variants"} and not args["urn"]:
        raise ValueError(f"`{mode}` mode requires `urn`.")
    return args


def fetch(args: dict[str, Any]) -> dict[str, Any]:
    timeout = args["timeout_sec"]
    if args["mode"] == "search":
        url = f"{BASE}/score-sets/search"
        body = {"text": args["gene"] or args["uniprot"]}
        r = requests.post(url, json=body, timeout=timeout)
    elif args["mode"] == "score_set":
        r = requests.get(f"{BASE}/score-sets/{args['urn']}", timeout=timeout)
    else:  # variants
        r = requests.get(
            f"{BASE}/score-sets/{args['urn']}/variants",
            params={"limit": args["limit"]},
            timeout=timeout,
        )
    if r.status_code == 404:
        raise LookupError(f"Not found: {r.url}")
    r.raise_for_status()
    return r.json()


def summarize(mode: str, data: Any, max_items: int, max_depth: int) -> Any:
    if mode == "search" and isinstance(data, list):
        return [
            {
                "urn": s.get("urn"),
                "title": s.get("title"),
                "target": (s.get("targetGenes") or [{}])[0].get("name"),
                "assay": (s.get("targetGenes") or [{}])[0].get("category"),
                "numVariants": s.get("numVariants"),
            }
            for s in data[:max_items]
        ]
    if mode == "score_set" and isinstance(data, dict):
        return _compact(
            {
                "urn": data.get("urn"),
                "title": data.get("title"),
                "publishedDate": data.get("publishedDate"),
                "numVariants": data.get("numVariants"),
                "targets": [t.get("name") for t in data.get("targetGenes", [])],
                "scoreCalibrations_keys": list((data.get("scoreCalibrations") or {}).keys()),
            },
            max_items,
            max_depth,
        )
    return _compact(data, max_items, max_depth)


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
    except LookupError as exc:
        print(json.dumps(error("not_found", str(exc))))
        return 1
    except requests.RequestException as exc:
        print(json.dumps(error("network_error", str(exc))))
        return 1

    out = {
        "ok": True,
        "source": "mavedb",
        "mode": args["mode"],
        "summary": summarize(args["mode"], data, args["max_items"], args["max_depth"]),
    }
    if args["save_raw"]:
        path = Path(args["raw_output_path"] or "/tmp/mavedb_raw.json")
        path.write_text(json.dumps(data, indent=2))
        out["raw_output_path"] = str(path)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
