#!/usr/bin/env python3
"""pretool_bash_approval_held_guard.py — block Bash commands that Claude Code holds for
explicit approval even under bypassPermissions, before Claude Code sees them.

An in-process background teammate has nobody to answer that prompt, so its call waits with
no process behind it until someone stops the lane (lane-stall-watch reports STALLED_TOOL).
A headless run is denied. Two classes are known:

1. `zsh_flag` — zsh parameter-expansion flag groups (`${(f)x}`, `"${(j:,:)arr}"`). Claude
   Code (2.1.310) cannot parse them: "This command could not be checked for dangerous rm
   operations: the shell may read it differently than it was parsed." Evidence: genomics
   lane negatives-panels, 2026-10-27 05:27:58 and 05:41:47 JST, the lane's only two calls
   using `${(f)nodes}` never ran; probes the same morning (`claude -p --permission-mode
   bypassPermissions`, haiku) denied `${(f)x}` and `"${(j:,:)arr}"`, ran `${=x}`.

2. `rm_var` / `rm_cmdsub` — a recursive rm whose target Claude Code (2.1.311) cannot prove
   safe: "Dangerous rm operation detected ... The target '"$P/$dir"' is a shell variable
   expansion: when $P or $dir is unset or empty it becomes `/`, `/*` or a top-level path."
   Evidence: negatives-panels hung 06:55-07:04 JST on
   `for dir in ...; do ... rm -rf "$P/$dir"; done`; probes 07:02-07:06 JST. The check fires
   when a target reduces to `/`, `/*` or a top-level path with every unresolved expansion
   empty; `${NAME:?}` and `$TMPDIR` count as safe, a literal assignment earlier in the same
   top-level list resolves, nothing resolves inside a for/while/until/if/case body, and a
   command-substitution target is always held.

Claude Code parses rm phrases inside double-quoted text too. Probe 2026-10-27 07:25 JST:
`echo "step 2; rm -r $D/" > /dev/null` was denied with "The rm is inside a quoted string, but
the guard parses it anyway". So a block on a commit message or echo that mentions
`rm -rf $X/y` matches Claude Code and is not a false positive. Quoted-delimiter heredoc
bodies stay masked: `cat <<'EOF'` and `python3 - <<'EOF'` bodies holding `rm -rf "$P/$d"`
ran. One residual is unexplained: a `cd X && python3 -I - <<'EOF'` whose body held
`'echo "step 2; rm -r $D/" > notes.txt',` was denied ("parsed again before it runs (it is
inside a quoted string or after eval)"); this guard does not block that shape.

Contract (sidecar convention): `offending(cmd)` returns the first Hit or None; `reason(hit)`
is the block text. Literal text (single quotes, $'...', comments, quoted-delimiter heredoc
bodies) is masked by lib_bash_cmd_strip.live_mask, so writing such text into a file through
`cat <<'EOF'` stays allowed. Bias is to recall: a miss hangs a lane, a false block costs one
rewrite.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from lib_bash_cmd_strip import live_mask


class Hit(NamedTuple):
    kind: str  # "zsh_flag" | "rm_var" | "rm_cmdsub" | "rm_mount"
    excerpt: str


# ------------------------------------------------------------------ class 1: zsh flags
_FLAG_GROUP = re.compile(r"\$\{\([^)\n]*\)")


def _zsh_flag(cmd: str, mask: str) -> str | None:
    match = _FLAG_GROUP.search(mask)
    if match is None:
        return None
    close = cmd.find("}", match.end())
    end = match.end() if close < 0 else close + 1
    return cmd[match.start() : min(end, match.start() + 60)]


# ------------------------------------------------------------------ class 2: rm targets
_SEPARATOR = re.compile(r"&&|\|\||[;&|\n()]|(?<!\$)\{")
_STOP = set(";&|\n)")
_ASSIGN = re.compile(r"([A-Za-z_]\w*)=(.*)\Z", re.S)
_OPENERS = {"if", "while", "until"}
_HEADERS = {"for", "case", "select"}
_CLOSERS = {"done", "fi", "esac"}
_PREFIX = {"then", "do", "else", "elif", "!", "{", "(", "time", "sudo", "command", "builtin"}
# Wrappers that run their argument as a command: skip their options (and env NAME=value
# words, nice's priority, timeout's duration). `nohup rm -rf "$X/"` was held (2026-10-27).
_WRAPPERS = {"nohup", "exec", "nice", "env", "caffeinate", "timeout", "gtimeout"}
_RM = re.compile(r"(?:.*/)?rm")
# `/`, `/x`, `/x/`, `/x/<glob>`, or any path whose first component is a glob (`/*/a/b`).
_ROOTISH = re.compile(r"/(?:[^/]*/?|[^/]+/[^/]*\*[^/]*|[^/]*\*[^/]*/.*)")
_MOUNT = re.compile(r"/Volumes(?:/[^/]+){0,2}/?")
_TMP = "/tmp/T"


def _read_word(s: str, i: int) -> int:
    """Return the end offset of the shell word starting at s[i]."""
    n = len(s)
    while i < n:
        c = s[i]
        if c in " \t" or c in _STOP or c in "<>":
            return i
        if c == "\\":
            i += 2
        elif c == "'":
            close = s.find("'", i + 1)
            i = n if close < 0 else close + 1
        elif c == '"':
            if s.find('"', i + 1) < 0:
                return i  # the closing quote of an enclosing string: `echo "...; rm -r $D/"`
            i += 1
            while i < n and s[i] != '"':
                if s[i] == "\\":
                    i += 2
                elif s.startswith("$(", i) or s[i] == "`":
                    i = _skip_sub(s, i)
                else:
                    i += 1
            i += 1
        elif s.startswith("$(", i) or c == "`":
            i = _skip_sub(s, i)
        elif s.startswith("${", i):
            close = s.find("}", i)
            i = n if close < 0 else close + 1
        else:
            i += 1
    return n


def _skip_sub(s: str, i: int) -> int:
    if s[i] == "`":
        close = s.find("`", i + 1)
        return len(s) if close < 0 else close + 1
    depth, i = 0, i + 1
    while i < len(s):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(s)


def _words(s: str, mask: str, i: int):
    """Yield (start, end) of the words of the simple command starting at i; skip redirects."""
    n, first = len(s), True
    while i < n:
        while i < n and (s[i] in " \t" or s.startswith("\\\n", i)):
            i += 2 if s[i] == "\\" else 1
        # A command that starts in masked text is literal data (heredoc body, comment).
        if i >= n or s[i] in _STOP or (first and mask[i] != s[i]):
            return
        first = False
        redirect = re.match(r"\d*(?:>>|>&|<<<|<<-?|&>|[<>])", s[i:])
        if redirect:
            i += redirect.end()
            while i < n and s[i] in " \t":
                i += 1
            i = _read_word(s, i)
            continue
        end = _read_word(s, i)
        if end == i:
            return
        yield i, end
        i = end


_VAR_NAMES = re.compile(r"\$\{?([A-Za-z_]\w*)")
_VAR = re.compile(r"\$(?:\{([^}]*)\}|([A-Za-z_]\w*)|([0-9@*#?$!-]))")


def _reduce(word: str, env: dict[str, str], derived=frozenset()) -> tuple[str, bool]:
    """Reduce a word to the path it names with unresolved expansions empty.

    Returns (path, resolved) where resolved is False when any expansion fell back to "".
    """
    out: list[str] = []
    resolved = True
    i, n, in_dq = 0, len(word), False
    while i < n:
        c = word[i]
        if c == '"':
            in_dq = not in_dq
            i += 1
        elif c == "'" and not in_dq:
            close = word.find("'", i + 1)
            close = n if close < 0 else close
            out.append(word[i + 1 : close])
            i = close + 1
        elif c == "\\":
            out.append(word[i + 1 : i + 2])
            i += 2
        elif c == "$":
            match = _VAR.match(word, i)
            if match is None:
                out.append(c)
                i += 1
                continue
            braced, plain = match.group(1), match.group(2)
            name = plain or (re.match(r"[A-Za-z_]\w*", braced).group(0)
                             if braced and re.match(r"[A-Za-z_]", braced) else None)
            guarded = braced is not None and name and re.fullmatch(
                re.escape(name) + r":?\?.*", braced, re.S
            )
            if guarded and name in derived:
                out.append(env[name])  # a guard cannot help: the value is non-empty but rootish
            elif guarded:
                out.append("G")
            elif name == "TMPDIR" and (plain or braced == "TMPDIR"):
                out.append(_TMP)
            elif name and (plain or braced == name) and name in env:
                out.append(env[name])
            else:
                resolved = False
            i = match.end()
        else:
            out.append(c)
            i += 1
    return re.sub(r"/+", "/", "".join(out)), resolved


def _rm_hit(s: str, mask: str, spans, env: dict[str, str], derived, in_body: bool) -> Hit | None:
    recursive, targets, opts_done = False, [], False
    for start, end in spans:
        word = s[start:end]
        if not opts_done and word == "--":
            opts_done = True
        elif not opts_done and word == "--recursive":
            recursive = True
        elif not opts_done and re.fullmatch(r"-[A-Za-z]+", word):
            recursive = recursive or "r" in word or "R" in word
        elif not opts_done and word.startswith("--"):
            continue
        else:
            targets.append((start, end))
    for start, end in targets:
        word, live = s[start:end], mask[start:end]
        if "$(" in live or "`" in live:
            return Hit("rm_cmdsub", word[:120])
        # A glob defeats assignment resolution: after P=/literal, `rm -rf $P/dl $P/*.log` was
        # held on `$P/*.log` only, and `rm -f "$D"/*" "*.log` was held (2.1.311 history).
        scope = {} if "*" in word else env
        path, resolved = _reduce(word, scope, derived & set(scope))
        if resolved and "$" not in live and _MOUNT.fullmatch(path):
            return Hit("rm_mount", word[:120])
        if resolved and not (derived & set(_VAR_NAMES.findall(live))):
            continue
        # Non-recursive rm is held only on a glob or inside a compound body (probes 4, 10 ran).
        if _ROOTISH.fullmatch(path) and (recursive or in_body or "*" in path):
            return Hit("rm_var", word[:120])
    return None


def _rm(cmd: str, mask: str) -> Hit | None:
    starts = [0] + [match.end() for match in _SEPARATOR.finditer(mask)]
    top: dict[str, str] = {}
    body: dict[str, str] = {}  # assignments made inside the current compound body
    derived: set[str] = set()  # names assigned from a value with an unresolved expansion
    depth = 0
    for pos in starts:
        spans = list(_words(cmd, mask, pos))
        k = 0
        while k < len(spans):
            word = cmd[spans[k][0] : spans[k][1]]
            if word in _OPENERS:
                depth += 1
            elif word in _HEADERS:
                depth += 1
                break
            elif word in _CLOSERS:
                depth = max(0, depth - 1)
                if depth == 0:
                    derived -= set(body)
                    body.clear()
                break
            elif word in _PREFIX:
                pass
            elif word in _WRAPPERS:
                k += 1
                takes_arg = word in ("timeout", "gtimeout")
                while k < len(spans):
                    arg = cmd[spans[k][0] : spans[k][1]]
                    if arg.startswith("-") or (word == "env" and _ASSIGN.match(arg)):
                        # nice -n 10 / timeout -s KILL / env -u NAME carry a value word
                        if arg in ("-n", "-s", "-k", "-u", "--signal", "--kill-after"):
                            k += 1
                        k += 1
                    elif takes_arg:
                        takes_arg = False
                        k += 1
                    else:
                        break
                continue
            elif (assign := _ASSIGN.match(word)) is not None:
                name, value = assign.group(1), assign.group(2)
                env = top if depth == 0 else body
                if "$(" in value or "`" in value:
                    env.pop(name, None)
                    derived.discard(name)
                    k += 1
                    continue
                path, resolved = _reduce(value, env, derived)
                env[name] = path
                if resolved or path.startswith(_TMP):
                    derived.discard(name)
                else:
                    derived.add(name)
                if depth:
                    top.pop(name, None)
            elif word in ("sh", "bash", "zsh") and k + 2 < len(spans) and cmd[
                spans[k + 1][0] : spans[k + 1][1]
            ] == "-c":
                script = cmd[spans[k + 2][0] : spans[k + 2][1]]
                if len(script) >= 2 and script[0] == script[-1] and script[0] in "'\"":
                    script = script[1:-1]
                inner = _rm(script, live_mask(script))
                if inner:
                    return inner
                break
            elif _RM.fullmatch(word):  # Claude Code matches rm by basename: /bin/rm
                env = top if depth == 0 else body
                hit = _rm_hit(cmd, mask, spans[k + 1 :], env, derived & set(env), depth > 0)
                if hit:
                    return hit
                break
            else:
                break
            k += 1
    return None


def offending(cmd: str) -> Hit | None:
    has_flag, has_rm = "${(" in cmd, re.search(r"\brm\b", cmd) is not None
    if not (has_flag or has_rm):
        return None
    mask = live_mask(cmd)
    if has_flag:
        flag = _zsh_flag(cmd, mask)
        if flag:
            return Hit("zsh_flag", flag)
    return _rm(cmd, mask) if has_rm else None


_HELD = (
    "Claude Code holds it for explicit approval even in bypass mode; a background agent cannot "
    "answer, so the call hangs (a headless run is denied).\n"
)


def reason(hit: Hit) -> str:
    if hit.kind == "zsh_flag":
        return (
            f"BLOCKED: zsh expansion flag {hit.excerpt}. Claude Code cannot parse ${{(...)...}} flag "
            "groups. " + _HELD + "Rewrite without the flag group:\n"
            "  lines as arguments:  tr '\\n' '\\0' < FILE | xargs -0 CMD\n"
            "                       (or: while IFS= read -r line; do ...; done < FILE)\n"
            "  split words:         ${=var}\n"
            "  join an array:       printf '%s,' \"${arr[@]}\"\n"
        )
    if hit.kind == "rm_mount":
        return (
            f"BLOCKED: rm target {hit.excerpt} is a mounted drive or a folder at its top level. "
            + _HELD + "Name the path deeper inside by its full literal path.\n"
        )
    if hit.kind == "rm_cmdsub":
        return (
            f"BLOCKED: recursive rm on a command-substitution target {hit.excerpt}. " + _HELD
            + "Run the substitution on its own first, then remove the literal paths it prints.\n"
        )
    return (
        f"BLOCKED: recursive rm target {hit.excerpt} can expand to / or a top-level path when a "
        "variable is unset or empty. " + _HELD
        + "Rewrite each variable with a guard, e.g. rm -rf \"${P:?}/${dir:?}\", or use a literal "
        "absolute path. The rm may sit inside a double-quoted string (Claude Code parses those "
        "too): reword a commit message or echo that mentions `rm -rf $X/y`, or single-quote it.\n"
    )
