"""Sidecar for the cat-guard — find missing literal files read by $(cat ...).

stdin: the full Bash command string. env CAT_GUARD_CWD: the tool call's cwd (may be empty).
stdout: newline-separated missing literal paths (empty = allow).

Callers: pretool-bash-dispatch.py (gate_bash_cat_guard, imports missing_paths) and
pretool-bash-cat-guard.sh (runs main). Both go through missing_paths, the one token filter.

Conservative by design (zero-false-positive bias):
- only a $(cat ...) the shell would EXECUTE counts; quoted heredoc bodies, single-quoted
  text, escaped \\$( and comments are data (lib_bash_cmd_strip.live_mask);
- a token is skipped unless it is a LITERAL path: no $ ` * ? [ ~ { } < > characters;
- flags (-n etc.) are skipped, and the span ends at a shell operator or `<<`;
- a path that appears as a redirect target (`> path` / `>> path`) in the command is
  skipped (created-before-use pattern);
- relative paths resolve against the caller's cwd.
"""

import os
import re
import shlex
import sys

from lib_bash_cmd_strip import live_mask

_SPAN_END = re.compile(r"[|;&]|<<")


def find_cat_spans(cmd: str):
    """Yield the argument text of each $(cat ...) the shell would execute.

    Matching runs on live_mask(cmd), so a "$(cat x)" written as data is never read as
    a substitution: 2026-09-22 had three false blocks in one session, from text inside
    <<'EOF' bodies (twice) and an escaped \\$(cat ...) in a commit message. The span is
    cut from the ORIGINAL text so quoted arguments keep their characters.

    The span stops at the first shell operator, so `$(cat f.md | wc -c)` yields
    "f.md " and never "f.md | wc -c". Tokens after a pipe are a downstream
    command, not cat arguments: scanning them as paths blocked valid commands
    with phantom "missing: |" / "missing: wc" (2026-07-26). It also stops at `<<`,
    where cat reads a heredoc or here-string instead of files. Truncating fails
    OPEN — an unchecked argument is a missed block, never a false one.
    """
    live = live_mask(cmd)
    # One whitespace char only: `\s+` would run on through a blanked 'quoted arg'.
    for m in re.finditer(r"\$\(\s*cat\s", live):
        depth, i = 1, m.end()
        while i < len(live) and depth:
            if live[i] == "(":
                depth += 1
            elif live[i] == ")":
                depth -= 1
            i += 1
        end = i - 1 if depth == 0 else len(live)
        cut = _SPAN_END.search(live, m.end(), end)
        yield cmd[m.end() : cut.start() if cut else end]


def missing_paths(cmd: str, cwd: str) -> list[str]:
    """Literal paths read by a live $(cat ...) that do not exist, deduplicated in order."""
    redirected = {t.rstrip(";&|").strip("\"'") for t in re.findall(r">>?\s*(\S+)", cmd)}
    missing = []
    for span in find_cat_spans(cmd):
        try:
            tokens = shlex.split(span)
        except ValueError:
            continue  # unbalanced quoting inside the span — never guess
        for tok in tokens:
            if not tok or tok.startswith("-") or tok in redirected:
                continue
            if any(c in tok for c in "<>$`*?[]{}~"):
                continue  # redirection or not a literal path — never guess
            path = tok if os.path.isabs(tok) else os.path.join(cwd, tok)
            if not os.path.exists(path):
                missing.append(tok)
    return list(dict.fromkeys(missing))


def main() -> None:
    missing = missing_paths(sys.stdin.read(), os.environ.get("CAT_GUARD_CWD") or os.getcwd())
    if missing:
        print("\n".join(missing))


if __name__ == "__main__":
    main()
