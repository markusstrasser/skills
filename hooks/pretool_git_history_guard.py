#!/usr/bin/env python3
# Gov-ID: hook:git-history-guard
# goal: in a checkout shared with live peer sessions, block history rewrites of commits this session cannot show it wrote, and any reset --hard
# verifier: skills/hooks/test_bash_dispatch.py (test_git_history_guard_*)
# blast_radius: shared
"""pretool_git_history_guard.py — git semantics for the Bash dispatcher's `git-history-guard`.

Incidents:
  * arc-agi 2026-07-16 (session b7b20a06): `git reset --soft HEAD~1`, meant to split the
    session's own commit, ran after a concurrent peer had committed. It un-committed the
    PEER's commit, and the re-commit published the peer's work under the wrong message
    (recovered from the reflog; fix-forward annotation bd91a04f).
  * arc-agi 2026-07-10 (session ab8eb4c5): `git commit --amend` raced six peers and swept two
    peer rows under the wrong message.
  * genomics 2026-06-27: `git reset --hard` in a shared checkout wiped a teammate's finished,
    uncommitted pass.

Rule, active only when peer-session-count.sh (the single peer detector, also used by the
stash, multiagent-commit and SessionStart hooks) reports >= 1 peer in the target checkout:
  * `git reset --hard` blocks whoever owns HEAD, because it discards every peer's uncommitted
    edits.
  * `git commit --amend`, a non-pathspec `git reset`, and `git rebase` (except its
    continue/abort/skip/quit/edit-todo/show-current-patch controls) block unless HEAD, and
    every commit the command would drop or rewrite (`<target>..HEAD`, `<upstream>..HEAD`,
    capped at RANGE_LIMIT), carries a `Session-ID:` trailer naming this session. A missing
    trailer counts as foreign: nothing then shows this session wrote the commit.
  * Path-scoped resets (`git reset [<tree>] -- <paths>`, `git reset <paths>`, `-p`,
    `--pathspec-from-file`) only unstage paths and always pass.

This session's identity is lib_hook_identity.session_id() (the envelope's `session_id`, then
CLAUDE_CODE_SESSION_ID), plus CODEX_THREAD_ID for Codex. The Bash shell that runs `git commit`
exports the same value under the Bash-only name prepare-commit-msg-session-id.sh stamps into
the trailer; hook processes never see that name (probed 2026-09-21), so keying on it here
would make every HEAD look foreign.

The dispatcher owns shell grammar (`_simple_commands`, the scanner the git-noext mutator
uses); this module owns git argument semantics, `cd`/assignment tracking and the git probes.
Every failure (git missing, timeout, unreadable HEAD, unresolvable target) fails open.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import lib_hook_identity

HOOKS_DIR = Path(__file__).resolve().parent
PEER_BIN = HOOKS_DIR / "peer-session-count.sh"
RANGE_LIMIT = 200
GIT_TIMEOUT = 5
PEER_TIMEOUT = 10

_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
_VAR_RE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
_SESSION_LINE_RE = re.compile(r"^Session-ID:[ \t]*(\S+)[ \t]*$", re.M)

# git global options that consume the next word (git.c handle_options).
_GIT_VALUE_OPTS = {"-c", "--namespace", "--super-prefix", "--config-env", "--attr-source"}
_GIT_REPO_OPTS = ("--git-dir", "--work-tree")
_GIT_REPO_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")

_COMMIT_VALUE_SHORT = set("mFcCt")
_COMMIT_VALUE_LONG = {
    "--message", "--file", "--reedit-message", "--reuse-message", "--fixup", "--squash",
    "--author", "--date", "--template", "--cleanup", "--trailer", "--pathspec-from-file",
}
# parse-options accepts any unique prefix; among `git commit` options only amend starts "am".
_AMEND_SPELLINGS = {"--am", "--ame", "--amen", "--amend"}

_RESET_MODES = {"--soft", "--mixed", "--hard", "--merge", "--keep"}

_REBASE_CONTROLS = {
    "--continue", "--abort", "--skip", "--quit", "--edit-todo", "--show-current-patch",
}
_REBASE_VALUE_SHORT = set("xsXC")
_REBASE_VALUE_LONG = {
    "--onto", "--exec", "--strategy", "--strategy-option", "--whitespace", "--empty", "--trailer",
}

UNKNOWN = object()  # a rev word that is present but cannot be expanded here


@dataclass
class HistoryOp:
    verb: str  # "amend" | "reset" | "rebase"
    display: str
    target_dir: str | None  # None: the command's directory could not be resolved
    git_opts: list[str] = field(default_factory=list)
    git_env: dict[str, str] = field(default_factory=dict)
    reset_mode: str | None = None
    rev: object = None  # str, UNKNOWN, or None (HEAD)
    needs_disambiguation: bool = False  # `git reset X`: X may be a commit or a path
    range_head: str = "HEAD"
    rebase_root: bool = False


@dataclass
class Decision:
    action: str  # "block" | "exposure-clean" | "skip-unresolved"
    detail: str
    message: str = ""


def session_ids(envelope, environ) -> set[str]:
    """Every identity this session's commits can carry (see module docstring)."""
    values = (lib_hook_identity.session_id(envelope), environ.get("CODEX_THREAD_ID") or "")
    return {value.strip() for value in values if value.strip()}


