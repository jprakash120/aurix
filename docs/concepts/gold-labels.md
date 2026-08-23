# Gold labels

**Agreed-correct verdicts for a FIXED set of responses.**

Used to score annotators — human or model — against a reference.

## The critical limitation

Gold labels attach to **specific response texts**, not to prompts.

Reruns generate new texts. Scoring fresh generations against old gold
labels compares different things.

## Where this went wrong

Variant B was scored 5/8 partly because it produced **better** responses
than the ones gold covered. Gold said FAIL, B correctly refused to
fabricate, and the refusal counted as a mismatch.

The improvement was scored as an error.

## The rule

| Use | Valid? |
|---|---|
| Scoring annotators on a fixed response set | Yes |
| Scoring new generations from a changed prompt | **No** |
| Comparing two prompts | No — use [[violation-rate]] |

Related: [[self-consistency]] · [[06-i-was-worse]]
