"""
Second-judge agreement check.

Every rate in this repo was graded by openai/gpt-oss-120b - the same model
that generated the replies. Anthropic's eval guidance recommends grading
with a different model. This script re-grades SAVED replies (no new
generation) with a second judge from a different model family, using the
identical rubric and prompt, and reports:

  - raw agreement and Cohen's kappa
  - the confusion matrix (which way the judges disagree)
  - every disagreement, with the reply text, for reading
  - each condition's rate under both judges, so you can see whether a
    finding (e.g. the 2x2 wording effect) survives a change of judge

All or nothing: the first failed judge call aborts and nothing is saved.

Usage:
    python judge_agreement.py --dry-run
    python judge_agreement.py                       # default files, default model
    python judge_agreement.py --model llama-3.3-70b-versatile --files a.json,b.json
"""

import json
import os
import sys
import time
from datetime import datetime

import v13_eval as E

DEFAULT_FILES = ["position_experiment_results.json", "position_2x2_interleaved.json"]
# llama-3.3-70b-versatile is in Groq's docs but returned 404 for this key
# (2026-10-14). Qwen3 is the only other general LLM family available.
DEFAULT_MODEL = "qwen/qwen3.8-27b"
OUT_FILE = "judge_agreement_results.json"


def gradeable(results):
    """(file-level) yield (case_id, case, condition, index, sample) for samples
    the primary judge actually graded."""
    p = results["primary_model"]
    for cid, c in results["cases"].items():
        case = {"id": cid, "rule": c["rule"], "input": c["input"]}
        for name, cond in c["conditions"].items():
            for i, s in enumerate(cond["samples"]):
                if s.get("model") == p and s["verdict"] in ("PASS", "FAIL"):
                    yield cid, case, name, i, s


def kappa(pairs):
    """Cohen's kappa for two binary raters. pairs: list of (a, b), 'PASS'/'FAIL'."""
    n = len(pairs)
    if n == 0:
        return None
    agree = sum(a == b for a, b in pairs) / n
    pa = sum(a == "FAIL" for a, _ in pairs) / n
    pb = sum(b == "FAIL" for _, b in pairs) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if expected == 1 else (agree - expected) / (1 - expected)


def summarize(rows):
    pairs = [(r["judge_a"], r["judge_b"]) for r in rows if r["judge_b"] in ("PASS", "FAIL")]
    conf = {"both_FAIL": 0, "both_PASS": 0, "A_FAIL_B_PASS": 0, "A_PASS_B_FAIL": 0}
    for a, b in pairs:
        key = ("both_" + a) if a == b else ("A_%s_B_%s" % (a, b))
        conf[key] += 1
    per_cond = {}
    for r in rows:
        k = r["file"] + " :: " + r["condition"]
        d = per_cond.setdefault(k, {"n": 0, "a_fail": 0, "b_fail": 0, "b_valid": 0})
        d["n"] += 1
        d["a_fail"] += r["judge_a"] == "FAIL"
        if r["judge_b"] in ("PASS", "FAIL"):
            d["b_valid"] += 1
            d["b_fail"] += r["judge_b"] == "FAIL"
    return {
        "n_pairs": len(pairs),
        "b_errors": sum(r["judge_b"] not in ("PASS", "FAIL") for r in rows),
        "agreement": (sum(a == b for a, b in pairs) / len(pairs)) if pairs else None,
        "kappa": kappa(pairs),
        "confusion": conf,
        "per_condition": per_cond,
    }


def run(files, client, model, sleep=E.SLEEP, log=print):
    rows = []
    todo = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            res = json.load(fh)
        todo += [(f,) + t for t in gradeable(res)]
    for k, (f, cid, case, name, i, s) in enumerate(todo):
        try:
            v, ev = E.judge(client, case, s["response"], model=model)
        except Exception as e:
            raise E.RegradeAborted(k, len(todo), str(e)[:160])
        rows.append({"file": f, "case": cid, "condition": name, "index": i,
                     "judge_a": s["verdict"], "judge_b": v, "evidence_b": ev,
                     "evidence_a": s.get("evidence", ""), "response": s["response"]})
        time.sleep(sleep)
    return rows


def report(summary, rows, model_a, model_b, log=print):
    log("\nJudge A: %s   Judge B: %s" % (model_a, model_b))
    log("pairs: %d   judge B parse errors: %d" % (summary["n_pairs"], summary["b_errors"]))
    if summary["agreement"] is not None:
        log("agreement %.2f   Cohen's kappa %.2f" % (summary["agreement"], summary["kappa"]))
    c = summary["confusion"]
    log("\n                 B: FAIL   B: PASS")
    log("  A: FAIL        %5d     %5d" % (c["both_FAIL"], c["A_FAIL_B_PASS"]))
    log("  A: PASS        %5d     %5d" % (c["A_PASS_B_FAIL"], c["both_PASS"]))
    log("\nRate per condition (A = original judge, B = second judge):")
    for k, d in summary["per_condition"].items():
        b = "%.2f" % (d["b_fail"] / d["b_valid"]) if d["b_valid"] else " n/a"
        log("  %-58s A %.2f  B %s  (n=%d)" % (k, d["a_fail"] / d["n"], b, d["n"]))
    dis = [r for r in rows if r["judge_b"] in ("PASS", "FAIL") and r["judge_a"] != r["judge_b"]]
    log("\nDisagreements (%d):" % len(dis))
    for r in dis:
        log("  A %s / B %s  %-14s %r" % (r["judge_a"], r["judge_b"], r["condition"][:14],
                                         r["response"][:80]))


def main():
    files = E._arg("--files")
    files = files.split(",") if files else DEFAULT_FILES
    model = E._arg("--model", DEFAULT_MODEL)
    total = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            total += sum(1 for _ in gradeable(json.load(fh)))
    print("Second judge %s on %d saved replies from %s (judge calls only)."
          % (model, total, ", ".join(files)))
    if model == E.JUDGE_MODEL:
        print("ERROR: second judge must differ from the original judge.")
        sys.exit(1)
    if "--dry-run" in sys.argv:
        return
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url=E.GROQ_BASE)
    try:
        rows = run(files, client, model)
    except E.RegradeAborted as e:
        print("\nABORTED - %s\nNothing saved." % e)
        sys.exit(1)
    summary = summarize(rows)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump({"run_at": datetime.now().isoformat(timespec="seconds"),
                   "judge_a": E.JUDGE_MODEL, "judge_b": model,
                   "rubric_version": E.RUBRIC_VERSION, "files": files,
                   "summary": summary, "rows": rows}, fh, indent=2, ensure_ascii=False)
    report(summary, rows, E.JUDGE_MODEL, model)
    print("\nSaved to " + OUT_FILE)


if __name__ == "__main__":
    main()
