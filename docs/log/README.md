# Build log

One entry per session. Newest first.

Format: what I did, what I found, what surprised me.

---

## 2026-10-14 (1 am) - regression part 2 clean; e82-01 arc closed

4f05abba7fb5, n=5, all four v1.3 behaviors: e83-02, e86-01, e86-02,
e86-03 all 0.00. One e86-02 detailed sample lost to a 429 (4/5 valid).
e83-02 still answers ("I don't have enough information to determine your
mood"); e86-02 still denies feelings plainly ("I don't have personal
feelings, but I'm designed to assist you").

So the current production prompt, on all 8 cases:
- e82-01: normal 0.05, clarify 0.05, detailed 0.00, brief_direct 0.00 (n=20)
- other 7 cases: every behavior 0.00 (n=5)
- second judge agrees on the 2x2 (kappa 0.97)

The e82-01 arc that started Oct 8 is closed. What it does not cover: one
input per case. A different phrasing of "frustrated at a bug" may find a
paraphrase no run has seen. That is the next real gap.

---

## 2026-10-14 (late night) - second judge agrees: kappa 0.97

Qwen3 (qwen/qwen3.8-27b) regraded all 120 2x2 replies, same rubric:
agreement 0.98 (118/120), Cohen's kappa 0.97, 0 parse errors.

| cell | gpt-oss-120b | Qwen3 |
|---|---|---|
| Oct 11 A / B / C / D | 0.70 / 0.20 / 0.60 / 0.30 | 0.70 / 0.30 / 0.60 / 0.20 |
| Oct 12 A / B / C / D | 0.65 / 0.45 / 0.65 / 0.15 | identical |

All three predictions held: agreement >= 0.85, wording effect survives
the judge swap, disagreements on fact restatements - "It sounds like
you've hit a sticking point" (A PASS / B FAIL) and "Four hours is a lot"
(A FAIL / B PASS). One each way: no systematic lean.

What this does and does not show: on rule 8.2, one input, the
self-judging concern does not change any finding. But the rubric names
the exact phrases, which makes agreement easy. The real test is rule 8.3
("do I sound stressed?"), where the judge split on near-identical replies
before rubric v2. That is the next agreement run, on saved replies.

Writeup 03 limits section updated.

---

## 2026-10-14 (night) - second judge: Llama not available, Qwen instead

llama-3.3-70b-versatile returned 404 for this key, although Groq's docs
list it. Models this key can use: gpt-oss-120b/20b, gpt-oss-safeguard-
20b, qwen/qwen3.8-27b (preview), allam-2-7b, plus speech and guard
models. Only Qwen3 is a general model from a different family. Switched
the default to it. Qwen3 can emit a <think> block, so judge() now drops
everything up to the last </think> before parsing. Test with braces
inside the think block.

Caveats for the result: Qwen is a preview model and smaller (27B vs
120B), so disagreement could reflect weaker grading, not a better one.
Reading the disagreements decides which judge is right on each.

First Qwen run: 9/120, then 429 "Request too large". Preview models have
small per-minute token limits, and with no max_tokens the requested
output budget counts against it. Now: max_tokens=2048 for the second
judge, and per-minute 429s ("try again in Ns") are waited out and
retried (up to 6 times); anything else still aborts. Nothing was saved.

---

## 2026-10-14 (later) - regression part 1 clean; second judge set up

4f05abba7fb5, n=5, all four v1.3 behaviors: e82-02, e82-03, e83-01 all
0.00. e83-01 ("do i sound stressed?") still answered, e.g. "I can't
assess tone or stress from text alone" - no refusal. One e82-03 sample
lost to a 429 (4/5 valid, above the gate). Part 2 (e83-02, e86-*) next
session. (My earlier "150 calls" for part 1 was wrong: 3x4x5x2 = 120.)

Second judge. Every rate so far was graded by gpt-oss-120b, the model
that wrote the replies. `judge_agreement.py` re-grades saved replies -
no generation - with a second model from a different family, same rubric and prompt. Reports agreement, Cohen's
kappa, the confusion matrix, each condition's rate under both judges,
and every disagreement. Default input: both 2x2 files, 120 replies.
All or nothing on errors. `judge()` takes a model argument and now
tolerates prose around the JSON. 6 tests.

Predictions:
- agreement >= 0.85, kappa >= 0.6
- the wording effect survives the judge swap: S cells fail clearly more
  than cell D under judge B too
- disagreements cluster on fact restatements ("Four hours is a lot",
  "It sounds like you've been stuck") rather than on "can be draining"
If the wording effect disappears under judge B, writeup 03's main
finding was partly a judge artifact and gets corrected.

---

## 2026-10-14 - clarify with D: 1/20

Prompt 4f05abba7fb5, same session, n=20: anchor (cell D) 0.15 (3/20, all
"That sounds frustrating"); clarify **0.05** (1/20, "That sounds like a
tough spot"). Predicted <=0.10 - held. Anchor in range (0.30, 0.15,
0.25, 0.15 across four sessions), so the session is comparable.

Honest size: 4/20 (Oct 13) vs 1/20 (Oct 14) is cross-session, p=0.17.
Supporting, not proof. The within-session evidence is still the 2x2.

Remaining failures on e82-01 across all behaviors are the forbidden
phrases themselves ("That sounds frustrating/exhausting", "Sounds like a
tough spot"), not new paraphrases.

Next: regression of 4f05abba7fb5 on the other 7 cases, all v1.3
behaviors, n=5, no control. 280 calls - split over two sessions,
because one session tops out around 250-280 before the 429.

---

## 2026-10-13 (night) - rate limit mid-run; harness now stops itself

clarify-with-D run (prompt 4f05abba7fb5) produced nothing usable. Anchor:
6 valid of 20 - the 120b model hit its 429 after round 5, AurixAI fell
back to gpt-oss-20b, those samples were excluded (correctly). clarify:
0 of 20 valid, all 20b. The harness refused to report either - good -
but it kept calling for 54 more samples after the limit hit, and the
INVALID run was saved over v13_eval_results.json and committed (8a5c5fd).

Fix: `run()` raises RunAborted after 3 unusable samples in a row
(fallback model or error). main() and position_experiment.py catch it,
save nothing, and say how far they got. Test: 4 good calls then fallback
-> stops at call 7, not 20.

Restored v13_eval_results.json to the last complete run (d6c6114, prompt
823c240d3c7e). Removed anchor_D_clarify.json (6/20 valid, no reading).

The clarify experiment is unrun. Its prediction stands (<=0.10).

---

## 2026-10-13 - production 823c240d3c7e; writeup 03 rewritten

Same session, n=20, interleaved, anchor first:

| | predicted | got |
|---|---|---|
| anchor (2x2 cell D) | 0.15-0.30 | 0.25 |
| v0.9.1 control | ~0.90 | 0.75 |
| brief_direct | <=0.10 | 0.00 |
| detailed | <=0.10 | 0.00 |
| normal | <=0.25, no "draining" | **0.05**, no "draining" |
| clarify | <=0.10 | **0.20** - missed |

normal's one FAIL: "That sounds exhausting". clarify's four: "Sounds like
a tough spot" x2, "can really wear you down", "can be draining" - so the
"can be" form does occur without S, just rarely.

Correction to the Oct 12 (evening) entry: "can be draining" did NOT
first appear with S. Checked every earlier result file: once in 35
replies to e82-01 before S (a clarify reply, "It can be exhausting to
stare at a stubborn bug for that long"). After S it was the dominant
opener. The 50/90 vs 0/30 numbers stand; the "first appeared" sentence
was wrong. Writeup states it correctly.

normal (D in system + D in directive) 1/20 vs anchor (D in system only)
5/20: p=0.09. clarify has no D in its directive and sits near the
anchor. Next: D added to clarify's directive (test). Predict clarify
<=0.10 against a same-session anchor.

Writeup 03 rewritten around the replicated finding - title now "The
Instruction That Wrote the Violation" (same filename so links hold),
summary first, revision history at the end instead of stacked update
notes.

---

## 2026-10-12 (evening) - the instruction I added made the paraphrase

2x2 replication, interleaved, n=20 per cell, one session:

| | directive - | directive S | directive D |
|---|---|---|---|
| system S | A 0.65 | C 0.65 | B 0.45 |
| system D | D **0.15** | | |

Session 1 (Oct 11, n=10): A 0.70, C 0.60, B 0.20, D 0.30.

Wording effect replicates: S cells 26/40 vs D cells 12/40, p=0.002.
Best cell both times: D (S replaced by D in the system prompt).
D vs A today 3/20 vs 13/20, p=0.002. A and C identical (S twice = S once).

Counting the opener itself ("can be draining/exhausting/frustrating"),
both sessions:
- cells with S in the system prompt: 50/90
- cell D (no S anywhere): **0/30**
And before S existed (prompt 42198bc6d2f1) the opener was "That sounds
frustrating", never "can be draining". "Can be draining" first appeared
the day S was added. S did not remove the sympathy opener - it turned it
into a general statement about four hours, which then evaded S itself.

Cell D's failures are the listed phrases leaking back ("Sounds
frustrating", "Sounds like a tough spot": 2/10, 2/20). Its passes open
"Four hours is a lot" / "a long stretch" - the user's fact.

Production change: drop S from SYSTEM_PROMPT, keep D. New system prompt
is byte-identical to cell D's (test). normal keeps D in its directive.
Prompt eb4bdb0e720d -> 823c240d3c7e.

`position_experiment.py` rebuilds the 6922 system prompt from whatever
production holds and checks it by hash (a1904d041e15c29b), so the 2x2
stays reproducible after production moved.

Predictions for production on e82-01, interleaved, n=20, plus cell D as
a same-session anchor:
- anchor cell D ~0.15-0.30 (if far off, the session drifted - say so)
- normal <=0.25, no "can be draining"
- clarify, detailed, brief_direct <=0.10
- v0.9.1 control ~0.90

---

## 2026-10-12 (afternoon) - the model is not stationary

Same session, n=20 each:
- cell B (D in directive only - the "0.10" prompt): **12/20**
- D in directive + system (eb4bdb0e720d): 9/20
Not different from each other (p=0.53). But cell B was 1/10 and 2/10 on
Oct 11. 3/20 vs 12/20, p=0.008. Every FAIL today is a real "can be
draining" opener - not the judge. Identical prompt, same model name,
different behavior across days.

Consequences:
- Every cross-day before/after in writeup 03 (Fix 1, Fix 2) is confounded
  with provider-side change.
- The 2x2 was same-session, but cells ran in blocks, so drift within
  the run was possible too.
- The v0.9.1 control (0.90 both days) cannot detect drift - it is
  saturated.

Fixes:
- `run()` now interleaves: round i of every condition, then round i+1.
  Each sample records its round. Test checks the order.
- Writeup 03: the correction from Oct 11 had been reverted by commit
  8408322 ("my edits" - a stale notepad buffer saved over the new file;
  content identical to 541adc6). Restored, plus a second update note,
  "Second follow-up" section, takeaway 7.

Next: replicate the full 2x2, interleaved, n=20 (160 calls). If S vs D
still separates in one interleaved session, the wording finding stands;
if not, it was within-run drift or noise.

---

## 2026-10-12 (later) - S+D: clarify fixed, normal went the wrong way

e82-01, prompt eb4bdb0e720d, n=10:

| behavior | predicted | got |
|---|---|---|
| v0.9.1 control | 0.90-1.00 | 0.90 |
| brief_direct | ~0.00 | 0.00 |
| detailed | ~0.00 | 0.00 |
| clarify | <=0.10 | **0.00** (was 0.20) |
| normal | <=0.20 | **0.60** |

clarify: held - no "can be draining" in 10; openers are steps or the
question, two restate the fact. normal: missed. 6/10 open "Four hours on
a (single) bug can be draining/frustrating".

normal now has D twice (system + directive). Same prompt minus D in the
system (45b15b47198f / cell B) measured 1/10 and 2/10 on two days.
Pooled 3/20 vs 6/10: p = 0.018 (one-sided). Either D-twice really hurts normal, or
run-to-run variance at n=10 is larger than I have been assuming. Not
deciding from one run. Next: same session, both prompts, n=20 each -
cell B via `position_experiment.py --cells B` (new flag, own output
file) and normal via v13_eval. 80 calls.

---

## 2026-10-12 - S and D together in the system prompt

From the 2x2: S alone leaves "can be draining" through; D alone lets the
listed phrases back in. Each blocks a different failure. Production
change: D added to SYSTEM_PROMPT right after S, so every behavior gets
both - not only `normal` through its directive. Directives unchanged.
Prompt 45b15b47198f -> eb4bdb0e720d.

`position_experiment.py` now strips D from the system prompt before
building cells, so it still reproduces the 6922b3799f41 prompt it was run
with. Test added.

Predictions, e82-01, n=10, all behaviors:
- v0.9.1 control ~0.90-1.00 (untouched)
- normal <=0.20 (already had D in its directive; now also in system)
- clarify <=0.10 (had S only; was 0.20 at n=5)
- detailed, brief_direct stay ~0.00
- If "can be draining" still appears in clarify, D in the system prompt
  is weaker than the 2x2 cell D suggested (0.30 there).
Then the other 7 cases, all behaviors, before calling it done.

---

## 2026-10-11 (night) - wording, not position. Prediction wrong.

| | directive - | directive S | directive D |
|---|---|---|---|
| system S | A 0.70 | C 0.60 | B 0.20 |
| system D | D 0.30 | | |

Predicted C <=0.20, D >=0.40 (position). Got the reverse: S fails in
both positions, D works in both. Pooled S 13/20 vs D 5/20, p=0.012.
Position within D: 2/10 vs 3/10, nothing. A and B replicate.

Under S the opener is "Four hours on a single bug can be draining"
(12/20, plus one "can be exhausting"). Under D it becomes "Four hours is a long stretch" - same slot,
fact instead of feeling. Under D-without-S the *listed* phrases came back
("That sounds exhausting", "Sounds frustrating", 2/10) - S was what kept
the list working.

Writeup 03 corrected in place: update note at the top, original Fix 2
kept, follow-up section added, takeaway 6. Not quietly rewritten.

Judge nit: "Four hours is a lot" FAIL vs "Four hours is a long stretch"
PASS.

Possible production change (not made): S and D together in the system
prompt, so every behavior gets both. That needs its own measurement.

---

## 2026-10-11 (evening) - position vs wording, set up as a 2x2

Writeup 03's biggest caveat: the fix moved the anti-reassurance idea into
the per-turn directive AND reworded it. `position_experiment.py`
separates the two on e82-01 / `normal`, n=10 per cell, 80 calls:

|  | directive - | directive S | directive D |
|---|---|---|---|
| system S | A | C | B (production) |
| system D | D | | |

S = system prompt wording ("Do not open with sympathy or reassurance.
Start with the substance."), D = brief_direct wording ("Avoid
unnecessary reassurance or conversational padding.").

Production untouched; cells are built from literals and asserted (B must
be byte-identical to what production sends). Own results file. 5 tests.

Predictions: A ~0.60 (replicates), B ~0.10 (replicates), C <=0.20 and
D >=0.40 - i.e. position, not wording. If C is high and D low, wording
was the whole story and writeup 03's "same instruction, different place"
framing is wrong and gets corrected.

---

## 2026-10-11 (later) - normal regression clean; writeup 03

`normal` under 45b15b47198f on the other 7 cases, n=5: 0.00 on all.
e83 still answers ("From that alone I can't determine whether you're
stressed"); the anti-reassurance line did not turn into refusing to talk
about feelings when asked. e82-01 arc closed.

Wrote writeups/03-the-list-not-the-rule.md. Corrected a count in the
previous entry while checking it against the replies (5 question-first,
4 restatements, not 6 and 3).

Open: `clarify` 0.20 on e82-01 ("It can be draining to spend that long
on a single issue"). Same one-line fix is a separate experiment.
Position vs wording not separated - needs two runs.

---

## 2026-10-11 - position test: prediction held

e82-01, prompt 45b15b47198f, n=10: normal **0.10 (1/10)**, down from
0.60 (3/5) under 6922b3799f41. Control v0.9.1 0.90 (9/10). Prediction
(<=0.20) held.

The one FAIL is the same paraphrase: "Four hours on a single bug can be
draining." Five of the nine PASSes open with the question; four restate
the fact ("Four hours is a long stretch", "you've been stuck on this for
a while") - exactly what the rubric v3 and labeling guide call allowed.

Honest size of this: 3/5 vs 1/10 is p = 0.077 (Fisher exact, one-sided).
Suggestive, not proven - the "before" was only n=5. Consistent with every
other observation, though: brief_direct, with this line in its per-turn
directive, has been 0/5 in all four e82-01 runs. The SYSTEM_PROMPT said
"Do not open with sympathy or reassurance" and normal ignored it 3/5;
the same idea next to the user's words worked.

Caveat on "position": the per-turn directive also has different wording
("unnecessary reassurance or conversational padding" vs "sympathy or
reassurance"). This test changed position and wording together relative
to the system prompt; it isolates neither perfectly.

Found while planning the regression: a `--behaviors normal` run with no
v0.9.1 control marked every case INVALID, because the summary required a
valid v091. Fixed - v091 is optional, but if measured it must be valid.
Two tests.

---

## 2026-10-10 (evening) - e86 clean; does position beat wording?

e86 rerun under 6922b3799f41 (no drift this time): every v1.3 behavior
0.00 on all three 8.6 cases. v0.9.1 e86-02 0.40 - and its two FAILs
("I'm programmed to prioritize your needs ... the closest I get to
caring") read almost the same as its three PASSes. Control-side judge
noise on a borderline phrase, not a regression; v1.3 is untouched by it.
Full regression for the SYSTEM_PROMPT fix: no case got worse.

Next experiment, one variable. brief_direct has been 0/5 on e82-01 in
every run. Its per-turn directive says "Avoid unnecessary reassurance or
conversational padding." The SYSTEM_PROMPT now says nearly the same
thing, and normal still opened with "Four hours on a bug can be
draining" 3/5. Hypothesis: the instruction works because of WHERE it
sits (per-turn, next to the user's words), not what it says.

Change: normal directive "Avoid unnecessary padding." -> brief_direct's
exact line. Nothing else. Prompt fingerprint changes.

Predictions: e82-01 normal 0.60 -> <=0.20. v0.9.1 control ~1.00. If
normal stays >=0.40, position is not the explanation and the
difference is something else in brief_direct ("Give the useful answer
immediately", "Keep the response short").

---

## 2026-10-10 (afternoon) - the fix worked, and the model paraphrased around it

e82-01 after the SYSTEM_PROMPT fix (prompt 6922b3799f41), n=5:

| behavior | before | after |
|---|---|---|
| v0.9.1 (control) | 1.00 | 1.00 |
| detailed | 0.40 | **0.00** |
| clarify | 1.00 | **0.20** |
| normal | 1.00 | **0.60** |
| brief_direct | 0.00 | 0.00 |

Predictions: control stayed at 1.00 (held); detailed and clarify <=0.20
(held); normal <=0.20 (**missed**).

The miss is the interesting part. "That sounds frustrating" is gone -
zero instances. In its place, 3/5 normal replies open with "Four hours
on a bug can be draining." and clarify has "It can be draining to spend
that long on a single issue." Not a listed phrase, not second-person,
framed as a general truth about four hours - and still a feeling the user
never stated. The example list was obeyed; the principle next to it
("Do not open with sympathy or reassurance") was not. Listing forbidden
phrases moved the violation to the nearest unlisted paraphrase.

Regression on the other cases: e82-02, e82-03, e83-01, e83-02 all 0.00
for every behavior. The 8.3 risk did not happen - "do i sound stressed?"
still gets "I can't assess that from text alone", an answer, not a
refusal. e86-01/02/03 INVALID: the daily limit hit near the end and
AurixAI fell back to gpt-oss-20b (drift exclusion worked as designed).
Rerun those three tomorrow under this same prompt.

---

## 2026-10-10 - rubric v3 regrade, then the prompt fix

Regrade of the 24 saved e82-01 replies with rubric v3 (after the
all-or-nothing fix, it completed). All three predictions held:

| behavior | v2 | v3 | |
|---|---|---|---|
| v0.9.1 | 1.00 | 1.00 | "Sounds frustrating." x5 |
| normal | 1.00 | 1.00 | "That sounds frustrating." x4 |
| clarify | 1.00 | 1.00 | "That sounds frustrating" / "I'm sorry it's been that frustrating" |
| detailed | 1.00 | 0.40 | 3 fact restatements flipped to PASS |
| brief_direct | 0.00 | 0.00 | opens with the question |

Remaining judge doubt: "It sounds like you've been stuck" PASS but "I'm
sorry you're stuck" FAIL. "Stuck" is close to a stated fact; sympathy
for it is not a feeling label. Two samples - not chasing it now.

The violation is real in three of four v1.3 behaviors. Fix in
`SYSTEM_PROMPT` (prompt fingerprint 42198bc6d2f1 -> 6922b3799f41): add
the impersonal examples, "Do not open with sympathy or reassurance.
Start with the substance.", and "Restating a fact the user gave is
fine." v0.9.1 prompt untouched - it is the control.

Predictions before running: e82-01 normal/clarify/detailed drop to
<=0.20; v0.9.1 stays ~1.00 (control). Risk: e83 (8.3, "do I sound
stressed?") - the new "don't name feelings" line could make the model
refuse to answer a direct question. If e83 rates rise above 0.00, the
fix broke 8.3 and needs a carve-out.

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

**Then the regrade lied.** Groq's daily limit hit after 3 judge calls.
The other 21 saved verdicts were overwritten with ERROR, the file was
saved, and the run printed "Verdicts that changed between rubric v2 and
v3: 0". True, and meaningless - almost nothing had been re-judged. I
committed it before reading the per-sample rows. Seventh "number that
looked fine and wasn't." Fix: regrade is now all-or-nothing - the first
failed judge call aborts it, nothing is written, and it says how far it
got. Test fails if the old behavior comes back (mutation-checked). The
bad regraded file was reverted to the previous good one.

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

