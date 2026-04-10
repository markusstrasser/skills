from __future__ import annotations

from dataclasses import dataclass, replace

from shared.context_packet import ContextPacket, PacketBlock, PacketSection, estimate_tokens
from shared.context_renderers import render_markdown, render_tagged_prompt


RENDERERS = {
    "markdown": render_markdown,
    "tagged": render_tagged_prompt,
}


@dataclass(frozen=True)
class BudgetOutcome:
    packet: ContextPacket
    estimated_usage: int
    limit: int | None
    metric: str
    estimate_method: str
    dropped_blocks: list[dict[str, object]]
    truncated_blocks: list[dict[str, object]]
    changed: bool


def _estimate_usage(packet: ContextPacket, *, renderer: str) -> tuple[int, str, str]:
    render = RENDERERS[renderer]
    rendered = render(packet)
    if packet.budget_policy is None:
        return estimate_tokens(rendered), "tokens", "heuristic:chars_div_4"
    if packet.budget_policy.metric == "chars":
        return len(rendered), "chars", packet.budget_policy.estimate_method
    return estimate_tokens(rendered, packet.budget_policy.estimate_method), "tokens", packet.budget_policy.estimate_method


def _with_budget_metadata(packet: ContextPacket, *, usage: int, limit: int | None, metric: str, estimate_method: str, dropped_blocks: list[dict[str, object]]) -> ContextPacket:
    metadata = dict(packet.metadata)
    metadata["budget_enforcement"] = {
        "usage": usage,
        "limit": limit,
        "metric": metric,
        "estimate_method": estimate_method,
        "dropped_blocks": dropped_blocks,
        "truncated_blocks": metadata.get("budget_enforcement", {}).get("truncated_blocks", []),
    }
    return replace(packet, metadata=metadata)


def _truncate_middle(text: str, *, max_chars: int, marker: str = "\n\n... [packet budget truncation] ...\n\n") -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 0:
        return ""
    if len(marker) >= max_chars:
        return marker[:max_chars]
    available = max_chars - len(marker)
    head = available // 2
    tail = available - head
    return text[:head] + marker + text[-tail:]


def _replace_block(packet: ContextPacket, *, section_index: int, block_index: int, new_block: PacketBlock) -> ContextPacket:
    sections = list(packet.sections)
    target_section = sections[section_index]
    blocks = list(target_section.blocks)
    blocks[block_index] = new_block
    sections[section_index] = PacketSection(title=target_section.title, blocks=blocks, tag=target_section.tag)
    return replace(packet, sections=sections)


