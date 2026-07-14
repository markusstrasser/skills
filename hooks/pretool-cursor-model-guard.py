#!/usr/bin/env python3
# Gov-ID: hook:cursor-model-guard
# goal: cursor-agent may run native Composer or exact admitted Cursor Grok
#       slugs — never generic proxied frontier models
# verifier: selftest
# blast_radius: shared
"""BLOCK `cursor-agent` model pins outside the admitted Cursor-native set.

Cursor's CLI can proxy frontier models (opus, gpt, claude, …) at their own
metered rates. Composer remains the default lane. On 2026-07-14 the live Cursor
registry and named/repo smokes admitted exact `cursor-grok-4.5-{low,medium,high}`
slugs (plus trailing `-fast`) for deliberate opt-in use. Bare `grok-4.5`, retired
aliases, and generic opus/gpt/claude/gemini/sonnet pins remain off-policy.

Enforcement, not instruction: a prior session called cursor with a foreign
model anyway. No explicit `--model` is fine — the account default is Composer.
We only block an explicit model outside the admitted set.
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

# Composer stays open to native future tiers. Grok is deliberately exact: registry
# drift previously made stale aliases silently unsafe, so no wildcard family match.
_COMPOSER = re.compile(r"^composer(?:[-.]|$)", re.IGNORECASE)
_CURSOR_GROK = re.compile(
    r"^cursor-grok-4\.5-(?:low|medium|high)(?:-fast)?$", re.IGNORECASE
)

_MSG = (
    "BLOCKED: cursor-agent model '{model}' is not admitted. Use native Composer "
    "(composer-2.5 / composer-2.5-fast) or an exact live Cursor Grok slug "
    "cursor-grok-4.5-{{low,medium,high}} with optional trailing -fast. Bare grok-4.5 "
    "is xAI API; retired xhigh/fast-prefix aliases are forbidden. For opus/gpt use "
    "`claude -p` / `codex exec` / `llmx`, not cursor."
)


def _model_allowed(model: str) -> bool:
    return bool(_COMPOSER.match(model) or _CURSOR_GROK.fullmatch(model))


def _is_cursor(cmd: str) -> bool:
    return bool(
        _CURSOR_AGENT.search(cmd) or _BARE_AGENT.search(cmd) or _DISPATCH_ARM.search(cmd)
    )


# Shell-segment separators. A foreign model blocks ONLY when it sits in the SAME
# segment as the cursor invocation — `cursor-agent …; llmx -m gpt-5.5` is two
# lanes, not cursor routing gpt. (Split before model-matching to kill that FP.)
_SEGMENT = re.compile(r"(?:&&|\|\||[;&|\n])")


def verdict(cmd: str) -> tuple[str, str]:
    if not cmd or not cmd.strip():
        return "pass", ""
    for seg in _SEGMENT.split(cmd):
        if not _is_cursor(seg):
            continue
        models: list[str] = [m.group(2) for m in _MODEL.finditer(seg)]
        if _DISPATCH_ARM.search(seg):
            arm = _ARM_MODEL.search(seg)
            if arm:
                models.append(arm.group(1))
        for model in models:
            if not _model_allowed(model):
                return "block", _MSG.format(model=model)
    return "pass", ""


def _selftest() -> int:
    cases = [
        ("agent -p --mode ask --trust --model composer-2.5 'hi'", "pass"),
        ("agent -p --trust --model composer-2.5-fast 'x'", "pass"),
        ("agent -p --mode ask --trust --model cursor-grok-4.5-low 'x'", "pass"),
        ("agent -p --mode ask --trust --model cursor-grok-4.5-medium-fast 'x'", "pass"),
        ("agent -p --mode ask --trust --model cursor-grok-4.5-high 'x'", "pass"),
        ("agent -p --trust --model grok-4.5 'x'", "block"),
        ("agent -p --trust --model cursor-grok-4.5-xhigh 'x'", "block"),
        ("agent -p --trust --model cursor-grok-4.5-fast-high 'x'", "block"),
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
        # dual-lane: cursor-agent (no model) + a SEPARATE llmx -m foreign → not cursor routing (FP fix, 2026-06-22)
        ("which cursor-agent; llmx chat --subscription -m gpt-5.5 'ping'", "pass"),
        ("cursor-agent --version; llmx -m claude-opus-4-8 'x'", "pass"),
        ("cursor-agent -p --model composer-2.5 'a' && llmx -m opus 'b'", "pass"),
        # but a foreign model IN the cursor segment still blocks
        ("cursor-agent -p --model gpt-5.5 'a' && echo done", "block"),
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
