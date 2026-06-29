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

    # 10. existing_infra slice: view/hook/just recipe → codebase-map + justfile + hooks.
    ex_td = tempfile.TemporaryDirectory()
    ex_base = Path(ex_td.name)
    (ex_base / ".claude/rules").mkdir(parents=True)
    (ex_base / ".claude/rules/codebase-map.md").write_text(
        "## scripts/hooks/ — 2 files\n  detail: .claude/maps/codebase.scripts-hooks.md\n"
    )
    (ex_base / "justfile").write_text("blindspot:\n    echo blindspot\n\nmaintain-tick:\n    echo tick\n")
    (ex_base / "scripts/hooks").mkdir(parents=True)
    (ex_base / "scripts/hooks/sample_guard.py").write_text("# hook\n")
    subprocess.run(["git", "-C", str(ex_base), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(ex_base), "add", "."], check=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    subprocess.run(["git", "-C", str(ex_base), "commit", "-m", "add blindspot hook scaffold", "-q"],
                   check=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    out = run({
        "user_message": "should we add a new hook for blindspot detection or use an existing view?",
        "cwd": str(ex_base),
        "session_id": "s_existing_infra",
    })
    c10 = ctx(out)
    check("existing_infra emits additionalContext", bool(c10))
    check("existing_infra surfaces codebase-map", "codebase-map" in c10 or "scripts-hooks" in c10)
    check("existing_infra surfaces just recipe", "just blindspot" in c10)
    check("existing_infra surfaces hook script", "sample_guard.py" in c10)
    check("existing_infra surfaces recent commits on infra prompt", "Recent commits" in c10 or "commit" in c10.lower())
    ex_td.cleanup()

    # 12. Git-path slice: committed tracked file surfaces via recent git-touched paths.
    gp_td = tempfile.TemporaryDirectory()
    gp_base = Path(gp_td.name)
    subprocess.run(["git", "-C", str(gp_base), "init", "-q"], check=True)
    (gp_base / "migrations").mkdir()
    seed = gp_base / "migrations/2026-06-29-seed-claimcore-view.sql"
    seed.write_text("-- claimcore view seed for prior-context test\n")
    subprocess.run(
        ["git", "-C", str(gp_base), "add", str(seed)],
        check=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )
    subprocess.run(
        ["git", "-C", str(gp_base), "commit", "-m", "add claimcore view migration", "-q"],
        check=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )
    out = run({
        "user_message": "should we design a new schema view for claimcore ingestion?",
        "cwd": str(gp_base),
        "session_id": "s_git_paths",
    })
    c12 = ctx(out)
    check("git-path slice emits on infra schema prompt", bool(c12))
    check("git-path surfaces committed migration path", "seed-claimcore-view.sql" in c12 or "migrations/" in c12)
    gp_td.cleanup()

    # 11. Rediscovery correction steers inject recent git log even without topic keywords.
    red_td = tempfile.TemporaryDirectory()
    red_base = Path(red_td.name)
    (red_base / ".git").mkdir()
    subprocess.run(["git", "-C", str(red_base), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(red_base), "commit", "--allow-empty", "-m", "prior observe work", "-q"],
        check=True, env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )
    out = run({
        "user_message": "why don't you check the git log for what we already built?",
        "cwd": str(red_base),
        "session_id": "s_rediscovery",
    })
    c11 = ctx(out)
    check("rediscovery steer emits prior-context", bool(c11))
    check("rediscovery surfaces recent commits", "prior observe" in c11 or "commit" in c11.lower())
    red_td.cleanup()

    td.cleanup()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
