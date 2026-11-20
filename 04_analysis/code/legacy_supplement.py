"""Supplementary Figures S1-S8 of the ORIGINAL manuscript drawn with the October-search data (author 2026-11-19: same
figures, new numbers; code missing items rather than drop a figure).
Runs the unchanged plotting functions of tools/make_supplementary_figures.py (and make_main_figures.figure_testbed /
figure_agreement) with their inputs swapped, as legacy_figures.py does for the main figures:
  CORE / HEALTH / METHOD and the protocol-shaped records  <- results/oct_search/legacy_fig/records.json (legacy_figdata.py)
  ROOT/results/derived/*.json                              <- results/oct_search/legacy_fig/results/derived (written here)
  EXP (algorithm families, tuning), PURPOSE_RECORDS (method studies), participant restrictions and flow, KNHANES role
                                                           <- October coding (v3.1.3 main items, legacy1 and legacy3 items)
Fixed rules for values that the October coding holds as text (no judgement made here):
  tuning (model_development.tuning_search): grid / random / Bayesian / Optuna / hyperopt / genetic / 'search' / 'optimi'
    -> systematic search; 'default' / 'not tuned' / 'no tuning' -> default or no tuning; other reported text -> manual tuning;
    not_reported / unclear -> not reported.
  algorithm families: legacy.algorithms_fitted codes; XGBoost / LightGBM / naive Bayes named in the fitted-algorithm text
    or model_development.model_family.
  participant selection reported: source size = participants.flow or sample_size.eligible_by_dataset reported;
    eligibility = participants.eligibility reported; numbers excluded = participants.exclusions reported with a number;
    reasons = participants.exclusions reported with words; final sample = sample_size.analysed_by_dataset reported;
    every step = all five.
  algorithms compared (S5A) = more than one algorithm fitted (legacy.selected_model not single_algorithm).
Output: results/oct_search/legacy_fig/supp/Supplementary_Figure_S0N_<same slug>.pdf/png
Usage: legacy_supplement.py"""
import collections, csv, json, os, re, sys
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
L = Path(ROOT) / "results/oct_search/legacy_fig"; DER = L / "results/derived"; OUT = L / "supp"; OUT.mkdir(parents=True, exist_ok=True)
REC = json.load(open(L / "records.json"))
CYC_YEARS = range(1998, 2028)


def finals(folder, reps):
    out = collections.defaultdict(dict)
    p = f"{folder}/final_items.jsonl" if "coding_legacy" in folder else f"{folder}/final_items_clean.jsonl"
    for l in (open(p) if os.path.exists(p) else []):
        r = json.loads(l)
        if r["record_id"] in reps and r.get("final"): out[r["item"]][r["record_id"]] = r["final"]
    return out