# ── shell-state tracking ────────────────────────────────────────────────────


def _expand(word, shell_vars, environ, cwd):
    """Expand $NAME/${NAME} and a leading ~; None when any part is unknowable here."""
    if word is None or "$(" in word or "`" in word:
        return None
    missing = False

    def repl(match):
        nonlocal missing
        name = match.group(1) or match.group(2)
        if name in shell_vars:
            value = shell_vars[name]
        elif name == "PWD":
            value = cwd
        else:
            value = environ.get(name)
        if value is None:
            missing = True
            return ""
        return value

    out = _VAR_RE.sub(repl, word)
    if missing or "$" in out:
        return None
    if out == "~" or out.startswith("~/"):
        home = environ.get("HOME")
        if not home:
            return None
        out = home + out[1:]
    return out


def _resolve_dir(word, base, shell_vars, environ):
    value = _expand(word, shell_vars, environ, base)
    if value is None or value == "-":
        return None
    if os.path.isabs(value):
        return os.path.normpath(value)
    if base is None:
        return None
    return os.path.normpath(os.path.join(base, value))


def find_ops(commands, base_dir, environ) -> list[HistoryOp]:
    """Walk the dispatcher's simple commands in order, tracking cd and assignments.

    ``commands`` holds ``(kind, assignments, argv)`` triples from the dispatcher's
    ``_simple_commands``; ``push``/``pop`` mark a subshell so its ``cd`` is undone.
    """
    cwd = os.path.normpath(base_dir) if base_dir else None
    shell_vars: dict[str, str | None] = {}
    stack: list[tuple[str | None, dict]] = []
    ops: list[HistoryOp] = []
    for kind, assigns, argv in commands:
        if kind == "push":
            stack.append((cwd, dict(shell_vars)))
            continue
        if kind == "pop":
            if stack:
                cwd, shell_vars = stack.pop()
            continue
        if not argv:
            for name, value in assigns.items():
                shell_vars[name] = _expand(value, shell_vars, environ, cwd)
            continue
        if argv[0] is None:
            continue
        prog = argv[0].rsplit("/", 1)[-1]
        if prog in ("export", "declare", "typeset", "local", "readonly"):
            for word in argv[1:]:
                match = _ASSIGN_RE.match(word or "")
                if match:
                    shell_vars[match.group(1)] = _expand(match.group(2), shell_vars, environ, cwd)
            continue
        if prog in ("cd", "pushd"):
            args = [w for w in argv[1:] if w not in ("-L", "-P", "-e", "-@")]
            cwd = _resolve_dir(args[0] if args else "~", cwd, shell_vars, environ)
            continue
        if prog == "popd":
            cwd = None
            continue
        if prog == "git":
            op = _parse_git(argv[1:], assigns, cwd, shell_vars, environ)
            if op is not None:
                ops.append(op)
    return ops


# ── git argument semantics ──────────────────────────────────────────────────


def _parse_git(args, assigns, cwd, shell_vars, environ) -> HistoryOp | None:
    target = cwd
    resolved = True
    git_opts: list[str] = []
    j = 0
    while j < len(args):
        word = args[j]
        if word is None:
            return None
        if word == "-C":
            if j + 1 >= len(args):
                return None
            target = _resolve_dir(args[j + 1], target, shell_vars, environ)
            j += 2
            continue
        if word in _GIT_REPO_OPTS or word.startswith(tuple(f"{o}=" for o in _GIT_REPO_OPTS)):
            if "=" in word:
                name, raw = word.split("=", 1)
                j += 1
            elif j + 1 < len(args):
                name, raw = word, args[j + 1]
                j += 2
            else:
                return None
            value = _expand(raw, shell_vars, environ, target)
            resolved = resolved and value is not None
            git_opts.append(f"{name}={value}")
            continue
        if word in _GIT_VALUE_OPTS:
            j += 2
            continue
        if word.startswith("-"):
            j += 1
            continue
        break
    if j >= len(args):
        return None
    sub, rest = args[j], args[j + 1 :]
    if sub == "commit":
        op = _amend_op(rest)
    elif sub == "reset":
        op = _reset_op(rest, shell_vars, environ, target)
    elif sub == "rebase":
        op = _rebase_op(rest, shell_vars, environ, target)
    else:
        return None
    if op is None:
        return None
    for name in _GIT_REPO_ENV:
        if name in assigns:
            value = _expand(assigns[name], shell_vars, environ, target)
            resolved = resolved and value is not None
            op.git_env[name] = value or ""
    op.git_opts = git_opts
    op.target_dir = target if resolved else None
    op.display = " ".join(["git", sub, *(w if w is not None else "…" for w in rest)])[:100]
    return op


