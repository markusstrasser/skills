"""Grader and verdict checks for blind_read.py (the grader is the verifier; it must be exact)."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("blind_read", Path(__file__).with_name("blind_read.py"))
assert _spec and _spec.loader
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def test_grade_number_tolerance_and_formats():
    q = {"kind": "number", "answer": 129.4, "tol": 1.5}
    assert br.grade(q, 129) == "ok"
    assert br.grade(q, "$129.0") == "ok"
    assert br.grade(q, 131) == "wrong"
    assert br.grade(q, None) == "null"
    assert br.grade(q, True) == "wrong"


def test_grade_range_order_and_bad_values():
    q = {"kind": "range", "answer": [120.1, 156.1], "tol": 1.5}
    assert br.grade(q, [156, 120]) == "ok"
    assert br.grade(q, [120, "n/a"]) == "wrong"
    assert br.grade(q, 120) == "wrong"


def test_grade_choice_case_insensitive():
    q = {"kind": "choice", "options": ["yes", "no"], "answer": "no"}
    assert br.grade(q, " No ") == "ok"
    assert br.grade(q, "yes") == "wrong"


def test_open_questions_asked_first_alone_and_ungraded(monkeypatch):
    calls = []

    def fake_run(arm, qs, base, model):
        calls.append([q["id"] for q in qs])
        ans = {q["id"]: ("a sentence" if q["kind"] == "open" else 3) for q in qs}
        return {"raw": __import__("json").dumps(ans), "in_tok": 10, "out_tok": 2}

    monkeypatch.setattr(br, "run_reader", fake_run)
    qs = [{"id": "q1", "kind": "number", "answer": 3}, {"id": "q0", "kind": "open", "q": "main point?"}]
    res = br.read_arm({}, qs, Path("."), "sonnet")
    assert calls == [["q0"], ["q1"]]
    assert res["answers"] == {"q0": "a sentence", "q1": 3} and res["in_tok"] == 20
    assert br.grade(qs[1], "anything") == "open"


def test_parse_answers_tolerates_wrapping_text():
    assert br.parse_answers('Here:\n```json\n{"q1": 3}\n```') == {"q1": 3}
    assert br.parse_answers("no json") is None


def _rows(item, grades_by_arm):
    return [{"item": item, "arm": arm, "rep": 0, "grades": g} for arm, g in grades_by_arm.items()]


def test_verdict_prose_carries_claim_chart_adds_lookup():
    it = {"id": "m", "arms": {"full": {}, "prose": {}},
          "questions": [{"id": "q1", "role": "claim"}, {"id": "q2", "role": "lookup"}]}
    rows = _rows("m", {"full": {"q1": "ok", "q2": "ok"}, "prose": {"q1": "ok", "q2": "null"}})
    assert "only if readers need" in br.verdict(it, rows)


def test_verdict_sentence_will_do():
    it = {"id": "m", "arms": {"full": {}, "prose": {}}, "questions": [{"id": "q1", "role": "claim"}]}
    rows = _rows("m", {"full": {"q1": "ok"}, "prose": {"q1": "ok"}})
    assert "a sentence will do" in br.verdict(it, rows)


def test_verdict_flags_trap_the_figure_fails():
    it = {"id": "m", "arms": {"full": {}, "prose": {}},
          "questions": [{"id": "q1", "role": "claim"}, {"id": "q2", "role": "trap"}]}
    rows = _rows("m", {"full": {"q1": "ok", "q2": "wrong"}, "prose": {"q1": "ok", "q2": "ok"}})
    assert "[MISLEADS]" in br.verdict(it, rows)
    rows = _rows("m", {"full": {"q1": "ok", "q2": "ok"}, "prose": {"q1": "ok", "q2": "ok"}})
    assert "[MISLEADS]" not in br.verdict(it, rows)


def test_verdict_chart_carries_claim():
    it = {"id": "m", "arms": {"full": {}, "prose": {}}, "questions": [{"id": "q1", "role": "claim"}]}
    rows = _rows("m", {"full": {"q1": "ok"}, "prose": {"q1": "null"}})
    assert "keep it" in br.verdict(it, rows)
