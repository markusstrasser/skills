#!/usr/bin/env python3
"""Deterministic review gate — triage, rank, inconclusive anchor check.

No LLM. Subcommands:
  triage      → dispatch.json (routing + blockers)
  rank        → orchestrator-top.json (top-N findings for Opus)
  inconclusive → inconclusive-verify.json (grep anchors for INCONCLUSIVE rows)
  contradictions → anchor-contradictions.json (cross-family contradictory anchors)

Usage:
  review_gate.py triage --repo . --packet .model-review/plan-close-context.md
  review_gate.py rank --review-dir .model-review/foo-abc123
  review_gate.py inconclusive --review-dir .model-review/foo --repo .
  review_gate.py contradictions --review-dir .model-review/foo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

from shared.context_packet import estimate_tokens  # noqa: E402

_ia_spec = importlib.util.spec_from_file_location(
    "integration_audit", Path(__file__).parent / "integration_audit.py"
)
assert _ia_spec and _ia_spec.loader
ia = importlib.util.module_from_spec(_ia_spec)
sys.modules["integration_audit"] = ia
_ia_spec.loader.exec_module(ia)

load_findings = ia.load_findings
merge_records = ia.merge_records

PACKET_WARN_TOKENS = 45_000
PACKET_FAIL_TOKENS = 90_000
DISPATCH_SCHEMA_VERSION = "dispatch.v1"
TOP_N = 8
# Escalate cross2 → cross4 when inconclusive-verify rows exceed this (per review run).
INCONCLUSIVE_ESCALATE_THRESHOLD = 3
# Escalate on contradictory cross-family anchor pairs (not mere non-overlap).
CONTRADICTORY_ESCALATE_THRESHOLD = 1
AXIS_FAMILY: dict[str, str] = {
    "arch": "gemini",
    "gaps": "gemini",
    "correctness": "gpt",
    "contracts": "gpt",
}
NEGATIVE_STANCE = re.compile(
    r"\b("
    r"bug|broken|missing|incorrect|wrong|fails?|invalid|unsafe|gap|risk|violation|"
    r"doesn'?t|does not|lack|absent|must not|should not|not implemented|"
    r"no caller|dead code|halluc|unverified|fail-open|bypass|orphan"
    r")\b",
    re.I,
)
POSITIVE_STANCE = re.compile(
    r"\b("
    r"correct|works|fine|valid|safe|acceptable|sufficient|unnecessary|not needed|"
    r"already exist|no issue|not a bug|appropriate|sound design|correctly enforced|"
    r"properly enforced|no problem"
    r")\b",
    re.I,
)
TOPIC_WORD = re.compile(r"[a-z0-9_]{4,}", re.I)
# Generic tokens that should not alone trigger contradiction overlap on a hot file.
ENTITY_STOPWORDS = frozenset(
    {
        "client",
        "config",
        "context",
        "data",
        "file",
        "code",
        "module",
        "service",
        "handler",
        "utils",
        "helper",
        "manager",
        "object",
        "value",
        "state",
        "error",
        "function",
        "class",
        "method",
        "string",
        "result",
        "return",
        "process",
        "system",
    }
)
TITLE_JACCARD_MIN = 0.20
GOVERNANCE_MARKERS = (
    "CLAUDE.md",
    "GOALS.md",
    "AGENTS.md",
    ".claude/settings.json",
    "decisions/",
    "hooks/",
    "constitution",
)
SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
PATH_LIKE = re.compile(
    r"(?:^|[\s`'\"(])([\w./-]+\.(?:py|md|sql|json|toml|sh|yaml|yml))(?=[\s:)'\"`,]|$)"
)
OPEN_FORK_RE = re.compile(
    r"\b(TBD|TODO|unclear|assume|might|either/or|open question|unsure|uncertain|fork)\b",
    re.I,
)
REPO_PREMISE_RE = re.compile(
    r"`[^`]*/[^`]+`|`\w+\.py`|(?:^|\s)(?:scripts|src|tests)/[\w./-]+",
    re.M,
)


@dataclass
class GateResult:
    ok: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)

    def exit_code(self, strict: bool) -> int:
        if self.blockers:
            return 1
        if strict and self.warnings:
            return 1
        return 0


def _format_blocker(check: str, message: str, fix: str) -> str:
    return f"[{check}] BLOCKED — {message}\nfix: {fix}"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _latest_review_dir(repo: Path) -> Path | None:
    root = repo / ".model-review"
    if not root.is_dir():
        return None
    candidates = [d for d in root.iterdir() if d.is_dir() and (d / "findings.json").exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _diff_files(repo: Path, base: str | None, head: str | None) -> set[str]:
    _, files = ia.collect_diff(repo, base, head)
    return files


def _scan_dead_refs(packet_text: str, repo: Path) -> list[str]:
    dead: list[str] = []
    seen: set[str] = set()
    for m in PATH_LIKE.finditer(packet_text):
        rel = m.group(1).lstrip("./")
        if rel in seen or rel.startswith("http"):
            continue
        seen.add(rel)
        if "/" not in rel and not rel.endswith((".py", ".md", ".json", ".sql", ".sh", ".toml", ".yaml", ".yml")):
            continue
        p = repo / rel
        if not p.is_file():
            dead.append(rel)
    return dead


def _touches_governance(paths: set[str], packet: str) -> bool:
    blob = " ".join(paths) + " " + packet
    return any(g in blob for g in GOVERNANCE_MARKERS)


def _multi_repo_projects(packet: str, paths: set[str]) -> set[str]:
    roots: set[str] = set()
    for blob in [packet, *paths]:
        for m in re.finditer(r"(?:~/Projects/|Projects/)([A-Za-z0-9_-]+)", blob):
            roots.add(m.group(1).lower())
    return roots


def _inconclusive_count(review_dir: Path | None) -> int:
    if not review_dir:
        return 0
    inv = review_dir / "inconclusive-verify.json"
    if not inv.is_file():
        return 0
    return int(_load_json(inv).get("inconclusive_count") or 0)


def _topic_words(text: str) -> set[str]:
    words = {w.lower() for w in TOPIC_WORD.findall(text)}
    stop = {
        "this",
        "that",
        "with",
        "from",
        "should",
        "could",
        "would",
        "does",
        "have",
        "will",
        "also",
        "been",
        "file",
        "code",
        "review",
        "finding",
    }
    return words - stop


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _norm_file(path: str) -> str:
    return path.strip().lstrip("./").replace("\\", "/")


def _finding_family(finding: dict) -> str:
    axis = str(finding.get("source_axis") or finding.get("axis") or "").strip()
    if axis in AXIS_FAMILY:
        return AXIS_FAMILY[axis]
    model = str(finding.get("source_model") or finding.get("model") or "").lower()
    if "gemini" in model:
        return "gemini"
    if "gpt" in model or "openai" in model:
        return "gpt"
    return ""


def _stance_scores(text: str) -> tuple[int, int]:
    return len(NEGATIVE_STANCE.findall(text)), len(POSITIVE_STANCE.findall(text))


def _meaningful_shared(words_a: set[str], words_b: set[str]) -> set[str]:
    return (words_a & words_b) - ENTITY_STOPWORDS


def _findings_overlap(f1: dict, f2: dict) -> bool:
    file_a = _norm_file(str(f1.get("file") or ""))
    file_b = _norm_file(str(f2.get("file") or ""))
    text_a = f"{f1.get('title', '')} {f1.get('description', '')}"
    text_b = f"{f2.get('title', '')} {f2.get('description', '')}"
    words_a = _topic_words(text_a)
    words_b = _topic_words(text_b)
    jacc = _jaccard(words_a, words_b)
    meaningful = _meaningful_shared(words_a, words_b)
    if file_a and file_b and file_a == file_b:
        return bool(meaningful) or jacc >= 0.10
    return jacc >= 0.28


def _is_contradictory_pair(f1: dict, f2: dict) -> bool:
    """Contradictory anchors: opposite stance on overlapping topic across families."""
    fam_a = _finding_family(f1)
    fam_b = _finding_family(f2)
    if not fam_a or not fam_b or fam_a == fam_b:
        return False
    text_a = f"{f1.get('title', '')} {f1.get('description', '')}"
    text_b = f"{f2.get('title', '')} {f2.get('description', '')}"
    words_a = _topic_words(text_a)
    words_b = _topic_words(text_b)
    title_a = _topic_words(str(f1.get("title") or ""))
    title_b = _topic_words(str(f2.get("title") or ""))
    meaningful_title_jacc = _jaccard(
        title_a - ENTITY_STOPWORDS,
        title_b - ENTITY_STOPWORDS,
    )
    if meaningful_title_jacc < TITLE_JACCARD_MIN and not _meaningful_shared(words_a, words_b):
        return False
    if not _findings_overlap(f1, f2):
        return False
    neg_a, pos_a = _stance_scores(text_a)
    neg_b, pos_b = _stance_scores(text_b)
    if neg_a > pos_a and pos_b > neg_b:
        return True
    if pos_a > neg_a and neg_b > pos_b:
        return True
    return False


def detect_contradictory_anchors(findings: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    for i, f1 in enumerate(findings):
        if not isinstance(f1, dict):
            continue
        for f2 in findings[i + 1 :]:
            if not isinstance(f2, dict):
                continue
            if _is_contradictory_pair(f1, f2):
                pairs.append(
                    {
                        "finding_a": {
                            "id": f1.get("id"),
                            "title": f1.get("title"),
                            "file": f1.get("file"),
                            "source_axis": f1.get("source_axis"),
                        },
                        "finding_b": {
                            "id": f2.get("id"),
                            "title": f2.get("title"),
                            "file": f2.get("file"),
                            "source_axis": f2.get("source_axis"),
                        },
                        "reason": "opposite_stance_same_topic",
                    }
                )
    return pairs


def _infer_preset_from_review_dir(review_dir: Path) -> str | None:
    cov = _load_json(review_dir / "coverage.json")
    axes = cov.get("dispatch", {}).get("requested_axes") or []
    if not isinstance(axes, list) or not axes:
        return None
    axis_set = set(axes)
    if axis_set == {"arch", "correctness"}:
        return "cross2"
    if axis_set == {"arch", "gaps", "correctness", "contracts"}:
        return "cross4"
    return ",".join(axes)


def _write_escalation_recommendation(
    review_dir: Path,
    *,
    contradictory_pairs: int,
    pairs: list[dict],
) -> Path | None:
    if contradictory_pairs < CONTRADICTORY_ESCALATE_THRESHOLD:
        return None
    current = _infer_preset_from_review_dir(review_dir)
    recommended = "cross4"
    reasons = ["contradictory_anchors"]
    executed = current in ("cross4", "lens4", "standard")
    payload = {
        "generated_at": _now(),
        "review_dir": str(review_dir),
        "contradictory_pairs": contradictory_pairs,
        "current_preset": current,
        "escalation_recommended": recommended,
        "escalation_reasons": reasons,
        "escalation_executed": executed,
        "action": (
            "none — already on cross4/standard"
            if executed
            else "re-run model-review --axes cross4 on same packet (post-rank auto-detected)"
        ),
        "pairs": pairs,
    }
    out_path = review_dir / "escalation-recommendation.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    return out_path


def _contradictory_count(review_dir: Path | None) -> int:
    if not review_dir:
        return 0
    path = review_dir / "anchor-contradictions.json"
    if path.is_file():
        return int(_load_json(path).get("contradictory_pairs") or 0)
    fj = review_dir / "findings.json"
    if not fj.is_file():
        return 0
    return len(detect_contradictory_anchors(load_findings(fj)))


def _recommend_preset(
    *,
    design_run: bool,
    diff_files: set[str],
    packet_text: str,
    inconclusive_count: int,
    contradictory_count: int,
    manifest_axes: str | None,
) -> tuple[str | None, list[str]]:
    if not design_run:
        return None, []
    if manifest_axes:
        return manifest_axes, ["manifest_override"]
    reasons: list[str] = []
    preset = "cross2"
    if _touches_governance(diff_files, packet_text):
        preset = "cross4"
        reasons.append("governance_paths")
    if len(_multi_repo_projects(packet_text, diff_files)) >= 2:
        preset = "cross4"
        reasons.append("multi_repo_packet")
    if inconclusive_count >= INCONCLUSIVE_ESCALATE_THRESHOLD:
        preset = "cross4"
        reasons.append(f"inconclusive>={INCONCLUSIVE_ESCALATE_THRESHOLD}")
    if contradictory_count >= CONTRADICTORY_ESCALATE_THRESHOLD:
        preset = "cross4"
        reasons.append("contradictory_anchors")
    return preset, reasons


def _packet_has_repo_premises(packet_text: str) -> bool:
    return bool(REPO_PREMISE_RE.search(packet_text))


def _packet_has_open_fork(packet_text: str) -> bool:
    return bool(OPEN_FORK_RE.search(packet_text))


def infer_dispatch_policy(
    packet_text: str,
    review_targets: dict,
    *,
    budget_seconds: int | None = None,
) -> dict:
    """Deterministic scout/scope/budget policy for model-review (no LLM)."""
    design = review_targets.get("design_target") or {}
    scope_token = design.get("context_scope")
    if scope_token in ("repo", "packet"):
        context_scope = scope_token
    elif not packet_text.strip() or not _packet_has_repo_premises(packet_text):
        context_scope = "packet"
    else:
        context_scope = "repo"

    if "premise_scout" in design:
        premise_scout = bool(design["premise_scout"])
    elif context_scope == "packet":
        premise_scout = False
    else:
        premise_scout = True

    budget = design.get("budget_seconds")
    if budget is None:
        budget = budget_seconds

    return {
        "premise_scout": premise_scout,
        "context_scope": context_scope,
        "budget_seconds": budget,
        "irreversible": bool(design.get("irreversible", False)),
        "cross_talk": bool(design.get("cross_talk", False)),
    }


def cmd_triage(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    packet = args.packet.resolve() if args.packet else None
    manifest = args.manifest.resolve() if args.manifest else None
    if packet and not manifest and packet.with_suffix(".manifest.json").is_file():
        manifest = packet.with_suffix(".manifest.json")

    blockers: list[str] = []
    warnings: list[str] = []
    contrad = 0
    layers: dict = {"diff": {"owner": "code-review", "run": False}, "design": {"owner": "critique", "run": False}}
    review_targets = {}
    if manifest and manifest.is_file():
        review_targets = _load_json(manifest).get("review_targets") or {}

    diff_files = _diff_files(repo, args.base, args.head)
    packet_text = packet.read_text() if packet and packet.is_file() else ""
    packet_tokens = estimate_tokens(packet_text) if packet_text else 0

    if review_targets.get("diff_target") or diff_files:
        layers["diff"]["run"] = True
        layers["diff"]["files"] = sorted(diff_files)[:50]
    design_run = bool(
        review_targets.get("design_target") or (packet and args.mode in ("close", "auto", "model"))
    )
    if design_run:
        layers["design"]["run"] = True
        manifest_axes = str(review_targets.get("design_target", {}).get("axes") or "").strip() or None
        review_dir_pre = args.review_dir.resolve() if args.review_dir else _latest_review_dir(repo)
        inconc = _inconclusive_count(review_dir_pre)
        contrad = _contradictory_count(review_dir_pre)
        preset, preset_reasons = _recommend_preset(
            design_run=True,
            diff_files=diff_files,
            packet_text=packet_text,
            inconclusive_count=inconc,
            contradictory_count=contrad,
            manifest_axes=manifest_axes,
        )
        axes = manifest_axes or preset or "standard"
        if args.mode == "close" and "composer" in {a.strip() for a in axes.split(",")}:
            blockers.append(
                _format_blocker(
                    "review-gate",
                    "closeout design must not use composer axis — diff layer owns Composer via /code-review",
                    "/critique model --axes standard --context .model-review/plan-close-context.md",
                )
            )
        layers["design"]["axes"] = axes
        layers["design"]["preset"] = preset if not manifest_axes else manifest_axes
        layers["design"]["preset_reasons"] = preset_reasons
        layers["design"]["extract"] = True
        layers["design"]["verify"] = True
        dispatch_policy = infer_dispatch_policy(
            packet_text,
            review_targets,
            budget_seconds=getattr(args, "budget_seconds", None),
        )
        layers["design"]["dispatch_policy"] = dispatch_policy
        if (
            dispatch_policy["context_scope"] == "repo"
            and not _packet_has_open_fork(packet_text)
            and dispatch_policy["premise_scout"]
        ):
            warnings.append(
                "no open-fork markers in packet — premise_scout still on (repo premises); "
                "set design_target.context_scope=packet or premise_scout=false to skip"
            )

    if packet_tokens > PACKET_FAIL_TOKENS:
        blockers.append(f"packet {packet_tokens} tokens > {PACKET_FAIL_TOKENS} — split subparts")
    elif packet_tokens > PACKET_WARN_TOKENS:
        warnings.append(f"packet {packet_tokens} tokens > {PACKET_WARN_TOKENS} — prefer subparts")

    dead = _scan_dead_refs(packet_text, repo) if packet_text else []
    if dead:
        blockers.append(f"dead refs in packet: {', '.join(dead[:8])}")

    review_dir = args.review_dir.resolve() if args.review_dir else _latest_review_dir(repo)
    review_hash = None
    if manifest and manifest.is_file():
        review_hash = _load_json(manifest).get("payload_hash") or _load_json(manifest).get("rendered_content_hash")

    skip_review = False
    if args.dispatch_out.is_file() and review_hash:
        prev = _load_json(args.dispatch_out)
        if prev.get("review_hash") == review_hash and prev.get("skip_review"):
            skip_review = True
            warnings.append("packet hash unchanged — prior review may still apply (re-run if commits changed)")

    escalate = layers["design"].get("preset") in ("cross4", "lens4", "standard") or layers[
        "design"
    ].get("axes") in ("cross4", "lens4", "standard")

    if args.mode == "close" and layers["design"]["run"]:
        if not review_dir or not (review_dir / "verified-disposition.md").is_file():
            blockers.append(
                _format_blocker(
                    "review-gate",
                    "missing verified-disposition.md — run model-review --extract --verify before closeout",
                    "uv run python3 ${CLAUDE_SKILL_DIR}/scripts/model-review.py --extract --verify --context .model-review/plan-close-context.md",
                )
            )

    artifact = "plan"
    if layers["diff"]["run"] and layers["design"]["run"]:
        artifact = "closeout"
    elif layers["diff"]["run"]:
        artifact = "diff"

    dispatch_policy = layers["design"].get("dispatch_policy") if design_run else {
        "premise_scout": False,
        "context_scope": "packet",
        "budget_seconds": getattr(args, "budget_seconds", None),
        "irreversible": False,
        "cross_talk": False,
    }

    dispatch = {
        "schema_version": DISPATCH_SCHEMA_VERSION,
        "generated_at": _now(),
        "artifact": artifact,
        "layers": layers,
        "dispatch_policy": dispatch_policy,
        "preset": layers["design"].get("preset"),
        "preset_reasons": layers["design"].get("preset_reasons") or [],
        "inconclusive_escalate_threshold": INCONCLUSIVE_ESCALATE_THRESHOLD,
        "contradictory_escalate_threshold": CONTRADICTORY_ESCALATE_THRESHOLD,
        "contradictory_pairs": contrad if design_run else 0,
        "escalate_4axis": escalate,
        "packet_path": str(packet) if packet else None,
        "packet_tokens": packet_tokens,
        "review_dir": str(review_dir) if review_dir else None,
        "review_hash": review_hash,
        "skip_review": skip_review,
        "blockers": blockers,
        "warnings": warnings,
    }

    args.dispatch_out.parent.mkdir(parents=True, exist_ok=True)
    args.dispatch_out.write_text(json.dumps(dispatch, indent=2) + "\n")

    if args.json:
        print(json.dumps(dispatch, indent=2))
    else:
        print(f"Review triage — {artifact}")
        print(f"  diff:   {'yes' if layers['diff']['run'] else 'no'} → code-review")
        print(f"  design: {'yes' if layers['design']['run'] else 'no'} → critique {layers['design'].get('axes', '')}")
        if layers["design"].get("preset"):
            print(f"  preset: {layers['design']['preset']} ({', '.join(layers['design'].get('preset_reasons') or [])})")
        policy = dispatch.get("dispatch_policy") or {}
        if policy:
            print(
                f"  policy: scout={policy.get('premise_scout')} "
                f"scope={policy.get('context_scope')} "
                f"budget={policy.get('budget_seconds')}"
            )
        print(f"  tokens: {packet_tokens}")
        if blockers:
            print(f"  BLOCK ({len(blockers)})")
            for b in blockers:
                print(f"    {b}")
        if warnings:
            print(f"  WARN ({len(warnings)})")
            for w in warnings:
                print(f"    - {w}")
        if not blockers:
            print("  PASS")
        print(f"  → {args.dispatch_out}")

    return 1 if blockers else 0


def cmd_rank(args: argparse.Namespace) -> int:
    review_dir = args.review_dir.resolve()
    fj = review_dir / "findings.json"
    if not fj.is_file():
        print(f"no findings.json in {review_dir}", file=sys.stderr)
        return 2
    findings = load_findings(fj)
    scored: list[tuple[float, dict]] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = SEV_RANK.get(str(f.get("severity", "")).lower(), 1)
        conf = float(f.get("confidence") or 0.5)
        cross = 1.0 if f.get("cross_model") else 0.0
        has_file = 1.0 if f.get("file") else 0.0
        # drop noise: singleton low, no file, no cross-model
        if sev <= 1 and not cross and not has_file:
            continue
        score = cross * 10 + sev * 3 + conf + has_file * 0.5
        scored.append((score, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [f for _, f in scored[: args.top]]
    out = {
        "generated_at": _now(),
        "review_dir": str(review_dir),
        "total_findings": len(findings),
        "ranked_count": len(scored),
        "top_n": args.top,
        "findings": top,
    }
    out_path = review_dir / "orchestrator-top.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")

    pairs = detect_contradictory_anchors(findings)
    contrad_path = review_dir / "anchor-contradictions.json"
    contrad_path.write_text(
        json.dumps(
            {
                "generated_at": _now(),
                "review_dir": str(review_dir),
                "contradictory_pairs": len(pairs),
                "pairs": pairs,
            },
            indent=2,
        )
        + "\n"
    )
    esc_path = _write_escalation_recommendation(
        review_dir,
        contradictory_pairs=len(pairs),
        pairs=pairs,
    )

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Ranked {len(top)}/{len(findings)} findings → {out_path}")
        if pairs:
            print(f"  contradictory anchor pairs: {len(pairs)} → {contrad_path}")
        if esc_path:
            print(f"  escalation recommended: cross4 → {esc_path}")
        for i, f in enumerate(top, 1):
            tag = "×2" if f.get("cross_model") else "  "
            print(f"  {i}. [{tag}] [{f.get('severity','?')}] {str(f.get('title',''))[:70]}")
    return 0


def _grep_file(repo: Path, rel: str, needles: list[str]) -> bool:
    p = repo / rel
    if not p.is_file():
        return False
    try:
        text = p.read_text(errors="replace").lower()
    except OSError:
        return False
    hits = sum(1 for n in needles if n and n in text)
    return hits >= min(2, len([n for n in needles if n]))


def cmd_inconclusive(args: argparse.Namespace) -> int:
    review_dir = args.review_dir.resolve()
    repo = args.repo.resolve()
    records = merge_records(review_dir)
    inconc = [r for r in records if r.verdict == "INCONCLUSIVE"]
    rows: list[dict] = []
    for r in inconc:
        rel = r.file.lstrip("/")
        if rel.startswith(str(repo)):
            rel = Path(rel).relative_to(repo).as_posix()
        needles = [w.lower() for w in ia.SIG_WORD.findall(r.title + " " + r.fix) if w.lower() not in ia.STOP][:12]
        resolved = False
        note = "no file"
        if rel:
            p = repo / rel
            if p.is_file():
                resolved = _grep_file(repo, rel, needles)
                note = "anchor_hit" if resolved else "file_ok_no_anchor"
            else:
                note = "file_missing"
        rows.append(
            {
                "num": r.num,
                "title": r.title,
                "file": rel,
                "resolved_deterministic": resolved,
                "note": note,
            }
        )
    out = {
        "generated_at": _now(),
        "review_dir": str(review_dir),
        "inconclusive_count": len(rows),
        "resolved_count": sum(1 for x in rows if x["resolved_deterministic"]),
        "rows": rows,
    }
    out_path = review_dir / "inconclusive-verify.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Inconclusive verify-lite: {out['resolved_count']}/{len(rows)} anchor hits → {out_path}")
        for row in rows:
            mark = "✓" if row["resolved_deterministic"] else "?"
            print(f"  {mark} #{row['num']} [{row['note']}] {row['title'][:60]}")
    return 0


def cmd_contradictions(args: argparse.Namespace) -> int:
    review_dir = args.review_dir.resolve()
    findings = load_findings(review_dir / "findings.json")
    if not findings:
        print(f"no findings.json in {review_dir}", file=sys.stderr)
        return 2
    pairs = detect_contradictory_anchors(findings)
    out = {
        "generated_at": _now(),
        "review_dir": str(review_dir),
        "contradictory_pairs": len(pairs),
        "pairs": pairs,
    }
    out_path = review_dir / "anchor-contradictions.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Contradictory anchors: {len(pairs)} pair(s) → {out_path}")
        for p in pairs:
            a = p["finding_a"]
            b = p["finding_b"]
            print(f"  #{a.get('id')} ({a.get('source_axis')}) vs #{b.get('id')} ({b.get('source_axis')})")
            print(f"    A: {str(a.get('title', ''))[:65]}")
            print(f"    B: {str(b.get('title', ''))[:65]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic review gate (no LLM).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("triage", help="Emit dispatch.json routing + blockers")
    t.add_argument("--repo", type=Path, default=Path.cwd())
    t.add_argument("--packet", type=Path, default=None)
    t.add_argument("--manifest", type=Path, default=None)
    t.add_argument("--review-dir", type=Path, default=None)
    t.add_argument("--base", default=None)
    t.add_argument("--head", default=None)
    t.add_argument("--mode", choices=("close", "model", "auto"), default="auto")
    t.add_argument(
        "--budget-seconds",
        type=int,
        default=None,
        help="Optional session time-box passed into dispatch_policy.budget_seconds",
    )
    t.add_argument("--dispatch-out", type=Path, default=Path(".model-review/dispatch.json"))
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=cmd_triage)

    r = sub.add_parser("rank", help="Top-N findings for orchestrator")
    r.add_argument("--review-dir", type=Path, required=True)
    r.add_argument("--top", type=int, default=TOP_N)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_rank)

    i = sub.add_parser("inconclusive", help="Deterministic anchor check on INCONCLUSIVE rows")
    i.add_argument("--review-dir", type=Path, required=True)
    i.add_argument("--repo", type=Path, default=Path.cwd())
    i.add_argument("--json", action="store_true")
    i.set_defaults(func=cmd_inconclusive)

    c = sub.add_parser("contradictions", help="Detect cross-family contradictory anchors")
    c.add_argument("--review-dir", type=Path, required=True)
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_contradictions)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
