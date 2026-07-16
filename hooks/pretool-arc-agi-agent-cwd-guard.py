#!/usr/bin/env python3
# Gov-ID: hook:arc-agi-agent-cwd-guard
# goal: stop ModuleNotFoundError for arc_agi/arcengine/local_runner when uv run
#       is invoked from arc-agi repo root (deps live in agent/pyproject.toml)
# verifier: --selftest
# blast_radius: shared (PreToolUse Bash; cwd-gated to arc-agi)
"""pretool-arc-agi-agent-cwd-guard.py — steer agent-package imports into agent/.

Measured (observe 2026-07-10): missing-module:arcengine ×18/5d + arc_agi ×11/4d
+ local_runner — all interactive agents running `uv run` from repo root. Root
pyproject has no arc-agi/arcengine; packages are declared in agent/pyproject.toml.

Prefer rewrite via `uv run --directory <agent>` (works for site-packages AND
local agent/*.py modules). Fail-open on parse errors.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ARC_ROOT_NAME = "arc-agi"
# Bug fix (arc-agi docs/audit/2026-07-16-bughunt-dossier.md finding D-P2-15): the plain
# `from`/`import` form missed the two dynamic-import shapes Python offers for the exact
# same modules — `importlib.import_module('arc_agi')` and `__import__('arc_agi')` — both
# real bypasses (no `import`/`from` keyword token for the static regex to anchor on), and
# both produce the identical ModuleNotFoundError this hook exists to prevent.
_IMPORT = re.compile(
    r"\b(?:from|import)\s+(arc_agi|arcengine|local_runner)\b"
    r"|\bimportlib\.import_module\(\s*['\"](arc_agi|arcengine|local_runner)['\"]"
    r"|\b__import__\(\s*['\"](arc_agi|arcengine|local_runner)['\"]"
)
_UV_RUN = re.compile(r"\buv\s+run\b")
_ALREADY_DIR = re.compile(
    r"(?:--directory|--project)\s+(\S*agent\S*)"
    r"|\bcd\s+(?:\./)?agent\b"
    r"|\bcd\s+\S+/agent\b"
)
def _find_agent_dir(cwd: str) -> Path | None:
    if not cwd:
        return None
    try:
        p = Path(cwd).expanduser().resolve()
    except OSError:
        return None
    for cand in (p, *p.parents):
        if cand.name == "agent" and cand.parent.name == _ARC_ROOT_NAME:
            if (cand / "pyproject.toml").exists():
                return cand
        if cand.name == _ARC_ROOT_NAME and (cand / "agent" / "pyproject.toml").exists():
            return cand / "agent"
        if cand == cand.parent:
            break
    return None


def _needs_agent_env(cmd: str) -> bool:
    if _IMPORT.search(cmd):
        return True
    # `uv run python3 agent/foo.py` from root — script lives under agent/.
    # The execution prefix is REQUIRED: a bare ` agent/foo.py` argument to
    # git/cat/grep is not an import site (false-blocked git diff, 2026-07-10).
    if re.search(r"(?:^|[\s;|&])(?:uv\s+run\s+(?:python3?\s+)?|python3?\s+)agent/\S+\.py\b", cmd):
        return True
    # pytest targeting agent/ tree from repo root (observe 2026-07-12 residual)
    if re.search(r"\bpytest\b.*\bagent/", cmd) or re.search(
        r"\bpython3?\s+-m\s+pytest\b.*\bagent/", cmd
    ):
        return True
    return False


def _insert_directory(cmd: str, agent_dir: Path) -> str | None:
    """Insert `uv run --directory <agent>` after first `uv run`, or None if no uv run."""
    m = _UV_RUN.search(cmd)
    if not m:
        return None
    rest = cmd[m.end() :]
    if re.match(r"\s+--(?:directory|project)\b", rest):
        return None
    insert = f" --directory {agent_dir}"
    out = cmd[: m.end()] + insert + cmd[m.end() :]
    # `uv run --directory agent [python3] agent/foo.py` → … [python3] foo.py
    # (anchored to the uv-run invocation so unrelated `-f agent/x.py` args survive)
    out = re.sub(
        r"(\buv\s+run\s+--directory\s+\S+\s+(?:python3?\s+)?)agent/(\S+\.py)\b",
        r"\1\2",
        out,
        count=1,
    )
    # `… -m pytest agent/tests/…` → `… -m pytest tests/…` under agent/
    out = re.sub(
        r"(\b(?:python3?\s+-m\s+)?pytest\s+)agent/",
        r"\1",
        out,
        count=1,
    )
    return out


def verdict(cmd: str, cwd: str = "") -> tuple[str, str]:
    """Return ('block'|'rewrite'|'pass', message_or_new_cmd)."""
    if not cmd or not cmd.strip():
        return "pass", ""
    agent = _find_agent_dir(cwd)
    if agent is None:
        return "pass", ""
    try:
        cwd_res = Path(cwd).expanduser().resolve()
        cwd_res.relative_to(agent)  # already under agent/
        return "pass", ""
    except (OSError, ValueError):
        pass
    if _ALREADY_DIR.search(cmd):
        return "pass", ""
    if not _needs_agent_env(cmd):
        return "pass", ""

    if _UV_RUN.search(cmd):
        new = _insert_directory(cmd, agent)
        if new and new != cmd:
            return "rewrite", new
        return "pass", ""

    return (
        "block",
        "BLOCK: arc-agi packages `arc_agi`/`arcengine`/`local_runner` live in "
        f"`agent/` (not repo root). Run: `cd agent && uv run python3 …` or "
        f"`uv run --directory {agent} python3 …`. See arc-agi CLAUDE.md.",
    )


def _selftest() -> int:
    root = "/Users/alien/Projects/arc-agi"
    agent = f"{root}/agent"
    cases: list[tuple[str, str, str]] = [
        # block/rewrite targets
        (root, 'uv run python3 -c "import arc_agi"', "rewrite"),
        (root, 'uv run python3 -c "from arcengine import GameAction"', "rewrite"),
        (root, 'uv run python3 -c "import local_runner"', "rewrite"),
        (root, "uv run python3 agent/foundry_pilot.py", "rewrite"),
        (f"{root}/experiments", 'uv run python3 -c "import arcengine"', "rewrite"),
        # D-P2-15: dynamic-import bypass shapes (importlib.import_module / __import__) —
        # must be caught the same as a static `import`/`from` statement.
        (root, 'uv run python3 -c "import importlib; importlib.import_module(\'arc_agi\')"', "rewrite"),
        (root, "uv run python3 -c \"import importlib; importlib.import_module('arcengine')\"", "rewrite"),
        (root, 'uv run python3 -c "__import__(\'local_runner\')"', "rewrite"),
        (root, "uv run python3 -c \"__import__('arc_agi')\"", "rewrite"),
        # already correct
        (agent, 'uv run python3 -c "import arc_agi"', "pass"),
        (root, f'uv run --directory {agent} python3 -c "import arc_agi"', "pass"),
        (root, 'cd agent && uv run python3 -c "import arc_agi"', "pass"),
        # out of scope
        ("/Users/alien/Projects/intel", 'uv run python3 -c "import arc_agi"', "pass"),
        (root, "uv run python3 -m pytest tests/", "pass"),
        (root, "git status", "pass"),
        # agent/*.py as a NON-execution argument (the 2026-07-10 false block)
        (root, "git diff --stat -- agent/tests/test_answer_semantic.py", "pass"),
        (root, "cat agent/foundry_pilot.py", "pass"),
        (root, "uv run agent/foundry_pilot.py", "rewrite"),
        # bare python with import → block (uv-guard should rewrite first)
        (root, 'python3 -c "import arcengine"', "block"),
        (root, "python3 -c \"__import__('arcengine')\"", "block"),
        # 2026-07-12 residual shapes
        (root, "uv run python3 -m pytest agent/tests/test_foo.py", "rewrite"),
    ]
    bad = 0
    for cwd, cmd, want in cases:
        got, msg = verdict(cmd, cwd)
        ok = got == want
        if ok and want == "rewrite":
            ok = "--directory" in msg and "agent" in msg
            if "agent/foundry_pilot.py" in cmd:
                tail_part = msg.split("--directory", 1)[-1]
                ok = ok and "foundry_pilot.py" in tail_part and "agent/foundry_pilot.py" not in tail_part
        bad += not ok
        print(f"  {'ok' if ok else 'FAIL'} want={want} got={got} cwd={cwd!r} cmd={cmd!r}")
        if want == "rewrite" and got == "rewrite":
            print(f"       → {msg}")
    # rewrite shape spot-check
    _, rw = verdict('uv run python3 -c "import arc_agi"', root)
    expect = f'uv run --directory {agent} python3 -c "import arc_agi"'
    if rw != expect:
        # agent path resolve may differ by symlink; check suffix
        if not (rw.startswith("uv run --directory ") and rw.endswith(' python3 -c "import arc_agi"')):
            print(f"  FAIL rewrite shape: {rw!r}")
            bad += 1
        else:
            print(f"  ok rewrite shape (resolved path): {rw}")
    print("PASS" if not bad else "FAIL", f"{len(cases) - bad}/{len(cases)}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash", "Shell"):
        return 0
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "")
    cwd = payload.get("cwd") or ""
    action, msg = verdict(cmd, cwd)
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    if action == "rewrite" and msg:
        updated = dict(ti)
        updated["command"] = msg
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "updatedInput": updated,
                    }
                }
            )
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