def _skip_short_cluster(cluster: str, value_letters: set[str]) -> int:
    """Words to skip after a short-option cluster: 1 if its last value-taking letter ends it."""
    for pos, letter in enumerate(cluster):
        if letter in value_letters:
            return 1 if pos == len(cluster) - 1 else 0
    return 0


def _amend_op(rest) -> HistoryOp | None:
    amend = False
    k = 0
    while k < len(rest):
        word = rest[k]
        k += 1
        if word is None or not word.startswith("-") or word == "-":
            continue
        if word == "--":
            break
        if word.startswith("--"):
            name = word.split("=", 1)[0]
            if name in _AMEND_SPELLINGS:
                amend = True
            elif name == "--no-amend":
                amend = False
            elif word in _COMMIT_VALUE_LONG:
                k += 1
            continue
        k += _skip_short_cluster(word[1:], _COMMIT_VALUE_SHORT)
    return HistoryOp("amend", "", None) if amend else None


def _rev_value(word, shell_vars, environ, cwd):
    if word is None:
        return UNKNOWN
    value = _expand(word, shell_vars, environ, cwd)
    return UNKNOWN if value is None else value


def _reset_op(rest, shell_vars, environ, cwd) -> HistoryOp | None:
    mode = None
    path_scoped = False
    positional: list = []
    after_dashdash = None
    k = 0
    while k < len(rest):
        word = rest[k]
        k += 1
        if after_dashdash is not None:
            after_dashdash.append(word)
            continue
        if word is None:
            positional.append(None)
            continue
        if word == "--":
            after_dashdash = []
        elif word in _RESET_MODES:
            mode = word[2:]
        elif word in ("-p", "--patch") or word.startswith("--pathspec-from-file"):
            path_scoped = True
            if word == "--pathspec-from-file":
                k += 1
        elif word.startswith("--"):
            pass  # --quiet, --no-refresh, --recurse-submodules[=..], --intent-to-add, ...
        elif word.startswith("-") and len(word) > 1:
            path_scoped = path_scoped or "p" in word[1:]
        else:
            positional.append(word)
    if path_scoped:
        return None
    if after_dashdash is not None:
        if positional[1:] or after_dashdash:
            return None  # `git reset [<tree>] -- <paths>` only unstages paths
        rev_word = positional[0] if positional else "HEAD"
        disambiguate = False
    elif len(positional) >= 2:
        return None  # `<tree> <paths>` or `<paths>`: path-scoped either way
    elif positional:
        rev_word = positional[0]
        disambiguate = mode is None
    else:
        rev_word = "HEAD"
        disambiguate = False
    op = HistoryOp("reset", "", None, reset_mode=mode)
    op.rev = _rev_value(rev_word, shell_vars, environ, cwd)
    op.needs_disambiguation = disambiguate and op.rev is not UNKNOWN
    return op


def _rebase_op(rest, shell_vars, environ, cwd) -> HistoryOp | None:
    if any(word in _REBASE_CONTROLS for word in rest if word):
        return None
    root = False
    positional: list = []
    k = 0
    while k < len(rest):
        word = rest[k]
        k += 1
        if word is None:
            positional.append(None)
            continue
        if word == "--root":
            root = True
        elif word.startswith("--"):
            if word in _REBASE_VALUE_LONG:
                k += 1
        elif word.startswith("-") and len(word) > 1:
            k += _skip_short_cluster(word[1:], _REBASE_VALUE_SHORT)
        else:
            positional.append(word)
    op = HistoryOp("rebase", "", None, rebase_root=root)
    if root:
        head_word = positional[0] if positional else "HEAD"
        op.rev = None
    else:
        head_word = positional[1] if len(positional) > 1 else "HEAD"
        op.rev = _rev_value(positional[0], shell_vars, environ, cwd) if positional else "@{upstream}"
    head = _rev_value(head_word, shell_vars, environ, cwd)
    op.range_head = head if isinstance(head, str) else "HEAD"
    return op


# ── probes ──────────────────────────────────────────────────────────────────


