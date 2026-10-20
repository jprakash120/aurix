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


# ---------------------------------------------------------------
# Rubric v2 and regrade
# ---------------------------------------------------------------

def test_8_3_rubric_says_insufficient_evidence_is_an_answer():
    r = E.RULE_TEXT["8.3"].lower()
    assert "insufficient" in r and "is an honest answer" in r
    assert "question back" in r and "deflection" in r


def _saved_results(verdicts, rubric_version=1):
    samples = [{"verdict": v, "model": P, "response": "reply %d" % i}
               for i, v in enumerate(verdicts)]
    cond = dict(E.score_condition(samples, len(samples), P), samples=samples)
    return {"n": len(samples), "primary_model": P, "rubric_version": rubric_version,
            "cases": {"e83-01": {"rule": "8.3", "input": "do i sound stressed to you?",
                                 "conditions": {"v13:normal": cond}}}}


def test_regrade_keeps_replies_and_records_old_verdicts():
    old = _saved_results(["FAIL", "FAIL", "PASS", "FAIL"])
    new, flips = E.regrade(old, FakeJudge("PASS"), sleep=0, log=lambda *_: None)
    samples = new["cases"]["e83-01"]["conditions"]["v13:normal"]["samples"]
    assert [s["response"] for s in samples] == ["reply 0", "reply 1", "reply 2", "reply 3"]
    assert [s["verdict_v1"] for s in samples] == ["FAIL", "FAIL", "PASS", "FAIL"]
    assert all(s["verdict"] == "PASS" for s in samples)
    assert len(flips) == 3
    assert new["rubric_version"] == E.RUBRIC_VERSION and new["regraded_from"] == 1
    assert new["cases"]["e83-01"]["conditions"]["v13:normal"]["rate"] == 0.0


def test_regrade_does_not_mutate_the_original():
    old = _saved_results(["FAIL"])
    E.regrade(old, FakeJudge("PASS"), sleep=0, log=lambda *_: None)
    assert old["cases"]["e83-01"]["conditions"]["v13:normal"]["samples"][0]["verdict"] == "FAIL"


def test_regrade_skips_errors_and_other_models():
    old = _saved_results(["PASS"])
    old["cases"]["e83-01"]["conditions"]["v13:normal"]["samples"] += [
        {"verdict": "ERROR", "model": None},
        {"verdict": "SKIPPED", "model": "openai/gpt-oss-20b", "response": "x"}]
    assert E.judge_calls_for_regrade(old) == 1


# ---------------------------------------------------------------
# clarify answers first; fingerprint covers directives; filter
# ---------------------------------------------------------------

def test_clarify_directive_answers_before_asking():
    d = E.policy_directive("clarify").lower()
    assert "answer it first" in d
    assert "never reply to a question with only a question" in d
    assert d.index("answer it first") < d.index("clarifying question")


def test_fingerprint_changes_when_a_directive_changes(monkeypatch):
    import aurix_learning
    before = E.prompt_fingerprint()
    original = aurix_learning.policy_directive
    monkeypatch.setattr(E, "policy_directive",
                        lambda a: original(a) + ("x" if a == "clarify" else ""))
    assert E.prompt_fingerprint() != before


def test_behaviors_filter():
    plan = E.build_plan({"e83-02"}, {"v091", "clarify"})
    assert [c["name"] for c in plan[0]["conditions"]] == ["v091", "v13:clarify"]
    assert E.call_count(plan, 5) == 2 * 5 * 2


def test_8_2_rubric_names_impersonal_forms_and_allows_restated_facts():
    r = E.RULE_TEXT["8.2"].lower()
    assert "that sounds frustrating" in r and "impersonal" in r
    assert "restating a fact the user stated" in r and "not a violation" in r


def test_rubric_version_is_3():
    assert E.RUBRIC_VERSION == 3


class RateLimitedJudge:
    """Judges the first `ok` calls, then raises like a Groq 429."""
    def __init__(self, ok):
        self.left = ok
        good = FakeJudge("PASS").chat.completions.create
        def create(**kw):
            if self.left <= 0:
                raise RuntimeError("Error code: 429 - Rate limit reached")
            self.left -= 1
            return good(**kw)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_regrade_aborts_on_judge_error_instead_of_saving_errors():
    """2026-10-09: a 429 mid-regrade turned 21 of 24 saved verdicts into
    ERROR, and the run reported 'Verdicts that changed: 0'."""
    import pytest
    old = _saved_results(["FAIL", "FAIL", "PASS", "FAIL"])
    with pytest.raises(E.RegradeAborted) as info:
        E.regrade(old, RateLimitedJudge(ok=2), sleep=0, log=lambda *_: None)
    assert info.value.done == 2 and info.value.total == 4
    assert "429" in info.value.reason
    # caller's saved verdicts untouched
    assert [x["verdict"] for x in old["cases"]["e83-01"]["conditions"]["v13:normal"]["samples"]] \
        == ["FAIL", "FAIL", "PASS", "FAIL"]


