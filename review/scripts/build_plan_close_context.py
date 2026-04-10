#!/usr/bin/env python3
"""Build a single markdown review packet for plan-close / post-implementation review.

The packet is intentionally single-file because llmx multi-file transport has
recurring loss/truncation failures in critical review flows.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.context_budget import enforce_budget
from shared.context_packet import BudgetPolicy, CommandBlock, ContextPacket, DiffBlock, FileBlock, ListBlock, PacketSection, TextBlock
from shared.context_renderers import render_markdown, write_packet_artifact
from shared.file_specs import parse_file_spec, read_file_excerpt
from shared.git_context import collect_diff, collect_diff_stat, current_status, diff_ref, resolve_touched_files
from shared.llm_dispatch import profile_input_budget


BUILDER_VERSION = "2026-04-10-v1"


def log_progress(message: str) -> None:
    print(f"[build-plan-close-context] {message}", file=sys.stderr)


def build_scope(scope_text: str | None, scope_file: Path | None) -> str:
    if scope_file is not None:
        return scope_file.read_text().strip()
    if scope_text:
        return scope_text.strip()
    return (
        "- Target users: FILL ME\n"
        "- Scale: FILL ME\n"
        "- Rate of change: FILL ME"
    )


def build_packet_model(
    repo: Path,
    *,
    profile_name: str,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
    scope_text: str | None,
    scope_file: Path | None,
    max_diff_chars: int,
    max_file_chars: int,
    max_files: int,
    budget_limit_override: int | None = None,
) -> ContextPacket:
    log_progress("resolving touched files")
    touched = resolve_touched_files(repo, base=base, head=head, files=files, tracked_only=tracked_only)
    ref = diff_ref(base, head)

    log_progress("collecting git status")
    status_text = current_status(repo, tracked_only=tracked_only) or "(clean)"
    log_progress(f"collecting diffs for {len(touched)} touched files")
    diff_stat = collect_diff_stat(repo, ref=ref, files=touched) if touched else "(no touched files)"
    diff_text, diff_truncated = collect_diff(repo, ref=ref, files=touched, max_chars=max_diff_chars) if touched else ("(no touched files)", False)

    touched_section = PacketSection(
        "Touched Files",
        [ListBlock("Touched Files", [f"- `{path}`" for path in touched] if touched else ["- (none)"], priority=70, drop_if_needed=True)],
    )
    git_section = PacketSection(
        "Git Status",
        [
            CommandBlock("git status --short", status_text, priority=50, drop_if_needed=True),
            CommandBlock("git diff --stat", diff_stat, priority=60, drop_if_needed=True),
            DiffBlock(
                "Unified Diff",
                diff_text,
                priority=200,
                drop_if_needed=False,
                min_chars=2_000,
                truncated=diff_truncated,
                truncation_reason="diff_char_limit" if diff_truncated else None,
            ),
        ],
    )

    display_files = touched[:max_files]
    log_progress(f"reading excerpts for {len(display_files)} files")
    file_sections_blocks = []
    for rel_path in display_files:
        spec_path = repo / rel_path
        spec = parse_file_spec(str(spec_path))
        text, truncated, omission_reason = read_file_excerpt(spec, max_chars=max_file_chars)
        metadata: dict[str, object] = {}
        if omission_reason:
            metadata["omission_reason"] = omission_reason
        block = FileBlock(
            rel_path,
            text,
            range_spec=spec.range_spec,
            priority=30,
            drop_if_needed=True,
            min_chars=1_200,
            truncated=truncated,
            truncation_reason="file_excerpt_limit" if truncated else None,
            original_chars=None if not truncated else len(spec_path.read_text(errors="replace")),
            metadata=metadata,
        )
        file_sections_blocks.append(block)
    omitted = len(touched) - len(display_files)
    if omitted > 0:
        file_sections_blocks.append(TextBlock("Omitted Files", f"(Omitted {omitted} additional touched files from excerpts.)", priority=10, drop_if_needed=True))
    files_section = PacketSection("Current File Excerpts", file_sections_blocks or [TextBlock("Current File Excerpts", "(none)", priority=10, drop_if_needed=True)])

    budget = profile_input_budget(profile_name)
    budget_limit = budget_limit_override if budget_limit_override is not None else budget["input_token_limit"]

    packet = ContextPacket(
        title="Plan-Close Review Packet",
        sections=[touched_section, git_section, files_section],
        scope=build_scope(scope_text, scope_file),
        metadata={
            "Repo": str(repo),
            "Mode": "commit-range" if ref else "worktree",
            "Ref": ref or "HEAD vs current worktree",
            "Profile": profile_name,
            "diff_char_cap": max_diff_chars,
            "file_char_cap": max_file_chars,
            "max_file_count": max_files,
        },
        budget_policy=BudgetPolicy(
            metric="tokens",
            limit=budget_limit or 120_000,
            estimate_method=budget["input_token_estimator"],
        ),
    )
    return enforce_budget(packet, renderer="markdown").packet


def build_packet(
    repo: Path,
    *,
    profile_name: str,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
    scope_text: str | None,
    scope_file: Path | None,
    max_diff_chars: int,
    max_file_chars: int,
    max_files: int,
) -> str:
    packet = build_packet_model(
        repo,
        profile_name=profile_name,
        base=base,
        head=head,
        files=files,
        tracked_only=tracked_only,
        scope_text=scope_text,
        scope_file=scope_file,
        max_diff_chars=max_diff_chars,
        max_file_chars=max_file_chars,
        max_files=max_files,
    )
    return render_markdown(packet)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Git repo to inspect")
    parser.add_argument("--output", type=Path, required=True, help="Markdown packet path")
    parser.add_argument("--base", help="Base git ref for commit-range review")
    parser.add_argument("--head", help="Head git ref for commit-range review")
    parser.add_argument("--file", action="append", dest="files", help="Specific file to include; may repeat")
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help=(
            "In worktree mode, limit touched files and git status to tracked changes only. "
            "Use this on dirty repos with large .scratch/ or other untracked trees."
        ),
    )
    parser.add_argument("--scope-text", help="Inline scope block for the packet")
    parser.add_argument("--scope-file", type=Path, help="File containing the scope block")
    parser.add_argument("--profile", default="formal_review", help="Dispatch profile whose input budget should bound the packet")
    parser.add_argument("--max-diff-chars", type=int, default=40_000)
    parser.add_argument("--max-file-chars", type=int, default=8_000)
    parser.add_argument("--max-files", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        print(f"not a git repo: {repo}", file=sys.stderr)
        return 2

    packet = build_packet_model(
        repo,
        profile_name=args.profile,
        base=args.base,
        head=args.head,
        files=args.files,
        tracked_only=args.tracked_only,
        scope_text=args.scope_text,
        scope_file=args.scope_file,
        max_diff_chars=args.max_diff_chars,
        max_file_chars=args.max_file_chars,
        max_files=args.max_files,
    )

    log_progress(f"writing packet to {args.output}")
    manifest_path = args.output.with_suffix(".manifest.json")
    write_packet_artifact(
        packet,
        renderer="markdown",
        output_path=args.output,
        manifest_path=manifest_path,
        builder_name="plan_close_context",
        builder_version=BUILDER_VERSION,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