def _git(op: HistoryOp, environ, *args: str) -> subprocess.CompletedProcess | None:
    env = dict(environ)
    env.update(op.git_env)
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        return subprocess.run(
            ["git", "-C", op.target_dir, *op.git_opts, *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            env=env,
        )
    except Exception:
        return None


def _commits(op: HistoryOp, environ, *revs: str) -> list[tuple[str, list[str]]] | None:
    proc = _git(
        op, environ, "-c", "log.showSignature=false", "log", "--no-color",
        "--format=%H%x1f%B%x1e", *revs, "--",
    )
    if proc is None or proc.returncode != 0:
        return None
    commits = []
    for record in proc.stdout.split("\x1e"):
        sha, _, body = record.strip("\n").partition("\x1f")
        if sha:
            commits.append((sha, _SESSION_LINE_RE.findall(body)))
    return commits


def peer_count(root: str, environ) -> int:
    peer_bin = environ.get("PEER_SESSION_COUNT_BIN") or str(PEER_BIN)
    try:
        out = subprocess.run(
            [peer_bin, root], capture_output=True, text=True, timeout=PEER_TIMEOUT
        ).stdout.strip()
    except Exception:
        return 0
    return int(out) if out.isdigit() else 0


def _range_spec(op: HistoryOp) -> list[str] | None:
    """The revs whose commits the command drops or rewrites, beyond HEAD itself."""
    if op.verb == "rebase" and op.rebase_root:
        return [f"--max-count={RANGE_LIMIT}", op.range_head]
    if op.verb == "amend" or op.rev is None or op.rev is UNKNOWN or op.rev in ("HEAD", "@"):
        return None
    return [f"--max-count={RANGE_LIMIT}", f"{op.rev}..{op.range_head}"]


# ── decision ────────────────────────────────────────────────────────────────


def _owner(ids: list[str]) -> str:
    return f"session {ids[0][:8]}" if ids else "no Session-ID"


def _owner_clause(ids: list[str]) -> str:
    if ids:
        return f"belongs to session {ids[0][:8]}"
    return "has no Session-ID trailer, so nothing shows this session wrote it"


def check(op: HistoryOp, my_ids: set[str], environ) -> Decision | None:
    """Return a block, an exposure-clean row (peers present, allowed), or None (solo/skip)."""
    if op.target_dir is None:
        return Decision("skip-unresolved", f"verb={op.verb} target=unresolved")
    top = _git(op, environ, "rev-parse", "--show-toplevel")
    if top is None or top.returncode != 0 or not top.stdout.strip():
        return None
    root = top.stdout.strip()
    if op.needs_disambiguation:
        probe = _git(op, environ, "rev-parse", "--verify", "--quiet", f"{op.rev}^{{commit}}")
        if probe is None or probe.returncode != 0:
            return None  # `git reset <path>`: unstages one path
    peers = peer_count(root, environ)
    if peers < 1:
        return None
    head = _commits(op, environ, "-1", "HEAD")
    if not head:
        return None
    head_sha, head_ids = head[0]
    detail = f"verb={op.verb} peers={peers} head={head_sha[:7]} owner={_owner(head_ids)}"

    if op.verb == "reset" and op.reset_mode == "hard":
        return Decision(
            "block",
            detail + " mode=hard",
            f"BLOCK: `{op.display}` discards every uncommitted change in this checkout, and "
            f"{peers} live peer session(s) share it, so their in-flight edits would be lost "
            f"(genomics 2026-06-27). HEAD is {head_sha[:7]} ({_owner(head_ids)}). Discard only "
            "your own paths (`git stash push -- <paths>` keeps them recoverable) or reset inside "
            "your own worktree, and fix forward with a new commit.\n",
        )

    checked = list(head)
    spec = _range_spec(op)
    if spec:
        dropped = _commits(op, environ, *spec)
        if dropped:
            checked += [c for c in dropped if c[0] != head_sha]
    for sha, ids in checked:
        if set(ids) & my_ids:
            continue
        if sha == head_sha:
            subject = f"HEAD {sha[:7]} {_owner_clause(ids)}"
        else:
            subject = (
                f"HEAD {head_sha[:7]} is yours, but {sha[:7]} in the rewritten range "
                f"({spec[-1]}) {_owner_clause(ids)}"
            )
        unstage_all = op.verb == "reset" and op.reset_mode in (None, "mixed") and op.rev in (
            "HEAD",
            "@",
        )
        effect = "resets the whole shared index" if unstage_all else "rewrites history"
        hint = " To unstage only your own files: `git reset -- <paths>`." if unstage_all else ""
        return Decision(
            "block",
            f"{detail} offending={sha[:7]}",
            f"BLOCK: `{op.display}` {effect} in a checkout shared with {peers} live peer "
            f"session(s), and {subject}. A peer can commit between your last look and the "
            "rewrite: `git reset --soft HEAD~1` once un-committed a peer's commit and "
            "republished it under the wrong message (arc-agi 2026-07-16). Fix forward with a "
            "new commit instead (a follow-up commit, or `git revert <sha>`), or rewrite only "
            f"inside your own worktree.{hint}\n",
        )
    return Decision("exposure-clean", detail)
