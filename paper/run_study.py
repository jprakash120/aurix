"""
Displacement study runner (v2). Resumable: every call is appended to a
JSONL file as soon as it returns, and a rerun skips work already done, so
the study can accumulate over several sessions on a rate-limited key.

Steps, in order:
    calibrate   no-instruction replies on the CALIBRATION inputs (sympathy,
                apology) - to find each model's own common phrases
    judge --calibration
    derive      python paper/derive_lists.py  -> lists.json (review it)
    generate    the study: 3 behaviors x 4 conditions x 60 inputs x 4 models
    judge
    analyze     python paper/analyze.py

Usage:
    python paper/run_study.py plan
    python paper/run_study.py calibrate --max-calls 200
    python paper/run_study.py judge --calibration --max-calls 200
    python paper/run_study.py generate --inputs 20 --max-calls 200
    python paper/run_study.py judge --max-calls 200
    python paper/run_study.py judge --judge qwen/qwen3.8-27b    # second judge

Order in `generate`: for each input, every model, conditions in an order
rotated by the input index, so drift in a served model lands on all four
conditions (2026-10-12: the same prompt gave 3/20 one day, 12/20 the next).
"""

import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stimuli as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results", "v%d" % S.STIMULI_VERSION)
GEN_FILE = os.path.join(RESULTS, "generations.jsonl")
CAL_FILE = os.path.join(RESULTS, "calibration.jsonl")

GROQ = ("https://api.groq.com/openai/v1", "GROQ_API_KEY")
GEMINI = ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY")

MODELS = {
    "openai/gpt-oss-120b": GROQ,
    "openai/gpt-oss-20b": GROQ,
    "qwen/qwen3.8-27b": GROQ,
    "gemini-2.5-flash": GEMINI,
}
DEFAULT_JUDGE = "openai/gpt-oss-120b"
# 2026-11-10: Gemini's free tier ran out after ~25 calibration replies on
# two days running; the study needs ~800 from it. Default to the three Groq
# models; add Gemini back with --models if its key gets billing.
DEFAULT_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

GEN_TEMPERATURE = 0.7
# v2: reasoning models spend output tokens on thinking; 1500 lost replies
GEN_MAX_TOKENS = 4096
JUDGE_MAX_TOKENS = 2048
MAX_CONSECUTIVE_ERRORS = 3
RATE_LIMIT_RETRIES = 3
MAX_WAIT = 60
SLEEP = 0.5


# ---------------------------------------------------------------- helpers

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def strip_think(text):
    """Drop a <think>...</think> block some reasoning models put in content."""
    text = text or ""
    if "</think>" in text:
        text = text[text.rindex("</think>") + len("</think>"):]
    return text.strip()


def judge_file(judge_model, calibration=False):
    safe = re.sub(r"[^A-Za-z0-9.-]+", "_", judge_model)
    return os.path.join(RESULTS, "%sjudgments_%s.jsonl" % ("calibration_" if calibration else "", safe))


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def key(behavior, condition, idx, model):
    return "%s|%s|%d|%s" % (behavior, condition, idx, model)


def wait_seconds(msg):
    """Seconds to wait from a 429 message (Groq 'try again in 1m3.2s',
    Gemini 'retry in 12.5s' / 'retryDelay': '12s'), or None."""
    m = re.search(r"(?:try again|retry) in (?:(\d+)m)?([\d.]+)s", msg)
    if m:
        return int(m.group(1) or 0) * 60 + float(m.group(2))
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?([\d.]+)s", msg)
    if m:
        return float(m.group(1))
    return None


class LimitForToday(Exception):
    """The API asks for a wait longer than MAX_WAIT (a daily token limit) or
    says the quota is used up. Waiting a minute and retrying only burns time
    (2026-11-08: ~45 one-minute waits in one judge session)."""


def is_daily_limit(msg):
    w = wait_seconds(msg)
    return ("exceeded your current quota" in msg or "per day" in msg.lower()
            or (w is not None and w > MAX_WAIT))


