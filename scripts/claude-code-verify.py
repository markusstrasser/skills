#!/usr/bin/env python3
"""Run Claude Code as a read-only verifier from automation.

Default mode intentionally uses the local Claude Code auth stack rather than
the Anthropic API key path: unset ``ANTHROPIC_API_KEY``, do not use ``--bare``,
run from a small cwd, and pass the prompt on stdin so secrets/prompts do not
land in process argv.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


READ_ONLY_TOOLS = (
    "Read,"
    "Bash(rg *),"
    "Bash(sed *),"
    "Bash(nl *),"
    "Bash(git grep *),"
    "Bash(git diff *),"
    "Bash(git status *),"
    "Bash(ls *),"
    "Bash(wc *)"
)
WRITE_TOOLS = "Edit,Write,MultiEdit,NotebookEdit"


def _read_prompt(prompt_file: Path | None) -> str:
    if prompt_file is None:
        prompt = sys.stdin.read()
    else:
        prompt = prompt_file.read_text()
    if not prompt.strip():
        raise SystemExit("empty prompt")
    return prompt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Claude Code verifier using local subscription auth by default"
    )
    parser.add_argument("--repo", type=Path, required=True, help="Repository to allow Claude to read")
    parser.add_argument("--prompt-file", type=Path, help="Prompt file. Defaults to stdin")
    parser.add_argument("--output", type=Path, required=True, help="Write Claude output here")
    parser.add_argument("--budget-usd", default="5.00", help="Claude Code --max-budget-usd value")
    parser.add_argument("--timeout", type=int, default=420, help="Subprocess timeout seconds")
    parser.add_argument(
        "--output-format",
        choices=("text", "json", "stream-json"),
        default="text",
        help="Claude Code output format",
    )
    parser.add_argument(
        "--use-api-key",
        action="store_true",
        help="Keep ANTHROPIC_API_KEY and use --bare API-key mode. Default uses local Claude Code auth.",
    )
    parser.add_argument(
        "--allowed-tools",
        default=READ_ONLY_TOOLS,
        help="Claude Code tools to allow. Defaults to read-only file/grep/git inspection.",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not repo.exists():
        raise SystemExit(f"repo does not exist: {repo}")
    prompt = _read_prompt(args.prompt_file)

    env = os.environ.copy()
    command = [
        "claude",
        "-p",
        "--no-session-persistence",
        "--output-format",
        args.output_format,
        "--max-budget-usd",
        args.budget_usd,
        "--add-dir",
        str(repo),
        "--allowedTools",
        args.allowed_tools,
        "--disallowedTools",
        WRITE_TOOLS,
    ]
    if args.use_api_key:
        command.insert(1, "--bare")
    else:
        env.pop("ANTHROPIC_API_KEY", None)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="claude-code-verify-") as tmpdir:
        proc = subprocess.run(
            command,
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmpdir,
            env=env,
            timeout=args.timeout,
            check=False,
        )

    args.output.write_text(proc.stdout)
    if proc.stderr:
        args.output.with_suffix(args.output.suffix + ".stderr").write_text(proc.stderr)

    if proc.returncode != 0:
        print(
            f"claude-code-verify failed with exit {proc.returncode}; "
            f"stdout={args.output} stderr={args.output.with_suffix(args.output.suffix + '.stderr')}",
            file=sys.stderr,
        )
    else:
        print(args.output)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
