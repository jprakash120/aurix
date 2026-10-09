"""
Spec rule 8.5 guards - each test isolates ONE guard in eligible_actions().

Found 2026-10-08 by mutation testing: all five guards could be deleted
and the original 11 tests still passed. The single "no silence" test
used input that tripped two guards at once, so each covered for the
other. Every input below is chosen so exactly one guard is responsible.
"""

from aurix_learning import eligible_actions, extract_signals


def allowed(text):
    return eligible_actions(extract_signals(text))


def test_inputs_isolate_one_guard_each():
    """Guard the test inputs themselves - if signal extraction changes,
    these must fail loudly instead of silently testing nothing."""
    s = extract_signals("why?")
    assert s["low_information"] and s["direct_request"] and not s["problem_language"]
    s = extract_signals("bug again")
    assert s["low_information"] and s["problem_language"] and not s["direct_request"]
    s = extract_signals("full code")
    assert s["low_information"] and s["detail_request"] and not s["direct_request"]
    s = extract_signals("i was thinking about lunch today")
    assert not any(s[k] for k in ("low_information", "direct_request",
                                  "problem_language", "detail_request"))


def test_8_5_short_direct_question_never_silent():
    """'why?' is low-information, so only the direct_request guard blocks silence."""
    assert "silence" not in allowed("why?")


def test_8_5_short_problem_report_never_silent():
    """'bug again' is low-information and not a question - only problem_language blocks silence."""
    assert "silence" not in allowed("bug again")


def test_8_5_short_detail_request_never_silent():
    """'full code' - only detail_request blocks silence."""
    assert "silence" not in allowed("full code")


def test_detail_request_excludes_brief_direct():
    """Asking for full code must not get a brief answer."""
    assert "brief_direct" not in allowed("full code")


def test_8_5_silence_only_for_low_information():
    """A real sentence with no request still must not get silence."""
    assert "silence" not in allowed("i was thinking about lunch today")


def test_never_empty():
    for t in ("", "why?", "full code", "ugh", "explain everything in detail"):
        assert allowed(t), t
