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
     the command matches a glob (git* / git commit*); 8 of 28 entries carry
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
pretool-bare-modal-guard.py. Two of these are adjacent in settings.json order
(uv-python-guard at position 11, arc-agi-agent-cwd-guard at position 13) and
arc-agi-agent-cwd-guard's OWN selftest encodes an explicit assumption that it
runs AFTER uv-python-guard's rewrite has already landed — its selftest has a
case literally commented "# bare python with import -> block (uv-guard should
rewrite first)": a bare `python3 -c "import arcengine"` (no `uv run` yet)
verdicts to BLOCK, not REWRITE, because _insert_directory() requires `uv run`
to already be present in the command to insert `--directory agent` into. For
arc-agi-agent-cwd-guard to ever reach its REWRITE branch on a bare-python
arc-agi command, it must see uv-python-guard's rewritten command, not the
original. This dispatcher therefore CHAINS mutations: each gate (native,
ported, or subprocess) is fed the CURRENT (possibly already-rewritten)
envelope, and a mutation updates that running envelope before the next gate
runs. This was not independently verified against a Claude Code release note
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
  pretool-arc-agi-agent-cwd-guard.py, pretool-bare-modal-guard.py,
  pretool-cursor-model-guard.py                                   (7 gates)

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


def _log_trigger(hook: str, action: str, detail: str) -> None:
    """Fire-and-forget telemetry — mirrors each gate's own
    `~/Projects/skills/hooks/hook-trigger-log.sh "$name" "$action" "$detail"`
    call. Never affects gate behavior."""
    try:
        subprocess.run(
            [TRIGGER_LOG, hook, action, detail],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────
# "if": "Bash(<glob>)" per-hook condition (8 of 28 entries carry this in
# settings.json). Only observed shapes are "Bash(git*)" and
# "Bash(git commit*)"; an unrecognized shape fails open to RUNNING the gate
# (skipping a safety gate is the worse failure mode).
# ─────────────────────────────────────────────────────────────────────────

_IF_RE = re.compile(r"^Bash\((.*)\)$")


def _if_matches(if_pattern: str | None, cmd: str) -> bool:
    if not if_pattern:
        return True
    m = _IF_RE.match(if_pattern)
    if not m:
        return True
    return fnmatch.fnmatchcase((cmd or "").lstrip(), m.group(1))


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

# --- 1. pretool-git-noext-inject.sh (MUTATOR, if=Bash(git*)) ---------------

def _git_noext_inject_verdict(ti: dict) -> tuple[str, str]:
    cmd = ti.get("command", "") or ""
    if not cmd:
        return "pass", ""
    if any(tok in cmd for tok in ("|", "&&", "||", ";", "$(", "`", "<", "\n")):
        return "pass", ""
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return "pass", ""
    redirect_suffix: list[str] = []
    if ">" in cmd:
        if (len(parts) >= 3 and parts[-2] in (">", ">>") and ">" not in parts[-1]
                and not any(">" in p for p in parts[:-2])):
            redirect_suffix = parts[-2:]
            parts = parts[:-2]
        else:
            return "pass", ""
    if not parts or parts[0] != "git":
        return "pass", ""
    i = 1
    while i < len(parts) and parts[i].startswith("-"):
        i += 2 if parts[i] in ("-C", "-c") else 1
    if i >= len(parts):
        return "pass", ""
    subcmd = parts[i]
    if subcmd not in ("diff", "show", "log"):
        return "pass", ""
    if "--no-ext-diff" in parts and "--no-pager" in parts:
        return "pass", ""
    new = parts[:i]
    if "--no-pager" not in new:
        new = new + ["--no-pager"]
    new = new + [subcmd]
    rest = parts[i + 1:]
    if "--no-ext-diff" not in rest:
        new = new + ["--no-ext-diff"]
    new = new + rest
    new_cmd = " ".join(shlex.quote(p) for p in new)
    if redirect_suffix:
        new_cmd += " " + redirect_suffix[0] + " " + shlex.quote(redirect_suffix[1])
    if new_cmd == cmd:
        return "pass", ""
    return "mutate", new_cmd


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
    _log_trigger("git-noext-inject", "rewrite", "git diff/show/log")
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}})
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
    _log_trigger("pyunbuffered-inject", "rewrite", "bg python")
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}})
    return GateResult(0, "", out)


