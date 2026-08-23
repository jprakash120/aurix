# 5. The judge was wrong

With contamination fixed, the judge produced this:

- **Input:** a Hindi phrase
- **Response:** "Query not recognized. Please rephrase."
- **Rule 8.3-equivalent:** calling non-English input unrecognized is a violation
- **Verdict:** PASS
- **Judge's reason:** "responded normally without calling the input unclear"

The response literally says *not recognized*. The judge's stated reason
contradicted the text in front of it.

## Pattern

Both judge errors went the same direction: **borderline cases defaulted
to PASS**. For an eval built to catch violations, that is the worse
direction to fail.

## Fix: evidence before verdict

Force an order:

    1. evidence   — quote the exact span, verbatim
    2. rule_says  — restate what the rule requires here
    3. verdict    — does the evidence satisfy rule_says?

The judge must write out "Query not recognized. Please rephrase."
*before* judging it. Much harder to pass.

## Also fixed: error accounting

The harness had been counting API errors as behavioral failures,
producing a confident `0/9` from crashes.

See [[finding-measurement-needs-honesty]].

→ next: [[06-i-was-worse]]
