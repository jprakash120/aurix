# Build log

One entry per session. Newest first.

Format: what I did, what I found, what surprised me.

---

## 2026-10-08 (catch-up entry)

Project dormant ~6 weeks. Recording what happened before the gap.

**Optimizer, Aug 24-25.** Two iterations, both REVERT.

Iteration 1 hit a bug in my own gate: MIN_VALID was hardcoded to 15
while running n=10, so every case failed the sample check regardless of
data. Fixed by scaling the threshold to 75% of n. Fourth instance of
measurement code reporting a conclusion it had no basis for.

Iteration 2 was the real result. Proposal: "respond that you cannot
determine the user mood confidently and express uncertainty."
e83-02 went 0.80 -> 0.00. e83-01 went 0.70 -> 0.20, unasked.
Rule 8.3 solved outright. REVERTED because e82-03 moved 0.20 -> 0.50.

At n=10 that regression is 2 samples becoming 5 - inside the noise band
already measured for these cases. The regression threshold (0.15) is
tighter than the measurement precision. The guard may have rejected a
genuinely good change.

**Vision, undated.** Built `vision_test.py`: OpenCV webcam capture ->
Gemini with a model fallback chain -> spoken description. Stage 4 of
[[track-2-robot]], $0, no hardware.

Surprise on reading it back: the vision prompt contains "do not invent
objects that are not visible", "do not claim to know how a person
feels", "if something is uncertain, say it appears to be". That is
[[rule-4.1-honesty]] and [[rule-8.2-dont-narrate]] applied to a new
modality, written from memory without the spec open.

First evidence the spec generalizes beyond the script it was written
for. Needs to become SPEC section 9.

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