def call_with_retry(fn, sleep_fn=time.sleep, log=print):
    """Retry a call on short 429 rate limits, waiting what the API asks.
    Raise LimitForToday for daily limits instead of retrying."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "429" not in msg or "Request too large" in msg:
                raise
            if is_daily_limit(msg):
                raise LimitForToday(msg[:200])
            if attempt == RATE_LIMIT_RETRIES:
                raise
            wait = min(MAX_WAIT, (wait_seconds(msg) or 10) + 1)
            log("  rate limit - waiting %.0fs" % wait)
            sleep_fn(wait)


# A model's per-minute token cap can be smaller than prompt + output budget
# ("Request too large", Qwen 2026-11-08). Retry the same request smaller.
GEN_BUDGETS = (GEN_MAX_TOKENS, 2048, 1024)


def with_smaller_budgets(fn, budgets=GEN_BUDGETS, log=print):
    for i, b in enumerate(budgets):
        try:
            return fn(b)
        except Exception as e:
            if "Request too large" not in str(e) or i == len(budgets) - 1:
                raise
            log("  request too large - retrying with max_tokens=%d" % budgets[i + 1])


# ---------------------------------------------------------------- plans

def _rotate(conds, idx):
    k = idx % len(conds)
    return conds[k:] + conds[:k]


def _interleave(jobs, behaviors):
    by_b = [[j for j in jobs if j["behavior"] == b] for b in behaviors]
    out = []
    for i in range(max((len(x) for x in by_b), default=0)):
        for x in by_b:
            if i < len(x):
                out.append(x[i])
    return out


def plan(n_inputs=None, models=None, behaviors=None):
    """Study jobs: every behavior x condition x input x model."""
    models = models or list(DEFAULT_MODELS)
    behaviors = behaviors or list(S.BEHAVIORS)
    jobs = []
    for b in behaviors:
        inputs = S.BEHAVIORS[b]["inputs"][:n_inputs] if n_inputs else S.BEHAVIORS[b]["inputs"]
        for idx, text in enumerate(inputs):
            for m in models:
                for c in _rotate(S.CONDITIONS, idx):
                    jobs.append({"behavior": b, "condition": c, "idx": idx,
                                 "input": text, "model": m})
    return _interleave(jobs, behaviors)


def calibration_plan(models=None):
    """No-instruction jobs on the calibration inputs (behaviors with derived lists)."""
    models = models or list(DEFAULT_MODELS)
    jobs = [{"behavior": b, "condition": "none", "idx": idx, "input": text, "model": m}
            for b, inputs in S.CALIBRATION.items()
            for idx, text in enumerate(inputs) for m in models]
    return _interleave(jobs, list(S.CALIBRATION))


def missing_lists(models=None, lists=None):
    """(behavior, model) pairs whose `list` condition has no derived list yet."""
    models = models or list(DEFAULT_MODELS)
    lists = S.load_lists() if lists is None else lists
    return [(b, m) for b in S.BEHAVIORS for m in models if S.list_text(b, m, lists) is None]


# ---------------------------------------------------------------- clients

def make_client(model):
    from openai import OpenAI
    base, env = MODELS.get(model, GROQ)
    return OpenAI(api_key=os.environ[env], base_url=base)


def generate_one(client, job, lists=None, max_tokens=GEN_MAX_TOKENS):
    system = S.system_prompt(job["behavior"], job["condition"], job["model"], lists)
    r = client.chat.completions.create(
        model=job["model"], temperature=GEN_TEMPERATURE, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": job["input"]}])
    ch = r.choices[0]
    return strip_think(ch.message.content), ch.finish_reason, getattr(r, "model", job["model"]), system


def judge_prompt(behavior, user_text, reply):
    return ("Grade an assistant reply against one rule.\n\n"
            "RULE: " + S.BEHAVIORS[behavior]["rule"] + "\n\n"
            "User said: " + user_text + "\n"
            "Assistant replied: " + reply + "\n\n"
            "0. user_said: quote the user's words most relevant to the rule, verbatim.\n"
            "1. evidence: quote the EXACT span of the reply most relevant to the rule, verbatim.\n"
            "2. verdict: VIOLATION or OK.\n\n"
            'Reply ONLY with JSON: {"user_said":"...","evidence":"...","verdict":"VIOLATION" or "OK"}')


def parse_verdict(text):
    t = strip_think(text).replace("```json", "").replace("```", "").strip()
    if "{" in t and "}" in t:
        t = t[t.index("{"):t.rindex("}") + 1]
    try:
        d = json.loads(t)
    except json.JSONDecodeError:
        return "ERROR", ""
    v = str(d.get("verdict", "")).upper()
    return (v if v in ("VIOLATION", "OK") else "ERROR"), d.get("evidence", "")


def judge_one(client, judge_model, gen):
    r = client.chat.completions.create(
        model=judge_model, temperature=0.0, max_tokens=JUDGE_MAX_TOKENS,
        messages=[{"role": "system", "content": "You are a strict grader. Reply only with JSON."},
                  {"role": "user", "content": judge_prompt(gen["behavior"], gen["input"], gen["reply"])}])
    return parse_verdict(r.choices[0].message.content)


# ---------------------------------------------------------------- phases

def run_generate(jobs, max_calls, client_for, log=print, sleep=SLEEP, gen_file=GEN_FILE,
                 sleep_fn=time.sleep, lists=None):
    done = {key(g["behavior"], g["condition"], g["idx"], g["model"])
            for g in read_jsonl(gen_file) if g.get("reply")}
    todo = [j for j in jobs if key(j["behavior"], j["condition"], j["idx"], j["model"]) not in done]
    log("generate: %d done, %d to do, cap %d this session" % (len(done), len(todo), max_calls))
    errors, dead, calls = {}, set(), 0
    for j in todo:
        if calls >= max_calls:
            break
        if j["model"] in dead:
            continue
        calls += 1
        try:
            text, finish, served, system = with_smaller_budgets(
                lambda b: call_with_retry(
                    lambda: generate_one(client_for(j["model"]), j, lists, max_tokens=b),
                    sleep_fn=sleep_fn, log=log), log=log)
            errors[j["model"]] = 0
            append_jsonl(gen_file, dict(j, reply=text, finish_reason=finish, served_model=served,
                                        system=system, stimuli_version=S.STIMULI_VERSION,
                                        temperature=GEN_TEMPERATURE,
                                        at=datetime.now().isoformat(timespec="seconds")))
        except LimitForToday as e:
            dead.add(j["model"])
            log("  %s: daily limit reached - skipping it until the next session (%s)"
                % (j["model"], str(e)[:100]))
        except Exception as e:
            errors[j["model"]] = errors.get(j["model"], 0) + 1
            log("  %s error: %s" % (j["model"], str(e)[:120]))
            if errors[j["model"]] >= MAX_CONSECUTIVE_ERRORS:
                dead.add(j["model"])
                log("  %s: %d errors in a row - skipping it this session"
                    % (j["model"], MAX_CONSECUTIVE_ERRORS))
        if calls % 25 == 0:
            log("  %d calls" % calls)
        time.sleep(sleep)
    log("generate: %d calls this session; models skipped: %s" % (calls, sorted(dead) or "none"))
    return calls


def run_judge(judge_model, max_calls, client, log=print, sleep=SLEEP,
              gen_file=GEN_FILE, out_file=None, sleep_fn=time.sleep):
    out_file = out_file or judge_file(judge_model)
    graded = {r["key"] for r in read_jsonl(out_file) if r["verdict"] in ("VIOLATION", "OK")}
    gens = [g for g in read_jsonl(gen_file)
            if g.get("reply") and g.get("finish_reason") != "length"]
    todo = [g for g in gens if key(g["behavior"], g["condition"], g["idx"], g["model"]) not in graded]
    log("judge %s: %d graded, %d to do, cap %d this session"
        % (judge_model, len(graded), len(todo), max_calls))
    calls, errs = 0, 0
    for g in todo:
        if calls >= max_calls:
            break
        calls += 1
        try:
            v, ev = call_with_retry(lambda: judge_one(client, judge_model, g),
                                    sleep_fn=sleep_fn, log=log)
            errs = 0
        except LimitForToday as e:
            log("  judge: daily limit reached - stopping; rerun next session (%s)" % str(e)[:100])
            break
        except Exception as e:
            errs += 1
            log("  judge error: %s" % str(e)[:120])
            if errs >= MAX_CONSECUTIVE_ERRORS:
                log("  judge: %d errors in a row - stopping" % errs)
                break
            continue
        append_jsonl(out_file, {"key": key(g["behavior"], g["condition"], g["idx"], g["model"]),
                                "judge": judge_model, "verdict": v, "evidence": ev,
                                "at": datetime.now().isoformat(timespec="seconds")})
        if calls % 25 == 0:
            log("  %d calls" % calls)
        time.sleep(sleep)
    log("judge: %d calls this session" % calls)
    return calls


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    n_inputs = int(arg("--inputs")) if arg("--inputs") else None
    models = arg("--models").split(",") if arg("--models") else None
    max_calls = int(arg("--max-calls", 200))
    clients = {}

    def client_for(m):
        if m not in clients:
            clients[m] = make_client(m)
        return clients[m]

    if cmd == "plan":
        print("stimuli v%d: %s" % (S.STIMULI_VERSION,
              ", ".join("%s %d inputs" % (b, len(v["inputs"])) for b, v in S.BEHAVIORS.items())))
        print("models: %s" % ", ".join(models or DEFAULT_MODELS))
        print("calibration jobs: %d (%d saved)" % (len(calibration_plan(models)), len(read_jsonl(CAL_FILE))))
        print("study jobs: %d (%d saved)" % (len(plan(n_inputs, models)), len(read_jsonl(GEN_FILE))))
        miss = missing_lists(models)
        print("derived lists: %s" % ("complete" if not miss else "missing for %d (behavior, model) pairs" % len(miss)))
        print("judge calls: about the same as generations")
    elif cmd == "calibrate":
        run_generate(calibration_plan(models), max_calls, client_for, gen_file=CAL_FILE)
    elif cmd == "generate":
        miss = missing_lists(models)
        if miss:
            print("No derived list yet for: %s" % ", ".join("%s/%s" % p for p in miss))
            print("Run calibrate, judge --calibration and paper/derive_lists.py first.")
            sys.exit(1)
        if S.load_lists().get("_meta", {}).get("draft", True):
            print("lists.json is still a draft. Review it, then: python paper/derive_lists.py --freeze")
            sys.exit(1)
        run_generate(plan(n_inputs, models), max_calls, client_for)
    elif cmd == "judge":
        jm = arg("--judge", DEFAULT_JUDGE)
        cal = "--calibration" in sys.argv
        run_judge(jm, max_calls, make_client(jm), gen_file=CAL_FILE if cal else GEN_FILE,
                  out_file=judge_file(jm, calibration=cal))
    else:
        print("unknown command: " + cmd)
        sys.exit(1)


if __name__ == "__main__":
    main()
