# The Model Read the List, Not the Rule

*I banned a phrase. The model stopped saying it and found the nearest
phrase I had not banned. What worked was a differently worded version of
the same instruction, and where I put it turned out not to matter.*

Jayaprakash Makkena - October 2026

> **Updated 2026-10-11.** The first version of this writeup concluded
> that the fix worked because of *where* the instruction sat. A follow-up
> 2x2 experiment (last section) separated position from wording. The
> wording mattered and the position did not. The original Fix 2 section
> is kept as written, with the correction added after it.

---

## The rule

Rule 8.2 of my assistant's behavior spec: when the assistant infers an
emotional state, it should change how it behaves and not announce what it
thinks the user feels. "You sound tired" turns a private guess into a
claim the user then has to accept or correct.

The test case is a single message:

> ugh i have been at this bug for 4 hours

A good reply gets to the bug. A reply that opens "That sounds
frustrating" has told the user what they feel.

## Setup

The assistant (AURIX) does not use one fixed prompt. A contextual bandit
picks a response *behavior* each turn (`brief_direct`, `normal`,
`detailed`, `clarify`, sometimes `silence`), and each behavior adds a
short directive to the turn prompt. So an eval has to measure every
behavior the bandit could pick, not just one prompt. The harness
(`v13_eval.py`) does that, plus the old v0.9.1 fixed prompt as a control
that never changes.

Generation uses `openai/gpt-oss-120b` at temperature 0.4, the production
setting. An LLM judge grades each reply against one rule, quoting the
evidence before giving a verdict. Samples from fallback models are
excluded, not averaged in. A condition is reported only if at least 75%
of its samples are valid.

## Baseline: four of five behaviors fail

n=5 per behavior:

| behavior | violation rate | typical opening |
|---|---|---|
| v0.9.1 (control) | 1.00 | "Sounds frustrating." |
| normal | 1.00 | "That sounds frustrating." |
| clarify | 1.00 | "That sounds frustrating." |
| detailed | 1.00 | "I'm sorry you're stuck." |
| brief_direct | **0.00** | "What's the bug?" |

Two things stood out.

The system prompt already forbade this, with examples: *"You are sad."
"You sound stressed." "You seem angry."* All three are second-person.
The model's violation is impersonal: "*That* sounds frustrating." It
followed the examples to the letter and missed the point.

And one behavior was clean. `brief_direct`'s directive is the only one
containing the line *"Avoid unnecessary reassurance or conversational
padding."*

## First, check the judge

Before changing behavior I read the FAILs. Some `detailed` replies only
restated what the user had said: "It sounds like you've been stuck on
this for a while." That repeats a fact; it is not a guess about a
feeling. The spec never said which side of the line that falls on.

So I amended the spec (impersonal forms count; restating a stated fact
does not), updated the judge rubric to match, and regraded the 24 saved
replies. The replies stay fixed, so any change in a verdict comes from
the judge, not the model. I wrote down predictions first:

1. "That sounds frustrating" replies stay FAIL.
2. Restatements of the user's own fact flip to PASS.
3. `brief_direct` stays at 0.00.

All three held. `detailed` went from 1.00 to 0.40 (three flips, all fact
restatements); nothing else moved. The violation was real in three of
four v1.3 behaviors.

### The regrade that said nothing changed

The first attempt at that regrade printed:

    Verdicts that changed between rubric v2 and v3: 0

That was true and meant nothing. Groq's daily rate limit hit after 3
judge calls. The regrade caught each failure, overwrote the saved FAIL or
PASS with ERROR, saved the file, and counted zero flips, because an ERROR
is not a flip. I committed it before reading the rows.

The fix: a regrade is now all or nothing. The first failed judge call
aborts it, nothing is written, and it reports how far it got. A test
fails if the old behavior returns. I checked that by restoring the old
code and watching the test fail.

## Fix 1: improve the list

I changed the system prompt. I added the impersonal forms to the
forbidden examples ("That sounds frustrating." "Sounds exhausting."
"I'm sorry you're upset."), then a principle: *"Do not open with sympathy
or reassurance. Start with the substance."* and an allowance:
*"Restating a fact the user gave is fine."*

| behavior | before | after |
|---|---|---|
| v0.9.1 (control) | 1.00 | 1.00 |
| detailed | 0.40 | 0.00 |
| clarify | 1.00 | 0.20 |
| normal | 1.00 | **0.60** |
| brief_direct | 0.00 | 0.00 |

"That sounds frustrating" disappeared from v1.3: zero instances in 20
replies. (The control still said it, as it should.)
In its place, three of five `normal` replies opened with:

> Four hours on a bug can be draining.

`clarify` produced: *"It can be draining to spend that long on a single
issue."*

Neither is on the list. Neither is second-person. Both are worded as a
general truth about four hours rather than a claim about the user. Both
still name a feeling the user never stated, and both break the principle
written two lines below the list.

The model obeyed the list and ignored the rule written right after it.
Banning phrases did not remove the behavior. It moved it to the closest
phrase I had not banned.

The regression on the other seven cases was clean: 0.00 for every v1.3
behavior. The case I worried about, "do i sound stressed?" (rule 8.3,
where the assistant *should* talk about feelings because it was asked),
still got real answers: "I can't assess stress from the text alone."

