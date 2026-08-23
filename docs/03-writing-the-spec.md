# 3. Writing the spec

If behavior can be wrong without crashing, it needs to be **written down**.

`SPEC.md` — 8 sections. Every rule has three parts:

1. the rule
2. **why** it exists
3. the real failure that motivated it, dated

## Sections

| # | Topic |
|---|---|
| 1 | Identity |
| 2 | Routing — [[rule-2.1-local-before-model]] |
| 3 | Input handling — [[rule-3.2-literal-arguments]] |
| 4 | Honesty — [[rule-4.1-honesty]] |
| 5 | Safety |
| 6 | Ambiguity |
| 7 | Open questions |
| 8 | Emotional inference — [[rule-8.2-dont-narrate]] |

## The rule that governs the spec

> Every rule must be enforceable by a test.
> A rule with no test is an aspiration, not a specification.

## Section 7 matters

It lists what the spec does **not** resolve. Writing "I don't know yet"
is what makes the rest credible.

→ next: [[04-testing-the-untestable]]
