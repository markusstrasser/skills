from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.context_packet import FileBlock


TRUNCATION_MARKER = "\n\n... [truncated for review packet] ...\n\n"


@dataclass(frozen=True)
class FileSpec:
    path: Path
    range_spec: str | None = None
    start_line: int | None = None
    end_line: int | None = None

    @property
    def display_path(self) -> str:
        return str(self.path)


def parse_file_spec(spec: str) -> FileSpec:
    trimmed = spec.strip()
    if ":" not in trimmed:
        return FileSpec(path=Path(trimmed).expanduser())

    file_part, maybe_range = trimmed.rsplit(":", 1)
    if not maybe_range or not maybe_range.replace("-", "").isdigit():
        return FileSpec(path=Path(trimmed).expanduser())

    path = Path(file_part).expanduser()
    if "-" in maybe_range:
        start_text, end_text = maybe_range.split("-", 1)
        return FileSpec(
            path=path,
            range_spec=maybe_range,
            start_line=int(start_text),
            end_line=int(end_text),
        )
    line_number = int(maybe_range)
    return FileSpec(
        path=path,
        range_spec=maybe_range,
        start_line=line_number,
        end_line=line_number,
    )


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data


def _truncate_middle(text: str, *, max_chars: int, marker: str) -> str:
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


def read_file_excerpt(spec: FileSpec, *, max_chars: int | None = None) -> tuple[str, bool, str | None]:
    if not spec.path.exists():
        return "[read failed: file not found]", False, "missing"
    if spec.path.is_symlink():
        return f"[symlink target: {spec.path.resolve()}]", False, "symlink"
    if spec.path.is_dir():
        return "[directory omitted from context packet]", False, "directory"

    raw = spec.path.read_bytes()
    if _is_binary(raw[:4096]):
        return "[binary file omitted from context packet]", False, "binary"

    text = raw.decode("utf-8", errors="replace")
    if spec.start_line is not None and spec.end_line is not None:
        lines = text.splitlines()
        start_index = max(spec.start_line - 1, 0)
        end_index = min(spec.end_line, len(lines))
        text = "\n".join(lines[start_index:end_index])

    truncated = False
    if max_chars is not None and len(text) > max_chars:
        text = _truncate_middle(text, max_chars=max_chars, marker=TRUNCATION_MARKER)
        truncated = True
    return text, truncated, None


def build_file_block(spec: FileSpec, *, max_chars: int | None = None):
    text, truncated, omission = read_file_excerpt(spec, max_chars=max_chars)
    metadata: dict[str, object] = {}
    if omission:
        metadata["omission_reason"] = omission
    return FileBlock(
        spec.display_path,
        text,
        range_spec=spec.range_spec,
        truncated=truncated,
        truncation_reason="file_excerpt_limit" if truncated else None,
        original_chars=None if not truncated else len(spec.path.read_text(errors="replace")),
        metadata=metadata,
    )
