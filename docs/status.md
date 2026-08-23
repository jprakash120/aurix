# Status

Updated: 2026-08-23

## Built and working

| Thing | File | State |
|---|---|---|
| Voice assistant | `aurix_v091.py` | works — voice, files, commands |
| Pure logic core | `aurix_core.py` | no platform deps, portable to Pi |
| Test suite | `test_aurix_core.py` | 45 passing |
| Behavior spec | `SPEC.md` | 8 sections |
| Eval harness | `eval_judge.py` | v3, evidence-first judge |
| Labeling study | `human_eval.py` | 3 rounds done |
| Rate test | `rate_test.py` | running at n=20 |

## Measured

- Labeler self-consistency: **50%** — see [[06-i-was-worse]]
- Judge vs gold: **7/8**
- Human vs gold: **6/8**
- Rule 8.3 violation rate: **~0.40–0.60** — see [[07-its-a-coin-flip]]
- Rule 8.2 case e82-01: **1.00** — deterministic failure

## Next

1. Finish n=20 run, compare variants
2. Writeup 03 — the coin-flip finding
3. Laptop camera vision (Track 2, $0)

## Blocked / parked

- Gemini quota (~20/day) → moved to Groq
- Aider agent loop → Python 3.14 conflict, parked
- Hardware purchases → nothing until vision works in software
