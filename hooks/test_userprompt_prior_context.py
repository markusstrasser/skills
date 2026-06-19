#!/usr/bin/env python3
"""Selftest for userprompt-prior-context.py — run: uv run python3 test_userprompt_prior_context.py

Verifies the two gates (intent + keyword-match), dedup, emission shape, and
fail-open. Uses a temp dir with fixture research-index.md + ideas.md so file
scans match deterministically; git scan returns [] in the temp dir (fine).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent / "userprompt-prior-context.py"

# Hermetic HOME so the hook's per-session dedup files (Path.home()/.claude/...)
# land in a temp dir, never littering the real ~/.claude.
_HOME = tempfile.TemporaryDirectory()
(Path(_HOME.name) / ".claude").mkdir(parents=True, exist_ok=True)


def run(envelope: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(envelope), capture_output=True, text=True, timeout=10,
        env={**os.environ, "HOME": _HOME.name},
    )
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}: {p.stderr}"
    return p.stdout.strip()


def ctx(out: str) -> str:
    if not out:
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def fixture_dir() -> tempfile.TemporaryDirectory:
    td = tempfile.TemporaryDirectory()
    base = Path(td.name)
    (base / ".claude/rules").mkdir(parents=True)
    (base / ".claude/rules/research-index.md").write_text(
        "| `2026-06-04-arena-agent-eval-transfer.md` | tool-hallucination metric, arena |\n"
        "| `2026-06-07-state-externalization.md` | externalize bookkeeping, harness |\n"
    )
    (base / "ideas.md").write_text(
        "- A standing duckdb dependency guard for missing-dep failures\n"
        "- something short\n"
        "- Investigate whether the blindspot miner should embed fewer candidates\n"
    )
    (base / "research").mkdir()
    (base / "research/2026-06-11-duckdb-invocation-discipline.md").write_text("x")
    return td


def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")

    td = fixture_dir()
    base = td.name

    # 1. No intent -> silent (even though "duckdb" matches prior work).
    out = run({"user_message": "the duckdb guard is working great, thanks",
               "cwd": base, "session_id": "s1"})
    check("no-intent prompt is silent", out == "")

    # 2. Intent + no matching topic -> silent.
    out = run({"user_message": "should we build a kubernetes operator for xyzzy?",
               "cwd": base, "session_id": "s2"})
    check("intent but no prior-work match is silent", out == "")

    # 3. Intent + matching memo/ideas -> emits, names the source.
    out = run({"user_message": "should we build a duckdb dependency guard?",
               "cwd": base, "session_id": "s3"})
    c = ctx(out)
    check("intent + match emits additionalContext", bool(c))
    check("names PRIOR-CONTEXT", "PRIOR-CONTEXT" in c)
    check("surfaces the matching ideas.md line", "duckdb dependency guard" in c)
    check("surfaces the matching research memo", "duckdb-invocation-discipline" in c)

    # 4. Dedup: same session, same reference-set -> silent the second time.
    out2 = run({"user_message": "remind me, should we build that duckdb dependency guard?",
                "cwd": base, "session_id": "s3"})
    check("same session + same refs is deduped (silent)", out2 == "")

    # 5. Different session, same prompt -> emits again (dedup is per-session).
    out3 = run({"user_message": "should we build a duckdb dependency guard?",
                "cwd": base, "session_id": "s_other"})
    check("different session re-emits", bool(ctx(out3)))

    # 6. Status/prior-existence intent ("do we have") also fires.
    out = run({"user_message": "do we already have anything for blindspot miner candidates?",
               "cwd": base, "session_id": "s4"})
    check("'do we have' status intent fires on match", bool(ctx(out)))

    # 7. Malformed / empty input -> no crash, no output.
    check("empty stdin is safe", run({}) == "")
    p = subprocess.run([sys.executable, str(HOOK)], input="not json{",
                       capture_output=True, text=True, timeout=10)
    check("garbage stdin exits 0 silently", p.returncode == 0 and p.stdout.strip() == "")

    # 8. Very short prompt -> silent.
    check("too-short prompt is silent",
          run({"user_message": "build", "cwd": base, "session_id": "s5"}) == "")

    # 9. Infra-design intent surfaces session-forensics + local script inventory.
    infra_td = tempfile.TemporaryDirectory()
    infra_base = Path(infra_td.name)
    (infra_base / "scripts").mkdir()
    (infra_base / "scripts/session_probe.py").write_text(
        "# uses v_session_commits and agentlogs.db\n"
    )
    (infra_base / ".claude/rules").mkdir(parents=True)
    (infra_base / ".claude/rules/session-forensics.md").write_text("# agentlogs schema\n")
    out = run({
        "user_message": "should we design a schema to join session_commits with git_commits?",
        "cwd": str(infra_base),
        "session_id": "s_infra",
    })
    c9 = ctx(out)
    check("infra-design emits additionalContext", bool(c9))
    check("infra surfaces session-forensics path", "session-forensics.md" in c9)
    check("infra surfaces local script hit", "session_probe.py" in c9)
    infra_td.cleanup()

    td.cleanup()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
