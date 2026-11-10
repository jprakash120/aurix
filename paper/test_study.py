"""Offline tests for the displacement study - no API calls."""
import json
from types import SimpleNamespace

import pytest

import analyze as A
import derive_lists as D
import run_study as R
import stimuli as S


# ---------------------------------------------------------------- stimuli

def test_sixty_unique_inputs_per_behavior():
    for b, v in S.BEHAVIORS.items():
        assert len(v["inputs"]) == 60 and len(set(v["inputs"])) == 60, b


def test_sympathy_inputs_state_no_feeling():
    """Any feeling a reply names must be one the user did not state."""
    for t in S.BEHAVIORS["sympathy"]["inputs"]:
        assert not any(w in t.lower() for w in S.FEELING_WORDS), t


LISTS = {"sympathy": {"m1": {"say": ["Oh no.", "That's rough."], "match": ["oh no", "that's rough"]}},
         "apology": {"m1": {"say": ["My apologies."], "match": ["my apologies"]}}}


def test_list_condition_uses_the_models_own_derived_phrases():
    p = S.system_prompt("sympathy", "list", "m1", LISTS)
    assert p.endswith('Do not say: "Oh no." "That\'s rough."')
    assert S.listed_for("apology", "m1", LISTS) == ["my apologies"]


def test_list_condition_refuses_without_a_derived_list():
    with pytest.raises(KeyError):
        S.system_prompt("sympathy", "list", "unknown-model", LISTS)


def test_emphasis_list_is_fixed_bold():
    assert "bold" in S.system_prompt("emphasis", "list", "any", {})
    assert S.listed_for("emphasis", "any", {}) == ["**"]


def test_none_condition_is_the_bare_base_prompt():
    for b in S.BEHAVIORS:
        assert S.system_prompt(b, "none", "m1", LISTS) == S.BASE_SYSTEM
        for c in ("principle", "positive"):
            assert S.system_prompt(b, c, "m1", LISTS).startswith(S.BASE_SYSTEM + "\n\n")


def test_calibration_inputs_are_separate_and_state_no_feeling():
    for b, inputs in S.CALIBRATION.items():
        assert len(inputs) == 20 and len(set(inputs)) == 20
        assert not set(inputs) & set(S.BEHAVIORS[b]["inputs"]), b
    for t in S.CALIBRATION["sympathy"]:
        assert not any(w in t.lower() for w in S.FEELING_WORDS), t


def test_closer_was_replaced_by_emphasis():
    assert list(S.BEHAVIORS) == ["sympathy", "apology", "emphasis"]
    assert S.STIMULI_VERSION == 2


# ---------------------------------------------------------------- plan

def test_plan_size_and_rotation():
    jobs = R.plan()
    assert len(jobs) == 3 * 4 * 60 * len(R.DEFAULT_MODELS)
    # for one (behavior, input, model) the four conditions are adjacent
    b0 = [j for j in jobs if j["behavior"] == "sympathy" and j["idx"] == 1
          and j["model"] == "openai/gpt-oss-120b"]
    assert [j["condition"] for j in b0] == list(S.CONDITIONS[1:] + S.CONDITIONS[:1])


def test_plan_interleaves_behaviors():
    first = [j["behavior"] for j in R.plan(n_inputs=1)[:3]]
    assert first == list(S.BEHAVIORS)


# ---------------------------------------------------------------- generate / judge

def fake_client(text="What's the bug?", fail=False, finish="stop"):
    def create(**kw):
        if fail:
            raise RuntimeError("Error code: 429 - Rate limit reached")
        msg = SimpleNamespace(content=text)
        return SimpleNamespace(model=kw["model"],
                               choices=[SimpleNamespace(message=msg, finish_reason=finish)])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _lists(models):
    return {b: {m: {"say": ["X."], "match": ["x"]} for m in models} for b in S.CALIBRATION}


NOSLEEP = dict(log=lambda *_: None, sleep=0, sleep_fn=lambda s: None)


