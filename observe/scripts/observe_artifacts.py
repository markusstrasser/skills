#!/usr/bin/env python3
"""Shared paths and JSONL helpers for observe artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = Path.home() / "Projects" / "agent-infra"
ARTIFACT_SUBDIR = Path("artifacts") / "observe"

MANIFEST_JSON = "manifest.json"
INPUT_MD = "input.md"
CODEX_MD = "codex.md"
COVERAGE_DIGEST_TXT = "coverage-digest.txt"
OPERATIONAL_CONTEXT_TXT = "operational-context.txt"
GEMINI_OUTPUT_MD = "gemini-output.md"
GEMINI_OUTPUT_META_JSON = "gemini-output.meta.json"
GEMINI_OUTPUT_ERROR_JSON = "gemini-output.error.json"
DISPATCH_META_JSON = "dispatch.meta.json"
SIGNALS_JSONL = "signals.jsonl"
CANDIDATES_JSONL = "candidates.jsonl"
PATTERNS_JSONL = "patterns.jsonl"
LAST_SYNTHESIS_MD = "last-synthesis.md"
DIGEST_MD = "digest.md"

OBSERVE_ARTIFACT_ROOT_ENV = "OBSERVE_ARTIFACT_ROOT"
OBSERVE_PROJECT_ROOT_ENV = "OBSERVE_PROJECT_ROOT"


def project_root() -> Path:
    """Resolve the canonical workspace root for observe outputs."""
    env_root = os.environ.get(OBSERVE_PROJECT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()

    env_artifact_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_artifact_root:
        artifact_dir = Path(env_artifact_root).expanduser()
        if len(artifact_dir.parents) >= 2:
            return artifact_dir.parents[1]
        return artifact_dir.parent

    return DEFAULT_PROJECT_ROOT


def artifact_root() -> Path:
    """Resolve the canonical observe artifact directory."""
    env_root = os.environ.get(OBSERVE_ARTIFACT_ROOT_ENV)
    if env_root:
        return Path(env_root).expanduser()
    return project_root() / ARTIFACT_SUBDIR


def artifact_path(*parts: str) -> Path:
    """Join a path under the canonical artifact root."""
    return artifact_root().joinpath(*parts)


def improvement_log_path() -> Path:
    """Canonical improvement log used by sessions and supervision modes."""
    return project_root() / "improvement-log.md"


def stable_id(prefix: str, *parts: str, length: int = 12) -> str:
    """Create a stable short identifier from a sequence of string parts."""
    digest_input = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha1(digest_input).hexdigest()[:length]
    return f"{prefix}_{digest}"


def jsonl_line(record: dict[str, Any]) -> str:
    """Serialize one JSONL record with stable key ordering."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSONL record, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(jsonl_line(record))
        handle.write("\n")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write a full JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(jsonl_line(record))
            handle.write("\n")
