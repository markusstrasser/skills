#!/usr/bin/env python3
"""Regression tests for the multiline zsh syntax preflight.

Tests the sidecar predicate and the shell wrapper (exit 2 means block).
Run: python3 <thisfile>
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SH = HERE / "pretool-bash-loop-guard.sh"

sys.path.insert(0, str(HERE))
from pretool_bash_loop_guard import syntax_error  # noqa: E402


def run_sh(command: str) -> int:
    env = {"tool_name": "Bash", "tool_input": {"command": command}}
    result = subprocess.run(
        ["bash", str(SH)],
        input=json.dumps(env),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode


CURRENT_TURN_COMMAND = """for f in experiments/tranche4_affinity/out/hx01_opus.json experiments/tranche4_affinity/out/hx04_opus.json experiments/tranche4_affinity/out/hx01_gpt.json experiments/tranche4_affinity/out/hx04_gpt.json; do
  echo "$f"
  jq '{keys:(keys), game:(.game_id // .game), stop_reason, levels_completed, nsteps:(.steps|length), nhyp:([.steps[]?|select(.hypothesis != null)]|length), first_levelups:[.steps[]?|select((.frame_after.levels_completed // 0)>0)|{i:(.step // .turn // .action_index),action,levels:(.frame_after.levels_completed // null)}][0:4]}' "$f"
done
jq '.steps[0] | keys' experiments/tranche4_affinity/out/hx01_opus.json
jq '.steps[0:3]' experiments/tranche4_affinity/out/hx01_opus.json | head -n 160
find data/agi3 external_envs agent -path '*environment_files*' -type f -iname 'hx01*' -o -iname 'hx04*' 2>/dev/null | head -n 30"""


# (command, expected_block, label)
CASES = [
    # PASS: ordinary multiline zsh control structures, including the live failure.
    (CURRENT_TURN_COMMAND, False, "exact current-turn multiline for regression"),
    ("for x in a b; do\n  echo $x\ndone", False, "valid multiline for"),
    ("while read l; do\n  echo $l\ndone < f", False, "valid multiline while"),
    ("if [ -f x ]; then\n  echo yes\nfi", False, "valid multiline if"),
    ('echo "prefix" && for x in a; do\n echo $x\ndone', False, "loop after quoted string"),
    # BLOCK: actual parse failures in the shape this guard was intended to catch.
    ("for x in a b; do\n  echo $x", True, "for missing done"),
    ("while read l; do\n  echo $l", True, "while missing done"),
    ("if [ -f x ]; then\n  echo yes", True, "if missing fi"),
    # PASS: non-candidate commands remain fail-open and cost no zsh subprocess.
    ("for x in a b; do echo $x; done", False, "single-line for"),
    (
        'git commit -m "goal-confirmation, then\nconfirmed-class fallback"',
        False,
        "quoted prose ending in then",
    ),
    (
        "python3 - <<'EOF'\nfor x in y: do_thing()  # do\nthen = 1\nEOF",
        False,
        "do and then inside heredoc body",
    ),
    ("echo done", False, "plain command"),
]


def main() -> int:
    if shutil.which("zsh") is None:
        print("SKIP: zsh is unavailable")
        return 0

    failures = 0
    for command, expected_block, label in CASES:
        unit_block = syntax_error(command) is not None
        shell_rc = run_sh(command)
        wrapper_block = shell_rc == 2
        ok = unit_block == expected_block and wrapper_block == expected_block
        print(
            f"  {'✓' if ok else '✗'} {label} "
            f"(unit={unit_block} sh_exit={shell_rc} want_block={expected_block})"
        )
        failures += 0 if ok else 1

    # `zsh -n` must never execute a syntactically valid command while checking it.
    with tempfile.TemporaryDirectory() as tmp:
        sentinel = Path(tmp) / "must-not-exist"
        command = f"for x in a; do\n  touch {sentinel}\ndone"
        no_side_effect = syntax_error(command) is None and not sentinel.exists()
        print(f"  {'✓' if no_side_effect else '✗'} zsh -n has no side effects")
        failures += 0 if no_side_effect else 1

    print(f"{len(CASES) + 1 - failures}/{len(CASES) + 1} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