def test_generate_is_resumable_and_capped(tmp_path):
    f = str(tmp_path / "g.jsonl")
    jobs = R.plan(n_inputs=1, models=["m1"])
    L = _lists(["m1"])
    assert R.run_generate(jobs, 5, lambda m: fake_client(), gen_file=f, lists=L, **NOSLEEP) == 5
    assert len(R.read_jsonl(f)) == 5
    R.run_generate(jobs, 100, lambda m: fake_client(), gen_file=f, lists=L, **NOSLEEP)
    rows = R.read_jsonl(f)
    assert len(rows) == len(jobs) == 12
    assert len({R.key(r["behavior"], r["condition"], r["idx"], r["model"]) for r in rows}) == 12
    # the exact system prompt is saved with every reply
    lst = [r for r in rows if r["condition"] == "list" and r["behavior"] == "sympathy"][0]
    assert lst["system"].endswith('Do not say: "X."')


def test_rate_limited_model_is_skipped_others_continue(tmp_path):
    f = str(tmp_path / "g.jsonl")
    jobs = R.plan(n_inputs=1, models=["bad", "good"])
    R.run_generate(jobs, 100, lambda m: fake_client(fail=(m == "bad")), gen_file=f,
                   lists=_lists(["bad", "good"]), **NOSLEEP)
    rows = R.read_jsonl(f)
    assert {r["model"] for r in rows} == {"good"} and len(rows) == 12


def test_rate_limit_is_waited_out_then_succeeds():
    calls, waits = {"n": 0}, []

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("Error code: 429 - Please retry in 7.5s.")
        return "ok"
    assert R.call_with_retry(fn, sleep_fn=waits.append, log=lambda *_: None) == "ok"
    assert waits == [8.5, 8.5]


def test_wait_seconds_groq_and_gemini_forms():
    assert R.wait_seconds("Rate limit reached. Please try again in 1m3.2s.") == 63.2
    assert R.wait_seconds("Resource exhausted. Please retry in 12.5s.") == 12.5
    assert R.wait_seconds("{'retryDelay': '30s'}") == 30.0
    assert R.wait_seconds("server error") is None


def test_missing_lists_and_calibration_plan():
    assert len(R.missing_lists(["m1"], {})) == 2           # sympathy, apology
    assert R.missing_lists(["m1"], _lists(["m1"])) == []
    cal = R.calibration_plan(["m1", "m2"])
    assert len(cal) == 2 * 20 * 2 and {j["condition"] for j in cal} == {"none"}


def test_think_block_is_stripped():
    assert R.strip_think("<think>hmm {x}</think>\n Answer.") == "Answer."


def test_parse_verdict():
    assert R.parse_verdict('ok {"verdict":"violation","evidence":"e"}')[0] == "VIOLATION"
    assert R.parse_verdict('{"verdict":"OK"}')[0] == "OK"
    assert R.parse_verdict("no json")[0] == "ERROR"
    assert R.parse_verdict('{"verdict":"PASS"}')[0] == "ERROR"


def test_judge_skips_truncated_and_resumes(tmp_path):
    g, j = str(tmp_path / "g.jsonl"), str(tmp_path / "j.jsonl")
    jobs = R.plan(n_inputs=1, models=["m1"])
    R.run_generate(jobs, 100, lambda m: fake_client(), gen_file=g, lists=_lists(["m1"]), **NOSLEEP)
    rows = R.read_jsonl(g)
    rows[0]["finish_reason"] = "length"
    with open(g, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(r) for r in rows) + "\n")
    judge = fake_client('{"user_said":"u","evidence":"e","verdict":"OK"}')
    R.run_judge("J", 4, judge, log=lambda *_: None, sleep=0, gen_file=g, out_file=j)
    R.run_judge("J", 100, judge, log=lambda *_: None, sleep=0, gen_file=g, out_file=j)
    assert len(R.read_jsonl(j)) == 11


# ---------------------------------------------------------------- analysis

def test_listed_match_handles_curly_apostrophes():
    L = {"sympathy": {"m1": {"say": ["I'm sorry you're dealing with this."],
                             "match": ["i'm sorry you're"]}}}
    assert A.has_listed("sympathy", "I\u2019m sorry you\u2019re dealing with this. Try X.", "m1", L)
    assert not A.has_listed("sympathy", "Four hours on a bug can be draining.", "m1", L)
    assert A.has_listed("emphasis", "It is **Ottawa**.", "any", {})


