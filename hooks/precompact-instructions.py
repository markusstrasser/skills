#!/usr/bin/env python3
"""PreCompact hook: the summarizer contract for every session, plus active skill arcs.

# Gov-ID: hook:precompact-instructions
# goal: (1) LLM summaries paraphrase sources and the agent then stops re-reading
#       them (CliffCompaction 2609.26779 App. C.1); each summary also re-paraphrases
#       the previous one (measured 2026-10-15: 4-32% 12-gram carry-over between
#       consecutive summaries across 6 sessions, one with 50 compactions) — so the
#       summary must name what to re-read and carry prior open items forward intact.
#       (2) compaction drops loaded SKILL.md instructions mid-arc (40-85% of
#       skill-invoking sessions compact after the invocation; agent-infra
#       research/2026-07-06-skill-usage-value-audit.md §5).
# verifier: null
# blast_radius: shared

Emits summarizer customInstructions (binary-verified: PreCompact stdout ->
newCustomInstructions). Several PreCompact hooks' outputs are joined with
newlines (CC 2.1.300 binary: `newCustomInstructions: M.join("\\n")`), so this
hook runs in goal runs too; precompact-goal-guard.py adds only the goal-specific
lines. Idle compaction (CC 2.1.299) reaches hooks as trigger "auto".

Fail open on any error; no output means default summarizer behavior.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checkpoint_resume import (  # noqa: E402
    auto_checkpoint_name,
    handwritten_checkpoint_name,
    project_root,
)

TRIGGER_LOG = Path.home() / ".claude" / "skill-triggers.jsonl"
TAIL_BYTES = 512_000  # generous tail; the log is append-only JSONL
MAX_SKILLS = 3
MAX_AGE_H = 12  # ignore stale same-session invocations (resumed old sessions)

SUMMARY_CONTRACT = (
    "Open the summary with one line saying it is a lossy compaction summary and "
    "that the files it lists are the source of truth. Then include a section "
    "'Re-read before relying on details' that lists, by exact path or URL, every "
    "file, document and source whose contents the next steps depend on{checkpoints}; "
    "name them instead of paraphrasing their contents, and "
    "do not reproduce long tool output. Keep exactly: the user's requests and "
    "corrections close to verbatim; decisions and what was ruled out, with the "
    "reason; problems hit and how they were resolved; names, numbers, dates, "
    "paths and commit SHAs. Condense your own reasoning to its conclusions. State "
    "where work stands: what finished and was verified, what was started but not "
    "verified (say so explicitly), what is still open or promised, and the next "
    "action. If the conversation opens with an earlier compaction summary, carry "
    "its still-valid open items, decisions and re-read list forward word for word "
    "and drop what is finished; do not re-paraphrase it."
)


def checkpoint_clause(payload: dict) -> str:
    """', plus <this session's checkpoint paths>' for the re-read list, or '' without a
    usable session id (the PreCompact writer then writes no checkpoint)."""
    session = str(payload.get("session_id") or "")
    auto = auto_checkpoint_name(session)
    if not auto:
        return ""
    cwd = str(payload.get("cwd") or "")
    claude_dir = os.path.join(project_root(cwd), ".claude") if cwd else ".claude"
    clause = ", plus this session's resume checkpoint " + os.path.join(claude_dir, auto)
    brief = os.path.join(claude_dir, handwritten_checkpoint_name(session))
    if os.path.isfile(brief):
        clause += " and its hand-written brief " + brief
    return clause


def active_skills(session_id: str) -> list[dict]:
    if not session_id or not TRIGGER_LOG.is_file():
        return []
    try:
        with TRIGGER_LOG.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            lines = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_H)
    latest: dict[str, dict] = {}
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue  # corrupt log fragments can parse as bare scalars ("1." -> 1.0)
        if row.get("event") != "skill_invoke" or row.get("session") != session_id:
            continue
        try:
            ts = datetime.fromisoformat(row.get("ts", "").replace("Z", "+00:00"))
            if ts < cutoff:
                continue
        except ValueError:
            pass
        latest[row.get("skill", "")] = row  # dedup, keep newest per skill
    latest.pop("", None)
    rows = sorted(latest.values(), key=lambda r: r.get("ts", ""))
    return rows[-MAX_SKILLS:]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    print(SUMMARY_CONTRACT.format(checkpoints=checkpoint_clause(payload)))
    rows = active_skills(str(payload.get("session_id") or ""))
    if not rows:
        return 0
    arcs = ", ".join(
        f"/{r['skill']}" + (f" (args: {r['args']})" if r.get("args") else "")
        for r in rows
    )
    print(
        f"Active skill arcs this session: {arcs}. For each, the summary MUST state "
        f"which step of the skill's workflow was reached and what remains. The "
        f"skill's instructions are NOT carried across compaction — before "
        f"continuing an unfinished arc, re-invoke Skill(<name>) (or Read "
        f"~/.claude/skills/<name>/SKILL.md)."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open per contract — never break compaction
