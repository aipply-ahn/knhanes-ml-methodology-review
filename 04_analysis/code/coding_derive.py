"""Study-level analysis variables from the final data coding (author: 'convert to Excel ... and complete the manuscript text').
One row per study (279 studies = representative report of each study, results/oct_search/public/report_study_links.csv).
Every variable is derived mechanically from the final coded items (final_items.jsonl of the full run + pilot_final),
by the fixed rules written next to each variable below (keyword or label matching on the coded values of items with
status reported; 'unclear' and 'not_reported' kept as such). No value is re-read from the reports here.
Output: results/oct_search/coding/analysis/study_derived.csv and derive_rules.tsv (variable, item, rule).
Usage: coding_derive.py"""
import collections, csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
C = "results/oct_search/coding"; A = f"{C}/analysis"
RULES = []


def rule(var, item, text): RULES.append((var, item, text))


def low(x): return " ".join(v["value"].lower() for v in x["values"]) if x else ""
def vals(x): return [v["value"] for v in x["values"]] if x else []


def scopes(x):
    """(step, scope) pairs of model_development.step_data_scope, from 'step: scope' values and JSON-text values."""
    out = []
    for v in vals(x):
        t = v.strip()
        if t.startswith("{"):
            try: out += [(k, str(s)) for k, s in json.loads(t).items()]; continue
            except Exception: pass
        m = re.match(r"(.+?):\s*([a-z_]+.*)$", t)
        if m: out.append((m.group(1), m.group(2)))
        else: out.append((v.get("unit", "") if isinstance(v, dict) else "", t))
    return out


FAM = [("tree_ensemble", r"random forest|\brf\b|xgboost|xgb\b|lightgbm|lgbm|catboost|gradient boost|\bgbm\b|\bgbdt\b|adaboost|extra trees|extremely randomi[sz]ed|bagging|boost"),
       ("svm", r"support vector|\bsvm\b|\bsvc\b|\bsvr\b"),
       ("neural_network", r"neural|\bann\b|\bmlp\b|perceptron|\bdnn\b|\bcnn\b|lstm|deep learning|tabnet|transformer|autoencoder|\bgru\b|\brnn\b|resnet|ft-transformer"),
       ("single_tree", r"decision tree|\bcart\b|\bchaid\b|c4\.5|c5\.0|\bdt\b|classification tree|regression tree|\bid3\b"),
       ("knn", r"nearest neighbo|\bknn\b|k-nn"), ("naive_bayes", r"naive bayes|naïve bayes|\bnb\b"),
       ("regression_family", r"logistic|linear regression|lasso|ridge|elastic net|\blr\b|glm|cox"),
       ("llm", r"\bgpt|large language|\bllm\b|llama|gemini|claude"), ("automl", r"automl|auto-sklearn|h2o|pycaret|autogluon")]
rule("fam_*", "model_development.model_family", "1 if any value matches the family's pattern: " + "; ".join(f"{k} = /{p}/" for k, p in FAM))