## Fix 2: brief_direct's line

`brief_direct` had been at 0/5 in every run, and its anti-reassurance
line is in the per-turn directive, placed right next to the user's
message. The system prompt now said nearly the same thing and `normal`
ignored it.

So I changed one line. `normal`'s directive went from *"Avoid
unnecessary padding."* to `brief_direct`'s exact line, *"Avoid
unnecessary reassurance or conversational padding."* Nothing else
changed. I predicted `normal` would fall to 0.20 or below, and ran n=10
because at n=5 one sample moves the rate by 0.20.

| | before | after |
|---|---|---|
| normal | 0.60 (3/5) | **0.10 (1/10)** |
| v0.9.1 (control) | 1.00 | 0.90 |

The prediction held. Five of the ten replies opened with the question.
Four restated the fact ("Four hours is a long stretch"), which the spec
allows. One said "can be draining" again. `normal` on the other seven
cases: 0.00.

## How much this shows

Less than the table suggests.

- **3/5 vs 1/10 is p = 0.077** (Fisher's exact test, one-sided). That is
  suggestive, not proof, because the "before" was only five samples.
- **Position and wording changed together.** Compared with the system
  prompt, the directive is in a different place *and* worded differently
  ("unnecessary reassurance or conversational padding" vs "sympathy or
  reassurance"). This test cannot tell which one mattered. *Resolved
  below: it was the wording.*
- **One input.** Every number here is one user message. A different
  message might produce different paraphrases.
- **One model, one judge, one author.** I wrote the spec, the cases, the
  rubric and the fixes. The judge is the same model as the generator
  (`gpt-oss-120b`, at temperature 0).

## Follow-up: it was the wording, not the place

I separated the two with a 2x2 on the same input and the same
behavior, n=10 per cell. S is the system prompt's wording (*"Do not open
with sympathy or reassurance. Start with the substance."*). D is
`brief_direct`'s wording (*"Avoid unnecessary reassurance or
conversational padding."*).

| | no extra directive | S in directive | D in directive |
|---|---|---|---|
| **S in system prompt** | A: 0.70 | C: 0.60 | B: 0.20 |
| **D in system prompt** | D: 0.30 | | |

My written prediction was C at 0.20 or below and D at 0.40 or above,
which would mean position. The results came out the other way.

- **Wording S fails wherever it goes.** It fails in the system prompt
  (A, 0.70), and it still fails when also repeated in the directive
  (C, 0.60). Saying it twice, once next to the user's words, did not help.
- **Wording D works wherever it goes.** In the directive (B) it scored
  0.20; moved into the system prompt instead (D) it scored 0.30. That is
  one sample apart.
- Pooled, the S cells failed 13/20 and the D cells 5/20: **p = 0.012**
  (Fisher's exact test, one-sided). Position within the D cells: 2/10 vs 3/10, no
  detectable difference.
- A and B reproduce the earlier runs (0.60 and 0.10 then, 0.70 and 0.20
  now).

The replies show what each wording does. Under S, the opener is "Four
hours on a single bug can be draining" in 12 of the 20 replies (plus
one "can be exhausting"). The
model does not seem to read that as sympathy, so S never applies to it.
Under D, the most common opener becomes "Four hours is a long stretch":
the same slot in the sentence, filled with the user's fact instead of a
feeling. My guess is that "conversational padding" covers the whole
opener, while "sympathy" only covers the forms the model recognizes as
sympathy. That is a hypothesis; this experiment does not test it.

One more detail. With D in the system prompt *in place of* S, "That
sounds exhausting" and "Sounds frustrating" came back (2/10), even
though both are on the forbidden list in that same prompt. With S
present, the listed phrases never appeared. Each wording seems to
suppress something different.

The judge has a problem at this level of detail too: "Four hours is a
long stretch" passes, "Four hours is a lot" fails once. Both restate the
user's fact.

## Takeaways

1. **A list of forbidden examples is a spec the model can satisfy
   literally.** Second-person examples taught the model that the
   second-person form was the problem. When I added impersonal examples,
   it moved to generalizations. Each list gets followed exactly, and the
   behavior moves somewhere the list does not cover.
2. **Read the replies, not the rate.** 1.00 → 0.60 looks like partial
   progress. In the replies, it is one violation being swapped for
   another.
3. **Look for the behavior that already works.** The best clue in this
   whole investigation was a behavior sitting at 0.00 from the first
   run. I copied its line before I understood why it worked.
4. **Fix the instrument before the behavior.** Two judge problems in this
   arc (an unclear rubric and a regrade that saved bad data) would
   each have made a behavior change look better or worse than it was.
5. **Write predictions before running.** Four predictions held and one
   missed. The miss was the finding.
6. **A plausible mechanism is not a tested one.** I wrote "same idea,
   different place" because it fit the evidence I had. Testing it cost 80
   API calls and showed the explanation was wrong. The fix still works.
   My explanation for why it worked did not survive the test.

## Reproducing

Spec, harness, every result file and the build log:
github.com/jprakash120/aurix

Prompt fingerprints identify each state: `42198bc6d2f1` (baseline),
`6922b3799f41` (system-prompt fix), `45b15b47198f` (directive fix).
Each run is a separate commit. The 2x2 is `position_experiment.py`;
its results are in `position_experiment_results.json`.
