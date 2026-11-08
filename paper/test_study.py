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
    assert len(jobs) == 3 * 4 * 60 * len(R.MODELS)
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


def test_derive_uses_own_phrases_and_fills_from_pooled():
    gens, js = [], []
    data = {"m1": ["My apologies for the error.", "My apologies for the error.", "I apologize."],
            "m2": []}
    for m, evs in data.items():
        for i in range(3):
            g = {"behavior": "apology", "condition": "none", "idx": i, "model": m, "reply": "r"}
            gens.append(g)
            ev = evs[i] if i < len(evs) else ""
            js.append({"key": R.key("apology", "none", i, m),
                       "verdict": "VIOLATION" if ev else "OK", "evidence": ev})
    lists, report = D.derive(gens, js, models=["m1", "m2"])
    m1 = lists["apology"]["m1"]
    assert m1["say"] == ["My apologies for the error.", "I apologize."] and m1["from_pooled"] == 0
    assert m1["n_violations"] == 3 and "my apologies for" in m1["match"]
    m2 = lists["apology"]["m2"]        # no own violations: pooled list
    assert m2["n_violations"] == 0 and m2["from_pooled"] == 2


def test_fisher_known_value():
    assert abs(A.fisher_two_sided(3, 1, 1, 3) - 0.4857) < 1e-3
    assert A.fisher_two_sided(5, 5, 5, 5) == 1.0


def test_wilson_bounds():
    lo, hi = A.wilson(0, 20)
    assert lo == 0.0 and 0.1 < hi < 0.2


def test_displaced_counts_only_unlisted_violations():
    rows = [{"verdict": "VIOLATION", "listed": True}, {"verdict": "VIOLATION", "listed": False},
            {"verdict": "OK", "listed": False}, {"verdict": "OK", "listed": True}]
    c = A.cell(rows)
    assert c["violations"] == 2 and c["displaced"] == 1 and c["displaced_share"] == 0.5
