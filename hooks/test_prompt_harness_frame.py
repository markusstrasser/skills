"""Harness-frame skip (harness_frame.py) and PRIOR-CONTEXT junk-token stripping.
Run: uv run --no-project --with pytest python3 -m pytest -q hooks/test_prompt_harness_frame.py
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness_frame  # noqa: E402

PRIOR = HERE / "userprompt-prior-context.py"


def _load_prior():
    spec = importlib.util.spec_from_file_location("prior_context", PRIOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_task_notification_is_frame():
    assert harness_frame.is_harness_frame("<task-notification>\n<status>done</status>")


def test_peer_relay_is_frame():
    assert harness_frame.is_harness_frame("Another Claude session sent a message: hi")


def test_human_prompt_is_not_frame():
    assert not harness_frame.is_harness_frame("should we revisit duckdb invocation now?")


def test_missing_authorship_fails_open_but_keeps_task_notification(monkeypatch, tmp_path):
    monkeypatch.setattr(harness_frame, "AUTHORSHIP", tmp_path / "missing.py")
    monkeypatch.setattr(harness_frame, "_MOD", None)
    assert not harness_frame.is_harness_frame("Another Claude session sent a message: hi")
    assert harness_frame.is_harness_frame("<task-notification>x")


def _run_prior(prompt: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, str(PRIOR)],
        input=json.dumps({"prompt": prompt, "cwd": str(tmp_path), "session_id": "s"}),
        capture_output=True, text=True, timeout=10, env=env,
    )


def test_prior_context_skips_frames(tmp_path):
    for p in ("<task-notification>should we fix the duckdb invocation?</task-notification>",
              "Another Claude session sent a message: should we fix duckdb invocation?"):
        proc = _run_prior(p, tmp_path)
        assert proc.returncode == 0 and proc.stdout == ""


def test_junk_tokens_dropped():
    kw = _load_prior()._kw(
        "session 3f2a9c1e-77ab-4cde and deadbeef12 in /Users/alien/Projects/genomics/x "
        "~/tmp/foo -users-alien-projects-genomics private tmp duckdb invocation"
    )
    assert set(kw) == {"duckdb", "invocation"}


def test_hexy_english_words_kept():
    assert "facade" in _load_prior()._kw("the facade pattern")
