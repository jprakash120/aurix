# AURIX

Start here. This is the map.

> **What AURIX is:** a voice assistant on a laptop, built as a lab for
> studying how AI systems should behave — and eventually the software
> brain for a physical robot.

---

## The two tracks

AURIX serves two purposes that share a codebase but not a destination.

| | Track 1 — Career | Track 2 — Personal |
|---|---|---|
| Goal | Model behavior / post-training role | A physical robot I own |
| Output | Specs, evals, writeups | Hardware, vision, movement |
| Timeline | 2–4 years via intermediate roles | Years, hobby pace |
| Status | Active | Design only |

Both are real. Track 1 pays. Track 2 is why I open the laptop.

→ [[track-1-career]] · [[track-2-robot]]

---

## Where things stand

```
BUILT        spec · 45 tests · router · eval harness (v3)
             human labeling · gold labels · 2 writeups
MEASURING    violation rates at n=20
NEXT         writeup 03 · vision on laptop camera
```

→ [[status]] · [[progress]]

---

## Learning

Ten free courses, two tracks, checkboxes to tick as you go.

→ **[[learning-path]]** · [[progress]]

---

## The story so far

1. [[01-the-assistant]] — a script that worked, mostly
2. [[02-the-first-bug]] — filenames lost their extensions
3. [[03-writing-the-spec]] — rules with reasons
4. [[04-testing-the-untestable]] — LLM as judge
5. [[05-the-judge-was-wrong]] — evidence before verdict
6. [[06-i-was-worse]] — 50% self-consistency
7. [[07-its-a-coin-flip]] — same prompt, different behavior

---

## Reference

**Concepts** — [[llm-as-judge]] · [[violation-rate]] · [[n-samples]] ·
[[gold-labels]] · [[self-consistency]] · [[contamination]]

**Rules** — [[rule-4.1-honesty]] · [[rule-8.2-dont-narrate]] ·
[[rule-8.3-answer-when-asked]] · [[rule-8.6-no-inner-states]]

**Findings** — [[finding-conditional-rules]] ·
[[finding-persona-causes-fabrication]] · [[finding-measurement-needs-honesty]]

**Experiments** — [[exp-log]]

**Daily** — [[log/README|build log]]

---

## If I have been away a while

Read in this order:

1. This page
2. [[status]] — what is done, what is next
3. [[07-its-a-coin-flip]] — the most recent result
4. `SPEC.md` in the repo root — the actual rules

Then run `python -m pytest -q` to confirm nothing is broken.
