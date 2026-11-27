#!/usr/bin/env python3
"""Stub Antigravity CLI used by the lane dispatch tests."""
import json
import os
import sys
import time
from pathlib import Path


def emit(event):
    print(json.dumps(event), flush=True)


args = sys.argv[1:]
model = args[args.index("--model") + 1]
effort = args[args.index("--effort") + 1]
prompt = args[args.index("-p") + 1]
mode = os.environ.get("FAKE_AGY_MODE", "success")
calls = Path(os.environ["FAKE_AGY_CALLS"])
assert all(key not in os.environ for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"))
zdotdir = os.environ.get("ZDOTDIR")
with calls.open("a") as f:
    print(json.dumps({"args": args, "cwd": str(Path.cwd()), "env": sorted(os.environ),
                      "zdotdir": sorted(os.listdir(zdotdir)) if zdotdir else None}), file=f)

if prompt == "/model":
    assert "--disable-slash-commands=false" in args
    assert args[args.index("--output-format") + 1] == "json"
    slow_marker = calls.with_suffix(".slow")
    if mode == "slow-model" or (mode == "slow-model-once" and not slow_marker.exists()):
        slow_marker.touch()
        time.sleep(3)
    emit({"status": "SUCCESS", "num_turns": 0, "command": {"name": "model", "data": {
        "id": "unexpected-variant" if mode == "wrong-selection" else model, "effort": effort,
    }}})
    sys.exit(0)

assert "--disable-slash-commands" in args
assert args[args.index("--output-format") + 1] == "stream-json"
conversation = args[args.index("--conversation") + 1] if "--conversation" in args else "fake-conversation"
emit({"event": "init", "conversation_id": conversation,
      "init": {"model": model, "permission_mode": "proceed-in-sandbox"}})

if mode == "hold":
    release = calls.with_suffix(".release")
    deadline = time.monotonic() + 15
    while not release.exists():
        assert time.monotonic() < deadline, "test never released the fake AGY turn"
        time.sleep(0.05)
    Path("tracked.txt").write_text("agy changed this\n")

result = {"conversation_id": conversation, "status": "SUCCESS", "response": "Fake AGY response."}
if mode == "quota":
    result.update(status="ERROR", error="ResourceExhausted, HTTP 429: Individual quota reached. Resets in 4h.")
elif mode == "capacity" or (mode == "capacity-once" and "--conversation" not in args):
    print('AGY_ERROR: {"status":"UNAVAILABLE","message":"Selected model is at capacity"}', file=sys.stderr)
    sys.exit(3)
emit({"event": "step_update", "step_update": {"step_type": "agent_response", "state": "DONE"}})
emit({"event": "result", "result": result})
