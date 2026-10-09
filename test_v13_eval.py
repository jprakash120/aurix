"""
Offline tests for v13_eval.py and the shared prompt module.

No API key needed. Fake model and judge clients stand in for Groq.
"""

import ast
import pathlib
from types import SimpleNamespace

import aurix_prompting
import v13_eval as E


# ---------------------------------------------------------------
# No more forked prompts
# ---------------------------------------------------------------

def test_runner_does_not_define_its_own_prompt():
    """aurix_v13.py must import SYSTEM_PROMPT, never redefine it.
    A local copy is how every eval harness in this repo went stale."""
    tree = ast.parse(pathlib.Path("aurix_v13.py").read_text(encoding="utf-8"))
    assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Name)}
    assert "SYSTEM_PROMPT" not in assigned
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom)
               and n.module == "aurix_prompting"]
    names = {a.name for n in imports for a in n.names}
    assert {"SYSTEM_PROMPT", "build_turn_prompt"} <= names


def test_eval_uses_the_shared_prompt_object():
    assert E.SYSTEM_PROMPT is aurix_prompting.SYSTEM_PROMPT


def test_turn_prompt_layout():
    p = aurix_prompting.build_turn_prompt("POLICY", "CHAT", "WORLD", "INPUT")
    order = [p.index(x) for x in ("INTERACTION POLICY", "POLICY", "RECENT CHAT HISTORY",
                                  "CHAT", "RECENT EPISODIC WORLD MEMORY", "WORLD",
                                  "CURRENT USER INPUT", "INPUT")]
    assert order == sorted(order)


# ---------------------------------------------------------------
# Plan
# ---------------------------------------------------------------

def test_plan_measures_every_allowed_behavior_plus_baseline():
    for p in E.build_plan():
        names = [c["name"] for c in p["conditions"]]
        assert names[0] == "v091"
        expected = ["v13:" + a for a in p["allowed"] if a != "silence"]
        assert names[1:] == expected


def test_v13_conditions_carry_the_policy_and_input():
    case = E.CASES[0]
    conds, _ = E.conditions_for(case)
    for c in conds[1:]:
        behavior = c["name"].split(":", 1)[1]
        assert c["system"] is aurix_prompting.SYSTEM_PROMPT
        assert E.policy_directive(behavior) in c["user"]
        assert case["input"] in c["user"]


def test_call_count():
    plan = E.build_plan({"e83-01"})
    assert E.call_count(plan, 5) == len(plan[0]["conditions"]) * 5 * 2


# ---------------------------------------------------------------
# Scoring guards
# ---------------------------------------------------------------

P = "primary"


def s(verdict, model=P):
    return {"verdict": verdict, "model": model}


def test_rate_counts_only_primary_model_verdicts():
    r = E.score_condition([s("FAIL"), s("PASS"), s("PASS"), s("PASS")], 4, P)
    assert r["rate"] == 0.25 and r["status"] == "OK"


def test_model_drift_is_excluded_not_averaged():
    """AurixAI falls back to smaller models on rate limits. Those samples
    must not be averaged into the primary model's rate."""
    r = E.score_condition([s("PASS"), s("PASS"), s("SKIPPED", "openai/gpt-oss-20b"),
                           s("SKIPPED", "gemini-x")], 4, P)
    assert r["valid"] == 2 and r["model_drift"] == 2
    assert r["status"] == "INVALID"


def test_errors_are_not_failures():
    r = E.score_condition([s("FAIL"), s("ERROR", None), s("ERROR", None), s("ERROR", None)], 4, P)
    assert r["errors"] == 3 and r["valid"] == 1 and r["status"] == "INVALID"


def test_judge_parse_error_counts_as_error():
    r = E.score_condition([s("PASS"), s("ERROR")], 2, P)
    assert r["errors"] == 1 and r["valid"] == 1


def test_valid_threshold_is_75_percent():
    assert E.score_condition([s("PASS")] * 8 + [s("ERROR", None)] * 2, 10, P)["status"] == "OK"
    assert E.score_condition([s("PASS")] * 7 + [s("ERROR", None)] * 3, 10, P)["status"] == "INVALID"


def test_summary_reports_mean_and_worst_behavior():
    ok = lambda r: {"rate": r, "status": "OK"}
    out = E.summarize_case({"v091": ok(0.6), "v13:normal": ok(0.2), "v13:clarify": ok(0.4)})
    assert out["complete"] and out["v091"] == 0.6
    assert abs(out["v13_mean"] - 0.3) < 1e-9
    assert out["v13_worst"] == 0.4 and out["worst_behavior"] == "clarify"


def test_one_invalid_behavior_makes_case_incomplete():
    ok = {"rate": 0.0, "status": "OK"}
    bad = {"rate": None, "status": "INVALID"}
    assert not E.summarize_case({"v091": ok, "v13:normal": ok, "v13:clarify": bad})["complete"]


def test_report_refuses_comparison_when_incomplete():
    results = {"n": 5, "prompt_fingerprint": "x", "primary_model": P, "cases": {
        "a": {"rule": "8.3", "summary": {"complete": False}},
        "b": {"rule": "8.3", "summary": {"complete": True, "v091": 0.4, "v13_mean": 0.1,
                                          "v13_worst": 0.2, "worst_behavior": "normal"}}}}
    lines = []
    assert E.report(results, log=lines.append) is None
    assert any("No overall comparison" in l for l in lines)


# ---------------------------------------------------------------
# End-to-end with fakes
# ---------------------------------------------------------------

class FakeAI:
    """Answers from the primary model, except it 'falls back' every 3rd call."""
    def __init__(self):
        self.calls = []

    def ask_text(self, system, user, temperature):
        self.calls.append((system, user, temperature))
        model = "openai/gpt-oss-20b" if len(self.calls) % 3 == 0 else P
        return SimpleNamespace(text="reply %d" % len(self.calls), model=model)


class FakeJudge:
    def __init__(self, verdict):
        content = '{"evidence":"reply","rule_says":"x","verdict":"%s"}' % verdict
        msg = SimpleNamespace(content=content)
        resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: resp))


def test_end_to_end_with_fakes_detects_drift_and_uses_production_settings():
    ai = FakeAI()
    plan = E.build_plan({"e86-01"})
    out = E.run(plan, 3, ai, FakeJudge("PASS"), P, sleep=0, log=lambda *_: None)
    conds = out["e86-01"]["conditions"]
    assert all(t == E.TEMPERATURE == 0.4 for _, _, t in ai.calls)
    assert any(c["model_drift"] > 0 for c in conds.values())
    assert all(c["valid"] + c["model_drift"] + c["errors"] == 3 for c in conds.values())
    # drift made every condition 2/3 valid, below the 75% gate
    assert not out["e86-01"]["summary"]["complete"]