# ---------------------------------------------------------------- derive

def test_first_clause():
    assert D.first_clause("I\u2019m sorry about that mistake\u2014Sydney is a city") == "i'm sorry about that mistake"
    assert D.first_clause("My apologies for that error. Canberra is") == "my apologies for that error"
    assert D.first_clause("Ugh, that's incredibly frustrating!") == "ugh, that's incredibly frustrating"
    assert D.first_clause("Ugh, that's incredibly frustrating, especially when it's the same step") \
        == "ugh, that's incredibly frustrating"
    assert D.first_clause("My apologies for the mix\u2011up") == "my apologies for the mix-up"


def test_derive_groups_by_form_and_fills_from_pooled():
    gens, js = [], []
    data = {"m1": ["I'm sorry about that mistake.", "I'm sorry about the earlier error.",
                   "I'm sorry for the confusion.", "And I apologize for the error."],
            "m2": []}
    for m in data:
        for i in range(4):
            gens.append({"behavior": "apology", "condition": "none", "idx": i, "model": m, "reply": "r"})
            ev = data[m][i] if i < len(data[m]) else ""
            js.append({"key": R.key("apology", "none", i, m),
                       "verdict": "VIOLATION" if ev else "OK", "evidence": ev})
    lists, report = D.derive(gens, js, models=["m1", "m2"])
    m1 = lists["apology"]["m1"]
    # "i'm sorry about" (2) ranks first; leading "and" is stripped
    assert m1["match"] == ["i'm sorry about", "i apologize for", "i'm sorry for"]
    assert m1["say"][0] == "I'm sorry about that mistake." and m1["n_violations"] == 4
    m2 = lists["apology"]["m2"]        # no own violations: pooled forms
    assert m2["from_pooled"] == 3 and m2["match"] == m1["match"]


def test_daily_limits_are_not_retried():
    def fn():
        raise RuntimeError("Error code: 429 - Rate limit reached ... tokens per day (TPD). "
                           "Please try again in 7m12.5s.")
    with pytest.raises(R.LimitForToday):
        R.call_with_retry(fn, sleep_fn=lambda s: None, log=lambda *_: None)

    def gem():
        raise RuntimeError("Error code: 429 - You exceeded your current quota")
    with pytest.raises(R.LimitForToday):
        R.call_with_retry(gem, sleep_fn=lambda s: None, log=lambda *_: None)


def test_request_too_large_retries_with_smaller_budget():
    seen = []

    def fn(b):
        seen.append(b)
        if b > 2048:
            raise RuntimeError("Error code: 429 - Request too large for model")
        return "ok"
    assert R.with_smaller_budgets(fn, log=lambda *_: None) == "ok" and seen == [4096, 2048]


def test_daily_limit_skips_model_for_the_session(tmp_path):
    f = str(tmp_path / "g.jsonl")

    def client(m):
        def create(**kw):
            if m == "bad":
                raise RuntimeError("Error code: 429 - You exceeded your current quota")
            return fake_client().chat.completions.create(**kw)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    jobs = R.plan(n_inputs=1, models=["bad", "good"])
    R.run_generate(jobs, 100, client, gen_file=f, lists=_lists(["bad", "good"]), **NOSLEEP)
    assert {r["model"] for r in R.read_jsonl(f)} == {"good"}


def test_non_forms_are_excluded_from_lists():
    gens = [{"behavior": "apology", "condition": "none", "idx": i, "model": "m1", "reply": "r"}
            for i in range(3)]
    evs = ["You are absolutely right.", "I apologize for the error.", "I apologize for the error."]
    js = [{"key": R.key("apology", "none", i, "m1"), "verdict": "VIOLATION", "evidence": e}
          for i, e in enumerate(evs)]
    lists, _ = D.derive(gens, js, models=["m1"])
    assert lists["apology"]["m1"]["match"] == ["i apologize for"]
    assert D.derive.excluded[("apology", "m1")]["you are absolutely right"] == 1


def test_default_models_leave_out_gemini():
    assert "gemini-2.5-flash" not in R.DEFAULT_MODELS and "gemini-2.5-flash" in R.MODELS
    assert {j["model"] for j in R.plan(n_inputs=1)} == set(R.DEFAULT_MODELS)
