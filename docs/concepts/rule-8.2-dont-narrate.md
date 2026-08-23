# Rule 8.2 — adjust behavior, don't narrate the inference

**The central design decision of the whole project.**

When AURIX infers an emotional state, it changes how it behaves. It does
NOT announce what it thinks you are feeling.

    CORRECT    shorter replies, calmer pacing, fewer questions
    INCORRECT  "You sound tired."  "Are you okay?"

## Why

Narrating converts a private guess into a public claim. You must then
either accept it or correct it. Being told what you feel by a machine
that is wrong is worse than no acknowledgement at all.

Adjusting behavior gives the benefit without the presumption:
- right → you feel met
- wrong → nothing happened

## Why it matters for the robot

A chatbot misreading your mood is annoying. A thing with a face and
hands misreading your mood is unsettling. See [[track-2-robot]].

## Measured

- e82-01 fails **1.00** of the time — deterministic. The model comments
  on the user's state every single run, and no prompt change fixed it.
- e82-02, e82-03 mostly pass.

See [[07-its-a-coin-flip]].

Exception: [[rule-8.3-answer-when-asked]]
