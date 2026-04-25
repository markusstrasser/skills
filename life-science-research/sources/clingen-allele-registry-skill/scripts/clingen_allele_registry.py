#!/usr/bin/env python3
"""ClinGen Allele Registry client. JSON-on-stdin, compact JSON-on-stdout."""

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

BASE = "https://reg.clinicalgenome.org"


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
    hgvs = payload.get("hgvs")
    ca_id = payload.get("ca_id")
    if not (hgvs or ca_id):
        raise ValueError("Provide `hgvs` or `ca_id`.")
    if hgvs and not isinstance(hgvs, str):
        raise ValueError("`hgvs` must be a string.")
    if ca_id and not isinstance(ca_id, str):
        raise ValueError("`ca_id` must be a string.")
    return {
        "hgvs": hgvs,
        "ca_id": ca_id,
        "max_items": int(payload.get("max_items", 8)),
        "max_depth": int(payload.get("max_depth", 3)),
        "timeout_sec": int(payload.get("timeout_sec", 30)),
        "save_raw": bool(payload.get("save_raw", False)),
        "raw_output_path": payload.get("raw_output_path"),
    }


def fetch(args: dict[str, Any]) -> dict[str, Any]:
    if args["ca_id"]:
        url = f"{BASE}/allele/{args['ca_id']}"
        params = {}
    else:
        url = f"{BASE}/allele"
        params = {"hgvs": args["hgvs"]}
    r = requests.get(url, params=params, timeout=args["timeout_sec"], headers={"Accept": "application/json"})
    if r.status_code == 404:
        raise LookupError("Variant not in registry.")
    r.raise_for_status()
    return r.json()


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
    except ValueError as exc:
        print(json.dumps(error("invalid_response", str(exc))))
        return 1

    out: dict[str, Any] = {"ok": True, "source": "clingen-allele-registry"}
    if isinstance(data, dict):
        out["caid"] = data.get("@id", "").rsplit("/", 1)[-1] or data.get("communityStandardTitle")
        out["summary"] = _compact(
            {
                "genomicAlleles": data.get("genomicAlleles", []),
                "externalRecords_keys": list((data.get("externalRecords") or {}).keys()),
                "transcriptAlleles_count": len(data.get("transcriptAlleles", []) or []),
                "proteinEffect_keys": list((data.get("aminoAcidAlleles", [{}])[0] or {}).keys())
                if data.get("aminoAcidAlleles") else [],
            },
            args["max_items"],
            args["max_depth"],
        )
    if args["save_raw"]:
        path = Path(args["raw_output_path"] or "/tmp/clingen_allele_registry_raw.json")
        path.write_text(json.dumps(data, indent=2))
        out["raw_output_path"] = str(path)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
