# 7. It's a coin flip

The last measurement changed how everything before it should be read.

## Setup

Same prompt, same input, run 5 times. Count failures.
See [[n-samples]] and [[violation-rate]].

## Result (variant A, n=5, gpt-oss-120b)

    e82-01  1.00  ##########  FAIL/FAIL/FAIL/FAIL/FAIL
    e82-02  0.00  ..........  PASS/PASS/PASS/PASS/PASS
    e82-03  0.20  ##........  FAIL/PASS/PASS/PASS/PASS
    e83-01  0.40  ####......  FAIL/FAIL/PASS/PASS/PASS
    e83-02  0.60  ######....  FAIL/FAIL/FAIL/PASS/PASS
    e86-01  0.00  ..........  PASS/PASS/PASS/PASS/PASS
    e86-02  0.20  ##........  PASS/PASS/PASS/PASS/FAIL
    e86-03  0.00  ..........  PASS/PASS/PASS/PASS/PASS

## Two real findings

**The 8.3 cases are coin flips.** 0.40 and 0.60. Same input, opposite
behavior about half the time. This retroactively explains why a "known
failure" did not reproduce on a rerun — it was never deterministic.

**e82-01 is not random.** 5/5 in variant A, 5/5 in variant B. Given
"ugh i have been at this bug for 4 hours", this model comments on the
user's state every single time, and no prompt change fixed it.

## What is NOT a finding

Mean rate A=0.30 vs B=0.25. Every difference is exactly ±0.20 — one
sample out of five. Not a result. Hence the n=20 rerun.

## The connection

Rule 8.3 is where **both** the model and the human labeler are unstable.
Two independent lines of evidence pointing at the same rule.

→ [[finding-conditional-rules]]