def enforce_budget(packet: ContextPacket, *, renderer: str) -> BudgetOutcome:
    usage, metric, estimate_method = _estimate_usage(packet, renderer=renderer)
    policy = packet.budget_policy
    if policy is None or usage <= policy.limit:
        packet_with_meta = _with_budget_metadata(
            packet,
            usage=usage,
            limit=policy.limit if policy else None,
            metric=metric,
            estimate_method=estimate_method,
            dropped_blocks=[],
        )
        return BudgetOutcome(
            packet=packet_with_meta,
            estimated_usage=usage,
            limit=policy.limit if policy else None,
            metric=metric,
            estimate_method=estimate_method,
            dropped_blocks=[],
            truncated_blocks=[],
            changed=False,
        )

    truncated_blocks: list[dict[str, object]] = []
    trunc_candidates: list[tuple[int, int, int, PacketBlock]] = []
    for section_index, section in enumerate(packet.sections):
        for block_index, block in enumerate(section.blocks):
            minimum = block.min_chars if block.min_chars is not None else 0
            if block.truncatable and block.block_type != "source_file" and block.rendered_chars() > minimum:
                trunc_candidates.append((block.priority, section_index, block_index, block))
    trunc_candidates.sort(key=lambda item: (item[0], -item[3].rendered_chars(), item[1], item[2]))

    while usage > policy.limit:
        changed_this_round = False
        overflow = usage - policy.limit
        approx_char_overflow = overflow * 4 if metric == "tokens" else overflow
        for priority, section_index, block_index, block in trunc_candidates:
            current_block = packet.sections[section_index].blocks[block_index]
            current_len = current_block.rendered_chars()
            minimum = current_block.min_chars if current_block.min_chars is not None else 0
            if current_len <= minimum:
                continue
            cut_target = max(approx_char_overflow, max(current_len // 3, 256))
            target_chars = max(minimum, current_len - cut_target)
            if target_chars >= current_len:
                continue
            new_text = _truncate_middle(current_block.text, max_chars=target_chars)
            if new_text == current_block.text:
                continue
            new_block = replace(
                current_block,
                text=new_text,
                truncated=True,
                truncation_reason="budget_enforced",
                original_chars=current_block.original_chars or current_len,
            )
            packet = _replace_block(packet, section_index=section_index, block_index=block_index, new_block=new_block)
            usage, metric, estimate_method = _estimate_usage(packet, renderer=renderer)
            truncated_blocks.append(
                {
                    "section_title": packet.sections[section_index].title,
                    "block_title": current_block.title,
                    "block_type": current_block.block_type,
                    "priority": priority,
                    "original_chars": current_len,
                    "rendered_chars": new_block.rendered_chars(),
                }
            )
            changed_this_round = True
            if usage <= policy.limit:
                break
        if usage <= policy.limit or not changed_this_round:
            break

    candidates: list[tuple[int, int, int, PacketBlock]] = []
    for section_index, section in enumerate(packet.sections):
        for block_index, block in enumerate(section.blocks):
            if block.drop_if_needed:
                candidates.append((block.priority, section_index, block_index, block))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))

    remaining_sections = [PacketSection(title=section.title, blocks=list(section.blocks), tag=section.tag) for section in packet.sections]
    dropped_blocks: list[dict[str, object]] = []

    for priority, section_index, block_index, block in candidates:
        current_section = remaining_sections[section_index]
        current_index = next(
            (
                idx
                for idx, current_block in enumerate(current_section.blocks)
                if current_block.title == block.title and current_block.block_type == block.block_type
            ),
            None,
        )
        if current_index is None:
            continue

        updated_blocks = [candidate for idx, candidate in enumerate(current_section.blocks) if idx != current_index]
        remaining_sections[section_index] = PacketSection(title=current_section.title, blocks=updated_blocks, tag=current_section.tag)
        candidate_packet = replace(
            packet,
            sections=[section for section in remaining_sections if section.blocks],
        )
        usage, metric, estimate_method = _estimate_usage(candidate_packet, renderer=renderer)
        dropped_blocks.append(
            {
                "section_title": current_section.title,
                "block_title": block.title,
                "block_type": block.block_type,
                "priority": priority,
            }
        )
        if usage <= policy.limit:
            packet_with_meta = _with_budget_metadata(
                candidate_packet,
                usage=usage,
                limit=policy.limit,
                metric=metric,
                estimate_method=estimate_method,
                dropped_blocks=dropped_blocks,
            )
            packet_with_meta.metadata["budget_enforcement"]["truncated_blocks"] = truncated_blocks
            return BudgetOutcome(
                packet=packet_with_meta,
                estimated_usage=usage,
                limit=policy.limit,
                metric=metric,
                estimate_method=estimate_method,
                dropped_blocks=dropped_blocks,
                truncated_blocks=truncated_blocks,
                changed=True,
            )
        packet = candidate_packet

    packet_with_meta = _with_budget_metadata(
        packet,
        usage=usage,
        limit=policy.limit,
        metric=metric,
        estimate_method=estimate_method,
        dropped_blocks=dropped_blocks,
    )
    packet_with_meta.metadata["budget_enforcement"]["truncated_blocks"] = truncated_blocks
    return BudgetOutcome(
        packet=packet_with_meta,
        estimated_usage=usage,
        limit=policy.limit,
        metric=metric,
        estimate_method=estimate_method,
        dropped_blocks=dropped_blocks,
        truncated_blocks=truncated_blocks,
        changed=bool(dropped_blocks or truncated_blocks),
    )
