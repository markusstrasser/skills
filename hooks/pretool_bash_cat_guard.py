"""Sidecar for pretool-bash-cat-guard.sh — find missing literal files in $(cat ...).

stdin: the full Bash command string. env CAT_GUARD_CWD: the tool call's cwd (may be empty).
stdout: newline-separated missing literal paths (empty = allow).

Conservative by design (zero-false-positive bias):
- only tokens inside $(cat ...) up to the matching close paren;
- a token is skipped unless it is a LITERAL path: no $ ` * ? [ ~ { } characters;
- flags (-n etc.) and heredoc markers are skipped;
- a path that appears as a redirect target (`> path` / `>> path`) EARLIER in the command
  is skipped (created-before-use pattern);
- relative paths resolve against CAT_GUARD_CWD when provided, else os.getcwd().
"""

import os
import re
import sys


_SHELL_OP = re.compile(r"[|;&]")


def find_cat_spans(cmd: str):
    """Yield the cat ARGUMENTS of each $(cat ...) with naive paren matching.

    The span stops at the first shell operator, so `$(cat f.md | wc -c)` yields
    "f.md " and never "f.md | wc -c". Tokens after a pipe are a downstream
    command, not cat arguments: scanning them as paths blocked valid commands
    with phantom "missing: |" / "missing: wc" (2026-07-26). Truncating fails
    OPEN — an unchecked argument is a missed block, never a false one.
    """
    for m in re.finditer(r"\$\(\s*cat\s+", cmd):
        depth, i = 1, m.end()
        start = i
        while i < len(cmd) and depth:
            if cmd[i] == "(":
                depth += 1
            elif cmd[i] == ")":
                depth -= 1
            i += 1
        yield _SHELL_OP.split(cmd[start : i - 1], 1)[0]


def main() -> None:
    cmd = sys.stdin.read()
    cwd = os.environ.get("CAT_GUARD_CWD") or os.getcwd()
    redirected = {t.rstrip(";&|").strip("\"'") for t in re.findall(r">>?\s*(\S+)", cmd)}
    missing = []
    for span in find_cat_spans(cmd):
        for tok in span.split():
            if tok.startswith("-") or tok in ("<<", "<<<"):
                continue
            if ">" in tok or "<" in tok:
                continue  # redirection (2>/dev/null, <file) — not a cat argument
            if any(c in tok for c in "$`*?[]{}~"):
                continue  # not a literal path — never guess
            tok = tok.strip("\"'")
            if not tok or tok in redirected:
                continue
            path = tok if os.path.isabs(tok) else os.path.join(cwd, tok)
            if not os.path.exists(path):
                missing.append(tok)
    if missing:
        print("\n".join(dict.fromkeys(missing)))


if __name__ == "__main__":
    main()
