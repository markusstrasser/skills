#!/usr/bin/env python3
"""lint_hook_input_contract.py — enforce the Claude/Codex hook input contract.

Ground truth (captured from Claude Code 2.1.168, 2026-06-07):
  - Tool input arrives on **stdin** as the FULL envelope:
        {"hook_event_name","tool_name","tool_input":{...},"cwd",...}
    Fields like command/file_path/skill live under `.tool_input`, NOT at top level.
  - Claude Code sets **no** CLAUDE_TOOL_INPUT / CLAUDE_TOOL_NAME env vars.
  - Codex sets CLAUDE_TOOL_INPUT (same full-envelope shape) AND pipes stdin.

So a hook is correct iff it:
  1. Obtains input from stdin (`$(cat)`), or from CLAUDE_TOOL_INPUT WITH a
     `${CLAUDE_TOOL_INPUT:-$(cat)}` stdin fallback (never bare `$CLAUDE_TOOL_INPUT`).
  2. Extracts tool fields from `.tool_input.<field>`, not the top level.

This catches the two failure classes found in the 30h hook audit:
  - env-only hooks → dead/no-op under Claude Code (var unset).
  - top-level field extraction → reads the envelope's wrong level → empty value
    → guard silently does nothing (e.g. pretool-bash-loop-guard never fired).

Usage:
    python3 lint_hook_input_contract.py            # lint all wired hooks
    python3 lint_hook_input_contract.py --all      # lint every *.sh in hooks/
    python3 lint_hook_input_contract.py --json
Exit 1 if any violation found.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
HOME = Path.home()
FIELDS = ("command", "file_path", "skill", "args", "content", "new_string",
          "query", "search_query", "prompt", "url", "claim", "path", "description")

# bare $CLAUDE_TOOL_INPUT with no stdin fallback anywhere in the file
# Shell `$CLAUDE_TOOL_INPUT` and Python `os.environ[...CLAUDE_TOOL_INPUT...]`
BARE_ENV = re.compile(r'\$\{?CLAUDE_TOOL_(INPUT|NAME)\b'
                      r'|environ(\.get)?\(\s*[\'"]CLAUDE_TOOL_(INPUT|NAME)'
                      r'|environ\[\s*[\'"]CLAUDE_TOOL_(INPUT|NAME)')
ENV_FALLBACK = re.compile(r'CLAUDE_TOOL_INPUT:-\s*\$\(cat\)')
STDIN_READ = re.compile(r'=\s*\$\(cat\)|json\.load\(sys\.stdin\)|sys\.stdin\.read\(\)|</dev/stdin')

# python top-level extraction: .get('command'...) NOT chained off tool_input
PY_TOPLEVEL = re.compile(
    r"""(?<!tool_input)(?<!tool_input\}\)) *\.get\(\s*['"](%s)['"]""" % "|".join(FIELDS))

# Embedded `python3 -c '<program>'` blocks in shell hooks. A SyntaxError here
# is a SILENTLY dead hook: the standard wrapper (trap exit-0 + 2>/dev/null)
# swallows the crash and the hook no-ops forever. Found live 2026-06-11:
# stop-uncommitted-warn's auto-commit never ran once — {\"s\" if ...} backslash
# escapes inside f-string expressions are invalid in every Python version.
# The word may be spliced: 'A'\''B' means A'B — match the full splice chain,
# then collapse '\'' back to a literal quote before compiling.
EMBEDDED_PY = re.compile(r"python3?\s+-c\s+'([^']*(?:'\\''[^']*)*)'")
SPLICE = "'\\''"
# Double-quoted form: python3 -c "<program>". bash unescapes ONLY \" \\ \$ \` and a
# line-continuation (\<newline>); every other backslash stays literal, so a regex like
# \[ \d \s survives into python. Replicate exactly, else we'd false-flag valid regexes.
EMBEDDED_PY_DQ = re.compile(r'python3?\s+-c\s+"((?:[^"\\]|\\.)*)"', re.S)


def _bash_dq_unescape(s: str) -> str:
    return re.sub(r"\\([$`\"\\\n])", lambda m: "" if m.group(1) == "\n" else m.group(1), s)
# jq top-level: .command / .file_path (not .tool_input.command)
JQ_TOPLEVEL = re.compile(r"""jq[^\n]*['"][^'"]*(?<!tool_input)\.(%s)\b""" % "|".join(FIELDS))


def wired_hooks() -> set[str]:
    names: set[str] = set()
    settings = [HOME / ".claude/settings.json"] + [
        Path(p) for p in glob.glob(str(HOME / "Projects/*/.claude/settings.json"))
    ]
    settings += [Path(p) for p in glob.glob(str(HOME / ".codex/hooks.json"))]
    for s in settings:
        try:
            txt = s.read_text()
        except OSError:
            continue
        names.update(re.findall(r'hooks/([a-z0-9_-]+\.sh)', txt))
    return names


# Hooks whose payload has NO tool_input envelope — top-level field reads are correct.
# Stop / SessionEnd / SubagentStop / SessionStart / UserPromptSubmit receive a
# different shape (transcript/message/session fields at top level).
NO_TOOLINPUT_TOKENS = ("stop", "sessionend", "sessionstart", "session-start",
                       "subagent", "userprompt", "precompact", "postcompact",
                       # Task lifecycle events (TaskCreated/TaskUpdated) carry a
                       # top-level .task object, NOT a tool_input envelope — they
                       # are distinct from the TaskCreate/TaskUpdate *tools*.
                       "task-created", "taskcreated", "task-updated", "taskupdated")


def has_no_toolinput(name: str) -> bool:
    """True if this hook's event carries no tool_input (token appears in name)."""
    return any(tok in name for tok in NO_TOOLINPUT_TOKENS)


def extracts_tool_field(code: str) -> str | None:
    """Return the first tool_input field this hook tries to read, else None."""
    m = re.search(r"""\.get\(\s*['"](%s)['"]""" % "|".join(FIELDS), code)
    if m:
        return m.group(1)
    m = re.search(r"""jq[^\n]*['"][^'"]*\.(%s)\b""" % "|".join(FIELDS), code)
    if m:
        return m.group(1)
    return None


def lint_code(name: str, src: str) -> list[str]:
    """Lint a hook's source (file contents or an inline settings command)."""
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    viol: list[str] = []

    refs_env = bool(BARE_ENV.search(code))
    has_fallback = bool(ENV_FALLBACK.search(code))
    has_stdin = bool(STDIN_READ.search(code))
    if refs_env and not has_stdin and not has_fallback:
        viol.append("env-only input (CLAUDE_TOOL_* unset under Claude Code; no stdin read)")
    if re.search(r'INPUT="\$\{?CLAUDE_TOOL_INPUT\}?"', code) and not has_fallback \
            and not re.search(r'\$\(cat\)', code):
        viol.append("INPUT=$CLAUDE_TOOL_INPUT without ${CLAUDE_TOOL_INPUT:-$(cat)} fallback")

    # Top-level extraction: only meaningful for tool-input-bearing events.
    # The clean signal: the hook reads a tool field but NEVER references
    # `tool_input` — i.e. it parses the envelope's wrong level.
    # Top-level field extraction: reliable for SHELL hooks (a bare .get('command')
    # almost always means tool input). Python hooks do real data processing —
    # obj.get('url')/.get('content') on a NON-envelope object is common — so the
    # heuristic over-matches there. The precise env-var check above still covers
    # .py; field-level extraction is shell-only to stay false-positive-free.
    if not name.endswith(".py") and not has_no_toolinput(name):
        field = extracts_tool_field(code)
        if field and "tool_input" not in code:
            viol.append(
                f"reads .{field} but never references tool_input — field lives under "
                f".tool_input.{field} (Claude stdin is the full envelope)")

    # UserPromptSubmit field rename: CC 2.1.x carries the prompt in `.prompt`
    # (renamed from `.user_message` ~2026-06-16). A hook reading only the old key
    # is a SILENT no-op — it reads empty and exits, producing no output and no
    # error. Found live 2026-07-06: four UserPromptSubmit hooks (prior-context,
    # clash-capture, context-warn, continuation-guard) dead for ~3 weeks, starving
    # the prior-context front-load AND the clash-detect shadow. `user_message`
    # has no other legitimate use, so this is filename-agnostic: flag any hook that
    # reads user_message without also reading prompt (comment/docstring mentions are
    # already stripped from `code`).
    if re.search(r"user_message", code) and not re.search(
            r"""\.prompt\b|get\(\s*['"]prompt['"]|['"]\.prompt['"]|jq[^\n]*\.prompt\b""", code):
        viol.append(
            "reads .user_message but not .prompt — CC 2.1.x renamed the "
            "UserPromptSubmit field to .prompt (~2026-06-16); reading only the old "
            "name is a silent no-op (read .prompt, keep .user_message as fallback)")

    # Compile embedded python -c blocks (raw src — comment-stripping would
    # mangle python strings). Multi-line blocks only: one-liners with a
    # syntax-looking error are usually '\'' quote-splicing artifacts.
    if not name.endswith(".py"):
        progs = [m.group(1).replace(SPLICE, "'") for m in EMBEDDED_PY.finditer(src)]
        progs += [_bash_dq_unescape(m.group(1)) for m in EMBEDDED_PY_DQ.finditer(src)]
        for prog in progs:
            if prog.count("\n") < 2:
                continue
            try:
                compile(prog, name, "exec")
            except SyntaxError as e:
                viol.append(
                    f"embedded python -c block is a SyntaxError (line {e.lineno}: "
                    f"{e.msg}) — hook is silently dead under fail-open")
    return viol


def lint_file(path: Path) -> list[str]:
    return lint_code(path.name, path.read_text())


def scan_inline_settings() -> dict[str, list[str]]:
    """Lint INLINE command hooks (not file paths) in every settings.json /
    codex hooks.json — the surface the per-file lint misses."""
    results: dict[str, list[str]] = {}
    files = [HOME / ".claude/settings.json", HOME / ".codex/hooks.json"]
    files += [Path(p) for p in glob.glob(str(HOME / "Projects/*/.claude/settings.json"))]
    for s in files:
        try:
            cfg = json.loads(s.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        hooks = cfg.get("hooks", {})
        for event, blocks in (hooks.items() if isinstance(hooks, dict) else []):
            for bi, blk in enumerate(blocks if isinstance(blocks, list) else []):
                for hi, h in enumerate(blk.get("hooks", []) if isinstance(blk, dict) else []):
                    cmd = h.get("command", "") if isinstance(h, dict) else ""
                    # Only INLINE commands — a bare path is a script file (linted elsewhere).
                    if not cmd or "\n" not in cmd and "CLAUDE_TOOL" not in cmd and " " not in cmd.strip():
                        continue
                    if cmd.strip().startswith("/") or cmd.strip().startswith("~") or cmd.strip().startswith("."):
                        if "CLAUDE_TOOL" not in cmd:  # plain script path
                            continue
                    label = f"{s.name}:{event}[{bi}.{hi}]"
                    v = lint_code(f"inline-{event.lower()}-{label}", cmd)
                    if v:
                        results[label] = v
    return results


def _hook_files(base: str) -> list[str]:
    """Hook scripts (.sh + .py) under a glob base, excluding tests/backups."""
    out = []
    for ext in ("*.sh", "*.py"):
        for f in glob.glob(f"{base}/{ext}"):
            bn = os.path.basename(f)
            if bn.startswith("test_") or bn.endswith("_test.py") or ".bak" in bn:
                continue
            if bn == "lint_hook_input_contract.py":
                continue
            out.append(f)
    return sorted(out)


def per_project_hooks() -> list[str]:
    res = []
    for d in glob.glob(str(HOME / "Projects/*/.claude/hooks")):
        res += _hook_files(d)
    return sorted(res)


def global_hooks() -> list[str]:
    """Hook scripts under ~/.claude/hooks — the GLOBAL inline-hooks dir, wired
    in ~/.claude/settings.json and loaded in every project. Neither the skills
    glob nor the per-project glob (~/Projects/*/.claude/hooks) reaches it, so a
    contract-dead hook here is invisible to --surfaces. Found live 2026-06-12:
    posttool-unsourced-claim-check.sh read bare $CLAUDE_TOOL_INPUT → no-op
    under Claude for an unknown duration."""
    return _hook_files(str(HOME / ".claude/hooks"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="lint every *.sh, not just wired")
    ap.add_argument("--surfaces", action="store_true",
                    help="cross-surface scan: skills + per-project hooks + inline settings")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("files", nargs="*", help="specific hook files to lint (for pre-commit gates)")
    args = ap.parse_args()

    if args.files:
        targets = [f for f in args.files if f.endswith((".sh", ".py"))]
    elif args.surfaces:
        targets = _hook_files(str(HOOKS_DIR)) + per_project_hooks() + global_hooks()
    else:
        targets = _hook_files(str(HOOKS_DIR))
    wired = wired_hooks()
    results: dict[str, list[str]] = {}
    for t in targets:
        name = os.path.basename(t)
        if not args.files and not args.all and not args.surfaces and name not in wired:
            continue
        if not Path(t).exists():
            continue
        v = lint_file(Path(t))
        if v:
            results[name if not args.surfaces else t.replace(str(HOME), "~")] = v

    if args.surfaces:
        results.update(scan_inline_settings())

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("✓ hook input contract: all clean")
        else:
            print(f"✗ hook input contract: {len(results)} hook(s) violate the stdin/.tool_input contract\n")
            for name, v in sorted(results.items()):
                print(f"  {name}")
                for item in v:
                    print(f"      └─ {item}")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
