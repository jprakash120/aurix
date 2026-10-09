# AURIX

A voice assistant, built as a lab for studying model behavior.

The assistant is real and runs on Windows. But the point of the project is
what surrounds it: a written behavior specification, a routing layer that
decides when a language model should and should not be consulted, and a
test suite that enforces the spec.

## Why this exists

Most assistant projects demonstrate that an API can be called. This one is
about a harder question: **how do you specify how a system should behave,
and then verify that it does?**

Every rule in [SPEC.md](SPEC.md) is enforceable by a test. A rule with no
test is an aspiration, not a specification.

## Repository layout

| File | Purpose |
|---|---|
| `SPEC.md` | Behavior specification. The source of truth. |
| `aurix_core.py` | Pure logic. No platform dependencies. Testable anywhere. |
| `test_aurix_core.py` | 59 tests: routing, input handling, file commands. |
| `test_eligibility_guards.py` | Rule 8.5 silence guards, one test per guard, mutation-verified. |
| `aurix_v13.py` | Current runner: voice, vision, bandit policy, episodic memory. |
| `aurix_ai.py` | Provider layer: Groq first (reasoning, Whisper STT, vision), Gemini fallback. |
| `aurix_learning.py` | LinUCB contextual bandit choosing response *behavior*, not emotion labels. |
| `aurix_world_memory.py` | SQLite episodic memory with scene-novelty change detection. |
| `aurix_prompting.py` | The system prompt and turn template. Imported by the runner AND the eval, never copied. |
| `v13_eval.py` | Section 8 violation rates for the real v1.3 pipeline, per bandit behavior, vs the v0.9.1 baseline. |
| `eval_judge.py`, `rate_test.py`, `optimizer.py` | Earlier harnesses. They measure the v0.9.1 prompt, not v1.3. |
| `TASK.md` | Standing rules for automated coding agents working on this repo. |

The core/runner split is deliberate. `aurix_core.py` imports nothing
platform-specific, so the logic can move to other hardware later without
being rewritten.

## The central design rule

**Local before model.** If the operating system knows something with
certainty, the model is never asked.

    route_command("what time is it")     -> "time"     (local)
    route_command("read file notes.txt") -> "file"     (local)
    route_command("explain transformers")-> "model"    (API call)

This is a correctness rule before it is a cost rule. Asked for the time,
a language model cannot know the answer - but it will often produce
something answer-shaped anyway.

## Documented failures

Each of these was observed in real use, then specified and tested against.

**Fabricated time.** Asked "wat time is it?", the assistant routed to the
model, which returned the literal placeholder text
`[Insert Current Time, e.g., 10:30 AM PST]`. The model had no way to know
the time and produced a plausible-looking answer instead of declining.
Fixed by explicit routing. Spec rules 2.1 and 4.1.

**Destroyed filenames.** A single normalization pass stripped punctuation
from all input, so `aurix_memory.txt` became `aurix_memorytxt` before file
lookup. The underlying tension: spoken commands should be forgiving, but
filename arguments must be literal. One regex cannot serve both. Fixed by
splitting the paths. Spec rules 3.1 through 3.3.

**Over-interrogation.** Given the input "Mmm", the assistant replied with a
numbered three-option diagnostic questionnaire. Specified as a violation
under rule 6.2 - not yet automatically enforced, since tone requires a
model-based grader rather than an assertion.

## Running it

    python -m pip install -r requirements.txt
    setx GEMINI_API_KEY "your_key"      # once, then reopen the shell
    python aurix_v091.py

Tests, which need no API key and no Windows:

    python -m pytest -q

## Status and next steps

Working: voice I/O, local command routing, file reading and summarization,
vision, episodic world memory, a learned response policy, 99 passing tests
(under a second, no API calls).

Next: run `v13_eval.py` - the judge-measured rates below were taken against
the v0.9.1 fixed prompt, which v1.3 no longer uses. Then writeups 03 and 04,
and SPEC section 9 extending the honesty rules to vision.

Open design questions are tracked in section 7 of the spec rather than
left implicit.

## License

MIT

## Results so far

| Finding | Measurement |
|---|---|
| Labeler self-consistency across 3 rounds | 50% (chance) |
| LLM judge vs gold labels | 7/8 |
| Human labeler vs gold labels | 6/8 |
| Rule 8.3 violation rate, n=20 (v0.9.1 prompt, judge rubric v1) | 0.59-0.70 |
| Rule 8.3, v1.3 per behavior, n=5, rubric v2 | 0.00 except `clarify` (0.80 on one case) |
| Judge verdicts changed by clarifying the 8.3 rubric | 16 of 49, all FAIL -> PASS |
| Optimizer changes kept | 0 of 2 |
| Rule 8.5 guards protected by tests, before / after mutation testing | 0 of 5 / 5 of 5 |
| Automated tests | 99 passing |

Writeups: [judge failure modes](writeups/01-judge-failures.md) - [the labeler was the problem](writeups/02-labeler-was-the-problem.md)

