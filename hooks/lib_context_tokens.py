"""Shared context-size measurement for Stop hooks (one definition — the
goal-night controller and the generic pre-compact wrap-up must agree on
what "current context" means, or their thresholds silently diverge).

Context = last assistant usage entry in the transcript:
input_tokens + cache_read + cache_creation. Fail-open: 0 on any error.
"""
import json


def context_tokens(transcript: str) -> int:
    try:
        with open(transcript, "rb") as f:
            tail = f.read()[-200_000:].decode("utf-8", "replace").splitlines()
        for line in reversed(tail):
            if '"usage"' not in line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            usage = (entry.get("message") or {}).get("usage") or {}
            if "input_tokens" in usage:
                return (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                )
    except Exception:
        pass
    return 0
