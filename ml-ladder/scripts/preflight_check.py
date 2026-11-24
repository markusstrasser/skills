#!/usr/bin/env python3
"""Check an ml-ladder preflight block.

Exit 0: every row is filled, holds a passing value and names a file that exists. Without
        --arm-score or a pass_bar it says the trivial policies were not compared.
Exit 1: a row is missing, empty, or names a file that does not exist; the positive control scored
        zero; a seed replay differed; two distinguishable states gave the same input; train and
        held-out share a group; or the score came from another regime than the deployed one.
Exit 2: the rows are complete, but a trivial policy reaches the arm's score or the pass bar, so
        the panel cannot show skill.

Scores are "k/n" strings (wins out of fights, correct out of items). Artifact paths are relative
to the preflight file.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROWS = {
    "positive_control": ("what", "score", "artifact"),
    "reachable": ("policy_that_passes", "key_event_chance", "artifact"),
    "smallest": ("sub_skills", "task", "result", "artifact"),
    "replay": ("same_seed_identical", "same_code_pair", "artifact"),
    "held_out": ("split_unit", "shared_groups", "prior_use", "artifact"),
    "inputs": ("states_differ", "zero_variance_columns", "artifact"),
    "regime": ("scored_in", "matches_deployment", "artifact"),
    "watched": ("saw", "artifact"),
}
TRIVIAL_FIELDS = ("policy", "score", "artifact")

TEMPLATE = {
    "question": "what this run is meant to show, in one sentence",
    "panel": "the opponents, seeds and split every arm and trivial policy is scored on",
    "pass_bar": "k/n a result must reach to be reported as a pass, or null",
    "positive_control": {"what": "", "score": "k/n", "artifact": ""},
    "trivial": [
        {"policy": "constant", "score": "k/n", "artifact": ""},
        {"policy": "blind", "score": "k/n", "artifact": ""},
        {"policy": "random", "score": "k/n", "artifact": ""},
    ],
    "reachable": {"policy_that_passes": "", "key_event_chance": "", "artifact": ""},
    "smallest": {"sub_skills": [], "task": "", "result": "", "artifact": ""},
    "replay": {
        "same_seed_identical": None,
        "same_code_pair": "k/n vs k/n",
        "artifact": "",
    },
    "held_out": {
        "split_unit": "",
        "shared_groups": None,
        "prior_use": "",
        "artifact": "",
    },
    "inputs": {"states_differ": None, "zero_variance_columns": [], "artifact": ""},
    "regime": {
        "scored_in": "the pipeline, state length and inputs the score came from",
        "matches_deployment": None,
        "artifact": "",
    },
    "watched": {"saw": "", "artifact": ""},
}


def parse_score(text: object) -> tuple[int, int]:
    """Read "k/n"; raise ValueError on anything else."""
    if not isinstance(text, str) or "/" not in text:
        raise ValueError(f"score {text!r} is not k/n")
    k, n = text.replace(" ", "").split("/", 1)
    wins, total = int(k), int(n)
    if total <= 0 or not 0 <= wins <= total:
        raise ValueError(f"score {text!r} is not a count out of a positive total")
    return wins, total


def within_noise(arm: tuple[int, int], other: tuple[int, int]) -> bool:
    """True when the arm's rate is less than two standard errors above the other's."""
    p1, p2 = arm[0] / arm[1], other[0] / other[1]
    se = math.sqrt(p1 * (1 - p1) / arm[1] + p2 * (1 - p2) / other[1])
    return p1 - p2 < 2 * se or p1 <= p2


def empty(value: object) -> bool:
    return value is None or value == "" or value == "k/n"


def check(
    block: dict, base: Path, arm_score: str | None
) -> tuple[list[str], list[str], int]:
    """Return (problems, trivial_matches, number of scores the trivial policies were compared with)."""
    problems: list[str] = []
    for key in ("question", "panel"):
        if empty(block.get(key)) or block.get(key) == TEMPLATE[key]:
            problems.append(f"{key}: not filled")

    def need_file(row: str, path: object) -> None:
        if empty(path):
            problems.append(f"{row}: no artifact named")
        elif not (base / str(path)).exists():
            problems.append(f"{row}: artifact {path} does not exist")

    for row, fields in ROWS.items():
        entry = block.get(row)
        if not isinstance(entry, dict):
            problems.append(f"{row}: row missing")
            continue
        for field in fields:
            if field not in entry or (
                field != "zero_variance_columns" and empty(entry[field])
            ):
                problems.append(f"{row}.{field}: not filled")
        need_file(row, entry.get("artifact"))

    for row, field, want, meaning in (
        (
            "replay",
            "same_seed_identical",
            True,
            "one seed replayed must give the same trajectory",
        ),
        (
            "inputs",
            "states_differ",
            True,
            "two states a player tells apart must give different inputs",
        ),
        (
            "held_out",
            "shared_groups",
            0,
            "train and held-out must share no source group",
        ),
        (
            "regime",
            "matches_deployment",
            True,
            "score in the pipeline the model will run in",
        ),
    ):
        entry = block.get(row)
        if isinstance(entry, dict) and not empty(entry.get(field)):
            value = entry[field]
            if type(value) is not type(want) or value != want:
                problems.append(f"{row}.{field} is {value!r}: {meaning}")

    control = block.get("positive_control", {})
    if isinstance(control, dict) and not empty(control.get("score")):
        try:
            if parse_score(control["score"])[0] == 0:
                problems.append(
                    "positive_control: scored zero, so a zero elsewhere reads the harness"
                )
        except ValueError as err:
            problems.append(f"positive_control: {err}")

    trivial = block.get("trivial")
    scored: list[tuple[str, tuple[int, int]]] = []
    if not isinstance(trivial, list) or not trivial:
        problems.append("trivial: no trivial policy scored")
    else:
        for i, entry in enumerate(trivial):
            name = entry.get("policy", f"#{i}") if isinstance(entry, dict) else f"#{i}"
            if not isinstance(entry, dict) or any(
                empty(entry.get(f)) for f in TRIVIAL_FIELDS
            ):
                problems.append(f"trivial[{name}]: not filled")
                continue
            need_file(f"trivial[{name}]", entry["artifact"])
            try:
                scored.append((name, parse_score(entry["score"])))
            except ValueError as err:
                problems.append(f"trivial[{name}]: {err}")

    matches: list[str] = []
    bars: list[tuple[str, tuple[int, int]]] = []
    for label, text in (
        ("the arm", arm_score),
        ("the pass bar", block.get("pass_bar")),
    ):
        if empty(text):
            continue
        try:
            bars.append((label, parse_score(text)))
        except ValueError as err:
            problems.append(f"{label}: {err}")
    for name, score in scored:
        for label, bar in bars:
            if within_noise(bar, score):
                matches.append(
                    f"trivial policy '{name}' at {score[0]}/{score[1]} reaches {label} "
                    f"at {bar[0]}/{bar[1]}: the panel cannot show skill; change the task, "
                    "panel or opponent"
                )
    return problems, matches, len(bars)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("preflight", nargs="?", type=Path, help="preflight.json")
    parser.add_argument("--arm-score", help="the trained arm's k/n on the same panel")
    parser.add_argument("--template", action="store_true", help="print an empty block")
    args = parser.parse_args(argv)
    if args.template:
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if args.preflight is None:
        parser.error("name the preflight file, or pass --template")
    block = json.loads(args.preflight.read_text())
    problems, matches, compared = check(
        block, args.preflight.resolve().parent, args.arm_score
    )
    for line in problems:
        print(f"✗ {line}")
    for line in matches:
        print(f"! {line}")
    if problems:
        return 1
    if matches:
        return 2
    if not compared:
        print("✓ rows complete")
        print("! trivial policies NOT compared: pass --arm-score k/n or set pass_bar")
        return 0
    print(
        f"✓ preflight complete: {len(block['trivial'])} trivial policies below the arm or the bar"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
