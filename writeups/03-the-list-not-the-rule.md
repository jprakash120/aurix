# The Instruction That Wrote the Violation

*I banned a phrase and the model found the nearest one I had not banned.
The instruction I added to stop it turned out to be what produced the
new phrase. Showing that took two sessions, because the model behaved
differently from one day to the next.*

Jayaprakash Makkena - October 2026

(This file was first published as "The Model Read the List, Not the
Rule". Two of its conclusions were wrong; the revision history at the end
says which, and why.)

---

## Summary

- Asked to stop telling a frustrated user what they feel, the model kept
  doing it in whatever form the rules did not name: "That sounds
  frustrating", then "Four hours on a bug can be draining".
- The second form was caused by my fix. Across two same-session
  experiments, replies opened with "can be draining" (or "exhausting" /
  "frustrating") in **50 of 90** cases when the system prompt contained
  *"Do not open with sympathy or reassurance. Start with the
  substance."*, and in **0 of 30** when that sentence was replaced with
  *"Avoid unnecessary reassurance or conversational padding."*
- The same prompt, same model name, gave **3/20 one day and 12/20 the
  next** (p = 0.008). Comparisons across days were unreliable; only
  same-session, interleaved comparisons held up.
- Production now uses the second wording. On the test input, the
  `normal` behavior fails 1/20; `clarify` still fails 4/20.

## The rule and the test

Rule 8.2 of my assistant's behavior spec: when the assistant infers an
emotional state, it changes how it behaves. It does not announce what it
thinks the user feels. "You sound tired" turns a private guess into a
claim the user then has to accept or correct.

The test input:

> ugh i have been at this bug for 4 hours

A good reply gets to the bug. "That sounds frustrating" tells the user
what they feel. "Four hours is a long stretch" restates their own fact,
and is allowed.

## Setup

The assistant (AURIX) has no single prompt. A contextual bandit picks a
response *behavior* each turn (`brief_direct`, `normal`, `detailed`,
`clarify`), and each adds a short directive to the turn. A bandit can
learn to pick any of them, so the eval measures every one, plus the old
fixed v0.9.1 prompt as a control.

Generation: `openai/gpt-oss-120b` via Groq, temperature 0.4 (the
production setting). Judge: the same model at temperature 0, grading one
rule, quoting the evidence before its verdict. Samples answered by a
fallback model are excluded. A condition with fewer than 75% valid
samples is not reported.

## Baseline

n=5 per behavior:

| behavior | violation rate | typical opening |
|---|---|---|
| v0.9.1 (control) | 1.00 | "Sounds frustrating." |
| normal | 1.00 | "That sounds frustrating." |
| clarify | 1.00 | "That sounds frustrating." |
| detailed | 1.00 | "I'm sorry you're stuck." |
| brief_direct | **0.00** | "What's the bug?" |

The system prompt already forbade this, with examples: *"You are sad."
"You sound stressed." "You seem angry."* All second-person. The
violation was impersonal ("*That* sounds frustrating"). The model kept
to the examples and missed the rule.

One behavior was clean. Only `brief_direct`'s directive contained
*"Avoid unnecessary reassurance or conversational padding."*

## First, the judge

Some `detailed` FAILs only restated the user's fact ("you've been stuck
on this for a while"). The spec had not said whether that counts. I
amended it (impersonal forms count; restating a stated fact does not),
updated the judge rubric, and regraded the saved replies, so any change
in a verdict came from the judge and not the model. All three written
predictions held: "That sounds frustrating" stayed FAIL, the
restatements flipped to PASS, `brief_direct` stayed 0.00.

The first attempt at that regrade reported *"Verdicts that changed: 0"*.
That was true and meant nothing: a rate limit hit after 3 of 24 judge
calls, the code wrote ERROR over the other 21 saved verdicts, and an
ERROR does not count as a change. I committed it before reading the
rows. Regrades are now all or nothing, and a test fails if the old
behavior returns.

## Fix 1: a better list, and a new paraphrase

