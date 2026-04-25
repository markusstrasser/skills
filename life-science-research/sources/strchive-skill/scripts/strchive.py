#!/usr/bin/env python3
"""STRchive disease-STR catalog lookup. JSON-on-stdin, compact JSON-on-stdout."""

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

DEFAULT_URL = "https://raw.githubusercontent.com/dashnowlab/STRchive/main/data/STRchive-loci.json"
MODES = {"list", "gene", "disease", "region"}


def error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def parse_input(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input must be one JSON object.")
    mode = payload.get("mode")
    if mode not in MODES:
        raise ValueError(f"`mode` must be one of {sorted(MODES)}.")
    args: dict[str, Any] = {
        "mode": mode,
        "gene": payload.get("gene"),
        "disease": payload.get("disease"),
        "chrom": payload.get("chrom"),
        "start": payload.get("start"),
        "stop": payload.get("stop"),
        "source_url": payload.get("source_url", DEFAULT_URL),
        "max_items": int(payload.get("max_items", 50)),
        "timeout_sec": int(payload.get("timeout_sec", 30)),
        "save_raw": bool(payload.get("save_raw", False)),
        "raw_output_path": payload.get("raw_output_path"),
    }
    if mode == "gene" and not args["gene"]:
        raise ValueError("`gene` mode requires `gene`.")
    if mode == "disease" and not args["disease"]:
        raise ValueError("`disease` mode requires `disease`.")
    if mode == "region" and not (args["chrom"] and args["start"] is not None and args["stop"] is not None):
        raise ValueError("`region` mode requires `chrom`, `start`, `stop`.")
    return args


def fetch_catalog(url: str, timeout: int) -> list[dict[str, Any]]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "loci" in data:
        data = data["loci"]
    if not isinstance(data, list):
        raise ValueError(f"Unexpected catalog shape: {type(data).__name__}")
    return data


def _norm_chrom(c: str | None) -> str:
    return (c or "").lower().lstrip("chr")


def _coord_field(entry: dict[str, Any], build: str) -> tuple[str, int, int] | None:
    for key in (f"{build}", f"chrom_{build}", f"reference_region_{build}"):
        v = entry.get(key)
        if isinstance(v, dict):
            try:
                return (
                    str(v.get("chrom") or v.get("chromosome") or ""),
                    int(v.get("start", 0)),
                    int(v.get("end") or v.get("stop") or 0),
                )
            except (TypeError, ValueError):
                continue
    chrom = entry.get("chrom") or entry.get("chromosome")
    start = entry.get("start_hg38") or entry.get("start")
    end = entry.get("end_hg38") or entry.get("end") or entry.get("stop")
    if chrom and start is not None and end is not None:
        try:
            return str(chrom), int(start), int(end)
        except (TypeError, ValueError):
            return None
    return None


def filter_entries(entries: list[dict[str, Any]], args: dict[str, Any]) -> list[dict[str, Any]]:
    if args["mode"] == "list":
        return entries
    if args["mode"] == "gene":
        target = args["gene"].upper()
        return [e for e in entries if (e.get("gene") or e.get("gene_symbol") or "").upper() == target]
    if args["mode"] == "disease":
        sub = args["disease"].lower()
        return [
            e
            for e in entries
            if sub in (e.get("disease") or e.get("disease_name") or "").lower()
            or sub in (e.get("disease_id") or "").lower()
        ]
    # region
    target_chrom = _norm_chrom(args["chrom"])
    s, t = int(args["start"]), int(args["stop"])
    out: list[dict[str, Any]] = []
    for e in entries:
        coord = _coord_field(e, "hg38")
        if not coord:
            continue
        ec, es, ee = coord
        if _norm_chrom(ec) == target_chrom and ee >= s and es <= t:
            out.append(e)
    return out


def summarize(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("id") or entry.get("locus_id"),
        "gene": entry.get("gene") or entry.get("gene_symbol"),
        "disease": entry.get("disease") or entry.get("disease_name"),
        "inheritance": entry.get("inheritance") or entry.get("inheritance_pattern"),
        "motif": entry.get("motif") or entry.get("repeat_motif"),
        "pathogenic_threshold": entry.get("pathogenic_min")
        or entry.get("pathogenic_threshold")
        or entry.get("pathogenic"),
        "benign_max": entry.get("benign_max") or entry.get("normal_max"),
        "hg38": _coord_field(entry, "hg38"),
        "omim": entry.get("omim") or entry.get("OMIM"),
    }


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
        catalog = fetch_catalog(args["source_url"], args["timeout_sec"])
    except requests.RequestException as exc:
        print(json.dumps(error("network_error", str(exc))))
        return 1
    except ValueError as exc:
        print(json.dumps(error("invalid_response", str(exc))))
        return 1

    matches = filter_entries(catalog, args)
    summary = [summarize(e) for e in matches[: args["max_items"]]]
    out: dict[str, Any] = {
        "ok": True,
        "source": "strchive",
        "mode": args["mode"],
        "count": len(matches),
        "summary": summary,
    }
    if len(matches) > args["max_items"]:
        out["truncated"] = True
    if args["save_raw"]:
        path = Path(args["raw_output_path"] or "/tmp/strchive_raw.json")
        path.write_text(json.dumps(matches, indent=2))
        out["raw_output_path"] = str(path)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
