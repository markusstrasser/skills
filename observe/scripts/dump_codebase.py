#!/usr/bin/env python3
"""Dump an entire codebase into a structured markdown document for LLM ingestion.

Respects .gitignore, skips binary files, orders by importance (config first,
then by fan-in — files imported by the most other files). When over budget,
uses AST skeletonization (signatures only) instead of raw truncation.

Usage:
    python3 dump_codebase.py ~/Projects/genomics --output /tmp/codebase.md --max-tokens 400000
"""

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

# File extensions to include, ordered by priority
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".sh", ".bash",
    ".sql", ".toml", ".yaml", ".yml", ".json", ".md", ".cfg", ".ini",
    ".env.example", ".dockerfile", ".Makefile",
}

# Config files that should appear first (project context)
CONFIG_PRIORITY = [
    "CLAUDE.md", "README.md", "pyproject.toml", "Cargo.toml", "package.json",
    "tsconfig.json", "Makefile", "docker-compose.yml", "Dockerfile",
    ".env.example", "setup.py", "setup.cfg",
]

# Directories to always skip (even if not in .gitignore)
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "target",
    "dist", "build", ".eggs", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".project-upgrade", ".model-review",
}

# Max file size in bytes (skip files larger than this)
MAX_FILE_SIZE = 100_000  # 100KB per file

# Rough tokens-per-char ratio
CHARS_PER_TOKEN = 4


