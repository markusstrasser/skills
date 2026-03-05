#!/usr/bin/env python3
"""Rewrite noisy research MCP outputs before they hit the planner context."""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PAPER_TOOLS = {
    "mcp__research__read_paper",
    "mcp__research__fetch_paper",
}

SEARCH_TOOL_PREFIXES = (
    "mcp__exa__web_search_exa",
    "mcp__exa__web_search_advanced_exa",
    "mcp__exa__crawling_exa",
    "mcp__brave-search__brave_web_search",
    "mcp__brave-search__brave_news_search",
    "mcp__paper-search__search_",
    "mcp__research__search_papers",
)

PASS_THROUGH_TOOLS = {
    "mcp__firecrawl__firecrawl_scrape",
    "mcp__firecrawl__firecrawl_extract",
}

ARCHIVE_ROOT = Path.home() / ".claude" / "tool-output-archive"
ARCHIVE_INDEX = ARCHIVE_ROOT / "index.jsonl"


def shorten_home(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    return text.replace(home, "~", 1) if text.startswith(home) else text


def log_hook(tool_name: str, message: str) -> None:
    try:
        subprocess.run(
            [
                os.path.expanduser("~/Projects/skills/hooks/hook-trigger-log.sh"),
                "research-reformat",
                "rewrite",
                f"{tool_name} {message}",
            ],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def archive_raw_output(tool_name: str, raw_text: str, content_hash: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", tool_name or "unknown")
    tool_dir = ARCHIVE_ROOT / slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    archive_path = tool_dir / f"{content_hash}.txt"
    if not archive_path.exists():
        archive_path.write_text(raw_text)
    with open(ARCHIVE_INDEX, "a") as f:
        f.write(
            json.dumps(
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "tool_name": tool_name,
                    "hash": content_hash,
                    "chars": len(raw_text),
                    "path": str(archive_path),
                }
            )
            + "\n"
        )
    return shorten_home(archive_path)


def clean_snippet(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def restructure_paper_text(text: str, *, original_len: int, content_hash: str, archive_path: str) -> str:
    lines = text.split("\n")
    sections = []
    current_section = "Header"
    current_lines: list[str] = []

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

        is_header = False
        if 2 < len(stripped) < 80:
            for pattern in section_patterns:
                if lower == pattern or lower.startswith(pattern + " ") or lower.endswith(pattern):
                    is_header = True
                    break
            if not is_header and len(stripped) < 60 and re.match(r"^\d+\.?\d*\.?\s+[A-Z]", stripped):
                is_header = True

        if is_header:
            if current_lines:
                sections.append((current_section, current_lines))
            current_section = stripped
            current_lines = []
        elif stripped:
            current_lines.append(stripped)

    if current_lines:
        sections.append((current_section, current_lines))

    parts = [
        f"[Reformatted paper output | original: {original_len} chars | hash: {content_hash} | archive: {archive_path}]",
        "",
    ]

    for section_name, section_lines in sections:
        lower_name = section_name.lower()
        if lower_name == "references" or lower_name.startswith("reference"):
            ref_count = len(section_lines)
            parts.append("## References")
            parts.append(f"[{ref_count} references — truncated to save context]")
            parts.append("")
            continue

        parts.append(f"## {section_name}")
        text_block = " ".join(section_lines)
        if len(text_block) > 4000:
            parts.append(text_block[:3200] + "\n[...]\n" + text_block[-800:])
        else:
            parts.append(text_block)
        parts.append("")

    return "\n".join(parts).strip()


def extract_plaintext_results(text: str) -> list[dict]:
    blocks = [block.strip() for block in re.split(r"(?=^Title:\s)", text, flags=re.M) if block.strip()]
    results = []
    for block in blocks:
        title = re.search(r"^Title:\s*(.+)$", block, re.M)
        url = re.search(r"^URL:\s*(.+)$", block, re.M)
        date = re.search(r"^Published Date:\s*(.+)$", block, re.M)
        author = re.search(r"^Author:\s*(.+)$", block, re.M)
        description = re.search(r"^Description:\s*(.+)$", block, re.M)
        text_match = re.search(r"^Text:\s*(.+)$", block, re.M | re.S)
        if not title:
            continue
        snippet = ""
        if description:
            snippet = description.group(1).strip()
        elif text_match:
            snippet = text_match.group(1).strip()
        results.append(
            {
                "title": title.group(1).strip(),
                "url": url.group(1).strip() if url else "",
                "date": date.group(1).strip() if date else "",
                "author": author.group(1).strip() if author else "",
                "snippet": clean_snippet(snippet),
            }
        )
    return results


def collect_json_results(obj, results: list[dict]) -> None:
    if isinstance(obj, list):
        for item in obj:
            collect_json_results(item, results)
        return

    if not isinstance(obj, dict):
        return

    title = obj.get("title") or obj.get("name")
    url = obj.get("url") or obj.get("link")
    snippet = (
        obj.get("description")
        or obj.get("snippet")
        or obj.get("summary")
        or obj.get("text")
        or obj.get("content")
        or obj.get("abstract")
    )
    date = obj.get("published_date") or obj.get("date") or obj.get("Published Date")
    author = obj.get("author") or obj.get("authors")

    if title and (url or snippet):
        results.append(
            {
                "title": str(title).strip(),
                "url": str(url).strip() if url else "",
                "date": str(date).strip() if date else "",
                "author": str(author).strip() if author else "",
                "snippet": clean_snippet(str(snippet)) if snippet else "",
            }
        )

    for value in obj.values():
        collect_json_results(value, results)


def dedupe_results(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for result in results:
        key = (result.get("title", ""), result.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def looks_like_search_result(item) -> bool:
    if not isinstance(item, dict):
        return False
    return bool(
        item.get("title")
        or item.get("name")
        or item.get("url")
        or item.get("link")
    )


def looks_like_search_payload(parsed) -> bool:
    if isinstance(parsed, list):
        return any(looks_like_search_result(item) for item in parsed[:10])

    if not isinstance(parsed, dict):
        return False

    if looks_like_search_result(parsed):
        return True

    for key in ("results", "web", "news", "items", "organic_results", "data"):
        value = parsed.get(key)
        if isinstance(value, list) and any(looks_like_search_result(item) for item in value[:10]):
            return True
        if isinstance(value, dict) and looks_like_search_payload(value):
            return True

    return False


def restructure_search_output(text: str, *, tool_name: str, original_len: int, content_hash: str, archive_path: str) -> str | None:
    results = []
    stripped = text.strip()
    parsed = None

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if parsed is not None and looks_like_search_payload(parsed):
            collect_json_results(parsed, results)
        elif parsed is not None:
            return None

    if not results and "Title:" in text:
        results = extract_plaintext_results(text)

    results = dedupe_results(results)
    if not results:
        if original_len < 1200:
            return None
        fallback = clean_snippet(text, limit=1400)
        return "\n".join(
            [
                f"[Quarantined MCP output | tool: {tool_name} | original: {original_len} chars | hash: {content_hash} | archive: {archive_path}]",
                "",
                fallback,
            ]
        )

    parts = [
        f"[Quarantined MCP output | tool: {tool_name} | original: {original_len} chars | hash: {content_hash} | archive: {archive_path}]",
        "",
        f"Showing {min(len(results), 6)} normalized result(s). Fetch chosen URLs directly if full text is needed.",
        "",
    ]

    for idx, result in enumerate(results[:6], start=1):
        parts.append(f"{idx}. {result['title']}")
        if result.get("url"):
            parts.append(f"   URL: {result['url']}")
        if result.get("date"):
            parts.append(f"   Date: {result['date']}")
        if result.get("author"):
            parts.append(f"   Author: {result['author']}")
        if result.get("snippet"):
            parts.append(f"   Snippet: {result['snippet']}")
        parts.append("")

    if len(results) > 6:
        parts.append(f"[{len(results) - 6} additional result(s) truncated]")

    return "\n".join(parts).strip()


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    tool_name = data.get("tool_name", "")
    tool_result = data.get("tool_result", "")
    if isinstance(tool_result, str):
        raw_text = tool_result
    elif isinstance(tool_result, (dict, list)):
        raw_text = json.dumps(tool_result, ensure_ascii=False)
    else:
        return

    if not raw_text:
        return

    original_len = len(raw_text)
    content_hash = hashlib.sha256(raw_text.encode()).hexdigest()[:16]
    archive_path = archive_raw_output(tool_name, raw_text, content_hash)

    reformatted = None
    if tool_name in PAPER_TOOLS:
        if original_len < 4000:
            return
        reformatted = restructure_paper_text(
            raw_text,
            original_len=original_len,
            content_hash=content_hash,
            archive_path=archive_path,
        )
    elif tool_name in PASS_THROUGH_TOOLS:
        return
    elif any(tool_name.startswith(prefix) for prefix in SEARCH_TOOL_PREFIXES):
        reformatted = restructure_search_output(
            raw_text,
            tool_name=tool_name,
            original_len=original_len,
            content_hash=content_hash,
            archive_path=archive_path,
        )

    if not reformatted or reformatted == raw_text:
        return

    log_hook(tool_name, f"{original_len}→{len(reformatted)} hash:{content_hash}")
    print(json.dumps({"updatedMCPToolOutput": reformatted}))


if __name__ == "__main__":
    main()
