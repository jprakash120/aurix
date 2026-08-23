# Experiment log

| Date | What | Result | Note |
|---|---|---|---|
| 08-02 | 22 unit tests | pass | regression for filename bug |
| 08-02 | + router tests | 45 pass | [[rule-2.1-local-before-model]] |
| 08-09 | eval v1, rule 6.2 | 2/2 | **invalid** — [[contamination]] |
| 08-09 | eval v2, 2 modes | 0/9 | **invalid** — errors scored as fails |
| 08-09 | eval v3, evidence-first | 5/9 | 2 judge errors found |
| 08-09 | labeling rounds 1–3 | 50% self-consistency | [[06-i-was-worse]] |
| 08-10 | A/B single sample | A=7/8 B=5/8 | **invalid** — [[gold-labels]] misuse |
| 08-23 | rate test n=5 | A=0.30 B=0.25 | delta within noise |
| 08-23 | rate test n=20 | running | — |

## Pattern

Four of nine experiments were invalid, each for a different reason.
Every invalidation was caught by asking "why does this number look
wrong?" rather than by a crash.

Related: [[finding-measurement-needs-honesty]]
