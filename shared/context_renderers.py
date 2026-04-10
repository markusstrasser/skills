from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from shared.context_packet import (
    BuildArtifact,
    ContextPacket,
    PacketBlock,
    PacketSection,
    atomic_write_json,
    atomic_write_text,
    build_manifest,
    estimate_tokens,
    normalize_text,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _block_text(block: PacketBlock) -> str:
    if block.block_type == "source_file":
        source_path = block.source_path()
        if source_path is None:
            return ""
        return Path(source_path).read_text()
    return block.text


def _render_block_markdown(block: PacketBlock) -> list[str]:
    lines: list[str] = []
    if block.block_type == "preamble":
        lines.extend([f"## {block.title}", "", _block_text(block).strip(), ""])
        return lines
    if block.block_type == "list":
        lines.extend([f"### {block.title}", ""])
        lines.extend(_block_text(block).splitlines() or [""])
        lines.append("")
        return lines

    fence = "text"
    if block.block_type == "diff":
        fence = "diff"
    lines.extend([f"### {block.title}", "", f"```{fence}", _block_text(block).rstrip(), "```", ""])
    return lines


def render_markdown(packet: ContextPacket) -> str:
    lines = [f"# {packet.title}", ""]
    if packet.metadata:
        for key, value in packet.metadata.items():
            if isinstance(value, (dict, list)):
                continue
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    if packet.scope:
        lines.extend(["## Scope", "", packet.scope.strip(), ""])
    for section in packet.sections:
        lines.extend([f"## {section.title}", ""])
        for block in section.blocks:
            lines.extend(_render_block_markdown(block))
    return normalize_text("\n".join(lines).rstrip("\n"))


def render_tagged_prompt(packet: ContextPacket) -> str:
    rendered_sections: list[str] = []
    for section in packet.sections:
        tag = section.tag or section.title.lower().replace(" ", "_")
        body_parts = []
        for block in section.blocks:
            body_parts.append(_block_text(block).rstrip())
        body_text = "\n\n".join(part for part in body_parts if part)
        rendered_sections.append(f"<{tag}>\n{body_text}\n</{tag}>")
    trailer = str(packet.metadata.get("trailing_text", "")).strip()
    body = "\n\n".join(rendered_sections)
    if trailer:
        body = f"{body}\n\n{trailer}"
    return normalize_text(body)


def write_tagged_prompt_streaming(packet: ContextPacket, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=output_path.parent, prefix=f".{output_path.name}.", suffix=".tmp", delete=False) as handle:
        first_section = True
        for section in packet.sections:
            if not first_section:
                handle.write("\n\n")
            first_section = False
            tag = section.tag or section.title.lower().replace(" ", "_")
            handle.write(f"<{tag}>\n")
            first_block = True
            for block in section.blocks:
                if not first_block:
                    handle.write("\n\n")
                first_block = False
                if block.block_type == "source_file":
                    source_path = block.source_path()
                    if source_path:
                        with Path(source_path).open("r") as source_handle:
                            for chunk in iter(lambda: source_handle.read(65_536), ""):
                                if not chunk:
                                    break
                                handle.write(chunk)
                    continue
                handle.write(block.text.rstrip())
            handle.write(f"\n</{tag}>")
        trailer = str(packet.metadata.get("trailing_text", "")).strip()
        if trailer:
            handle.write(f"\n\n{trailer}")
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, output_path)


def write_packet_artifact(
    packet: ContextPacket,
    *,
    renderer: str,
    output_path: Path,
    manifest_path: Path,
    builder_name: str,
    builder_version: str,
) -> BuildArtifact:
    if renderer == "markdown":
        rendered_content = render_markdown(packet)
        atomic_write_text(output_path, rendered_content)
    elif renderer == "tagged":
        if any(block.block_type == "source_file" for section in packet.sections for block in section.blocks):
            write_tagged_prompt_streaming(packet, output_path)
            rendered_content = normalize_text(output_path.read_text())
        else:
            rendered_content = render_tagged_prompt(packet)
            atomic_write_text(output_path, rendered_content)
    else:
        raise ValueError(f"unsupported renderer '{renderer}'")

    estimate_method = packet.budget_policy.estimate_method if packet.budget_policy else "heuristic:chars_div_4"
    budget_metric = packet.budget_policy.metric if packet.budget_policy else "tokens"
    manifest = build_manifest(
        packet,
        rendered_content=rendered_content,
        builder_name=builder_name,
        builder_version=builder_version,
        created_at=_utc_now(),
        estimate_method=estimate_method,
        budget_metric=budget_metric,
    )
    atomic_write_json(manifest_path, manifest)
    return BuildArtifact(
        content_path=output_path,
        manifest_path=manifest_path,
        content_hash=manifest["rendered_content_hash"],
        payload_hash=manifest["payload_hash"],
        rendered_bytes=manifest["rendered_bytes"],
        token_estimate=manifest["token_estimate"],
        estimate_method=manifest["estimate_method"],
        budget_metric=manifest["budget_metric"],
        truncated=bool(manifest["truncation_events"]),
    )


def write_text_artifact(
    *,
    content: str,
    output_path: Path,
    manifest_path: Path,
    builder_name: str,
    builder_version: str,
    metadata: dict[str, object] | None = None,
) -> BuildArtifact:
    packet = ContextPacket(
        title="raw-payload",
        sections=[],
        metadata=metadata or {},
    )
    estimate_method = "heuristic:chars_div_4"
    normalized_content = normalize_text(content)
    manifest = build_manifest(
        packet,
        rendered_content=normalized_content,
        builder_name=builder_name,
        builder_version=builder_version,
        created_at=_utc_now(),
        estimate_method=estimate_method,
        budget_metric="tokens",
    )
    atomic_write_text(output_path, normalized_content)
    atomic_write_json(manifest_path, manifest)
    return BuildArtifact(
        content_path=output_path,
        manifest_path=manifest_path,
        content_hash=manifest["rendered_content_hash"],
        payload_hash=manifest["payload_hash"],
        rendered_bytes=manifest["rendered_bytes"],
        token_estimate=manifest["token_estimate"],
        estimate_method=manifest["estimate_method"],
        budget_metric=manifest["budget_metric"],
        truncated=False,
    )
