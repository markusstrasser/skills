from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.llm_dispatch import PROFILES

KNOWN_KINDS = {"worker", "orchestrator", "operator", "reference"}
KNOWN_INTENT_CLASSES = {
    "divergent",
    "convergent",
    "observational",
    "operator",
    "reference",
    "verification",
}
KNOWN_ENTRYPOINT_TYPES = {"script", "skill_doc", "manual"}
KNOWN_PACKET_BUILDERS = {
    "shared_context_packet",
    "plan_close_packet",
    "observe_transcript_packet",
    "brainstorm_context_packet",
    "overview_packet",
    "status_reconciliation_packet",
}
ARTIFACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "review-coverage.v1": {
        "required_fields": [
            "schema",
            "topic",
            "mode",
            "axes",
            "claims",
            "verification",
            "packet",
        ]
    },
    "observe.signal.v1": {
        "required_fields": ["schema", "kind", "signal_id", "project", "source", "status"]
    },
    "observe.candidate.v1": {
        "required_fields": [
            "schema",
            "kind",
            "candidate_id",
            "project",
            "source_signal_ids",
            "state",
            "promoted",
            "checkable",
            "summary",
        ]
    },
    "brainstorm.matrix.v1": {
        "required_fields": [
            "idea_id",
            "source_artifact",
            "axis",
            "dominant_paradigm_escaped",
            "disposition",
        ]
    },
    "brainstorm.coverage.v1": {
        "required_fields": [
            "requested_axes",
            "executed_axes",
            "idea_count_by_axis",
            "uncovered_cells",
        ]
    },
    "status-reconciliation.v1": {
        "required_fields": [
            "stage",
            "mismatch_class",
            "live_state",
            "control_plane_state",
            "local_state",
        ]
    },
}


@dataclass(frozen=True)
class ManifestIssue:
    manifest_path: Path
    message: str


def iter_manifest_paths(root: Path) -> list[Path]:
    return sorted(root.glob("*/skill.json"))


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text())


def _expect_dict(value: Any, label: str, issues: list[ManifestIssue], manifest_path: Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    issues.append(ManifestIssue(manifest_path, f"{label} must be an object"))
    return {}


def _expect_list(value: Any, label: str, issues: list[ManifestIssue], manifest_path: Path) -> list[Any]:
    if isinstance(value, list):
        return value
    issues.append(ManifestIssue(manifest_path, f"{label} must be an array"))
    return []


def validate_manifest(manifest_path: Path, repo_root: Path) -> list[ManifestIssue]:
    issues: list[ManifestIssue] = []
    try:
        manifest = load_manifest(manifest_path)
    except json.JSONDecodeError as exc:
        return [ManifestIssue(manifest_path, f"invalid JSON: {exc}")]

    if not isinstance(manifest, dict):
        return [ManifestIssue(manifest_path, "manifest root must be an object")]

    skill_dir = manifest_path.parent.name
    name = manifest.get("name")
    if not isinstance(name, str) or not name:
        issues.append(ManifestIssue(manifest_path, "name must be a non-empty string"))
    elif name != skill_dir:
        issues.append(ManifestIssue(manifest_path, f"name must match skill dir '{skill_dir}'"))

    kind = manifest.get("kind")
    if kind not in KNOWN_KINDS:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"kind must be one of {sorted(KNOWN_KINDS)}",
            )
        )

    intent_class = manifest.get("intent_class")
    if intent_class not in KNOWN_INTENT_CLASSES:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"intent_class must be one of {sorted(KNOWN_INTENT_CLASSES)}",
            )
        )

    entrypoint = _expect_dict(manifest.get("entrypoint"), "entrypoint", issues, manifest_path)
    entrypoint_type = entrypoint.get("type")
    entrypoint_path = entrypoint.get("path")
    if entrypoint_type not in KNOWN_ENTRYPOINT_TYPES:
        issues.append(
            ManifestIssue(
                manifest_path,
                f"entrypoint.type must be one of {sorted(KNOWN_ENTRYPOINT_TYPES)}",
            )
        )
    if not isinstance(entrypoint_path, str) or not entrypoint_path:
        issues.append(ManifestIssue(manifest_path, "entrypoint.path must be a non-empty string"))
    else:
        resolved = repo_root / entrypoint_path
        if not resolved.exists():
            issues.append(
                ManifestIssue(manifest_path, f"entrypoint.path does not exist: {entrypoint_path}")
            )

    modes = _expect_dict(manifest.get("modes"), "modes", issues, manifest_path)
    if not modes:
        issues.append(ManifestIssue(manifest_path, "modes must declare at least one mode"))
    for mode_name, raw_mode in sorted(modes.items()):
        mode = _expect_dict(raw_mode, f"modes.{mode_name}", issues, manifest_path)
        mode_intent = mode.get("intent_class")
        if mode_intent not in KNOWN_INTENT_CLASSES:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"modes.{mode_name}.intent_class must be one of {sorted(KNOWN_INTENT_CLASSES)}",
                )
            )
        artifacts = _expect_list(mode.get("artifacts"), f"modes.{mode_name}.artifacts", issues, manifest_path)
        if not artifacts:
            issues.append(ManifestIssue(manifest_path, f"modes.{mode_name} must declare artifacts"))
        elif not all(isinstance(item, str) and item for item in artifacts):
            issues.append(
                ManifestIssue(manifest_path, f"modes.{mode_name}.artifacts must contain strings")
            )

    uses = _expect_dict(manifest.get("uses"), "uses", issues, manifest_path)
    dispatch_profiles = _expect_list(uses.get("dispatch_profiles", []), "uses.dispatch_profiles", issues, manifest_path)
    for profile_name in dispatch_profiles:
        if profile_name not in PROFILES:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown dispatch profile '{profile_name}'",
                )
            )

    packet_builders = _expect_list(uses.get("packet_builders", []), "uses.packet_builders", issues, manifest_path)
    for builder_name in packet_builders:
        if builder_name not in KNOWN_PACKET_BUILDERS:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown packet builder '{builder_name}'",
                )
            )

    artifact_schemas = _expect_list(uses.get("artifact_schemas", []), "uses.artifact_schemas", issues, manifest_path)
    for schema_name in artifact_schemas:
        if schema_name not in ARTIFACT_SCHEMAS:
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"unknown artifact schema '{schema_name}'",
                )
            )

    follow_on = _expect_list(manifest.get("follow_on", []), "follow_on", issues, manifest_path)
    if follow_on and not all(isinstance(item, str) and item for item in follow_on):
        issues.append(ManifestIssue(manifest_path, "follow_on must contain non-empty strings"))

    references = _expect_list(manifest.get("references", []), "references", issues, manifest_path)
    for reference_path in references:
        if not isinstance(reference_path, str) or not reference_path:
            issues.append(ManifestIssue(manifest_path, "references must contain non-empty strings"))
            continue
        resolved = repo_root / reference_path
        if not resolved.exists():
            issues.append(
                ManifestIssue(
                    manifest_path,
                    f"reference does not exist: {reference_path}",
                )
            )

    return issues


def validate_repo_manifests(repo_root: Path, manifest_paths: list[Path] | None = None) -> list[ManifestIssue]:
    paths = manifest_paths or iter_manifest_paths(repo_root)
    issues: list[ManifestIssue] = []
    for manifest_path in paths:
        issues.extend(validate_manifest(manifest_path, repo_root))
    return issues
