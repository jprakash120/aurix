# 2. The first bug

**2026-08-02.** Typed `read file aurix_memory.txt`. Got back:

> I could not find the file aurix_memorytxt.

The dot vanished.

## Cause

One regex served two purposes:

    text = re.sub(r"[^\w\s]", "", text)   # strip punctuation

Correct for spoken commands — "open calculator!" should still match.
Destructive for filenames — `notes.txt` becomes `notestxt`.

## The tension

- Spoken commands are **fuzzy**. Forgive typos and punctuation.
- Filename arguments are **literal**. Preserve exactly.

One function cannot do both. Fixed by splitting: `normalize_command()`
for verbs, `raw_command()` for arguments.

Became [[rule-3.2-literal-arguments]] in the spec.

## Why it mattered

Nothing crashed. No stack trace. The code did exactly what it was told —
it was just wrong about what the user meant.

That is the whole subject of model behavior work: not "does it error"
but "does it do the right thing."

→ next: [[03-writing-the-spec]]
