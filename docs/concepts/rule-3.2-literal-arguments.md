# Rule 3.2 — arguments can be literal

Filenames and folder names must survive normalization exactly.
`notes.txt` must never become `notestxt`.

## The tension with 3.1

- **3.1** Spoken commands are fuzzy. Forgive typos and punctuation.
- **3.2** Arguments are literal. Preserve exactly.

**3.3** resolves it: fuzzy normalization on the command *verb*, literal
handling on the *argument*. Never one regex for both.

## Enforced

`normalize_command()` vs `raw_command()`. Five regression tests.

Origin: [[02-the-first-bug]]
