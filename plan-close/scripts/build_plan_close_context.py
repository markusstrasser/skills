#!/usr/bin/env python3
"""Build a single markdown review packet for plan-close / post-implementation review.

The packet is intentionally single-file because llmx multi-file `-f` transport
has recurring loss/truncation failures in critical review flows.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def log_progress(message: str) -> None:
    print(f"[build-plan-close-context] {message}", file=sys.stderr)


def run_git(repo: Path, args: list[str], *, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def diff_ref(base: str | None, head: str | None) -> str | None:
    if base and head:
        return f"{base}..{head}"
    if base:
        return f"{base}..HEAD"
    if head:
        return f"HEAD..{head}"
    return None


def parse_status_paths(status_text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for raw_line in status_text.splitlines():
        line = raw_line.rstrip()
        if len(line) < 4:
            continue
        path_field = line[3:]
        if " -> " in path_field:
            path_field = path_field.split(" -> ", 1)[1]
        if path_field and path_field not in seen:
            seen.add(path_field)
            paths.append(path_field)
    return paths


def unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def resolve_touched_files(
    repo: Path,
    *,
    base: str | None,
    head: str | None,
    files: list[str] | None,
    tracked_only: bool,
) -> list[str]:
    if files:
        return unique_paths(files)

    ref = diff_ref(base, head)
    if ref:
        names = run_git(repo, ["diff", "--name-only", ref, "--"]).splitlines()
        return [name for name in names if name.strip()]

    if tracked_only:
        names = run_git(repo, ["diff", "--name-only", "HEAD", "--"], check=False).splitlines()
        return [name for name in names if name.strip()]

    status_text = run_git(repo, ["status", "--short", "--untracked-files=all"])
    return parse_status_paths(status_text)


def current_status(repo: Path, *, tracked_only: bool) -> str:
    args = ["status", "--short"]
    args.append("--untracked-files=no" if tracked_only else "--untracked-files=all")
    return run_git(repo, args, check=False).strip()


def untracked_paths(repo: Path) -> set[str]:
    raw = run_git(repo, ["ls-files", "--others", "--exclude-standard"], check=False)
    return {line.strip() for line in raw.splitlines() if line.strip()}


def collect_diff_stat(repo: Path, *, ref: str | None, files: list[str]) -> str:
    tracked_files = [path for path in files if path not in untracked_paths(repo)]
    if not tracked_files:
        return "(no tracked diff stat available)"
    args = ["diff", "--stat"]
    if ref:
        args.append(ref)
    else:
        args.append("HEAD")
    args.append("--")
    args.extend(tracked_files)
    return run_git(repo, args, check=False).strip() or "(empty diff stat)"


def collect_diff(repo: Path, *, ref: str | None, files: list[str]) -> str:
    tracked_files = [path for path in files if path not in untracked_paths(repo)]
    if not tracked_files:
        return "(no tracked unified diff available)"
    args = ["diff", "--unified=3"]
    if ref:
        args.append(ref)
    else:
        args.append("HEAD")
    args.append("--")
    args.extend(tracked_files)
    return run_git(repo, args, check=False).strip() or "(empty diff)"


def read_excerpt(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(errors="replace")
    except OSError as exc:
        return f"[read failed: {exc}]"

    if len(text) <= max_chars:
        return text

    head = max_chars // 2
    tail = max_chars - head
    return (
        text[:head]
        + "\n\n... [truncated for review packet] ...\n\n"
        + text[-tail:]
    )


def file_section(repo: Path, rel_path: str, *, max_chars: int) -> str:
    path = repo / rel_path
    if not path.exists():
        return f"### {rel_path}\n\n(deleted or absent in current worktree)\n"

    return (
        f"### {rel_path}\n\n"
        f"```text\n{read_excerpt(path, max_chars)}\n```\n"
    )


def build_packet(
    repo: Path,
    *,
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
    log_progress("resolving touched files")
    touched = resolve_touched_files(repo, base=base, head=head, files=files, tracked_only=tracked_only)
    ref = diff_ref(base, head)
    log_progress("collecting git status")
    status_text = current_status(repo, tracked_only=tracked_only) or "(clean)"
    log_progress(f"collecting diffs for {len(touched)} touched files")
    diff_stat = collect_diff_stat(repo, ref=ref, files=touched) if touched else "(no touched files)"
    diff_text = collect_diff(repo, ref=ref, files=touched) if touched else "(no touched files)"
    if len(diff_text) > max_diff_chars:
        diff_text = diff_text[:max_diff_chars] + "\n\n... [diff truncated] ..."

    if scope_file is not None:
        scope_block = scope_file.read_text()
    elif scope_text:
        scope_block = scope_text
    else:
        scope_block = (
            "- Target users: FILL ME\n"
            "- Scale: FILL ME\n"
            "- Rate of change: FILL ME\n"
        )

    packet = [
        "# Plan-Close Review Packet",
        "",
        f"- Repo: `{repo}`",
        f"- Mode: `{'commit-range' if ref else 'worktree'}`",
        f"- Ref: `{ref or 'HEAD vs current worktree'}`",
        "",
        "## Scope",
        "",
        scope_block.strip(),
        "",
        "## Touched Files",
        "",
    ]

    if touched:
        packet.extend(f"- `{path}`" for path in touched)
    else:
        packet.append("- (none)")

    packet.extend(
        [
            "",
            "## Git Status",
            "",
            "```text",
            status_text,
            "```",
            "",
            "## Diff Stat",
            "",
            "```text",
            diff_stat,
            "```",
            "",
            "## Unified Diff",
            "",
            "```diff",
            diff_text,
            "```",
            "",
            "## Current File Excerpts",
            "",
        ]
    )

    display_files = touched[:max_files]
    log_progress(f"reading excerpts for {len(display_files)} files")
    for rel_path in display_files:
        packet.append(file_section(repo, rel_path, max_chars=max_file_chars))

    omitted = len(touched) - len(display_files)
    if omitted > 0:
        packet.append(f"\n(Omitted {omitted} additional touched files from excerpts.)\n")

    return "\n".join(packet)


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

    packet = build_packet(
        repo,
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(packet)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
