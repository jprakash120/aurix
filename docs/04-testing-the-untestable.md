# 4. Testing the untestable

Some rules are testable with plain assertions:

    assert parse_file_command("read file notes.txt")[1] == "notes.txt"

45 of these exist. They run in 3 seconds and catch regressions forever.

## But most rules are not

- Was that reply too pushy?
- Did it pad the answer?
- Was that clarifying question appropriate?

No assertion answers these. There is no exact expected string.

## The technique: [[llm-as-judge]]

Send the response and the rule to a model. Ask it to grade.

    RULE: {the rule text}
    User said: {input}
    Assistant replied: {response}
    → PASS or FAIL, with a reason

## First result: 2/2 — and meaningless

The response was:

> Didn't catch that - what would you like to do?

That exact sentence was **in the spec**, as the example of a good reply.
The harness was sending the whole spec as the system prompt, so the
model copied the answer key.

See [[contamination]].

→ next: [[05-the-judge-was-wrong]]
