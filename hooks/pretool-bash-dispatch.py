#!/usr/bin/env python3
"""pretool-bash-dispatch.py — ONE in-process dispatcher for the ~28 formerly-
separate PreToolUse(Bash) safety gates on matcher="Bash" in ~/.claude/settings.json.

Each gate used to be its own settings.json PreToolUse entry: 28 gates spawning
28 subprocesses (bash + inline python3 for most) on EVERY Bash tool call — the
dominant global latency tax. This dispatcher reads the stdin envelope ONCE and
runs every gate in-process (or, for a small named subset, as a single
subprocess call passing the already-read envelope — see SUBPROCESS_KEPT
below), in the EXACT settings.json order, preserving:

  1. Block/pass verdicts, byte-for-byte block messages.
  2. Mutator (updatedInput) rewrites — see "Mutator chaining" below.
  3. Every "if": "Bash(<glob>)" per-hook condition from settings.json — Claude
     Code itself only invokes a subset of these 28 hooks depending on whether
     the command matches a glob (git* / git commit*); 7 of 28 entries carry
     this condition. Skipping a gate whose `if` doesn't match is NOT a
     shortcut — it is the ORIGINAL behavior (Claude Code never spawned that
     hook's process for a non-matching command either). See _if_matches().
  4. Fail-open uniformly: any unexpected internal error in a ported gate
     exits that gate 0 (pass), never blocks a tool call as a side effect of a
     dispatcher bug.
  5. Fail-fast on first BLOCK (exit 2): stops immediately, propagates that
     gate's exact stderr/stdout message, same as "Claude Code would never
     have invoked hook #9 if hook #3 already blocked."
  6. All advisory (additionalContext) output across every passing gate is
     accumulated and emitted as ONE merged blob at the end (only one
     additionalContext blob is meaningful per hook invocation).

Mutator chaining
-----------------
5 of the 28 gates rewrite tool_input.command via the PreToolUse `updatedInput`
contract: pretool-git-noext-inject.sh, pretool-pyunbuffered-inject.sh,
pretool-uv-python-guard.py, pretool-arc-agi-agent-cwd-guard.py,
pretool-emb-project-guard.py, pretool-bare-modal-guard.py. Two of these are
adjacent in settings.json order (uv-python-guard at position 11,
arc-agi-agent-cwd-guard at position 13) and arc-agi-agent-cwd-guard's OWN
selftest encodes an explicit assumption that it runs AFTER uv-python-guard's
rewrite has already landed — its selftest has a case literally commented
"# bare python with import -> block (uv-guard should rewrite first)": a bare
`python3 -c "import arcengine"` (no `uv run` yet) verdicts to BLOCK, not
REWRITE, because _insert_directory() requires `uv run` to already be present
in the command to insert `--directory agent` into. For arc-agi-agent-cwd-guard
to ever reach its REWRITE branch on a bare-python arc-agi command, it must see
uv-python-guard's rewritten command, not the original. emb-project-guard is
the same shape for `blindspot_miner` / `emb.embed` → `--project ~/Projects/emb`.
This dispatcher therefore CHAINS mutations: each gate (native, ported, or
subprocess) is fed the CURRENT (possibly already-rewritten) envelope, and a
mutation updates that running envelope before the next gate runs. This was not
independently verified against a Claude Code release note
(none found in this repo) — it is the only interpretation consistent with how
the two adjacent gates were authored. If live Claude Code does NOT chain
hook mutations, the current un-consolidated 28-hook fleet already has this
latent bug independent of consolidation; this dispatcher's chained behavior
is a strict improvement either way.

Bash-vs-Python port classification (report this table on delivery)
--------------------------------------------------------------------
NATIVE  (zero-edit importable — already .py with a stdin-JSON `main()`):
  pretool-bash-background-ampersand.py, pretool-bg-dispatch-footgun.py,
  pretool-uv-python-guard.py, pretool-genomics-pythonpath-guard.py,
  pretool-arc-agi-agent-cwd-guard.py, pretool-emb-project-guard.py,
  pretool-bare-modal-guard.py, pretool-cursor-model-guard.py      (8 gates)

PORTED  (bash driver + embedded logic transcribed into Python; sidecar .py
  files are imported directly where they already exist):
  pretool-git-noext-inject.sh, pretool-pyunbuffered-inject.sh,
  pretool-git-add-all-guard.sh, pretool-bash-loop-guard.sh (imports
  pretool_bash_loop_guard), pretool-bash-cat-guard.sh (imports
  pretool_bash_cat_guard), pretool-noext-nongit-guard.sh,
  pretool-heavy-load-guard.sh, pretool-no-background-commit.sh (imports
  pretool_no_background_commit), pretool-duckdb-quote-guard.sh,
  ~/.claude/hooks/pretool-modal-cost-guard.sh,
  ~/.claude/hooks/pretool-modal-script-audit.sh, pretool-cost-guard.sh,
  pretool-cost-awareness.sh, pretool-ast-precommit.sh,
  pretool-commit-check.sh (imports commit-check-parse),
  pretool-modal-run-guard.sh, pretool-timeout-modal-guard.sh,
  pretool-plan-protect.sh                                        (18 gates)

SUBPROCESS-KEPT  (complex bash-native control flow, external sidecar-process
  dependencies, or git-mutating side effects — porting risked drift; kept as
  a literal subprocess call receiving the CURRENT envelope on stdin, same
  as before minus the outer jq/bash double-parse this dispatcher replaces):
  pretool-multiagent-commit-guard.sh   (BASH_REMATCH parsing + calls
                                         peer-session-count.sh, which itself
                                         shells out to lsof/pgrep/ps — porting
                                         this control flow risked silent
                                         drift on a safety-critical guard)
  pretool-destructive-git-ref.sh       (creates real git backup refs as a
                                         side effect before a destructive op —
                                         kept as literal subprocess so the
                                         git-mutating behavior is byte-for-byte
                                         the original, not a reimplementation)
  precommit-plan-completion-guard.sh   (bash loop over `git diff --cached`
                                         output; low-frequency git-commit-only
                                         gate, kept for time/risk budget)
                                                                    (3 gates)

Total: 7 + 18 + 3 = 28.

Fail-open safety net: every gate call (native, ported, subprocess) is wrapped
so an uncaught exception in gate logic exits that gate 0 (pass) rather than
crashing the dispatcher or blocking the tool call.
"""

from __future__ import annotations

import ast
import bisect
import collections
import fnmatch
import importlib.util
import io
import json
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Callable, NamedTuple

HOOKS_DIR = Path(__file__).resolve().parent
GLOBAL_HOOKS_DIR = Path.home() / ".claude" / "hooks"
TRIGGER_LOG = str(HOOKS_DIR / "hook-trigger-log.sh")


class GateResult(NamedTuple):
    code: int
    stderr: str
    stdout: str


