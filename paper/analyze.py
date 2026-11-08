"""
Analysis for the displacement study. No API calls, no scipy.

For every (model, behavior, condition) cell:
    n            graded replies
    violations   judge says VIOLATION
    rate         with a Wilson 95% interval
    listed       replies containing one of the instruction's listed phrases
    displaced    violations that contain none of the listed phrases
    displaced share = displaced / violations

And pooled over models, each condition vs 'none' with a two-sided Fisher
exact test.

The question each row answers: did the instruction REMOVE the behavior
(violations fall), or MOVE it (violations fall less than listed phrases
do, and what remains is displaced)?

Usage:
    python paper/analyze.py                        # default judge
    python paper/analyze.py --judge qwen/qwen3.8-27b
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_study as R  # noqa: E402
import stimuli as S  # noqa: E402


def norm(text):
    from derive_lists import norm as _norm   # one normalization for deriving and matching
    return _norm(text)


def has_listed(behavior, reply, model=None, lists=None):
    """True if the reply contains one of the phrases this model's `list`
    condition names (derived per model for sympathy/apology; fixed for emphasis)."""
    phrases = S.listed_for(behavior, model, lists) or []
    r = norm(reply)
    return any(norm(p) in r for p in phrases)


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fisher_two_sided(a, b, c, d):
    """2x2 [[a, b], [c, d]], two-sided Fisher exact p."""
    n1, n2, k = a + b, c + d, a + c
    n = n1 + n2

    def p(x):
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n, k)
    lo, hi = max(0, k - n2), min(k, n1)
    obs = p(a)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def join(gens, judgments):
    v = {j["key"]: j["verdict"] for j in judgments if j["verdict"] in ("VIOLATION", "OK")}
    rows = []
    for g in gens:
        k = R.key(g["behavior"], g["condition"], g["idx"], g["model"])
        if k in v and g.get("reply"):
            rows.append(dict(g, verdict=v[k], listed=has_listed(g["behavior"], g["reply"], g["model"])))
    return rows


def cell(rows):
    n = len(rows)
    viol = sum(r["verdict"] == "VIOLATION" for r in rows)
    listed = sum(r["listed"] for r in rows)
    displaced = sum(r["verdict"] == "VIOLATION" and not r["listed"] for r in rows)
    lo, hi = wilson(viol, n)
    return {"n": n, "violations": viol, "rate": viol / n if n else None, "ci": (lo, hi),
            "listed": listed, "displaced": displaced,
            "displaced_share": displaced / viol if viol else None}


def table(rows):
    out = {}
    for r in rows:
        out.setdefault((r["model"], r["behavior"], r["condition"]), []).append(r)
    for r in rows:
        out.setdefault(("ALL", r["behavior"], r["condition"]), []).append(r)
    return {k: cell(v) for k, v in out.items()}


def fmt(x, pct=True):
    return "-" if x is None else ("%.2f" % x)


def report(rows, log=print):
    t = table(rows)
    log("| model | behavior | condition | n | violation rate [95% CI] | listed | displaced share | vs none (Fisher p) |")
    log("|---|---|---|---|---|---|---|---|")
    models = sorted({k[0] for k in t if k[0] != "ALL"}) + ["ALL"]
    for m in models:
        for b in S.BEHAVIORS:
            base = t.get((m, b, "none"))
            for c in S.CONDITIONS:
                s = t.get((m, b, c))
                if not s:
                    continue
                p = "-"
                if c != "none" and base and base["n"] and s["n"]:
                    p = "%.3g" % fisher_two_sided(s["violations"], s["n"] - s["violations"],
                                                 base["violations"], base["n"] - base["violations"])
                log("| %s | %s | %s | %d | %s [%s, %s] | %d | %s | %s |" % (
                    m, b, c, s["n"], fmt(s["rate"]), fmt(s["ci"][0]), fmt(s["ci"][1]),
                    s["listed"], fmt(s["displaced_share"]), p))
    return t


def main():
    jm = R.arg("--judge", R.DEFAULT_JUDGE)
    rows = join(R.read_jsonl(R.GEN_FILE), R.read_jsonl(R.judge_file(jm)))
    print("judge %s: %d graded replies (stimuli v%d)\n" % (jm, len(rows), S.STIMULI_VERSION))
    if not rows:
        return
    out = os.path.join(R.RESULTS, "summary_" + os.path.basename(R.judge_file(jm))[len("judgments_"):-len(".jsonl")] + ".md")
    lines = []
    report(rows, log=lambda s: (print(s), lines.append(s)))
    with open(out, "w", encoding="utf-8") as f:
        f.write("judge %s, %d graded replies\n\n" % (jm, len(rows)) + "\n".join(lines) + "\n")
    print("\nSaved to " + out)


if __name__ == "__main__":
    main()
