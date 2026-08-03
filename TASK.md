# AURIX — Standing Rules for the Agent

Read this before every change.

## Project goal
AURIX is a voice AI assistant. Laptop software first, small hardware device later.
Every design choice should keep the hardware path open.

## Architecture rules

1. **All pure logic goes in `aurix_core.py`.**
   No `winsound`, no `win32com`, no `sounddevice`, no API calls, no `input()`,
   no `while True` in that file. It must import cleanly on Linux.
   This is what makes the code testable and what will later port to a device.

2. **Platform-specific code stays in the runner file** (`aurix_v091.py`).
   When AURIX moves to hardware, only the runner gets rewritten. Core survives.

3. **Never break existing tests.** If a test fails, fix the code, not the test —
   unless the test itself encodes wrong behavior, and then say so explicitly.

4. **Every new behavior needs a test** in `test_aurix_core.py`.

5. **Every bug found becomes a regression test** before it is fixed.

## Behavior rules (the AURIX spec, v0.1)

- **Filenames are literal.** Never normalize, lowercase-strip, or remove
  punctuation from a filename argument. The `.txt` must survive.
- **Spoken commands are fuzzy.** Typos and punctuation should be forgiven
  ("wat time is it" → "what time is it").
- **Local before AI.** Time, date, opening apps, folders, and files are handled
  locally. Never spend an API call on something the laptop already knows.
- **Fail loud, not silent.** If a file is missing, say which file and why.
  Never pretend an action succeeded.
- **Destructive actions need confirmation.** Deleting or overwriting anything
  must ask first. Creating is fine without asking.

## Known constraints
- Gemini free tier: keep API calls minimal, batch where possible.
- Windows 11, Python venv at `.venv`.
- Voice output is Windows SAPI via pywin32.
