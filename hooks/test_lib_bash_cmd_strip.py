#!/usr/bin/env python3
"""Test lib_bash_cmd_strip — the single-sourced bash-command-text preprocessing.

Pins the 4 historical divergence edge cases (each was a live false block or
silent pass while the two hooks carried private stripper copies):
  c1323e8  heredoc body with 'do\\n'/'then\\n' payload false-blocked loop-guard
  ff79b2d  heredoc body saying "Do NOT git commit" false-blocked a brief write
  7af4faa  quoted prose 'then' at end-of-line false-blocked a commit
  681a068  real leading `git commit | tail` must SURVIVE stripping (pipe-mask
           detection depends on the stripper not over-eating command text)

Also asserts both hook sidecars use the lib's exact function objects, so a
future re-privatized copy in either hook fails loudly here.

Run: python3 <thisfile>
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib_bash_cmd_strip as lib  # noqa: E402
import pretool_bash_loop_guard as loop_guard  # noqa: E402
import pretool_no_background_commit as no_bg_commit  # noqa: E402

CHECKS = []


def check(label, ok):
    CHECKS.append((label, ok))
    print(f"  {'✓' if ok else '✗'} {label}")


def main():
    # c1323e8: heredoc body is data — 'do\n'/'then\n' inside it must vanish
    edn = "uv run python3 - <<'EOF'\n:task (do\nthen more edn\nEOF\necho ok"
    stripped = lib.strip_heredocs(edn)
    check("c1323e8 heredoc body do/then stripped",
          not re.search(r"\b(do|then)\s*\n", stripped) and "echo ok" in stripped)

    # ff79b2d: 'git commit' as heredoc prose must vanish; commands around it stay
    brief = ("cat > brief.md <<'EOF'\nDo NOT git commit anything.\nEOF\n"
             "codex exec --full-auto 'x'")
    stripped = lib.strip_heredocs(brief)
    check("ff79b2d heredoc 'git commit' prose stripped",
          "git commit" not in stripped and "codex exec" in stripped)

    # ff79b2d companion: a REAL commit after the heredoc must survive stripping
    after = "cat > b.md <<'EOF'\nhello\nEOF\ngit commit -m real"
    check("ff79b2d real commit after heredoc survives",
          "git commit -m real" in lib.strip_heredocs(after))

    # 7af4faa: quoted span with prose 'then' at EOL vanishes, incl. its newline
    msg = 'git commit -m "goal-confirmation, then\nconfirmed-class fallback"'
    stripped = lib.strip_quoted(msg)
    check("7af4faa quoted 'then' at EOL stripped",
          not re.search(r"\b(do|then)\s*\n", stripped) and stripped.startswith("git commit -m "))
    check("7af4faa escaped dquote inside dquotes",
          not re.search(r"\b(do|then)\s*\n",
                        lib.strip_quoted('echo "escaped \\" quote, then\nstill quoted"')))

    # 681a068: strippers must not over-eat — a leading pipe-masked commit stays matchable
    masked = "git commit -m x 2>&1 | tail -2"
    check("681a068 pipe-masked commit survives strip_heredocs",
          lib.strip_heredocs(masked) == masked)

    # Single-source guard: both sidecars must use THESE function objects
    check("loop-guard imports lib strippers",
          loop_guard.strip_heredocs is lib.strip_heredocs
          and loop_guard.strip_quoted is lib.strip_quoted)
    check("no-background-commit imports lib stripper",
          no_bg_commit.strip_heredocs is lib.strip_heredocs)

    fails = sum(1 for _, ok in CHECKS if not ok)
    print(f"{len(CHECKS) - fails}/{len(CHECKS)} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