I added the impersonal forms to the forbidden examples ("That sounds
frustrating." "Sounds exhausting." "I'm sorry you're upset."), and two
sentences. I'll call the first one **S**:

> *Do not open with sympathy or reassurance. Start with the substance.*
> *Restating a fact the user gave is fine.*

"That sounds frustrating" disappeared. In its place:

> Four hours on a bug can be draining.

It is not on the list and not second-person. It is phrased as a general
truth about four hours, and it still names a feeling the user never
stated. `normal` went from 1.00 to 0.60. At the time I read this as the
model obeying the list and ignoring S. The 2x2 below shows S was
producing it.

## A wrong turn

Copying `brief_direct`'s line (call it **D**) into `normal`'s directive
took `normal` from 0.60 to 0.10. I concluded that *position* mattered,
because the directive sits next to the user's message. A 2x2 that
separated position from wording said it was the wording. The day after
that, the exact prompt behind the "0.10" measured 0.60. Both earlier
conclusions came from comparing runs on different days.

## The model does not hold still

Same prompt (D in the directive, S in the system prompt), same model
name:

| | Oct 11 | Oct 12 |
|---|---|---|
| violations | 1/10, 2/10 | **12/20** |

3/20 vs 12/20, p = 0.008. Every FAIL on Oct 12 was a real "can be
draining" opener, so it was not the judge. I cannot see what changed on
the provider's side. The control could not have shown it: a prompt that
fails 90% of the time has no room to move.

After this I changed the method. Conditions are compared only within one
session, and samples are interleaved (one of each condition, then the
next round), so drift during a run lands on every condition equally. A
test checks the order.

## The 2x2, twice

`normal` behavior, same input. S and D in the system prompt and/or the
directive:

| | no extra directive | S in directive | D in directive |
|---|---|---|---|
| **S in system prompt** | 0.70 / 0.65 | 0.60 / 0.65 | 0.20 / 0.45 |
| **D in system prompt** | 0.30 / **0.15** | | |

Oct 11 (n=10, blocked) / Oct 12 (n=20, interleaved).

- **Wording, not position.** In the Oct 12 run the S cells failed 26/40
  and the D cells 12/40 (p = 0.002). Repeating S in the directive changed
  nothing (0.65 vs 0.65).
- **The best cell both times** had no S anywhere: D in the system
  prompt.
- **The opener itself.** "Can be draining / exhausting / frustrating":
  **50 of 90** replies in cells with S in the system prompt, **0 of 30**
  in the cell without it. Before S existed, the usual opener was "That
  sounds frustrating"; the "can be ..." form appeared once in 35 earlier
  replies to this input (a `clarify` reply: "It can be exhausting to
  stare at a stubborn bug for that long"). After S it became the
  dominant opener.

My best reading is that S did not remove the sympathy opener. It pushed
the model to recast it as a statement about the substance, the four
hours, and the model does not treat that as sympathy, so S never applies
to it. D does not mention sympathy. In the D cell the same opening
slot is filled with the user's fact: "Four hours is a lot", "Four hours
is a long stretch". This is an interpretation of the replies; I did not
test the mechanism directly.

D has its own leak: without S, 2/10 and 2/20 replies used the forbidden
phrases themselves ("Sounds frustrating", "Sounds like a tough spot").

## What production runs now

S removed, D kept in the system prompt (byte-identical to the best
cell). `normal` also keeps D in its directive. Oct 13, n=20,
interleaved, with the best 2x2 cell re-run in the same session as an
anchor:

| | violation rate |
|---|---|
| anchor (2x2 cell D) | 0.25 (was 0.30, 0.15) |
| v0.9.1 control | 0.75 |
| brief_direct | 0.00 |
| detailed | 0.00 |
| normal | **0.05** |
| clarify | **0.20** |

The anchor landed in its earlier range, so the session is comparable.
`normal` has no "can be draining"; its one FAIL is "That sounds
exhausting". `clarify` fails 4/20: two "Sounds like a tough spot", one
"can really wear you down", one "can be draining". Its directive did
not carry D.

Oct 14: with D added to `clarify`'s directive, `clarify` failed **1/20**
("That sounds like a tough spot"). The same-session anchor scored 0.15,
inside its earlier range. 4/20 vs 1/20 across sessions is p = 0.17, so
this is consistent with the `normal` result rather than proof on its
own. Production now has D in the system prompt and in the `normal` and
`clarify` directives (prompt `4f05abba7fb5`). The regression on the
other seven test inputs is still to run.

## Limits

- **One input.** Every number is one user message. Other messages may
  produce other paraphrases.
- **One model, judging itself.** The judge is the generator's own model.
  Anthropic's eval guidance recommends a different grader model. A
  cross-model regrade of the saved replies is planned.
- **Small n.** The strongest results are p = 0.002 within a session.
  Several others are p ≈ 0.08 and are reported as suggestive.
- **Provider drift is observed, not explained.** I know the behavior
  changed between days; I do not know why.
- **One author.** I wrote the spec, cases, rubric, fixes, and this.

## Takeaways

1. **A list of forbidden examples gets satisfied literally.** Each list
   I wrote was obeyed, and the behavior moved to whatever the list did
   not name.
2. **An instruction can create the behavior it forbids.** "Do not open
   with sympathy" produced a new kind of sympathy opener in 50 of 90
   replies. Read the replies after every fix, not just the rate.
3. **A fix that "works" may only have moved the violation.** 1.00 → 0.60
   looked like progress. In the replies it was one violation being
   replaced by another.
4. **Compare within a session, interleaved, with an anchor.** An API
   model under a fixed name gave 3/20 and 12/20 on consecutive days.
   Cross-day before/after numbers mixed my change with the provider's.
5. **Fix the instrument before the behavior.** An unclear rubric and a
   regrade that saved bad data would each have made a change look better
   or worse than it was.
6. **Write predictions down, and test your own explanations.** Two of my
   explanations ("the model ignored S", "position matters") fit the data
   I had and were wrong. Both were caught because the next experiment
   was designed to test them.

## Revision history

- **Oct 10:** first version. Concluded the directive fix worked
  because of *position*.
- **Oct 11:** a 2x2 showed wording, not position.
- **Oct 12:** the "0.60 → 0.10" result did not replicate: the same
  prompt changed between days. Cross-day comparisons withdrawn.
- **Oct 13:** rewritten around the replicated 2x2. The main finding
  changed from "the model ignored S" to "S produced the paraphrase".
  Earlier versions are in the git history of this file.

## Reproducing

Spec, harness, all result files and the build log:
github.com/jprakash120/aurix

- Prompt fingerprints: `42198bc6d2f1` baseline, `6922b3799f41` with S,
  `45b15b47198f` D in `normal`'s directive, `eb4bdb0e720d` S+D,
  `823c240d3c7e` D only, `4f05abba7fb5` current (D also in `clarify`).
- 2x2: `position_experiment.py`. Results: `position_experiment_results.json`
  (Oct 11), `position_2x2_interleaved.json` (Oct 12). It rebuilds the
  S-era system prompt and checks it by hash, so it still runs after
  production changed.
- Production run with anchor: `v13_eval_results.json` and
  `anchor_D_1013.json` at commit d6c6114.
