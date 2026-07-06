#!/usr/bin/env python3
"""Stop hook: overnight /goal run controller (wrap-up ritual + goal continuation).

Opt-in per run via `just goal-night` (or manually: `.claude/goal-run` file whose
content = ritual threshold in tokens; launch with CLAUDE_CODE_AUTO_COMPACT_WINDOW
~10% above it). Stop = the "agent finished a meaningful unit of work" event, so
one hook drives the whole night:

  Stop fires
    ├─ context >= ritual threshold and ritual not yet prompted
    │    → block ONCE with the wrap-up ritual (do it with full context;
    │      native auto-compact fires next turn; precompact-goal-guard.py
    │      enforces ordering + injects summarizer instructions)
    ├─ goal not done, not human-blocked, continuation budget left
    │    → block with the continuation prompt (goal keeps going after compaction)
    └─ .claude/goal-done / .claude/goal-blocked / budget exhausted → allow stop

Escapes the agent controls: touch .claude/goal-done (goal complete + verified),
touch .claude/goal-blocked (write HUMAN.md first). Operator disarm: rm .claude/goal-run.

Optional goal<->deliverable binding: write a progress-check command to .claude/goal-deliverable
(e.g. `ls results/syn3sr/stage-*.done | wc -l | sed 's:$:/258:'`). When armed, a continuing goal
whose deliverable is still at ZERO progress gets a loud one-time UNSTARTED warning — the class the
agent conflated with "condition not yet met" (2026-06-27 syn3sr). No marker -> no firing.
Continuation budget (MAX_CONTINUES) bounds a pathological spin; PostCompact re-arms
the ritual for the next fill cycle. Fail-open everywhere (P10).

Context measurement: lib_context_tokens (shared with stop-context-wrapup.py —
the two Stop hooks must agree on what "current context" means).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_context_tokens import context_tokens  # noqa: E402

MAX_CONTINUES = 100


def _deliverable_progress(cwd: Path, claude_dir: Path):
    """Opt-in goal<->deliverable binding: .claude/goal-deliverable holds a shell command that
    prints the goal's checkable progress ("done/total" or a bare integer). Returns (raw, done,
    total|None) or None when unbound / unparseable. done==0 is the UNSTARTED signal (the goal's
    deliverable has zero progress — the class the agent conflated with "condition not yet met",
    2026-06-27 genomics syn3sr). Narrow trigger: fires nothing unless the operator armed the marker.
    """
    marker = claude_dir / "goal-deliverable"
    if not marker.is_file():
        return None
    try:
        cmd = marker.read_text().strip()
    except Exception:
        return None
    if not cmd:
        return None
    try:
        out = subprocess.run(
            cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=15
        ).stdout.strip()
    except Exception:
        return None
    m = re.search(r"(\d+)\s*/\s*(\d+)", out)
    if m:
        return (out[:120], int(m.group(1)), int(m.group(2)))
    m = re.search(r"-?\d+", out)
    if m:
        return (out[:120], int(m.group(0)), None)
    return None

WRAPUP_PROMPT = """CONTEXT THRESHOLD REACHED ({ctx:,} >= {thr:,} tokens) — run the wrap-up ritual NOW, while full context exists. Order matters:

1. COMMIT everything finished (granular, semantic). Post-compaction verification trusts git, not memory — uncommitted work risks being hallucinated-as-done after the summary.
2. Session sweep: anything to improve, eradicate, or rethink with smart tooling, hooks, skills, MCPs, or goal rethinking? Wasted effort? Bad infrastructure? What could a future agent leverage? Only long-term, deep, STRICTLY better changes — no noise, no iatrogenic harm, no backward-compat cruft. "Nothing strictly better" is a fine answer.
3. Run /rsi.
4. Spend remaining full-context leverage: loose ends only this context can tie off; update docs/indexes for files this session touched; record path-dependent decisions in decisions/.
5. Rewrite .claude/checkpoint.md as the post-compact re-entry brief:
   GOAL — the /goal verbatim.
   FRONTS — per-front status (done / in-flight / blocked) with evidence (commit SHAs, paths).
   NEXT — the 2-3 highest-value next actions, with exact commands.
   VERIFY — commands the post-compact agent must run before trusting state (git log --oneline -10, test/gate commands). Never carry bare numbers across the boundary — carry the command that produces them.
   ASKS — anything for the human (also append to HUMAN.md).
