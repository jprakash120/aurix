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
| `test_aurix_core.py` | 45 tests enforcing the spec. |
| `aurix_v091.py` | Windows runner: voice, microphone, OS commands. |
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
conversation memory, 45 passing tests.

Next: an LLM-as-judge grader for the spec rules that assertions cannot
check - tone, length, and the quality of clarifying questions.

Open design questions are tracked in section 7 of the spec rather than
left implicit.

## License

MIT