def test_system_prompt_forbids_impersonal_feeling_labels():
    """e82-01, 2026-10-09: 'That sounds frustrating' in normal/clarify/v091,
    0/5 only in brief_direct, whose directive says 'avoid unnecessary
    reassurance'. The prompt's examples were all second-person."""
    p = aurix_prompting.SYSTEM_PROMPT
    for phrase in ('"That sounds frustrating."', '"Sounds exhausting."',
                   "Avoid unnecessary reassurance or conversational padding."):
        assert phrase in p
    assert "Restating a fact the user gave" in p


def test_v091_control_prompt_is_frozen():
    """The v0.9.1 baseline is the control. A prompt fix must not touch it."""
    assert "That sounds frustrating" not in E.V091_PROMPT
    assert E.V091_PROMPT is not aurix_prompting.SYSTEM_PROMPT


def test_normal_directive_carries_brief_directs_anti_reassurance_line():
    """2026-10-10 experiment: the same idea in SYSTEM_PROMPT left normal at
    0.60 ('Four hours on a bug can be draining'); brief_direct, which has
    this exact line in its per-turn directive, stayed 0/5. Same words,
    different position."""
    line = "Avoid unnecessary reassurance or conversational padding."
    assert line in E.policy_directive("brief_direct")
    assert line in E.policy_directive("normal")


def test_case_without_v091_is_complete_and_reports():
    """--behaviors normal (no control) must not mark every case INVALID."""
    ok = {"rate": 0.0, "status": "OK"}
    summ = E.summarize_case({"v13:normal": ok})
    assert summ["complete"] and summ["v091"] is None
    results = {"n": 5, "prompt_fingerprint": "x", "primary_model": P,
               "cases": {"a": {"rule": "8.2", "summary": summ}}}
    lines = []
    out = E.report(results, log=lines.append)
    assert out is not None and out["v091"] is None
    assert any("n/a" in l for l in lines)


def test_measured_but_invalid_v091_still_blocks():
    ok = {"rate": 0.0, "status": "OK"}
    bad = {"rate": None, "status": "INVALID"}
    assert not E.summarize_case({"v091": bad, "v13:normal": ok})["complete"]


def test_system_prompt_has_d_and_not_s():
    """Two same-session 2x2s (2026-10-11, -12): every cell with S in the
    system prompt produced 'Four hours on a bug can be draining' (50/90);
    cells with D instead, never (0/30). S did not stop the sympathy
    opener - it reshaped it. Production keeps D and drops S."""
    p = aurix_prompting.SYSTEM_PROMPT
    s = "Do not open with sympathy or reassurance"
    d = "Avoid unnecessary reassurance or conversational padding."
    assert d in p and s not in p



def test_conditions_are_interleaved_not_blocked():
    """Drift during a run must hit every condition equally."""
    seen = []

    class AI:
        def ask_text(self, system, user, temperature):
            seen.append(user)
            return SimpleNamespace(text="ok", model=P)
    plan = E.build_plan({"e82-01"}, {"v091", "normal"})
    E.run(plan, 3, AI(), FakeJudge("PASS"), P, sleep=0, log=lambda *_: None)
    conds = plan[0]["conditions"]
    order = [next(c["name"] for c in conds if c["user"] == u) for u in seen]
    assert order == ["v091", "v13:normal"] * 3


def test_clarify_directive_carries_d():
    """2026-10-13, prompt 823c240d3c7e: clarify 4/20 on e82-01 ('Sounds
    like a tough spot', 'can be draining'); normal, with D in its
    directive, 1/20. clarify's directive did not have D."""
    d = "Avoid unnecessary reassurance or conversational padding."
    assert d in E.policy_directive("clarify")
    # answering-first instruction still comes first
    c = E.policy_directive("clarify")
    assert c.index("answer it first") < c.index(d)


def test_run_aborts_after_consecutive_fallbacks():
    """2026-10-13: a 429 turned 40 of 60 calls into excluded fallback
    samples, and the INVALID run was saved over good results."""
    import pytest

    class AI:
        def __init__(self):
            self.calls = 0

        def ask_text(self, system, user, temperature):
            self.calls += 1
            model = P if self.calls <= 4 else "openai/gpt-oss-20b"
            return SimpleNamespace(text="ok", model=model)
    ai = AI()
    with pytest.raises(E.RunAborted) as info:
        E.run(E.build_plan({"e82-01"}, {"normal"}), 20, ai, FakeJudge("PASS"), P,
              sleep=0, log=lambda *_: None)
    assert info.value.done == 7 and ai.calls == 7


def test_heldout_cases_are_selectable_but_not_in_default_run():
    default_ids = {p["case"]["id"] for p in E.build_plan()}
    held = {c["id"] for c in E.HELDOUT_CASES}
    assert not default_ids & held
    assert {p["case"]["id"] for p in E.build_plan(held)} == held


def test_case_ids_are_unique():
    ids = [c["id"] for c in E.ALL_CASES]
    assert len(ids) == len(set(ids))
