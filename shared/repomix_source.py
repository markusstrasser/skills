from __future__ import annotations

import subprocess
from pathlib import Path


def build_include_pattern(entries: list[str]) -> str:
    patterns: list[str] = []
    for entry in entries:
        trimmed = entry.strip()
        if not trimmed:
            continue
        if any(char in trimmed for char in "*?[]"):
            patterns.append(trimmed)
        elif trimmed.endswith("/"):
            patterns.append(f"{trimmed}**")
        else:
            patterns.append(trimmed)
    return ",".join(patterns)


def repomix_args(*, include_pattern: str, exclude: str | None, no_gitignore: bool) -> list[str]:
    args = ["--stdout", "--include", include_pattern]
    if no_gitignore:
        args.append("--no-gitignore")
    if exclude:
        args.extend(["--ignore", exclude])
    return args


def capture_repomix_to_file(
    *,
    project_root: Path,
    include_pattern: str,
    exclude: str | None,
    no_gitignore: bool,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    args = ["repomix", *repomix_args(include_pattern=include_pattern, exclude=exclude, no_gitignore=no_gitignore)]
    with output_path.open("w") as handle:
        proc = subprocess.run(
            args,
            cwd=project_root,
            stdout=handle,
            stderr=subprocess.PIPE,
            text=True,
        )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "repomix failed")

