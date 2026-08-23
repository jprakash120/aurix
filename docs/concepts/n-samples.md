# n (number of samples)

**n = how many times you ask the same question.**

## Why it exists

These models are random. `temperature=1.0` means the model samples from
a probability distribution instead of always picking the most likely
next word. Same input, different output.

So asking once tells you almost nothing. It is one coin flip.

## What one n costs

Each n is **two API calls**:

    CALL 1  send prompt + user input   → response
    CALL 2  send response + rule       → PASS or FAIL

## The loop

    for each case (8):
        for i in 1..n:
            ask
            judge
            record PASS/FAIL
        rate = FAILs / n

The question never changes between iterations. Only the model's
randomness does.

## Cost table

| n | calls/case | 8 cases |
|---|---|---|
| 1 | 2 | 16 |
| 5 | 10 | 80 |
| 20 | 40 | 320 |

## How to pick n

- **n=1** — smoke test only. Does the pipeline run? Never for data.
- **n=5** — see whether a case is stable or unstable. Cannot compare variants.
- **n=20** — a rate you can start to defend.

Related: [[violation-rate]] · [[07-its-a-coin-flip]]
