#!/usr/bin/env bash
# posttool-research-reformat.sh — PostToolUse hook for research MCP output cleanup.
# Uses updatedMCPToolOutput to reformat noisy read_paper/fetch_paper output
# before Claude sees it. Logs original content hash for audit trail.
#
# Deploy: PostToolUse matcher "mcp__research__read_paper|mcp__research__fetch_paper"
# Fails open (exit 0 on any error).

trap 'exit 0' ERR

INPUT=$(cat)

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"

# Process with Python — heavy lifting for text restructuring
echo "$INPUT" | python3 -c '
import sys, json, hashlib, os, time

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = data.get("tool_name", "")
tool_result = data.get("tool_result", "")

if not tool_result or not isinstance(tool_result, str):
    sys.exit(0)

# Log original content hash for epistemic audit trail
content_hash = hashlib.sha256(tool_result.encode()).hexdigest()[:16]
original_len = len(tool_result)

# Only reformat if content is substantial (>2000 chars of raw text)
if original_len < 2000:
    sys.exit(0)

def restructure_paper_text(text: str) -> str:
    """Restructure raw PDF extraction into cleaner sections."""
    lines = text.split("\n")
    sections: list[tuple[str, list[str]]] = []
    current_section = "Header"
    current_lines: list[str] = []

    # Common section headings in academic papers
    section_patterns = [
        "abstract", "introduction", "background", "related work",
        "methods", "methodology", "materials and methods", "experimental",
        "results", "findings", "discussion", "conclusion", "conclusions",
        "references", "bibliography", "acknowledgments", "acknowledgements",
        "supplementary", "appendix", "funding", "data availability",
    ]

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower().rstrip(".")

        # Detect section headers: short lines that match known patterns
        is_header = False
        if 2 < len(stripped) < 80:
            # Check against known patterns
            for pattern in section_patterns:
                if lower == pattern or lower.startswith(pattern + " ") or lower.endswith(pattern):
                    is_header = True
                    break
            # Also detect numbered sections: "1. Introduction", "2.1 Methods"
            if not is_header and len(stripped) < 60:
                import re
                if re.match(r"^\d+\.?\d*\.?\s+[A-Z]", stripped):
                    is_header = True

        if is_header:
            if current_lines:
                sections.append((current_section, current_lines))
            current_section = stripped
            current_lines = []
        else:
            if stripped:  # Skip blank lines
                current_lines.append(stripped)

    if current_lines:
        sections.append((current_section, current_lines))

    # Build reformatted output
    parts = [f"[Reformatted from raw PDF extraction | original: {original_len} chars | hash: {content_hash}]\n"]

    for section_name, section_lines in sections:
        if section_name == "References" or section_name.lower().startswith("reference"):
            # Truncate references — they waste context
            ref_count = len(section_lines)
            parts.append(f"\n## References\n[{ref_count} references — truncated to save context]\n")
            continue

        parts.append(f"\n## {section_name}\n")
        # Join lines into paragraphs (consecutive non-empty lines)
        text_block = " ".join(section_lines)
        # Wrap at ~1000 chars per block for readability
        if len(text_block) > 1500:
            # Keep first 1200 chars + last 300 chars for very long sections
            parts.append(text_block[:1200] + "\n[...]\n" + text_block[-300:] + "\n")
        else:
            parts.append(text_block + "\n")

    return "\n".join(parts)

reformatted = restructure_paper_text(tool_result)

# Log to hook telemetry
try:
    import subprocess
    subprocess.run(
        [os.path.expanduser("~/Projects/skills/hooks/hook-trigger-log.sh"),
         "research-reformat", "rewrite",
         f"{tool_name} {original_len}→{len(reformatted)} hash:{content_hash}"],
        capture_output=True, timeout=5
    )
except Exception:
    pass

# Output the rewrite
output = {"updatedMCPToolOutput": reformatted}
print(json.dumps(output))
' 2>/dev/null
