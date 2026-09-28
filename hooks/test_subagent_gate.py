"""Discipline checks of pretool-subagent-gate.sh (checks 7, 10, self-report).

2026-09-21 retune, immigration-research: seven dispatches of the form "first read
<lane>/BRIEF.md and follow it exactly" each drew "missing file-output instruction" and
"no turn-budget note" although the brief carried both; "do not write any file" was read as a
file-output instruction; and the turn-budget note fired on 71 of 101 replayed dispatches.
"""

import glob
import json
import os
import subprocess
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parent / "pretool-subagent-gate.sh"

BRIEF = """# Paper-reading brief
Budget: at most 12 turns and 8 searches.
Write your notes to notes/<slug>.md. Your first tool call is a Write of a stub at that path;
then append findings as you confirm them.
The first line of the notes file is your exact model ID.
"""


@pytest.fixture(autouse=True)
def own_gate_state():
    yield
    for path in glob.glob(f"/tmp/claude-*-{os.getpid()}"):
        os.unlink(path)


def gate(prompt, stype="researcher", description="Read one paper", cwd=None):
    envelope = {"tool_name": "Agent", "session_id": "s",
                "tool_input": {"description": description, "subagent_type": stype,
                               "prompt": prompt, "model": "opus"}}
    env = dict(os.environ, HOOK_TRIGGER_LOG=os.devnull,
               SUBAGENT_MEMORY_BLOCK_MB="0", SUBAGENT_MEMORY_WARN_MB="0")
    proc = subprocess.run(["bash", str(GATE)], input=json.dumps(envelope), capture_output=True,
                          text=True, env=env, cwd=cwd)
    if proc.returncode == 2:
        pytest.skip(f"machine-state block, not under test: {proc.stdout[:80]}")
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return "", ""
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    injected = out.get("updatedInput", {}).get("prompt", prompt)[len(prompt):]
    return out.get("additionalContext", ""), injected


def test_a_delegated_brief_counts_as_part_of_the_prompt(tmp_path):
    (tmp_path / "BRIEF.md").write_text(BRIEF)
    prompt = f"First read {tmp_path}/BRIEF.md and follow it exactly.\n\nPAPER: Butcher, Moran, Watson (2021)."
    advisory, injected = gate(prompt)
    assert "SUBAGENT OUTPUT" not in advisory and "TURN-BUDGET" not in advisory
    assert "WRITE-FIRST" not in advisory and "MODEL SELF-REPORT" not in injected


def test_the_same_prompt_without_the_brief_on_disk_still_draws_the_advisories(tmp_path):
    prompt = f"First read {tmp_path}/BRIEF.md and follow it exactly.\n\nPAPER: Butcher, Moran, Watson (2021)."
    advisory, injected = gate(prompt)
    assert "SUBAGENT OUTPUT" in advisory and "TURN-BUDGET" in advisory
    assert "MODEL SELF-REPORT" in injected


def test_a_brief_stops_a_second_output_path_being_injected(tmp_path):
    (tmp_path / "lane-brief.md").write_text(BRIEF)
    prompt = (f"Follow {tmp_path}/lane-brief.md. " + "Tabulate the ACS direct-care workforce by birthplace. " * 5)
    assert len(prompt) > 200
    _, injected = gate(prompt, stype="general-purpose", description="Tabulate care workforce")
    assert "OUTPUT DISCIPLINE" not in injected
    _, injected = gate(prompt.replace("lane-brief.md", "missing-brief.md"), stype="general-purpose",
                       description="Tabulate care workforce")
    assert "OUTPUT DISCIPLINE" in injected


def test_a_relative_brief_path_resolves_against_the_session_directory(tmp_path):
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra" / "BRIEF.md").write_text(BRIEF)
    advisory, _ = gate("First read infra/BRIEF.md and follow it exactly. PAPER: GGM 2026.", cwd=str(tmp_path))
    assert "SUBAGENT OUTPUT" not in advisory


def test_an_ordinary_memo_is_not_a_brief(tmp_path):
    (tmp_path / "findings.md").write_text(BRIEF)
    advisory, _ = gate(f"Audit {tmp_path}/findings.md for unsupported numbers.")
    assert "SUBAGENT OUTPUT" in advisory


@pytest.mark.parametrize("prompt", [
    "Probe, 2 turns maximum. Run one Bash command. Do not write any file; the parent reads a log.",
    "Probe, 2 turns maximum. Make one Read call. No result file needed.",
])
def test_an_explicit_no_file_opt_out_is_respected(prompt):
    advisory, _ = gate(prompt, stype="Explore", description="Probe hook envelope")
    assert "SUBAGENT OUTPUT" not in advisory and "WRITE-FIRST" not in advisory


def test_a_negation_does_not_hide_a_real_output_instruction():
    advisory, _ = gate("12 turns. Do not write files in the repo. Write your results to the file /tmp/x/notes.md.")
    assert "WRITE-FIRST" in advisory and "SUBAGENT OUTPUT" not in advisory


def test_turn_budget_note_is_for_research_shaped_dispatches_only():
    lane = "Run infra/lane/build.py, compare derived/out.csv with the pinned copy, write results to RESULT.md."
    assert "TURN-BUDGET" not in gate(lane, stype="general-purpose", description="Rebuild ledger lane")[0]
    assert "TURN-BUDGET" not in gate(lane, stype="opus-low", description="Rebuild ledger lane")[0]
    research = "Find the primary estimates on nursing-home entry. Write notes to the file /tmp/x/notes.md."
    assert "TURN-BUDGET" in gate(research)[0]
    assert "TURN-BUDGET" not in gate("Budget 12 turns. " + research)[0]
    assert "TURN-BUDGET" in gate("Survey the literature on Tiebout sorting; write a memo file.",
                                 stype="general-purpose", description="Tiebout evidence")[0]


def test_a_refused_report_basename_is_named(tmp_path):
    # 2026-09-28 anki: summary_NN.md in the brief → the harness refused 14 of 15 result writes.
    brief = tmp_path / "BRIEF.md"
    brief.write_text("Write FC/claude/out_NN.jsonl, then write FC/claude/summary_NN.md with the verdict.\n")
    context, _ = gate(f"Read {brief} and follow it; write your results to the files it names.",
                      stype="general-purpose", description="Fact-check batch")
    assert "BLOCKED FILENAME: 'summary_NN.md'" in context


def test_an_ordinary_result_name_is_not_flagged(tmp_path):
    context, _ = gate("Write your result to out/result_01.md, first line **Verdict:**, then reply with its path.",
                      stype="general-purpose", description="Fact-check batch")
    assert "BLOCKED FILENAME" not in context
