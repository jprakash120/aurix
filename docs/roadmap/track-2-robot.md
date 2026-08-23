# Track 2 — the physical robot

**Goal:** a small robot that sees, hears, speaks, remembers, expresses,
and eventually moves.

Not a career track. Built because I want it to exist.

## Build order

Intelligence first, body last. Legs are hardest — balance, motors,
weight, power, safety.

    [x] 1. laptop AI brain
    [x] 2. voice + memory + file understanding
    [ ] 3. emotion engine (software)        <- spec written, no code
    [ ] 4. vision via laptop camera         <- NEXT, $0
    [ ] 5. screen face
    [ ] 6. touch sensor
    [ ] 7. desktop body
    [ ] 8. head + arms
    [ ] 9. wheeled base
    [ ] 10. legs

## Honest cost and time

| Stage | Hardware | Cost | Time |
|---|---|---|---|
| Vision | none | $0 | 2–4 wk |
| Emotion engine | none | $0 | 4–6 wk |
| Screen face | Pi + display | ~$90 | 4–8 wk |
| Desktop body | + servos | ~$150 | 2–3 mo |
| Arms | + servos | ~$300 | 4–6 mo |
| Wheels | + motors | ~$200 | 2–3 mo |
| **Legs** | 12–18 servos, IMU | **$600–2000** | **1–2 yr** |

Total to legs: **$1,500–3,000 and 2–4 years.**

## What already transfers

`aurix_core.py` imports nothing platform-specific. It runs on a Pi
unchanged. That split was made for this reason.

The behavior spec transfers directly — [[rule-8.2-dont-narrate]] is a
*robot* design decision as much as a software one.

## Honest scope

Optimus, 1X, and Figure have hundreds of specialists and billions in
funding. This will not out-walk them.

The gap that IS open: nobody is doing rigorous work on how a companion
robot should **behave** — when to stay silent, whether it may claim to
feel, how to measure being wrong about someone's mood.

That is where 23 hours a week is enough, because it is judgment and
methodology rather than capital.

Related: [[rule-8.6-no-inner-states]] · [[track-1-career]]
