#!/usr/bin/env python3
"""verify_citations.py — citation rate-gate for /research memos.

Deterministic, ZERO third-party deps (stdlib only). Extracts arXiv IDs + DOIs
from a finalized research memo, resolves each against public keyless APIs
(Crossref, arXiv, DBLP), and emits a coverage report.

The ONE blocking gate is `hallucinated > 0` — a citation that resolves to
nothing (the dangerous citable-slop case). Every other threshold is ADVISORY
(constitution P3: measure before enforcing). Transient network failures are
reported as `unreachable` and DO NOT block (no false-fail on a flaky API).

Grounding (ADR agent-infra/decisions/2026-06-19-autoresearch-grounding-imports.md):
the `corpus` CLI resolves *ingested* papers (per-repo store, keyed by --corpus-root),
but most cited papers are not in the store, so this hits the public APIs directly and
covers them too. And `verify_claim`/scite are in-session MCP tools that cannot run from
a standalone script. Hence: keyless public-API resolution, zero third-party deps.

Usage:
    verify_citations.py MEMO.md            # human-readable dispatch brief
    verify_citations.py MEMO.md --json     # machine-readable report
    verify_citations.py MEMO.md --max 200  # cap citations resolved (politeness)
Exit: non-zero iff hallucinated > 0 (the blocking gate).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict

# --- config ------------------------------------------------------------------
MAILTO = "ax.strasser@gmail.com"  # Crossref polite pool
UA = f"verify_citations/1.0 (mailto:{MAILTO})"
TIMEOUT = 12
WORKERS = 6

# advisory thresholds (P3: measured first, promoted to blocking only on a real miss)
RESOLVED_RATE_MIN = 0.80      # advisory
ARXIV_ONLY_RATIO_MAX = 0.60   # advisory

CROSSREF = "https://api.crossref.org/works/{doi}?mailto=" + urllib.parse.quote(MAILTO)
ARXIV = "http://export.arxiv.org/api/query?id_list={aid}"
DBLP = "https://dblp.org/search/publ/api?format=json&h=3&q={q}"

ATOM = "{http://www.w3.org/2005/Atom}"
ARX = "{http://arxiv.org/schemas/atom}"

# --- extraction --------------------------------------------------------------
# arXiv new-style IDs: YYMM.NNNNN (4-5 digit suffix), optional version.
ARXIV_RE = re.compile(r"(?:arxiv[:\s/]*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
# DOIs: 10.NNNN/suffix — strip trailing markdown/sentence punctuation.
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s)\]\}\"<>]+", re.I)
_DOI_TRAIL = '.,;:)]}>"\''


def extract(text: str) -> tuple[set[str], set[str]]:
    arxiv = {m.group(1) for m in ARXIV_RE.finditer(text)}
    dois = set()
    for m in DOI_RE.finditer(text):
        d = m.group(0)
        while d and d[-1] in _DOI_TRAIL:
            d = d[:-1]
        # a doi.org URL leaves a bare doi; lowercase the registrant-agnostic prefix
        dois.add(d)
    return arxiv, dois


# --- HTTP --------------------------------------------------------------------
class Unreachable(Exception):
    """Transient failure (timeout / 5xx / network) — NOT a hallucination."""


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return b""  # definitive: does not exist
        raise Unreachable(f"{url} -> HTTP {e.code}")
    except Exception as e:  # noqa: BLE001 — URLError, timeout, socket, etc.
        raise Unreachable(f"{url} -> {e}")


# --- resolvers ---------------------------------------------------------------
@dataclass
class Cite:
    kind: str            # "arxiv" | "doi"
    raw: str
    status: str = "?"    # resolved | hallucinated | unreachable
    title: str = ""
    year: str = ""
    venue: str = ""      # "" => preprint-only
    arxiv_only: bool = False
    upgrade: str = ""    # DBLP venue if an arxiv-only paper has a published version
    note: str = ""


def resolve_doi(doi: str) -> Cite:
    c = Cite(kind="doi", raw=doi)
    try:
        body = _get(CROSSREF.format(doi=urllib.parse.quote(doi, safe="")))
    except Unreachable as e:
        c.status, c.note = "unreachable", str(e)
        return c
    if not body:
        c.status = "hallucinated"
        return c
    msg = json.loads(body).get("message", {})
    c.status = "resolved"
    c.title = (msg.get("title") or [""])[0]
    parts = (msg.get("published") or msg.get("issued") or {}).get("date-parts") or [[None]]
    c.year = str(parts[0][0]) if parts and parts[0] and parts[0][0] else ""
    container = msg.get("container-title") or []
    typ = msg.get("type", "")
    if typ == "posted-content" or (not container and typ not in ("journal-article", "proceedings-article")):
        c.venue, c.arxiv_only = "", True  # preprint
    else:
        c.venue = container[0] if container else typ
    return c


def resolve_arxiv(aid: str) -> Cite:
    c = Cite(kind="arxiv", raw=aid)
    try:
        body = _get(ARXIV.format(aid=urllib.parse.quote(aid)))
    except Unreachable as e:
        c.status, c.note = "unreachable", str(e)
        return c
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        c.status, c.note = "unreachable", "arxiv: unparseable response"
        return c
    entry = root.find(f"{ATOM}entry")
    # arXiv returns a single <entry> with an <id> ending in /api/errors for a bad id
    if entry is None or (entry.findtext(f"{ATOM}id") or "").endswith("errors"):
        c.status = "hallucinated"
        return c
    c.status = "resolved"
    c.title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
    c.year = (entry.findtext(f"{ATOM}published") or "")[:4]
    journal_ref = entry.findtext(f"{ARX}journal_ref")
    doi = entry.findtext(f"{ARX}doi")
    if journal_ref or doi:
        c.venue = journal_ref or "published (has DOI)"
    else:
        c.arxiv_only = True
    return c


def _toks(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2}


def dblp_upgrade(title: str) -> str:
    """Return a published venue ONLY if a DBLP hit's title closely matches `title`.

    Without the title guard, DBLP's approximate search returns a wrong top hit
    (e.g. "Attention Is All You Need" -> DAC 2021), producing misleading upgrade
    suggestions. Require high token overlap so the suggestion names the SAME paper.
    """
    qt = _toks(title)
    if len(qt) < 2:
        return ""
    try:
        body = _get(DBLP.format(q=urllib.parse.quote(title)))
    except Unreachable:
        return ""
    hits = (json.loads(body).get("result", {}).get("hits", {}) or {}).get("hit") or []
    for h in hits:
        info = h.get("info", {})
        typ = info.get("type", "")
        venue = info.get("venue", "")
        if typ not in ("Conference and Workshop Papers", "Journal Articles"):
            continue
        if not venue or venue.lower() == "corr":  # CoRR == arXiv; not an upgrade
            continue
        ht = _toks(info.get("title", ""))
        overlap = len(qt & ht) / len(qt | ht) if (qt | ht) else 0.0  # Jaccard
        if overlap >= 0.6:
            return f"{venue} ({info.get('year','')})"
    return ""


def resolve(c_in: Cite) -> Cite:
    c = resolve_arxiv(c_in.raw) if c_in.kind == "arxiv" else resolve_doi(c_in.raw)
    if c.status == "resolved" and c.arxiv_only:
        c.upgrade = dblp_upgrade(c.title)
    return c


# --- report ------------------------------------------------------------------
@dataclass
class Report:
    total: int = 0
    resolved: int = 0
    hallucinated: int = 0
    unreachable: int = 0
    arxiv_only: int = 0
    resolved_rate: float = 0.0
    arxiv_only_ratio: float = 0.0
    blocking: bool = False
    advisories: list[str] = field(default_factory=list)
    cites: list[dict] = field(default_factory=list)


def build_report(cites: list[Cite]) -> Report:
    r = Report(total=len(cites))
    for c in cites:
        if c.status == "resolved":
            r.resolved += 1
            if c.arxiv_only:
                r.arxiv_only += 1
        elif c.status == "hallucinated":
            r.hallucinated += 1
        elif c.status == "unreachable":
            r.unreachable += 1
    verifiable = r.resolved + r.hallucinated  # exclude unreachable from the rate
    r.resolved_rate = round(r.resolved / verifiable, 3) if verifiable else 1.0
    r.arxiv_only_ratio = round(r.arxiv_only / r.resolved, 3) if r.resolved else 0.0
    r.blocking = r.hallucinated > 0
    if r.resolved_rate < RESOLVED_RATE_MIN:
        r.advisories.append(f"resolved_rate {r.resolved_rate:.0%} < {RESOLVED_RATE_MIN:.0%}")
    if r.arxiv_only_ratio > ARXIV_ONLY_RATIO_MAX:
        r.advisories.append(f"arxiv_only_ratio {r.arxiv_only_ratio:.0%} > {ARXIV_ONLY_RATIO_MAX:.0%}")
    if r.unreachable:
        r.advisories.append(f"{r.unreachable} citation(s) unreachable (not counted; re-run)")
    r.cites = [asdict(c) for c in cites]
    return r


def brief(r: Report) -> str:
    """dispatch-brief 5-line schema (agent-infra .claude/rules/dispatch-brief-schema.md)."""
    halluc = [c["raw"] for c in r.cites if c["status"] == "hallucinated"]
    upgrades = [(c["raw"], c["upgrade"]) for c in r.cites if c.get("upgrade")]
    lines = [
        f"gathered: {r.resolved}/{r.total} citations resolved "
        f"(arxiv-only {r.arxiv_only}, unreachable {r.unreachable})",
        f"missing:  {'HALLUCINATED → ' + ', '.join(halluc) if halluc else 'none unresolvable'}"
        f"{' | advisories: ' + '; '.join(r.advisories) if r.advisories else ''}",
        f"findings: {'BLOCK — hallucinated>0' if r.blocking else 'PASS (blocking gate clear)'}"
        f"; resolved_rate {r.resolved_rate:.0%}; arxiv-only {r.arxiv_only_ratio:.0%}",
        "drill:    verify_citations.py <memo> --json",
        "next:     fix/remove hallucinated cites; venue-upgrade where DBLP shows a published version",
    ]
    if upgrades:
        lines.append("upgrade:  " + "; ".join(f"{a} → {v}" for a, v in upgrades))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Citation rate-gate for /research memos.")
    ap.add_argument("memo", help="path to the research memo (.md)")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--max", type=int, default=300, help="cap citations resolved (politeness)")
    args = ap.parse_args()

    try:
        text = open(args.memo, encoding="utf-8").read()
    except OSError as e:
        print(f"cannot read memo: {e}", file=sys.stderr)
        return 2

    arxiv, dois = extract(text)
    # de-dupe arXiv ids that also appear as a doi.org/10.48550/arXiv.* entry is rare; keep separate.
    inputs = [Cite("arxiv", a) for a in sorted(arxiv)] + [Cite("doi", d) for d in sorted(dois)]
    if len(inputs) > args.max:
        dropped = len(inputs) - args.max
        inputs = inputs[: args.max]
    else:
        dropped = 0

    if not inputs:
        print("gathered: 0 citations found (no arXiv IDs or DOIs in memo)\n"
              "missing:  nothing to verify\nfindings: PASS (vacuous — no citations)\n"
              "drill:    verify_citations.py <memo> --json\nnext:     n/a")
        return 0

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        resolved = list(ex.map(resolve, inputs))

    r = build_report(resolved)
    if dropped:
        r.advisories.append(f"{dropped} citation(s) over --max not checked")
    print(json.dumps(asdict(r), indent=2) if args.json else brief(r))
    return 1 if r.blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
