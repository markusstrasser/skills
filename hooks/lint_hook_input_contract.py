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
BARE_ENV = re.compile(r'\$\{?CLAUDE_TOOL_(INPUT|NAME)\b')
ENV_FALLBACK = re.compile(r'CLAUDE_TOOL_INPUT:-\s*\$\(cat\)')
STDIN_READ = re.compile(r'=\s*\$\(cat\)|json\.load\(sys\.stdin\)|sys\.stdin\.read\(\)|</dev/stdin')

# python top-level extraction: .get('command'...) NOT chained off tool_input
PY_TOPLEVEL = re.compile(
    r"""(?<!tool_input)(?<!tool_input\}\)) *\.get\(\s*['"](%s)['"]""" % "|".join(FIELDS))
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
NO_TOOLINPUT_PREFIX = ("stop-", "sessionend-", "sessionstart-", "session-start-",
                       "subagent-", "userprompt-", "precompact-", "postcompact-")


def extracts_tool_field(code: str) -> str | None:
    """Return the first tool_input field this hook tries to read, else None."""
    m = re.search(r"""\.get\(\s*['"](%s)['"]""" % "|".join(FIELDS), code)
    if m:
        return m.group(1)
    m = re.search(r"""jq[^\n]*['"][^'"]*\.(%s)\b""" % "|".join(FIELDS), code)
    if m:
        return m.group(1)
    return None


def lint_file(path: Path) -> list[str]:
    name = path.name
    src = path.read_text()
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
    if not name.startswith(NO_TOOLINPUT_PREFIX):
        field = extracts_tool_field(code)
        if field and "tool_input" not in code:
            viol.append(
                f"reads .{field} but never references tool_input — field lives under "
                f".tool_input.{field} (Claude stdin is the full envelope)")
    return viol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="lint every *.sh, not just wired")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("files", nargs="*", help="specific hook files to lint (for pre-commit gates)")
    args = ap.parse_args()

    if args.files:
        targets = [f for f in args.files if f.endswith(".sh")]
    else:
        targets = sorted(glob.glob(str(HOOKS_DIR / "*.sh")))
    wired = wired_hooks()
    results: dict[str, list[str]] = {}
    for t in targets:
        name = os.path.basename(t)
        if not args.files and not args.all and name not in wired:
            continue
        if not Path(t).exists():
            continue
        v = lint_file(Path(t))
        if v:
            results[name] = v

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
