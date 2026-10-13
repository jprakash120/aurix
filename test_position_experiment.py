"""Offline tests for position_experiment.py - no API calls."""

import aurix_prompting
import position_experiment as X
import v13_eval as E
from test_v13_eval import FakeJudge, P


def _cells():
    return {c["name"]: c for c in X.build_plan()[0]["conditions"]}


def test_cell_b_uses_production_normal_directive():
    b = _cells()["B:sysS+dirD"]
    case = next(c for c in E.CASES if c["id"] == "e82-01")
    conds, _ = E.conditions_for(case)
    prod = next(c for c in conds if c["name"] == "v13:normal")
    assert b["user"] == prod["user"]


def test_cells_use_the_6922_system_prompt_without_d():
    """Production gained D in the system prompt after the 2x2 ran.
    The experiment must still reproduce the prompt it was run with."""
    a = _cells()["A:sysS"]["system"]
    assert X.S in a and X.D not in a
    assert a != aurix_prompting.SYSTEM_PROMPT


def test_each_cell_differs_from_a_in_exactly_one_place():
    c = _cells()
    a = c["A:sysS"]
    # C: same system, different directive
    assert c["C:sysS+dirS"]["system"] == a["system"] and c["C:sysS+dirS"]["user"] != a["user"]
    # D: same directive, different system
    assert c["D:sysD"]["user"] == a["user"] and c["D:sysD"]["system"] != a["system"]


def test_wordings_land_where_the_cell_says():
    c = _cells()
    assert X.S in c["C:sysS+dirS"]["user"] and X.D not in c["C:sysS+dirS"]["user"]
    assert X.D in c["D:sysD"]["system"] and X.S not in c["D:sysD"]["system"]
    assert X.S not in c["A:sysS"]["user"] and X.D not in c["A:sysS"]["user"]
    assert "Avoid unnecessary padding." in c["A:sysS"]["user"]


def test_production_prompt_is_not_modified():
    before = aurix_prompting.SYSTEM_PROMPT
    X.build_plan()
    assert aurix_prompting.SYSTEM_PROMPT is before


def test_base_system_is_the_6922_prompt_byte_for_byte():
    import hashlib
    assert hashlib.sha256(X.BASE_SYSTEM.encode("utf-8")).hexdigest()[:16] == X.SYSTEM_6922_SHA


def test_runs_end_to_end_with_fakes():
    class AI:
        def ask_text(self, system, user, temperature):
            from types import SimpleNamespace
            return SimpleNamespace(text="What's the bug?", model=P)
    out = E.run(X.build_plan(), 2, AI(), FakeJudge("PASS"), P, sleep=0, log=lambda *_: None)
    assert set(out["e82-01"]["conditions"]) == {n for n, _, _ in X.CELLS}


def test_cells_filter():
    names = [c["name"] for c in X.build_plan({"B"})[0]["conditions"]]
    assert names == ["B:sysS+dirD"]


def test_new_production_system_prompt_is_cell_d():
    """Production (2026-10-12) = cell D's system prompt, measured 0.30 and
    0.15 in two sessions. Only normal's directive differs (D vs old pad)."""
    assert _cells()["D:sysD"]["system"] == aurix_prompting.SYSTEM_PROMPT
