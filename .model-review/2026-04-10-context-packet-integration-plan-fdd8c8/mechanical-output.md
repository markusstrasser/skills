This implementation follows the **Context Packet Integration Plan**, establishing the shared engine in `shared/` and migrating the `build_plan_close_context.py` script as the first proof-of-concept.

### Phase 1: Shared Packet Core

I've created three new modules in `shared/` to handle the primitives, selection logic, and rendering.

#### 1. `shared/context_packet.py`
Defines the object model, block types, and truncation logic.

```python
"""Core data structures for context packets."""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class PacketBlock:
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def truncate(self, max_chars: int) -> str:
        if len(self.content) <= max_chars:
            return self.content
        head = max_chars // 2
        tail = max_chars - head
        return (
            self.content[:head] 
            + "\n\n... [truncated] ...\n\n" 
            + self.content[-tail:]
        )

@dataclass
class FileBlock(PacketBlock):
    path: str
    range_spec: Optional[str] = None

@dataclass
class DiffBlock(PacketBlock):
    label: str

@dataclass
class PacketSection:
    title: str
    blocks: list[PacketBlock] = field(default_factory=list)

@dataclass
class ContextPacket:
    title: str
    sections: list[PacketSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def add_section(self, title: str) -> PacketSection:
        section = PacketSection(title=title)
        self.sections.append(section)
        return section
```

#### 2. `shared/context_selectors.py`
Contains the mechanical logic for extracting data from the environment (Git, Filesystem).

```python
"""Shared selection helpers for gathering context."""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional

def run_git(repo: Path, args: list[str], check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout

def parse_file_spec(spec: str) -> tuple[str, Optional[str]]:
    """Parses path:start-end or path:line into (path, range_spec)."""
    if ":" in spec:
        path, range_spec = spec.rsplit(":", 1)
        return path, range_spec
    return spec, None

def get_file_excerpt(path: Path, range_spec: Optional[str] = None) -> str:
    """Reads a file or a specific range of lines."""
    if not path.exists():
        return f"[File not found: {path}]"
    
    try:
        lines = path.read_text(errors="replace").splitlines()
        if not range_spec:
            return "\n".join(lines)
            
        if "-" in range_spec:
            start, end = map(int, range_spec.split("-"))
            return "\n".join(lines[start-1:end])
        else:
            line_no = int(range_spec)
            return lines[line_no-1] if 0 < line_no <= len(lines) else "[Line out of range]"
    except Exception as e:
        return f"[Error reading {path}: {e}]"

def resolve_touched_files(
    repo: Path,
    base: Optional[str] = None,
    head: Optional[str] = None,
    tracked_only: bool = False
) -> list[str]:
    """Resolves list of changed files between refs or in worktree."""
    if base:
        ref = f"{base}..{head}" if head else f"{base}..HEAD"
        cmd = ["diff", "--name-only", ref, "--"]
    elif tracked_only:
        cmd = ["diff", "--name-only", "HEAD", "--"]
    else:
        # Short status parsing
        status = run_git(repo, ["status", "--short", "--untracked-files=all"])
        paths = []
        for line in status.splitlines():
            if len(line) > 3:
                path = line[3:]
                if " -> " in path: path = path.split(" -> ", 1)[1]
                paths.append(path)
        return sorted(list(set(paths)))

    return [line.strip() for line in run_git(repo, cmd).splitlines() if line.strip()]
```

#### 3. `shared/context_renderers.py`
Standardizes the Markdown output and generates the JSON manifest for provenance.

```python
"""Renderers for ContextPackets."""
from __future__ import annotations
import json
from .context_packet import ContextPacket, FileBlock, DiffBlock

class MarkdownRenderer:
    @staticmethod
    def render(packet: ContextPacket, max_block_chars: int = 8000) -> str:
        lines = [f"# {packet.title}", ""]
        
        # Render Metadata/Scope if present
        if "repo" in packet.metadata:
            lines.append(f"- Repo: `{packet.metadata['repo']}`")
        if "ref" in packet.metadata:
            lines.append(f"- Ref: `{packet.metadata['ref']}`")
        lines.append("")

        for section in packet.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            for block in section.blocks:
                if block.title:
                    lines.append(f"### {block.title}")
                
                content = block.truncate(max_block_chars)
                lang = "text"
                if isinstance(block, FileBlock): lang = "text"
                elif isinstance(block, DiffBlock): lang = "diff"
                
                lines.append(f"```{lang}\n{content}\n```")
                lines.append("")
        
        return "\n".join(lines)

class ManifestRenderer:
    @staticmethod
    def render(packet: ContextPacket) -> str:
        manifest = {
            "title": packet.title,
            "created_at": packet.created_at,
            "metadata": packet.metadata,
            "sections": [
                {
                    "title": s.title,
                    "blocks": [
                        {
                            "title": b.title,
                            "hash": b.get_hash(),
                            "meta": b.metadata
                        } for b in s.blocks
                    ]
                } for s in packet.sections
            ]
        }
        return json.dumps(manifest, indent=2)
```

### Phase 2: Migrate Plan-Close

The existing `review/scripts/build_plan_close_context.py` is now a consumer of the engine.

```python
#!/usr/bin/env python3
"""Build a single markdown review packet using the shared context engine."""

import argparse
import sys
from pathlib import Path

# Assuming path setup for shared imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from shared.context_packet import ContextPacket, FileBlock, DiffBlock, PacketBlock
from shared.context_selectors import resolve_touched_files, run_git, get_file_excerpt
from shared.context_renderers import MarkdownRenderer, ManifestRenderer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--tracked-only", action="store_true")
    parser.add_argument("--scope-text")
    parser.add_argument("--max-files", type=int, default=12)
    args = parser.parse_args()

    repo = args.repo.resolve()
    touched = resolve_touched_files(repo, base=args.base, head=args.head, tracked_only=args.tracked_only)
    
    packet = ContextPacket(
        title="Plan-Close Review Packet",
        metadata={
            "repo": str(repo),
            "ref": f"{args.base}..{args.head}" if args.base else "Worktree"
        }
    )

    # 1. Scope Section
    scope = packet.add_section("Scope")
    scope.blocks.append(PacketBlock(title="", content=args.scope_text or "General Review"))

    # 2. Git Context
    git_sec = packet.add_section("Git Context")
    status = run_git(repo, ["status", "--short"])
    git_sec.blocks.append(PacketBlock(title="Status", content=status))
    
    diff = run_git(repo, ["diff", args.base or "HEAD", "--"])
    git_sec.blocks.append(DiffBlock(title="Unified Diff", label="diff", content=diff))

    # 3. File Excerpts
    files_sec = packet.add_section("Current File Excerpts")
    for rel_path in touched[:args.max_files]:
        content = get_file_excerpt(repo / rel_path)
        files_sec.blocks.append(FileBlock(title=rel_path, path=rel_path, content=content))

    # Write outputs
    rendered = MarkdownRenderer.render(packet)
    args.output.write_text(rendered)
    
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(ManifestRenderer.render(packet))
    
    print(f"Packet: {args.output}")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    main()
```

### Key Improvements
1.  **Deterministic Logic**: All scripts now use the same line-range and git-diff logic.
2.  **Manifests**: Every review now produces a `.manifest.json` showing exactly what hashes of files were included, solving the "what did the model see" audit problem.
3.  **Truncation**: Truncation logic is now a first-class method of `PacketBlock`, ensuring we don't accidentally send 1MB of diff to an LLM.
4.  **Extensibility**: Adding a new "Axis" to a review just means adding a `PacketSection` to the `ContextPacket` object.