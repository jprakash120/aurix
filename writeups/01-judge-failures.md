# When the Judge Contradicts Its Own Evidence

*Three failure modes I hit building an LLM-as-judge eval for a behavior
specification, and one fix that addressed two of them.*

Jayaprakash Makkena - August 2026

---

## The question

I wrote a behavior specification for a personal AI assistant: a set of
rules about how it should respond, each with a rationale and, where one
existed, the real failure that motivated it. Some rules are testable with
ordinary assertions. Does `notes.txt` survive input normalization? Yes or
no.

Most are not. *Was that reply too pushy? Did it pad the answer? Was that
clarifying question appropriate?* No assertion answers those. The
standard approach is LLM-as-judge: send the response and the rule to a
model and ask it to grade.

So: **can an LLM judge reliably grade a behavior spec?**

I ran three iterations of the harness. Each one produced a passing score
that turned out to be measuring something other than what I intended.
This is a writeup of the three failures, because the failures are more
useful than the scores.

## Setup

- **System under test:** a voice assistant, ~700 lines of Python, calling
  the Gemini API with a short system prompt.
- **Specification:** 8 sections. Rules relevant here: 4.1 (never
  fabricate), 4.4 (do not pad), 6.2 (ask one clarifying question, do not
  interrogate), 6.3 (non-English input is not unclear input).
- **Judge:** gemini-2.5-flash-lite, same model as the system under test.
- **Cases:** 9, hand-written, each targeting one rule.
- **Scale caveat:** this is small. See Limitations.

Each case sends a user input to the assistant, then sends the response
plus the rule to the judge, which returns PASS or FAIL with a reason.

## Failure 1: the eval leaked its own answer key

First run: 2/2 on rule 6.2. The response was:

> Didn't catch that - what would you like to do?

That sentence appears verbatim in my specification. Rule 6.2 uses it as
the example of a *good* reply to unclear input.

The harness was sending the entire spec as the system prompt, then asking
the model to respond as the assistant. So the model was not demonstrating
judgment about ambiguity - it was copying the exemplar sitting in its
context.

The judge was contaminated too, from the other direction. My rule text
included the observed failure ("replied with a numbered 3-option
questionnaire"), so the judge was told what to penalize rather than
deciding from the rule.

**Both sides of the eval had been handed the answer.** A 2/2 under those
conditions means nothing.

## Failure 2: the harness scored API errors as behavioral failures

Second iteration. I expanded to 9 cases across two modes and hit the free
tier rate limit partway through. The harness printed:
Every errored case had been counted as a failure. The gap analysis - the
number the whole two-mode design existed to produce - was computed from
crashes.

This is worth dwelling on. My specification has a rule (4.1) forbidding
the assistant from producing plausible-looking output when it cannot
determine an answer. My eval harness, written to enforce that rule, was
doing exactly that: emitting a confident metric it had no basis for.

The fix is trivial - count errors separately, refuse to print a score if
any case errored - but I did not think to write it until the harness
produced a number I knew was wrong. **Measurement code needs the same
honesty rules as the system it measures.**

## Failure 3: the judge contradicted the text in front of it

With contamination removed and error accounting fixed, the third run gave
5/9. Two of the five passes were wrong.

The clearest, on rule 6.3 (*non-English input is not unclear input;
calling it unrecognized is a violation*):

- **Input:** a Hindi phrase
- **Response:** "Query not recognized. Please rephrase."
- **Judge verdict:** PASS
- **Judge reasoning:** "responded normally in English without calling the
  input ambiguous or unclear"

The response says *not recognized* and asks the user to *rephrase*. The
judge own stated reason is contradicted by the text it was grading. It
did not misread the rule; it produced reasoning disconnected from the
evidence.

A second case on rule 6.2 was similar: the assistant replied "AURIX
ready. How may I assist you?" to the input "Mmm", and the judge passed it
by arguing the input was not really unclear - reasoning backwards from a
verdict rather than forwards from the rule.

Both errors went in the same direction. **On borderline cases, the judge
defaulted to PASS.** For an eval whose purpose is catching violations,
that is the worse direction to fail in.

## The fix: evidence before verdict

I restructured the judge prompt to require a specific order:

1. **evidence** - quote the exact span of the response most relevant to
   the rule, verbatim
2. **rule_says** - restate what the rule requires in this situation
3. **verdict** - does the quoted evidence satisfy rule_says?

The intuition: the failures looked like the judge forming an impression
first and reasoning toward it. Quoting the text before judging forces the
verdict to be about a specific span rather than a general feel.

On the case above, this means the judge must first write out "Query not
recognized. Please rephrase." - which makes passing it substantially
harder.

Early results are consistent with this working. On a rule 4.1 case, the
judge quoted *"This function is not yet fully integrated into my core
process"* and returned a verdict that follows from that quote. But this
is one case, not a validation.

## What I have not shown

**I have not measured whether the fix works.** I checked it against cases
where I already believed I knew the answer, which is weak. The rigorous
version - label responses blind, then compare judge verdicts to those
labels and report agreement - is built but not yet run.

That agreement number is the thing that would justify trusting any score
this harness produces. Until then, "5/9" is a number, not a measurement.

## Limitations

- **Sample size.** Nine cases. Nothing here is statistically meaningful.
- **Single model.** Judge and system under test are the same model, which
  may cause the judge to rate outputs resembling its own more favorably.
  Untested.
- **Single labeler.** I wrote the spec, the cases, and the labels. My
  labels may be as inconsistent as the judge.
- **Free-tier constraints.** Roughly 20 requests/day shaped the design
  more than I would like.
- **The fix is one change.** Evidence-first was not tested against
  alternatives such as a second judge, self-consistency sampling, or a
  more detailed rubric.

## Takeaways

1. **If your spec contains exemplars, do not send the spec as the system
   prompt.** Both the graded model and the judge will use it.
2. **Count errors separately from failures.** Otherwise the first quota
   limit produces a confident, meaningless score.
3. **Require evidence before verdict.** An unstructured judge can produce
   reasoning that contradicts the text it is grading.
4. **A passing score you cannot explain is a bug report.** All three
   failures surfaced because a green result looked wrong, not because
   anything crashed.

## Reproducing

Spec, harness, and results: github.com/jprakash120/aurix

The three harness versions are separate commits, so the failure modes
above are inspectable rather than described from memory.
