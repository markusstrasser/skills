from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


DIFF_TRUNCATION_MARKER = "... [diff truncated] ..."


@dataclass(frozen=True)
class GitStatusEntry:
    code: str
    path: str
    old_path: str | None = None


def run_git(repo: Path, args: list[str], *, check: bool = True, text: bool = True):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=text,
    )
    if check and proc.returncode != 0:
        stderr = proc.stderr if text else proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def diff_ref(base: str | None, head: str | None) -> str | None:
    if base and head:
        return f"{base}..{head}"
    if base:
        return f"{base}..HEAD"
    if head:
        return f"HEAD..{head}"
    return None


def parse_status_porcelain(raw: bytes) -> list[GitStatusEntry]:
    entries: list[GitStatusEntry] = []
    fields = raw.split(b"\x00")
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4:
            continue
        code = field[:2].decode("utf-8", errors="replace")
        path = field[3:].decode("utf-8", errors="replace")
        old_path = None
        if code.startswith(("R", "C")) and index < len(fields):
            old_path = path
            path = fields[index].decode("utf-8", errors="replace")
            index += 1
        entries.append(GitStatusEntry(code=code, path=path, old_path=old_path))
    return entries


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
        output = run_git(repo, ["diff", "--name-only", "-z", ref, "--"], text=False)
        names = [item.decode("utf-8", errors="replace") for item in output.split(b"\x00") if item]
        return unique_paths(names)

    if tracked_only:
        tracked = run_git(repo, ["diff", "--name-only", "-z", "HEAD", "--"], check=False, text=False)
        staged = run_git(repo, ["diff", "--cached", "--name-only", "-z", "HEAD", "--"], check=False, text=False)
        names = [item.decode("utf-8", errors="replace") for item in tracked.split(b"\x00") if item]
        names.extend(item.decode("utf-8", errors="replace") for item in staged.split(b"\x00") if item)
        return unique_paths(names)

    raw = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], text=False)
    return unique_paths([entry.path for entry in parse_status_porcelain(raw)])


def current_status(repo: Path, *, tracked_only: bool) -> str:
    args = ["status", "--short"]
    args.append("--untracked-files=no" if tracked_only else "--untracked-files=all")
    return str(run_git(repo, args, check=False)).strip()


def untracked_paths(repo: Path) -> set[str]:
    raw = run_git(repo, ["ls-files", "--others", "--exclude-standard", "-z"], check=False, text=False)
    return {item.decode("utf-8", errors="replace") for item in raw.split(b"\x00") if item}


def tracked_paths(repo: Path, files: list[str]) -> list[str]:
    untracked = untracked_paths(repo)
    return [path for path in files if path not in untracked]


def collect_diff_stat(repo: Path, *, ref: str | None, files: list[str]) -> str:
    tracked = tracked_paths(repo, files)
    if not tracked:
        return "(no tracked diff stat available)"
    args = ["diff", "--stat"]
    args.append(ref or "HEAD")
    args.append("--")
    args.extend(tracked)
    return str(run_git(repo, args, check=False)).strip() or "(empty diff stat)"


def _split_diff_chunks(diff_text: str) -> list[str]:
    lines = diff_text.splitlines()
    if not lines:
        return []
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("diff --git ") and current:
            chunks.append(current)
            current = [line]
            continue
        current.append(line)
    if current:
        chunks.append(current)
    return ["\n".join(chunk) for chunk in chunks]


def _append_marker_within_limit(text: str, *, max_chars: int, marker: str) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 0:
        return ""

    suffix = "\n" + marker
    if len(suffix) >= max_chars:
        return suffix[-max_chars:]

    budget = max_chars - len(suffix)
    return text[:budget].rstrip() + suffix


def truncate_diff_text(diff_text: str, max_chars: int) -> tuple[str, bool]:
    if len(diff_text) <= max_chars:
        return diff_text, False

    chunks = _split_diff_chunks(diff_text)
    if not chunks:
        return _append_marker_within_limit(diff_text, max_chars=max_chars, marker=DIFF_TRUNCATION_MARKER), True

    selected: list[str] = []
    total = 0
    for chunk in chunks:
        chunk_len = len(chunk) + (2 if selected else 0)
        if total + chunk_len <= max_chars:
            selected.append(chunk)
            total += chunk_len
            continue
        if not selected:
            lines = chunk.splitlines()
            partial: list[str] = []
            current_len = 0
            for line in lines:
                next_len = current_len + len(line) + 1
                if next_len >= max_chars:
                    break
                partial.append(line)
                current_len = next_len
            selected.append("\n".join(partial))
        break

    rendered = "\n\n".join(part.rstrip() for part in selected if part.strip()).rstrip()
    return _append_marker_within_limit(rendered, max_chars=max_chars, marker=DIFF_TRUNCATION_MARKER), True


def collect_diff(repo: Path, *, ref: str | None, files: list[str], max_chars: int | None = None) -> tuple[str, bool]:
    tracked = tracked_paths(repo, files)
    if not tracked:
        return "(no tracked unified diff available)", False
    args = ["diff", "--unified=3"]
    args.append(ref or "HEAD")
    args.append("--")
    args.extend(tracked)
    diff_text = str(run_git(repo, args, check=False)).strip() or "(empty diff)"
    if max_chars is None:
        return diff_text, False
    return truncate_diff_text(diff_text, max_chars)
