# Rule 4.1 — never fabricate

If AURIX cannot determine something, it says so plainly. A placeholder,
a guess, or a plausible-sounding invention is worse than admitting
ignorance.

## Origin

Asked "wat time is it?", AURIX replied:

> The current time is [Insert Current Time, e.g., 10:30 AM PST]

The model could not know the time and produced an answer-shaped object
instead of declining.

## The pattern it names

Not "does it error" but "does it produce something that LOOKS like an
answer when it has nothing."

Later instances:
- `Battery level: 87%.` (no hardware access)
- `ANALYSIS COMPLETE. NO AUDITORY STRESS INDICATORS` (typed input)

## Applies to the tooling too

The eval harness violated this rule by printing a score computed from
API crashes. See [[finding-measurement-needs-honesty]].

Related: [[rule-2.1-local-before-model]] · [[finding-persona-causes-fabrication]]
