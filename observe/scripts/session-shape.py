#!/usr/bin/env python3
"""Session shape detector — zero-LLM-cost structural anomaly detection.

Analyzes session topology (tool patterns, message ratios, structural signals)
to flag anomalous sessions worth deep analysis. The deterministic output can
also be written as observe signal/candidate JSONL records for backlog staging.

Usage:
    session-shape.py [--days N] [--project P] [--threshold T] [--json]
        [--signals-out PATH] [--candidates-out PATH]
"""

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, stdev

import os

from observe_artifacts import (
    append_jsonl,
    artifact_path,
    stable_id,
)

# Inlined from meta/scripts/common/paths.py and meta/scripts/config.py
_CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", str(Path.home() / ".claude")))
DB_PATH = Path(os.environ.get("AGENTLOGS_DB", str(_CLAUDE_DIR / "agentlogs.db")))
_METRICS_FILE = _CLAUDE_DIR / "epistemic-metrics.jsonl"


def log_metric(metric_name: str, **fields) -> None:
    """Append a metric entry to epistemic-metrics.jsonl."""
    entry = {"ts": datetime.now().isoformat(), "metric": metric_name, **fields}
    with open(_METRICS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _open_db(path: Path, *, wal: bool = True) -> sqlite3.Connection:
    """Open SQLite DB with consistent policy defaults."""
    path = Path(path)
    db = sqlite3.connect(str(path), timeout=5.0, isolation_level="DEFERRED")
    db.row_factory = sqlite3.Row
    if wal:
        db.execute("PRAGMA journal_mode=WAL")
    return db

# Structural features extracted per session
FEATURE_NAMES = [
    "tool_diversity",       # unique tools / total tool calls
    "read_write_ratio",     # reads / (writes + edits + 1)
    "bash_fraction",        # bash calls / total tool calls
    "agent_fraction",       # agent calls / total tool calls
    "search_density",       # (grep + glob + web) / total
    "transcript_density",   # transcript lines / duration minutes
    "tool_intensity",       # total tool calls / duration minutes
    "mcp_fraction",         # mcp tool calls / total
    "commit_ratio",         # commits / edits
    "read_only_flag",       # 1 if zero writes/edits, else 0
]


@dataclass
class SessionShape:
    uuid: str
    project: str
    start_ts: str
    first_message: str
    duration_min: float
    cost_usd: float
    features: dict = field(default_factory=dict)
    anomaly_score: float = 0.0
    anomaly_reasons: list = field(default_factory=list)


def extract_features(row: sqlite3.Row) -> dict:
    """Extract structural features from a session row."""
    tools_raw = row["tools_used"]
    tools = json.loads(tools_raw) if tools_raw else []
    total_tools = len(tools)

    # Count tool categories
    reads = sum(1 for t in tools if t in ("Read", "Glob", "Grep"))
    writes = sum(1 for t in tools if t in ("Write", "Edit", "NotebookEdit"))
    bashes = sum(1 for t in tools if t == "Bash")
    agents = sum(1 for t in tools if t == "Agent")
    searches = sum(1 for t in tools if t in ("Grep", "Glob", "WebSearch", "WebFetch"))
    mcps = sum(1 for t in tools if t.startswith("mcp__"))

    unique_tools = len(set(tools))
    duration = max(row["duration_min"] or 1.0, 0.1)
    transcript_lines = row["transcript_lines"] or 0

    commits_raw = row["commits"]
    commits = json.loads(commits_raw) if commits_raw else []

    return {
        "tool_diversity": unique_tools / max(total_tools, 1),
        "read_write_ratio": reads / max(writes + 1, 1),
        "bash_fraction": bashes / max(total_tools, 1),
        "agent_fraction": agents / max(total_tools, 1),
        "search_density": searches / max(total_tools, 1),
        "transcript_density": transcript_lines / duration,
        "tool_intensity": total_tools / duration,
        "mcp_fraction": mcps / max(total_tools, 1),
        "commit_ratio": len(commits) / max(writes + 1, 1),
        "read_only_flag": 1.0 if writes == 0 and total_tools > 5 else 0.0,
    }


def compute_anomalies(
    shapes: list[SessionShape], threshold: float = 2.0
) -> list[SessionShape]:
    """Flag sessions where features are > threshold stddevs from mean."""
    if len(shapes) < 5:
        return shapes  # Not enough data for statistics

    # Compute mean/stdev per feature
    stats = {}
    for feat in FEATURE_NAMES:
        values = [s.features.get(feat, 0.0) for s in shapes]
        m = mean(values)
        s = stdev(values) if len(values) > 1 else 1.0
        stats[feat] = (m, max(s, 0.001))

    for shape in shapes:
        score = 0.0
        reasons = []
        for feat in FEATURE_NAMES:
            val = shape.features.get(feat, 0.0)
            m, s = stats[feat]
            z = abs(val - m) / s
            if z > threshold:
                score += z
                direction = "high" if val > m else "low"
                reasons.append(f"{feat}={val:.2f} ({direction}, z={z:.1f})")
        shape.anomaly_score = score
        shape.anomaly_reasons = reasons

    return shapes


def build_signal_record(shape: SessionShape, *, threshold: float) -> dict:
    """Build a deterministic signal record for backlog staging."""
    return {
        "schema": "observe.signal.v1",
        "kind": "session_shape",
        "session_id": shape.uuid,
        "signal_id": stable_id(
            "signal",
            "session_shape",
            shape.uuid,
            shape.project,
        ),
        "project": shape.project,
        "start_ts": shape.start_ts,
        "threshold": threshold,
        "anomaly_score": round(shape.anomaly_score, 3),
        "reasons": list(shape.anomaly_reasons),
        "features": {k: round(v, 6) for k, v in shape.features.items()},
        "first_message": shape.first_message,
        "source": "scripts/session-shape.py",
        "status": "signal",
    }


def build_candidate_record(shape: SessionShape, *, threshold: float) -> dict:
    """Build a candidate backlog record derived from a signal."""
    signal_id = stable_id("signal", "session_shape", shape.uuid, shape.project)
    candidate_summary = (
        f"Session shape anomaly for {shape.project} {shape.uuid[:8]} "
        f"(score {shape.anomaly_score:.1f}, threshold {threshold:.1f})"
    )
    return {
        "schema": "observe.candidate.v1",
        "kind": "session_shape_anomaly",
        "candidate_id": stable_id(
            "candidate",
            "session_shape_anomaly",
            shape.uuid,
            shape.project,
        ),
        "session_id": shape.uuid,
        "project": shape.project,
        "source_signal_ids": [signal_id],
        "recurrence": 1,
        "promoted": False,
        "state": "candidate",
        "checkable": True,
        "summary": candidate_summary,
        "evidence": {
            "score": round(shape.anomaly_score, 3),
            "threshold": threshold,
            "reasons": list(shape.anomaly_reasons),
            "first_message": shape.first_message,
            "duration_min": round(shape.duration_min, 2),
            "cost_usd": round(shape.cost_usd, 2),
        },
        "source": "scripts/session-shape.py",
    }


def main():
    parser = argparse.ArgumentParser(description="Session shape anomaly detector")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--project", "-p", help="Filter by project")
    parser.add_argument(
        "--threshold", "-t", type=float, default=2.0, help="Z-score threshold (default: 2.0)"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--all", action="store_true", help="Show all sessions, not just anomalies")
    parser.add_argument(
        "--signals-out",
        type=Path,
        help="Append deterministic signal records as JSONL",
    )
    parser.add_argument(
        "--candidates-out",
        type=Path,
        help="Append candidate backlog records as JSONL",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"agentlogs DB not found at {DB_PATH}. Run: uv run agentlogs index", file=sys.stderr)
        sys.exit(1)

    db = _open_db(DB_PATH)

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    # agentlogs schema: derive tools_used as a JSON array of distinct tool
    # names from tool_calls joined via runs. commits come from the git_commits
    # table on vendor_session_id.
    query = """
        SELECT
            s.session_uuid AS uuid,
            s.project_slug AS project,
            s.start_ts,
            s.first_message,
            s.duration_min,
            s.cost_usd,
            (SELECT json_group_array(tool_name) FROM (
                SELECT DISTINCT tc.tool_name
                FROM tool_calls tc JOIN runs r ON r.run_id = tc.run_id
                WHERE r.session_pk = s.session_pk
            )) AS tools_used,
            (SELECT json_group_array(gc.hash) FROM git_commits gc
             WHERE gc.session_id = s.vendor_session_id) AS commits,
            s.transcript_lines
        FROM sessions s
        WHERE s.session_uuid IS NOT NULL
          AND s.start_ts >= ?
          AND s.duration_min IS NOT NULL
          AND s.duration_min > 0.5
    """
    params = [since]
    if args.project:
        query += " AND s.project_slug = ?"
        params.append(args.project)
    query += " ORDER BY s.start_ts DESC"

    rows = db.execute(query, params).fetchall()
    if not rows:
        print("No sessions found in the given period.", file=sys.stderr)
        sys.exit(0)

    # Extract features
    shapes = []
    for row in rows:
        shape = SessionShape(
            uuid=row["uuid"],
            project=row["project"] or "unknown",
            start_ts=row["start_ts"] or "",
            first_message=(row["first_message"] or "")[:80],
            duration_min=row["duration_min"] or 0,
            cost_usd=row["cost_usd"] or 0,
            features=extract_features(row),
        )
        shapes.append(shape)

    # Compute anomalies
    shapes = compute_anomalies(shapes, threshold=args.threshold)
    signal_shapes = list(shapes)

    # Filter to anomalies unless --all
    anomalous = len([s for s in shapes if s.anomaly_score > 0])
    if not args.all:
        shapes = [s for s in shapes if s.anomaly_score > 0]

    # Sort by anomaly score descending
    shapes.sort(key=lambda s: s.anomaly_score, reverse=True)

    if args.json:
        output = []
        for s in shapes:
            output.append({
                "uuid": s.uuid[:8],
                "project": s.project,
                "date": s.start_ts[:10],
                "anomaly_score": round(s.anomaly_score, 2),
                "reasons": s.anomaly_reasons,
                "first_message": s.first_message,
                "features": {k: round(v, 3) for k, v in s.features.items()},
            })
        print(json.dumps(output, indent=2))
    else:
        total = len(rows)
        anomalous = len([s for s in shapes if s.anomaly_score > 0]) if args.all else len(shapes)
        print(f"Sessions: {total} total, {anomalous} anomalous (threshold z>{args.threshold})")
        print()

        if not shapes:
            print("No anomalous sessions found.")
            return

        for s in shapes[:20]:
            score_bar = "█" * min(int(s.anomaly_score), 20)
            print(f"{s.uuid[:8]}  {s.start_ts[:10]}  {s.project:<12}  "
                  f"${s.cost_usd:>5.2f}  {s.duration_min:>5.1f}m  "
                  f"score={s.anomaly_score:>5.1f}  {score_bar}")
            for reason in s.anomaly_reasons[:3]:
                print(f"  ↳ {reason}")
            print(f"  {s.first_message}")
            print()

    signals_out = args.signals_out or artifact_path("signals.jsonl")
    candidates_out = args.candidates_out or artifact_path("candidates.jsonl")
    for shape in signal_shapes:
        append_jsonl(signals_out, build_signal_record(shape, threshold=args.threshold))
        if shape.anomaly_score > 0:
            append_jsonl(candidates_out, build_candidate_record(shape, threshold=args.threshold))

    # Log metric
    log_metric("session_shape",
               sessions_scanned=len(rows),
               anomalies_found=anomalous if not args.all else len([s for s in shapes if s.anomaly_score > 0]),
               threshold=args.threshold,
               days=args.days)

    db.close()


if __name__ == "__main__":
    main()