def main():
    reps = set(REC["records"])
    F = finals("results/oct_search/coding_legacy", reps)
    for k, v in finals("results/oct_search/coding_legacy3", reps).items(): F[k] = v
    M = finals("results/oct_search/coding", reps)

    def vals(D, item, rid):
        x = D.get(item, {}).get(rid) or {}
        return x.get("status"), [str(v.get("value", "")) for v in (x.get("values") or []) if str(v.get("value", "")).strip()]

    def codes(item, rid):
        return [c.split(":")[0].split("(")[0].strip() for v in vals(F, item, rid)[1] for c in re.split(r"\s*;\s*", v) if c.strip()]

    def text(D, item, rid):
        return " ; ".join(vals(D, item, rid)[1]).lower()

    recs = REC["records"]; core = [recs[r] for r in REC["CORE"]]
    health = [recs[r] for r in REC["HEALTH"]]; method = [recs[r] for r in REC["METHOD"]]
    rank = [d for d in core if any(x["value"] == "USED" for x in d["protocol_items"]["VI01"])]
    o = json.load(open(DER / "practice_trends_112.json"))
    cat = {r: ("compare" if "compare" in text(F, "legacy.study_category", r) or "COMPARE" in " ".join(codes("legacy.study_category", r)) else "develop") for r in REC["METHOD"]}

    # ---- protocol items the supplementary code reads in addition to the main-figure ones
    for d in core:
        r = d["study_id"]; pi = d["protocol_items"]
        st = (codes("legacy.outcome_structure", r) or ["UNC"])[0].upper()
        pi["OUT09"] = [{"value": v} for v in {"BINARY": ["BINARY"], "MULTIBIN": ["MULTIBIN"], "MULTICLASS": ["MULTICLASS"], "UNC": []}.get(st, ["BINARY", "MULTICLASS"])]
        pi["FUN_COMPARE"] = [{"value": "ABSENT" if text(F, "legacy.selected_model", r) == "single_algorithm" else "PRESENT"}]
        # Supplementary Figure S8B counts model units: one value per development or evaluation unit (the study-level code
        # lists repeat a value for each signalling answer); Figure S6E counts importance methods among ranking studies only,
        # as Figure 4B does (author review 2026-11-20)
        for kk in [k_ for k_ in pi if k_.startswith("U:P")]: pi[kk[2:]] = [{"value": u["value"]} for u in pi[kk] if u["value"]] or [{"value": "NA"}]
        # evaluation domains: only the units with an overall judgement, matched by unit label (as the text, legacy_numbers.py)
        ov = {u["unit"]: u["value"] for u in pi.get("U:PE_OVERALL", []) if u["value"] != "NA"}
        for kk in ("PE_D1", "PE_D2", "PE_D3", "PE_D4"):
            dm = {u["unit"]: u["value"] for u in pi.get("U:" + kk, []) if u["value"] != "NA"}
            dvals = list(dm.values()) if (len(ov) == 1 and len(dm) == 1) else [dm[u] for u in ov if u in dm]
            pi[kk] = [{"value": v} for v in dvals] or [{"value": "NA"}]
        if "USED" not in [x["value"] for x in pi["VI01"]]: pi["VI02"] = [{"value": "NA"}]
        res = {c.upper() for c in codes("legacy.restrictions", r)}
        d["adjudication"] = {"selection_restriction_dimensions": {"fields": {k: {"value": c in res} for k, c in (
            ("age_restriction", "AGE"), ("sex_restriction", "SEX"), ("disease_or_risk_restriction", "DISEASE_OR_RISK_GROUP"),
            ("measurement_or_data_availability_restriction", "MEASUREMENT_OR_DATA_AVAILABILITY"))}}}

    # ---- EXP: algorithm families and tuning per core study
    FAM = [("Random forest", "random_forest", r"random forest"), ("Logistic regression", "logistic_regression", r"logistic"),
           ("XGBoost", None, r"xgb"), ("SVM", "svm", r"\bsvm|support vector"), ("DNN/MLP", "neural_network", r"neural|mlp|dnn|deep"),
           ("LightGBM", None, r"lightgbm|lgbm|light gbm"), ("Decision tree", "decision_tree", r"decision tree|\bcart\b"),
           ("Naive Bayes", None, r"naive bayes|naïve bayes")]
    EXP = {}
    for d in core:
        r = d["study_id"]; cs = set(codes("legacy.algorithms_fitted", r))
        t = text(F, "legacy.algorithms_fitted", r) + " " + text(M, "model_development.model_family", r)
        fam = [n for n, c, pat in FAM if (c and c in cs) or re.search(pat, t)]
        if "boosting" in cs and not ({"XGBoost", "LightGBM"} & set(fam)): fam.append("Gradient boosting")
        if "other" in cs or re.search(r"\bknn\b|nearest|catboost|adaboost|extra tree", t): fam.append("Other")
        sts, tv = vals(M, "model_development.tuning_search", r); tt = " ".join(tv).lower()
        if sts != "reported": tm, ts = "NR", "NR"
        elif re.search(r"default|not tuned|no tuning|without tuning|not performed|not done", tt) and not re.search(r"grid|random search|bayes|optuna", tt): tm, ts = "MANUAL_OR_DEFAULT", "NO_TUNING_OR_DEFAULT_MODEL"
        elif re.search(r"grid|random|bayes|optuna|hyperopt|genetic|search|optimi|tpe\b", tt): tm, ts = "GRID_SEARCH", "TUNED"
        else: tm, ts = "MANUAL_OR_DEFAULT", "TUNED"
        EXP[r] = {"study_id": r, "task_group": "CLS", "algorithm_development": {"algorithm_family": fam, "hyperparameter_tuning_method": tm, "tuning_selection_status": ts}}

    # ---- participant selection reported (S4B)
    def st(item, r): return vals(M, item, r)[0] == "reported"
    flow = {"source_population_size_reported": 0, "eligibility_criteria_reported": 0, "exclusion_numbers_reported": 0,
            "exclusion_reasons_reported": 0, "final_analytic_sample_reported": 0, "complete_cohort_traceability": 0}
    for d in core:
        r = d["study_id"]; ex = text(M, "participants.exclusions", r)
        f = [st("participants.flow", r) or st("sample_size.eligible_by_dataset", r), st("participants.eligibility", r),
             st("participants.exclusions", r) and bool(re.search(r"\d", ex)), st("participants.exclusions", r) and bool(re.search(r"[a-z]{3}", ex)),
             st("sample_size.analysed_by_dataset", r)]
        for k, v in zip(list(flow)[:5], f): flow[k] += v
        flow["complete_cohort_traceability"] += all(f)

    # ---- KNHANES role (S2A) and method studies (S1, S6)
    POS = {"EXTERNAL_OR_TRANSPORT_EVALUATION_DATASET": "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"}
    pos = {r: POS.get(c, c) for r in recs for c in [(codes("legacy.knhanes_position", r) or ["UNCLEAR"])[0].upper()]}
    pc = collections.Counter(pos.values())
    EVAL = {"EXTERNAL_OR_TRANSPORTABILITY_EVALUATION": "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"}
    precs = []
    for d in method:
        r = d["study_id"]
        precs.append({"study_id": r, "publication_year": d["metadata"]["publication_year"], "study_category": "METHOD_RESEARCH",
                      "method_research_category": "EXISTING_METHODS_COMPARISON_OR_EVALUATION" if cat[r] == "compare" else "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT",
                      "method_intervention_stages": [c.upper() for c in codes("legacy.method_stages", r)],
                      "method_evaluation_mode": EVAL.get(*(2 * [(codes("legacy.method_evaluation", r) or ["EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED"])[0].upper()])),
                      "knhanes_position": pos[r]})
    precs += [{"study_id": d["study_id"], "publication_year": d["metadata"]["publication_year"], "study_category": "HEALTH_ANALYSIS",
               "knhanes_position": pos[d["study_id"]]} for d in health]

    # ---- derived files read by the supplementary code
    P = lambda y: 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3
    lm = {q["id"]: q["topic"] for q in o["literature_map"]}
    rt = {}
    for t in ("METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR"):
        g = [[d for d in core if lm[d["study_id"]] == t and P(d["metadata"]["publication_year"]) == k] for k in range(4)]
        rt[t] = {"n": [len(x) for x in g], "ranking": [sum(d in rank for d in x) for x in g]}
    rep = {"outcome_fully_specified": sum(any(x["value"] == "R2" for x in d["protocol_items"]["OUT16"]) for d in core),
           "predictor_set_rebuildable": sum(any(x["value"] == "R2" for x in d["protocol_items"]["PRD13"]) for d in core)}
    rep["all_three"] = sum(any(x["value"] == "R2" for x in d["protocol_items"]["OUT16"]) and any(x["value"] == "R2" for x in d["protocol_items"]["PRD13"])
                           and (codes("legacy.tuning_kept_apart", d["study_id"]) or ["NR"])[0] in ("USED", "NA") for d in core)
    years = collections.Counter(); ynr = 0
    for d in core:
        ys = set()
        for v in (M.get("data_source.survey_cycles", {}).get(d["study_id"]) or {}).get("values") or []:
            if re.match(r"\s*NHANES", str(v.get("unit", ""))): continue
            tv = str(v.get("value", ""))
            for a_, b_ in re.findall(r"((?:19|20)\d\d)\s*(?:[-–—~∼]|to|through)\s*((?:19|20)?\d\d)\b", tv):
                a1, b1 = int(a_), int(b_) if len(b_) == 4 else int(a_[:2] + b_)
                if a1 <= b1: ys.update(range(a1, b1 + 1))
            ys.update(int(y) for y in re.findall(r"\b((?:19|20)\d\d)\b", tv))
        ys = {y for y in ys if y in CYC_YEARS}
        years.update(ys); ynr += not ys
    o.update(ranking_by_topic_period=rt, reproducibility=rep, health_functions={"FUN_INTERP": len(rank)},
             validation_beyond_development_184=sum(o["practices"]["validation_beyond_development"]),
             survey_components_220=o["survey_components_165"], survey_year_scope_220=o["core_year_scope"],
             core_survey_years={"counts": {str(y): years[y] for y in sorted(years)}, "not_reported": ynr})
    for n in ("106", "107", "110"): json.dump(o, open(DER / f"practice_trends_{n}.json", "w"), ensure_ascii=False, indent=1)
    json.dump({"health_focused_classification": {"health_topics": {}}}, open(DER / "exploratory_temporal_practice_analysis.json", "w"))

    # ---- run the unchanged plotting code
    import claim_evidence_analysis as ce, make_streamlined_figures as m, practice_trends as pt, make_main_figures as mm
    ce.CORE[:] = core; ce.EXP = EXP; ce.build = lambda: {"participant_flow_core": flow}
    m.HEALTH[:] = health; m.METHOD[:] = method; m.PURPOSE_RECORDS[:] = precs
    m.PURPOSE = {"summary": {"knhanes_position": dict(pc)}}
    pt.outcome_source_codes = lambda dd: []
    import make_supplementary_figures as S
    S.CORE, S.HEALTH, S.METHOD, S.EXP = core, health, method, EXP
    S.N_CORE, S.N_HEALTH, S.N_METHOD = len(core), len(health), len(method); S.N_ALL = len(health) + len(method); S.N_RANK = len(rank)
    S.ROOT = L; S.OUT = OUT; S._pin = lambda *a, **k: True
    S.reporting_summary = lambda rows: {"members": {"threshold_reported": [], "threshold_independent": []}}
    mm.ROOT = L; mm._pin = lambda *a, **k: True
    _bars = S.bars  # axis limits of the September counts are too short for the October counts: widen so the value labels fit
    S.bars = lambda ax, labels, values, denom=None, color=S.NAVY, xmax=None, fmt=None: _bars(ax, labels, values, denom, color, max(xmax or 0, 1.3 * max(values or [1])), fmt)
    S.style("en")
    out = [S.s1(), S.s2(), S.s8(), S.s3(), S.s4()[0], S.s_testbed(), S.s_agreement(), S.s7()]
    print("built", len(out), "supplementary figures in", OUT)
    print("knhanes_position", dict(pc), "flow", flow, "reproducibility", rep, "tuning", collections.Counter(e["algorithm_development"]["tuning_selection_status"] + "/" + e["algorithm_development"]["hyperparameter_tuning_method"] for e in EXP.values()))


if __name__ == "__main__":
    main()
