# Displacement study

**Question.** When a system prompt forbids a behavior, does the behavior
go away, or move into a form the instruction does not name?

Origin: writeup 03. "Do not open with sympathy" did not stop sympathy
openers on one input; it turned "That sounds frustrating" into "Four hours
on a bug can be draining" (50/90 replies vs 0/30 without it). This study
tests whether that generalizes: three behaviors, four instruction styles,
60 inputs each, four models.

| behavior | position | example violation |
|---|---|---|
| sympathy | opening | "That sounds frustrating." |
| apology | anywhere, after a correction | "Apologies for the confusion." |
| closer | ending | "Let me know if you need anything else!" |

Conditions: `none`, `list` (three forbidden phrases), `principle` (one
sentence forbidding the behavior), `positive` (one sentence saying what
to do instead).

Main measure: violation rate per cell, and the **displaced share** -
violations containing none of the listed phrases.

## Run

```
python paper/run_study.py plan
python paper/run_study.py generate --inputs 2 --max-calls 24     # smoke test, all 4 models
python paper/run_study.py judge --max-calls 24
python paper/analyze.py
```

Then the pilot (20 inputs) and the full run (60), a few hundred calls per
session. Both phases resume where they stopped.

Files: `results/generations.jsonl` (one reply per line),
`results/judgments_<judge>.jsonl`, `results/summary_<judge>.md`.

Stimuli are frozen once the first real run starts (`STIMULI_VERSION`).