6. End your turn normally. Native auto-compact fires on a subsequent turn (the PreCompact guard passes once this ritual has been prompted); the goal continues after."""

CONTINUE_PROMPT = """GOAL-RUN ACTIVE (continuation {n}/{cap}) — the goal is not marked done; keep going.
- If you just compacted: re-orient from .claude/checkpoint.md and VERIFY claimed work against git log / the checkpoint's VERIFY commands before building on it — compaction summaries hallucinate completions.
- Advance the highest-value front. Run the portfolio (grind subagents / heretic on what just landed / scout / meta) rather than a single serial thread; don't idle, don't re-derive settled state.
- Goal fully done AND verified → touch .claude/goal-done, write the final summary, stop.
- Genuinely blocked on the human with no other front progressable → append the ask to HUMAN.md, touch .claude/goal-blocked, stop."""


def _block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    claude_dir = cwd / ".claude"
    marker = claude_dir / "goal-run"
    if not marker.is_file():
        return 0
    lines = []
    try:
        lines = marker.read_text().split()
    except Exception:
        pass
    try:
        threshold = int(lines[0]) if lines else 100000
    except Exception:
        threshold = 100000
    # Ownership FIRST: goal-night stamps the goal session's id as the 2nd token, so
    # OTHER sessions in an armed repo (a daytime peer, a subagent shell) are never
    # controlled — including the goal-done challenges below. No 2nd token (manual
    # arming) = legacy: control any session.
    owner = lines[1] if len(lines) > 1 else ""
    if owner and payload.get("session_id") != owner:
        return 0
    if (claude_dir / "goal-done").exists() or (claude_dir / "goal-blocked").exists():
        # Open-board challenge (fires ONCE): goal-done with unblocked A-rows still
        # open is the premature-stop class (6th manual flag 2026-07-05) — the goal
        # FILE finishing is not the board being empty. Repo-generic: only where the
        # obligation backlog exists. Fail-open on any error.
        challenged = claude_dir / "goal-done-challenged"
        backlog = cwd / "loop" / "idea_backlog.py"
        if (
            (claude_dir / "goal-done").exists()
            and not challenged.exists()
            and backlog.is_file()
        ):
            try:
                import subprocess

                out = subprocess.run(
                    ["uv", "run", "python3", str(backlog), "list", "--open"],
                    cwd=cwd, capture_output=True, text=True, timeout=15,
                ).stdout
                a_rows = [
                    ln for ln in out.splitlines()
                    if " A open " in ln and "dep:" not in ln.split("—")[0]
                ]
                if a_rows:
                    challenged.write_text("\n".join(a_rows) + "\n")
                    return _block(
                        "GOAL-DONE CHALLENGED (fires once): the goal file is done but "
                        f"{len(a_rows)} unblocked A-row(s) remain open:\n"
                        + "\n".join("  " + ln.strip() for ln in a_rows[:8])
                        + "\nEither continue working them (portfolio dispatches), or append a "
                        "per-row deferral reason to HUMAN.md and stop. The board being empty, "
                        "not the goal file, is the stop condition."
                    )
            except Exception:
                pass
        # Conversion-debt challenge (fires ONCE, arc-agi shape but repo-generic via the
        # status surface): goal-done while the HELD-OUT ratchet is dark is the
        # characterize-without-converting class (118 commits / 5 days, 2026-07-05
        # postmortem). Thresholds live in loop/status.py conversion_note() — loaded via
        # --conversion, never re-stated here (one-definition rule). Fail-open.
        debt_challenged = claude_dir / "goal-done-debt-challenged"
        status_py = cwd / "loop" / "status.py"
        if (
            (claude_dir / "goal-done").exists()
            and not debt_challenged.exists()
            and status_py.is_file()
        ):
            try:
                import subprocess

                line = subprocess.run(
                    ["uv", "run", "python3", str(status_py), "--conversion"],
                    cwd=cwd, capture_output=True, text=True, timeout=30,
                ).stdout.strip()
                if "CONVERSION DEBT" in line:
                    debt_challenged.write_text(line + "\n")
                    return _block(
                        "GOAL-DONE CHALLENGED (fires once): the held-out conversion ratchet "
                        "is in debt:\n  " + line + "\nA goal run that promotes mechanisms "
                        "without a held-out conversion attempt is ratcheting on in-sample "
                        "characterization (Constitution #1). Either run the composed held-out "
                        "eval (agent/holdout_eval.py) now, or append the per-run deferral "
                        "reason to HUMAN.md and stop."
                    )
            except Exception:
                pass
        return 0

    # Ritual outranks continuation: it must land before the native compact.
    fired = claude_dir / "goal-wrapup-fired"
    ctx = context_tokens(payload.get("transcript_path", ""))
    if ctx >= threshold and not fired.exists():
        try:
            fired.write_text(f"ctx={ctx}\n")
        except Exception:
            pass
        return _block(WRAPUP_PROMPT.format(ctx=ctx, thr=threshold))

    # Continuation: Stop = "finished a meaningful unit" — re-kick until done/blocked.
    # Deliberately ignores stop_hook_active (the re-kick loop is the point);
    # MAX_CONTINUES + the done/blocked escapes bound it.
    counter = claude_dir / "goal-continues"
    n = 0
    try:
        n = int(counter.read_text().strip() or "0")
    except Exception:
        pass
    if n >= MAX_CONTINUES:
        return 0
    try:
        counter.write_text(str(n + 1))
    except Exception:
        pass

    # UNSTARTED detection (opt-in, fires ONCE): the goal keeps CONTINUING but its bound deliverable
    # has zero progress -> the agent may be monitoring already-done work instead of starting the goal
    # (2026-06-27 genomics: syn3sr sat 0/258 an entire overnight window while markus/syn2sr, both
    # done, were monitored). No-op unless .claude/goal-deliverable is armed; fail-open.
    unstarted_prefix = ""
    warned = claude_dir / "goal-unstarted-warned"
    if n >= 1 and not warned.exists():
        prog = _deliverable_progress(cwd, claude_dir)
        if prog is not None and prog[1] == 0:
            label, _done, total = prog
            tot = f"/{total}" if total is not None else ""
            try:
                warned.write_text(f"{label}\n")
            except Exception:
                pass
            unstarted_prefix = (
                f"GOAL UNSTARTED: deliverable at 0{tot} after {n} continuation(s). You have been "
                f"CONTINUING, but the goal's checkable deliverable has ZERO progress — you may be "
                f"monitoring already-done work instead of starting the goal (progress check output: "
                f"{label}). START the deliverable NOW, or if it is intentionally deferred, say so "
                f"explicitly and touch .claude/goal-blocked with the reason in HUMAN.md. Do NOT keep "
                f"monitoring done work.\n\n"
            )
    return _block(unstarted_prefix + CONTINUE_PROMPT.format(n=n + 1, cap=MAX_CONTINUES))


if __name__ == "__main__":
    sys.exit(main())
