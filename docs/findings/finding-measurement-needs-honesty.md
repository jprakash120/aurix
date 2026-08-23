# Finding: measurement code needs its own honesty rules

**The eval harness violated the rule it was built to enforce.**

## What happened

[[rule-4.1-honesty]] forbids producing plausible output when you cannot
determine an answer.

The harness hit a rate limit partway through a run and printed:

    REAL SCORE: 0/9
    SPEC SCORE: 0/9
    gap        : 0 cases

Every API error had been counted as a behavioral failure. The gap
analysis — the entire point of the two-mode design — was computed from
crashes.

## Second instance

The labeling tool reported "All labeled" when zero responses existed.
Technically true (0 of 0). Practically a false success message, and it
would have sent the next phase into an empty dataset.

## Fixes

- Count errors separately from verdicts
- Refuse to print a score if any case errored
- Never report success on an empty set

## The general point

Code that measures behavior is code that can be wrong about behavior.
Apply the same standard to the instrument as to the thing measured.

Related: [[05-the-judge-was-wrong]]
