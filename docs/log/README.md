# Build log

One entry per session. Newest first.

Format: what I did, what I found, what surprised me.

---

## 2026-08-23

Moved off Gemini (20 req/day) to Groq gpt-oss-120b. Built `rate_test.py`
to measure [[violation-rate]] at n samples instead of single verdicts.

n=5 both variants. Mean 0.30 vs 0.25 — **not a result**, every delta was
exactly one sample. But two real findings: the 8.3 cases are coin flips
(0.40, 0.60) and e82-01 fails 10/10 across both variants.

Started n=20 run.

Surprise: model list on Groq had no Llama 3.3 — the hardcoded model
would have failed. Checking the live list first saved a wasted run.

---

## 2026-08-10

A/B test. Predicted A=6/8, B=8/8. Got A=7/8, B=5/8. **Hypothesis
falsified** — but partly a scoring bug: [[gold-labels]] only valid for
fixed response sets, and B was penalized for producing better responses.

---

## 2026-08-09

Three labeling rounds. [[self-consistency]] 50%. Judge beat me 7/8 to
6/8. Wrote a decision procedure, then pattern-matched it instead of
executing it. Published writeup 02.

---

## 2026-08-02

Found the filename bug. Split core from runner, 22 tests. Wrote SPEC.md.
Added local-before-model router, 45 tests. Pushed to GitHub.
