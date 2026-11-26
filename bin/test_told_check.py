"""told-check must count only assistant text the operator could read, at or after --since."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

loader = importlib.machinery.SourceFileLoader("told_check", str(Path(__file__).with_name("told-check")))
spec = importlib.util.spec_from_loader("told_check", loader)
told_check = importlib.util.module_from_spec(spec)
loader.exec_module(told_check)

SINCE = "2026-11-26T07:40:00Z"


def write_transcript(tmp_path, records):
    path = tmp_path / "session.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records) + "not json\n")
    return path


def assistant(stamp, *blocks):
    return {"type": "assistant", "timestamp": stamp, "message": {"content": list(blocks)}}


def test_text_after_since_counts(tmp_path, capsys):
    path = write_transcript(
        tmp_path, [assistant("2026-11-26T07:42:50.974Z", {"type": "text", "text": "Correction first. Pass 2 ran."})]
    )
    assert told_check.main(["--transcript", str(path), "--since", SINCE, "Correction first", "Pass 2"]) == 0
    assert "2026-11-26T07:42:50.974Z" in capsys.readouterr().out


def test_unsaid_needle_is_not_told(tmp_path):
    path = write_transcript(tmp_path, [assistant("2026-11-26T07:42:50Z", {"type": "text", "text": "Correction first."})])
    assert told_check.main(["--transcript", str(path), "--since", SINCE, "Correction first", "never said"]) == 1


def test_thinking_tool_use_user_and_earlier_text_never_count(tmp_path):
    needle = "told him"
    path = write_transcript(
        tmp_path,
        [
            assistant("2026-11-26T07:30:00Z", {"type": "text", "text": needle}),
            assistant("2026-11-26T07:45:00Z", {"type": "thinking", "thinking": needle}),
            assistant("2026-11-26T07:46:00Z", {"type": "tool_use", "input": {"code": needle}}),
            {"type": "user", "timestamp": "2026-11-26T07:47:00Z", "message": {"content": needle}},
        ],
    )
    assert told_check.main(["--transcript", str(path), "--since", SINCE, needle]) == 1


def test_local_time_and_missing_transcript_refuse(tmp_path):
    path = write_transcript(tmp_path, [])
    assert told_check.main(["--transcript", str(path), "--since", "15:07", "x"]) == 2
    assert told_check.main(["--transcript", str(path), "--since", "2026-11-26T07:40:00", "x"]) == 2
    assert told_check.main(["--transcript", str(tmp_path / "absent.jsonl"), "--since", SINCE, "x"]) == 2
