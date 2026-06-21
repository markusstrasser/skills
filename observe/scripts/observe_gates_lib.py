"""Composable, deterministic gates for /observe — inspectable promotion R/P.

Consumers: observe_gates.py CLI, tests, future harness-eval. No LLM calls.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from observe_artifacts import (
    CANDIDATES_JSONL,
    CODEX_MD,
    INPUT_MD,
    artifact_root,
    improvement_log_path,
    project_root,
)

DEFAULT_DB = Path.home() / ".claude" / "agentlogs.db"
MANIFEST_ROW = re.compile(r"\|\s*([0-9a-f]{8})\s*\|")
SESSION_IN_TEXT = re.compile(
    r"(?:session[_\s-]?id|Session|uuid)\s*[:=]?\s*([0-9a-f]{8})\b", re.I
)
HEX8 = re.compile(r"\b([0-9a-f]{8})\b")
_LAUNCHD_MARKERS = re.compile(
    r"\b(launchctl|LaunchAgents|pulse-tick|maintain-tick|agentlogs\s+index|"
    r"com\.agent-infra\.)\b",
    re.I,
)
_MIN_RECURRENCE = 2
_STALE_INDEX_HOURS = 6


@dataclass
class HealthReport:
    indexer_ok: bool
    promotions_allowed: bool
    last_index_status: str | None
    last_index_at: str | None
    last_index_error: str | None
    launchd_agentlogs_exit: int | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "observe.health.v1",
            "indexer_ok": self.indexer_ok,
            "promotions_allowed": self.promotions_allowed,
            "last_index_status": self.last_index_status,
            "last_index_at": self.last_index_at,
            "last_index_error": self.last_index_error,
            "launchd_agentlogs_exit": self.launchd_agentlogs_exit,
            "warnings": self.warnings,
        }


@dataclass
class PromotionVerdict:
    candidate_id: str
    verdict: str  # promote | obs | suppress | needs_evidence
    gates: dict[str, str]
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "observe.promotion_verdict.v1",
            "candidate_id": self.candidate_id,
            "verdict": self.verdict,
            "gates": self.gates,
            "reasons": self.reasons,
        }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def manifest_session_ids(*paths: Path) -> set[str]:
    ids: set[str] = set()
    for p in paths:
        if not p.is_file():
            continue
        ids.update(MANIFEST_ROW.findall(p.read_text(encoding="utf-8", errors="ignore")))
        for m in SESSION_IN_TEXT.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            ids.add(m.group(1))
    return ids


def _launchd_exit(label: str) -> int | None:
    try:
        r = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit():
                return int(parts[0])
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def check_health(db_path: Path = DEFAULT_DB) -> HealthReport:
    warnings: list[str] = []
    last_status = last_at = last_err = None
    indexer_ok = False

    if not db_path.is_file():
        warnings.append(f"agentlogs db missing: {db_path}")
        return HealthReport(False, False, None, None, None, None, warnings)

    con = sqlite3.connect(f"file://{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT status, started_at, ended_at, error_message "
            "FROM indexer_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if row:
            last_status = row["status"]
            last_at = row["ended_at"] or row["started_at"]
            last_err = row["error_message"]
            if last_status == "success":
                indexer_ok = True
            elif last_status == "running" and last_at:
                try:
                    started = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) - started < timedelta(hours=2):
                        indexer_ok = True
                        warnings.append("indexer run still running (<2h) — treat as ok")
                except ValueError:
                    pass
            if last_at and last_status != "success":
                try:
                    ended = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) - ended < timedelta(hours=_STALE_INDEX_HOURS):
                        warnings.append(
                            f"last indexer status={last_status} within {_STALE_INDEX_HOURS}h"
                        )
                except ValueError:
                    pass
    finally:
        con.close()

    launchd_exit = _launchd_exit("com.agent-infra.agentlogs-index")
    if launchd_exit not in (None, 0):
        warnings.append(f"launchd com.agent-infra.agentlogs-index exit={launchd_exit}")
        if launchd_exit != 0:
            indexer_ok = False

    promotions_allowed = indexer_ok
    if not indexer_ok:
        warnings.append(
            "agentlogs-derived promotion blocked — fix indexer before promoting failures/supervision/blindspot"
        )

    return HealthReport(
        indexer_ok=indexer_ok,
        promotions_allowed=promotions_allowed,
        last_index_status=last_status,
        last_index_at=last_at,
        last_index_error=(last_err or "")[:200] or None,
        launchd_agentlogs_exit=launchd_exit,
        warnings=warnings,
    )


def _coverage_hits(summary: str, log_text: str, digest_text: str) -> list[str]:
    """Return lines in log/digest that loosely match summary tokens."""
    tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", summary)][:8]
    if not tokens:
        return []
    hits: list[str] = []
    for blob_name, blob in (("improvement-log", log_text), ("coverage-digest", digest_text)):
        for i, line in enumerate(blob.splitlines()):
            low = line.lower()
            if sum(1 for t in tokens if t in low) >= min(2, len(tokens)):
                hits.append(f"{blob_name}:{i+1}:{line.strip()[:120]}")
                if len(hits) >= 3:
                    return hits
    return hits


def _session_gate(sessions: list[str], manifest: set[str]) -> tuple[str, str]:
    if not sessions:
        return "fail", "no sessions listed"
    known = [s for s in sessions if any(s.startswith(m) or m.startswith(s[:8]) for m in manifest)]
    if not known and manifest:
        return "fail", f"sessions {sessions} not in manifest ({len(manifest)} ids)"
    if not manifest:
        return "warn", "no manifest session table — cannot verify ids"
    return "pass", f"{len(known)}/{len(sessions)} sessions in manifest"


def verdict_for_candidate(
    cand: dict[str, Any],
    *,
    manifest: set[str],
    log_text: str,
    digest_text: str,
    promotions_allowed: bool,
    require_recurrence: bool = True,
) -> PromotionVerdict:
    cid = cand.get("candidate_id") or cand.get("id") or "unknown"
    reasons: list[str] = []
    gates: dict[str, str] = {}

    recurrence = int(cand.get("recurrence") or 0)
    sessions = list(cand.get("sessions") or [])
    if not sessions and cand.get("session_id"):
        sessions = [cand["session_id"]]
    distinct = len({s[:8] for s in sessions})
    if require_recurrence and distinct < _MIN_RECURRENCE and recurrence < _MIN_RECURRENCE:
        gates["recurrence"] = "fail"
        reasons.append(f"recurrence {recurrence} / {distinct} sessions < {_MIN_RECURRENCE}")
    else:
        gates["recurrence"] = "pass"

    sg_status, sg_note = _session_gate(sessions, manifest)
    gates["session_manifest"] = sg_status
    if sg_status == "fail":
        reasons.append(sg_note)

    summary = cand.get("summary") or cand.get("pattern_summary") or ""
    hits = _coverage_hits(summary, log_text, digest_text)
    dedupe = cand.get("dedupe_status") or ""
    existing = cand.get("existing_coverage_match")
    if existing and str(existing).lower() not in ("null", "none", ""):
        gates["existing_coverage"] = "matched"
        reasons.append(f"existing_coverage_match={existing}")
    elif hits or dedupe == "matched":
        gates["existing_coverage"] = "matched"
        if hits:
            reasons.append(f"coverage hit: {hits[0]}")
    else:
        gates["existing_coverage"] = "novel"

    checkable = bool(cand.get("checkable"))
    gates["checkable"] = "pass" if checkable else "fail"
    if not checkable:
        reasons.append("not checkable — route to [obs] not [ ]")

    mode = cand.get("mode") or ""
    if mode in ("failures", "supervision", "blindspot") and not promotions_allowed:
        gates["indexer_health"] = "fail"
        reasons.append("indexer unhealthy — block agentlogs-sourced promotion")
    else:
        gates["indexer_health"] = "pass"

    failed = [g for g, v in gates.items() if v == "fail"]
    if failed:
        if "checkable" in failed and gates.get("existing_coverage") == "matched":
            verdict = "obs"
        elif "recurrence" in failed or "session_manifest" in failed:
            verdict = "needs_evidence"
        else:
            verdict = "suppress"
    elif gates.get("existing_coverage") == "matched":
        verdict = "obs"
    elif checkable and gates.get("recurrence") == "pass":
        verdict = "promote"
    else:
        verdict = "needs_evidence"

    return PromotionVerdict(cid, verdict, gates, reasons)


def promote_check(
    artifact_dir: Path | None = None,
    *,
    promotions_allowed: bool | None = None,
) -> list[PromotionVerdict]:
    root = artifact_dir or artifact_root()
    candidates = load_jsonl(root / CANDIDATES_JSONL)
    manifest = manifest_session_ids(root / INPUT_MD, root / CODEX_MD)
    log_path = improvement_log_path()
    log_text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.is_file() else ""
    digest_path = root / "coverage-digest.txt"
    digest_text = digest_path.read_text(encoding="utf-8", errors="ignore") if digest_path.is_file() else ""

    if promotions_allowed is None:
        promotions_allowed = check_health().promotions_allowed

    # Latest row per candidate_id wins
    by_id: dict[str, dict[str, Any]] = {}
    for c in candidates:
        cid = c.get("candidate_id") or c.get("id")
        if cid:
            by_id[cid] = c

    return [
        verdict_for_candidate(
            c,
            manifest=manifest,
            log_text=log_text,
            digest_text=digest_text,
            promotions_allowed=promotions_allowed,
        )
        for c in by_id.values()
    ]


def saturation_check(
    artifact_dir: Path | None = None,
    *,
    lookback_runs: int = 5,
    overlap_threshold: float = 0.6,
) -> dict[str, Any]:
    root = artifact_dir or artifact_root()
    observe_root = project_root() / "artifacts" / "observe"
    current = load_jsonl(root / CANDIDATES_JSONL)
    current_ids = {c.get("candidate_id") for c in current if c.get("candidate_id")}
    current_tokens: set[str] = set()
    for c in current:
        summary = c.get("summary") or ""
        current_tokens.update(t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", summary))

    prior_dirs = sorted(
        [p for p in observe_root.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    prior_ids: set[str] = set()
    prior_tokens: set[str] = set()
    compared_runs: list[str] = []
    for d in prior_dirs:
        if d.resolve() == root.resolve():
            continue
        if len(compared_runs) >= lookback_runs:
            break
        rows = load_jsonl(d / CANDIDATES_JSONL)
        if not rows:
            continue
        compared_runs.append(d.name)
        for c in rows:
            if c.get("candidate_id"):
                prior_ids.add(c["candidate_id"])
            summary = c.get("summary") or ""
            prior_tokens.update(
                t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", summary)
            )

    id_overlap = len(current_ids & prior_ids) / max(1, len(current_ids))
    token_overlap = len(current_tokens & prior_tokens) / max(1, len(current_tokens))
    saturated = id_overlap >= overlap_threshold or (
        len(current_ids) > 0 and token_overlap >= overlap_threshold
    )

    return {
        "schema": "observe.saturation.v1",
        "artifact_dir": str(root),
        "candidate_count": len(current_ids),
        "compared_runs": compared_runs,
        "id_overlap": round(id_overlap, 3),
        "token_overlap": round(token_overlap, 3),
        "saturated": saturated,
        "promotions_suppressed": saturated,
        "note": (
            "coverage saturated — digest should say so; do not promote without novel candidates"
            if saturated
            else "novelty ok"
        ),
    }


def run_preflight(artifact_dir: Path | None = None) -> dict[str, Any]:
    root = artifact_dir or artifact_root()
    health = check_health()
    saturation = saturation_check(root)
    verdicts = promote_check(root, promotions_allowed=health.promotions_allowed)
    counts = {}
    for v in verdicts:
        counts[v.verdict] = counts.get(v.verdict, 0) + 1

    report = {
        "schema": "observe.preflight.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(root),
        "health": health.to_dict(),
        "saturation": saturation,
        "promotion_counts": counts,
        "promotions_allowed": health.promotions_allowed and not saturation["saturated"],
    }
    out = root / "preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    verdicts_path = root / "promotion-verdicts.jsonl"
    with verdicts_path.open("w", encoding="utf-8") as fh:
        for v in verdicts:
            fh.write(json.dumps(v.to_dict(), ensure_ascii=False) + "\n")

    return report
