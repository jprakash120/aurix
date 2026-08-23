# LLM as judge

**Using a model to grade another model's output against a written rule.**

Needed because most behavior rules have no exact expected answer.
See [[04-testing-the-untestable]].

## Shape

    RULE: {rule text}
    User said: {input}
    Assistant replied: {response}

    1. evidence   — quote the exact span, verbatim
    2. rule_says  — restate what the rule requires here
    3. verdict    — PASS or FAIL

## The evidence-first requirement

Without it, judges form an impression and reason toward it. Measured
failure: a judge passed "Query not recognized. Please rephrase." against
a rule forbidding exactly that, and gave a reason contradicting the text.

Quoting first forces the verdict to attach to a specific span.
See [[05-the-judge-was-wrong]].

## Known limits

- **PASS bias** on borderline cases
- **Same-model risk** — judge and system under test being the same model
  may favor familiar output. Untested here.
- Measured accuracy: 7/8 vs [[gold-labels]]. Not perfect. Better than
  the human labeler — see [[06-i-was-worse]].

## Rule to remember

A judge you have not measured is not a measurement.

Related: [[contamination]] · [[self-consistency]]
