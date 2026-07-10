#!/usr/bin/env python3
"""Refuse broad genomics volume crawls while a stage writer is active.

The Modal list quota is workspace-wide, but only a task-bearing genomics stage
app is evidence of a concurrent writer. Canonical stage apps carry a ``gcpid``
launch identity in their description. Unrelated ephemeral jobs and zero-task
detached apps must not block post-drain diagnostics.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


_CRAWL_COMMANDS = re.compile(
    r"\bjust\s+(?:sample-remediation|sample-state|sample-readiness)\b"
)
_TARGET_SCOPE = re.compile(r"--target\b|--stage\b")
_PULL_COMMAND = re.compile(r"modal_sync_results\.py\s+pull\b")
_ALL_SCOPE = re.compile(r"--all\b")
_SUMMARY_ONLY = re.compile(r"--summaries-only\b")
_RECURSIVE_VOLUME_LIST = re.compile(
    r"\bmodal\s+volume\s+ls\b.*(?:\s-R\b|--recursive\b)"
)
_RESULTS_ROOT_LIST = re.compile(
    r"\bmodal\s+volume\s+ls\b[^|;&]*samples/\S+/results/?\s*$"
)
_CANONICAL_STAGE_IDENTITY = "--gcpid-"


@dataclass(frozen=True)
class GuardDecision:
    blocked: bool
    writers: tuple[Mapping[str, Any], ...] = ()


def is_full_dag_crawl(command: str) -> bool:
    """Return whether *command* performs a broad VolumeListFiles crawl."""
    broad_pull = bool(
        _PULL_COMMAND.search(command)
        and _ALL_SCOPE.search(command)
        and not _TARGET_SCOPE.search(command)
        and not _SUMMARY_ONLY.search(command)
    )
    broad_status = bool(
        _CRAWL_COMMANDS.search(command) and not _TARGET_SCOPE.search(command)
    )
    recursive_list = bool(
        _RECURSIVE_VOLUME_LIST.search(command)
        or _RESULTS_ROOT_LIST.search(command)
    )
    return broad_pull or broad_status or recursive_list


def _task_count(row: Mapping[str, Any]) -> int | None:
    raw_count = row.get("tasks", row.get("task_count"))
    try:
        return int(raw_count)
    except (TypeError, ValueError):
        return None


def is_genomics_stage_writer(row: Mapping[str, Any]) -> bool:
    """Identify a canonical stage app that currently owns worker tasks."""
    state = str(row.get("state") or "").strip().lower()
    description = str(row.get("description") or "")
    return (
        state.startswith("ephemeral")
        and _task_count(row) is not None
        and _task_count(row) > 0
        and _CANONICAL_STAGE_IDENTITY in description
    )


def load_modal_apps() -> Sequence[Mapping[str, Any]] | None:
    """Read the structured Modal app inventory, failing open on transport errors."""
    try:
        result = subprocess.run(
            ["modal", "app", "list", "--json"],
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return None
    return rows


def evaluate(
    payload: Mapping[str, Any],
    *,
    app_loader: Callable[[], Sequence[Mapping[str, Any]] | None] = load_modal_apps,
) -> GuardDecision:
    """Evaluate one PreToolUse payload without mutating external state."""
    if payload.get("tool_name") != "Bash":
        return GuardDecision(blocked=False)
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, Mapping):
        return GuardDecision(blocked=False)
    command = str(tool_input.get("command") or "")
    if not command or not is_full_dag_crawl(command):
        return GuardDecision(blocked=False)
    if os.environ.get("GENOMICS_F16_ACK") or re.search(
        r"\bGENOMICS_F16_ACK=1\b", command
    ):
        return GuardDecision(blocked=False)
    rows = app_loader()
    if rows is None:
        return GuardDecision(blocked=False)
    writers = tuple(row for row in rows if is_genomics_stage_writer(row))
    return GuardDecision(blocked=bool(writers), writers=writers)


def _writer_label(row: Mapping[str, Any]) -> str:
    app_id = str(row.get("app_id") or "unknown-app")
    description = str(row.get("description") or "unknown-stage")
    return f"{app_id}:{description.split('--gcpid-', maxsplit=1)[0]}"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    decision = evaluate(payload)
    if not decision.blocked:
        return 0
    labels = ", ".join(_writer_label(row) for row in decision.writers)
    sys.stderr.write(
        "BLOCKED (F16): a full-DAG Modal/volume crawl while "
        f"{len(decision.writers)} task-bearing genomics stage app(s) are LIVE.\n"
        "Per-stage VolumeListFiles bursts compete with stage writers for the workspace "
        "list quota and can silently throttle-hang.\n"
        f"Writers: {labels}\n"
        "Wait for zero stage writers, scope the diagnostic with --target/--stage, or "
        "use GENOMICS_F16_ACK=1 only after independently proving no genomics writer "
        "touches the volume.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
