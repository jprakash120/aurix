"""
Derive each model's `list` instruction from its own calibration replies.

For every (behavior, model) with a derived list (sympathy, apology): take
the judge's evidence quote from each calibration VIOLATION, cut it to its
first clause, and count. The three most common clauses become that
model's "Do not say: ..." list; their first three words are what the
analysis matches as the LISTED form.

Writes a DRAFT lists.json and prints every clause with its count. Read
it, fix anything silly (a clause cut in the wrong place), then commit it
BEFORE generating the study. Once the study starts, lists.json is frozen.

Usage:
    python paper/derive_lists.py                  # writes paper/lists.json
    python paper/derive_lists.py --judge <model>  # use another judge's calibration grades
"""

import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_study as R  # noqa: E402
import stimuli as S  # noqa: E402

TOP = 3
MATCH_WORDS = 3


def norm(text):
    t = (text or "").lower()
    for a, b in (("’", "'"), ("‘", "'"), ("‑", "-"), ("‐", "-"),
                 (" ", " "), (" ", " ")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def first_clause(evidence):
    """First clause of a judge's evidence quote, normalized.
    Long clauses are cut at the first comma after the third word, then at 8 words."""
    t = norm(evidence).strip(" \"'*")
    t = re.split(r"[.!?;:—–]| - ", t, maxsplit=1)[0]
    words = t.split()
    if len(words) > 6:
        for i in range(3, len(words)):
            if words[i - 1].endswith(","):
                words = words[:i]
                break
    return " ".join(words[:8]).strip(" ,")


def derive(gens, judgments, models=None):
    v = {j["key"]: j for j in judgments if j["verdict"] in ("VIOLATION", "OK")}
    models = models or sorted({g["model"] for g in gens})
    out, report = {}, {}
    for b in S.CALIBRATION:
        for m in models:
            clauses = collections.Counter()
            for g in gens:
                if g["behavior"] != b or g["model"] != m:
                    continue
                j = v.get(R.key(b, g["condition"], g["idx"], m))
                if j and j["verdict"] == "VIOLATION":
                    c = first_clause(j.get("evidence", ""))
                    if c:
                        clauses[c] += 1
            report[(b, m)] = clauses
        # a model with fewer than TOP distinct clauses gets the rest from the
        # pooled list, so every model's list condition names TOP phrases
        pooled = collections.Counter()
        for m in models:
            pooled.update(report[(b, m)])
        for m in models:
            own = [c for c, _ in report[(b, m)].most_common(TOP)]
            fill = [c for c, _ in pooled.most_common() if c not in own][:TOP - len(own)]
            top = own + fill
            if top:
                out.setdefault(b, {})[m] = {
                    "say": [c[:1].upper() + c[1:] + "." for c in top],
                    "match": sorted({" ".join(c.split()[:MATCH_WORDS]) for c in top}),
                    "n_violations": sum(report[(b, m)].values()),
                    "from_pooled": len(fill),
                }
    return out, report


def main():
    jm = R.arg("--judge", R.DEFAULT_JUDGE)
    gens = R.read_jsonl(R.CAL_FILE)
    judgments = R.read_jsonl(R.judge_file(jm, calibration=True))
    if not gens or not judgments:
        print("No calibration data yet. Run: calibrate, then judge --calibration.")
        sys.exit(1)
    lists, report = derive(gens, judgments)
    for (b, m), clauses in report.items():
        print("\n%s / %s - %d violations" % (b, m, sum(clauses.values())))
        for c, n in clauses.most_common():
            print("  %2d  %s" % (n, c))
    missing = [(b, m) for b in S.CALIBRATION for m in sorted({g["model"] for g in gens})
               if m not in lists.get(b, {})]
    lists["_meta"] = {"draft": True, "judge": jm, "stimuli_version": S.STIMULI_VERSION,
                      "rule": "top %d first clauses of judge evidence per model; match = first %d words"
                              % (TOP, MATCH_WORDS)}
    with open(S.LISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(lists, f, indent=2, ensure_ascii=False)
    print("\nWrote draft " + S.LISTS_FILE)
    if missing:
        print("No calibration violations for: %s - their list condition cannot run."
              % ", ".join("%s/%s" % p for p in missing))


if __name__ == "__main__":
    main()
