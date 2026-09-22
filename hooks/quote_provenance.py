"""Quote provenance for subagent briefs and peer messages (advisory).

The Opus 5.5 system card (§6.3.1) records the model relaying a fabricated
user-authorization quote to a subagent. This check finds text that an Agent
prompt or SendMessage body attributes to the user in quotation marks and looks
for it in what the user actually wrote this session. Unmatched quotes produce
an advisory note; nothing is blocked.

User-authored text comes from agent-infra's single definition
(scripts/common/transcript_text.py), loaded by path; compaction summaries also
count, since they carry the user's pre-compaction messages. A quote whose line
cites a source (file, session id, date, memory) is taken as sourced elsewhere.
"""

# Gov-ID: hook:quote-provenance
# goal: stop fabricated user quotes/authorizations from reaching subagents unflagged
# verifier: null (unit tests: hooks/test_quote_provenance.py)
# blast_radius: shared

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

# Sibling checkout (~/Projects/skills/hooks → ~/Projects/agent-infra), not $HOME: hermetic tests swap HOME.
TRANSCRIPT_TEXT = Path(__file__).resolve().parents[2] / "agent-infra/scripts/common/transcript_text.py"

_WHO = r"(?:the\s+)?(?:user|operator|markus|human|principal)"
_VERB = (
    r"(?:said|says|wrote|writes|asked|asks|told\s+(?:me|us|you)|approved|"
    r"authori[sz]ed|confirmed|instructed|requested|replied|answered|stated|"
    r"explicitly\s+said)"
)
_OPEN, _CLOSE = "\"“", "\"”"
_BODY = rf"[{_OPEN}]([^{_CLOSE}\n]{{8,400}})[{_CLOSE}]"
_ATTRIBUTED = [
    re.compile(rf"\b{_WHO}(?:'s)?\s+{_VERB}\s*[,:]?\s*(?:to\s+)?{_BODY}", re.I),
    re.compile(rf"\b(?:per|from)\s+{_WHO}\s*[,:]?\s*{_BODY}", re.I),
    re.compile(rf"{_BODY}\s*[,—–-]?\s*{_VERB}\s+{_WHO}\b", re.I),
]
_SOURCED = re.compile(
    r"\.(?:md|jsonl|py|json|txt)\b|\bsession\s+[0-9a-f]{6,}|\b20\d\d-\d\d-\d\d\b|"
    r"\bmemory\b|CLAUDE\.md|\brules/|#[fg]\b|\btranscript\b",
    re.I,
)
_FRAGMENT_SPLIT = re.compile(r"\.\.\.|…|\[[^\]]*\]")
_MIN_FRAGMENT = 6


def _normalize(text: str) -> str:
    text = text.lower().translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'}))
    return re.sub(r"\s+", " ", text).strip(" .,;:!?\"'")


def attributed_quotes(text: str) -> list[tuple[str, str]]:
    """(quote, containing line) pairs for quotes attributed to the user."""
    found = []
    for line in text.splitlines():
        for pattern in _ATTRIBUTED:
            for m in pattern.finditer(line):
                found.append((m.group(1), line))
    return found


def _load_transcript_text():
    spec = importlib.util.spec_from_file_location("transcript_text", TRANSCRIPT_TEXT)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def user_corpus(transcript_path: str) -> str | None:
    """Normalized user-authored text of a session, or None when unreadable."""
    tt = _load_transcript_text()
    path = Path(transcript_path) if transcript_path else None
    if tt is None or path is None or not path.is_file():
        return None
    parts = []
    with path.open(errors="replace") as fh:
        for line in fh:
            if '"user"' not in line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("isCompactSummary"):
                obj = {**obj, "isCompactSummary": False}
            parts.extend(tt.user_texts(obj))
    return _normalize(" ".join(parts))


def unmatched_quotes(text: str, corpus: str) -> list[str]:
    missing = []
    for quote, line in attributed_quotes(text):
        if _SOURCED.search(line):
            continue
        fragments = [_normalize(f) for f in _FRAGMENT_SPLIT.split(quote)]
        fragments = [f for f in fragments if len(f) >= _MIN_FRAGMENT]
        if fragments and not all(f in corpus for f in fragments):
            missing.append(quote)
    return missing


def check_dispatch(tool_input: dict, transcript_path: str) -> str:
    """Advisory note for an Agent/SendMessage call, or "" when clean."""
    text = "\n".join(
        v for k, v in (tool_input or {}).items() if k in ("prompt", "message", "description") and isinstance(v, str)
    )
    if not text or not attributed_quotes(text):
        return ""
    corpus = user_corpus(transcript_path)
    if corpus is None:
        return ""
    missing = unmatched_quotes(text, corpus)
    if not missing:
        return ""
    shown = "; ".join(f"“{q[:120]}”" for q in missing[:3])
    return (
        f"quote-provenance: this message attributes to the user {len(missing)} quote(s) that no user "
        f"message in this session contains: {shown}. Quote the user verbatim, cite where the words come "
        "from, or drop the quotation marks and mark it as your summary. A subagent treats a quoted user "
        "instruction as authorization (Opus 5.5 system card §6.3.1)."
    )
