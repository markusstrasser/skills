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

Window resolution (the value auto-compact actually triggers against), in
priority order — every source capped by the model window when known:
1. CLAUDE_CODE_AUTO_COMPACT_WINDOW env (explicit lever; goal-night/goal-loop
   set it — it MOVES the native trigger, so it wins when present).
2. autoCompactWindow settings key (project settings.local > project > global)
   — the same binary lever in settings form.
3. The binary's own default, derived from the model window teed by
   statusline.sh to /tmp/claude-ctxpct-<sid> ("pct|tokens|window", the same
   source posttool-context-checkpoint-advisory.sh reads): on a 1M window the
   UNCONFIGURED binary auto-compacts at ~475K — i.e. an effective 500K
   window (measured: 12 native compactions at 462-530K, genomics be0657a9,
   CC 2.1.201, fable-5[1m], no env/settings lever set). So: min(window,
   500K). Re-verify that constant on CC major bumps; the statusline payload
   carries no trigger field (raw-payload dump checked 2026-07-06).
4. 200K default (headless sessions with no statusline and no lever).
Getting this wrong is symmetric pain: assuming 200K on a 1M session nudged
at ~17% fill (6 sessions, 2026-07-06); assuming the full 1M would place the
threshold at 955K and the nudge would NEVER beat the ~475K native compact
(the 14-compactions-0-wrap-ups failure this hook exists to close).
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


UNCONFIGURED_1M_EFFECTIVE = 500_000  # measured binary default, CC 2.1.201


def _settings_auto_compact_window(cwd: Path) -> int:
    for settings in (
        cwd / ".claude" / "settings.local.json",
        cwd / ".claude" / "settings.json",
        Path.home() / ".claude" / "settings.json",
    ):
        try:
            value = int(json.loads(settings.read_text())["autoCompactWindow"])
            if value > 0:
                return value
        except Exception:
            continue
    return 0


def resolve_window(sid: str, cwd: Path) -> int:
    """The value the binary's auto-compact actually triggers against:
    env lever > settings lever > binary default for the model window > 200K.
    Levers are capped by the model window when the statusline teed it."""
    model_window = 0
    try:
        model_window = int(Path(f"/tmp/claude-ctxpct-{sid}").read_text().split("|")[2])
    except Exception:
        pass

    lever = 0
    try:
        lever = int(os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW", ""))
    except Exception:
        pass
    if lever <= 0:
        lever = _settings_auto_compact_window(cwd)
    if lever > 0:
        return min(lever, model_window) if model_window > 0 else lever

    if model_window > 0:
        return min(model_window, UNCONFIGURED_1M_EFFECTIVE)
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
    window = resolve_window(sid, cwd)
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
