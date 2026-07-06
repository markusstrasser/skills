#!/usr/bin/env python3
"""Stop hook: pre-compact loose-ends wrap-up for ORDINARY sessions (always-on).

The goal-night controller (stop-goal-wrapup.py) covers marker-armed overnight
runs; every other session used to hit native auto-compact with ZERO wrap-up —
uncommitted work risks being hallucinated-as-done after the summary, and the
global CLAUDE.md "save progress before compaction" contract had no enforcing
hook (verified 2026-07-06: genomics be0657a9, 14 compactions, 0 wrap-ups).

Fires ONCE per fill cycle: blocks the Stop with a short commit/loose-ends/
checkpoint prompt when context crosses (window - MARGIN). Cycle detection is
self-contained — the state file records ctx at firing; a later ctx well below
it means a compaction landed, which re-arms. No PostCompact companion needed,
and manual /compact re-arms too.

Window source, in priority order:
1. CLAUDE_CODE_AUTO_COMPACT_WINDOW env (explicit lever; goal-night/goal-loop
   set it — it MOVES the native trigger, so it wins when present).
2. /tmp/claude-ctxpct-<session_id> — statusline.sh tees "pct|tokens|window"
   from the harness's own context_window payload (same canonical source
   posttool-context-checkpoint-advisory.sh reads). This is the ground truth
   for the model's real window: 1M sessions (claude-fable-5[1m]) misfired at
   ~17% when this hook assumed 200K (6 sessions, 2026-07-06).
3. 200K default (headless sessions with no statusline and no env).
The binary's EFFECTIVE trigger fires ~26K below the configured window
(observed pre=473,991 on window=500,000, arc-agi 182fba14) — MARGIN=45K
prompts the wrap-up a comfortable turn before that.

Skips: goal-run-owned sessions (the goal ritual is richer), repos with a
.claude/ctx-wrapup-off file (opt-out). State: ~/.claude/ctx-wrapup/<session>.
Fail-open everywhere (P10).
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_context_tokens import context_tokens  # noqa: E402

MARGIN = 45_000
DEFAULT_WINDOW = 200_000
REARM_RATIO = 0.6  # ctx fell below 60% of fired-ctx => compaction landed
STATE_TTL_S = 7 * 86_400

PROMPT = """CONTEXT NEAR AUTO-COMPACT ({ctx:,} tokens; trigger fires ≈{trigger:,}) — tie off loose ends NOW, while full context exists (this fires once per fill cycle):
1. COMMIT everything finished (granular, semantic). Post-compaction verification trusts git, not memory — uncommitted work risks being hallucinated-as-done after the summary.
2. Loose ends only this context can tie off: in-flight edits, promised follow-ups, doc/index updates for files this session touched.
3. Rewrite .claude/checkpoint.md as the re-entry brief: STATE (what's done, with commit SHAs/paths), NEXT (2-3 actions with exact commands), VERIFY (commands that re-derive claimed state — never bare numbers across the boundary).
Then end your turn normally; native auto-compact proceeds on a subsequent turn."""


def resolve_window(sid: str) -> int:
    """Env lever > statusline-teed harness window > 200K default."""
    try:
        window = int(os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW", ""))
        if window > 0:
            return window
    except Exception:
        pass
    try:
        parts = Path(f"/tmp/claude-ctxpct-{sid}").read_text().split("|")
        window = int(parts[2])
        if window > 0:
            return window
    except Exception:
        pass
    return DEFAULT_WINDOW


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    sid = payload.get("session_id") or ""
    if not sid:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    claude_dir = cwd / ".claude"
    if (claude_dir / "ctx-wrapup-off").exists():
        return 0
    # Goal-controlled session? The goal-night ritual supersedes this nudge.
    marker = claude_dir / "goal-run"
    if marker.is_file():
        try:
            words = marker.read_text().split()
        except Exception:
            words = []
        owner = words[1] if len(words) > 1 else ""
        # Ownerless (legacy manual arming) controls every session in the repo.
        if not owner or owner == sid:
            return 0

    ctx = context_tokens(payload.get("transcript_path", ""))
    if ctx <= 0:
        return 0
    window = resolve_window(sid)
    threshold = max(80_000 - MARGIN, window - MARGIN)

    state_dir = Path.home() / ".claude" / "ctx-wrapup"
    state = state_dir / sid
    if state.exists():
        fired_ctx = 0
        try:
            fired_ctx = int(state.read_text().strip() or "0")
        except Exception:
            pass
        if fired_ctx and ctx < fired_ctx * REARM_RATIO:
            try:
                state.unlink()  # compaction landed since firing — new fill cycle
            except Exception:
                return 0
        else:
            return 0
    if ctx < threshold:
        return 0
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        now = time.time()
        for old in state_dir.iterdir():
            try:
                if now - old.stat().st_mtime > STATE_TTL_S:
                    old.unlink()
            except Exception:
                pass
        state.write_text(str(ctx))
    except Exception:
        return 0  # can't record once-per-cycle state -> stay silent, never loop
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": PROMPT.format(ctx=ctx, trigger=max(0, window - 26_000)),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