def derive(rid, I):
    d = {}
    g = lambda it: I.get(it)
    st = lambda it: (g(it) or {}).get("status", "missing")
    # timing
    t = low(g("outcome.timing_horizon"))
    d["timing"] = "prognostic" if "prognostic" in t else "cross_sectional" if "cross_sectional" in t or "cross-sectional" in t else ("unclear" if st("outcome.timing_horizon") in ("reported", "unclear") else st("outcome.timing_horizon"))
    # validation design
    v = low(g("validation.type"))
    for k, p in [("val_external", r"fully_external|external"), ("val_temporal", r"temporal"), ("val_geographic", r"geographic"), ("val_split", r"split_sample|split"),
                 ("val_cv", r"cross_validation|cross-validation|cross validation"), ("val_bootstrap", r"bootstrap"), ("val_apparent", r"apparent"), ("val_none", r"no validation")]:
        d[k] = int(bool(re.search(p, v))) if st("validation.type") == "reported" else 0
    d["val_best"] = ("external_or_temporal" if d["val_external"] or d["val_temporal"] or d["val_geographic"] else "split_sample" if d["val_split"] else
                     "resampling" if d["val_cv"] or d["val_bootstrap"] else "apparent_only" if d["val_apparent"] else "no_validation" if d["val_none"] else "not_clear")
    # performance
    disc = g("performance.discrimination")
    d["auc_reported"] = int(st("performance.discrimination") == "reported" and any(x.lower().startswith("reported") or re.search(r"\d", x) for x in vals(disc)))
    cal = low(g("performance.calibration"))
    d["calibration"] = int(st("performance.calibration") == "reported" and bool(re.search(r"calibrat|brier|hosmer|reliability|o:e|observed", cal)))
    d["calibration_beyond_brier"] = int(d["calibration"] and bool(re.search(r"calibrat|hosmer|reliability|o:e|observed|slope|intercept", cal)))
    d["uncertainty"] = int(st("performance.uncertainty") == "reported")
    d["threshold_reported"] = int(st("performance.threshold") == "reported")
    # survey design
    sh = low(g("model_development.survey_handling"))
    d["weights_fitting"] = int(st("model_development.survey_handling") == "reported" and "used_in_fitting" in sh)
    d["weights_evaluation"] = int(st("model_development.survey_handling") == "reported" and "used_in_evaluation" in sh)
    sw = low(g("data_source.survey_design_weights"))
    d["design_any"] = int(st("data_source.survey_design_weights") == "reported" and bool(re.search(r"used_in|used_but|weight|strat|psu|cluster", sw)) and "not_used_stated" not in sw[:20])
    d["design_descriptive_only"] = int("used_in_descriptive_only" in sw and not (d["weights_fitting"] or d["weights_evaluation"]))
    # data scope of data-dependent steps
    sc = scopes(g("model_development.step_data_scope"))
    lab = [s.lower() for _, s in sc]
    d["scope_whole_before_split"] = int(any("whole_dataset_before_split" in s for s in lab))
    d["scope_test_outcomes_used"] = int(any("test_outcomes_used" in s for s in lab))
    d["scope_all_stated_within_training"] = int(bool(lab) and all(("training_only" in s or "within_cv_folds" in s or s.startswith("not done") or "external_predictors_transformed" in s) for s in lab))
    d["scope_any_not_stated"] = int(any("not_stated" in s for s in lab))
    # overlap and availability
    labs = [re.match(r"\W*([a-z_]+)", x.lower()).group(1) if re.match(r"\W*([a-z_]+)", x.lower()) else "" for x in vals(g("predictors.outcome_overlap"))]  # leading label of each value
    d["overlap"] = ("overlap" if "overlap" in labs else "possible" if "possible" in labs else "none_found" if "none_found" in labs else "unclear") if st("predictors.outcome_overlap") == "reported" else st("predictors.outcome_overlap")
    av = vals(g("predictors.availability_at_use"))
    d["use_setting_stated"] = int(st("predictors.availability_at_use") == "reported" and bool(av) and "not_stated" not in av[0].lower())
    # imbalance, missing data
    ci = low(g("model_development.class_imbalance"))
    rep = st("model_development.class_imbalance") == "reported"
    d["imb_synthetic"] = int(rep and bool(re.search(r"smote|adasyn|borderline|synthetic|gan\b|vae", ci)))
    d["imb_resampling"] = int(rep and bool(re.search(r"undersampl|under-sampl|oversampl|over-sampl|random sampl|downsampl|upsampl|\bros\b|\brus\b|near ?miss|tomek", ci)))
    d["imb_weights"] = int(rep and bool(re.search(r"class.?weight|sample.?weight|scale_pos_weight|cost.?sensitive|balanced", ci)))
    d["imb_any"] = int(rep and not re.match(r"\s*not done", ci) and (d["imb_synthetic"] or d["imb_resampling"] or d["imb_weights"] or bool(re.search(r"threshold|focal|stratif|balanc", ci))))
    im = low(g("missing_data.imputation_method"))
    d["missing_imputation"] = ("multiple_or_model" if re.search(r"multiple imput|mice|chained|knn|nearest|missforest|random forest|regression imput|em algorithm|expectation|hot.?deck|autoencoder|iterative", im)
                               else "simple" if re.search(r"mean|median|mode|zero|constant|most frequent|last observation", im)
                               else "complete_case" if re.search(r"not done|complete.?case|excluded|removed|deleted|listwise", im)
                               else "other" if st("missing_data.imputation_method") == "reported" else st("missing_data.imputation_method"))
    # models
    mf = low(g("model_development.model_family"))
    for k, p in FAM: d["fam_" + k] = int(bool(re.search(p, mf)))
    # use, presentation, code, reporting
    pr = low(g("presentation.model_presentation"))
    d["pres_shap"] = int(bool(re.search(r"shap|shapley", pr)))
    d["pres_tool"] = int(bool(re.search(r"nomogram|score|calculator|web|app\b|equation|formula|application", pr)))
    # code availability and online tools: coding_classify.py (two AI systems), not keyword rules
    for k, it in [("intended_use_stated", "intended_use.intended_use"), ("limitations_stated", "interpretation.interpretation_limitations"), ("ss_rationale", "sample_size.rationale"),
                  ("tuning_reported", "model_development.tuning_search"), ("predsel_reported", "model_development.predictor_selection"), ("flow_reported", "participants.flow"),
                  ("events_reported", "sample_size.events_nonevents"), ("missing_amount_reported", "missing_data.amount_by_variable"), ("funding_reported", "funding.funding"),
                  ("coi_reported", "conflicts.conflicts"), ("linkage_or_pooling", "data_source.dataset_linkage"), ("recalibration_reported", "validation.updating_recalibration")]:
        d[k] = int(st(it) == "reported")
    # analysed sample size: largest integer in the analysed-size values (thousands separators removed)
    nums = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+|\d+", " ".join(vals(g("sample_size.analysed_by_dataset")))) if 20 <= int(x.replace(",", "")) <= 5_000_000]
    d["n_analysed_max"] = max(nums) if nums else ""
    d["inconsistency_items"] = sum(1 for x in I.values() if x and x.get("inconsistency") == "present")
    return d


