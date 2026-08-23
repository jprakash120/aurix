# Finding: persona instructions cause behavioral failures

**A style instruction produced a factual failure mode.**

## Observed

Prompt line: `Fast, clear, confident, and practical.`

Output, asked for laptop battery percentage with no hardware access:

> Battery level: 87%.

Invented. Specific. No hedge. Also:

> ANALYSIS COMPLETE. NO AUDITORY STRESS INDICATORS DETECTED IN USER INPUT.

...in response to **typed text**. There was no audio.

## Related: the robot-cop failure

Prompt line: `Reply like an intelligent robot assistant, not a normal chatbot.`

Output to unclear input:

> INPUT UNRECOGNIZED. PLEASE RESTATE QUERY.

Status announcements instead of a clarifying question. A worse response
to a person than the thing it replaced.

## Status: hypothesis NOT confirmed

The A/B test replacing "confident" with "honest about uncertainty" did
**not** cleanly fix it. See [[07-its-a-coin-flip]] — differences were
within noise at n=5.

What is confirmed: the failures are real and reproducible at some rate.
What is not: that "confident" is the cause.

## Open

- Does removing "robot assistant" fix the announcement style?
- Is e82-01 (1.00 failure rate) caused by persona or by something else?