def get_git_tracked_files(project_root: Path) -> set[str]:
    """Get files tracked by git (respects .gitignore)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return set(result.stdout.strip().split("\n"))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return set()


def is_binary(filepath: Path) -> bool:
    """Quick binary check: look for null bytes in first 8KB."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except (OSError, PermissionError):
        return True


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def skeletonize_python(content: str) -> str:
    """Extract class/function signatures from Python source, omitting bodies.

    Preserves the API surface (what can be imported/called) while
    dramatically reducing token count. This prevents Gemini from
    hallucinating DEAD_CODE for functions defined beyond the truncation point.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Fall back to first 100 lines if AST fails
        lines = content.split("\n")
        return "\n".join(lines[:100]) + f"\n\n# [SKELETON FAILED — showing first 100 of {len(lines)} lines]"

    parts = []
    # Top-level imports and assignments
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            parts.append(ast.get_source_segment(content, node) or "")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            segment = ast.get_source_segment(content, node)
            if segment:
                parts.append(segment)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            sig = _extract_func_signature(content, node)
            parts.append(sig)
        elif isinstance(node, ast.ClassDef):
            sig = _extract_class_skeleton(content, node)
            parts.append(sig)

    total_lines = len(content.split("\n"))
    skeleton = "\n\n".join(parts)
    skeleton += f"\n\n# [SKELETON: {total_lines} lines → signatures only]"
    return skeleton


def _extract_func_signature(source: str, node: ast.FunctionDef) -> str:
    """Extract function signature + docstring."""
    lines = source.split("\n")
    # Get the def line(s) — may span multiple lines with long signatures
    start = node.lineno - 1
    # Find the colon that ends the signature
    sig_lines = []
    for i in range(start, min(start + 10, len(lines))):
        sig_lines.append(lines[i])
        if ":" in lines[i]:
            break

    sig = "\n".join(sig_lines)

    # Add docstring if present
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        docstring = node.body[0].value.value
        # Truncate long docstrings
        if len(docstring) > 200:
            docstring = docstring[:200] + "..."
        sig += f'\n    """{docstring}"""'

    sig += "\n    ..."
    return sig


def _extract_class_skeleton(source: str, node: ast.ClassDef) -> str:
    """Extract class definition with method signatures."""
    lines = source.split("\n")
    start = node.lineno - 1
    # Get the class line
    class_line = lines[start]

    parts = [class_line]

    # Class docstring
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        docstring = node.body[0].value.value
        if len(docstring) > 200:
            docstring = docstring[:200] + "..."
        parts.append(f'    """{docstring}"""')

    # Method signatures
    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            sig = _extract_func_signature(source, item)
            # Indent for class method
            parts.append("    " + sig.replace("\n", "\n    "))

    return "\n".join(parts)


def compute_fan_in(project_root: Path, files: list[tuple[Path, str]]) -> dict[str, int]:
    """Count how many files import each module (fan-in).

    Higher fan-in = more important to include fully (breaking changes
    to high-fan-in files affect more of the codebase).
    """
    fan_in: dict[str, int] = {}
    py_files = [(f, c) for f, c in files if f.suffix == ".py"]

    # Build a set of module names from file paths
    module_names: dict[str, Path] = {}
    for filepath, _ in py_files:
        rel = filepath.relative_to(project_root)
        # Convert path to module name: scripts/modal_utils.py → modal_utils
        stem = rel.stem
        module_names[stem] = filepath
        fan_in[str(rel)] = 0

    # Count imports
    import_pattern = re.compile(
        r'(?:from\s+\.?(\w+)|import\s+(\w+))'
    )
    for filepath, _ in py_files:
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue
        for match in import_pattern.finditer(content):
            imported = match.group(1) or match.group(2)
            if imported in module_names:
                target = str(module_names[imported].relative_to(project_root))
                fan_in[target] = fan_in.get(target, 0) + 1

    return fan_in


def collect_files(
    project_root: Path, files_from: Path | None = None
) -> list[tuple[Path, str]]:
    """Collect source files, return as (path, category) pairs.

    If files_from is provided, only include those files plus their direct
    importers (fan-in neighbors). This enables diff-aware mode.
    """
    # If files_from specified, restrict to those files + their importers
    restrict_to: set[str] | None = None
    if files_from and files_from.exists():
        seed_files = {
            line.strip()
            for line in files_from.read_text().strip().split("\n")
            if line.strip()
        }
        # Always include config files for context
        restrict_to = set(seed_files)
        # Add direct importers of changed files (so we see callers too)
        importers = _find_importers(project_root, seed_files)
        restrict_to.update(importers)

    git_files = get_git_tracked_files(project_root)
    use_git = len(git_files) > 0

    config_files = []
    source_files = []

    for root_str, dirs, files in os.walk(project_root):
        root = Path(root_str)

        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            filepath = root / filename
            rel_path = filepath.relative_to(project_root)
            rel_str = str(rel_path)

            # Skip if git-tracked files are available and this isn't tracked
            if use_git and rel_str not in git_files:
                continue

            # In diff-aware mode, skip files not in the restrict set
            # (but always include config files for context)
            if restrict_to is not None and rel_str not in restrict_to and filename not in CONFIG_PRIORITY:
                continue

            # Skip large files
            try:
                if filepath.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            # Check extension
            suffix = filepath.suffix.lower()
            if suffix not in SOURCE_EXTENSIONS and filename not in CONFIG_PRIORITY:
                continue

            # Skip binary files
            if is_binary(filepath):
                continue

            # Categorize
            if filename in CONFIG_PRIORITY:
                priority = CONFIG_PRIORITY.index(filename)
                config_files.append((filepath, priority))
            else:
                mtime = filepath.stat().st_mtime
                source_files.append((filepath, mtime))

    # Sort: configs by priority, sources by mtime (newest first)
    config_files.sort(key=lambda x: x[1])
    source_files.sort(key=lambda x: x[1], reverse=True)

    result = [(f, "config") for f, _ in config_files]
    result += [(f, "source") for f, _ in source_files]
    return result


def _find_importers(project_root: Path, seed_files: set[str]) -> set[str]:
    """Find files that import any of the seed files (direct importers only)."""
    # Extract module names from seed file paths
    seed_modules = set()
    for f in seed_files:
        p = Path(f)
        if p.suffix == ".py":
            seed_modules.add(p.stem)

    if not seed_modules:
        return set()

    importers = set()
    import_pattern = re.compile(r'(?:from\s+\.?(\w+)|import\s+(\w+))')

    for root_str, dirs, files in os.walk(project_root):
        root = Path(root_str)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            filepath = root / filename
            rel_str = str(filepath.relative_to(project_root))
            if rel_str in seed_files:
                continue  # Don't add seed files as their own importers
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue
            for match in import_pattern.finditer(content):
                imported = match.group(1) or match.group(2)
                if imported in seed_modules:
                    importers.add(rel_str)
                    break  # One match is enough

    return importers


def dump(project_root: Path, max_tokens: int, files_from: Path | None = None) -> str:
    """Build the structured markdown document."""
    project_name = project_root.name
    files = collect_files(project_root, files_from=files_from)

    # Compute fan-in for priority ordering when budget is tight
    fan_in = compute_fan_in(project_root, files)

    parts = []
    parts.append(f"# Codebase: {project_name}\n")
    parts.append(f"Files: {len(files)}\n")

    # File inventory (lightweight — helps the model navigate)
    parts.append("\n## File Inventory\n")
    for filepath, category in files:
        rel = filepath.relative_to(project_root)
        size = filepath.stat().st_size
        fi = fan_in.get(str(rel), 0)
        fan_in_str = f" [fan-in:{fi}]" if fi > 0 else ""
        parts.append(f"- `{rel}` ({size:,} bytes) [{category}]{fan_in_str}")
    parts.append("")

    # File contents
    total_tokens = estimate_tokens("\n".join(parts))
    files_included = 0
    files_skeletonized = 0

    for filepath, category in files:
        rel = filepath.relative_to(project_root)
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        file_tokens = estimate_tokens(content)

        # Check budget
        if total_tokens + file_tokens > max_tokens:
            # Use AST skeletonization for Python files (preserves API surface)
            if filepath.suffix == ".py":
                content = skeletonize_python(content)
                file_tokens = estimate_tokens(content)
                files_skeletonized += 1
            else:
                # Non-Python: truncate to first 100 lines
                lines = content.split("\n")
                if len(lines) > 100:
                    content = "\n".join(lines[:100]) + f"\n\n// [TRUNCATED: {len(lines)} lines total]"
                    file_tokens = estimate_tokens(content)

            if total_tokens + file_tokens > max_tokens:
                parts.append(f"\n## {rel}\n[SKIPPED: token budget exceeded]\n")
                continue

        section = f"\n## {rel}\n```{filepath.suffix.lstrip('.')}\n{content}\n```\n"
        parts.append(section)
        total_tokens += file_tokens
        files_included += 1

    # Summary at the end
    parts.append(f"\n---\n**Token estimate:** ~{total_tokens:,}")
    parts.append(f"**Files included:** {files_included} (of {len(files)})")
    if files_skeletonized:
        parts.append(f"**Files skeletonized:** {files_skeletonized} (signatures only, API surface preserved)")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Dump codebase for LLM analysis")
    parser.add_argument("project_root", type=Path, help="Path to project root")
    parser.add_argument("--output", "-o", type=Path, help="Output file (default: stdout)")
    parser.add_argument("--max-tokens", type=int, default=400_000, help="Token budget (default: 400K)")
    parser.add_argument("--files-from", type=Path, help="File listing changed files (diff-aware mode)")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"ERROR: {project_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = dump(project_root, args.max_tokens, files_from=args.files_from)

    if args.output:
        args.output.write_text(result)
        tokens = estimate_tokens(result)
        print(f"Wrote {args.output} (~{tokens:,} tokens)", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