for var, it, txt in [("timing", "outcome.timing_horizon", "prognostic if any value contains 'prognostic'; else cross_sectional if 'cross_sectional'/'cross-sectional'; else unclear"),
                     ("val_*", "validation.type", "label present in any value (status reported): fully_external|external, temporal, geographic, split_sample, cross_validation, bootstrap, apparent, 'no validation'; val_best = highest of external/temporal/geographic > split > resampling > apparent > none"),
                     ("auc_reported", "performance.discrimination", "status reported and a value 'reported...' or with a number"),
                     ("calibration", "performance.calibration", "status reported and a value naming calibration, Brier, Hosmer-Lemeshow, reliability, O:E; calibration_beyond_brier excludes Brier-only"),
                     ("weights_fitting / weights_evaluation", "model_development.survey_handling", "label used_in_fitting / used_in_evaluation in a value (status reported)"),
                     ("design_any / design_descriptive_only", "data_source.survey_design_weights", "design used anywhere (weights, strata, PSU named; not 'not_used_stated'); descriptive only = used_in_descriptive_only and not in fitting/evaluation"),
                     ("scope_*", "model_development.step_data_scope", "scope labels of the steps: whole_dataset_before_split, test_outcomes_used; all within training = every step training_only/within_cv_folds/not done"),
                     ("imb_*", "model_development.class_imbalance", "synthetic (SMOTE, ADASYN, GAN, VAE), resampling (over/under-sampling), weights (class/sample weights, scale_pos_weight, cost-sensitive)"),
                     ("missing_imputation", "missing_data.imputation_method", "multiple_or_model (MICE, kNN, missForest, ...) > simple (mean/median/mode) > complete_case (not done, excluded) > other"),
                     ("pres_shap / pres_tool", "presentation.model_presentation", "SHAP named; nomogram, score, calculator, web/app, equation named"),
                     ("overlap", "predictors.outcome_overlap", "leading label of each value: overlap > possible > none_found > unclear"),
                     ("n_analysed_max", "sample_size.analysed_by_dataset", "largest integer 20-5,000,000 in the values")]:
    rule(var, it, txt)


def main():
    rows = [json.loads(l) for l in open(f"{C}/pilot_final/final_items.jsonl")] + [json.loads(l) for l in open(f"{C}/final_items.jsonl")]
    I = collections.defaultdict(dict)
    for r in rows: I[r["record_id"]][r["item"]] = r["final"]
    links = list(csv.DictReader(open("results/oct_search/public/report_study_links.csv")))
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    os.makedirs(A, exist_ok=True)
    out = []
    for l in links:
        if l["role"] != "representative": continue
        rid = l["record_id"]; y = int(meta[rid]["year"])
        d = dict(study_id=l["study_id"], record_id=rid, year=y, period="2010-2019" if y <= 2019 else "2020-2022" if y <= 2022 else "2023-2024" if y <= 2024 else "2025-2026")
        d.update(derive(rid, I[rid])); out.append(d)
    with open(f"{A}/study_derived.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    with open(f"{A}/derive_rules.tsv", "w") as f:
        f.write("variable\titem\trule\n" + "".join(f"{a}\t{b}\t{c}\n" for a, b, c in RULES))
    print("studies", len(out), "missing coding", sum(1 for d in out if not I[d['record_id']]))


if __name__ == "__main__":
    main()
