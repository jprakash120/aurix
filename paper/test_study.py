"""Offline tests for the displacement study - no API calls."""
import json
from types import SimpleNamespace

import pytest

import analyze as A
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


def test_listed_phrases_are_the_ones_the_list_condition_names():
    for b, v in S.BEHAVIORS.items():
        text = A.norm(v["conditions"]["list"])
        for p in v["listed"]:
            assert p in text, (b, p)


def test_none_condition_is_the_bare_base_prompt():
    for b in S.BEHAVIORS:
        assert S.system_prompt(b, "none") == S.BASE_SYSTEM
        for c in S.CONDITIONS[1:]:
            assert S.system_prompt(b, c).startswith(S.BASE_SYSTEM + "\n\n")


def test_principle_and_positive_do_not_name_listed_phrases():
    """Otherwise 'displaced' would be confounded with 'listed'."""
    for b, v in S.BEHAVIORS.items():
        for c in ("principle", "positive"):
            t = A.norm(v["conditions"][c])
            assert not any(p in t for p in v["listed"]), (b, c)


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


def test_generate_is_resumable_and_capped(tmp_path):
    f = str(tmp_path / "g.jsonl")
    jobs = R.plan(n_inputs=1, models=["m1"])
    assert R.run_generate(jobs, 5, lambda m: fake_client(), log=lambda *_: None,
                          sleep=0, gen_file=f) == 5
    assert len(R.read_jsonl(f)) == 5
    R.run_generate(jobs, 100, lambda m: fake_client(), log=lambda *_: None, sleep=0, gen_file=f)
    rows = R.read_jsonl(f)
    assert len(rows) == len(jobs) == 12
    assert len({R.key(r["behavior"], r["condition"], r["idx"], r["model"]) for r in rows}) == 12


def test_rate_limited_model_is_skipped_others_continue(tmp_path):
    f = str(tmp_path / "g.jsonl")
    jobs = R.plan(n_inputs=1, models=["bad", "good"])
    R.run_generate(jobs, 100, lambda m: fake_client(fail=(m == "bad")),
                   log=lambda *_: None, sleep=0, gen_file=f)
    rows = R.read_jsonl(f)
    assert {r["model"] for r in rows} == {"good"} and len(rows) == 12


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
    R.run_generate(jobs, 100, lambda m: fake_client(), log=lambda *_: None, sleep=0, gen_file=g)
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
    assert A.has_listed("sympathy", "I’m sorry you’re dealing with this. Try X.")
    assert not A.has_listed("sympathy", "Four hours on a bug can be draining.")


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
