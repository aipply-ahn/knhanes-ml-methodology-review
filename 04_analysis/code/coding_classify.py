"""Study-level categories that keyword rules cannot settle from the free-text coded values (2026-11-19): code
availability, online tool, primary outcome domain and study purpose. Per study, Claude and Codex each classify
independently (text only, isolated calls) from the title and the final coded values of the relevant items (no report
text); same category -> final; different -> one second look in which each sees the other's choice and reason; still
different -> settled by rule: code availability and online tool take the less available category (conservative),
outcome domain and purpose take 'mixed_or_other' / 'unclear'. Output: results/oct_search/coding/analysis/
study_classified.csv and classify_calls.jsonl (raw). Usage: coding_classify.py [--workers N]"""
import collections, concurrent.futures as cf, csv, hashlib, json, os, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN
C = "results/oct_search/coding"; A = f"{C}/analysis"; CALLS = f"{A}/classify_calls.jsonl"; LOCK = threading.Lock()
VARS = {
 "code": (["none_stated", "on_request", "promised_later", "in_supplement", "public_repository"],
          "Availability of the authors' own analysis code or trained model (not the survey data): public_repository = a link to code or model files (GitHub, Zenodo, OSF, other URL); in_supplement = code printed in the article or its supplement; promised_later = to be released later; on_request = code or model available on request; none_stated = no statement about code or model (statements about the KNHANES data only count as none_stated)."),
 "tool": (["no", "yes"], "yes = an online prediction tool, web calculator or app that applies the model is offered with a link or as accessible; otherwise no."),
 "domain": (["cardiometabolic", "kidney_liver", "mental_health", "musculoskeletal", "respiratory", "cancer", "eye_ear_oral", "nutrition_behaviour", "general_health_mortality", "other_disease", "mixed_or_other"],
            "Primary outcome domain of the study's main outcome: cardiometabolic (diabetes, prediabetes, hypertension, dyslipidaemia, obesity, metabolic syndrome, cardiovascular disease, hyperuricaemia); kidney_liver (CKD, fatty liver, liver function); mental_health (depression, anxiety, suicidality, stress, cognition, sleep); musculoskeletal (osteoporosis, sarcopenia, arthritis, back pain, frailty); respiratory (COPD, asthma, lung function); cancer; eye_ear_oral (eye disease, hearing, dental, periodontal); nutrition_behaviour (diet, nutrient intake, smoking, alcohol, physical activity, weight control behaviour); general_health_mortality (self-rated health, quality of life, multimorbidity, mortality, health-care use); other_disease (another specific disease such as anaemia or thyroid); mixed_or_other (several domains with none primary, or a non-health outcome in a method study)."),
 "purpose": (["health_prediction", "health_explanation", "method_development", "unclear"],
             "Main purpose of using ML as stated: health_prediction = to predict, classify, screen for or estimate a health outcome, a tool or model for identifying people; health_explanation = mainly to identify, rank or explain factors related to a health outcome (risk factors, variable importance), prediction secondary; method_development = to develop, propose or compare ML methods or algorithms with KNHANES as test data; unclear."),
}
S = {"type": "string"}
SCH = {"type": "object", "additionalProperties": False, "required": list(VARS), "properties": {
    k: {"type": "object", "additionalProperties": False, "required": ["category", "reason"], "properties": {"category": {"type": "string", "enum": v[0]}, "reason": S}} for k, v in VARS.items()}}
ITEMS = ["intended_use.intended_use", "outcome.definition", "model_development.model_code_availability", "presentation.model_presentation", "model_development.model_family", "interpretation.interpretation_limitations"]
PROMPT = """Classify one study of a systematic review of machine-learning studies using the Korea National Health and Nutrition
Examination Survey (KNHANES). You see its title and the coded values of some items (not the report itself). Choose one
category per variable using only this information; reason: one short sentence.

VARIABLES
{defs}
{second}
TITLE
{title}

CODED VALUES
{coded}"""


def ask(who, prompt, tag):
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    with LOCK:
        if os.path.exists(CALLS):
            for l in open(CALLS):
                r = json.loads(l)
                if r["tag"] == tag and r["assessor"] == who and r["prompt_sha256"] == ps and r.get("answer"): return r["answer"]
    res, err, meta = RUN.text_call(who, prompt, SCH, tag)
    with LOCK: open(CALLS, "a").write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res, error=err, call=meta), ensure_ascii=False) + "\n")
    return res


def one(rid, title, I):
    coded = "\n".join(f"- {it}: " + ("; ".join((v['unit'] + ': ' if v['unit'] else '') + v.get('value_full', v['value'])[:400] for v in I[it]['values']) or I[it]['status'])
                      for it in ITEMS if I.get(it))
    defs = "\n".join(f"- {k}: {v[1]} Categories: {' | '.join(v[0])}" for k, v in VARS.items())
    p1 = PROMPT.format(defs=defs, second="", title=title, coded=coded)
    with cf.ThreadPoolExecutor(2) as ex: a = list(ex.map(lambda w: ask(w, p1, f"{rid}@classify-1"), ("claude", "codex")))
    if not all(a): return None
    out = {}; diff = [k for k in VARS if a[0][k]["category"] != a[1][k]["category"]]
    for k in VARS:
        if k not in diff: out[k] = (a[0][k]["category"], "agree_r1")
    if diff:
        sec = "\nSECOND LOOK: two classifiers chose differently before: " + "; ".join(
            f"{k}: one chose {a[0][k]['category']} ({a[0][k]['reason']}), the other {a[1][k]['category']} ({a[1][k]['reason']})" for k in diff) + ". Decide again for all variables.\n"
        p2 = PROMPT.format(defs=defs, second=sec, title=title, coded=coded)
        with cf.ThreadPoolExecutor(2) as ex: b = list(ex.map(lambda w: ask(w, p2, f"{rid}@classify-2"), ("claude", "codex")))
        for k in diff:
            if all(b) and b[0][k]["category"] == b[1][k]["category"]: out[k] = (b[0][k]["category"], "agree_r2")
            else:
                cats = VARS[k][0]; c = [a[0][k]["category"], a[1][k]["category"]]
                out[k] = ((min(c, key=cats.index), "rule_conservative") if k in ("code", "tool") else ("mixed_or_other" if k == "domain" else "unclear", "rule_unresolved"))
    return out


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    rows = [json.loads(l) for l in open(f"{C}/pilot_final/final_items.jsonl")] + [json.loads(l) for l in open(f"{C}/final_items.jsonl")]
    I = collections.defaultdict(dict)
    for r in rows: I[r["record_id"]][r["item"]] = r["final"]
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    reps = [l["record_id"] for l in csv.DictReader(open("results/oct_search/public/report_study_links.csv")) if l["role"] == "representative"]
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(lambda r: one(r, meta[r]["title"], I[r]), reps))
    os.makedirs(A, exist_ok=True)
    with open(f"{A}/study_classified.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["record_id"] + [x for k in VARS for x in (k, k + "_how")])
        for r, o in zip(reps, res): w.writerow([r] + ([x for k in VARS for x in o[k]] if o else ["FAILED"] * (2 * len(VARS))))
    print("studies", len(reps), "failed", sum(1 for o in res if not o))
    for k in VARS: print(k, dict(collections.Counter(o[k][0] for o in res if o)), dict(collections.Counter(o[k][1] for o in res if o)))


if __name__ == "__main__":
    main()