# --- 3. pretool-git-add-all-guard.sh (BLOCKER, if=Bash(git*)) -------------

def _git_add_all_offends(seg: str) -> bool:
    seg = seg.strip()
    try:
        parts = shlex.split(seg)
    except ValueError:
        return bool(re.match(r"(?:[A-Za-z_]\w*=\S+\s+)*git\s+add\b.*(\s-A\b|\s--all\b|\s\.(\s|$))", seg))
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
    for a in parts[j + 1:]:
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
    _log_trigger("git-add-all-guard", "block", cmd[:80])
    return GateResult(2, msg, "")


# --- 4. pretool-bash-loop-guard.sh (BLOCKER, no if) — imports sidecar ------

def gate_bash_loop_guard(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(HOOKS_DIR / "pretool_bash_loop_guard.py", "pretool_bash_loop_guard")
        data = json.loads(raw_payload)
        cmd = _jqlike_cmd(data)
        if not cmd:
            return GateResult(0, "", "")
        if mod.has_multiline_block(cmd):
            msg = (
                "BLOCKED: Multiline for/while/if blocks cause zsh parse errors. Use single-line syntax:\n"
                "  for x in *.txt; do echo \"$x\"; done\n"
                "  while read line; do echo \"$line\"; done\n"
                "  if [ -f x ]; then echo yes; else echo no; fi\n"
                "Or write a script file and run it.\n"
            )
            return GateResult(2, msg, "")
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
        lines = ["BLOCKED: $(cat ...) references file(s) that do not exist — the command would silently run with a truncated/empty substitution:"]
        lines += [f"  missing: {m}" for m in missing]
        lines.append("Create the file first (verify with wc -c), or fix the path. If the file is created earlier in this same command via a redirect, this guard skips it — heredocs inside $( ) are not detected, restructure instead.")
        return GateResult(2, "\n".join(lines) + "\n", "")
    except Exception:
        return GateResult(0, "", "")


# --- 6. pretool-noext-nongit-guard.sh (BLOCKER, no if) ---------------------

_NONGIT_TOOLS = {'rg', 'grep', 'egrep', 'fgrep', 'ag', 'ack', 'fd', 'find', 'sed', 'awk', 'zoekt',
                 'cat', 'head', 'tail', 'wc', 'cut', 'tr', 'sort', 'uniq', 'ast-grep', 'sg'}
_SHELL_RESET = {'|', '||', '&&', ';', '&', '|&', '(', ')', '{', '}'}


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
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
                continue
            cur = t.rsplit('/', 1)[-1]
            seg_nongit = cur in _NONGIT_TOOLS
            expect_cmd = False
            continue
        if t == '--no-ext-diff' and seg_nongit:
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
    _log_trigger("noext-nongit-guard", "block", hit)
    return GateResult(2, msg, "")


# --- 7/8. pretool-bash-background-ampersand.py, pretool-bg-dispatch-footgun.py: NATIVE (below in MANIFEST) ---

# --- 9. pretool-heavy-load-guard.sh (ADVISORY+BLOCKER, no if) --------------

_HEAVY_RE = re.compile(
    r'generate_unified_embeddings|generate_gemini_embeddings|extract_media|extract_media_phenotype|'
    r'rebuild_identity|identity[._]rebuild|20260610j|p4_identity|marker_single|local.*marker|ffmpeg|'
    r'transcribe|voxtral|whisper|late_chunking|build_certs|rebuild_image_embeddings|sentence-transformers|'
    r'\.embed\b|embed\.py|rerank=True|CrossEncoder|reranker|SearchEngine|fs_recall|fs_hard|emb_rerank|'
    r'recall_eval|recall_bakeoff|fs_ab', re.I,
)
_OFFLOAD_RE = re.compile(r'modal (run|deploy)|--remote', re.I)


def gate_heavy_load_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or {}).get("command", "") or ""
        if not cmd or not _HEAVY_RE.search(cmd):
            return GateResult(0, "", "")
        if _OFFLOAD_RE.search(cmd):
            return GateResult(0, "", "")

        try:
            ps_out = subprocess.run(["ps", "-axo", "rss=,pid=,comm="], capture_output=True, text=True, timeout=5).stdout
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
            mps_note = ("PYTORCH_ENABLE_MPS_FALLBACK=1 silently spills oversized tensors into CPU RAM "
                         "(14GB/proc, 2026-06-10) — drop it so they error cleanly. ")

        try:
            cores = float(subprocess.run(["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True, timeout=3).stdout.strip() or 8)
        except Exception:
            cores = 8.0
        load1 = 0.0
        try:
            raw = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True, timeout=3).stdout
            load1 = float(raw.strip().strip("{}").split()[0])
        except Exception:
            try:
                up = subprocess.run(["uptime"], capture_output=True, text=True, timeout=3).stdout
                load1 = float(re.split(r'averages?:\s*', up)[-1].split()[0].rstrip(','))
            except Exception:
                load1 = 0.0
        try:
            claudes = int(subprocess.run(["pgrep", "-c", "-f", "claude"], capture_output=True, text=True, timeout=3).stdout.strip() or 1)
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
        _log_trigger("heavy-load-guard", "warn", f"load={load1} cores={cores} claudes={claudes}")
        out = json.dumps({"additionalContext": warn})
        return GateResult(0, "", out)
    except Exception:
        return GateResult(0, "", "")


# --- 10. pretool-no-background-commit.sh (BLOCKER, if=Bash(git*)) — imports sidecar ---

def gate_no_background_commit(raw_payload: str) -> GateResult:
    try:
        mod = _load_module(HOOKS_DIR / "pretool_no_background_commit.py", "pretool_no_background_commit")
        data = json.loads(raw_payload)
        verdict = mod.classify(data)
    except Exception:
        return GateResult(0, "", "")
    if verdict == "BG":
        return GateResult(2, "BLOCKED: git commit inside run_in_background=true — a hook-blocked commit reports success while nothing lands. Run the commit FOREGROUND (background the slow step, then commit in a separate foreground call).\n", "")
    if verdict == "PIPE":
        return GateResult(2, "BLOCKED: git commit piped into tail/head/grep/... masks git's exit code (the pipeline returns the reader's rc), so a hook-blocked commit reads rc=0 while nothing lands. Capture the exit code explicitly instead: 'git commit -F msg > /tmp/c.txt 2>&1; echo COMMIT_RC=$?; tail /tmp/c.txt' — then verify with 'git log --oneline -1'.\n", "")
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
    if not re.search(r'duckdb|\.execute\(|SELECT |INSERT |UPDATE |WHERE ', cmd, re.I):
        return GateResult(0, "", "")
    if re.search(r'= "[a-zA-Z_]+"', cmd) and not re.search(r'= "[a-zA-Z_]+"\)', cmd):
        msg = ("DuckDB gotcha: double quotes = column identifier, not string literal. Use single "
               "quotes for string values (e.g., WHERE col = 'value' not WHERE col = \"value\").")
        return GateResult(0, "", msg)
    return GateResult(0, "", "")


# --- 16. ~/.claude/hooks/pretool-modal-cost-guard.sh (BLOCKER+ADVISORY, no if) ---

def gate_modal_cost_guard(raw_payload: str) -> GateResult:
    try:
        data = json.loads(raw_payload)
        cmd = (data.get("tool_input") or data).get("command", "") or ""
    except Exception:
        return GateResult(0, "", "")
    if not re.search(r'modal run', cmd):
        return GateResult(0, "", "")
    m = re.search(r'[^ ]+\.py', cmd)
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
    if re.search(r'gpu=', src):
        if not re.search(r'timeout=', src):
            warnings.append("WARNING: GPU function has no timeout= set. Add timeout = 1.5x expected duration as cost circuit breaker.")
        else:
            tm = re.search(r'timeout=([0-9]+)', src)
            if tm and int(tm.group(1)) > 43200:
                warnings.append(f"WARNING: timeout={tm.group(1)} ({int(tm.group(1)) // 3600}h) is very high. Is this intentional?")
        if re.search(r'\.(starmap|map)\(', src):
            if 'max_containers' not in src:
                warnings.append("BLOCK: Script uses .starmap()/.map() with GPU but no max_containers set. Unbounded auto-scaling will burn money. Add max_containers= to the @app.function decorator.")
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
    if not re.search(r'modal run.*--detach|modal run.*\.py', cmd):
        return GateResult(0, "", "")
    m = re.search(r'[^ ]+\.py', cmd)
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
    if re.search(r'@app\.function|@stage', src):
        cap_count = len(re.findall(r'capture_output=True', src))
        if cap_count > 0:
            warnings.append(f"WARNING: {cap_count} subprocess call(s) use capture_output=True — output invisible in modal app logs (gotcha #16). Use stdout=subprocess.PIPE, stderr=subprocess.STDOUT instead.")
    if re.search(r'@stage', src):
        if re.search(r'for .* in .*:', src) and 'vol.commit()' not in src:
            warnings.append("WARNING: Script has loops in @stage functions but no vol.commit() — intermediate results lost on crash (gotcha #20). Add vol.commit() after each iteration.")
    if '--detach' in cmd and re.search(r'subprocess\.run\(.*timeout=', src):
        warnings.append("WARNING: subprocess.run(timeout=) in a --detach script can create orphan apps (gotcha #32). Remove subprocess timeouts for detached runs.")
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
    if not cmd or not re.search(r'llmx|modal run|curl.*api|python.*openai|python.*anthropic', cmd):
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
        _log_trigger("cost-guard", "block", f"daily_spend=${total:.2f} cmd={cmd[:80]}")
        out = json.dumps({"decision": "block", "reason": f"Daily API spend ${total:.2f} exceeds the $25 constitutional cap. Defer non-essential API calls, or set LLMX_SPEND_OVERRIDE=1 for an intended llmx job / get human approval."})
        return GateResult(2, "", out)
    if spend_int >= 10:
        _log_trigger("cost-guard", "warn", f"daily_spend=${total:.2f} cmd={cmd[:80]}")
        out = json.dumps({"decision": "allow", "additionalContext": f"Cost warning: daily spend at ${total:.2f} (warn at $10, block at $25). Consider batching or deferring."})
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
            r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
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
        advisory = (f"Cost awareness: this session (${current:.2f}) has exceeded P95 "
                    f"(${p95:.2f}) for project {project}. Project median: ${median:.2f}. "
                    "Consider whether this session should continue or checkpoint.")
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
            after_quote = line[m.end():]
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
    if not re.match(r'^\s*git\s+commit', cmd):
        return GateResult(0, "", "")
    try:
        staged_py = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "--", "*.py"],
                                    capture_output=True, text=True, timeout=10).stdout.splitlines()
        staged_sh = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "--", "*.sh"],
                                    capture_output=True, text=True, timeout=10).stdout.splitlines()
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
        mod = _load_module(HOOKS_DIR / "commit-check-parse.py", "commit_check_parse")
        result = _run_entry(mod.main, raw_payload)
    except Exception:
        return GateResult(0, "", "")
    text = (result.stdout or "").strip()
    if text in ("SKIP", "OK", ""):
        return GateResult(0, "", "")
    if text.startswith("BLOCK:"):
        msg = text[len("BLOCK:"):]
        _log_trigger("commit-check", "block", msg[:100])
        return GateResult(2, f"[commit-check]: BLOCKED: {msg}\n{msg}\n", "")
    if not text.startswith("WARN:"):
        return GateResult(0, "", "")
    warn_text = text[len("WARN:"):]
    try:
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, timeout=10).stdout.splitlines()
        staged = [f for f in staged if f]
    except Exception:
        staged = []
    concept_files = sum(1 for f in staged if re.match(r'^(research/|decisions/|docs/research/)', f))
    if concept_files > 0:
        warn_text = warn_text.replace("NOBODY", "Concept files (research/decisions) staged — body REQUIRED. Name the concept affected and what changed.")
    elif len(staged) <= 1:
        warn_text = warn_text.replace(" | NOBODY", "").replace("NOBODY | ", "").replace("NOBODY", "")
    else:
        warn_text = warn_text.replace("NOBODY", f"{len(staged)} files staged but no body — add trigger, changes, impact.")

    gov = next((f for f in staged if re.search(r'(CLAUDE\.md|MEMORY\.md|improvement-log|hooks/)', f, re.I)), None)
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
    _log_trigger("commit-check", "warn", warn_text[:100])
    out = json.dumps({"additionalContext": f"COMMIT CHECK: {warn_text}"})
    return GateResult(0, "", out)


