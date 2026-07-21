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


# experiments/*.py often `import arc_agi` internally — the shell command has no
# import token, so static import regex misses it (observe 2026-07-20: render_trace,
# smoke_novelty_divergence, residue selftests from repo root).
_EXPERIMENTS_PY = re.compile(
    r"(?:^|[\s;|&])(?:uv\s+run\s+(?:python3?\s+)?|python3?\s+)"
    r"((?:\S+/)?experiments/\S+\.py|\S+/arc-agi/experiments/\S+\.py)\b"
)

# The _IMPORT text branch needs an actual python/uv invocation in the command —
# otherwise `rg -n "import arc_agi" f.py` (pattern TEXT, not an import site) gets
# hard-blocked (live false block 2026-07-21, same class as the 2026-07-10 git-diff one).
_EXEC_TOKEN = re.compile(r"\b(?:uv\s+run|python3?)\b")


def _experiments_script_needs_agent(cmd: str, cwd: str) -> bool | None:
    """None = not an experiments/*.py invocation. Else: does the SCRIPT itself
    import agent packages? Reads the file (first 64KB); unresolvable/unreadable
    paths stay True (conservative — old blanket behavior). Transitive imports are
    NOT chased: a false pass just surfaces the original loud ModuleNotFoundError
    this hook exists to pre-empt, which is fail-open, not silent corruption.
    (2026-07-21: the A/B converter suite — zero agent imports, pure stdlib+
    transformers — was blanket-rewritten; lane had to dodge via cwd.)"""
    m = _EXPERIMENTS_PY.search(cmd)
    if not m:
        return None
    path_txt = m.group(1)
    p = Path(path_txt)
    if not p.is_absolute():
        cands = []
        agent = _find_agent_dir(cwd)
        if agent is not None:
            cands.append(agent.parent / path_txt)
        if cwd:
            cands.append(Path(cwd) / path_txt)
        p = next((c for c in cands if c.exists()), None)
        if p is None:
            return True
    elif not p.exists():
        return True
    try:
        content = p.read_text(errors="replace")[:65536]
    except OSError:
        return True
    return bool(_IMPORT.search(content))


def _needs_agent_env(cmd: str, *, cwd: str = "") -> bool:
    if _IMPORT.search(cmd) and _EXEC_TOKEN.search(cmd):
        return True
    # `uv run python3 agent/foo.py` from root — script lives under agent/.
    # The execution prefix is REQUIRED: a bare ` agent/foo.py` argument to
    # git/cat/grep is not an import site (false-blocked git diff, 2026-07-10).
    if re.search(r"(?:^|[\s;|&])(?:uv\s+run\s+(?:python3?\s+)?|python3?\s+)agent/\S+\.py\b", cmd):
        return True
    exp = _experiments_script_needs_agent(cmd, cwd)
    if exp is not None and exp:
        return True
    # pytest targeting agent/ tree from repo root (observe 2026-07-12 residual).
    # Segment-scoped + invocation-anchored: `pytest` must be the invoked command of a
    # segment whose OWN arguments reference agent/. The old cross-command form
    # (`\bpytest\b.*\bagent/` over the whole string) false-blocked a read-only status
    # compound where an `echo "== pytest lastfailed =="` preceded an unrelated
    # `cat agent/.pytest_cache/...` (2026-07-18) — same class as the 2026-07-10
    # git-diff false block that anchored the .py branch above.
    #
    # 2026-07-20 residual: cwd under experiments/… running pytest tests/ (no
    # agent/ in argv) — tests import arc_agi. Narrow: experiments path in argv
    # OR cwd contains /experiments (not all root-level pytest).
    cwd_norm = (cwd or "").replace("\\", "/")
    cwd_under_experiments = "/experiments/" in (cwd_norm + "/") or cwd_norm.rstrip("/").endswith(
        "/experiments"
    )
    for seg in re.split(r"[;|&\n]+", cmd):
        is_pytest = bool(
            re.match(
                r"\s*(?:\S+=\S+\s+)*(?:uv\s+run\s+(?:--\S+(?:\s+\S+)?\s+)*)?"
                r"(?:python3?\s+-m\s+)?pytest\b",
                seg,
            )
        )
        if not is_pytest:
            continue
        if re.search(r"\bagent/", seg) or re.search(r"\bexperiments/", seg) or cwd_under_experiments:
            return True
    return False


def _insert_directory(cmd: str, agent_dir: Path, *, cwd: str = "") -> str | None:
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
    # experiments/*.py is NOT under agent/ — absolutize so --directory agent still finds it
    root = agent_dir.parent
    out = re.sub(
        r"(\buv\s+run\s+--directory\s+\S+\s+(?:python3?\s+)?)experiments/",
        rf"\1{root}/experiments/",
        out,
        count=1,
    )
    # pytest from cwd under experiments/foo: relative tests/ → absolute
    cwd_norm = (cwd or "").replace("\\", "/")
    if "/experiments/" in (cwd_norm + "/") or cwd_norm.rstrip("/").endswith("/experiments"):
        try:
            cwd_abs = str(Path(cwd).expanduser().resolve())
        except OSError:
            cwd_abs = cwd
        out = re.sub(
            r"(\b(?:python3?\s+-m\s+)?pytest\s+)(?!/)",
            rf"\1{cwd_abs}/",
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
    if not _needs_agent_env(cmd, cwd=cwd):
        return "pass", ""

    if _UV_RUN.search(cmd):
        new = _insert_directory(cmd, agent, cwd=cwd)
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
        (root, "pytest agent/tests/test_foo.py", "block"),
        (root, "PYTHONUNBUFFERED=1 pytest agent/tests/", "block"),
        # 2026-07-18 false block: "pytest" in echo TEXT + unrelated agent/ path in a
        # LATER segment must not fire (read-only status compound, blocked live).
        (root, 'echo "== pytest lastfailed =="; cat agent/.pytest_cache/v/cache/lastfailed; git status --short', "pass"),
        (root, 'echo "pytest agent/tests broken?"', "pass"),
        # 2026-07-20: experiments/*.py imports arc_agi internally (no import token in shell)
        (root, "uv run python3 experiments/render_trace.py traces/x.json --steps 0", "rewrite"),
        (root, "uv run python3 experiments/gate_goal_term/smoke_novelty_divergence.py --help", "rewrite"),
        (f"{root}/experiments/probe_selector_abc", "uv run python3 -m pytest tests/test_bridge2.py -q", "rewrite"),
        (root, "cat experiments/render_trace.py", "pass"),
        # 2026-07-21: experiments script PROVEN agent-import-free must pass (A/B converter suite);
        # unresolvable script stays conservative (rewrite); non-execution rg with import-shaped
        # pattern TEXT must pass (live false block same day).
        (root, "uv run --with transformers python3 experiments/harness_format_ab/converter/gate2_admission.py", "pass"),
        (root, "uv run python3 experiments/nonexistent_selftest_dummy_xyz.py", "rewrite"),
        (root, 'rg -n "(import|from) (arc_agi|arcengine|local_runner)" experiments/render_trace.py', "pass"),
        (root, 'rg -n "import arc_agi" agent/foo.py', "pass"),
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
            if "experiments/render_trace" in cmd:
                ok = ok and f"{root}/experiments/render_trace.py" in msg
            if "probe_selector_abc" in cwd and "pytest" in cmd:
                ok = ok and f"{cwd}/tests/test_bridge2.py" in msg
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
