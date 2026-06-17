#!/usr/bin/env python3
# Gov-ID: hook:cursor-model-guard
# goal: cursor-agent must only ever run its native Composer model — never a
#       proxied frontier model (opus/gpt/claude/gemini/sonnet/o*)
# verifier: selftest
# blast_radius: shared
"""BLOCK `cursor-agent`/`agent` invocations that pin a non-Composer model.

Cursor's CLI can proxy frontier models (opus, gpt, claude, …) at their own
metered rates. Operator rule (2026-06-17, stated twice in-session): cursor is
the *Composer* lane — always `composer-2.5`/`-fast`, never another model. Using
opus/gpt through cursor is both off-policy and wasteful (Composer is the cheap
included-usage tier; proxied models bill separately).

Enforcement, not instruction: a prior session called cursor with a foreign
model anyway. No explicit `--model` is fine — the account default is Composer.
We only block an EXPLICIT non-composer model.
"""
from __future__ import annotations

import json
import re
import sys

# A cursor-agent invocation: `cursor-agent …`, or bare `agent …` paired with a
# cursor-typical flag (bare `agent` alone is too generic to assume).
_CURSOR_FLAG = r"(?:-p\b|--print\b|--trust\b|--mode\b|--model\b|--workspace\b|--yolo\b|--force\b|--output-format\b|--resume\b|--continue\b)"
_CURSOR_AGENT = re.compile(r"(?:^|[;&|(]|\bcd\b[^;&|]*?(?:&&|;)\s*)\s*cursor-agent\b")
_BARE_AGENT = re.compile(rf"(?:^|[;&|(])\s*agent\b(?=[^;&|]*{_CURSOR_FLAG})")
_DISPATCH_ARM = re.compile(r"\bdispatch-cursor-arm\.sh\b")

# model pinned via --model X / --model=X / -m X
_MODEL = re.compile(r"(?:--model[=\s]+|(?<![\w-])-m\s+)([\"']?)([A-Za-z0-9._/-]+)\1")
# dispatch-cursor-arm.sh <workspace> <model> ask "<prompt>" — model is arg #2
_ARM_MODEL = re.compile(r"\bdispatch-cursor-arm\.sh\s+\S+\s+([A-Za-z0-9._/-]+)")

# Composer is the only allowed family (any tier: composer-2.5, -fast, future).
_ALLOWED = re.compile(r"^composer(?:[-.]|$)", re.IGNORECASE)

_MSG = (
    "BLOCKED: cursor-agent must use its native Composer model only "
    "(composer-2.5 / composer-2.5-fast) — never '{model}'. "
    "Cursor proxies frontier models (opus/gpt/claude) at separate metered rates "
    "and that's off-policy here. Drop the foreign --model (account default is "
    "Composer) or pass --model composer-2.5. For opus/gpt use `claude -p` / "
    "`codex exec` / `llmx`, not cursor."
)


def _is_cursor(cmd: str) -> bool:
    return bool(
        _CURSOR_AGENT.search(cmd) or _BARE_AGENT.search(cmd) or _DISPATCH_ARM.search(cmd)
    )


def verdict(cmd: str) -> tuple[str, str]:
    if not cmd or not cmd.strip():
        return "pass", ""
    if not _is_cursor(cmd):
        return "pass", ""
    models: list[str] = [m.group(2) for m in _MODEL.finditer(cmd)]
    if _DISPATCH_ARM.search(cmd):
        arm = _ARM_MODEL.search(cmd)
        if arm:
            models.append(arm.group(1))
    for model in models:
        if not _ALLOWED.match(model):
            return "block", _MSG.format(model=model)
    return "pass", ""


def _selftest() -> int:
    cases = [
        ("agent -p --mode ask --trust --model composer-2.5 'hi'", "pass"),
        ("agent -p --trust --model composer-2.5-fast 'x'", "pass"),
        ("cursor-agent --model opus 'review this'", "block"),
        ("agent -p --trust --model gpt-5.5 'do it'", "block"),
        ("agent -p --trust -m claude-opus-4-8 'x'", "block"),
        ("agent -p --trust --model=sonnet 'x'", "block"),
        ("cursor-agent -p --trust 'no model = account default'", "pass"),
        ("agent models", "pass"),  # bare agent, no cursor flag → not matched
        ("agent status", "pass"),
        ("~/Projects/evals/bin/dispatch-cursor-arm.sh /tmp/wt composer-2.5 ask 'x' o.txt", "pass"),
        ("dispatch-cursor-arm.sh /tmp/wt opus ask 'x' o.txt", "block"),
        ("llmx chat -m claude-opus-4-8 'hi'", "pass"),  # not cursor
        ("python3 -m agent_infra.foo", "pass"),
        ("cd ~/Projects/foo && agent -p --trust --model gpt-5.5 'x'", "block"),
        ("git commit -m 'add agent'", "pass"),
    ]
    bad = 0
    for cmd, want in cases:
        got = verdict(cmd)[0]
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} want={want:<5} got={got:<5} {cmd!r}")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    action, msg = verdict(cmd)
    if action == "block":
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
