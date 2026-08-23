# Finding: conditional rules break consistency

**Rules with embedded exceptions are where both humans and models
become unstable.**

## Two independent lines of evidence

**Human.** Across three labeling rounds, both persistent errors landed
on [[rule-8.3-answer-when-asked]] — the only conditional rule in the
set. See [[06-i-was-worse]].

**Model.** At n=5, the two 8.3 cases had violation rates of 0.40 and
0.60. Coin flips. The 8.2 and 8.6 cases were mostly 0.00 or 1.00.
See [[07-its-a-coin-flip]].

## Why

| Rule type | Question to answer |
|---|---|
| Prohibition (8.2, 8.6) | Did it do the forbidden thing? Yes/no. |
| Conditional (8.3) | Is the claim *warranted*? Requires judging evidence. |

Prohibitions are pattern matching. Conditionals require evaluating
whether a statement rests on evidence that exists.

## Implication for spec design

Rules with exceptions need explicit decision procedures — numbered
steps with a required citation of which step fired. Without that,
annotators pattern-match the shape instead of executing the logic.

## Not yet established

- Does this hold for other conditional rules, or is 8.3 just badly
  worded?
- Would a second human labeler show the same clustering?
