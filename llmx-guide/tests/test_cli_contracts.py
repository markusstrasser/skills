"""CLI dispatch contract tripwires — catch when codex / claude / cursor CLIs change
the flags + behaviors our lean/bare/sub dispatch depends on.

These providers ship fast and rename flags or change routing silently (the whole
reason this file exists). Two tiers:

  TIER 1 — FLAG CONTRACTS (cheap, no API spend, always run): parse `<cli> --help` and
  assert the load-bearing flags still exist. Catches a renamed/removed flag the instant
  the CLI updates. ~1s total.

  TIER 2 — LIVE BEHAVIOR (gated on LIVE_CLI=1, run "here and there" — weekly / after a
  CLI update): tiny real dispatches (~pennies) confirming bare/ask/sub modes actually
  work AND stay on the subscription. Skipped by default so CI/dev loops don't pay.

Run:  pytest test_cli_contracts.py                 # flag contracts only
      LIVE_CLI=1 pytest test_cli_contracts.py -v   # + live smokes

Background (the contracts being defended — see `../references/bare-lean-dispatch.md`):
codex `-c mcp_servers={}` strips the 56K MCP overhead; claude `--system-prompt` REPLACES
the harness for a lean free-sub call; cursor `--mode ask` is the lean Composer path (vs
the 38K Cloud-Agents agent); `-p codex-cli` stays on the ChatGPT sub (bare `--subscription`
via llmx silently falls back to the PAID openai-api).
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

LIVE = os.environ.get("LIVE_CLI") == "1"
live = pytest.mark.skipif(not LIVE, reason="set LIVE_CLI=1 to run live dispatch smokes")


def _help(cmd: list[str]) -> str:
    """Return combined --help text, or '' if the binary is absent."""
    if shutil.which(cmd[0]) is None:
        pytest.skip(f"{cmd[0]} not installed")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return (p.stdout or "") + (p.stderr or "")


# ----------------------------------------------------------------------------
# TIER 1 — flag contracts (cheap, always run)
# ----------------------------------------------------------------------------


def test_codex_has_config_override():
    """codex `-c key=value` is how we strip MCP (`mcp_servers={}`) + set effort
    (`model_reasoning_effort=low`). If `-c`/`--config` vanishes, the bare/effort path breaks."""
    h = _help(["codex", "exec", "--help"])
    assert "-c" in h and ("--config" in h), "codex lost -c/--config override"


def test_claude_has_lean_flags():
    """claude `--system-prompt` REPLACES the harness (lean free-sub one-off); `--strict-mcp-config`
    drops project MCPs. Losing either kills the lean-claude path."""
    h = _help(["claude", "--help"])
    assert "--system-prompt" in h, (
        "claude lost --system-prompt (harness no longer replaceable)"
    )
    assert "--strict-mcp-config" in h, "claude lost --strict-mcp-config"


def test_cursor_has_ask_mode_and_apikey():
    """cursor `--mode ask` is the LEAN Composer path (vs the 38K agent); `--api-key` is the
    programmatic auth. The lean Composer arm depends on `--mode ask` existing with the `ask` choice."""
    h = _help(["cursor-agent", "--help"])
    assert "--mode" in h, "cursor-agent lost --mode"
    assert "ask" in h, "cursor-agent --mode lost the 'ask' choice (lean Composer path)"
    assert "--api-key" in h, "cursor-agent lost --api-key"


# ----------------------------------------------------------------------------
# TIER 2 — live behavior smokes (gated; run here and there)
# ----------------------------------------------------------------------------


@live
def test_live_claude_bare_runs_on_subscription():
    """claude bare (key-stripped + no tools + no MCP) must run on the OAuth SUB, not the API.
    rc==0 with the key stripped == sub; an API-billing error would mean the sub path broke."""
    if shutil.which("claude") is None:
        pytest.skip("claude not installed")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")
    }
    p = subprocess.run(
        [
            "claude",
            "-p",
            "--strict-mcp-config",
            "--tools",
            "",
            "--output-format",
            "json",
            "Reply with exactly: OK",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert p.returncode == 0, f"claude bare sub failed: {p.stderr[:200]}"
    assert "OK" in p.stdout, "claude bare produced no OK"


@live
def test_live_codex_bare_and_effort_apply():
    """codex `-c mcp_servers={}` (bare) + `-c model_reasoning_effort=low` must both still apply.
    rc==0 confirms the overrides parse; the effort assertion would need the rollout log (left to
    the operator — see the memory)."""
    if shutil.which("codex") is None:
        pytest.skip("codex not installed")
    p = subprocess.run(
        [
            "codex",
            "exec",
            "--full-auto",
            "--skip-git-repo-check",
            "-c",
            "mcp_servers={}",
            "-c",
            'model_reasoning_effort="low"',
            "Reply with exactly: OK",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert p.returncode == 0, f"codex bare failed: {p.stderr[:200]}"


@live
def test_live_cursor_ask_mode_is_lean():
    """cursor `--mode ask` must produce output (the lean Composer path). Also a latency tripwire:
    ask mode should be FAST (~tens of seconds); if it balloons toward agent-mode times, the
    ephemeral path may have regressed to the full harness."""
    if shutil.which("cursor-agent") is None:
        pytest.skip("cursor-agent not installed")
    import time

    t0 = time.time()
    p = subprocess.run(
        [
            "cursor-agent",
            "-p",
            "--mode",
            "ask",
            "--output-format",
            "text",
            "Reply with exactly: OK",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    dt = time.time() - t0
    assert p.returncode == 0, f"cursor ask failed: {p.stderr[:200]}"
    assert "OK" in p.stdout, "cursor ask produced no output"
    assert dt < 90, (
        f"cursor ask mode took {dt:.0f}s — may have regressed to the agent harness"
    )


@live
def test_live_codex_subscription_route_not_api_fallback():
    """Tripwire for the llmx `--subscription` -> PAID openai-api fallback. `-p codex-cli` MUST keep
    gpt-5.6-sol on the ChatGPT sub. We assert the transport line says codex-cli, not openai-api billing."""
    if shutil.which("llmx") is None:
        pytest.skip("llmx not installed")
    p = subprocess.run(
        [
            "llmx",
            "chat",
            "-m",
            "gpt-5.6-sol",
            "-p",
            "codex-cli",
            "-e",
            "low",
            "Reply with exactly: OK",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # transport line is on stderr; must route codex-cli (sub), never bill the API
    assert "transport" in p.stderr.lower(), f"no transport diagnostic: {p.stderr[:200]}"
    assert "codex-cli" in p.stderr, (
        f"gpt-5.6-sol -p codex-cli did NOT route codex-cli sub: {p.stderr[:300]}"
    )
