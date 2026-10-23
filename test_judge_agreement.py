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
    rows = J.run([f], FakeJudge("PASS"), "other", sleep=0, log=lambda *_: None)
    s = J.summarize(rows)
    assert s["confusion"] == {"both_FAIL": 0, "both_PASS": 1, "A_FAIL_B_PASS": 2, "A_PASS_B_FAIL": 0}
    d = list(s["per_condition"].values())[0]
    assert d["a_fail"] == 2 and d["b_fail"] == 0


def test_aborts_on_judge_error(tmp_path):
    f = _file(tmp_path, ["FAIL", "PASS"])
    boom = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: (_ for _ in ()).throw(RuntimeError("429")))))
    with pytest.raises(E.RegradeAborted):
        J.run([f], boom, "other", sleep=0, log=lambda *_: None)


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


def test_wait_parsing():
    assert J._wait_seconds("Rate limit reached ... try again in 12.5s.") == 12.5
    assert J._wait_seconds("try again in 1m3.2s") == 63.2
    assert J._wait_seconds("Request too large") is None


def test_retries_rate_limit_then_succeeds():
    calls = {"n": 0}
    ok = FakeJudge("PASS").chat.completions.create

    def create(**kw):
        calls["n"] += 1
        assert kw.get("max_tokens") == J.MAX_TOKENS
        if calls["n"] <= 2:
            raise RuntimeError("Error code: 429 - Rate limit reached ... try again in 3s")
        return ok(**kw)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    waits = []
    v = J._judge_with_retry(client, {"rule": "8.2", "input": "x"}, "y", "q",
                            sleep_fn=waits.append, log=lambda *_: None)
    assert v[0] == "PASS" and waits == [4, 4]


def test_request_too_large_shrinks_budget_then_skips_one_reply():
    budgets = []

    def create(**kw):
        budgets.append(kw["max_tokens"])
        raise RuntimeError("Error code: 429 - Request too large for model")
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    v = J._judge_with_retry(client, {"rule": "8.2", "input": "x"}, "y", "q",
                            sleep_fn=lambda s: None, log=lambda *_: None)
    assert v == ("TOO_LARGE", "") and budgets == [2048, 1024, 512]


def test_request_too_large_succeeds_with_smaller_budget():
    ok = FakeJudge("FAIL").chat.completions.create

    def create(**kw):
        if kw["max_tokens"] > 1024:
            raise RuntimeError("Error code: 429 - Request too large for model")
        return ok(**kw)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    v = J._judge_with_retry(client, {"rule": "8.2", "input": "x"}, "y", "q",
                            sleep_fn=lambda s: None, log=lambda *_: None)
    assert v[0] == "FAIL"


def test_other_errors_still_abort():
    def create(**kw):
        raise RuntimeError("Error code: 500 - server error")
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(RuntimeError):
        J._judge_with_retry(client, {"rule": "8.2", "input": "x"}, "y", "q",
                            sleep_fn=lambda s: None, log=lambda *_: None)
