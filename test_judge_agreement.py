"""Offline tests for judge_agreement.py."""
import json
from types import SimpleNamespace

import pytest

import judge_agreement as J
import v13_eval as E
from test_v13_eval import FakeJudge, P


def test_kappa_perfect_and_chance():
    assert J.kappa([("PASS", "PASS"), ("FAIL", "FAIL")]) == 1.0
    # A always FAIL, B alternates: agreement 0.5, expected 0.5 -> kappa 0
    assert abs(J.kappa([("FAIL", "FAIL"), ("FAIL", "PASS")] * 5)) < 1e-9


def test_only_primary_graded_samples_are_regraded():
    res = {"primary_model": P, "cases": {"e82-01": {"rule": "8.2", "input": "x", "conditions": {
        "c": {"samples": [{"verdict": "FAIL", "model": P, "response": "a"},
                          {"verdict": "SKIPPED", "model": "small", "response": "b"},
                          {"verdict": "ERROR", "model": None}]}}}}}
    assert len(list(J.gradeable(res))) == 1


def _file(tmp_path, verdicts):
    res = {"primary_model": P, "cases": {"e82-01": {"rule": "8.2", "input": "x", "conditions": {
        "A:sysS": {"samples": [{"verdict": v, "model": P, "response": "r%d" % i}
                               for i, v in enumerate(verdicts)]}}}}}
    f = tmp_path / "r.json"
    f.write_text(json.dumps(res), encoding="utf-8")
    return str(f)


def test_summary_counts_disagreement_direction(tmp_path):
    f = _file(tmp_path, ["FAIL", "FAIL", "PASS"])
    rows = J.run([f], FakeJudge("PASS"), "other", sleep=0)
    s = J.summarize(rows)
    assert s["confusion"] == {"both_FAIL": 0, "both_PASS": 1, "A_FAIL_B_PASS": 2, "A_PASS_B_FAIL": 0}
    d = list(s["per_condition"].values())[0]
    assert d["a_fail"] == 2 and d["b_fail"] == 0


def test_aborts_on_judge_error(tmp_path):
    f = _file(tmp_path, ["FAIL", "PASS"])
    boom = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: (_ for _ in ()).throw(RuntimeError("429")))))
    with pytest.raises(E.RegradeAborted):
        J.run([f], boom, "other", sleep=0)


def test_judge_uses_the_model_it_is_given():
    seen = {}
    msg = SimpleNamespace(content='{"evidence":"e","rule_says":"r","verdict":"PASS"}')

    def create(**kw):
        seen.update(kw)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    E.judge(client, {"rule": "8.2", "input": "x"}, "y", model="llama-x")
    assert seen["model"] == "llama-x"
    E.judge(client, {"rule": "8.2", "input": "x"}, "y")
    assert seen["model"] == E.JUDGE_MODEL


def test_judge_tolerates_prose_around_json():
    msg = SimpleNamespace(content='Here is my grade:\n{"evidence":"e","rule_says":"r","verdict":"FAIL"}\nDone.')
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=msg)]))))
    assert E.judge(client, {"rule": "8.2", "input": "x"}, "y")[0] == "FAIL"


def test_judge_skips_a_think_block_with_braces_in_it():
    msg = SimpleNamespace(content='<think>maybe {"verdict":"PASS"}? no.</think>\n{"evidence":"e","rule_says":"r","verdict":"FAIL"}')
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=msg)]))))
    assert E.judge(client, {"rule": "8.2", "input": "x"}, "y")[0] == "FAIL"