def _log_trigger(hook: str, action: str, detail: str, cmd: str = "") -> None:
    """Fire-and-forget telemetry — mirrors each gate's own
    `~/Projects/skills/hooks/hook-trigger-log.sh "$name" "$action" "$detail" "$cmd"`
    call. Never affects gate behavior. `cmd` (optional, 2026-07-18) is
    fingerprinted by hook-trigger-log.sh into cmd_tok/cmd_fp — the RAW
    command is never persisted, only the two derived fields (see
    hook_cmd_fingerprint.py). Omit `cmd` for fires that aren't
    command-shaped (e.g. cost-awareness, which fires on a call counter, not
    on any one command)."""
    try:
        subprocess.run(
            [TRIGGER_LOG, hook, action, detail, cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────
# "if": "Bash(<glob>)" per-hook condition (7 of 28 entries carry this in
# settings.json). Only observed shapes are "Bash(git*)" and
# "Bash(git commit*)"; an unrecognized shape fails open to RUNNING the gate
# (skipping a safety gate is the worse failure mode).
# ─────────────────────────────────────────────────────────────────────────

_IF_RE = re.compile(r"^Bash\((.*)\)$")


_IF_SEGMENT_RE = re.compile(r"&&|\|\||;|\||\n")
_IF_COMMAND_PREFIX_RE = re.compile(r"^(?:(?:[A-Za-z_][A-Za-z0-9_]*=\S*)|!|time|command|exec)\s+")


def _strip_if_command_prefixes(segment: str) -> str:
    """Expose a command behind assignment and shell prefix words to glob matching."""
    view = segment.strip()
    while match := _IF_COMMAND_PREFIX_RE.match(view):
        view = view[match.end() :]
    return view


def _if_matches(if_pattern: str | None, cmd: str) -> bool:
    """Match a gate predicate against every COMMAND POSITION, not just the string start.

    `Bash(git*)` used to fnmatch the whole lstripped command, so a gate fired on
    `git add -A` and was silently skipped on `cd /repo; git add -A`. Every
    git-predicated gate inherited that hole — including the `git add -A` ban, the
    destructive-ref guard, the multiagent-commit guard, and the masked-commit
    guard — and `cd <repo>; git ...` is the DOMINANT phrasing for any agent using
    absolute paths. Demonstrated 2026-08-18 (genomics): `git add -A --dry-run`
    blocked; `cd /repo; git add -A --dry-run` ran unblocked.

    The gates themselves already segment and match precisely (see
    gate_git_add_all_guard), so widening the predicate restores their intended
    reach rather than making them coarser.

    Heredoc bodies AND quoted strings are stripped before segmenting. Splitting on
    newlines/;/&& would otherwise expose DATA as a command position — the
    2026-07-04 false-positive class (a brief containing "git commit" blocking the
    write that would have created it). Caught during this very change: a test
    command carrying 'git add -A' inside a quoted argument tripped the add-all ban
    until strip_quoted was applied here too.
    """
    if not if_pattern:
        return True
    m = _IF_RE.match(if_pattern)
    if not m:
        return True
    glob = m.group(1)
    text = cmd or ""
    if fnmatch.fnmatchcase(text.lstrip(), glob):
        return True
    try:
        from lib_bash_cmd_strip import strip_heredocs, strip_quoted

        text = strip_quoted(strip_heredocs(text))
    except Exception:  # fallback-ok — a missing stripper must not disable gating
        pass
    return any(
        fnmatch.fnmatchcase(_strip_if_command_prefixes(segment), glob)
        for segment in _IF_SEGMENT_RE.split(text)
    )


def _jqlike_cmd(data: dict) -> str:
    """Mirrors `(if has("tool_input") then (.tool_input // {}) else . end) |
    .command // ""` — the extraction several gates use (tolerates the flat
    legacy envelope shape as well as the nested tool_input shape)."""
    if not isinstance(data, dict):
        return ""
    if "tool_input" in data:
        ti = data.get("tool_input") or {}
        return (ti.get("command") or "") if isinstance(ti, dict) else ""
    return data.get("command") or ""


# ─────────────────────────────────────────────────────────────────────────
# NATIVE gates — zero-edit import of on-disk .py files that already expose a
# stdin-JSON `main()`. Runs the file's real, unmodified main() in-process by
# swapping sys.stdin, mirroring intel's pretool_writeedit_dispatch.py
# _run_entry pattern exactly.
# ─────────────────────────────────────────────────────────────────────────

_module_cache: dict[str, object] = {}


def _load_module(path: Path, mod_name: str):
    if mod_name in _module_cache:
        return _module_cache[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    _module_cache[mod_name] = mod
    return mod


def _run_entry(entry: Callable[[], object], raw_payload: str) -> GateResult:
    old_stdin, old_argv = sys.stdin, sys.argv
    sys.stdin = io.StringIO(raw_payload)
    sys.argv = old_argv[:1]
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            result = entry()
        if isinstance(result, int):
            code = result
    except SystemExit as e:
        c = e.code
        code = c if isinstance(c, int) else (0 if c is None else 1)
    except Exception:
        code = 0  # fail-open — mirrors every native gate's own try/except
    finally:
        sys.stdin, sys.argv = old_stdin, old_argv
    return GateResult(code, buf_err.getvalue(), buf_out.getvalue())


def make_native_gate(rel_path: str, mod_name: str, base: Path = HOOKS_DIR):
    path = base / rel_path

    def run(raw_payload: str) -> GateResult:
        try:
            mod = _load_module(path, mod_name)
            return _run_entry(mod.main, raw_payload)
        except Exception:
            return GateResult(0, "", "")

    return run


# ─────────────────────────────────────────────────────────────────────────
# PORTED gates — hand-transcribed from the bash driver + embedded python.
# Each exposes a `run(raw_payload: str) -> GateResult` matching the exact
# stdout/stderr/exit-code shape the original bash script produced.
# ─────────────────────────────────────────────────────────────────────────

# --- 1. pretool-git-noext-inject.sh (MUTATOR, no if) -----------------------


def _after_heredoc_bodies(command: str, start: int, delimiters: list[tuple[str, bool]]) -> int:
    """Return the offset after sequential, exactly matched heredoc terminators."""
    cursor = start
    for delimiter, strip_tabs in delimiters:
        while cursor < len(command):
            line_end = command.find("\n", cursor)
            if line_end < 0:
                line_end = len(command)
            line = command[cursor:line_end]
            candidate = line.lstrip("\t") if strip_tabs else line
            if candidate == delimiter:
                cursor = min(line_end + 1, len(command))
                break
            cursor = min(line_end + 1, len(command))
    return cursor


def _is_shell_redirection_fd(raw: str) -> bool:
    """Return whether a raw word is a numeric or Bash dynamic-FD prefix."""
    return raw.isdigit() or bool(re.fullmatch(r"\{[A-Za-z_][A-Za-z0-9_]*\}", raw))


def _shell_heredoc_declaration(command: str, start: int) -> tuple[int, str, bool] | None:
    """Parse one heredoc operator as ``(end, delimiter, strip_tabs)``."""
    if command[start : start + 2] != "<<" or command[start : start + 3] == "<<<":
        return None
    delimiter_start = start + 2
    strip_tabs = command[delimiter_start : delimiter_start + 1] == "-"
    if strip_tabs:
        delimiter_start += 1
    while command[delimiter_start : delimiter_start + 1] in (" ", "\t"):
        delimiter_start += 1
    delimiter_token = next(_iter_shell_syntax(command[delimiter_start:]), None)
    if delimiter_token is None or delimiter_token[0] != "word":
        return None
    raw_delimiter, relative_start, relative_end = delimiter_token[1:]
    if relative_start != 0:
        return None
    delimiter_parts = shlex.split(raw_delimiter, comments=False, posix=True)
    if len(delimiter_parts) != 1:
        return None
    return delimiter_start + relative_end, delimiter_parts[0], strip_tabs


def _shell_expansion_end(command: str, start: int) -> int:
    """Return the end of one balanced opaque shell expansion.

    Parameter and command substitutions can contain shell separators that do
    not delimit the surrounding command.  Scan their balanced braces or
    parentheses without yielding internal syntax.  Legacy backticks are
    similarly opaque.  Any missing closer or quote raises ``ValueError`` so
    the caller fails open for the whole command.
    """
    if command.startswith("${", start):
        kind = "parameter"
        closer = "}"
        i = start + 2
    elif command.startswith("$((", start):
        kind = "arithmetic"
        closer = ")"
        i = start + 2
    elif command.startswith("$(", start):
        kind = "command"
        closer = ")"
        i = start + 2
    elif command.startswith("`", start):
        kind = "backtick"
        closer = "`"
        i = start + 1
    else:
        raise ValueError("not a shell expansion")

    if kind == "backtick":
        while i < len(command):
            if command[i] == "\\":
                if i + 1 >= len(command):
                    raise ValueError("unbalanced shell expansion")
                i += 2
                continue
            if command[i] == closer:
                return i + 1
            if command.startswith("${", i) or command.startswith("$(", i):
                i = _shell_expansion_end(command, i)
                continue
            i += 1
        raise ValueError("unbalanced shell expansion")

    depth = 1
    quote: str | None = None
    at_word_start = True
    pending_heredocs: list[tuple[str, bool]] = []
    while i < len(command):
        ch = command[i]
        if quote == "'":
            if ch == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if ch == "\\":
                if i + 1 >= len(command):
                    raise ValueError("unbalanced shell expansion")
                i += 2
                continue
            if ch == '"':
                quote = None
                i += 1
                continue
            if command.startswith("${", i) or command.startswith("$(", i):
                i = _shell_expansion_end(command, i)
                continue
            if ch == "`":
                i = _shell_expansion_end(command, i)
                continue
            i += 1
            continue
        if kind == "command" and ch == "#" and at_word_start:
            line_end = command.find("\n", i)
            if line_end < 0:
                raise ValueError("unbalanced shell expansion")
            i = line_end
            continue
        if kind == "command":
            heredoc = _shell_heredoc_declaration(command, i)
            if heredoc is not None:
                delimiter_end, delimiter, strip_tabs = heredoc
                pending_heredocs.append((delimiter, strip_tabs))
                at_word_start = False
                i = delimiter_end
                continue
            if ch == "\n":
                i += 1
                if pending_heredocs:
                    i = _after_heredoc_bodies(command, i, pending_heredocs)
                    pending_heredocs.clear()
                at_word_start = True
                continue
        if ch == "\\":
            if i + 1 >= len(command):
                raise ValueError("unbalanced shell expansion")
            at_word_start = False
            i += 2
            continue
        if ch in ("'", '"'):
            quote = ch
            at_word_start = False
            i += 1
            continue
        if command.startswith("${", i) or command.startswith("$(", i):
            i = _shell_expansion_end(command, i)
            at_word_start = False
            continue
        if ch == "`":
            i = _shell_expansion_end(command, i)
            at_word_start = False
            continue
        if kind == "parameter" and ch == "{":
            depth += 1
        elif kind in {"arithmetic", "command"} and ch == "(":
            depth += 1
        elif ch == closer:
            if pending_heredocs:
                raise ValueError("unbalanced shell heredoc")
            depth -= 1
            if depth == 0:
                return i + 1
        if kind == "command":
            if ch.isspace() or ch in ";|&()":
                at_word_start = True
            else:
                at_word_start = False
        i += 1
    raise ValueError("unbalanced shell expansion")


def _iter_shell_syntax(command: str):
    """Lex raw word and separator spans without normalizing any shell bytes.

    Both segment discovery and git-word discovery consume this one scanner, so
    their quote and backslash rules cannot drift.  Words retain their original
    quoting. Separators are ``;``, ``&&``, ``||``, ``|``, standalone ``&``, and
    newline. Redirection forms such as ``2>&1``, ``&>``, and ``|&`` are classified
    before standalone ``&``. Comments, heredoc bodies, parameter expansions,
    command substitutions, and backticks are opaque. Unbalanced quoting or
    expansion raises ``ValueError`` so the mutator fails open for the whole command.
    """
    redirection_operators = (
        "<<<",
        "&>>",
        ">>",
        "<>",
        ">|",
        ">&",
        "<&",
        "&>",
        "<<",
        ">",
        "<",
    )
    word_start: int | None = None
    redirect_target = False
    quote: str | None = None
    escaped = False
    pending_heredocs: list[tuple[str, bool]] = []
    i = 0
    while i < len(command):
        ch = command[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if quote == "'":
            if ch == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if ch == "\\":
                escaped = True
            elif command.startswith("${", i) or command.startswith("$(", i):
                i = _shell_expansion_end(command, i)
                continue
            elif ch == "`":
                i = _shell_expansion_end(command, i)
                continue
            elif ch == '"':
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            if word_start is None:
                word_start = i
            quote = ch
            i += 1
            continue
        if ch == "\\":
            if word_start is None:
                word_start = i
            escaped = True
            i += 1
            continue
        if command.startswith("${", i) or command.startswith("$(", i) or ch == "`":
            if word_start is None:
                word_start = i
            i = _shell_expansion_end(command, i)
            continue

        if ch == "#" and word_start is None:
            redirect_target = False
            line_end = command.find("\n", i)
            if line_end < 0:
                i = len(command)
                break
            separator_end = line_end + 1
            if pending_heredocs:
                separator_end = _after_heredoc_bodies(command, separator_end, pending_heredocs)
                pending_heredocs.clear()
            yield "separator", command[line_end:separator_end], line_end, separator_end
            i = separator_end
            continue
        heredoc = _shell_heredoc_declaration(command, i)
        if heredoc is not None:
            if word_start is not None:
                raw = command[word_start:i]
                kind = "redirect" if redirect_target or _is_shell_redirection_fd(raw) else "word"
                yield kind, raw, word_start, i
                word_start = None
                redirect_target = False
            delimiter_end, delimiter, strip_tabs = heredoc
            yield "redirect", command[i:delimiter_end], i, delimiter_end
            pending_heredocs.append((delimiter, strip_tabs))
            i = delimiter_end
            continue

        redirection = next((op for op in redirection_operators if command.startswith(op, i)), None)
        if redirection is not None:
            if word_start is not None:
                raw = command[word_start:i]
                kind = "redirect" if redirect_target or _is_shell_redirection_fd(raw) else "word"
                yield kind, raw, word_start, i
                word_start = None
                redirect_target = False
            redirection_end = i + len(redirection)
            yield "redirect", command[i:redirection_end], i, redirection_end
            redirect_target = True
            i = redirection_end
            continue

        if ch in "()":
            if word_start is not None:
                raw = command[word_start:i]
                kind = "redirect" if redirect_target else "word"
                yield kind, raw, word_start, i
                word_start = None
                redirect_target = False
            yield "structure", ch, i, i + 1
            i += 1
            continue

        separator_len = 0
        if ch in (";", "\n"):
            separator_len = 1
        elif ch == "|":
            separator_len = 2 if command[i : i + 2] in ("||", "|&") else 1
        elif ch == "&":
            separator_len = 2 if command[i : i + 2] == "&&" else 1
        if separator_len:
            if word_start is not None:
                raw = command[word_start:i]
                kind = "redirect" if redirect_target else "word"
                yield kind, raw, word_start, i
                word_start = None
            redirect_target = False
            separator_end = i + separator_len
            if ch == "\n" and pending_heredocs:
                separator_end = _after_heredoc_bodies(command, separator_end, pending_heredocs)
                pending_heredocs.clear()
            yield "separator", command[i:separator_end], i, separator_end
            i = separator_end
            continue
        if ch.isspace():
            if word_start is not None:
                raw = command[word_start:i]
                kind = "redirect" if redirect_target else "word"
                yield kind, raw, word_start, i
                word_start = None
                redirect_target = False
            i += 1
            continue
        if word_start is None:
            word_start = i
        i += 1

    if quote is not None or escaped:
        raise ValueError("unbalanced shell quoting")
    if word_start is not None:
        kind = "redirect" if redirect_target else "word"
        yield kind, command[word_start:], word_start, len(command)
        redirect_target = False
    if redirect_target:
        raise ValueError("incomplete shell redirection")


def _iter_shell_segments(command: str):
    """Yield raw ``(text, start, end)`` spans between scanned separators."""
    start = 0
    for kind, _raw, token_start, token_end in _iter_shell_syntax(command):
        if kind != "separator":
            continue
        yield command[start:token_start], start, token_start
        start = token_end
    yield command[start:], start, len(command)


_SHELL_COMPLEX_COMMAND_WORDS = {
    "{",
    "}",
    "case",
    "do",
    "done",
    "elif",
    "else",
    "esac",
    "fi",
    "for",
    "function",
    "if",
    "in",
    "select",
    "then",
    "until",
    "while",
}


def _git_noext_has_complex_shell(command: str) -> bool:
    """Reject grouped/compound grammar before separators expose nested git words."""
    command_start = True
    for kind, raw, _start, _end in _iter_shell_syntax(command):
        if kind == "structure":
            return True
        if kind == "separator":
            command_start = True
            continue
        if kind != "word" or not command_start:
            continue
        if raw in {"!", "time", "command", "exec"} or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", raw):
            continue
        if raw in _SHELL_COMPLEX_COMMAND_WORDS:
            return True
        command_start = False
    return False


def _shlex_unquote_word(raw: str) -> str | None:
    """Normalize one scanner word for classification, never for re-emission.

    ``shlex`` does not understand unquoted shell substitutions, so a scanner
    word such as ``$(printf '%s' a)`` can appear to contain multiple tokens.
    Such a word is not classifiable here; callers leave that segment alone.
    """
    try:
        parts = shlex.split(raw, comments=False, posix=True)
    except ValueError:
        return None
    if len(parts) != 1:
        return None
    return parts[0]


def _git_noext_command_index(words: list[tuple[str, int, int]]) -> int | None:
    """Skip assignments plus supported shell prefix words and their options."""
    i = 0
    while i < len(words):
        value = _shlex_unquote_word(words[i][0])
        if value is None:
            return None
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", value):
            i += 1
            continue
        if value == "!":
            i += 1
            continue
        if value == "time":
            i += 1
            next_value = _shlex_unquote_word(words[i][0]) if i < len(words) else None
            if next_value == "-p":
                i += 1
            continue
        if value == "command":
            i += 1
            while i < len(words):
                next_value = _shlex_unquote_word(words[i][0])
                if next_value in {"-v", "-V"}:
                    return None
                if next_value != "-p":
                    break
                i += 1
            continue
        if value == "exec":
            i += 1
            if i < len(words) and _shlex_unquote_word(words[i][0]) == "-a":
                i += 1
                if i >= len(words):
                    return i
                i += 1
            continue
        return i
    return i


def _git_noext_rewrite_segment(segment: str) -> str | None:
    """Insert safety flags at raw word offsets, preserving every existing byte."""
    words = [
        (raw, start, end) for kind, raw, start, end in _iter_shell_syntax(segment) if kind == "word"
    ]
    git_index = _git_noext_command_index(words)
    if (
        git_index is None
        or git_index >= len(words)
        or _shlex_unquote_word(words[git_index][0]) != "git"
    ):
        return None
    i = git_index + 1
    has_no_pager = False
    while i < len(words):
        value = _shlex_unquote_word(words[i][0])
        if value is None:
            return None
        if not value.startswith("-"):
            break
        if value == "--":
            return None
        has_no_pager = has_no_pager or value == "--no-pager"
        i += 2 if value in ("-C", "-c") else 1
    if i >= len(words):
        return None
    subcmd = _shlex_unquote_word(words[i][0])
    subcmd_end = words[i][2]
    if subcmd not in ("diff", "show", "log"):
        return None
    has_no_ext_diff = False
    for raw, _start, _end in words[i + 1 :]:
        value = _shlex_unquote_word(raw)
        if value == "--":
            break
        if value == "--no-ext-diff":
            has_no_ext_diff = True
            break
    if has_no_pager and has_no_ext_diff:
        return None

    insertions: list[tuple[int, str]] = []
    if not has_no_pager:
        insertions.append((words[i - 1][2], " --no-pager"))
    if not has_no_ext_diff:
        insertions.append((subcmd_end, " --no-ext-diff"))
    rewritten = segment
    for offset, text in reversed(insertions):
        rewritten = rewritten[:offset] + text + rewritten[offset:]
    return rewritten


def _git_noext_inject_verdict(ti: dict) -> tuple[str, str]:
    cmd = ti.get("command", "") or ""
    if not cmd:
        return "pass", ""
    replacements: list[tuple[int, int, str]] = []
    try:
        if _git_noext_has_complex_shell(cmd):
            return "pass", ""
        segments = list(_iter_shell_segments(cmd))
        for segment, start, end in segments:
            rewritten = _git_noext_rewrite_segment(segment)
            if rewritten is not None:
                replacements.append((start, end, rewritten))
    except ValueError:
        return "pass", ""
    if not replacements:
        return "pass", ""
    pieces: list[str] = []
    cursor = 0
    for start, end, rewritten in replacements:
        pieces.extend((cmd[cursor:start], rewritten))
        cursor = end
    pieces.append(cmd[cursor:])
    return "mutate", "".join(pieces)


def gate_git_noext_inject(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    ti = data.get("tool_input") or {}
    kind, val = _git_noext_inject_verdict(ti)
    if kind != "mutate":
        return GateResult(0, "", "")
    updated = dict(ti)
    updated["command"] = val
    _log_trigger("git-noext-inject", "rewrite", "git diff/show/log", ti.get("command", "") or "")
    out = json.dumps(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}}
    )
    return GateResult(0, "", out)


# --- 2. pretool-pyunbuffered-inject.sh (MUTATOR, no if) --------------------


def _pyunbuffered_verdict(ti: dict) -> tuple[str, str]:
    cmd = ti.get("command", "") or ""
    if not cmd:
        return "pass", ""
    if not ti.get("run_in_background"):
        return "pass", ""
    if "PYTHONUNBUFFERED" in cmd or re.search(r"\bpython3?\s+-u\b", cmd):
        return "pass", ""
    if not re.search(r"\bpython3?\b", cmd):
        return "pass", ""
    return "mutate", "export PYTHONUNBUFFERED=1; " + cmd


def gate_pyunbuffered_inject(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    ti = data.get("tool_input") or {}
    kind, val = _pyunbuffered_verdict(ti)
    if kind != "mutate":
        return GateResult(0, "", "")
    updated = dict(ti)
    updated["command"] = val
    _log_trigger("pyunbuffered-inject", "rewrite", "bg python", ti.get("command", "") or "")
    out = json.dumps(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}}
    )
    return GateResult(0, "", out)


# --- 2b. bg-buffering-pipe guard (WARNER) ----------------------------------
# A background command whose FINAL segment pipes through tail/head/grep loses
# output: tail buffers until EOF (a reap swallows everything) and grep block-
# buffers to pipes (results arrive scrambled at exit). Bit 2x on 2026-08-10
# (genomics storage reclaim) despite the written wakeup-cadence rule — pair-
# rule promoted to a hook. Redirect the full stream to a log; filter at READ.

_BUFFERING_TAIL_RE = re.compile(
    r"\|\s*(tail|head)\s+-?\w*\s*$|\|\s*grep\s+(?!.*--line-buffered)[^|]*$"
)


def gate_bg_buffering_pipe(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    ti = data.get("tool_input") or {}
    cmd = (ti.get("command", "") or "").strip()
    if not cmd or not ti.get("run_in_background"):
        return GateResult(0, "", "")
    # Only the final pipeline segment matters; ignore redirected-to-file forms.
    last_line = cmd.splitlines()[-1]
    if ">" in last_line.split("|")[-1]:
        return GateResult(0, "", "")
    if _BUFFERING_TAIL_RE.search(last_line):
        _log_trigger("bg-buffering-pipe", "warn", "buffered filter on bg output", cmd)
        return GateResult(
            0,
            "",
            "[bg-buffering-pipe] WARNING: run_in_background output piped through tail/head/grep "
            "— tail buffers until EOF (a reap swallows ALL output) and grep block-buffers "
            "(output arrives scrambled at exit). Redirect the FULL stream to a log file and "
            "filter when reading, or add --line-buffered to grep.\n",
        )
    return GateResult(0, "", "")


# --- 3. pretool-git-add-all-guard.sh (BLOCKER, if=Bash(git*)) -------------


def _git_add_all_offends(seg: str) -> bool:
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        return bool(
            re.match(r"(?:[A-Za-z_]\w*=\S+\s+)*git\s+add\b.*(\s-A\b|\s--all\b|\s\.(\s|$))", seg)
        )
    i = 0
    while i < len(parts) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", parts[i]):
        i += 1
    if i >= len(parts) or parts[i] != "git":
        return False
    j = i + 1
    while j < len(parts) and parts[j].startswith("-"):
        j += 2 if parts[j] in ("-C", "-c") else 1
    if j >= len(parts) or parts[j] != "add":
        return False
    for a in parts[j + 1 :]:
        if a in ("-A", "--all", "."):
            return True
        if re.fullmatch(r"-[A-Za-z]*A[A-Za-z]*", a):
            return True
    return False


def gate_git_add_all_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd or "add" not in cmd:
        return GateResult(0, "", "")
    segments = re.split(r"&&|\|\||;|\||\n", cmd)
    if not any(_git_add_all_offends(s) for s in segments):
        return GateResult(0, "", "")
    msg = (
        "BLOCK: `git add -A` / `git add .` / `git add --all` are banned "
        "(global <git_rules>) — they sweep in untracked scratch/temp files. "
        "Stage specific files (`git add path/to/file`) or use `git add -p`.\n"
    )
    _log_trigger("git-add-all-guard", "block", cmd[:80], cmd)
    return GateResult(2, msg, "")


# --- 4. multiline zsh syntax preflight (BLOCKER, no if) — imports sidecar -


def gate_bash_loop_guard(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(HOOKS_DIR / "pretool_bash_loop_guard.py", "pretool_bash_loop_guard")
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd:
            return GateResult(0, "", "")
        error = mod.syntax_error(cmd)
        if error:
            msg = (
                "BLOCKED: Command fails zsh syntax preflight:\n"
                f"{error}\n"
                "Complete the control structure (for example, add the missing done/fi).\n"
            )
            return GateResult(2, msg, "")
        return GateResult(0, "", "")
    except Exception:
        return GateResult(0, "", "")


# --- 4b. bash-backtick-guard (BLOCKER, no if) — imports sidecar ------------
# Markdown `inline code` inside a double-quoted data field is executed by the shell and the
# span is silently deleted. 5 incidents / 4 sessions / 3 weeks before this guard existed; the
# hook is the only layer that still holds the un-expanded text (see sidecar docstring).


def gate_bash_backtick_guard(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(
            HOOKS_DIR / "pretool_bash_backtick_guard.py", "pretool_bash_backtick_guard"
        )
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd or "`" not in cmd:
            return GateResult(0, "", "")
        flag = mod.offending_flag(cmd)
        if flag:
            return GateResult(2, mod.reason(flag), "")
        return GateResult(0, "", "")
    except Exception:
        return GateResult(0, "", "")


# --- 4c. approval-held-guard (BLOCKER, no if) — imports sidecar ------------
# Claude Code asks for approval on `${(f)x}`-style flag groups and on recursive rm targets it
# cannot prove safe, even under bypassPermissions; a background teammate cannot answer and
# its call hangs (sidecar docstring, 2026-10-27).


def gate_approval_held_guard(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(
            HOOKS_DIR / "pretool_bash_approval_held_guard.py", "pretool_bash_approval_held_guard"
        )
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd or ("${(" not in cmd and "rm" not in cmd):
            return GateResult(0, "", "")
        hit = mod.offending(cmd)
        if hit:
            return GateResult(2, mod.reason(hit), "")
        return GateResult(0, "", "")
    except Exception:
        return GateResult(0, "", "")


# --- 5. pretool-bash-cat-guard.sh (BLOCKER, no if) — imports sidecar -------


def gate_bash_cat_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd or not re.search(r"\$\(\s*cat\s", cmd):
            return GateResult(0, "", "")
        mod = _load_module(HOOKS_DIR / "pretool_bash_cat_guard.py", "pretool_bash_cat_guard")
        missing = mod.missing_paths(cmd, data.get("cwd") or os.getcwd())
        if not missing:
            return GateResult(0, "", "")
        lines = [
            "BLOCKED: $(cat ...) references file(s) that do not exist — the command would silently run with a truncated/empty substitution:"
        ]
        lines += [f"  missing: {m}" for m in missing]
        lines.append(
            "Create the file first (verify with wc -c), or fix the path. A redirect target in the same command is skipped, and so is text the shell never expands (quoted heredoc bodies, single quotes, \\$( escapes, comments)."
        )
        return GateResult(2, "\n".join(lines) + "\n", "")
    except Exception:
        return GateResult(0, "", "")


# --- 6. pretool-noext-nongit-guard.sh (BLOCKER, no if) ---------------------

_NONGIT_TOOLS = {
    "rg",
    "grep",
    "egrep",
    "fgrep",
    "ag",
    "ack",
    "fd",
    "find",
    "sed",
    "awk",
    "zoekt",
    "cat",
    "head",
    "tail",
    "wc",
    "cut",
    "tr",
    "sort",
    "uniq",
    "ast-grep",
    "sg",
}
_SHELL_RESET = {"|", "||", "&&", ";", "&", "|&", "(", ")", "{", "}"}
# shlex(punctuation_chars=True) returns a run of adjacent operator characters as ONE token,
# so `( ... | tail -2 ); git diff --no-ext-diff` yields `);` — a run the set above misses,
# which carried `tail` into the git segment and blocked git's own flag. A run resets the
# segment when it holds a separator; a redirection run (`>&` in `2>&1`, `&>`, `>|`) does not.
_REDIRECTION_RUN = re.compile(r"[<>]{1,3}[&|]?|&>{1,2}|<>")


def _is_shell_reset(token: str) -> bool:
    if token in _SHELL_RESET:
        return True
    if not token or any(char not in "();<>|&\n" for char in token):
        return False
    if _REDIRECTION_RUN.fullmatch(token):
        return False
    return any(char in ";|&()\n" for char in token)


def _noext_nongit_hit(cmd: str) -> str | None:
    try:
        from lib_bash_cmd_strip import strip_heredocs

        cmd = strip_heredocs(cmd)  # a heredoc body is stdin data, never a command's flags
    except Exception:  # fallback-ok — a missing stripper must not disable the guard
        pass
    # An unquoted newline ends a command, but shlex reads it as whitespace: make it an
    # operator character instead. A comment's reader consumes the newline that ends it, so
    # each newline is doubled first; a backslash-newline continuation joins its lines.
    cmd = cmd.replace("\\\n", " ").replace("\n", "\n\n")
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return None
    expect_cmd = True
    seg_nongit = False
    cur = None
    for t in toks:
        if _is_shell_reset(t):
            expect_cmd, seg_nongit = True, False
            continue
        if expect_cmd:
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
                continue
            cur = t.rsplit("/", 1)[-1]
            seg_nongit = cur in _NONGIT_TOOLS
            expect_cmd = False
            continue
        if t == "--no-ext-diff" and seg_nongit:
            return cur
    return None


def gate_noext_nongit_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = _jqlike_cmd(data)
    if not cmd or "--no-ext-diff" not in cmd:
        return GateResult(0, "", "")
    hit = _noext_nongit_hit(cmd)
    if not hit:
        return GateResult(0, "", "")
    msg = (
        f"BLOCKED: --no-ext-diff is a GIT-ONLY flag, but you applied it to '{hit}'.\n"
        f"On {hit} it is an UNRECOGNIZED FLAG → the tool errors (exit 2) with no output → with\n"
        "2>/dev/null this is a SILENT FALSE-ZERO (0 hits for content that exists, the worst trap).\n"
        f"Fix: drop --no-ext-diff from the '{hit}' command (it is auto-injected for git ONLY).\n"
    )
    _log_trigger("noext-nongit-guard", "block", hit, cmd)
    return GateResult(2, msg, "")


# --- 7/8. pretool-bash-background-ampersand.py, pretool-bg-dispatch-footgun.py: NATIVE (below in MANIFEST) ---

# --- 9. pretool-heavy-load-guard.sh (ADVISORY+BLOCKER, no if) --------------

_HEAVY_RE = re.compile(
    r"generate_unified_embeddings|generate_gemini_embeddings|extract_media|extract_media_phenotype|"
    r"rebuild_identity|identity[._]rebuild|20260610j|p4_identity|marker_single|local.*marker|ffmpeg|"
    r"transcribe|voxtral|whisper|late_chunking|build_certs|rebuild_image_embeddings|sentence-transformers|"
    r"\.embed\b|embed\.py|rerank=True|CrossEncoder|reranker|SearchEngine|fs_recall|fs_hard|emb_rerank|"
    r"recall_eval|recall_bakeoff|fs_ab",
    re.I,
)
_OFFLOAD_RE = re.compile(r"modal (run|deploy)|--remote", re.I)


def gate_heavy_load_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        if not cmd or not _HEAVY_RE.search(cmd):
            return GateResult(0, "", "")
        if _OFFLOAD_RE.search(cmd):
            return GateResult(0, "", "")

        try:
            ps_out = subprocess.run(
                ["ps", "-axo", "rss=,pid=,comm="], capture_output=True, text=True, timeout=5
            ).stdout
        except Exception:
            ps_out = ""
        huge = []
        for line in ps_out.splitlines():
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            try:
                rss = int(parts[0])
            except ValueError:
                continue
            if rss > 8388608 and "python" in parts[2].lower():
                huge.append(f"PID {parts[1]} ~{rss / 1048576:.0f}GB")
        if huge:
            msg = (
                f"BLOCKED: a python job is already holding >8GB RAM ({'; '.join(huge)}; ) — a model job in flight.\n"
                "Cap local model-loading jobs to ONE AT A TIME. On 2026-06-10 three parallel torch eval\n"
                "jobs (embedding model + cross-encoder over a full index, MPS-fallback spilling to RAM)\n"
                "consumed ~44GB on this 36GB Mac → OOM freeze → forced reboot. Wait for it or kill it.\n"
                "Inspect: ps -axo rss,pid,command | sort -rn | head\n"
            )
            return GateResult(2, msg, "")

        mps_note = ""
        if "PYTORCH_ENABLE_MPS_FALLBACK" in cmd:
            mps_note = (
                "PYTORCH_ENABLE_MPS_FALLBACK=1 silently spills oversized tensors into CPU RAM "
                "(14GB/proc, 2026-06-10) — drop it so they error cleanly. "
            )

        try:
            cores = float(
                subprocess.run(
                    ["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True, timeout=3
                ).stdout.strip()
                or 8
            )
        except Exception:
            cores = 8.0
        load1 = 0.0
        try:
            raw = subprocess.run(
                ["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True, timeout=3
            ).stdout
            load1 = float(raw.strip().strip("{}").split()[0])
        except Exception:
            try:
                up = subprocess.run(["uptime"], capture_output=True, text=True, timeout=3).stdout
                load1 = float(re.split(r"averages?:\s*", up)[-1].split()[0].rstrip(","))
            except Exception:
                load1 = 0.0
        try:
            claudes = int(
                subprocess.run(
                    ["pgrep", "-c", "-f", "claude"], capture_output=True, text=True, timeout=3
                ).stdout.strip()
                or 1
            )
        except Exception:
            claudes = 1

        warn = ""
        if load1 > cores or claudes >= 4:
            warn = (
                f"Compute preflight: 1-min load {load1:.1f} on {int(cores)} cores"
                + (f", {claudes} claude procs" if claudes >= 4 else "")
                + ". This is a HEAVY LOCAL job — launching now risks thrash/starvation "
                "(see reference_throttle_heavy_local_batches: a prior such launch hard-rebooted the Mac). "
                f"Prefer: throttle workers to 4-6, defer until load < {int(cores)}, or offload to Modal."
            )
        warn = mps_note + warn
        if not warn:
            return GateResult(0, "", "")
        _log_trigger(
            "heavy-load-guard", "warn", f"load={load1} cores={cores} claudes={claudes}", cmd
        )
        out = json.dumps({"additionalContext": warn})
        return GateResult(0, "", out)
    except Exception:
        return GateResult(0, "", "")


# --- 10. pretool-no-background-commit.sh (BLOCKER, if=Bash(git*)) — imports sidecar ---


def gate_no_background_commit(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(
            HOOKS_DIR / "pretool_no_background_commit.py", "pretool_no_background_commit"
        )
        data = json.loads(raw_payload)
        verdict = mod.classify(data)
    except Exception:
        return GateResult(0, "", "")
    if verdict == "BG":
        return GateResult(
            2,
            "BLOCKED: git commit inside run_in_background=true — a hook-blocked commit reports success while nothing lands. Run the commit FOREGROUND (background the slow step, then commit in a separate foreground call).\n",
            "",
        )
    if verdict == "PIPE":
        return GateResult(
            2,
            "BLOCKED: git commit piped into tail/head/grep/... masks git's exit code (the pipeline returns the reader's rc), so a hook-blocked commit reads rc=0 while nothing lands. Capture the exit code explicitly instead: 'git commit -F msg > /tmp/c.txt 2>&1; echo COMMIT_RC=$?; tail /tmp/c.txt' — then verify with 'git log --oneline -1'.\n",
            "",
        )
    return GateResult(0, "", "")


# --- 11/12/13/14/28: NATIVE imports (see MANIFEST) -------------------------

# --- 15. pretool-duckdb-quote-guard.sh (ADVISORY, no if) -------------------
# Original extracts CMD via `grep -oE '"command"\s*:\s*"[^"]*"' | head -1` on
# the RAW json text (not jq) — no escape handling, so an escaped quote inside
# the command truncates the match. Bug-compatible on purpose.
_DUCKDB_CMD_RE = re.compile(r'"command"\s*:\s*"([^"]*)"')


def gate_duckdb_quote_guard(raw_payload: str) -> GateResult:
    m = _DUCKDB_CMD_RE.search(raw_payload)
    cmd = m.group(1) if m else ""
    if not re.search(r"duckdb|\.execute\(|SELECT |INSERT |UPDATE |WHERE ", cmd, re.I):
        return GateResult(0, "", "")
    if re.search(r'= "[a-zA-Z_]+"', cmd) and not re.search(r'= "[a-zA-Z_]+"\)', cmd):
        msg = (
            "DuckDB gotcha: double quotes = column identifier, not string literal. Use single "
            "quotes for string values (e.g., WHERE col = 'value' not WHERE col = \"value\")."
        )
        return GateResult(0, "", msg)
    return GateResult(0, "", "")


# --- 16. ~/.claude/hooks/pretool-modal-cost-guard.sh (BLOCKER+ADVISORY, no if) ---


def gate_modal_cost_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or data).get("command", "") or ""
    except Exception:
        return GateResult(0, "", "")
    if not re.search(r"modal run", cmd):
        return GateResult(0, "", "")
    m = re.search(r"[^ ]+\.py", cmd)
    if not m:
        return GateResult(0, "", "")
    script = m.group(0)
    if not os.path.isfile(script):
        return GateResult(0, "", "")
    try:
        src = open(script).read()
    except Exception:
        return GateResult(0, "", "")
    warnings, is_block = [], False
    if re.search(r"gpu=", src):
        if not re.search(r"timeout=", src):
            warnings.append(
                "WARNING: GPU function has no timeout= set. Add timeout = 1.5x expected duration as cost circuit breaker."
            )
        else:
            tm = re.search(r"timeout=([0-9]+)", src)
            if tm and int(tm.group(1)) > 43200:
                warnings.append(
                    f"WARNING: timeout={tm.group(1)} ({int(tm.group(1)) // 3600}h) is very high. Is this intentional?"
                )
        if re.search(r"\.(starmap|map)\(", src):
            if "max_containers" not in src:
                warnings.append(
                    "BLOCK: Script uses .starmap()/.map() with GPU but no max_containers set. Unbounded auto-scaling will burn money. Add max_containers= to the @app.function decorator."
                )
                is_block = True
    if not warnings:
        return GateResult(0, "", "")
    text = "\n".join(warnings) + "\n"
    if is_block:
        return GateResult(2, text, "")
    return GateResult(0, text, "")


# --- 17. ~/.claude/hooks/pretool-modal-script-audit.sh (ADVISORY, no if) ---


def gate_modal_script_audit(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or data).get("command", "") or ""
    except Exception:
        return GateResult(0, "", "")
    if not re.search(r"modal run.*--detach|modal run.*\.py", cmd):
        return GateResult(0, "", "")
    m = re.search(r"[^ ]+\.py", cmd)
    if not m:
        return GateResult(0, "", "")
    script = m.group(0)
    if not os.path.isfile(script):
        return GateResult(0, "", "")
    try:
        src = open(script).read()
    except Exception:
        return GateResult(0, "", "")
    warnings = []
    if re.search(r"@app\.function|@stage", src):
        cap_count = len(re.findall(r"capture_output=True", src))
        if cap_count > 0:
            warnings.append(
                f"WARNING: {cap_count} subprocess call(s) use capture_output=True — output invisible in modal app logs (gotcha #16). Use stdout=subprocess.PIPE, stderr=subprocess.STDOUT instead."
            )
    if re.search(r"@stage", src):
        if re.search(r"for .* in .*:", src) and "vol.commit()" not in src:
            warnings.append(
                "WARNING: Script has loops in @stage functions but no vol.commit() — intermediate results lost on crash (gotcha #20). Add vol.commit() after each iteration."
            )
    if "--detach" in cmd and re.search(r"subprocess\.run\(.*timeout=", src):
        warnings.append(
            "WARNING: subprocess.run(timeout=) in a --detach script can create orphan apps (gotcha #32). Remove subprocess timeouts for detached runs."
        )
    if not warnings:
        return GateResult(0, "", "")
    return GateResult(0, "\n".join(warnings) + "\n", "")


# --- 18. pretool-cost-guard.sh (BLOCKER $25 / ADVISORY $10, no if) ---------


def gate_cost_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = _jqlike_cmd(data)
    if not cmd or not re.search(r"llmx|modal run|curl.*api|python.*openai|python.*anthropic", cmd):
        return GateResult(0, "", "")
    receipts = os.path.expanduser("~/.claude/session-receipts.jsonl")
    if not os.path.isfile(receipts):
        return GateResult(0, "", "")
    today = time.strftime("%Y-%m-%d")
    total = 0.0
    try:
        with open(receipts) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if not r.get("ts", "").startswith(today):
                    continue
                if "transcript_lines" in r or "harness_hash" in r:
                    continue
                total += float(r.get("cost_usd", 0))
    except Exception:
        return GateResult(0, "", "")
    spend_int = int(total)
    if spend_int >= 25:
        _log_trigger("cost-guard", "block", f"daily_spend=${total:.2f} cmd={cmd[:80]}", cmd)
        out = json.dumps(
            {
                "decision": "block",
                "reason": f"Daily API spend ${total:.2f} exceeds the $25 constitutional cap. Defer non-essential API calls, or set LLMX_SPEND_OVERRIDE=1 for an intended llmx job / get human approval.",
            }
        )
        return GateResult(2, "", out)
    if spend_int >= 10:
        _log_trigger("cost-guard", "warn", f"daily_spend=${total:.2f} cmd={cmd[:80]}", cmd)
        out = json.dumps(
            {
                "decision": "allow",
                "additionalContext": f"Cost warning: daily spend at ${total:.2f} (warn at $10, block at $25). Consider batching or deferring.",
            }
        )
        return GateResult(0, "", out)
    return GateResult(0, "", "")


# --- 19. pretool-cost-awareness.sh (ADVISORY, every 50 calls, no if) -------


def gate_cost_awareness(raw_payload: str) -> GateResult:
    try:
        ppid = os.getppid()
        counter_file = f"/tmp/claude-cost-check-{ppid}"
        try:
            count = int(open(counter_file).read().strip())
        except Exception:
            count = 0
        count += 1
        try:
            with open(counter_file, "w") as f:
                f.write(str(count))
        except OSError:
            pass
        if count % 50 != 0:
            return GateResult(0, "", "")

        cwd = os.getcwd()
        try:
            r = subprocess.run(
                ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            root = r.stdout.strip()
        except Exception:
            root = ""
        project = os.path.basename(root) if root else os.path.basename(cwd)
        if not project:
            project = os.path.basename(cwd)

        receipts = os.path.expanduser("~/.claude/session-receipts.jsonl")
        if not os.path.isfile(receipts):
            return GateResult(0, "", "")
        session_id = os.environ.get("CLAUDE_SESSION_ID", str(ppid))
        costs, current = [], 0.0
        with open(receipts) as f:
            for line in f:
                try:
                    r2 = json.loads(line)
                except Exception:
                    continue
                if r2.get("project", "") != project:
                    continue
                c = float(r2.get("cost_usd", 0))
                costs.append(c)
                if r2.get("session", "") == session_id:
                    current = c
        if len(costs) < 5:
            return GateResult(0, "", "")
        costs.sort()
        n = len(costs)
        p95 = costs[min(int(n * 0.95), n - 1)]
        median = costs[n // 2]
        if current <= p95:
            return GateResult(0, "", "")
        advisory = (
            f"Cost awareness: this session (${current:.2f}) has exceeded P95 "
            f"(${p95:.2f}) for project {project}. Project median: ${median:.2f}. "
            "Consider whether this session should continue or checkpoint."
        )
        _log_trigger("cost-awareness", "warn", f"project={project}")
        out = json.dumps({"additionalContext": advisory})
        return GateResult(0, "", out)
    except Exception:
        return GateResult(0, "", "")


# --- 20. pretool-ast-precommit.sh (BLOCKER, if=Bash(git commit*)) ----------


def _extract_inline_python_blocks(src: str):
    """Mirrors the original's fragile single-quote python3 -c scanner
    (double-quote blocks are deliberately skipped — bug-compatible)."""
    lines = src.splitlines(keepends=True)
    i = 0
    blocks = []  # (start_line_1idx, code)
    while i < len(lines):
        line = lines[i]
        if re.search(r'python3\s+-c\s+"', line):
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith('"'):
                i += 1
            i += 1
            continue
        m = re.search(r"python3\s+-c\s+\$?'", line)
        if m:
            start_line = i + 1
            after_quote = line[m.end() :]
            close_idx = after_quote.find("'")
            if close_idx >= 0:
                code = after_quote[:close_idx]
                if code.strip():
                    blocks.append((start_line, code))
                i += 1
                continue
            block_lines = []
            if after_quote.strip():
                block_lines.append(after_quote)
            i += 1
            while i < len(lines):
                cur = lines[i]
                if cur.lstrip().startswith("'"):
                    break
                block_lines.append(cur)
                i += 1
            code = "".join(block_lines).replace("'\\''", "'")
            if code.strip():
                blocks.append((start_line, code))
        i += 1
    return blocks


def gate_ast_precommit(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not re.match(r"^\s*git\s+commit", cmd):
        return GateResult(0, "", "")
    try:
        staged_py = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "--", "*.py"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.splitlines()
        staged_sh = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "--", "*.sh"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.splitlines()
    except Exception:
        return GateResult(0, "", "")
    staged_py = [f for f in staged_py if f]
    staged_sh = [f for f in staged_sh if f]
    if not staged_py and not staged_sh:
        return GateResult(0, "", "")

    errors = []
    for f in staged_py:
        if not os.path.isfile(f):
            continue
        try:
            ast.parse(open(f).read())
        except SyntaxError as e:
            errors.append(f"  {f}: {e.msg} (line {e.lineno})\n")
        except Exception:
            pass
    for f in staged_sh:
        if not os.path.isfile(f):
            continue
        try:
            src = open(f).read()
        except Exception:
            continue
        sub_errors = []
        for start_line, code in _extract_inline_python_blocks(src):
            try:
                ast.parse(code)
            except SyntaxError as e:
                offset = start_line + (e.lineno or 1)
                sub_errors.append(f"inline python3 -c (line ~{offset}): {e.msg}")
        if sub_errors:
            errors.append(f"  {f}: " + "\n".join(sub_errors) + "\n")

    if not errors:
        return GateResult(0, "", "")
    reason = "Syntax errors in staged files:\n" + "".join(errors)
    out = json.dumps({"decision": "block", "reason": reason})
    return GateResult(2, "", out)


# --- 21. pretool-commit-check.sh (BLOCKER+ADVISORY, if=Bash(git commit*)) --


def gate_commit_check(raw_payload: str) -> GateResult:
    try:
        cmd = (json.loads(raw_payload).get("tool_input") or {}).get("command", "") or ""
    except Exception:
        cmd = ""
    try:
        mod = _load_module(HOOKS_DIR / "commit-check-parse.py", "commit_check_parse")
        result = _run_entry(mod.main, raw_payload)
    except Exception:
        return GateResult(0, "", "")
    text = (result.stdout or "").strip()
    if text in ("SKIP", "OK", ""):
        return GateResult(0, "", "")
    if text.startswith("BLOCK:"):
        msg = text[len("BLOCK:") :]
        _log_trigger("commit-check", "block", msg[:100], cmd)
        return GateResult(2, f"[commit-check]: BLOCKED: {msg}\n{msg}\n", "")
    if not text.startswith("WARN:"):
        return GateResult(0, "", "")
    warn_text = text[len("WARN:") :]
    try:
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, timeout=10
        ).stdout.splitlines()
        staged = [f for f in staged if f]
    except Exception:
        staged = []
    concept_files = sum(1 for f in staged if re.match(r"^(research/|decisions/|docs/research/)", f))
    if concept_files > 0:
        warn_text = warn_text.replace(
            "NOBODY",
            "Concept files (research/decisions) staged — body REQUIRED. Name the concept affected and what changed.",
        )
    elif len(staged) <= 1:
        warn_text = (
            warn_text.replace(" | NOBODY", "").replace("NOBODY | ", "").replace("NOBODY", "")
        )
    else:
        warn_text = warn_text.replace(
            "NOBODY", f"{len(staged)} files staged but no body — add trigger, changes, impact."
        )

    gov = next(
        (
            f
            for f in staged
            if re.search(r"(CLAUDE\.md|MEMORY\.md|improvement-log|hooks/)", f, re.I)
        ),
        None,
    )
    if gov:
        if "Evidence:" not in text:
            warn_text += f" | Governance file ({gov}) needs Evidence: trailer."
        if "Affects:" not in text:
            warn_text += " | Governance file needs Affects: trailer."

    warn_text = re.sub(r"^\s*\|\s*", "", warn_text)
    warn_text = re.sub(r"\s*\|\s*$", "", warn_text)
    warn_text = re.sub(r"\|\s*\|\s*\|", "|", warn_text)
    if not warn_text.strip():
        return GateResult(0, "", "")
    _log_trigger("commit-check", "warn", warn_text[:100], cmd)
    out = json.dumps({"additionalContext": f"COMMIT CHECK: {warn_text}"})
    return GateResult(0, "", out)


# --- 23. pretool-modal-run-guard.sh (BLOCKER, no if) -----------------------


def _kw_value(node):
    if isinstance(node, ast.Constant):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
    ):
        return -node.operand.value
    if isinstance(node, ast.Name):
        return f"<name:{node.id}>"
    return None


def gate_modal_run_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    if data.get("tool_name", "") != "Bash":
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd or not re.search(r"\bmodal\s+run\b", cmd):
        return GateResult(0, "", "")
    tokens = cmd.split()
    target = None
    for t in tokens:
        tt = t.split("::")[0]
        if tt.endswith(".py"):
            target = tt
            break
    if not target:
        return GateResult(0, "", "")
    cwd = data.get("cwd", "") or ""
    if not os.path.isabs(target):
        target = os.path.join(cwd, target)
    if not os.path.isfile(target):
        return GateResult(0, "", "")
    try:
        tree = ast.parse(open(target).read())
    except Exception:
        return GateResult(0, "", "")

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            fn = dec.func
            name = (
                fn.attr
                if isinstance(fn, ast.Attribute)
                else (fn.id if isinstance(fn, ast.Name) else "")
            )
            if name not in ("function", "cls"):
                continue
            kwargs = {kw.arg: _kw_value(kw.value) for kw in dec.keywords if kw.arg is not None}
            line = dec.lineno
            ed = kwargs.get("ephemeral_disk")
            if isinstance(ed, int) and not (524288 <= ed <= 3145728):
                findings.append(
                    f"{os.path.basename(target)}:{line} @app.{name} has ephemeral_disk={ed} — Modal requires [524288, 3145728] MiB. Use ephemeral_disk=524288 (512 GB min)."
                )
            np_val, gpu_val = kwargs.get("nonpreemptible"), kwargs.get("gpu")
            if np_val is True and gpu_val not in (None, False):
                findings.append(
                    f"{os.path.basename(target)}:{line} @app.{name} has nonpreemptible=True AND gpu={gpu_val!r} — Modal does not support nonpreemptible for GPU functions. Drop one."
                )
    if not findings:
        return GateResult(0, "", "")
    reason = (
        "MODAL LAUNCH BLOCKED — invalid config in target script:\n\n"
        + "\n".join(f"  - {f}" for f in findings)
        + "\n\nFix in the script, then re-run."
    )
    out = json.dumps({"decision": "block", "reason": reason})
    return GateResult(
        0, "", out
    )  # original always exits 0; the JSON decision field carries the block


# --- 24. pretool-timeout-modal-guard.sh (BLOCKER, no if) -------------------

_TIMEOUT_HEREDOC_RE = re.compile(r"<<-?\s*'?([A-Za-z_]\w*)'?.*?\n\1\s*$", re.S | re.M)
_TIMEOUT_CRAWL_RE = re.compile(
    r"\bmodal\s+(?:volume|run|app|container)\b"
    r"|\bjust\s+(?:dispatch|sample-remediation|sample-state|sample-readiness"
    r"|complete-sample|pipeline-run|pipeline-rerun|pipeline-rerun-vcf|census"
    r"|volume-status|stage-status|probe|download-results)\b"
    r"|pipeline_orchestrator\.py\s+(?:dispatch|rerun|run|resume|recover|reconcile|reconcile-runs|backfill|sync-cass)\b"
    r"|complete_sample\.py"
    r"|\bmodal_sync_results\.py\b",
)


_TIMEOUT_PREFIX = {"nohup", "sudo", "env", "exec", "command", "time", "do", "then", "else"}
# Search/print tools: a crawl name in their argv is a pattern or text, never a run.
_TIMEOUT_TEXT_TOOLS = {"grep", "egrep", "fgrep", "rg", "ag", "echo", "printf", "cat", "head", "tail", "sed", "awk", "jq"}
_TIMEOUT_SEPS = {";", "&&", "||", "|", "&", "(", ")", "$", "`", "|&", ";;"}
# Bounded read-only listings and streams: a timeout on these is harmless (and the
# streaming guard REQUIRES one on logs/exec). 2026-10-14..21: 24 false blocks in 6
# sessions on `volume ls`, `app list`, `container list`, `app stop`.
_TIMEOUT_MODAL_OK = {
    ("volume", "ls"), ("app", "list"), ("container", "list"), ("app", "stop"),
    ("app", "logs"), ("container", "logs"), ("container", "exec"),
}


def _timeout_segments(cmd: str):
    """Parsed argv per pipeline/list segment; quoted text stays one opaque token."""
    # `\⏎` is a continuation, not a separator; `$` stays in words so `$VOL -r` is one segment
    # (a bare `$` token before `(` still splits `$(…)`).
    text = cmd.replace("\\\n", " ").replace("\n", " ; ")
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()`")
    lex.whitespace_split = True
    seg: list[str] = []
    try:
        for tok in lex:
            if tok in _TIMEOUT_SEPS or set(tok) <= set(";&|()`$"):
                if seg:
                    yield seg
                seg = []
            else:
                seg.append(tok)
    except ValueError:
        return  # unbalanced quoting — fail open
    if seg:
        yield seg


def _timeout_skip_prefix(seg: list[str]) -> int:
    i = 0
    while i < len(seg) and (seg[i] in _TIMEOUT_PREFIX or re.fullmatch(r"[A-Za-z_]\w*=.*", seg[i])):
        i += 1
    return i


def _timeout_wrapped_argv(seg: list[str]) -> list[str] | None:
    """argv after `timeout [opts] DURATION`, or None if the segment is not timeout-wrapped."""
    i = 0
    i = _timeout_skip_prefix(seg)
    if i >= len(seg) or seg[i] != "timeout":
        return None
    i += 1
    while i < len(seg) and seg[i].startswith("-"):
        i += 2 if seg[i] in {"-k", "-s", "--kill-after", "--signal"} else 1
    if i >= len(seg) or not re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", seg[i]):
        return None
    return seg[i + 1 :]


def _timeout_crawl(argv: list[str]) -> bool:
    for k, tok in enumerate(argv):
        if tok == "modal" or tok.endswith("/modal"):
            sub = tuple(argv[k + 1 : k + 3])
            if sub[:1] and sub[0] in {"volume", "run", "app", "container"}:
                if sub in _TIMEOUT_MODAL_OK and not (
                    sub == ("volume", "ls") and {"-r", "--recursive"} & set(argv[k + 3 :])
                ):
                    return False
                return True
            return False
    if argv and argv[0].rsplit("/", 1)[-1] in _TIMEOUT_TEXT_TOOLS:
        return False
    return bool(_TIMEOUT_CRAWL_RE.search(" ".join(argv)))


_SHELLS = {"bash", "sh", "zsh"}


def _timeout_blocks(text: str, depth: int = 0) -> bool:
    """True if any segment is `timeout … <crawl>`; recurses into `bash|sh|zsh -c STR`
    (depth cap 3) so a nested-shell wrapper cannot hide a crawl."""
    for seg in _timeout_segments(text):
        argv = _timeout_wrapped_argv(seg)
        if argv is not None and _timeout_crawl(argv):
            return True
        head = _timeout_skip_prefix(seg)
        if depth < 3 and head < len(seg) and seg[head].rsplit("/", 1)[-1] in _SHELLS:
            for k, tok in enumerate(seg[head + 1 : -1], start=head + 1):
                if re.fullmatch(r"-[a-z]*c[a-z]*", tok) and _timeout_blocks(seg[k + 1], depth + 1):
                    return True
    return False


def gate_timeout_modal_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    if data.get("tool_name") != "Bash":
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return GateResult(0, "", "")
    scan = _TIMEOUT_HEREDOC_RE.sub(" ", cmd)
    if not re.search(r"\btimeout\s", scan):  # cheap prefilter; the parser decides
        return GateResult(0, "", "")
    # One owner: block only parsed argv `timeout … <crawl>` — never text inside quotes
    # or grep/rg patterns (2026-10-14..21: 2 blocks on `rg 'timeout='` alone).
    if not _timeout_blocks(scan):
        return GateResult(0, "", "")
    msg = (
        "BLOCKED: `timeout N` wraps a Modal/volume-crawl command. At the deadline it\n"
        "sends SIGTERM (exit 143) and kills the crawl MID-RUN — wasting the dispatch/\n"
        "remediation/volume-ls and any partial state. (genomics 2026-06-24: this footgun\n"
        "fired 4x in one session.)\n"
        "Fix: DROP `timeout N` and either\n"
        "  - run_in_background=true  (tracked; you get a completion notification), or\n"
        "  - use the commands OWN bound (`just dispatch ... --detach`, llmx `--timeout`).\n"
        "A timeout IS fine on bounded reads: modal volume ls, app list/stop/logs,\n"
        "container list/logs/exec (the streaming guard requires it on logs).\n"
        "Never SIGTERM a Modal crawl to bound it.\n"
    )
    return GateResult(2, msg, "")


# --- 27. pretool-plan-protect.sh (BLOCKER, no if) --------------------------

_PLAN_DESTRUCTIVE_RE = re.compile(r"^\s*(?:sudo\s+)?(?:rm|mv|trash)(?:\s|$)")
_PLAN_PROTECTED_RE = re.compile(
    r"\.claude/plans/[^\s]*\.md|docs/ops/plans/[^\s]*\.md|\.claude/checkpoint\.md"
)


def gate_plan_protect(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return GateResult(0, "", "")
    if "PLAN-PROTECT-OVERRIDE" in cmd:
        return GateResult(0, "", "")
    if os.environ.get("PLAN_PROTECT_OVERRIDE", "") == "ALLOW":
        return GateResult(0, "", "")
    segments = re.split(r"(?:&&|\|\||[;|\n])", cmd)
    hit = any(
        _PLAN_DESTRUCTIVE_RE.search(seg) and _PLAN_PROTECTED_RE.search(seg) for seg in segments
    )
    if not hit:
        return GateResult(0, "", "")
    _log_trigger("plan-protect", "block", cmd, cmd)
    reason = (
        "BLOCKED: rm/mv/trash targets a plan or checkpoint markdown (.claude/plans/, docs/ops/plans/, "
        ".claude/checkpoint.md). These are usually untracked agent state; recovery needs user paste-back. "
        "Use git mv for tracked files, or include PLAN-PROTECT-OVERRIDE to acknowledge the risk."
    )
    out = json.dumps({"decision": "block", "reason": reason})
    return GateResult(2, out + "\n", "")


# ─────────────────────────────────────────────────────────────────────────
# SUBPROCESS-KEPT gates — literal subprocess call, fed the CURRENT (possibly
# already-mutated) envelope on stdin. See module docstring for why each one
# was not ported.
# ─────────────────────────────────────────────────────────────────────────


def _envelope_dir(raw_payload: str) -> str | None:
    """The directory the Bash call runs in, as the envelope records it.

    Same precedence as pretool-multiagent-commit-guard.sh and the git-history gate:
    tool_input.workdir, then tool_input.cwd, then the top-level cwd. None when the
    envelope names none; the caller then inherits the dispatcher's own cwd."""
    try:
        data = json.loads(raw_payload)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    ti = data.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    for value in (ti.get("workdir"), ti.get("cwd"), data.get("cwd")):
        if isinstance(value, str) and value:
            return value
    return None


def make_subprocess_gate(path: str, *, cwd_from_envelope: bool = False, timeout: float = 30):
    """Run a kept gate as a subprocess fed the current envelope on stdin.

    By default the child inherits the dispatcher's cwd; the three original kept
    gates read the envelope themselves or use that cwd, and keep doing so.
    ``cwd_from_envelope`` starts the child in ``_envelope_dir`` instead, for a gate
    that resolves its repo from its own cwd. A directory that does not exist makes
    subprocess.run raise, which fails open like any other error here."""

    def run(raw_payload: str) -> GateResult:
        cwd = _envelope_dir(raw_payload) if cwd_from_envelope else None
        try:
            proc = subprocess.run(
                [path],
                input=raw_payload,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
        except Exception:
            return GateResult(0, "", "")
        return GateResult(proc.returncode, proc.stderr or "", proc.stdout or "")

    return run


# --- git-stale-lock (SIDE EFFECT ONLY, never a verdict; trigger `\bgit\b`) -----
# pretool-git-stale-lock.sh deletes git lock files that no process holds open (lsof)
# and that are at least 30 s old, but never while a git process runs in that repo (a
# git in a hook phase keeps its index.lock closed), and logs each removal to
# ~/.cache/git-stale-lock/removed.jsonl. Until 2026-09-24 only genomics wired it (its
# project settings.json). That day a 0-byte heli .git/index.lock, left at 20:05:05
# with no holder and no git process, blocked every git write until it was removed by
# hand about 10 minutes later. Running it here covers every repo.
#
# Kept as a subprocess: the guard's lsof possession test and file removal are the
# safety logic, and a port could drift from them. The `\bgit\b` search runs anywhere
# in the command because `cd <repo> && git ...` is the common shape; every other Bash
# call pays only that search. The child starts in the envelope's directory because the
# guard finds the repo with `git rev-parse --git-common-dir` in its own cwd. The result
# is dropped and the gate always passes. _classify would turn the guard's exit-0 stderr
# note into model-visible advisory text, which the directly wired hook never produced:
# Claude Code feeds a hook's stderr to the model only on exit 2.
#
# Placed second, right after secret-output-guard (test_pretool_secret_output_guard.py
# pins that gate first). The cleanup then happens even when a later gate blocks, and
# the gates that run git (destructive-git-ref writes a backup ref) find the lock gone.
_GIT_WORD_RE = re.compile(r"\bgit\b")
_run_git_stale_lock = make_subprocess_gate(
    str(HOOKS_DIR / "pretool-git-stale-lock.sh"), cwd_from_envelope=True, timeout=10
)


def gate_git_stale_lock(raw_payload: str) -> GateResult:
    try:
        if _GIT_WORD_RE.search(_jqlike_cmd(json.loads(raw_payload))):
            _run_git_stale_lock(raw_payload)
    except Exception:
        pass  # fail-open: cleanup is best effort and never decides anything
    return GateResult(0, "", "")


# ─────────────────────────────────────────────────────────────────────────
# POST-CONSOLIDATION ADDITIONS (2026-07-18) — new gates with no
# pre-consolidation standalone original; the "28 gates" / "Total: 28"
# accounting above is a historical fact about the original port and is left
# unchanged. Each of these still gets a same-named on-disk .sh sibling
# (repo convention: every live gate has an on-disk copy for independent
# testing/documentation/rollback, wired into settings.json or not — see
# pretool-heavy-load-guard.sh, pretool-plan-protect.sh for precedent); the
# function below is the LIVE path, exactly like every gate above it. Native
# (not SUBPROCESS-KEPT) because the triggering condition is a cheap string
# check that costs ~nothing on the non-matching majority of Bash calls — a
# subprocess-kept gate would pay a `bash` + `python3` spawn on EVERY single
# Bash call, which is the exact cost this dispatcher exists to avoid. Where
# a gate genuinely needs OS-level peer/process introspection (git-stash
# guard's peer count), it shells out to the existing proven helper binary
# ONLY on the rare branch where the cheap check already matched — never
# reimplementing that binary's own logic natively (same "porting risks
# silent drift on a safety-critical guard" reasoning the multiagent-commit
# gate above states for keeping ITS peer-count call as a live subprocess).
# ─────────────────────────────────────────────────────────────────────────

# --- 29. pretool-git-stash-guard.sh (BLOCKER+ADVISORY, no if — the "stash"
# substring check below IS the cheap gate) ----------------------------------

_STASH_READONLY_SUBCMDS = {"list", "show"}


def _git_stash_call(seg: str):
    """Mirrors pretool-git-stash-guard.sh's stash_call(): (is_git_stash, args)."""
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        if re.match(r"(?:[A-Za-z_]\w*=\S+\s+)*git\s+(-\S+\s+)*stash\b", seg):
            return True, None
        return False, None
    i = 0
    while i < len(parts) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", parts[i]):
        i += 1
    if i >= len(parts) or parts[i] != "git":
        return False, None
    j = i + 1
    while j < len(parts) and parts[j].startswith("-"):
        j += 2 if parts[j] in ("-C", "-c") else 1
    if j >= len(parts) or parts[j] != "stash":
        return False, None
    return True, parts[j + 1 :]


def _git_stash_is_safe(args) -> bool:
    """Two allowed shapes, everything else is peer-gated — see
    pretool-git-stash-guard.sh's is_safe_pathlimited_push() for the full
    rationale (kept in sync; that file is this function's on-disk twin)."""
    if args is None:
        return False
    if not args:
        return False  # bare `git stash` == `git stash push` on the WHOLE tree
    sub = args[0]
    if sub in _STASH_READONLY_SUBCMDS:
        return True
    if sub not in ("push", "save"):
        return False
    return "--" in args[1:]


def gate_git_stash_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    ti = data.get("tool_input") or {}
    cmd = ti.get("command", "") or ""
    if not cmd or "stash" not in cmd:
        return GateResult(0, "", "")
    segments = re.split(r"&&|\|\||;|\||\n", cmd)
    offending = False
    for seg in segments:
        hit, args = _git_stash_call(seg)
        if hit and not _git_stash_is_safe(args):
            offending = True
            break

    cwd = ti.get("workdir") or data.get("cwd") or os.getcwd()
    peer_bin = os.environ.get("PEER_SESSION_COUNT_BIN") or str(HOOKS_DIR / "peer-session-count.sh")
    try:
        peer_out = subprocess.run(
            [peer_bin, cwd], capture_output=True, text=True, timeout=10
        ).stdout.strip()
        peer_count = int(peer_out) if peer_out.isdigit() else 0
    except Exception:
        peer_count = 0

    if not offending:
        # T3 exposure probe (guard-forcerate-study / rescue-class-surface-
        # closure-loop, arc-agi loop/backlog.jsonl rows 906/909): the guard's
        # precondition (a stash-shaped call with a peer sharing this checkout)
        # matched, but the shape was already safe (list/show, or
        # push -- <paths>) — log the eligible-and-clean row the
        # rescues-per-100-eligible-exposures denominator needs. No peer means
        # the precondition never applied (same scoping as the advisory branch
        # below), so there is nothing to log.
        if peer_count >= 1:
            _log_trigger("git-stash-guard", "exposure-clean", f"peers={peer_count}", cmd)
        return GateResult(0, "", "")

    if peer_count < 1:
        # Solo session: never block your own stash — advisory nudge only, so
        # the habit is corrected before a peer ever joins this checkout.
        advisory = (
            "git-stash-guard: bare `git stash` is tree-wide and cannot be path-limited "
            "by default (no peer detected right now, so this is allowed) — prefer "
            "`git stash push -- <paths>` so it stays safe if a peer joins this checkout "
            "later (global <git_rules>, CLAUDE.md 2026-07-16 entry)."
        )
        return GateResult(0, "", json.dumps({"additionalContext": advisory}))

    _log_trigger("git-stash-guard", "block", f"peers={peer_count} cmd={cmd[:80]}", cmd)
    msg = (
        f"BLOCK: bare `git stash` (or stash pop/apply/drop/clear) is banned in a "
        f"checkout with {peer_count} live peer Claude session(s) sharing it (global "
        "<git_rules> — CLAUDE.md, 2026-07-16 entry). `git stash` is tree-wide and "
        "cannot be path-limited by default; it silently rips a peer's in-flight edits "
        "out from under a live session, and `stash pop` against whatever the peer "
        "commits meanwhile FAILS (leaves UU conflict markers) rather than restoring "
        "anything.\n\nSafe alternatives:\n"
        "  - `git stash push -- <your-paths>`   (path-limited to files you own — ALWAYS allowed)\n"
        "  - a git worktree for the A/B you're trying to do\n"
        "  - `git show HEAD:<file>`             (read the committed version without touching the tree)\n\n"
        "If you already ran a bare stash: do NOT resolve a peer's conflict yourself — "
        "`git checkout HEAD -- <file>` to clear it, leave their stash entry intact, "
        "save `git stash show -p` to a patch outside git, and tell the operator.\n"
    )
    return GateResult(2, msg, "")


# --- 30. pkill-guard (BLOCKER, no if) -----------------------------------------
# A kill that selects processes by text reaches every process on the Mac. On 2026-11-07
# 13:12:25 CST a lane worker ran `pkill -f "grep -qE \"passed|failed|error\""` to stop its own
# watcher. pkill reads its pattern as an extended regex, so `|` matched every process whose
# arguments held `failed`, and every lane and bgrun supervisor died: both passed their whole
# script, comments included, to `bash -c`. The advisory this gate replaces split the command on
# `|` before shlex, so the quoted `|` broke its parse and it said nothing; it guessed safety
# from the pattern's shape (`^`, `/`, `-x`) in any case. Two pkills on 2026-07-12 killed a
# training client and a canary the same way.
#
# The gate replays the selection instead. Every pkill and killall, and every pgrep whose output
# feeds a kill, runs again as `pgrep` with the same selection options (killall as
# `killall -s`) and the words the shell would pass it: quotes removed, `~` expanded, and `$HOME`
# and `${HOME}` expanded, as is a variable the command sets once, unconditionally, before the kill
# (`d=$HOME/x; pkill -f "$d/y"`); any other expansion cannot be replayed. A pgrep feeds a kill
# through `xargs kill` or
# a `while read` loop (a pipe, a process substitution, a `( … )` or `{ …; }` group), through a
# `$( … )` in the kill's arguments, or through a variable, array, `for` list or file that a kill
# reads back (zsh `${=pids}` too). Shell `-c` text, a heredoc or here-string a shell reads, `eval`,
# a variable holding a kill command, and the wrappers (`sudo`, `env`, `nice`, `timeout`,
# `/usr/bin/time`, …) are followed. The command is refused when a match lies outside the caller's
# own tree: the nearest Claude or Codex ancestor of this hook and its descendants (the hook's
# parent without one). pkill and pgrep skip their own ancestors, and the replay inherits that;
# killall and `-a` do not, so a match on an ancestor above the agent blocks too. Other users'
# processes count only under sudo (pkill cannot signal them). A selection pinned to recorded PIDs
# is not replayed, as `kill <pid>` is not: `-F`, a numeric `-P` or `-g` other than 1, or the
# caller's own children (`-P $$`), unless `-v` inverts it. Recorded PIDs pass silently: literal
# ids, `$!`, `$$`, job specs, `jobs -p`, and pid files a kill reads back (`$(cat x.pid)`) that no
# pgrep in the command wrote. A kill whose pids come from where no replay reaches (ps output,
# lsof, a variable set elsewhere, a shell reading another program's output), or a replay that
# cannot run, degrades to an advisory marked [DEGRADED], never to a silent pass. Commands with no
# kill-family word at a command position return before any parsing, and nothing spawns a process
# unless a kill selection is found.
_PKILL_SIGNAL_NAMES = frozenset(
    "HUP INT QUIT ILL TRAP ABRT EMT FPE KILL BUS SEGV SYS PIPE ALRM TERM URG STOP TSTP CONT "
    "CHLD TTIN TTOU IO XCPU XFSZ VTALRM PROF WINCH INFO USR1 USR2".split()
)
# macOS pgrep/pkill options that take a value (pgrep(1); -c is FreeBSD's login class).
_PGREP_VALUE_OPTS = frozenset("FGPUcdgtu")
# Options that change only what gets printed or asked, never what is selected.
_PGREP_OUTPUT_OPTS = frozenset("DIdlq")
_PGREP_OWN_CHILDREN = frozenset({"$$", "${$}", "$BASHPID", "${BASHPID}", "$!", "${!}"})
_XARGS_VALUE_OPTS = frozenset("EIJLPRSns")
_PKILL_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
_AGENT_VERSION_COMM = re.compile(r"\d+\.\d+\.\d+")
_PKILL_LISTED_VICTIMS = 15
# The test before any parse: a kill-family word where a shell could run it (see below).
_KILL_WORD_RE = re.compile(r"(?<![\w.\-])(?:p?kill|killall)(?![\w.\-/])")
_KILL_SEGMENT_START_RE = re.compile(r"[\n;(){}`'\"!]|(?<!>)\||(?<![<>])&(?!>)")
_KILL_LAST_BREAK_RE = re.compile(r"(?s:.*)[ \t\n;&|(){}`'\"!<>]")  # matched up to a point
_KILL_FIRST_WORD_RE = re.compile(r"\s*(\S*)")
_KILL_PLAIN_WORD_RE = re.compile(r"[A-Za-z_./~][\w./~+:@%,-]*")
_KILL_COMMAND_PREFIXES = frozenset(
    "sudo doas nice nohup env exec command builtin time timeout gtimeout caffeinate lockf arch "
    "taskpolicy xargs eval noglob nocorrect coproc stdbuf gstdbuf setsid if then else elif do while "
    "until".split()
)
# Variables a word reads: `$p`, `${p}`, zsh `${=p}` and `${(f)p}`, arrays `${p[@]}`.
_KILL_VAR_REF_RE = re.compile(r"\$(?:\{(?:\([^)]*\)|[=~^#!+])*)?([A-Za-z_][A-Za-z0-9_]*)")
# The shell itself and its parent are recorded PIDs, as `$$` and `$!` are.
_KILL_PINNED_NAMES = frozenset({"BASHPID", "PPID"})
_KILL_ASSIGNMENT_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\+?=")
_KILL_DECLARERS = frozenset({"declare", "typeset", "local", "export", "readonly", "integer"})
_KILL_READERS = frozenset({"read", "mapfile", "readarray"})
# Reserved words whose own stage prints nothing.
_KILL_KEYWORDS = frozenset({"for", "select", "case", "esac", "fi", "in", "function", "[[", "]]"})
# Programs that pass the pids they read on: `pgrep … | head -1 | xargs kill`.
_PID_FILTERS = frozenset("grep egrep fgrep rg awk gawk sed cut tr sort uniq tee column paste".split())
_PID_FILE_READERS = frozenset({"cat", "head", "tail"})
_PLAIN_RAW_WORD_RE = re.compile(r"[^\s'\"\\]+")  # shlex returns such a word unchanged
_TILDE_PREFIX_RE = re.compile(r"~(?:[A-Za-z0-9_][A-Za-z0-9_.\-]*)?(?=/|$)")
_KILL_SELECTING_WORDS_RE = re.compile(r"\b(?:pkill|killall|pgrep|ps|lsof|xargs)\b")
_KILL_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_KILL_BARE_NAME_RE = re.compile(r"(?<![\w$])[A-Za-z_][A-Za-z0-9_]*")  # matches run to the name's end
# Characters that make an unquoted expansion split or glob (bash splits, zsh does not), so its
# words are not known.
_KILL_SPLIT_CHARS = frozenset(" \t\n*?[")
# Reserved words that open and close a compound command, and declarers that set a known value.
_KILL_OPENERS = frozenset({"if", "while", "until", "for", "select", "case", "{"})
_KILL_CLOSERS = frozenset({"fi", "done", "esac", "}"})
_KILL_SETTING_DECLARERS = frozenset({"declare", "typeset", "local", "export", "readonly"})
# Positional parameters a word reads: `"$@"`, `$*`, `$1`, `${2}`, `"${@:2}"`.
_KILL_POSITIONAL_RE = re.compile(r"\$\{?(?:[@*]|[1-9])")
# Reserved words a simple command's assignments may follow.
_KILL_RESERVED_LEAD = frozenset({"!", "{", "if", "then", "else", "elif", "do", "while", "until", "time"})
_ANSI_C_ESCAPES = {"a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}


class _DryRunError(Exception):
    """The selection could not be replayed; the gate degrades to an advisory."""


def _kill_word_at_command_position(cmd: str) -> bool:
    """Whether a kill-family word stands where a shell could run it, decided before any parse.

    It over-approximates. A word counts when it opens its segment (after a separator, a bracket,
    a quote, a backtick or `!`), or when the segment's first word is a wrapper, a keyword, an
    assignment, a redirection or anything else that is not a plain word. Only a kill word after a
    plain first word (`docker kill`, `rg -n kill`, prose such as `we kill`) or inside a longer word
    (`skills`, `kill-session`, `os.kill`) is skipped.

    It takes linear time. Each kill word's own word start comes from the last break between it
    and the kill word before it, and a segment's first word is judged once: a plain first word
    ends at a blank before the segment's first kill word, so later kill words share it.
    """
    starts: list[int] | None = None
    word_start = scanned = 0
    judged = -2  # the segment whose first word was judged plain
    for match in _KILL_WORD_RE.finditer(cmd):
        found = _KILL_LAST_BREAK_RE.match(cmd, scanned, match.start())
        if found:
            word_start = found.end()  # the word may be longer, as in /usr/bin/pkill
        scanned = match.start()
        if starts is None:
            starts = [segment.end() for segment in _KILL_SEGMENT_START_RE.finditer(cmd)]
        index = bisect.bisect_right(starts, word_start) - 1
        if index == judged:
            continue
        first = _KILL_FIRST_WORD_RE.match(cmd, starts[index] if index >= 0 else 0, word_start).group(1)
        if not first or not _KILL_PLAIN_WORD_RE.fullmatch(first):
            return True
        if first.rsplit("/", 1)[-1] in _KILL_COMMAND_PREFIXES or first in ("echo", "printf"):
            return True  # a wrapper runs it; a shell may read what echo or printf prints
        judged = index
    return False


class _KillFeed:
    """Where the pids that one stream of text (a pipe, a substitution, a variable) come from.

    Nothing recorded means recorded PIDs at most: literals, `$!`, `jobs -p`.
    """

    __slots__ = ("files", "other", "pgreps", "refs", "texts")

    def __init__(self) -> None:
        self.pgreps: list[tuple[list[str | None] | None, list[str]]] = []  # pgrep output (argv None: ps)
        self.refs: set[str] = set()  # variables it carries
        self.files: list[str] = []  # files it carries
        self.other: list[str] = []  # programs whose output it is, which no replay reproduces
        self.texts: list[str] = []  # shell text it carries, for a shell that reads it

    def merge(self, other: _KillFeed) -> None:
        self.pgreps += other.pgreps
        self.refs |= other.refs
        self.files += other.files
        self.other += other.other
        self.texts += other.texts


class _KillStage:
    """One simple command: its raw words and what it reads besides its pipe."""

    __slots__ = ("certain", "heredocs", "psubs", "redirects", "words")

    def __init__(self) -> None:
        self.words: list[str] = []
        self.redirects: list[tuple[str, str, str]] = []  # (fd, operator, raw target)
        self.psubs: list[tuple[str, str]] = []  # process substitutions: (`<` or `>`, body)
        self.heredocs: list[str] = []  # heredoc bodies it reads on stdin
        # It runs whenever the command line gets this far, in the shell that reads the line: alone in
        # its pipeline, after `;`, a newline or `&` and not backgrounded, outside any compound command.
        self.certain = False


def _kill_programs(names: list[str]) -> str:
    return ", ".join(dict.fromkeys(names))


class _KillShell:
    """What every scan of one command line shares: its text and the variables holding kill commands."""

    __slots__ = ("_counts", "kill_texts", "text")

    def __init__(self) -> None:
        self.text: str | None = None  # the whole command line
        self.kill_texts: dict[str, str] = {}  # variables holding a kill command
        self._counts: collections.Counter[str] | None = None

    def set_text(self, text: str) -> None:
        self.text, self._counts = text, None

    def bare_count(self, name: str) -> int:
        """How often the line names `name` other than to read it (`$name`, `${name}`).

        Every way to set a variable names it so (`name=`, `read name`, `for name in`, `unset name`,
        `printf -v name`), so a count of 1 means the one assignment the scan saw is the only one.
        Any other mention counts too, which only ever makes a value unknown.
        """
        if self.text is None:
            return 1 << 30
        if self._counts is None:  # one pass over the line, whatever the number of names asked
            reads_removed = _KILL_VAR_REF_RE.sub(" ", self.text)
            self._counts = collections.Counter(_KILL_BARE_NAME_RE.findall(reads_removed))
        return self._counts[name]


class _KillScan:
    """What one command line would kill, read from its text.

    genomics' .claude/hooks/pretool-bash-process-kill-guard.py loads this class and
    `_scan_kill_text` by name and reads `selections` after `resolve()`; its
    test_the_quote_aware_scan_loads fails if either is renamed.
    """

    def __init__(self, shell: _KillShell | None = None) -> None:
        self.shell = _KillShell() if shell is None else shell
        # What a variable holds, as `_word_value` reads it; None: set to what the guard cannot know.
        self.values: dict[str, str | None] = {}
        self.opaque = False  # a sourced file or runtime `eval` text may have set any variable
        # (tool, argv, raw argv): argv holds the words the shell passes, None for a word that
        # depends on what the guard cannot know; argv None: the pids come from ps output, which no
        # replay reproduces.
        self.selections: list[tuple[str, list[str | None] | None, list[str]]] = []
        self.output = _KillFeed()  # what the command prints
        self.groups: list[_KillFeed] = []  # outputs outside the open `( … )`, `{ …; }` or loop body
        self.var_feeds: dict[str, _KillFeed] = {}  # what each variable the command sets holds
        self.loop_vars: set[str] = set()  # variables `while read` loops set from their input
        self.loop_feed = _KillFeed()  # what those loops read
        self.file_feeds: dict[str, _KillFeed] = {}  # what each file the command writes holds
        self.kill_feed = _KillFeed()  # the variables and files kills read their pids from
        self.unknown: list[str] = []  # kills whose pids come from where no replay reaches
        self.kills = 0
        self.kill_all = False
        self.sudo = False

    def known(self, name: str) -> str | None:
        """What `$name` expands to here, or None when the guard cannot know it.

        Known: the value of the line's only assignment to `name`, made where it always runs before
        this point; `HOME` from the environment when the line never sets it.
        """
        if self.opaque:
            return None
        if name in self.values:
            return self.values[name] if self.shell.bare_count(name) == 1 else None
        if name == "HOME" and self.shell.bare_count(name) == 0:
            return os.environ.get("HOME") or None
        return None

    def merge(self, inner: "_KillScan") -> None:
        """Take in what a nested command (a substitution, `sh -c` text, a heredoc) recorded."""
        self.selections += inner.selections
        for name, held in inner.var_feeds.items():
            self.assign(name, held)
        self.loop_vars |= inner.loop_vars
        self.loop_feed.merge(inner.loop_feed)
        for name, held in inner.file_feeds.items():
            self.write(name, held)
        self.kill_feed.merge(inner.kill_feed)
        self.unknown += inner.unknown
        self.kills += inner.kills
        self.kill_all |= inner.kill_all
        self.sudo |= inner.sudo

    def assign(self, name: str, feed: _KillFeed) -> None:
        """A variable the command sets now holds the pids `feed` carries."""
        self.var_feeds.setdefault(name, _KillFeed()).merge(feed)

    def write(self, name: str, feed: _KillFeed) -> None:
        """A file the command writes now holds the pids `feed` carries."""
        self.file_feeds.setdefault(name, _KillFeed()).merge(feed)

    def consume(self, feed: _KillFeed, form: str) -> None:
        """A kill signals the pids `feed` carries."""
        self.selections += [("pgrep", argv, raw) for argv, raw in feed.pgreps]
        self.kill_feed.refs |= feed.refs
        self.kill_feed.files += feed.files
        if feed.other and not (feed.pgreps or feed.refs or feed.files):
            self.unknown.append(f"{form} takes its pids from {_kill_programs(feed.other)} output")

    def resolve(self) -> None:
        """Turn what the kills read into selections, or into reasons no replay reaches them."""
        names = set(self.kill_feed.refs)
        files = list(self.kill_feed.files)
        if names & self.loop_vars:  # a kill reads what a `while read` loop read
            loop = self.loop_feed
            self.selections += [("pgrep", argv, raw) for argv, raw in loop.pgreps]
            names |= loop.refs
            files += loop.files
            if loop.other and not (loop.pgreps or loop.refs or loop.files):
                self.unknown.append(
                    f"a `while read` loop that kills takes its pids from {_kill_programs(loop.other)} output"
                )
        # The variables and files a kill reads, followed through what each one holds.
        def sources(refs: set[str], read: list[str]) -> list[tuple[str, str]]:
            named = sorted(refs - self.loop_vars - _KILL_PINNED_NAMES)
            return [("file", name) for name in reversed(read)] + [("$", name) for name in reversed(named)]

        pending = sources(names, files)
        seen: set[tuple[str, str]] = set()
        while pending:
            kind, name = source = pending.pop()
            if source in seen:
                continue
            seen.add(source)
            held = (self.var_feeds if kind == "$" else self.file_feeds).get(name)
            if held is None:
                # A pid file no command here wrote holds recorded PIDs, and positional parameters
                # no `set` here assigned are the shell's own.
                if kind == "$" and name != "@":
                    self.unknown.append(f"a kill reads ${name}, which this command does not set")
                continue
            self.selections += [("pgrep", argv, raw) for argv, raw in held.pgreps]
            pending += sources(held.refs, held.files)
            if held.other and not (held.pgreps or held.refs or held.files):
                what = f"${name}" if kind == "$" else name
                self.unknown.append(f"a kill reads {what}, which holds {_kill_programs(held.other)} output")
        unique: dict[tuple, tuple[str, list[str | None] | None, list[str]]] = {}
        for tool, argv, raw in self.selections:
            unique.setdefault((tool, None if argv is None else tuple(argv), tuple(raw)), (tool, argv, raw))
        self.selections = list(unique.values())


def _ansi_c_text(body: str, echo: bool = False) -> str:
    """Text with its backslash escapes decoded: a `$'…'` body, or (`echo`) `echo -e` and printf `%b` text.

    `echo` reads `\\0NNN` as octal and stops the output at `\\c`; `$'…'` reads `\\cX` as control-X.
    A printf format decodes as a `$'…'` body does for every escape a command line can carry.
    """
    out: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch != "\\" or i + 1 >= len(body):
            out.append(ch)
            i += 1
            continue
        nxt = body[i + 1]
        i += 2
        if nxt in _ANSI_C_ESCAPES:
            out.append(_ANSI_C_ESCAPES[nxt])
        elif nxt in "01234567":
            start = i if echo and nxt == "0" else i - 1
            digits = re.match(r"[0-7]{0,3}", body[start:]).group(0)
            out.append(chr(int(digits or "0", 8) & 0xFF))
            i = start + len(digits)
        elif nxt in "xuU" and re.match(r"[0-9A-Fa-f]", body[i : i + 1]):
            width = {"x": 2, "u": 4, "U": 8}[nxt]
            digits = re.match(f"[0-9A-Fa-f]{{1,{width}}}", body[i:]).group(0)
            out.append(chr(min(int(digits, 16), 0x10FFFF)))
            i += len(digits)
        elif nxt == "c" and echo:
            break  # `\c`: nothing after it is printed
        elif nxt == "c" and i < len(body):
            out.append(chr(ord(body[i]) & 0x1F))
            i += 1
        else:
            out.append(nxt if nxt in "\\'\"?" else "\\" + nxt)
    return "".join(out)


_PRINTF_DIRECTIVE_RE = re.compile(r"%(?:%|[-+ #0']*(?:\*|\d+)?(?:\.(?:\*|\d+))?[A-Za-z])")


def _printf_text(args: list[str]) -> str:
    """What `printf FORMAT ARGS` prints, for the shell text it may carry.

    The format's escapes decode; each directive takes the next argument (`%b` with its escapes
    decoded, `%%` a percent sign), and the format repeats while arguments remain.
    """
    if not args:
        return ""
    fmt, rest = args[0], list(args[1:])
    parts: list[str] = []
    while True:
        used, pos = 0, 0
        for match in _PRINTF_DIRECTIVE_RE.finditer(fmt):
            parts.append(_ansi_c_text(fmt[pos : match.start()]))
            pos = match.end()
            if match.group(0) == "%%":
                parts.append("%")
                continue
            arg = rest.pop(0) if rest else ""
            used += 1
            parts.append(_ansi_c_text(arg, echo=True) if match.group(0).endswith("b") else arg)
        parts.append(_ansi_c_text(fmt[pos:]))
        if not rest or not used:
            return "".join(parts)


def _echo_texts(args: list[str]) -> list[str]:
    """What `echo ARGS` may print: bash leaves escapes alone unless -e, zsh decodes them unless -E."""
    decode: bool | None = None
    while args and re.fullmatch(r"-[neE]+", args[0]):
        for letter in args[0][1:]:
            decode = True if letter == "e" else False if letter == "E" else decode
        args = args[1:]
    text = " ".join(args)
    decoded = _ansi_c_text(text, echo=True)
    if decode is None:
        return list(dict.fromkeys([text, decoded]))
    return [decoded if decode else text]


def _word_value(raw: str, scan: _KillScan, assignment: bool = False) -> str | None:
    """The text the shell passes on for one raw word, or None when it depends on what the guard cannot know.

    Quotes, backslashes, `$'…'` and a leading `~` resolve as the shell resolves them; `$NAME` and
    `${NAME}` resolve to what `scan.known` knows. A command substitution, any other parameter
    form, and an unquoted expansion that would split, glob or vanish are unknown. An assignment's
    value (`assignment`) is neither split nor globbed.
    """
    if "$" not in raw and "`" not in raw and not raw.startswith("~") and _PLAIN_RAW_WORD_RE.fullmatch(raw):
        return raw
    out: list[str] = []
    i, n, quote = 0, len(raw), None
    if raw.startswith("~"):
        match = _TILDE_PREFIX_RE.match(raw)
        if match is not None:
            prefix = match.group(0)
            home = scan.known("HOME") if prefix == "~" else os.path.expanduser(prefix)
            if home is None:
                return None
            out.append(home)
            i = match.end()
        elif not any(ch in raw.split("/", 1)[0] for ch in "'\"\\$`"):
            return None  # `~+`, `~-`, `~2`: a directory the guard cannot know
    while i < n:
        ch = raw[i]
        if quote == "'":
            end = raw.find("'", i)
            if end < 0:
                return None
            out.append(raw[i:end])
            i, quote = end + 1, None
            continue
        if ch == "\\":
            nxt = raw[i + 1 : i + 2]
            if nxt != "\n":  # a backslash-newline joins lines and leaves nothing
                out.append(nxt if quote is None or nxt in '$`"\\' else "\\" + nxt)
            i += 2
            continue
        if ch == '"':
            quote = None if quote == '"' else '"'
            i += 1
            continue
        if ch == "'" and quote is None:
            quote = "'"
            i += 1
            continue
        if ch == "`":
            return None
        if ch == "$" and i + 1 < n:
            nxt = raw[i + 1]
            if nxt == "'" and quote is None:
                end = i + 2
                while end < n and raw[end] != "'":
                    end += 2 if raw[end] == "\\" else 1
                if end >= n:
                    return None
                out.append(_ansi_c_text(raw[i + 2 : end]))
                i = end + 1
                continue
            if nxt == '"' and quote is None:  # `$"…"`: a translated string, the same text here
                quote = '"'
                i += 2
                continue
            if nxt == "{":
                close = raw.find("}", i + 2)
                name = raw[i + 2 : close] if close > 0 else ""
                if not _KILL_NAME_RE.fullmatch(name):
                    return None  # `${p:-x}`, `${#p}`, `${p[@]}`, zsh flags
                i = close + 1
            elif nxt.isalpha() or nxt == "_":
                name = _KILL_NAME_RE.match(raw, i + 1).group(0)
                i += 1 + len(name)
                if raw[i : i + 1] in ("[", ":"):
                    return None  # zsh reads `$p[1]` and `$p:h` as a subscript and a modifier
            elif nxt.isdigit() or nxt in "@*#?$!-([":
                return None  # positional and special parameters, `$( )`, `$(( ))`, `$[ ]`
            else:
                out.append(ch)
                i += 1
                continue
            value = scan.known(name)
            if value is None:
                return None
            splits = not value or _KILL_SPLIT_CHARS.intersection(value) or scan.shell.bare_count("IFS")
            if quote is None and not assignment and splits:
                return None
            out.append(value)
            continue
        if assignment and quote is None and ch == ":" and raw.startswith("~", i + 1):
            return None  # bash expands a `~` after `:` in an assignment, zsh does not
        out.append(ch)
        i += 1
    return None if quote is not None else "".join(out)


def _substitution_parts(raw: str) -> list[tuple[int, int, str]]:
    """The `$( … )` and backtick substitutions the shell runs for one raw word: (start, end, body).

    Bodies inside a parameter expansion count too: zsh's `${(f)"$(pgrep -f x)"}`.
    """
    parts: list[tuple[int, int, str]] = []
    quote, i = None, 0
    while i < len(raw):
        ch = raw[i]
        if quote == "'":
            if ch == "'":
                quote = None
            i += 1
            continue
        if ch == "\\":
            i += 2
            continue
        if ch == "'" and quote is None:
            quote = "'"
            i += 1
            continue
        if ch == '"':
            quote = None if quote == '"' else '"'
            i += 1
            continue
        if raw.startswith("$((", i):
            i = _shell_expansion_end(raw, i)
            continue
        if raw.startswith("${", i):
            end = _shell_expansion_end(raw, i)
            parts += [(i + 2 + s, i + 2 + e, body) for s, e, body in _substitution_parts(raw[i + 2 : end - 1])]
            i = end
            continue
        if raw.startswith("$(", i) or ch == "`":
            end = _shell_expansion_end(raw, i)
            parts.append((i, end, raw[i + (2 if ch == "$" else 1) : end - 1]))
            i = end
            continue
        i += 1
    return parts


def _strip_xargs(argv: list[str | None]) -> list[str | None] | None:
    """The command `xargs [options]` runs, or None when argv is not an xargs call."""
    if not argv or argv[0] is None or argv[0].rsplit("/", 1)[-1] != "xargs":
        return None
    i = 1
    while i < len(argv):
        word = argv[i]
        if word is None or not word.startswith("-") or word == "-":
            break
        i += 1
        if word == "--":
            break
        if word.startswith("--"):
            continue
        for pos, letter in enumerate(word[1:], start=1):
            if letter in _XARGS_VALUE_OPTS:
                i += 1 if pos == len(word) - 1 else 0
                break
    return argv[i:]


def _kill_signal_and_targets(args: list[str | None]) -> tuple[bool, list[str | None]]:
    """(sends a real signal, targets) for the arguments of one `kill`."""
    i, sig = 0, "TERM"
    first = args[0] if args else None
    if first in ("-l", "-L"):
        return False, []
    if first in ("-s", "-n"):
        sig, i = (args[1] if len(args) > 1 and args[1] else ""), 2
    elif first and first != "--" and re.fullmatch(r"-(?:\d+|[A-Za-z][A-Za-z0-9]*)", first):
        sig, i = first[1:], 1
    if i < len(args) and args[i] == "--":
        i += 1
    return sig.upper() not in ("0", "SIG0", "ZERO"), args[i:]


def _pkill_signal(arg: str) -> str | None:
    """The signal a pkill's first argument names (pkill(1) `-signal`), or None for an option."""
    if not arg.startswith("-") or len(arg) < 2:
        return None
    body = arg[1:]
    if body.isdigit():
        return str(int(body))
    name = body.upper()
    name = name[3:] if name.startswith("SIG") else name
    return name if name in _PKILL_SIGNAL_NAMES else None


def _heredoc_texts(command: str, start: int, delimiters: list[tuple[str, bool]]) -> list[str]:
    """The bodies of sequential heredocs that begin at `start`, as `_after_heredoc_bodies` skips them."""
    texts: list[str] = []
    cursor = start
    for delimiter, strip_tabs in delimiters:
        lines: list[str] = []
        while cursor < len(command):
            line_end = command.find("\n", cursor)
            line_end = len(command) if line_end < 0 else line_end
            line = command[cursor:line_end]
            cursor = min(line_end + 1, len(command))
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                break
            lines.append(line)
        texts.append("\n".join(lines))
    return texts


def _scan_inner(
    text: str, scan: _KillScan, depth: int, child: bool = False, positional: _KillFeed | None = None
) -> _KillScan:
    """Scan text the command runs as a nested command line; return the nested scan.

    A subshell (`$( … )`, `<( … )`, `eval`) starts with the variables this shell holds; a child
    shell (`sh -c`, a shell reading stdin) with the environment only, and with `positional` as its
    positional parameters (`sh -c TEXT _ ARGS`).
    """
    inner = _KillScan(scan.shell)
    if not child:
        inner.values, inner.opaque = dict(scan.values), scan.opaque
    if positional is not None:
        inner.assign("@", positional)
    _scan_kill_text(text, inner, depth + 1)
    scan.merge(inner)
    return inner


def _word_feed(raw: str, scan: _KillScan, depth: int) -> _KillFeed:
    """Where the pids one word expands to come from: its substitutions' output and its variables."""
    feed = _KillFeed()
    outside = raw
    if "$(" in raw or "`" in raw:
        parts = _substitution_parts(raw)
        for _start, _end, body in parts:
            feed.merge(_scan_inner(body, scan, depth).output)
        for start, end, _body in sorted(parts, reverse=True):
            outside = outside[:start] + outside[end:]
    if "$" in outside:
        feed.refs |= set(_KILL_VAR_REF_RE.findall(outside)) - _KILL_PINNED_NAMES
        if _KILL_POSITIONAL_RE.search(outside):
            feed.refs.add("@")  # `"$@"`, `$*`, `$1`: what `set --` or `sh -c TEXT _ ARGS` assigned
    return feed


def _shell_script_source(argv: list[str | None]) -> tuple[str | None, bool, int]:
    """(its `-c` text, reads its commands from stdin, index of the word after the text) for one shell."""
    i = 1
    while i < len(argv):
        word = argv[i]
        if word is None:
            return None, False, len(argv)
        if word in ("-o", "+o", "-O", "+O"):
            i += 2
            continue
        if word == "--":
            i += 1
            break
        if not word.startswith(("-", "+")) or word in ("-", "+"):
            break
        if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", word):
            return (argv[i + 1] if i + 1 < len(argv) else None), False, i + 2
        if re.fullmatch(r"-[A-Za-z]*s[A-Za-z]*", word):
            return None, True, len(argv)
        i += 1
    operand = argv[i] if i < len(argv) else None
    return None, operand is None or operand in ("-", "/dev/stdin"), len(argv)


def _set_operands(argv: list[str | None]) -> tuple[int | None, str]:
    """Where a `set`'s new positional parameters start in argv, and the array `set -A` fills ("@" else).

    (None, "@") when it sets options only (`set -e`, `set -o pipefail`), which leaves them.
    """
    i = 1
    while i < len(argv):
        word = argv[i]
        if word is None:
            return None, "@"
        if word in ("--", "-"):
            return i + 1, "@"
        if word in ("-o", "+o"):
            i += 2
            continue
        if word in ("-A", "+A") and i + 1 < len(argv) and argv[i + 1]:  # zsh and ksh: `set -A name …`
            return i + 2, argv[i + 1] or "@"
        if not word.startswith(("-", "+")):
            return i, "@"
        i += 1
    return None, "@"


def _word_text(raw: str, scan: _KillScan) -> str | None:
    """A word's text as the shell passes it when the guard knows that (`~/x`, `$HOME/x`, `$'…'`),
    else as written without its quotes: a file it names, text it prints or a shell runs."""
    value = _word_value(raw, scan)
    return value if value is not None else _shlex_unquote_word(raw)


def _read_targets(prog: str, args: list[str | None]) -> set[str]:
    """The variables a `read`, `mapfile` or `readarray` sets."""
    value_opts = "dnNptu" if prog == "read" else "dnOsuCc"
    names: list[str] = []
    i = 0
    while i < len(args):
        word = args[i]
        i += 1
        if word is None:
            continue
        if not word.startswith("-") or word in ("-", "--"):
            names.append(word)
            continue
        for pos, letter in enumerate(word[1:], start=1):
            if prog == "read" and letter in "aA":  # read -a NAME: an array
                name = word[pos + 1 :] or (args[i] if i < len(args) else None)
                i += 0 if word[pos + 1 :] else 1
                if name:
                    names.append(name)
                break
            if letter in value_opts:
                i += 1 if pos == len(word) - 1 else 0
                break
    if prog == "read":
        return set(names) or {"REPLY"}
    return {names[-1]} if names else {"MAPFILE"}


def _file_operands(prog: str, raw_args: list[str]) -> list[str]:
    """The raw words naming the files a `cat`, `head`, `tail` or `tee` reads or writes.

    None for cat, head and tail means it reads its stdin.
    """
    operands: list[str] = []
    i = 0
    while i < len(raw_args):
        word = raw_args[i]
        i += 1
        if prog in ("head", "tail") and word in ("-n", "-c", "-b"):
            i += 1
        elif len(word) > 1 and word[0] in "-+":
            continue
        elif word != "-":
            operands.append(word)
    return operands


def _stage_output(stage: _KillStage, out: _KillFeed, scan: _KillScan) -> _KillFeed:
    """What a stage hands the next one: nothing when its stdout goes to a file or to stderr."""
    for fd, op, target in stage.redirects:
        if op.startswith("&>") or (fd in ("", "1") and op in (">", ">>", ">|")):
            name = _word_text(target, scan)
            if name:
                scan.write(name, out)
            return _KillFeed()
        if fd in ("", "1") and op == ">&" and target != "1":
            return _KillFeed()
    return out


def _scan_kill_text(cmd: str, scan: _KillScan, depth: int = 0) -> None:
    """Record every kill selection in one command line, its substitutions and the shell text it runs."""
    if depth > 6:
        raise ValueError("command nests too deeply to scan")
    if depth == 0:
        scan.shell.set_text(cmd)
    pipeline: list[_KillStage] = []
    stage = _KillStage()
    upstream: _KillFeed | None = None  # a closed `( … )` group's output, when a pipe follows it
    closed: _KillFeed | None = None
    waiting: list[tuple[list[_KillStage], _KillFeed | None]] = []  # pipelines whose heredocs follow
    heredocs: list[tuple[_KillStage, str, bool, bool]] = []  # (owner, delimiter, strip tabs, quoted)
    array: list[str] | None = None  # the elements of `name=( … )`
    op: str | None = None
    op_fd, op_end, skip_until, prev_end = "", -1, -1, -1
    before = ";"  # the separator before the open pipeline
    compound = groups = 0  # open compound commands; open `( … )` groups

    def add(finished: _KillStage) -> None:
        nonlocal compound
        pipeline.append(finished)
        for word in finished.words:
            if word in _KILL_OPENERS:
                compound += 1
            elif word in _KILL_CLOSERS:
                compound = max(0, compound - 1)
            elif word not in _CMD_TRANSPARENT_WORDS:
                break

    def run(stages: list[_KillStage], feed: _KillFeed | None, after: str = ";") -> None:
        if len(stages) == 1 and before in (";", "&") and after not in ("&", "|", "|&"):
            stages[0].certain = compound == 0 and groups == 0
        if heredocs:
            waiting.append((stages, feed))
        else:
            _scan_kill_pipeline(stages, scan, depth, feed)

    for kind, raw, start, end in _iter_shell_syntax(cmd):
        if start < skip_until:
            continue
        adjacent, prev_end = start == prev_end, end
        if array is not None:
            if kind == "structure" and raw == ")":
                stage.words[-1] += "(" + " ".join(array) + ")"
                array = None
            elif kind == "word":
                array.append(raw)
            continue  # newlines inside an array literal separate nothing
        if closed is not None:
            if kind == "separator" and raw in ("|", "|&"):
                upstream = closed
            else:
                scan.output.merge(closed)
            closed = None
        if kind == "word":
            stage.words.append(raw)
            op, op_fd = None, ""
            continue
        if kind == "redirect":
            if raw.startswith("<<") and not raw.startswith("<<<"):
                declared = _shell_heredoc_declaration(cmd, start)
                if declared is not None:
                    quoted = any(ch in raw[2:] for ch in "'\"\\")
                    heredocs.append((stage, declared[1], declared[2], quoted))
                op, op_fd = None, ""
            elif re.fullmatch(r"[<>&|]+", raw):
                op, op_end = raw, end
            elif op is None:
                op_fd = raw  # the descriptor the next operator redirects
            else:
                stage.redirects.append((op_fd, op, raw))
                op, op_fd = None, ""
            continue
        if kind == "structure" and raw == "(":
            if op in ("<", ">") and start == op_end:  # process substitution: `<( … )`, `>( … )`
                close = start - 1 + _shell_expansion_end("$" + cmd[start:], 0)
                stage.psubs.append((op, cmd[start + 1 : close - 1]))
                skip_until = prev_end = close
                op, op_fd = None, ""
                continue
            if adjacent and stage.words and _KILL_ASSIGNMENT_RE.fullmatch(stage.words[-1]):
                array = []  # `pids=( … )`
                continue
        op, op_fd = None, ""
        if stage.words or stage.redirects or stage.psubs:
            add(stage)
            stage = _KillStage()
        if kind == "separator" and raw in ("|", "|&"):
            continue
        after = raw if kind == "separator" and raw in ("&&", "||", "&") else ";"
        if pipeline:
            run(pipeline, upstream, after)
            pipeline, upstream = [], None
        if kind == "separator":
            before = after
        if kind == "separator" and heredocs and raw.startswith("\n"):
            bodies = _heredoc_texts(cmd, start + 1, [(name, strip) for _owner, name, strip, _q in heredocs])
            for (owner, _name, _strip, quoted), body in zip(heredocs, bodies):
                # An unquoted delimiter: the shell drops `\<newline>` and unescapes `\$`, `\``, `\\`.
                owner.heredocs.append(body if quoted else re.sub(r"\\\n|\\([$`\\])", r"\1", body))
            heredocs.clear()
            for stages, feed in waiting:
                _scan_kill_pipeline(stages, scan, depth, feed)
            waiting.clear()
        if kind == "structure":
            groups = groups + 1 if raw == "(" else max(0, groups - 1)
            if raw == "(":
                scan.groups.append(scan.output)
                scan.output = _KillFeed()
            elif scan.groups:
                closed, scan.output = scan.output, scan.groups.pop()
    if array is not None:
        raise ValueError("unbalanced array assignment")
    if stage.words or stage.redirects or stage.psubs:
        add(stage)
    if pipeline:
        run(pipeline, upstream)
    if closed is not None:
        scan.output.merge(closed)
    for stages, feed in waiting:
        _scan_kill_pipeline(stages, scan, depth, feed)


def _scan_kill_pipeline(
    stages: list[_KillStage], scan: _KillScan, depth: int, upstream: _KillFeed | None = None
) -> None:
    feed = upstream if upstream is not None else _KillFeed()
    for index, stage in enumerate(stages):
        if index == 0 and stage.words and stage.words[0] in ("{", "do"):
            scan.groups.append(scan.output)  # `{ …; } | xargs kill`, `done | xargs kill`
            scan.output = _KillFeed()
        feed = _scan_kill_stage(stage, feed, scan, depth)
    scan.output.merge(feed)


def _scan_kill_stage(stage: _KillStage, feed: _KillFeed, scan: _KillScan, depth: int) -> _KillFeed:
    """Scan one simple command that reads `feed` on its pipe; return what it prints."""
    raw_words = stage.words
    words = [raw if _PLAIN_RAW_WORD_RE.fullmatch(raw) else _shlex_unquote_word(raw) for raw in raw_words]
    scan.sudo |= any(word is not None and word.rsplit("/", 1)[-1] in ("sudo", "doas") for word in words)
    inp = _KillFeed()  # what it reads: its pipe, process substitutions, here-strings, heredocs, files
    inp.merge(feed)
    for direction, body in stage.psubs:
        inner = _scan_inner(body, scan, depth)
        if direction == "<":
            inp.merge(inner.output)
    for fd, op, target in stage.redirects:
        if op == "<<<":
            inp.merge(_word_feed(target, scan, depth))
            inp.texts.append(_word_text(target, scan) or "")
        elif op in ("<", "<>") and fd in ("", "0"):
            name = _word_text(target, scan)
            if name:
                inp.files.append(name)
    inp.texts += stage.heredocs
    if not raw_words:  # `$(< pids.txt)` reads the file as `$(cat pids.txt)` does (zsh: any `< f`)
        out = _KillFeed()
        out.files += inp.files
        return _stage_output(stage, out, scan)
    if raw_words and raw_words[0] in ("}", "done"):  # a group or loop body closes: its output flows on
        group = _KillFeed()
        if scan.groups:
            group, scan.output = scan.output, scan.groups.pop()
        if raw_words[0] == "done":
            scan.loop_feed.merge(inp)  # `done < <(pgrep …)`, `done < pids.txt`
        return _stage_output(stage, group, scan)
    lead = 0  # reserved words before the assignments: `do p=$(pgrep …)`, `if pids=$(pgrep …); then`
    while lead < len(raw_words) and raw_words[lead] in _KILL_RESERVED_LEAD:
        lead += 1
    n_assign = lead
    while n_assign < len(raw_words) and _KILL_ASSIGNMENT_RE.match(raw_words[n_assign]):
        n_assign += 1
    _assigns, argv = _split_command_prefix(words)
    stripped = _strip_xargs(argv)
    if stripped is not None:
        _assigns, argv = _split_command_prefix(stripped)
    program_at = len(raw_words) - len(argv)
    raw_argv = raw_words[program_at:]
    prog = argv[0].rsplit("/", 1)[-1] if argv and argv[0] else ""
    sends, targets = _kill_signal_and_targets(argv[1:]) if prog == "kill" else (False, [])
    first_target = len(raw_words) - len(targets)
    for_list = 3 if len(words) > 2 and words[0] == "for" and words[2] == "in" else None
    printed = prog in ("echo", "printf")
    # Where an assignment's value is known from here on: a stage of assignments alone (with a
    # command after them, they set its environment only) or a declarer without options, that
    # always runs in this shell (`stage.certain`). Anywhere else the value is unknown.
    shell_sets = stage.certain and lead == 0 and n_assign == len(raw_words)
    declarer_sets = (
        stage.certain
        and program_at == 0
        and prog in _KILL_SETTING_DECLARERS
        and not any(word is None or word.startswith(("-", "+")) for word in words[1:])
    )
    # Words that become positional parameters: a `set`'s operands (or a `set -A` array's), and the
    # arguments after `sh -c TEXT NAME`, which the child shell reads as $1, $2, ….
    positional_at, positional_name = len(raw_words), "@"
    shell_text, shell_reads_stdin, after_text = None, False, len(argv)
    if prog == "set":
        operands_at, positional_name = _set_operands(argv)
        if operands_at is not None:
            positional_at = program_at + operands_at
    elif prog in _PKILL_SHELLS:
        shell_text, shell_reads_stdin, after_text = _shell_script_source(argv)
        positional_at = program_at + after_text + 1
        if shell_text is not None:  # the text as this shell passes it: `sh -c "pkill -f $d"`, `$'…'`
            shell_text = _word_text(raw_words[program_at + after_text - 1], scan) or shell_text
    child_args = _KillFeed()
    out = _KillFeed()
    for index, raw in enumerate(raw_words):
        assigned = None
        if lead <= index < n_assign or (prog in _KILL_DECLARERS and index > program_at):
            assigned = _KILL_ASSIGNMENT_RE.match(raw)
        is_target = sends and index >= first_target
        listed = for_list is not None and index >= for_list
        positional = index >= positional_at
        if not (assigned or is_target or listed or printed or positional) and "$(" not in raw and "`" not in raw:
            continue  # runs nothing and hands no pids on
        value = _word_feed(raw, scan, depth)
        if positional:
            if prog == "set":
                scan.assign(positional_name, value)  # `set -- $(pgrep …); kill "$@"`
            else:
                child_args.merge(value)
            continue
        if assigned:
            name = assigned.group(1)
            scan.assign(name, value)
            text = (words[index] or "").split("=", 1)[-1]
            if _kill_word_at_command_position(text):
                scan.shell.kill_texts[name] = text  # `cmd="pkill -f x"; $cmd`
            rest = raw[assigned.end() :]
            sets = (shell_sets if index < n_assign else declarer_sets) and not assigned.group(0).endswith("+=")
            known = sets and not rest.startswith("(")  # `p=( … )` is an array
            scan.values[name] = _word_value(rest, scan, assignment=True) if known else None
        elif listed:
            scan.assign(words[1] or "", value)  # `for p in $(pgrep …)`
        elif is_target:
            scan.consume(value, f"`kill {raw[:60]}`")
        elif printed and index > program_at:
            out.merge(value)
        else:
            out.pgreps += value.pgreps  # pids handed to another program may come out of it
    if argv and argv[0] is not None and argv[0].startswith("$"):  # a command named by a variable
        named = re.fullmatch(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?", argv[0])
        if named and named.group(1) in scan.shell.kill_texts:
            out.merge(_scan_inner(scan.shell.kill_texts[named.group(1)], scan, depth).output)
        return _stage_output(stage, out, scan)
    if not prog or prog in _KILL_KEYWORDS:
        return _stage_output(stage, out, scan)
    if prog in ("source", "."):
        scan.opaque = True  # the file may set any variable
    if prog in _PKILL_SHELLS:
        if shell_text is not None:
            inner = _scan_inner(shell_text, scan, depth, child=True, positional=child_args)
            out.merge(inner.output)
            if stripped is not None and inner.kills:  # `xargs sh -c 'kill …'` kills what xargs reads
                scan.consume(inp, f"`xargs {prog} -c`")
        elif shell_reads_stdin:
            for body in inp.texts:
                out.merge(_scan_inner(body, scan, depth, child=True).output)
            if inp.other and not inp.texts:
                scan.unknown.append(f"`{prog}` runs what {_kill_programs(inp.other)} prints")
        return _stage_output(stage, out, scan)
    if prog == "eval":
        text = " ".join(word for raw in raw_argv[1:] if (word := _word_text(raw, scan)) is not None)
        out.merge(_scan_inner(text, scan, depth).output)
        if any("$" in raw or "`" in raw for raw in raw_argv[1:]):
            scan.opaque = True  # text known only when it runs may set any variable
        return _stage_output(stage, out, scan)
    if prog in ("pkill", "killall"):
        scan.selections.append((prog, [_word_value(raw, scan) for raw in raw_argv[1:]], raw_argv[1:]))
        scan.kills += 1
        return _stage_output(stage, out, scan)
    if prog in ("pgrep", "ps"):  # `ps aux | grep … | xargs kill` selects by text, as pkill -f does
        if stripped is not None:
            out.merge(inp)  # `pgrep … | xargs ps -p` prints what the upstream pgrep found
        selected = [_word_value(raw, scan) for raw in raw_argv[1:]] if prog == "pgrep" else None
        out.pgreps.append((selected, raw_argv[1:]))
        return _stage_output(stage, out, scan)
    if prog in _KILL_READERS:
        names = _read_targets(prog, argv[1:])
        if words[0] in ("while", "until"):
            scan.loop_feed.merge(inp)
            scan.loop_vars |= names
        else:
            for name in names:
                scan.assign(name, inp)
        return _KillFeed()
    if prog == "kill":
        if sends:
            scan.kills += 1
            scan.kill_all |= "-1" in targets
            if stripped is not None:
                scan.consume(inp, "`xargs kill`")
        return _stage_output(stage, out, scan)
    if printed:  # text a shell may read: `printf 'pkill -f x\n' | sh`, `echo $'…' | sh`
        args = [word for raw in raw_argv[1:] if (word := _word_text(raw, scan)) is not None]
        if prog == "echo":
            out.texts += _echo_texts(args)
        else:
            out.texts.append(_printf_text(args[1:] if args[:1] == ["--"] else args))
        if stripped is not None:
            out.merge(inp)
        return _stage_output(stage, out, scan)
    if prog in _PID_FILE_READERS:
        operands = [name for raw in _file_operands(prog, raw_argv[1:]) if (name := _word_text(raw, scan))]
        if operands:
            out.files += operands
        else:
            out.merge(inp)
        return _stage_output(stage, out, scan)
    if prog == "jobs":
        return _stage_output(stage, out, scan)
    if prog == "tee":  # `pgrep … | tee pids.txt`: each file holds what tee reads
        for raw in _file_operands(prog, raw_argv[1:]):
            name = _word_text(raw, scan)
            if name:
                scan.write(name, inp)
    if prog in _PID_FILTERS:
        out.merge(inp)
        return _stage_output(stage, out, scan)
    out.pgreps += inp.pgreps  # `pgrep … | python3 pick.py | xargs kill`
    out.refs |= inp.refs
    out.files += inp.files
    out.other += inp.other + [prog]
    return _stage_output(stage, out, scan)


def _pgrep_replay(tool: str, argv: list[str | None] | None, raw_argv: list[str]) -> list[str] | None:
    """The pgrep (killall: killall) arguments that select what this call signals.

    None when the call cannot reach outside the caller's tree: it sends signal 0, prints a list,
    is itself a dry run, or is pinned to recorded PIDs as `kill <pid>` and `kill -- -<pgid>` are
    (`-F`, a numeric `-P` or `-g` other than 1, the caller's own children `-P $$`) without `-v`,
    which turns a pin into every other process. `argv` holds the words as the shell passes them
    (`_word_value`); a word it could not know (None) cannot be replayed.
    """
    if argv is None:
        raise _DryRunError("a kill takes its pids from ps output, which only pgrep could replay")
    if len(argv) != len(raw_argv):
        raise _DryRunError(f"a {tool} argument holds a command substitution")
    if tool == "killall":
        if any(a in ("-l", "-help", "-s", "-d") for a in argv):
            return None
        unknown = [r for r, a in zip(raw_argv, argv) if a is None]
        if unknown:
            raise _DryRunError(f"the killall argument {unknown[0]} holds a shell expansion")
        return ["-s"] + [a for a in argv if a is not None and a != "-I"]
    i = 0
    if tool == "pkill" and argv and argv[0] is not None:
        sig = _pkill_signal(argv[0])
        if sig == "0":
            return None
        i = 1 if sig is not None else 0
    out: list[str] = []
    pins: list[tuple[str, str | None]] = []  # (raw, value) of the options that pin to recorded PIDs
    inverted = False
    while i < len(argv):
        word = argv[i]
        if word is None:  # an option or a pattern: the guard cannot tell
            raise _DryRunError(f"the {tool} argument {raw_argv[i]} holds a shell expansion")
        if word == "--":
            i += 1
            break
        if not word.startswith("-") or word == "-":
            break  # pgrep(1) parses with getopt: options end at the first pattern
        i += 1
        kept = ""
        for pos in range(1, len(word)):
            letter = word[pos]
            if letter not in _PGREP_VALUE_OPTS:
                inverted |= letter == "v"
                if letter not in _PGREP_OUTPUT_OPTS:
                    kept += letter
                continue
            value: str | None = word[pos + 1 :]
            raw_value = value or ""
            if not value:
                if i >= len(argv):
                    raise _DryRunError(f"{tool} -{letter} has no value")
                value, raw_value = argv[i], raw_argv[i]
                i += 1
            if letter == "F" or (letter == "P" and raw_value.strip("'\"") in _PGREP_OWN_CHILDREN):
                pins.append((raw_value, value))
            elif (
                letter in "Pg"
                and value is not None
                and re.fullmatch(r"\d+(?:,\d+)*", value)
                and 1 not in {int(v) for v in value.split(",")}
            ):
                pins.append((raw_value, value))  # a recorded parent or group; -P 1 is every orphan on the Mac
            elif value is None:
                raise _DryRunError(f"the {tool} -{letter} value {raw_value} holds a shell expansion")
            if letter not in _PGREP_OUTPUT_OPTS:
                if kept:
                    out.append("-" + kept)
                    kept = ""
                out += ["-" + letter, value or ""]
            break
        if kept:
            out.append("-" + kept)
    if pins and not inverted:
        return None
    if any(value is None or raw.strip("'\"") in _PGREP_OWN_CHILDREN for raw, value in pins):
        raise _DryRunError(f"{tool} -v inverts a pin the guard cannot replay")
    patterns: list[str] = []
    for raw, pattern in zip(raw_argv[i:], argv[i:]):
        if pattern is None:
            raise _DryRunError(f"the {tool} pattern {raw} holds a shell expansion")
        patterns.append(pattern)
    return out + (["--"] + patterns if patterns else [])


def _pkill_process_table() -> dict[int, tuple[int, int, str, str]]:
    """pid -> (ppid, uid, etime, comm): one ps call, no argument vectors."""
    proc = subprocess.run(
        ["/bin/ps", "-axo", "pid=,ppid=,uid=,etime=,comm="], capture_output=True, text=True, timeout=10
    )
    if proc.returncode != 0:
        raise _DryRunError(f"ps exited {proc.returncode}")
    table: dict[int, tuple[int, int, str, str]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5 and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), int(parts[2]), parts[3], parts[4])
    if os.getpid() not in table:
        raise _DryRunError("ps did not list this hook")
    return table


def _is_agent_process(pid: int, comm: str) -> bool:
    """An agent CLI whose Bash calls run this hook.

    Claude Code: `claude`, a versioned binary (`2.1.319`), or node/bun running one. Codex: its
    native `codex` binary, or node running codex.js; ~/.codex/hooks.json sends Codex's Bash calls
    through agent-infra's codex_hook_shim.py to this dispatcher.
    """
    base = comm.rsplit("/", 1)[-1]
    if base in ("claude", "codex") or _AGENT_VERSION_COMM.fullmatch(base):
        return True
    if base not in ("node", "bun"):
        return False
    proc = subprocess.run(["/bin/ps", "-o", "args=", "-p", str(pid)], capture_output=True, text=True, timeout=10)
    script = proc.stdout.split()[1:2]
    return bool(script) and ("claude" in script[0] or script[0].rsplit("/", 1)[-1] in ("codex", "codex.js"))


def _pkill_caller_tree(table: dict[int, tuple[int, int, str, str]]) -> set[int]:
    """The nearest Claude or Codex ancestor of this hook and its descendants (the hook's parent without one)."""
    root, pid, seen = os.getppid(), os.getppid(), set()
    while pid in table and pid > 1 and pid not in seen:
        seen.add(pid)
        if _is_agent_process(pid, table[pid][3]):
            root = pid
            break
        pid = table[pid][0]
    children: dict[int, list[int]] = {}
    for child, (parent, _uid, _etime, _comm) in table.items():
        children.setdefault(parent, []).append(child)
    tree, stack = {root}, [root]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in tree:
                tree.add(child)
                stack.append(child)
    return tree


def _pkill_matches(tool: str, replay: list[str]) -> set[int]:
    if sys.platform != "darwin":
        raise _DryRunError(f"the replay knows macOS {tool} only, not {sys.platform}")
    binary = "/usr/bin/killall" if tool == "killall" else "/usr/bin/pgrep"
    proc = subprocess.run([binary, *replay], capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
    if tool == "killall":
        pids = {int(m) for m in re.findall(r"^kill -\S+ (\d+)$", proc.stdout, re.M)}
        if proc.returncode == 0 or (proc.returncode == 1 and "No matching processes" in proc.stdout + proc.stderr):
            return pids
    else:
        if proc.returncode in (0, 1):
            return {int(tok) for tok in proc.stdout.split() if tok.isdigit()}
    reason = (proc.stderr.strip().splitlines() or [""])[0][:160]
    raise _DryRunError(f"{binary} exited {proc.returncode}: {reason}")


def _etime_seconds(etime: str) -> int:
    """ps etime `[[dd-]hh:]mm:ss` in seconds; unreadable values sort last."""
    try:
        days, _sep, clock = etime.rpartition("-")
        parts = [int(p) for p in clock.split(":")]
        parts = [0] * (3 - len(parts)) + parts
        return int(days or 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        return 1 << 62


def _pkill_degraded(reason: str, cmd: str) -> GateResult:
    _log_trigger("pkill-guard", "warn", f"degraded: {reason}"[:200], cmd)
    msg = (
        f"[DEGRADED] pkill guard could not dry-run: {reason}. Nothing checked what this kill "
        "selects. Run its selection as `pgrep -f '<pattern>'` (or `killall -s`) first, and kill "
        "what you started by its recorded PID."
    )
    return GateResult(0, "", json.dumps({"additionalContext": msg}))


def gate_pkill_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
    except Exception:
        return GateResult(0, "", "")
    if not isinstance(cmd, str) or not _kill_word_at_command_position(cmd):
        return GateResult(0, "", "")
    scan = _KillScan()
    try:
        _scan_kill_text(cmd, scan)
        scan.resolve()
    except ValueError as exc:  # the lexer refused the text; a pid kill needs no advisory
        if not _KILL_SELECTING_WORDS_RE.search(cmd):
            return GateResult(0, "", "")
        return _pkill_degraded(f"the command did not parse ({exc})", cmd)
    except Exception as exc:  # fail loud, never silent: the gate's own bug is an advisory
        return _pkill_degraded(f"the scan failed ({type(exc).__name__}: {exc})", cmd)
    if scan.kill_all:
        _log_trigger("pkill-guard", "block", "kill -1", cmd)
        return GateResult(
            2,
            "BLOCKED by the pkill guard: `kill` with target -1 signals every process you own, "
            "this agent's terminal and every other session included. Kill what you started by "
            "its recorded PID (or its process group, `kill -TERM -- -<pgid>`).\n",
            "",
        )
    if not scan.selections and not scan.unknown:
        return GateResult(0, "", "")
    # A selection the guard cannot replay degrades to an advisory only when no other one blocks.
    unreplayable: list[str] = []
    matched: list[tuple[str, list[str], set[int]]] = []
    table: dict[int, tuple[int, int, str, str]] = {}
    tree: set[int] = set()
    try:
        for tool, argv, raw_argv in scan.selections:
            try:
                replay = _pgrep_replay(tool, argv, raw_argv)
                if replay is not None and argv is not None:
                    matched.append((tool, raw_argv, _pkill_matches(tool, replay)))
            except _DryRunError as exc:
                unreplayable.append(str(exc))
        if any(pids for _tool, _argv, pids in matched):
            table = _pkill_process_table()
            tree = _pkill_caller_tree(table)
    except _DryRunError as exc:
        return _pkill_degraded(str(exc), cmd)
    except Exception as exc:  # fail loud, never silent: the gate's own bug is an advisory
        return _pkill_degraded(f"{type(exc).__name__}: {exc}", cmd)
    uid = os.getuid()
    victims: dict[int, str] = {}
    for tool, raw_argv, pids in matched:
        for pid in sorted(pids):
            row = table.get(pid)
            if row is None or pid in tree or (row[1] != uid and not scan.sudo):
                continue  # gone already, the caller's own, or not signalable without sudo
            victims.setdefault(pid, " ".join([tool, *raw_argv]))  # as the agent wrote it
    if not victims:
        reasons = unreplayable + scan.unknown
        if reasons:
            return _pkill_degraded("; ".join(dict.fromkeys(reasons)), cmd)
        return GateResult(0, "", "")
    _log_trigger("pkill-guard", "block", f"{len(victims)} outside the caller's tree", cmd)
    lines = []
    newest_first = sorted(victims, key=lambda pid: (_etime_seconds(table[pid][2]), pid))
    for pid in newest_first[:_PKILL_LISTED_VICTIMS]:
        _ppid, _uid, etime, comm = table[pid]
        lines.append(f"  pid {pid:<7} etime {etime:<12} {comm.rsplit('/', 1)[-1]}")
    if len(victims) > _PKILL_LISTED_VICTIMS:
        lines.append(f"  … and {len(victims) - _PKILL_LISTED_VICTIMS} more")
    selections = sorted(set(victims.values()))
    msg = (
        f"BLOCKED by the pkill guard: {' and '.join(f'`{s}`' for s in selections)} would also "
        f"signal {len(victims)} process(es) outside this agent's own process tree:\n"
        + "\n".join(lines)
        + "\n\npgrep, pkill and killall -m patterns are extended regular expressions (`|` is "
        "alternation) matched against every process on this Mac; with -f they match the whole "
        "argument list. On 2026-11-07 `pkill -f \"grep -qE \\\"passed|failed|error\\\"\"` killed "
        "every lane and bgrun supervisor here. Kill what you started by its recorded PID: "
        "`kill <pid>` (`$!` after a launch, a .pid file), `kill -TERM -- -<pgid>` for a job's "
        "group, `lane stop <name>`, or TaskStop for your own background task. Or narrow the "
        "pattern until `pgrep -f '<pattern>'` lists only processes you started. To stop a "
        "program the user named, read what `pgrep -lx <name>` lists and kill those PIDs.\n"
    )
    return GateResult(2, msg, "")


# --- 31. opus-concurrency-advisory (ADVISORY, no if) -------------------------
# Pattern and threshold come from arc-agi's former `just opus-load` recipe
# (measured: 6+ concurrent streams -> 72% dead rounds, arc-agi 2026-07-18
# Stage-0 burn; throttle "keep <=2-3; stagger launches above that"). arc-agi
# was removed, so this is now the only definition. 2026-09-22: widened from
# opus-4-8 to every Opus 4/5 id; the old pattern missed Opus 5 and 5.5.
_OPUS_LOAD_PGREP_PATTERN = "claude-opus-[45]|claude-fable-5|claude -p"
_OPUS_TRIGGER_LLMX_RE = re.compile(r"\bllmx\b", re.I)
_OPUS_TRIGGER_MODEL_RE = re.compile(r"claude-opus-[45]|claude-fable-5", re.I)
_OPUS_TRIGGER_CLAUDE_P_RE = re.compile(r"(?:^|[;&|(]\s*)claude\s+-p\b")


def gate_opus_concurrency_advisory(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return GateResult(0, "", "")
    is_llmx_opus = bool(_OPUS_TRIGGER_LLMX_RE.search(cmd) and _OPUS_TRIGGER_MODEL_RE.search(cmd))
    is_claude_p = bool(_OPUS_TRIGGER_CLAUDE_P_RE.search(cmd))
    if not (is_llmx_opus or is_claude_p):
        return GateResult(0, "", "")
    pgrep_bin = os.environ.get("OPUS_LOAD_PGREP_BIN") or "pgrep"
    try:
        out = subprocess.run(
            [pgrep_bin, "-f", _OPUS_LOAD_PGREP_PATTERN],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        count = len([ln for ln in out.splitlines() if ln.strip()])
    except Exception:
        return GateResult(0, "", "")
    if count < 3:
        return GateResult(0, "", "")
    _log_trigger("opus-concurrency-advisory", "warn", f"count={count} cmd={cmd[:80]}", cmd)
    msg = (
        f"ADVISORY: {count} concurrent opus-family streams already live (pgrep -f "
        f"'{_OPUS_LOAD_PGREP_PATTERN}') — "
        "measured: 6+ concurrent -> 72% dead rounds (arc-agi 2026-07-18 Stage-0 burn: heavy "
        "induction calls slow past --llm-timeout and die as EMPTY/nonzero 'transport errors' "
        "under contention). Stagger or throttle this launch (throttle: keep <=2-3 concurrent; "
        "feedback_concurrency_throttle)."
    )
    out_json = json.dumps({"additionalContext": msg})
    return GateResult(0, "", out_json)


# ─────────────────────────────────────────────────────────────────────────
# MANIFEST — EXACT settings.json order. Each entry: name, if_pattern (None =
# always run), run(raw_payload)->GateResult.
# ─────────────────────────────────────────────────────────────────────────

# Scratch trees: lane worktrees, the repo's cache directory (lane briefs, batch candidates,
# gate logs) and DeepSeek lane clones under ~/.cache/oc-lanes.
_WORKTREE_CD_RE = re.compile(
    r"(?:^|[\s;&|])cd\s+[\"']?([^\s\"';&|()]*(?:\.claude/(?:worktrees|cache)|\.cache/oc-lanes)"
    r"(?:/[^\s\"';&|()]*)?)(?=$|[\s\"';&|()])"
)
# Any persistent cd target, quoted or bare, for the dynamic check below.
_CD_TARGET_RE = re.compile(r"(?:^|[\s;&|])cd\s+(\"[^\"]*\"|'[^']*'|[^\s\"';&|()]+)")
# A quoted string is an argument to something else (`echo "…cd $X…"`, `ssh h 'cd $X'`,
# `bash -c "cd $X"`) unless it directly follows cd, and none of those move this shell.
_QUOTED_ARG_RE = re.compile(r"(\bcd\s+)?(\"[^\"]*\"|'[^']*')")
_HOME_PREFIX_RE = re.compile(r"^(?:\$HOME|\$\{HOME\})(?=/|$)")
# A here-document body is data (a script being written), never this shell's commands.
_HEREDOC_RE = re.compile(r"<<-?\s*([\"']?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL)


def _dynamic_cd_target(cmd: str) -> str | None:
    """The first persistent ``cd`` target whose value this guard cannot read, or None.

    ``cd $WT && ...`` into a lane worktree passed the literal ``.claude/worktrees`` check:
    the variable hides the path. Any ``$`` or backtick left after a leading ``$HOME``
    counts; ``$HOME`` alone names a fixed place.
    """
    for match in _CD_TARGET_RE.finditer(cmd):
        target = match.group(1)
        if target[:1] in "\"'":
            target = target[1:-1]
        rest = _HOME_PREFIX_RE.sub("", target)
        if "$" in rest or "`" in rest:
            return target
    return None


def gate_worktree_cd_guard(raw_payload: str) -> GateResult:
    """Neutralize a persistent ``cd`` into a lane worktree (``.claude/worktrees/...``).

    The Bash tool's cwd persists across calls, so ``cd <worktree> && ...`` leaves
    every later command — ``git log`` ranges, ``uv run``, file swaps — running
    against the worktree instead of main. Genomics catalog M122; recurred
    2026-09-02 in one hour: a false-empty ``git log`` bisect, a 373 MB venv built
    inside the worktree, and an edit that landed in the wrong tree. A subshell
    ``(cd <wt> && ...)`` cannot persist and passes; ``git -C <wt>`` and absolute
    paths are the intended spellings. A persistent ``cd`` to a target the guard
    cannot read (``cd $WT``, ``cd "$(...)"``) is treated the same, since it may be a
    worktree. Since 2026-10-26 the command is rewritten into a subshell instead of blocked.
    The same holds for ``.claude/cache/...`` and ``~/.cache/oc-lanes/...``: one genomics
    session (1cce6699, 2026-10-22) made five persistent cds into those trees, past
    this guard, each caught only by the harness's working-directory notice.
    """
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    # A subagent's cwd resets between Bash calls, so its cd cannot persist; 554 of 1,054
    # blocks landed there, each a wasted turn that prevented nothing (hook audit 2026-10-24).
    if data.get("agent_id"):
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if "cd" not in cmd:
        return GateResult(0, "", "")
    # Here-document bodies and quoted arguments of other commands go first, so a quoted
    # paren cannot unbalance the subshell strip. A cd inside ( ... ) or $( ... ) cannot
    # change the persistent cwd: strip parenthesised groups innermost-first before matching.
    stripped = _HEREDOC_RE.sub(" ", cmd)
    vars_mod = _load_module(HOOKS_DIR / "shell_literal_vars.py", "shell_literal_vars")
    stripped = vars_mod.expand_literal_vars(stripped)
    stripped = _QUOTED_ARG_RE.sub(lambda m: m.group(0) if m.group(1) else " ", stripped)
    for _ in range(8):
        reduced = re.sub(r"\([^()]*\)", "", stripped)
        if reduced == stripped:
            break
        stripped = reduced
    match = _WORKTREE_CD_RE.search(stripped)
    if match is None:
        dynamic = _dynamic_cd_target(stripped)
        if dynamic is None:
            return GateResult(0, "", "")
        return _subshell_rewrite(data, cmd, dynamic)
    return _subshell_rewrite(data, cmd, match.group(1))


def _subshell_rewrite(data: dict, cmd: str, target: str) -> GateResult:
    """Run the command in a subshell so its cd cannot persist, and tell the agent so.

    Blocking cost a wasted round trip per fire (591 blocks in 7 days to 2026-10-26, each
    re-reading ~240K of context) for the same protection. The note matters: an agent that
    believes it moved would run its next relative command in main.
    """
    ti = dict(data.get("tool_input") or {})
    ti["command"] = f"(\n{cmd}\n)"
    cwd = data.get("cwd") or "the session directory"
    note = (
        f"worktree-cd-guard ran this command in a subshell, so `cd {target}` did not persist: "
        f"the next Bash call still starts in {cwd}. Keep using absolute paths or "
        f"`git -C {target} ...` there (genomics catalog M122)."
    )
    _log_trigger("worktree-cd-guard", "rewrite", cmd[:80], cmd)
    out = json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "updatedInput": ti, "additionalContext": note}})
    return GateResult(0, "", out)


# --- remote-delete-guard (BLOCKER, no if) --------------------------------------
_REMOTE_DELETE_PREFIX_WORDS = {"!", "sudo", "time", "command", "exec", "nohup", "env"}
_REMOTE_DELETE_SHELLS = {"bash", "sh", "zsh"}


def _remote_delete_hit(words: list[str], depth: int = 0) -> str | None:
    """Name the destructive call in one parsed command, or None.

    Recurses one level into ``bash -c '<cmd>'`` and ``xargs <cmd>`` so the
    wrapped spelling of the same call is caught too.
    """
    i = 0
    while i < len(words) and (
        words[i] in _REMOTE_DELETE_PREFIX_WORDS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[i])
    ):
        i += 1
    if i >= len(words):
        return None
    prog = words[i].rsplit("/", 1)[-1]
    rest = words[i + 1 :]
    if depth == 0 and prog in _REMOTE_DELETE_SHELLS and "-c" in rest:
        inner = rest[rest.index("-c") + 1 : rest.index("-c") + 2]
        for seg, _s, _e in _iter_shell_segments(inner[0] if inner else ""):
            try:
                hit = _remote_delete_hit(shlex.split(seg), depth + 1)
            except ValueError:
                continue
            if hit:
                return hit
        return None
    if depth == 0 and prog == "xargs":
        cmd_start = next((k for k, w in enumerate(rest) if not w.startswith("-")), None)
        return None if cmd_start is None else _remote_delete_hit(rest[cmd_start:], depth + 1)
    short = [w for w in rest if w.startswith("-") and not w.startswith("--")]
    if prog == "history" and any("c" in w[1:] for w in short):
        return "`history -c` (clears the shell's command history)"
    if prog == "gsutil":
        if "rb" in rest:
            return "`gsutil rb` (removes a bucket)"
        if "rm" in rest:
            after = rest[rest.index("rm") + 1 :]
            if any(re.match(r"^-[a-zA-Z]*[rR]", w) for w in after) or any("**" in w for w in after):
                return "`gsutil rm -r` (recursive object deletion)"
    if prog == "gcloud" and rest[:2] == ["storage", "rm"]:
        if "--recursive" in rest or any(re.match(r"^-[a-zA-Z]*[rR]", w) for w in rest):
            return "`gcloud storage rm --recursive` (recursive object deletion)"
    if prog == "gcloud" and rest[:3] == ["storage", "buckets", "delete"]:
        return "`gcloud storage buckets delete` (removes a bucket)"
    if prog == "aws" and rest[:2] == ["s3", "rm"] and "--recursive" in rest:
        return "`aws s3 rm --recursive` (recursive object deletion)"
    if prog == "aws" and rest[:2] == ["s3", "rb"]:
        return "`aws s3 rb` (removes a bucket)"
    return None


def gate_remote_delete_guard(raw_payload: str) -> GateResult:
    """Block recursive cloud-storage deletes and shell-history clearing.

    Claude Opus 5.5 System Card §6.3.1 (2026-09-22): internal snapshots issued
    hallucinated destructive calls with no task reason — ``history -c …``
    described as a "no-op check of shell", and a fabricated agent message asking
    for ``gsutil -m rm -r [path]`` "to clear the stale cache". The card credits
    auto mode with stopping these; sessions here run with bypassed permissions,
    so this gate is the remaining check. agentlogs, 30 days to 2026-09-22
    (45,255 shell calls, all vendors): zero real gsutil / gcloud storage / aws s3
    recursive deletes and zero ``history -c``, so the block costs nothing today.
    ``modal volume rm`` is deliberately not covered: 17 receipted genomics
    cleanups in the same window.
    """
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not any(tok in cmd for tok in ("gsutil", "gcloud", "aws", "history")):
        return GateResult(0, "", "")
    try:
        segments = list(_iter_shell_segments(cmd))
    except ValueError:
        return GateResult(0, "", "")
    for seg, _start, _end in segments:
        try:
            words = shlex.split(seg)
        except ValueError:
            continue
        hit = _remote_delete_hit(words)
        if hit is None:
            continue
        msg = (
            f"BLOCK: {hit}. The Claude Opus 5.5 system card (§6.3.1) records rare "
            "hallucinated destructive calls of exactly this shape — `history -c` framed as "
            "a no-op, a fabricated request to `gsutil -m rm -r` a cache — and this machine "
            "runs without auto mode's classifier. agentlogs shows no legitimate use in 30 "
            "days.\nIf the deletion is really intended, stop and ask the operator to run it "
            "with `! <command>`; do not respell the command to get past this guard.\n"
        )
        _log_trigger("remote-delete-guard", "block", hit, cmd)
        return GateResult(2, msg, "")
    return GateResult(0, "", "")


# --- 0b. secret-path-guard (BLOCKER, no if) — imports sidecar -------------------
# Replaces the two settings.json `Read()` deny rules (~/.config/sops/age/keys.txt,
# ~/.config/secrets/**). Those made the auto-mode permission classifier stop for a HUMAN
# whenever a Bash read path could not be resolved ("… after a cd would search a directory
# that cannot be determined here, and a Read() deny rule is configured") — a lane blocked on
# it while the operator was AFK, 2026-09-04. Deterministic here, never a prompt; the Read /
# Grep / Glob twin is pretool-secret-path-read-guard.py. Scope + calibration live in the
# sidecar docstring (0 fires over 1,151 real session commands; 2 over 4,570 across 12
# sessions, both quoting the protected path literally).


def gate_secret_path_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd or ".config" not in cmd:
            return GateResult(0, "", "")
        mod = _load_module(HOOKS_DIR / "pretool_secret_path_guard.py", "pretool_secret_path_guard")
        token = mod.offending_secret_path(cmd)
        if token:
            _log_trigger("secret-path-guard", "block", token, cmd)
            return GateResult(2, mod.reason(token, "Bash"), "")
        return GateResult(0, "", "")
    except Exception:
        return GateResult(0, "", "")


# --- simple-command view for semantic gates ------------------------------------
# Wrappers that run the next word as the command. `command -v/-V` only queries.
_CMD_WRAPPER_VALUE_OPTS = {
    "exec": {"-a"},
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "timeout": {"-k", "--kill-after", "-s", "--signal"},
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U"},
    # macOS wrappers that run their operand: lane workers run under /usr/bin/nice, bgrun jobs
    # under caffeinate; `lockf [-t s] FILE cmd`, `arch -arch x86_64 cmd`.
    "nice": {"-n"},
    "caffeinate": {"-t", "-w"},
    "lockf": {"-t"},
    "arch": {"-arch", "-d", "-e"},
    # `taskpolicy -c utility cmd`, GNU timeout from coreutils, and /usr/bin/time by path (the
    # reserved word `time` is handled below).
    "taskpolicy": {"-c", "-d", "-g", "-G", "-t", "-l", "-p"},
    "gtimeout": {"-k", "--kill-after", "-s", "--signal"},
    "time": {"-o"},
    # GNU stdbuf (coreutils' gstdbuf on macOS), util-linux setsid, and doas, sudo's OpenBSD peer.
    "stdbuf": {"-i", "-o", "-e", "--input", "--output", "--error"},
    "gstdbuf": {"-i", "-o", "-e", "--input", "--output", "--error"},
    "setsid": set(),
    "doas": {"-a", "-C", "-u"},
}
_CMD_WRAPPER_OPERANDS = {"timeout": 1, "gtimeout": 1, "lockf": 1}  # DURATION, FILE
_CMD_TRANSPARENT_WORDS = {
    "!", "{", "if", "then", "else", "elif", "do", "while", "until", "nohup", "builtin",
    "noglob", "nocorrect", "coproc",
}
_ASSIGNMENT_WORD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)


def _split_command_prefix(words: list[str | None]) -> tuple[dict[str, str], list[str | None]]:
    """Split leading assignments and wrapper words off one simple command."""
    assigns: dict[str, str] = {}
    i, n = 0, len(words)
    while i < n and words[i] is not None:
        word = words[i]
        match = _ASSIGNMENT_WORD_RE.match(word)
        if match:
            assigns[match.group(1)] = match.group(2)
            i += 1
        elif word in _CMD_TRANSPARENT_WORDS or (word.startswith("/") and word.endswith("/nohup")):
            i += 1
        elif word == "time":
            i += 2 if i + 1 < n and words[i + 1] == "-p" else 1
        elif word == "command" or (word.startswith("/") and word.endswith("/command")):
            i += 1
            while i < n and words[i] == "-p":
                i += 1
            if i < n and words[i] in ("-v", "-V"):
                return assigns, []
        elif word.rsplit("/", 1)[-1] in _CMD_WRAPPER_VALUE_OPTS:  # `/usr/bin/nice` too
            wrapper = word.rsplit("/", 1)[-1]
            value_opts = _CMD_WRAPPER_VALUE_OPTS[wrapper]
            i += 1
            while i < n and words[i] is not None and words[i].startswith("-") and words[i] != "-":
                i += 2 if words[i] in value_opts else 1
            i += _CMD_WRAPPER_OPERANDS.get(wrapper, 0)
        else:
            break
    return assigns, list(words[i:])


def _simple_commands(command: str) -> list[tuple[str, dict[str, str], list[str | None]]]:
    """Split a command line into ``(kind, assignments, argv)`` for semantic gates.

    ``kind`` is ``"cmd"``, or ``"push"``/``"pop"`` at a ``(``/``)`` boundary so a
    caller tracking ``cd`` can undo a subshell's. ``argv`` starts at the program
    word (assignments, reserved words and time/command/exec/env/nohup/timeout/sudo
    wrappers skipped); an empty ``argv`` with assignments is a plain assignment.
    Words are shell-unquoted; one the unquoter cannot classify is ``None``.

    Built on ``_iter_shell_syntax``, so heredoc bodies, comments and quoted text
    never become command words. Raises ``ValueError`` on unbalanced input; callers
    fail open.
    """
    out: list[tuple[str, dict[str, str], list[str | None]]] = []
    words: list[str | None] = []
    for kind, raw, _start, _end in _iter_shell_syntax(command):
        if kind == "word":
            words.append(_shlex_unquote_word(raw))
            continue
        if kind not in ("separator", "structure"):
            continue  # redirection operators and their targets are not argv
        if words:
            out.append(("cmd", *_split_command_prefix(words)))
            words = []
        if kind == "structure":
            out.append(("push" if raw == "(" else "pop", {}, []))
    if words:
        out.append(("cmd", *_split_command_prefix(words)))
    return out


# --- git-history-guard (BLOCKER, no if) — imports sidecar ----------------------
# A history rewrite in a checkout shared with a live peer can un-commit or republish
# the peer's commit (arc-agi 2026-07-16: `git reset --soft HEAD~1` after a peer had
# committed), `--amend` commits the whole shared index (arc-agi 2026-07-10), and
# `reset --hard` discards the peer's uncommitted work. Rule, verbs, identity and
# incidents: pretool_git_history_guard.py (the sidecar holds the git semantics and the
# Gov-ID). The cheap substring check keeps non-matching calls free.
_GIT_HISTORY_HINTS = ("reset", "rebase", "--am")


def gate_git_history_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        ti = data.get("tool_input") or {}
        cmd = ti.get("command", "") or ""
        if "git" not in cmd or not any(hint in cmd for hint in _GIT_HISTORY_HINTS):
            return GateResult(0, "", "")
        commands = _simple_commands(cmd)
        mod = _load_module(HOOKS_DIR / "pretool_git_history_guard.py", "pretool_git_history_guard")
        base = ti.get("workdir") or ti.get("cwd") or data.get("cwd") or os.getcwd()
        my_ids = mod.session_ids(data, os.environ)
        for op in mod.find_ops(commands, base, os.environ):
            decision = mod.check(op, my_ids, os.environ)
            if decision is None:
                continue
            _log_trigger("git-history-guard", decision.action, decision.detail, cmd)
            if decision.action == "block":
                return GateResult(2, decision.message, "")
        return GateResult(0, "", "")
    except Exception:
        return GateResult(0, "", "")


# --- rg-replace-flag-guard (ADVISORY, no if) ------------------------------------
# `rg -rn` reads as "recursive, line numbers", but rg is recursive by default and `-r`
# is `--replace`: the rest of the cluster becomes the replacement, so every match
# prints as `n`. agentlogs, 30 days to 2026-09-23: 88 glued `-r<letters>` calls
# (`-rn` 74, `-rln` 13, `-ril` 1; steward proposal 2026-06-21). Value-taking flags
# (rg 15.2 --help) skip their value, so `rg -e -rn` and `rg -g -rn` stay silent.
_RG_VALUE_SHORT = set("ABCEMTdefgjmrt")
_RG_VALUE_LONG = {
    "--after-context", "--before-context", "--color", "--colors", "--context",
    "--context-separator", "--dfa-size-limit", "--encoding", "--engine",
    "--field-context-separator", "--field-match-separator", "--file", "--generate", "--glob",
    "--hostname-bin", "--hyperlink-format", "--iglob", "--ignore-file", "--max-columns",
    "--max-count", "--max-depth", "--max-filesize", "--path-separator", "--pre", "--pre-glob",
    "--regex-size-limit", "--regexp", "--replace", "--sort", "--sortr", "--threads", "--type",
    "--type-add", "--type-clear", "--type-not",
}
_RG_GLUED_REPLACE_RE = re.compile(r"^-r[A-Za-z]+$")


def _rg_glued_replace(argv: list[str | None]) -> str | None:
    """The first `-r<letters>` cluster in one rg argv, skipping option values."""
    i = 1
    while i < len(argv):
        word = argv[i]
        i += 1
        if word is None or not word.startswith("-") or word == "-":
            continue
        if word == "--":
            return None
        if word.startswith("--"):
            i += 1 if word in _RG_VALUE_LONG else 0
            continue
        if _RG_GLUED_REPLACE_RE.match(word):
            return word
        for pos, letter in enumerate(word[1:]):
            if letter in _RG_VALUE_SHORT:
                i += 1 if pos == len(word) - 2 else 0
                break
    return None


def gate_rg_replace_flag_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        if "rg" not in cmd or "-r" not in cmd:
            return GateResult(0, "", "")
        for kind, _assigns, argv in _simple_commands(cmd):
            if kind != "cmd" or not argv or argv[0] is None or argv[0].rsplit("/", 1)[-1] != "rg":
                continue
            cluster = _rg_glued_replace(argv)
            if cluster is None:
                continue
            _log_trigger("rg-replace-flag-guard", "warn", cluster, cmd)
            msg = (
                f"rg is recursive by default; `-r` is `--replace` — `{cluster}` rewrites every "
                f"match to `{cluster[2:]}`. Drop the `r`."
            )
            return GateResult(0, "", json.dumps({"additionalContext": msg}))
        return GateResult(0, "", "")
    except Exception:
        return GateResult(0, "", "")


# --- zsh-modifier-guard (WARNER, 2026-10-27) --------------------------------
# The Bash tool runs $SHELL, zsh here, where an unbraced `$var:<letter>` is a
# history modifier, inside double quotes and unquoted heredoc bodies too:
# `git show $rev:tests/x.py` reads `:t` (tail), `"$T:scripts/x.py"` reads `:s`
# and `"$img:latest"` lowercases. A tree comparison printed wrong offender
# counts for three revisions (genomics 2026-10-27); same trap 2026-09-30.
# Single-quoted, $'…', escaped and commented text and quoted-delimiter heredoc
# bodies are literal, so they are blanked before the match. `:p` stays literal
# in parameter expansion, so it is not listed.

_ZSH_MODIFIER_RE = re.compile(r"(?<!\$)\$([A-Za-z_][A-Za-z0-9_]*|[0-9])(:[aAcehlPqQrstux&g])")
_HEREDOC_WORD_END = " \t\n;|&<>()"


def _zsh_expanding_text(command: str) -> str:
    """The command with zsh-literal text blanked; offsets are preserved."""
    out = list(command)
    n = len(command)

    def blank(start: int, end: int) -> None:
        for k in range(start, min(end, n)):
            if out[k] != "\n":
                out[k] = " "

    pending: list[tuple[str, bool, bool]] = []  # (delimiter, strip_tabs, literal body)
    in_double = False
    i = 0
    while i < n:
        ch = command[i]
        if in_double:
            if ch == "\\":
                blank(i, i + 2)
                i += 2
                continue
            in_double = ch != '"'
            i += 1
            continue
        if ch == "\\":
            blank(i, i + 2)
            i += 2
        elif ch == "'":
            end = command.find("'", i + 1)
            end = n if end < 0 else end
            blank(i, end + 1)
            i = end + 1
        elif ch == "$" and command.startswith("'", i + 1):
            j = i + 2
            while j < n and command[j] != "'":
                j += 2 if command[j] == "\\" else 1
            blank(i, j + 1)
            i = j + 1
        elif ch == '"':
            in_double = True
            i += 1
        elif ch == "#" and (i == 0 or command[i - 1] in " \t\n;|&("):
            end = command.find("\n", i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
        elif command.startswith("<<", i) and not command.startswith("<<<", i):
            j = i + 2
            strip_tabs = command.startswith("-", j)
            j += 1 if strip_tabs else 0
            while j < n and command[j] in " \t":
                j += 1
            k = j
            while k < n and command[k] not in _HEREDOC_WORD_END:
                k += 1
            raw = command[j:k]
            delimiter = raw.replace("'", "").replace('"', "").replace("\\", "")
            if delimiter:
                pending.append((delimiter, strip_tabs, raw != delimiter))
            blank(j, k)
            i = k
        elif ch == "\n" and pending:
            i += 1
            for delimiter, strip_tabs, literal in pending:
                start = body_end = i
                while i < n:
                    line_end = command.find("\n", i)
                    line_end = n if line_end < 0 else line_end
                    line = command[i:line_end]
                    if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                        body_end = i
                        i = min(line_end + 1, n)
                        break
                    i = body_end = min(line_end + 1, n)
                if literal:
                    blank(start, body_end)
                else:
                    k = start
                    while k < body_end:
                        if command[k] == "\\":
                            blank(k, k + 2)
                            k += 2
                        else:
                            k += 1
            pending = []
        else:
            i += 1
    return "".join(out)


def gate_zsh_modifier_guard(raw_payload: str) -> GateResult:
    try:
        if os.path.basename(os.environ.get("SHELL", "")) != "zsh":
            return GateResult(0, "", "")
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        if "$" not in cmd or ":" not in cmd:
            return GateResult(0, "", "")
        hits = [m.group(0) for m in _ZSH_MODIFIER_RE.finditer(_zsh_expanding_text(cmd))]
        if not hits:
            return GateResult(0, "", "")
        shown = ", ".join(f"`{hit}`" for hit in dict.fromkeys(hits))
        _log_trigger("zsh-modifier-guard", "warn", hits[0], cmd)
        msg = (
            f"zsh reads {shown} as a history modifier (`:t` tail, `:h` head, `:r` root, `:e` "
            "extension, `:s` substitute, `:a` absolute, `:l`/`:u` case), inside double quotes "
            "and unquoted heredocs too. Write `${name}:…`, or run the loop under `bash -c '…'`."
        )
        return GateResult(0, "", json.dumps({"additionalContext": msg}))
    except Exception:
        return GateResult(0, "", "")


MANIFEST: list[dict] = [
    {
        "name": "secret-output-guard",
        "if": None,
        "run": make_native_gate("pretool-secret-output-guard.py", "pretool_secret_output_guard"),
    },
    # 2026-09-24: side-effect-only stale-lock cleanup, early so later gates and the
    # command itself find the lock gone. Trigger lives in the gate (`\bgit\b`).
    {"name": "git-stale-lock", "if": None, "run": gate_git_stale_lock},
    {"name": "secret-path-guard", "if": None, "run": gate_secret_path_guard},
    {"name": "git-noext-inject", "if": None, "run": gate_git_noext_inject},
    {"name": "pyunbuffered-inject", "if": None, "run": gate_pyunbuffered_inject},
    {"name": "bg-buffering-pipe", "if": None, "run": gate_bg_buffering_pipe},
    {"name": "git-add-all-guard", "if": "Bash(git*)", "run": gate_git_add_all_guard},
    {"name": "bash-loop-guard", "if": None, "run": gate_bash_loop_guard},
    {"name": "bash-cat-guard", "if": None, "run": gate_bash_cat_guard},
    {"name": "bash-backtick-guard", "if": None, "run": gate_bash_backtick_guard},
    {"name": "approval-held-guard", "if": None, "run": gate_approval_held_guard},
    {"name": "noext-nongit-guard", "if": None, "run": gate_noext_nongit_guard},
    {
        "name": "bash-background-ampersand",
        "if": None,
        "run": make_native_gate(
            "pretool-bash-background-ampersand.py", "pretool_bash_background_ampersand"
        ),
    },
    {
        "name": "bg-dispatch-footgun",
        "if": None,
        "run": make_native_gate("pretool-bg-dispatch-footgun.py", "pretool_bg_dispatch_footgun"),
    },
    {"name": "heavy-load-guard", "if": None, "run": gate_heavy_load_guard},
    {"name": "no-background-commit", "if": "Bash(git*)", "run": gate_no_background_commit},
    # `if: None` on purpose — a compound command (`cd x && git worktree add /tmp/y`)
    # does not match Bash(git*), and that is exactly the shape that leaked.
    {
        "name": "worktree-location-guard",
        "if": None,
        "run": make_native_gate(
            "pretool-worktree-location-guard.py", "pretool_worktree_location_guard"
        ),
    },
    {
        "name": "uv-python-guard",
        "if": None,
        "run": make_native_gate("pretool-uv-python-guard.py", "pretool_uv_python_guard"),
    },
    # After uv-python-guard: its bare-python rewrite produces a `uv run` this gate must see.
    {
        "name": "uv-worktree-venv-guard",
        "if": None,
        "run": make_native_gate(
            "pretool-uv-worktree-venv-guard.py", "pretool_uv_worktree_venv_guard"
        ),
    },
    {
        "name": "genomics-pythonpath-guard",
        "if": None,
        "run": make_native_gate(
            "pretool-genomics-pythonpath-guard.py", "pretool_genomics_pythonpath_guard"
        ),
    },
    {
        "name": "arc-agi-agent-cwd-guard",
        "if": None,
        "run": make_native_gate(
            "pretool-arc-agi-agent-cwd-guard.py", "pretool_arc_agi_agent_cwd_guard"
        ),
    },
    {
        "name": "emb-project-guard",
        "if": None,
        "run": make_native_gate("pretool-emb-project-guard.py", "pretool_emb_project_guard"),
    },
    {
        "name": "bare-modal-guard",
        "if": None,
        "run": make_native_gate("pretool-bare-modal-guard.py", "pretool_bare_modal_guard"),
    },
    {"name": "duckdb-quote-guard", "if": None, "run": gate_duckdb_quote_guard},
    {"name": "modal-cost-guard", "if": None, "run": gate_modal_cost_guard},
    {"name": "modal-script-audit", "if": None, "run": gate_modal_script_audit},
    {"name": "cost-guard", "if": None, "run": gate_cost_guard},
    {"name": "cost-awareness", "if": None, "run": gate_cost_awareness},
    {"name": "ast-precommit", "if": "Bash(git commit*)", "run": gate_ast_precommit},
    {"name": "commit-check", "if": "Bash(git commit*)", "run": gate_commit_check},
    {
        "name": "multiagent-commit-guard",
        "if": "Bash(git*)",
        "run": make_subprocess_gate(str(HOOKS_DIR / "pretool-multiagent-commit-guard.sh")),
    },
    # 2026-09-23 addition, placed before destructive-git-ref so that gate's backup-ref
    # snapshot is not taken for a reset this guard is about to refuse.
    {"name": "git-history-guard", "if": None, "run": gate_git_history_guard},
    {"name": "modal-run-guard", "if": None, "run": gate_modal_run_guard},
    {"name": "timeout-modal-guard", "if": None, "run": gate_timeout_modal_guard},
    {
        "name": "destructive-git-ref",
        "if": "Bash(git*)",
        "run": make_subprocess_gate(str(HOOKS_DIR / "pretool-destructive-git-ref.sh")),
    },
    {
        "name": "plan-completion-guard",
        "if": "Bash(git commit*)",
        "run": make_subprocess_gate(str(HOOKS_DIR / "precommit-plan-completion-guard.sh")),
    },
    {"name": "plan-protect", "if": None, "run": gate_plan_protect},
    {
        "name": "cursor-model-guard",
        "if": None,
        "run": make_native_gate("pretool-cursor-model-guard.py", "pretool_cursor_model_guard"),
    },
    # --- post-consolidation additions (2026-07-18), see section above ------
    {"name": "git-stash-guard", "if": None, "run": gate_git_stash_guard},
    {"name": "pkill-guard", "if": None, "run": gate_pkill_guard},
    {"name": "opus-concurrency-advisory", "if": None, "run": gate_opus_concurrency_advisory},
    # --- 2026-09-02: persistent cd into a lane worktree (genomics M122 recurrence) ---
    {"name": "worktree-cd-guard", "if": None, "run": gate_worktree_cd_guard},
    {"name": "remote-delete-guard", "if": None, "run": gate_remote_delete_guard},
    # --- 2026-09-23: glued `rg -rn` silently rewrites matches (advisory) ---
    {"name": "rg-replace-flag-guard", "if": None, "run": gate_rg_replace_flag_guard},
    # --- 2026-10-27: unbraced `$var:<letter>` is a zsh history modifier (advisory) ---
    {"name": "zsh-modifier-guard", "if": None, "run": gate_zsh_modifier_guard},
]


# ─────────────────────────────────────────────────────────────────────────
# Uniform result classifier — interprets ANY gate's (code, stderr, stdout)
# into one of: block / mutate / advise / pass. Handles every contract shape
# observed across the 28 originals: exit2+stderr text, exit2+stdout JSON
# {"decision":"block",...}, exit0+stdout JSON {"decision":"block",...}
# (modal-run-guard's always-exit-0 shape), hookSpecificOutput.updatedInput,
# top-level/hookSpecificOutput additionalContext, and bare advisory text.
# ─────────────────────────────────────────────────────────────────────────


def _mutate_note(result: GateResult) -> str:
    """additionalContext a rewriting gate attached to its updatedInput, or ''."""
    try:
        hso = json.loads(result.stdout).get("hookSpecificOutput") or {}
    except Exception:
        return ""
    return hso.get("additionalContext") or "" if isinstance(hso, dict) else ""


def _classify(result: GateResult) -> tuple[str, str | dict]:
    stdout, stderr = result.stdout.strip(), result.stderr.strip()
    if result.code == 2:
        if stdout:
            try:
                obj = json.loads(stdout)
                if isinstance(obj, dict) and obj.get("decision") == "block":
                    return "block", obj.get("reason", stdout)
            except Exception:
                pass
        return "block", stderr or stdout or "BLOCKED (no message)"
    if stdout:
        try:
            obj = json.loads(stdout)
        except Exception:
            obj = None
        if isinstance(obj, dict):
            if obj.get("decision") == "block":
                return "block", obj.get("reason", stdout)
            hso = obj.get("hookSpecificOutput") or {}
            if isinstance(hso, dict) and "updatedInput" in hso:
                return "mutate", hso["updatedInput"]
            ctx = (hso.get("additionalContext") if isinstance(hso, dict) else None) or obj.get(
                "additionalContext"
            )
            if ctx:
                return "advise", ctx
            return "pass", ""
        return "advise", stdout
    if stderr:
        return "advise", stderr
    return "pass", ""


def _log_gate(name: str, kind: str, noted: bool = False) -> None:
    """ONE instrumentation point for all 35 in-process gates (2026-09-01 audit:
       163/207 wired hook scripts emit no event-log row, so fire counts are
       unmeasurable). Maps dispatcher verdicts onto the existing hook-trigger-log
    action vocabulary under a SEPARATE dispatch: namespace, so it can never
    double-count the 13 gates that already self-log; fail-open throughout."""
    # A silent rewrite (updatedInput only) never reaches the model, so it logs as
    # "rewrite", which hook-roi keeps out of nag volume; a rewrite with a note is a warn.
    action = {"block": "block", "mutate": "warn" if noted else "rewrite", "advise": "warn"}.get(kind)
    if action is None:
        return
    try:
        subprocess.run(
            [str(HOOKS_DIR / "hook-trigger-log.sh"), f"dispatch:{name}", action, "in-process gate"],
            capture_output=True,
            timeout=3,
            check=False,
        )
    except Exception:
        pass


def main() -> None:
    raw_payload = sys.stdin.read()
    try:
        envelope = json.loads(raw_payload) if raw_payload.strip() else {}
    except Exception:
        sys.exit(0)
    if not isinstance(envelope, dict) or envelope.get("tool_name") != "Bash":
        sys.exit(0)

    current_ti = dict(envelope.get("tool_input") or {})
    original_ti = dict(current_ti)
    advisories: list[str] = []

    for gate in MANIFEST:
        cmd_for_if = current_ti.get("command", "") or ""
        if not _if_matches(gate["if"], cmd_for_if):
            continue
        payload = dict(envelope)
        payload["tool_input"] = current_ti
        raw = json.dumps(payload)
        try:
            result = gate["run"](raw)
        except Exception:
            continue  # fail-open: a dispatcher-level bug in one gate never blocks
        kind, val = _classify(result)
        _log_gate(gate["name"], kind, kind == "mutate" and bool(_mutate_note(result)))
        if kind == "block":
            msg = val if isinstance(val, str) else json.dumps(val)
            sys.stderr.write(msg + ("\n" if not msg.endswith("\n") else ""))
            sys.exit(2)
        if kind == "mutate" and isinstance(val, dict):
            current_ti = val
            note = _mutate_note(result)
            if note:
                advisories.append(note)
        elif kind == "advise" and val:
            advisories.append(val if isinstance(val, str) else json.dumps(val))

    out: dict = {}
    if current_ti != original_ti:
        out["hookSpecificOutput"] = {"hookEventName": "PreToolUse", "updatedInput": current_ti}
    if advisories:
        out["additionalContext"] = "\n\n".join(advisories)
    if out:
        sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
