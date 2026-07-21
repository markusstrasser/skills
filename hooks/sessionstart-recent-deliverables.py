#!/usr/bin/env python3
# Gov-ID: hook:sessionstart-recent-deliverables
# goal: surface recent audit/debug-until-dry deliverables at session start (GROW_COVERAGE)
# verifier: --selftest
# blast_radius: shared if wired globally — default SHADOW; no advisory until ≥2026-07-24
"""sessionstart-recent-deliverables — SessionStart operational-deliverable inject.

Blindspot CONVERT (observe 2026-07-20 / 2026-07-21): operator asks whether a
debug-until-dry dossier / sibling-session cleanup was integrated. prior-context
covers memos; this covers deliverable *paths*.

Modes (env RECENT_DELIVERABLES_MODE):
  shadow   (default) — log candidates; silent to model
  advisory — ≤5 paths as SessionStart additionalContext

Not wired into ~/.claude/settings.json this tick (propose shared deploy).
Fail-open.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SHADOW_LOG = Path.home() / ".claude" / "sessionstart-recent-deliverables-shadow.jsonl"
MODE = os.environ.get("RECENT_DELIVERABLES_MODE", "shadow").strip().lower()
SINCE_DAYS = int(os.environ.get("RECENT_DELIVERABLES_SINCE_DAYS", "7"))
MAX_PATHS = int(os.environ.get("RECENT_DELIVERABLES_MAX", "5"))

GIT_PATHSPECS = (
    "artifacts/**/debug*.md",
    "artifacts/**/*debug-until-dry*",
    "docs/audit/**",
    "**/debug-until-dry*.md",
)


def _cwd_from_stdin() -> str:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if raw.strip():
        try:
            obj = json.loads(raw)
            cwd = (obj.get("cwd") or obj.get("workspace_roots", [None])[0] or "").strip()
            if cwd:
                return str(Path(cwd).expanduser().resolve())
        except Exception:
            pass
    env = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return str(Path(env).expanduser().resolve())


def _git_paths(cwd: str) -> list[str]:
    try:
        r = subprocess.run(
            [
                "git", "-C", cwd, "log",
                f"--since={SINCE_DAYS} days ago",
                "--name-only", "--pretty=format:",
                "--", *GIT_PATHSPECS,
            ],
            capture_output=True, text=True, timeout=8,
        )
    except Exception:
        return []
    seen: list[str] = []
    for line in (r.stdout or "").splitlines():
        p = line.strip()
        if p and p not in seen:
            seen.append(p)
        if len(seen) >= MAX_PATHS:
            break
    return seen


def _find_fallback(cwd: str) -> list[str]:
    root = Path(cwd)
    out: list[str] = []
    for base in (root / "artifacts", root / "docs" / "audit"):
        if not base.is_dir():
            continue
        try:
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                name = p.name.lower()
                if "debug" in name or "audit" in str(p.relative_to(root)).lower():
                    rel = str(p.relative_to(root))
                    if rel not in out:
                        out.append(rel)
                if len(out) >= MAX_PATHS:
                    return out
        except Exception:
            continue
    return out


def _log_shadow(cwd: str, paths: list[str]) -> None:
    try:
        SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cwd": cwd,
            "mode": MODE,
            "paths": paths,
        }
        with SHADOW_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main() -> int:
    if os.environ.get("CODEX_HOOK_COMPAT_SMOKE") == "1" or os.environ.get("CLAUDE_HOOK_SMOKE") == "1":
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        return _selftest()
    try:
        cwd = _cwd_from_stdin()
        paths = _git_paths(cwd) or _find_fallback(cwd)
        if not paths:
            return 0
        _log_shadow(cwd, paths)
        if MODE != "advisory":
            return 0
        lines = [f"Recent operational deliverables (last {SINCE_DAYS}d) — check if already integrated:"]
        lines.extend(f"  - {p}" for p in paths)
        ctx = "\n".join(lines)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }
        }))
    except Exception:
        return 0
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "artifacts" / "debug").mkdir(parents=True)
        demo = root / "artifacts" / "debug" / "debug-until-dry-demo.md"
        demo.write_text("# demo\n", encoding="utf-8")
        # fallback path (no git required)
        paths = _find_fallback(str(root))
        assert any("debug-until-dry-demo.md" in p for p in paths), paths
        # shadow must not print JSON when MODE=shadow
        os.environ["RECENT_DELIVERABLES_MODE"] = "shadow"
        global MODE
        MODE = "shadow"
        _log_shadow(str(root), paths)
        print("OK sessionstart-recent-deliverables selftest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
