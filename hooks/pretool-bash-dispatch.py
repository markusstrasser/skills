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


# --- 5. pretool-bash-cat-guard.sh (BLOCKER, no if) — imports sidecar -------


def gate_bash_cat_guard(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(HOOKS_DIR / "pretool_bash_cat_guard.py", "pretool_bash_cat_guard")
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd or "$(cat " not in cmd:
            return GateResult(0, "", "")
        cwd = data.get("cwd") or os.getcwd()
        redirected = {t.rstrip(";&|").strip("\"'") for t in re.findall(r">>?\s*(\S+)", cmd)}
        missing = []
        for span in mod.find_cat_spans(cmd):
            for tok in span.split():
                if tok.startswith("-") or tok in ("<<", "<<<"):
                    continue
                if ">" in tok or "<" in tok:
                    continue
                if any(c in tok for c in "$`*?[]{}~"):
                    continue
                tok = tok.strip("\"'")
                if not tok or tok in redirected:
                    continue
                path = tok if os.path.isabs(tok) else os.path.join(cwd, tok)
                if not os.path.exists(path):
                    missing.append(tok)
        missing = list(dict.fromkeys(missing))
        if not missing:
            return GateResult(0, "", "")
        lines = [
            "BLOCKED: $(cat ...) references file(s) that do not exist — the command would silently run with a truncated/empty substitution:"
        ]
        lines += [f"  missing: {m}" for m in missing]
        lines.append(
            "Create the file first (verify with wc -c), or fix the path. If the file is created earlier in this same command via a redirect, this guard skips it — heredocs inside $( ) are not detected, restructure instead."
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


def _noext_nongit_hit(cmd: str) -> str | None:
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return None
    expect_cmd = True
    seg_nongit = False
    cur = None
    for t in toks:
        if t in _SHELL_RESET:
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
_TIMEOUT_WRAP_RE = re.compile(
    r"(?:^|[;&|(]\s*|\$\(\s*|`\s*)"
    r"(?:nohup\s+|sudo\s+|[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
    r"timeout\s+(?:-[ksv]\S*\s+)*\d+(?:\.\d+)?[smhd]?\s",
    re.M,
)
_TIMEOUT_CRAWL_RE = re.compile(
    r"\bmodal\s+(?:volume|run|app|container)\b"
    r"|\bjust\s+(?:dispatch|sample-remediation|sample-state|sample-readiness"
    r"|complete-sample|pipeline-run|pipeline-rerun|pipeline-rerun-vcf|census"
    r"|volume-status|stage-status|probe|download-results)\b"
    r"|pipeline_orchestrator\.py\s+(?:dispatch|rerun|run|resume|recover|reconcile|reconcile-runs|backfill|sync-cass)\b"
    r"|complete_sample\.py"
    r"|\bmodal_sync_results\.py\b",
)


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
    if not _TIMEOUT_WRAP_RE.search(scan):
        return GateResult(0, "", "")
    cmd2 = scan
    # `app logs`, `container logs` and `container exec` are bounded streams, not crawls:
    # the streaming guard REQUIRES a timeout on them, so blocking it here made the two
    # gates unsatisfiable together (genomics 2026-09-02, a read-only `container exec`
    # to inspect a silent materializer was refused both ways).
    if re.search(r"\bmodal\s+(?:app|container)\s+(?:logs|exec)\b", cmd2):
        return GateResult(0, "", "")
    if not _TIMEOUT_CRAWL_RE.search(cmd2):
        return GateResult(0, "", "")
    msg = (
        "BLOCKED: `timeout N` wraps a Modal/volume-crawl command. At the deadline it\n"
        "sends SIGTERM (exit 143) and kills the crawl MID-RUN — wasting the dispatch/\n"
        "remediation/volume-ls and any partial state. (genomics 2026-06-24: this footgun\n"
        "fired 4x in one session.)\n"
        "Fix: DROP `timeout N` and either\n"
        "  - run_in_background=true  (tracked; you get a completion notification), or\n"
        "  - use the commands OWN bound (`just dispatch ... --detach`, llmx `--timeout`),\n"
        "    or `modal volume ls` (already fast) without the wrapper.\n"
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


def make_subprocess_gate(path: str):
    def run(raw_payload: str) -> GateResult:
        try:
            proc = subprocess.run(
                [path], input=raw_payload, capture_output=True, text=True, timeout=30
            )
        except Exception:
            return GateResult(0, "", "")
        return GateResult(proc.returncode, proc.stderr or "", proc.stdout or "")

    return run


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


# --- 30. pretool-pkill-anchor-guard.sh (ADVISORY, no if) --------------------


def _pkill_f_patterns(seg: str):
    """Mirrors pretool-pkill-anchor-guard.sh's find_pkill_f_patterns():
    yields (pattern, has_dash_x) for a `pkill ... -f <pattern>` call."""
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        return
    i = 0
    while i < len(parts):
        tok = parts[i].rsplit("/", 1)[-1]
        if tok != "pkill":
            i += 1
            continue
        args = parts[i + 1 :]
        has_dash_x = "-x" in args
        pattern = None
        j = 0
        while j < len(args):
            a = args[j]
            if a == "-f":
                if j + 1 < len(args) and not args[j + 1].startswith("-"):
                    pattern = args[j + 1]
                j += 2
                continue
            if a.startswith("-f") and len(a) > 2 and not a.startswith("--"):
                pattern = a[2:]
                j += 1
                continue
            if a == "--full":
                if j + 1 < len(args) and not args[j + 1].startswith("-"):
                    pattern = args[j + 1]
                j += 2
                continue
            j += 1
        if pattern is not None:
            yield pattern, has_dash_x
        break


def _pkill_is_anchored(pattern: str, has_dash_x: bool) -> bool:
    if has_dash_x:
        return True
    if pattern.startswith("^"):
        return True
    if "/" in pattern:
        return True
    return False


def gate_pkill_anchor_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd or "pkill" not in cmd:
        return GateResult(0, "", "")
    segments = re.split(r"&&|\|\||;|\||\n", cmd)
    hits: list[str] = []
    for seg in segments:
        for pattern, has_dash_x in _pkill_f_patterns(seg):
            if not _pkill_is_anchored(pattern, has_dash_x):
                hits.append(pattern)
    if not hits:
        return GateResult(0, "", "")
    pat_list = ", ".join(f"'{p}'" for p in hits)
    msg = (
        f"ADVISORY: pkill -f pattern(s) [{pat_list}] look unanchored (no `/` path segment, "
        "no leading `^`, no paired `-x`) — `-f` matches by SUBSTRING against the full command "
        "line. Run `pgrep -fl '<pattern>'` FIRST and read every match before killing anything; "
        "anchor to a unique token (full path, `^`, or `-x`) once you've confirmed the match set. "
        "(wakeup-cadence.md pkill discipline — 2 same-day incidents 2026-07-12, one killed a "
        "healthy training client via `*forkDC*` matching the unrelated `forkDCH`.)"
    )
    out = json.dumps({"additionalContext": msg})
    return GateResult(0, "", out)


# --- 31. opus-concurrency-advisory (ADVISORY, no if) -------------------------
# Reuses arc-agi's `just opus-load` recipe's EXACT pgrep pattern and threshold
# verbatim (arc-agi justfile:823 `opus-load`) rather than reinventing a count —
# see that recipe's own comment for the measured basis (6+ concurrent streams
# -> 72% dead rounds, arc-agi 2026-07-18 Stage-0 burn) and its stated throttle
# ("keep <=2-3; stagger launches above that"). Cited, not duplicated logic:
# the pattern string below IS the recipe's pattern string, kept identical on
# purpose so the two never silently drift apart.
_OPUS_LOAD_PGREP_PATTERN = "claude-opus-4-8|claude-fable-5|claude -p"
_OPUS_TRIGGER_LLMX_RE = re.compile(r"\bllmx\b", re.I)
_OPUS_TRIGGER_MODEL_RE = re.compile(r"claude-opus-4-8|claude-fable-5", re.I)
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
        f"'{_OPUS_LOAD_PGREP_PATTERN}', same pattern as `just opus-load` in arc-agi) — "
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

_WORKTREE_CD_RE = re.compile(
    r"(?:^|[\s;&|])cd\s+[\"']?([^\s\"';&|()]*\.claude/worktrees/[^\s\"';&|()]*)"
)


def gate_worktree_cd_guard(raw_payload: str) -> GateResult:
    """Block a persistent ``cd`` into a lane worktree (``.claude/worktrees/...``).

    The Bash tool's cwd persists across calls, so ``cd <worktree> && ...`` leaves
    every later command — ``git log`` ranges, ``uv run``, file swaps — running
    against the worktree instead of main. Genomics catalog M122; recurred
    2026-09-02 in one hour: a false-empty ``git log`` bisect, a 373 MB venv built
    inside the worktree, and an edit that landed in the wrong tree. A subshell
    ``(cd <wt> && ...)`` cannot persist and passes; ``git -C <wt>`` and absolute
    paths are the intended spellings.
    """
    try:
        data = json.loads(raw_payload)
    except Exception:
        return GateResult(0, "", "")
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if "worktrees" not in cmd or "cd" not in cmd:
        return GateResult(0, "", "")
    # A cd inside ( ... ) or $( ... ) cannot change the persistent cwd: strip
    # parenthesised groups innermost-first before matching.
    stripped = cmd
    for _ in range(8):
        reduced = re.sub(r"\([^()]*\)", "", stripped)
        if reduced == stripped:
            break
        stripped = reduced
    match = _WORKTREE_CD_RE.search(stripped)
    if match is None:
        return GateResult(0, "", "")
    target = match.group(1)
    msg = (
        f"BLOCK: `cd {target}` would leave this session's persistent cwd inside a lane "
        "worktree; every later Bash call (git log ranges, uv run, edits) would then run "
        "against the worktree, not main (genomics catalog M122, recurred 2026-09-02).\n"
        f"Use `git -C {target} ...`, absolute `{target}/...` paths, or a subshell "
        f"`(cd {target} && ...)`, which cannot persist.\n"
    )
    _log_trigger("worktree-cd-guard", "block", cmd[:80], cmd)
    return GateResult(2, msg, "")


MANIFEST: list[dict] = [
    {
        "name": "secret-output-guard",
        "if": None,
        "run": make_native_gate("pretool-secret-output-guard.py", "pretool_secret_output_guard"),
    },
    {"name": "git-noext-inject", "if": None, "run": gate_git_noext_inject},
    {"name": "pyunbuffered-inject", "if": None, "run": gate_pyunbuffered_inject},
    {"name": "bg-buffering-pipe", "if": None, "run": gate_bg_buffering_pipe},
    {"name": "git-add-all-guard", "if": "Bash(git*)", "run": gate_git_add_all_guard},
    {"name": "bash-loop-guard", "if": None, "run": gate_bash_loop_guard},
    {"name": "bash-cat-guard", "if": None, "run": gate_bash_cat_guard},
    {"name": "bash-backtick-guard", "if": None, "run": gate_bash_backtick_guard},
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
    {"name": "pkill-anchor-guard", "if": None, "run": gate_pkill_anchor_guard},
    {"name": "opus-concurrency-advisory", "if": None, "run": gate_opus_concurrency_advisory},
    # --- 2026-09-02: persistent cd into a lane worktree (genomics M122 recurrence) ---
    {"name": "worktree-cd-guard", "if": None, "run": gate_worktree_cd_guard},
]


# ─────────────────────────────────────────────────────────────────────────
# Uniform result classifier — interprets ANY gate's (code, stderr, stdout)
# into one of: block / mutate / advise / pass. Handles every contract shape
# observed across the 28 originals: exit2+stderr text, exit2+stdout JSON
# {"decision":"block",...}, exit0+stdout JSON {"decision":"block",...}
# (modal-run-guard's always-exit-0 shape), hookSpecificOutput.updatedInput,
# top-level/hookSpecificOutput additionalContext, and bare advisory text.
# ─────────────────────────────────────────────────────────────────────────


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


def _log_gate(name: str, kind: str) -> None:
    """ONE instrumentation point for all 35 in-process gates (2026-09-01 audit:
       163/207 wired hook scripts emit no event-log row, so fire counts are
       unmeasurable). Maps dispatcher verdicts onto the existing hook-trigger-log
    action vocabulary under a SEPARATE dispatch: namespace, so it can never
    double-count the 13 gates that already self-log; fail-open throughout."""
    action = {"block": "block", "mutate": "warn", "advise": "warn"}.get(kind)
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
        _log_gate(gate["name"], kind)
        if kind == "block":
            msg = val if isinstance(val, str) else json.dumps(val)
            sys.stderr.write(msg + ("\n" if not msg.endswith("\n") else ""))
            sys.exit(2)
        if kind == "mutate" and isinstance(val, dict):
            current_ti = val
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
