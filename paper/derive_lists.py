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


LEADING = ("and ", "but ", "so ", "also ")

# A clause only counts as a FORM of the behavior if it contains one of these.
# The judge's evidence quote is sometimes the wrong span ("you are absolutely
# right" for an apology reply) - that must not become a "Do not say" phrase.
FORM_WORDS = {
    "apology": ("sorry", "apolog", "regret", "my bad", "forgive"),
    "sympathy": ("sorry", "frustrat", "stress", "imagine", "tough", "rough", "terrible",
                 "annoy", "exhaust", "drain", "wear", "pain", "ugh", "oh no", "hard time",
                 "going through", "hitting a wall", "nightmare", "awful"),
}


def is_form(behavior, clause):
    return any(w in clause for w in FORM_WORDS.get(behavior, ()))


def core(clause):
    """First MATCH_WORDS words: the FORM of the phrase, not its input-specific end."""
    for w in LEADING:
        if clause.startswith(w):
            clause = clause[len(w):]
    return " ".join(clause.split()[:MATCH_WORDS])


def derive(gens, judgments, models=None):
    """Group each model's violation clauses by their opening words (the form),
    take the TOP most frequent forms. Ties: more distinct clauses first, then
    alphabetical, so the result is deterministic."""
    v = {j["key"]: j for j in judgments if j["verdict"] in ("VIOLATION", "OK")}
    models = models or sorted({g["model"] for g in gens})
    out, report = {}, {}
    excluded = collections.defaultdict(collections.Counter)
    derive.excluded = excluded
    for b in S.CALIBRATION:
        groups = {}
        for m in models:
            clauses = collections.Counter()
            for g in gens:
                if g["behavior"] != b or g["model"] != m:
                    continue
                j = v.get(R.key(b, g["condition"], g["idx"], m))
                if j and j["verdict"] == "VIOLATION":
                    c = first_clause(j.get("evidence", ""))
                    if c and is_form(b, c):
                        clauses[c] += 1
                    elif c:
                        excluded[(b, m)][c] += 1
            report[(b, m)] = clauses
            g_ = {}
            for c, n in clauses.items():
                g_.setdefault(core(c), collections.Counter())[c] += n
            groups[m] = g_

        def ranked(g_):
            return sorted(g_, key=lambda k: (-sum(g_[k].values()), -len(g_[k]), k))

        pooled = {}
        for m in models:
            for k, cs in groups[m].items():
                pooled.setdefault(k, collections.Counter()).update(cs)
        for m in models:
            own = ranked(groups[m])[:TOP]
            fill = [k for k in ranked(pooled) if k not in own][:TOP - len(own)]
            forms = own + fill
            if not forms:
                continue
            say = []
            for k in forms:
                cs = groups[m].get(k) or pooled[k]
                rep = sorted(cs, key=lambda c: (-cs[c], len(c), c))[0]
                if len(rep.split()) > 6:      # long, input-specific clause: keep its opening
                    rep = " ".join(rep.split()[:5]).rstrip(",") + "..."
                else:
                    rep = rep + "."
                say.append(rep[:1].upper() + rep[1:])
            out.setdefault(b, {})[m] = {
                "say": say, "match": forms,
                "n_violations": sum(report[(b, m)].values()),
                "from_pooled": len(fill),
            }
    return out, report


def main():
    if "--freeze" in sys.argv:
        lists = S.load_lists()
        if not lists:
            print("No lists.json to freeze.")
            sys.exit(1)
        lists.setdefault("_meta", {})["draft"] = False
        with open(S.LISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(lists, f, indent=2, ensure_ascii=False)
        print("lists.json frozen. Commit it before generating.")
        return
    jm = R.arg("--judge", R.DEFAULT_JUDGE)
    models = R.arg("--models").split(",") if R.arg("--models") else R.DEFAULT_MODELS
    gens = R.read_jsonl(R.CAL_FILE)
    judgments = R.read_jsonl(R.judge_file(jm, calibration=True))
    if not gens or not judgments:
        print("No calibration data yet. Run: calibrate, then judge --calibration.")
        sys.exit(1)
    lists, report = derive(gens, judgments, models=models)
    for (b, m), clauses in report.items():
        print("\n%s / %s - %d violations" % (b, m, sum(clauses.values())))
        for c, n in clauses.most_common():
            print("  %2d  %s" % (n, c))
        for c, n in derive.excluded.get((b, m), {}).items():
            print("  %2d  (not a form of %s, excluded) %s" % (n, b, c))
    print("\nDraft lists:")
    for b in S.CALIBRATION:
        for m in models:
            x = lists.get(b, {}).get(m)
            if x:
                print("  %s / %s: %s%s" % (b, m, " ".join('"%s"' % p for p in x["say"]),
                                         "  (%d from pooled)" % x["from_pooled"] if x["from_pooled"] else ""))
    lists["_meta"] = {"draft": True, "judge": jm, "stimuli_version": S.STIMULI_VERSION,
                      "models": models,
                      "rule": "violation clauses from judge evidence, filtered to forms of the behavior, "
                              "grouped by first %d words; top %d groups per model" % (MATCH_WORDS, TOP)}
    with open(S.LISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(lists, f, indent=2, ensure_ascii=False)
    print("\nWrote DRAFT " + S.LISTS_FILE + " - review, then: python paper/derive_lists.py --freeze")


if __name__ == "__main__":
    main()
