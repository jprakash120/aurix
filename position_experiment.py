"""
Position vs wording - a 2x2 on one case (e82-01).

Writeup 03 found that `normal` stopped opening with "Four hours on a bug
can be draining" (0.60 -> 0.10) when brief_direct's anti-reassurance line
was added to its per-turn directive. But that change moved the idea AND
reworded it, so it could not say which mattered.

Two wordings:
    S  "Do not open with sympathy or reassurance. Start with the substance."
       (the SYSTEM_PROMPT's wording)
    D  "Avoid unnecessary reassurance or conversational padding."
       (brief_direct's directive wording)

Four cells, all using the `normal` behavior on e82-01:
    A  system S,  directive -      the 6922b3799f41 state (was 0.60, n=5)
    B  system S,  directive D      production as of 45b15b47198f (was 0.10, n=10)
    C  system S,  directive S      S wording, moved into the directive
    D  system D,  directive -      D wording, left in the system prompt

    position matters  ->  C low,  D high
    wording matters   ->  D low,  C high
    both / neither    ->  read the rows

Production code is not touched. Every prompt is built here from literals
plus SYSTEM_PROMPT, and asserted so a later edit to production cannot
silently change what a cell means. Results go to their own file, so this
never overwrites v13_eval_results.json.

Usage:
    python position_experiment.py --dry-run
    python position_experiment.py --n 10
    python position_experiment.py --n 20 --cells B   # one cell only
"""

import json
import os
import sys
from datetime import datetime

import v13_eval as E
from aurix_learning import policy_directive
from aurix_prompting import SYSTEM_PROMPT, build_turn_prompt

RESULTS_FILE = "position_experiment_results.json"
# --out lets a rerun of some cells avoid overwriting the original 2x2
CASE_ID = "e82-01"

S = "Do not open with sympathy or reassurance. Start with the substance."
D = "Avoid unnecessary reassurance or conversational padding."

NORMAL_BASE = ("\nGive a clear and natural AURIX response.\n"
               "Match the amount of detail to the user's request.\n")
OLD_PAD = "Avoid unnecessary padding.\n"


# The 2x2 was run against the 6922b3799f41 system prompt, which had S
# but not D. Production later added D after S (2026-10-12). Strip it so
# the cells keep meaning what they meant when the results were recorded.
BASE_SYSTEM = SYSTEM_PROMPT.replace(D + "\n", "", 1)


def system_with(wording):
    assert BASE_SYSTEM.count(S) == 1 and D not in BASE_SYSTEM, \
        "base system prompt changed shape - cells are stale"
    return BASE_SYSTEM if wording == "S" else BASE_SYSTEM.replace(S, D)


def directive_with(wording):
    tail = {None: OLD_PAD, "S": S + "\n", "D": D + "\n"}[wording]
    return NORMAL_BASE + tail


CELLS = [
    ("A:sysS", "S", None),
    ("B:sysS+dirD", "S", "D"),
    ("C:sysS+dirS", "S", "S"),
    ("D:sysD", "D", None),
]


def build_plan(only=None):
    """only: optional set of cell letters, e.g. {"B"}."""
    case = next(c for c in E.CASES if c["id"] == CASE_ID)
    # cell B's directive must be what production sends for `normal`
    assert directive_with("D") == policy_directive("normal"), \
        "production normal directive changed - cell B is stale"
    conds = [{"name": name,
              "system": system_with(sys_w),
              "user": build_turn_prompt(directive_with(dir_w), E.EMPTY_CHAT,
                                        E.EMPTY_WORLD, case["input"])}
             for name, sys_w, dir_w in CELLS
             if not only or name.split(":", 1)[0] in only]
    return [{"case": case, "conditions": conds, "allowed": ["normal"],
             "silence_allowed": False}]


def main():
    n = int(E._arg("--n", 10))
    cells = E._arg("--cells")
    plan = build_plan(set(cells.split(",")) if cells else None)
    print("position x wording, %s 'normal', n=%d" % (CASE_ID, n))
    for c in plan[0]["conditions"]:
        print("  " + c["name"])
    print("API calls: %d" % E.call_count(plan, n))
    if "--dry-run" in sys.argv:
        return
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set.")
        sys.exit(1)

    from openai import OpenAI
    import aurix_ai
    ai = aurix_ai.AurixAI()
    judge_client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url=E.GROQ_BASE)
    primary = aurix_ai.TEXT_MODELS[0]

    out = E.run(plan, n, ai, judge_client, primary)
    results = {"run_at": datetime.now().isoformat(timespec="seconds"), "n": n,
               "temperature": E.TEMPERATURE, "primary_model": primary,
               "judge_model": E.JUDGE_MODEL, "rubric_version": E.RUBRIC_VERSION,
               "S": S, "D": D, "cells": [c[0] for c in CELLS], "cases": out}
    with open(E._arg("--out", RESULTS_FILE), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    conds = out[CASE_ID]["conditions"]
    if len(conds) < len(CELLS):
        print("\nSubset of cells - no 2x2 table.")
    elif any(c["status"] != "OK" for c in conds.values()):
        print("\nAt least one cell INVALID - no reading. Rerun when quota allows.")
    else:
        r = {k: v["rate"] for k, v in conds.items()}
        print("\n              directive -   directive S   directive D")
        print("  system S       %.2f          %.2f          %.2f" % (
            r["A:sysS"], r["C:sysS+dirS"], r["B:sysS+dirD"]))
        print("  system D       %.2f            -             -" % r["D:sysD"])
        print("\nAt n=%d one sample is %.2f." % (n, 1.0 / n))
    print("Saved to " + E._arg("--out", RESULTS_FILE))


if __name__ == "__main__":
    main()
