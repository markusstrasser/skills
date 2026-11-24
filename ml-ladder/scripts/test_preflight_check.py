"""preflight_check: a complete block passes, a hole fails, a trivial policy at the arm's score stops."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "preflight_check", Path(__file__).with_name("preflight_check.py")
)
pc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pc)


def block(tmp_path: Path, trivial: str = "9/640") -> Path:
    (tmp_path / "a.txt").write_text("x")
    data = {
        "question": "does the trained caster beat the panel",
        "panel": "three frozen opponents, roots 200800-200815, both seats",
        "pass_bar": None,
        "positive_control": {
            "what": "script vs passive",
            "score": "16/16",
            "artifact": "a.txt",
        },
        "trivial": [
            {"policy": "stand and fire", "score": trivial, "artifact": "a.txt"}
        ],
        "reachable": {
            "policy_that_passes": "script",
            "key_event_chance": "0.3",
            "artifact": "a.txt",
        },
        "smallest": {
            "sub_skills": ["hold still"],
            "task": "one cast",
            "result": "32/32",
            "artifact": "a.txt",
        },
        "replay": {
            "same_seed_identical": True,
            "same_code_pair": "31/64 vs 34/64",
            "artifact": "a.txt",
        },
        "held_out": {
            "split_unit": "opening root",
            "shared_groups": 0,
            "prior_use": "none",
            "artifact": "a.txt",
        },
        "regime": {
            "scored_in": "native host, full duel",
            "matches_deployment": True,
            "artifact": "a.txt",
        },
        "inputs": {
            "states_differ": True,
            "zero_variance_columns": [],
            "artifact": "a.txt",
        },
        "watched": {
            "saw": "195 casts started, 0 finished, all broken by own movement",
            "artifact": "a.txt",
        },
    }
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(data))
    return path


def test_complete_block_passes(tmp_path):
    assert pc.main([str(block(tmp_path)), "--arm-score", "500/640"]) == 0


def test_trivial_policy_at_the_arm_score_stops(tmp_path, capsys):
    # arena 2026-11-24: weight search 626/640, standing still and pressing Heavy 624/640
    assert pc.main([str(block(tmp_path, "624/640")), "--arm-score", "626/640"]) == 2
    assert "cannot show skill" in capsys.readouterr().out


def test_trivial_policy_at_the_pass_bar_stops(tmp_path):
    path = block(tmp_path, "39/39")
    data = json.loads(path.read_text())
    data["pass_bar"] = "39/39"
    path.write_text(json.dumps(data))
    assert pc.main([str(path)]) == 2


def test_missing_row_and_missing_artifact_fail(tmp_path, capsys):
    path = block(tmp_path)
    data = json.loads(path.read_text())
    del data["watched"]
    data["smallest"]["artifact"] = "gone.txt"
    path.write_text(json.dumps(data))
    assert pc.main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "watched: row missing" in out and "gone.txt does not exist" in out


def test_positive_control_at_zero_fails(tmp_path, capsys):
    path = block(tmp_path)
    data = json.loads(path.read_text())
    data["positive_control"]["score"] = "0/16"
    path.write_text(json.dumps(data))
    assert pc.main([str(path)]) == 1
    assert "reads the harness" in capsys.readouterr().out


def test_unfilled_template_fails(tmp_path):
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(pc.TEMPLATE))
    assert pc.main([str(path)]) == 1


@pytest.mark.parametrize(
    ("row", "field", "bad", "said"),
    [
        ("replay", "same_seed_identical", False, "same trajectory"),
        ("inputs", "states_differ", False, "different inputs"),
        ("held_out", "shared_groups", 5, "share no source group"),
        ("regime", "matches_deployment", False, "pipeline the model will run in"),
    ],
)
def test_failing_values_fail(tmp_path, capsys, row, field, bad, said):
    path = block(tmp_path)
    data = json.loads(path.read_text())
    data[row][field] = bad
    path.write_text(json.dumps(data))
    assert pc.main([str(path), "--arm-score", "500/640"]) == 1
    assert said in capsys.readouterr().out


def test_no_arm_score_and_no_bar_says_nothing_was_compared(tmp_path, capsys):
    assert pc.main([str(block(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "NOT compared" in out and "below the arm" not in out
