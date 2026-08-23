# Contamination

**When the eval hands the answer to the thing it is testing.**

## Two directions, both happened

**Into the graded model.** The harness sent the whole spec as the system
prompt. The spec contained exemplar responses. The model copied one
verbatim and scored 2/2.

**Into the judge.** The rule text included the observed failure
("replied with a numbered 3-option questionnaire"). The judge was told
what to penalize instead of deciding from the rule.

## The tell

A passing score that looks too clean. The exemplar appeared word for
word in the output.

## Prevention

- Never send the spec as a system prompt if it contains examples
- Give the judge the rule, not the failure history
- Be suspicious of high scores you cannot explain

## The general principle

> A passing score you cannot explain is a bug report.

Related: [[llm-as-judge]] · [[04-testing-the-untestable]]
