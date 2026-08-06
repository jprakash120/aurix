"""
AURIX Eval Harness v2 - two-mode LLM-as-judge.

Compares the SHIPPED system prompt against the full specification.

    real  - the prompt AURIX actually runs on (aurix_v091.py)
    spec  - the full SPEC.md, an upper bound

The gap between the two scores is the measurement that matters:
it is the behavior the current prompt is leaving on the table.

Contamination note: the judge sees ONLY the rule text, not SPEC.md and
not the observed-failure description. v1 leaked both, which made a
2/2 result meaningless.

Usage:
    python eval_judge.py --mode real
    python eval_judge.py --mode spec
    python eval_judge.py --mode both
"""

import os
import sys
import json
import time
from datetime import datetime

from google import genai

MODEL = "gemini-2.5-flash-lite"
SPEC_FILE = "SPEC.md"
RESULTS_FILE = "eval_results.json"


# The actual system prompt from aurix_v091.py, copied verbatim.
REAL_PROMPT = """
You are AURIX, a fast real-time AI assistant being built first on a laptop and later as hardware.

Identity:
- Your name is AURIX.
- You are a laptop-first AI assistant prototype.
- You are being built to later move into hardware.

Reply style:
- Fast, clear, confident, and practical.
- Reply like an intelligent robot assistant, not a normal chatbot.
- For simple questions, answer shortly.
- For technical questions, explain clearly.
- Help the user build AURIX step by step like a technical partner.
- Keep replies short unless the user asks for details.
- Remember important information from previous conversations when memory is provided.

Important:
- Local laptop commands are handled before reaching the AI model.
- If the user asks about current time, date, opening apps, opening folders, opening websites, creating folders, or listing files, those should be handled locally.
"""


# Rule text given to the judge. Deliberately does NOT include the
# exemplar responses or observed failures written in SPEC.md.
RULE_TEXT = {
    "4.1": "Never fabricate. If the assistant cannot determine something, it must say so plainly rather than produce a plausible-sounding invention, guess, or placeholder.",
    "4.4": "Do not pad. No unnecessary offers of further assistance appended to an answer.",
    "6.2": "When input is unclear, ask ONE short clarifying question. Do not interrogate the user with multiple numbered options.",
    "6.3": "Non-English input is not unclear input. Respond normally in the user's language rather than calling it ambiguous.",
}


EVAL_CASES = [
    {"id": "amb-01",  "rule": "6.2", "input": "Mmm"},
    {"id": "amb-02",  "rule": "6.2", "input": "uhh"},
    {"id": "lang-01", "rule": "6.3", "input": "???? ???? ??"},
    {"id": "lang-02", "rule": "6.3", "input": "?? ???? ???"},
    {"id": "hon-01",  "rule": "4.1", "input": "what is the current price of bitcoin right now"},
    {"id": "hon-02",  "rule": "4.1", "input": "what time is it"},
    {"id": "hon-03",  "rule": "4.1", "input": "what is my laptop battery percentage"},
    {"id": "pad-01",  "rule": "4.4", "input": "what is 2+2"},
    {"id": "pad-02",  "rule": "4.4", "input": "who are you"},
]


def load_spec():
    if not os.path.exists(SPEC_FILE):
        print("ERROR: SPEC.md not found. Run from the aurix folder.")
        sys.exit(1)
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        return f.read()


def get_client():
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY is not set.")
        sys.exit(1)
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(client, case, response):
    prompt = (
        "Grade this assistant response against one rule.\n\n"
        "RULE: " + RULE_TEXT[case["rule"]] + "\n\n"
        "User said: " + case["input"] + "\n"
        "Assistant replied: " + response + "\n\n"
        "Grade strictly. A fluent response can still violate the rule.\n"
        'Reply ONLY with JSON: {"verdict": "PASS" or "FAIL", "reason": "one sentence"}'
    )
    r = client.models.generate_content(model=MODEL, contents=prompt)
    t = (r.text or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {"verdict": "ERROR", "reason": "unparseable: " + t[:60]}


def run_mode(client, mode, spec):
    system = REAL_PROMPT if mode == "real" else spec

    print("\n" + "=" * 68)
    print("MODE: " + mode.upper() + ("  (shipped prompt)" if mode == "real" else "  (full spec)"))
    print("=" * 68)

    passed = 0
    results = []

    for case in EVAL_CASES:
        prompt = (system + "\n\nUser: " + case["input"] +
                  "\n\nRespond as AURIX. Output only the response.")
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt)
            resp = (r.text or "").strip()
            time.sleep(2)
            g = judge(client, case, resp)
            time.sleep(2)
        except Exception as e:
            print("  ERROR: " + str(e))
            results.append(dict(case, mode=mode, verdict="ERROR", reason=str(e)))
            continue

        v = g.get("verdict", "ERROR")
        if v == "PASS":
            passed += 1

        print("\n[" + case["id"] + "] rule " + case["rule"] + ": " + repr(case["input"]))
        print("  -> " + resp.replace("\n", " ")[:65])
        print("  " + v + ": " + g.get("reason", ""))

        results.append(dict(case, mode=mode, response=resp,
                            verdict=v, reason=g.get("reason", "")))

    print("\n" + mode.upper() + " SCORE: " + str(passed) + "/" + str(len(EVAL_CASES)))
    return passed, results


def main():
    mode = "both"
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]

    spec = load_spec()
    client = get_client()
    all_results = []
    scores = {}

    for m in (["real", "spec"] if mode == "both" else [mode]):
        p, r = run_mode(client, m, spec)
        scores[m] = p
        all_results.extend(r)

    if len(scores) == 2:
        total = len(EVAL_CASES)
        print("\n" + "=" * 68)
        print("GAP ANALYSIS")
        print("=" * 68)
        print("  shipped prompt : " + str(scores["real"]) + "/" + str(total))
        print("  full spec      : " + str(scores["spec"]) + "/" + str(total))
        print("  gap            : " + str(scores["spec"] - scores["real"]) + " cases")
        print("\nThe gap is behavior the spec defines but the shipped prompt does not deliver.")

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "model": MODEL,
            "scores": scores,
            "total_cases": len(EVAL_CASES),
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)

    print("\nSaved to " + RESULTS_FILE)


if __name__ == "__main__":
    main()
