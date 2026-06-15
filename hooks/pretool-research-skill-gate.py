#!/usr/bin/env python3
"""PreToolUse gate: /research for science/long-form work requires Skill(research) first.

Fires on search tools (matcher in settings). When a recent user message contains a
/research slash command scoped to literature/science/deep research — not casual
product lookups — block search until Skill(research) has fired this session.

Modes (RESEARCH_SKILL_GATE env):
  block (default) — exit 2 with fix instruction
  advisory        — stderr nudge, exit 0
  shadow          — JSONL log only, exit 0

Fails open on parse/transcript errors. Measure: hook-trigger-log + shadow JSONL.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Gov-ID: hook:research-skill-gate

RESEARCH_CMD = re.compile(r"(?:^|[\s?.,!])(/research)\b(?!-)", re.I | re.M)
RESEARCH_OPS = re.compile(r"/research-ops\b", re.I)

NOISE = (
    "Base directory for this skill",
    "continued from a previous conversation",
    "<local-command-stdout>",
    "You review an AI coding agent",
)

DEPTH = re.compile(
    r"\b("
    r"papers?|literature|lit review|arxiv|preprints?|biorxiv|pubmed|semantic scholar|"
    r"systematic|meta[- ]analysis|benchmarks?|what(?:'s| is) known|ground truth|"
    r"memo|memos|evidence base|state of the art|sota|"
    r"genomic?s?|genes?|variants?|clinvar|gnomad|ensembl|drug targets?|"
    r"disease|pathway|mechanism|hypotheses|hypothesis|clinical trials?|"
    r"biomedical|pharmacogen|proteomics?|transcriptomics?|"
    r"agents? and rsi|recursive self|harness[- ]1|"
    r"find papers|research (?:into|on|about)|deep research"
    r")\b",
    re.I,
)

CASUAL = re.compile(
    r"\b("
    r"loom|video alternative|screen\s*\+\s*camera|better .{0,30} alternative|"
    r"saas|pricing|subscription tool|dating app|screen recorder"
    r")\b",
    re.I,
)

EXPLICIT_CMD = re.compile(
    r"(?:"
    r"\b(?:do|run|more|some|any|then)\s+/research\b|"
    r"/research\s+(?:this|on|into|about|and)\b|"
    r"\?/research\b|"
    r"^/research\b"
    r")",
    re.I | re.M,
)

SCIENCE_PROJECT = re.compile(
    r"(?:^|/)(?:genomics|phenome|intel|emb|evals|hutter)(?:/|$)",
    re.I,
)

SEARCH_TOOLS = {
    "WebSearch",
    "WebFetch",
    "mcp__exa__web_search_exa",
    "mcp__exa__web_search_advanced_exa",
    "mcp__exa__company_research_exa",
    "mcp__research__search_papers",
    "mcp__research__search_preprints",
    "mcp__paper-search__search_arxiv",
    "mcp__paper-search__search_pubmed",
    "mcp__paper-search__search_biorxiv",
    "mcp__paper-search__search_medrxiv",
    "mcp__paper-search__search_google_scholar",
    "mcp__brave-search__brave_web_search",
    "mcp__brave-search__brave_news_search",
    "mcp__perplexity__perplexity_search",
    "mcp__perplexity__perplexity_research",
}

SHADOW_LOG = Path.home() / ".claude" / "surface-gates" / "research-skill-gate-shadow.jsonl"
SKIP_MARKER = "<!-- research-skill:skip -->"


def _mode() -> str:
    return (os.environ.get("RESEARCH_SKILL_GATE") or "block").strip().lower()


def _is_noise(text: str) -> bool:
    return any(n in text for n in NOISE)


def _scoped_research_intent(text: str, *, cwd: str) -> bool:
    if not text or _is_noise(text) or RESEARCH_OPS.search(text):
        return False
    if not RESEARCH_CMD.search(text):
        return False
    if SKIP_MARKER in text:
        return False
    if CASUAL.search(text) and not DEPTH.search(text):
        return False
    if DEPTH.search(text) or EXPLICIT_CMD.search(text):
        return True
    if SCIENCE_PROJECT.search(cwd.replace("\\", "/")):
        # Science repos: /research without casual product signals counts.
        return not CASUAL.search(text)
    return False


def _user_texts(transcript_path: str, *, limit: int = 12) -> list[str]:
    path = Path(transcript_path).expanduser()
    if not path.is_file():
        return []
    texts: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("type") != "user":
            continue
        msg = row.get("message")
        if isinstance(msg, str):
            texts.append(msg)
        elif isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                joined = "\n".join(p for p in parts if p)
                if joined:
                    texts.append(joined)
        if len(texts) >= limit:
            break
    return list(reversed(texts))


def _research_skill_invoked(transcript_path: str) -> bool:
    path = Path(transcript_path).expanduser()
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("type") != "assistant":
            continue
        msg = row.get("message")
        if not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != "Skill":
                continue
            inp = block.get("input") or {}
            if inp.get("skill") == "research":
                return True
    return False


def _session_wants_research(user_texts: list[str], cwd: str) -> bool:
    return any(_scoped_research_intent(t, cwd=cwd) for t in user_texts)


def _log_shadow(payload: dict) -> None:
    try:
        SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SHADOW_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _trigger_log(action: str, detail: str) -> None:
    log_sh = Path.home() / "Projects/skills/hooks/hook-trigger-log.sh"
    if not log_sh.is_file():
        return
    import subprocess

    try:
        subprocess.run(
            [str(log_sh), "research-skill-gate", action, detail],
            check=False,
            capture_output=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool = data.get("tool_name") or ""
    if tool not in SEARCH_TOOLS:
        return 0

    transcript = data.get("transcript_path") or ""
    cwd = data.get("cwd") or os.getcwd()
    user_texts = _user_texts(transcript)
    if not user_texts or not _session_wants_research(user_texts, cwd):
        return 0

    if _research_skill_invoked(transcript):
        return 0

    mode = _mode()
    detail = f"tool={tool} cwd={cwd}"
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "tool": tool,
        "cwd": cwd,
        "session_id": data.get("session_id"),
        "would_block": True,
        "user_snippet": user_texts[-1][:200] if user_texts else "",
    }
    _log_shadow(payload)

    msg = (
        "/research scoped to science/literature/deep work detected, but Skill(research) "
        "has not run this session. Invoke Skill(research) first (routes S2/Exa/axis "
        "diversity, phase separation). Then retry this search. "
        "Opt out: add <!-- research-skill:skip --> to your message."
    )

    if mode == "shadow":
        _trigger_log("shadow", detail)
        return 0
    if mode == "advisory":
        print(msg, file=sys.stderr)
        _trigger_log("advisory", detail)
        return 0

    _trigger_log("block", detail)
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
