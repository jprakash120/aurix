# 6. I was worse than the judge

To check whether the judge could be trusted, I labeled 8 responses by
hand and compared. Three phases, deliberately separated so judge
verdicts could not anchor my labels.

## Results

| Round | Labels | vs gold |
|---|---|---|
| 1 | 4 pass, 4 fail | 6/8 |
| 2 | 8 pass, 0 fail | — |
| 3 | 8 pass, 0 fail | 6/8 (different two wrong) |
| **Judge** | — | **7/8** |

**[[self-consistency]] between my own rounds: 50%.** Chance, on a
binary task.

## What went wrong each round

**Round 1** — drifted into grading overall quality. My reasons included
"it doesnt remember the memory" — not part of any rule I was testing.

**Round 2** — overcorrected. Passed everything. Agreement with the judge
rose to 7/8, which looked like improvement and was not: two labelers
sharing a PASS bias is not calibration.

**Round 3** — wrote a numbered decision procedure, then pattern-matched
its shape instead of executing it. Cited "step 1, step 2, step 3" on
consecutive cases — numbering the cases, not the step that fired.

## The finding

Both persistent errors landed on [[rule-8.3-answer-when-asked]] —
the only rule with a conditional exception.

→ [[finding-conditional-rules]]
→ next: [[07-its-a-coin-flip]]
