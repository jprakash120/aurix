# Violation rate

**How often a case breaks a rule, out of n tries.**

    FAIL/FAIL/FAIL/PASS/PASS  →  3/5  →  0.60

Replaces a single PASS/FAIL verdict, which cannot describe a random
system.

## Reading rates

| Rate | Meaning |
|---|---|
| 0.00 | Reliably correct |
| 0.20 | Occasional failure — at n=5 this is ONE sample |
| 0.40–0.60 | Coin flip. Unstable behavior. |
| 1.00 | Deterministic failure. Strongest signal. |

## The trap

At n=5, every possible rate is a multiple of 0.20. A difference of 0.20
between two variants is **one sample**, not a result.

This is why the first A/B comparison was meaningless — see
[[07-its-a-coin-flip]].

## Why rates beat verdicts

A verdict assigned to one response is a fact about that response.
A rate is a fact about the **prompt**. Only the second is what you want
when comparing prompts.

Related: [[n-samples]] · [[gold-labels]]
