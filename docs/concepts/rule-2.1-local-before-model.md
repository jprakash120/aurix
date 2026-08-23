# Rule 2.1 — local before model

If the machine can answer with certainty, the machine answers. Never
spend a model call on a fact the OS already knows.

    always local   time, date, opening apps, files, memory
    always model   explanations, summarization, open questions

## Why it is a correctness rule first

Local answers are correct, instant, and free. Model answers for these
are slower, cost quota, and can be **wrong** — see [[rule-4.1-honesty]].

## Enforced

`route_command()` in `aurix_core.py`. Tested — "what time is it" can
never reach the model again.

    route_command("what time is it")      → "time"   (local)
    route_command("read file notes.txt")  → "file"   (local)
    route_command("explain transformers") → "model"  (API)
