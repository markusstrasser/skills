from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal


NORMALIZATION_VERSION = "v1"
DEFAULT_TOKEN_ESTIMATOR = "heuristic:chars_div_4"


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_text(text: str) -> str:
    normalized = normalize_newlines(text)
    return normalized if normalized.endswith("\n") else normalized + "\n"


def normalize_path(value: str | Path) -> str:
    return Path(value).as_posix()


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def estimate_tokens(text: str, method: str = DEFAULT_TOKEN_ESTIMATOR) -> int:
    normalized = normalize_text(text)
    if method == "heuristic:chars_div_4":
        return max(1, len(normalized) // 4)
    raise ValueError(f"unsupported token estimate method '{method}'")


@dataclass(frozen=True)
class TruncationEvent:
    block_label: str
    reason: str
    original_chars: int
    rendered_chars: int


@dataclass(frozen=True)
class BudgetPolicy:
    metric: Literal["chars", "tokens"]
    limit: int
    estimate_method: str = DEFAULT_TOKEN_ESTIMATOR


@dataclass(frozen=True)
class PacketBlock:
    title: str
    text: str
    block_type: str
    truncatable: bool = True
    priority: int = 100
    drop_if_needed: bool = False
    min_chars: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    truncated: bool = False
    truncation_reason: str | None = None
    original_chars: int | None = None
    content_hash: str | None = None

    def rendered_chars(self) -> int:
        return len(normalize_text(self.text))

    def block_hash(self) -> str:
        return self.content_hash or sha256_text(self.text)

    def source_path(self) -> str | None:
        path_value = self.metadata.get("path")
        if path_value is None:
            return None
        return normalize_path(path_value)

    def truncation_event(self) -> TruncationEvent | None:
        if not self.truncated:
            return None
        return TruncationEvent(
            block_label=self.title,
            reason=self.truncation_reason or "truncated",
            original_chars=self.original_chars or self.rendered_chars(),
            rendered_chars=self.rendered_chars(),
        )


def TextBlock(title: str, text: str, **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=title, text=text, block_type="text", **kwargs)


def PreambleBlock(title: str, text: str, **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=title, text=text, block_type="preamble", truncatable=False, priority=1_000, **kwargs)


def FileBlock(path: str | Path, text: str, *, range_spec: str | None = None, **kwargs: Any) -> PacketBlock:
    metadata = dict(kwargs.pop("metadata", {}))
    metadata["path"] = normalize_path(path)
    if range_spec:
        metadata["range_spec"] = range_spec
    return PacketBlock(title=metadata["path"], text=text, block_type="file", metadata=metadata, **kwargs)


def SourceFileBlock(path: str | Path, *, title: str | None = None, **kwargs: Any) -> PacketBlock:
    normalized_path = normalize_path(path)
    source_path = Path(path)
    content_hash = sha256_text(source_path.read_text())
    metadata = dict(kwargs.pop("metadata", {}))
    metadata["path"] = normalized_path
    return PacketBlock(
        title=title or normalized_path,
        text="",
        block_type="source_file",
        metadata=metadata,
        truncatable=False,
        content_hash=content_hash,
        **kwargs,
    )


def DiffBlock(label: str, diff_text: str, **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=label, text=diff_text, block_type="diff", **kwargs)


def CommandBlock(command: str, output_text: str, **kwargs: Any) -> PacketBlock:
    metadata = dict(kwargs.pop("metadata", {}))
    metadata["command"] = command
    return PacketBlock(title=command, text=output_text, block_type="command", metadata=metadata, **kwargs)


def ListBlock(title: str, items: list[str], **kwargs: Any) -> PacketBlock:
    return PacketBlock(title=title, text="\n".join(items), block_type="list", **kwargs)


@dataclass(frozen=True)
class PacketSection:
    title: str
    blocks: list[PacketBlock]
    tag: str | None = None


@dataclass(frozen=True)
class ContextPacket:
    title: str
    sections: list[PacketSection]
    scope: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    budget_policy: BudgetPolicy | None = None


@dataclass(frozen=True)
class BuildArtifact:
    content_path: Path
    manifest_path: Path
    content_hash: str
    payload_hash: str
    rendered_bytes: int
    token_estimate: int | None
    estimate_method: str
    budget_metric: str
    truncated: bool


def build_manifest(
    packet: ContextPacket,
    *,
    rendered_content: str,
    builder_name: str,
    builder_version: str,
    created_at: str,
    estimate_method: str,
    budget_metric: str,
) -> dict[str, Any]:
    truncation_events = [
        asdict(event)
        for section in packet.sections
        for block in section.blocks
        for event in [block.truncation_event()]
        if event is not None
    ]
    source_blocks: list[dict[str, Any]] = []
    source_paths: list[str] = []
    for section_index, section in enumerate(packet.sections):
        for block_index, block in enumerate(section.blocks):
            source_path = block.source_path()
            if source_path and source_path not in source_paths:
                source_paths.append(source_path)
            source_blocks.append(
                {
                    "section_index": section_index,
                    "section_title": section.title,
                    "block_index": block_index,
                    "block_title": block.title,
                    "block_type": block.block_type,
                    "priority": block.priority,
                    "drop_if_needed": block.drop_if_needed,
                    "block_hash": block.block_hash(),
                    "source_path": source_path,
                    "metadata": block.metadata,
                    "truncated": block.truncated,
                }
            )

    normalized_content = normalize_text(rendered_content)
    token_estimate = estimate_tokens(normalized_content, estimate_method)
    budget_limit = packet.budget_policy.limit if packet.budget_policy else None

    return {
        "packet_title": packet.title,
        "builder_name": builder_name,
        "builder_version": builder_version,
        "created_at": created_at,
        "normalization_version": NORMALIZATION_VERSION,
        "source_blocks": source_blocks,
        "source_paths": source_paths,
        "rendered_content_hash": sha256_text(normalized_content),
        "payload_hash": sha256_text(normalized_content),
        "rendered_bytes": len(normalized_content.encode("utf-8")),
        "token_estimate": token_estimate,
        "estimate_method": estimate_method,
        "budget_metric": budget_metric,
        "budget_limit": budget_limit,
        "truncation_events": truncation_events,
        "packet_metadata": packet.metadata,
    }