# --- 23. pretool-modal-run-guard.sh (BLOCKER, no if) -----------------------

def _kw_value(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
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
            name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
            if name not in ("function", "cls"):
                continue
            kwargs = {kw.arg: _kw_value(kw.value) for kw in dec.keywords if kw.arg is not None}
            line = dec.lineno
            ed = kwargs.get("ephemeral_disk")
            if isinstance(ed, int) and not (524288 <= ed <= 3145728):
                findings.append(f"{os.path.basename(target)}:{line} @app.{name} has ephemeral_disk={ed} — Modal requires [524288, 3145728] MiB. Use ephemeral_disk=524288 (512 GB min).")
            np_val, gpu_val = kwargs.get("nonpreemptible"), kwargs.get("gpu")
            if np_val is True and gpu_val not in (None, False):
                findings.append(f"{os.path.basename(target)}:{line} @app.{name} has nonpreemptible=True AND gpu={gpu_val!r} — Modal does not support nonpreemptible for GPU functions. Drop one.")
    if not findings:
        return GateResult(0, "", "")
    reason = "MODAL LAUNCH BLOCKED — invalid config in target script:\n\n" + "\n".join(f"  - {f}" for f in findings) + "\n\nFix in the script, then re-run."
    out = json.dumps({"decision": "block", "reason": reason})
    return GateResult(0, "", out)  # original always exits 0; the JSON decision field carries the block


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
    if re.search(r"\bmodal\s+(?:app|container)\s+logs\b", cmd2):
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

_PLAN_DESTRUCTIVE_RE = re.compile(r'^\s*(?:sudo\s+)?(?:rm|mv|trash)(?:\s|$)')
_PLAN_PROTECTED_RE = re.compile(r'\.claude/plans/[^\s]*\.md|docs/ops/plans/[^\s]*\.md|\.claude/checkpoint\.md')


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
    segments = re.split(r'(?:&&|\|\||[;|\n])', cmd)
    hit = any(_PLAN_DESTRUCTIVE_RE.search(seg) and _PLAN_PROTECTED_RE.search(seg) for seg in segments)
    if not hit:
        return GateResult(0, "", "")
    _log_trigger("plan-protect", "block", cmd)
    reason = ('BLOCKED: rm/mv/trash targets a plan or checkpoint markdown (.claude/plans/, docs/ops/plans/, '
               '.claude/checkpoint.md). These are usually untracked agent state; recovery needs user paste-back. '
               'Use git mv for tracked files, or include PLAN-PROTECT-OVERRIDE to acknowledge the risk.')
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
            proc = subprocess.run([path], input=raw_payload, capture_output=True, text=True, timeout=30)
        except Exception:
            return GateResult(0, "", "")
        return GateResult(proc.returncode, proc.stderr or "", proc.stdout or "")
    return run


# ─────────────────────────────────────────────────────────────────────────
# MANIFEST — EXACT settings.json order. Each entry: name, if_pattern (None =
# always run), run(raw_payload)->GateResult.
# ─────────────────────────────────────────────────────────────────────────

MANIFEST: list[dict] = [
    {"name": "git-noext-inject", "if": "Bash(git*)", "run": gate_git_noext_inject},
    {"name": "pyunbuffered-inject", "if": None, "run": gate_pyunbuffered_inject},
    {"name": "git-add-all-guard", "if": "Bash(git*)", "run": gate_git_add_all_guard},
    {"name": "bash-loop-guard", "if": None, "run": gate_bash_loop_guard},
    {"name": "bash-cat-guard", "if": None, "run": gate_bash_cat_guard},
    {"name": "noext-nongit-guard", "if": None, "run": gate_noext_nongit_guard},
    {"name": "bash-background-ampersand", "if": None,
     "run": make_native_gate("pretool-bash-background-ampersand.py", "pretool_bash_background_ampersand")},
    {"name": "bg-dispatch-footgun", "if": None,
     "run": make_native_gate("pretool-bg-dispatch-footgun.py", "pretool_bg_dispatch_footgun")},
    {"name": "heavy-load-guard", "if": None, "run": gate_heavy_load_guard},
    {"name": "no-background-commit", "if": "Bash(git*)", "run": gate_no_background_commit},
    {"name": "uv-python-guard", "if": None,
     "run": make_native_gate("pretool-uv-python-guard.py", "pretool_uv_python_guard")},
    {"name": "genomics-pythonpath-guard", "if": None,
     "run": make_native_gate("pretool-genomics-pythonpath-guard.py", "pretool_genomics_pythonpath_guard")},
    {"name": "arc-agi-agent-cwd-guard", "if": None,
     "run": make_native_gate("pretool-arc-agi-agent-cwd-guard.py", "pretool_arc_agi_agent_cwd_guard")},
    {"name": "bare-modal-guard", "if": None,
     "run": make_native_gate("pretool-bare-modal-guard.py", "pretool_bare_modal_guard")},
    {"name": "duckdb-quote-guard", "if": None, "run": gate_duckdb_quote_guard},
    {"name": "modal-cost-guard", "if": None, "run": gate_modal_cost_guard},
    {"name": "modal-script-audit", "if": None, "run": gate_modal_script_audit},
    {"name": "cost-guard", "if": None, "run": gate_cost_guard},
    {"name": "cost-awareness", "if": None, "run": gate_cost_awareness},
    {"name": "ast-precommit", "if": "Bash(git commit*)", "run": gate_ast_precommit},
    {"name": "commit-check", "if": "Bash(git commit*)", "run": gate_commit_check},
    {"name": "multiagent-commit-guard", "if": "Bash(git*)",
     "run": make_subprocess_gate(str(HOOKS_DIR / "pretool-multiagent-commit-guard.sh"))},
    {"name": "modal-run-guard", "if": None, "run": gate_modal_run_guard},
    {"name": "timeout-modal-guard", "if": None, "run": gate_timeout_modal_guard},
    {"name": "destructive-git-ref", "if": "Bash(git*)",
     "run": make_subprocess_gate(str(HOOKS_DIR / "pretool-destructive-git-ref.sh"))},
    {"name": "plan-completion-guard", "if": "Bash(git commit*)",
     "run": make_subprocess_gate(str(HOOKS_DIR / "precommit-plan-completion-guard.sh"))},
    {"name": "plan-protect", "if": None, "run": gate_plan_protect},
    {"name": "cursor-model-guard", "if": None,
     "run": make_native_gate("pretool-cursor-model-guard.py", "pretool_cursor_model_guard")},
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
            ctx = (hso.get("additionalContext") if isinstance(hso, dict) else None) or obj.get("additionalContext")
            if ctx:
                return "advise", ctx
            return "pass", ""
        return "advise", stdout
    if stderr:
        return "advise", stderr
    return "pass", ""


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
