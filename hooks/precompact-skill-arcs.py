#!/usr/bin/env python3
"""PreCompact hook: preserve active skill arcs across compaction.

# Gov-ID: hook:precompact-skill-arcs
# goal: compaction summarizes away loaded SKILL.md instructions mid-arc (measured
#       40-85% of skill-invoking sessions compact after the invocation; audit
#       agent-infra research/2026-07-06-skill-usage-value-audit.md §5) — the
#       summary must carry which arcs are live + how to reload them.
# verifier: null
# blast_radius: shared

Emits summarizer customInstructions (binary-verified: PreCompact stdout ->
newCustomInstructions) listing skills invoked in THIS session, read from
~/.claude/skill-triggers.jsonl (written by posttool-skill-log.sh).

Scope guards:
- Defers entirely (exit 0, no output) when .claude/goal-run exists — the
  goal-run guard (precompact-goal-guard.py) owns compaction instructions there;
  two hooks emitting competing customInstructions is undefined behavior.
- Fail open on any error; no output means default summarizer behavior.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRIGGER_LOG = Path.home() / ".claude" / "skill-triggers.jsonl"
TAIL_BYTES = 512_000  # generous tail; the log is append-only JSONL
MAX_SKILLS = 3
MAX_AGE_H = 12  # ignore stale same-session invocations (resumed old sessions)


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
    cwd = Path(payload.get("cwd") or ".")
    if (cwd / ".claude" / "goal-run").is_file():
        return 0  # goal-run guard owns compaction instructions
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
    sys.exit(main())
