# Build log

One entry per session. Newest first.

Format: what I did, what I found, what surprised me.

---

## 2026-10-09 (evening) - "That sounds frustrating" and rubric v3

e82-01 baseline ("ugh i have been at this bug for 4 hours"), all
behaviors, n=5: v0.9.1 1.00, normal 1.00, clarify 1.00, detailed 1.00,
brief_direct 0.00. Almost every failing reply opened with "That sounds
frustrating." The prompt's forbidden examples are all second-person
("You sound stressed"); the model's violation is the impersonal form.
brief_direct is the only directive that says "avoid unnecessary
reassurance" - and the only behavior at 0.

Before touching behavior, fixed the instrument. Some `detailed` FAILs
were restatements of the user's own fact ("you've been stuck on this
for a while"), not feelings. SPEC 8.2 amended; judge rubric v3 names the
impersonal forms and says restating a stated fact is not a violation.

Predictions before regrading the saved replies: "That sounds
frustrating" replies stay FAIL; fact-only restatements flip to PASS;
brief_direct stays 0.00. Behavior fix (SYSTEM_PROMPT) comes after,
measured against the regraded baseline.

---

## 2026-10-09 (later) - regrade confirmed; clarify was the real problem

Regraded the 49 saved replies with rubric v2. Wrote four predictions
first. All four held: question-back-only replies stayed FAIL (5/5);
all 16 flips were "can't tell from text alone" moving FAIL -> PASS;
brief_direct on e83-01 went 0.80 -> 0.00; clarify on e83-02 stayed 0.80.
Zero flips PASS -> FAIL, so v2 got more specific, not just more lenient.

Caveat I owe myself: v2 was written after reading these replies. The
defense is that "can't tell is an answer" was in the labeling guide in
August, and question-backs still fail. The real test is fresh replies.

So the "v1.3 is worse than v0.9.1" headline was the judge. The only
genuine 8.3 problem: the clarify directive ("Do not guess the user's
intent. Ask one clarifying question") fires on clear questions and
answers "what mood am I in?" with "how are you feeling?".

Changed the directive to answer first, ask after, never a question
alone. Did NOT ban clarify for direct questions - "just tell me how to
fix it" is a direct request where asking *what* to fix is right.

Also caught: the eval's prompt fingerprint hashed only SYSTEM_PROMPT,
so a directive change would have left before/after runs with the same
label. Now it hashes the directives too. Added --behaviors to measure
one behavior across all 8 cases (160 calls instead of 400).

---

## 2026-10-09 - first v1.3 measurement, and the judge was the problem again

Built `aurix_prompting.py` so the runner and eval import one prompt -
the old harnesses kept a copy that went stale. Built `v13_eval.py`:
the real v1.3 pipeline, every behavior the bandit may pick, same model
and temperature (0.4) as production.

First run, rule 8.3, n=5. Headline looked like v1.3 was worse than
v0.9.1 (mean 0.47 vs 0.20; brief_direct 4/5 fail, clarify 5/5).

I predicted a mechanism before reading the replies: brief_direct drops
the uncertainty, clarify asks a question instead of answering. Read the
replies. **Half wrong.** clarify really does answer "what mood am I in?"
with "Could you tell me how you're feeling?" - deflection. But the
brief_direct "failures" were "I can't assess tone from text alone, so I
don't have evidence to determine that" - an honest answer. A near-
identical sentence under `normal` was graded PASS.

Sorted every verdict by what the reply did: question-back-only failed
5/5 (correct, consistent); "can't tell from text alone" failed 10/33
(same kind of reply, flipping). The 8.3 rule text never said whether
admitting insufficient evidence counts as answering. The labeling guide
had decided it did; the spec and the judge rubric had not.

Fourth time 8.3 - the only conditional rule - broke consistency: human
labels, model behavior, n=20 rates, now grading. Amended SPEC 8.3 and
the judge rubric (v2). Added `--regrade`: re-judges the SAVED replies
with the new rubric, so any change is the judge, not the model.

Surprise: the regrade tests caught `regrade()` mutating the original
results in memory - a shallow copy. Fixed with deepcopy before it ran
for real.

---

## 2026-10-08 (evening) - two silent failures in the test suite

**Mutation testing on rule 8.5.** v1.2 moved "silence is a valid
response" out of the prompt and into `eligible_actions()` - five guards
that remove silence for direct requests, problem reports, detail
requests and non-trivial input. 11 tests covered the module.

Deleted each guard in turn. All five deletions left the suite green.
The only "no silence" test used "why is my code failing?" - not
low-information AND a direct question, so two guards removed silence for
it and each covered for the other. Problem-language and detail guards
were never reached at all.

Added `test_eligibility_guards.py`: one input per guard, chosen so
exactly one guard is responsible ("why?", "bug again", "full code"),
plus a test that asserts the inputs still trip the signals they're meant
to - so a change in signal extraction fails loudly instead of quietly
testing nothing. Now 5 of 5 deletions are caught, each by one named test.

**pytest was running the webcam.** Default collection includes
`*_test.py`, which matched `vision_test.py`, `voice_test.py`,
`ab_test.py`, `rate_test.py`. `vision_test.py` has top-level code:
importing it opened the camera, called Gemini and spoke. Every test run
spent API quota. That's why the suite took 46-77s. Added `pytest.ini`
restricting collection to `test_*.py`. Suite: 77 passed in under a
second.

Surprise: both problems were invisible because the suite was green.
Fifth instance of a passing number that didn't mean what it looked like
- first one in unit tests rather than evals. See
[[finding-measurement-needs-honesty]].

SPEC 8.10 rewritten from "no rule has a test" to a per-rule enforcement
table. Also recorded that all judge-measured rates describe the v0.9.1
prompt, which v1.3 no longer runs.

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

