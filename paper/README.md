# Displacement study

**Question.** When a system prompt forbids a behavior, does the behavior
go away, or move into a form the instruction does not name?

Origin: writeup 03. "Do not open with sympathy" did not stop sympathy
openers on one input; it turned "That sounds frustrating" into "Four hours
on a bug can be draining" (50/90 replies vs 0/30 without it). This study
tests whether that generalizes: three behaviors, four instruction styles,
60 inputs each, four models.

| behavior | example violation |
|---|---|
| sympathy | "Oh no, that's incredibly frustrating." (user stated no feeling) |
| apology | "My apologies for that mistake." (after a correction) |
| emphasis | "The capital is **Ottawa**." (bold in a one-line answer) |

Conditions: `none`, `list` (the model's own three most common phrases,
or bold for emphasis), `principle` (one sentence forbidding the
behavior), `positive` (one sentence saying what to do instead).

Version 2 (2026-11-08). The 2-input smoke test (v1, files directly in
`results/`) showed: closers never happened (0/30), and the models never
used the sympathy phrases I had picked, so a list of them could not show
displacement. v2 replaces closers with emphasis and derives each model's
list from its own replies to 20 separate calibration inputs.

Main measure: violation rate per cell, and the **displaced share** -
violations containing none of the listed phrases.

## Run

```
python paper/run_study.py plan
python paper/run_study.py calibrate --max-calls 160          # no-instruction replies, calibration inputs
python paper/run_study.py judge --calibration --max-calls 160
python paper/derive_lists.py                                 # writes lists.json - review, then commit
python paper/run_study.py generate --inputs 20 --max-calls 250   # pilot
python paper/run_study.py judge --max-calls 250
python paper/analyze.py
```

Every step resumes where it stopped. `generate` refuses to start until
lists.json exists, and lists.json is frozen once it starts.

Files (in `results/v2/`): `calibration.jsonl`, `generations.jsonl` (one
reply per line, with the exact system prompt), `*judgments_<judge>.jsonl`,
`summary_<judge>.md`.

Stimuli are frozen once the first real run starts (`STIMULI_VERSION`).
