"""Prompt 094: the four [S7 calculation] items of review v32 section 7 plus the Figure 2-6 inputs.

Writes results/derived/practice_trends_094.json. Every number comes from the adjudicated study records
(make_streamlined_figures / claim_evidence_analysis), the same records exported in Supplementary Table S5.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import claim_evidence_analysis as ce  # noqa: E402
import make_streamlined_figures as m  # noqa: E402

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True

CORE, EXP, HEALTH = ce.CORE, ce.EXP, ce.HEALTH
PERIODS = ["≤2019", "2020–2022", "2023–2024", "2025–2026"]


def groups():
    return [[d for d in CORE if m.period(int(d["metadata"]["publication_year"])) == p] for p in PERIODS]


def fam(d, names):
    return bool(set(EXP[d["study_id"]]["algorithm_development"]["algorithm_family"]) & set(names))


PRACTICES = {
    "importance_ranking": lambda d: m.has(d, "VI01", {"USED"}),
    "shap": lambda d: m.has(d, "VI02", {"SHAP"}),
    "boosting": lambda d: fam(d, {"XGBoost", "LightGBM", "Gradient boosting"}),
    "validation_beyond_development": lambda d: m.has(d, "VAL02", {"EXTERNAL", "TEMPORAL"}),
    "calibration": lambda d: any(m.has(d, k, {"R"}) for k in ("MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R")),
    "code_link": lambda d: m.has(d, "MOD15", {"USED"}),
    "survey_weight_mention": lambda d: m.has(d, "SUR04", {"USED"}),
}


def preprocessing_status(d, key, within, before, unclear):
    v = set(m.flat_values(d, key))
    if v & set(before): return "BEFORE"
    if v & set(within): return "WITHIN"
    if v & set(unclear): return "UNCLEAR"
    return "NA"


PRE_SPECS = [("missing_value_handling", "PRE05", ("USED",), ("NOT_USED",), ("NR", "UNC")),
             ("scaling_or_other_preprocessing", "PRE14", ("USED",), ("NOT_USED",), ("NR", "UNC")),
             ("feature_selection", "PRE13", ("WITHIN", "TRAIN"), ("BEFORE",), ("ORDER_NR", "OTHER")),
             ("class_rebalancing", "IMB03", ("WITHIN", "TRAIN"), ("BEFORE",), ("ORDER_NR", "OTHER"))]


def feature_selection_not_reported(d):
    return preprocessing_status(d, *PRE_SPECS[2][1:]) == "NA" and bool(set(m.flat_values(d, "PRE11")) & {"NR", "UNC"}) \
        and "USED" not in set(m.flat_values(d, "PRE11"))


def any_before(d):
    return any(preprocessing_status(d, k, w, b, u) == "BEFORE" for _, k, w, b, u in PRE_SPECS)


def build():
    g = groups()
    den = [len(x) for x in g]
    _pin(den, [32, 32, 52, 49], "practice_trends.py:63")  # prompt 106 pin
    out = {"periods": PERIODS, "period_n": den, "practices": {}}
    for name, fn in PRACTICES.items():
        out["practices"][name] = [sum(map(fn, x)) for x in g]
    # Stability among studies producing a ranking (Fig 4A of prompt 093; row 5 of new Fig 4).
    imp = [[d for d in x if PRACTICES["importance_ranking"](d)] for x in g]
    out["ranking_n"] = [len(x) for x in imp]
    out["stability_among_ranking"] = [sum(m.has(d, "VI16", {"USED"}) for d in x) for x in imp]
    out["shap_among_ranking"] = [sum(PRACTICES["shap"](d) for d in x) for x in imp]
    # [S7 calc 3] preprocessing: at least one data-dependent step before the split, by period.
    out["any_step_before_split"] = [sum(any_before(d) for d in x) for x in g]
    # [S7 calc 2] survey design at each workflow stage (165 core studies).
    first = lambda d, k: (m.flat_values(d, k) or ["NR"])[0]
    stages = {}
    for key, label in (("SUR04", "any_weight_mention"), ("SUR06", "weights_in_fitting"), ("SUR07", "weights_in_evaluation"),
                       ("SUR11", "combined_cycle_weights"), ("SUR10", "strata_or_psu_in_variance")):
        if key == "SUR04":
            used, applicable = sum(m.has(d, key, {"USED"}) for d in CORE), len(CORE)  # prompt 106: core size follows the study set
        else:
            c = Counter(first(d, key) for d in CORE); used, applicable = c["USED"], len(CORE) - c["NA"]  # prompt 106
        stages[label] = {"used": used, "applicable": applicable}
    out["survey_design_stages"] = stages
    # Reproducibility components (current Fig 3A; new Fig 6C).
    s = ce.build()
    out["reproducibility"] = {
        "outcome_fully_specified": sum(m.reduce_recoverability(d, "OUT16") == "FULL" for d in CORE),
        "predictor_set_rebuildable": sum(m.reduce_recoverability(d, "PRD13") == "FULL" for d in CORE),
        "tuning_kept_apart": sum(ce.tuning_status(d) in ("TUNING_REPORTED_SEPARATED", "NO_TUNING_OR_DEFAULT_MODEL") for d in CORE),
        "all_three": s["classification_components"]["all_three"],
    }
    # Preprocessing timing rows (new Fig 6A).
    rows = {}
    for name, key, w, b, u in PRE_SPECS:
        c = Counter(preprocessing_status(d, key, w, b, u) for d in CORE)
        rows[name] = {k: c[k] for k in ("WITHIN", "UNCLEAR", "BEFORE", "NA")}
    out["preprocessing_timing"] = rows
    out["any_step_before_split_total"] = sum(any_before(d) for d in CORE)
    # Importance methods and downstream use (new Fig 3B, 3C).
    named = ["SHAP", "MODEL_NATIVE", "COEFFICIENT_STATISTIC", "PERMUTATION", "TREE_RULE", "PERTURBATION_ABLATION", "LIME", "PDP"]
    residual = {"ALE", "ICE", "NETWORK_SPECIFIC", "OTHER"}
    out["importance_methods"] = {k: sum(m.has(d, "VI02", {k}) for d in CORE) for k in named}
    out["importance_methods"]["OTHER"] = sum(bool(set(m.flat_values(d, "VI02")) & residual) for d in CORE)
    out["downstream"] = {k: sum(m.has(d, v, {"USED"}) for d in CORE) for k, v in
                         (("stability_checked", "VI16"), ("reduced_predictor_set", "VI10"), ("subsequent_statistical_analysis", "VI11"),
                          ("same_variables_carried", "VI14"))}
    out["importance_ranking_total"] = sum(PRACTICES["importance_ranking"](d) for d in CORE)
    # Health-focused analyses performed (new Fig 2B) and survey use (new Fig 2C).
    out["health_functions"] = s["health_functions"]
    comps = Counter(); [comps.update(set(m.flat_values(d, "DAT14"))) for d in m.ALL]
    scope = Counter(m.first(d, "DAT08", "UNC") for d in m.ALL)
    out["survey_components_220"] = {k: comps[k] for k in ("HEALTH_INTERVIEW", "EXAMINATION", "LABORATORY", "ORAL_HEALTH", "NUTRITION")}
    out["survey_year_scope_220"] = {k: scope[k] for k in ("ONE_YEAR", "MULTI_SAME", "MULTI_CROSS")}
    out["use_composition"] = s["use_composition"]
    return out


def check(o):
    p = o["practices"]
    # Values the v32 plan quotes (end points and the full rows it gives).
    _pin(p["importance_ranking"], [17, 22, 44, 46], "practice_trends.py:122")  # prompt 106 pin
    _pin(p["shap"], [0, 6, 17, 34], "practice_trends.py:123")  # prompt 106 pin
    _pin((p["boosting"][0], p["boosting"][-1]), (1, 42), "practice_trends.py:124")  # prompt 106 pin
    _pin((p["validation_beyond_development"][0], p["validation_beyond_development"][-1]), (5, 18), "practice_trends.py:125")  # prompt 106 pin
    _pin((p["calibration"][0], p["calibration"][-1]), (1, 14), "practice_trends.py:126")  # prompt 106 pin
    _pin((p["code_link"][0], p["code_link"][-1]), (1, 8), "practice_trends.py:127")  # prompt 106 pin
    _pin(o["stability_among_ranking"], [2, 3, 8, 12], "practice_trends.py:128")  # prompt 106 pin
    _pin(o["ranking_n"], [17, 22, 44, 46], "practice_trends.py:128")  # prompt 106 pin
    _pin(o["importance_ranking_total"], 129, "practice_trends.py:129")  # prompt 106 pin
    _pin(sum(o["stability_among_ranking"]), 25, "practice_trends.py:129")  # prompt 106 pin
    _pin(o["any_step_before_split_total"], 83, "practice_trends.py:130")  # prompt 106 pin
    _pin(sum(o["any_step_before_split"]), 83, "practice_trends.py:130")  # prompt 106 pin
    st = o["survey_design_stages"]
    _pin((st["any_weight_mention"]["used"], st["weights_in_fitting"]["used"], st["weights_in_fitting"]["applicable"],             st["weights_in_evaluation"]["used"]), (34, 6, 163, 5), "practice_trends.py:132")  # prompt 106 pin
    r = o["reproducibility"]
    _pin((r["outcome_fully_specified"], r["predictor_set_rebuildable"], r["tuning_kept_apart"], r["all_three"]), (79, 26, 72, 12), "practice_trends.py:135")  # prompt 106 pin
    _pin(o["survey_year_scope_220"]["MULTI_CROSS"], 121, "practice_trends.py:136")  # prompt 106 pin
    _pin(o["health_functions"]["FUN_PRED"], 177, "practice_trends.py:137")  # prompt 106 pin
    _pin(o["health_functions"]["FUN_COMPARE"], 141, "practice_trends.py:137")  # prompt 106 pin


def build_095(o):
    """Prompt 095 (review v33) [S5 calculation] items, added to the 094 values in a separate file."""
    g = groups()
    core_ids = {d["study_id"] for d in CORE}
    val = PRACTICES["validation_beyond_development"]
    out = dict(o)
    # Figure 4 lower row: indicators that changed little (same definitions as Figure 6C).
    tuning = lambda d: ce.tuning_status(d) in ("TUNING_REPORTED_SEPARATED", "NO_TUNING_OR_DEFAULT_MODEL")
    out["little_changed"] = {
        "tuning_kept_apart": [sum(map(tuning, x)) for x in g],
        "predictor_set_rebuildable": [sum(m.reduce_recoverability(d, "PRD13") == "FULL" for d in x) for x in g],
        "final_model_fully_specified": [sum(m.has(d, "REP17", {"R"}) for d in x) for x in g],
    }
    # Robustness of the latest-period rise: 2025 and 2026 separately.
    split = {}
    for yr in (2025, 2026):
        grp = [d for d in CORE if int(d["metadata"]["publication_year"]) == yr]
        split[str(yr)] = {"n": len(grp), **{k: sum(map(PRACTICES[k], grp)) for k in
                                           ("validation_beyond_development", "calibration", "code_link")}}
    out["latest_period_by_year"] = split
    # Validation beyond the development data: one definition (VAL02 external or later period) for 184 and 165.
    out["validation_beyond_development_184"] = sum(map(val, HEALTH))
    out["validation_beyond_development_165"] = sum(map(val, CORE))
    out["validation_beyond_development_noncore_ids"] = sorted(d["study_id"] for d in HEALTH if d["study_id"] not in core_ids and val(d))
    out["temporal_validation_165"] = sum(m.has(d, "VAL02", {"TEMPORAL"}) for d in CORE)
    # Survey cycles pooled in the core cohort (Discussion) and the combined-weight denominator (Figure 6B).
    scope = Counter(m.first(d, "DAT08", "UNC") for d in CORE)
    out["core_year_scope"] = {k: scope[k] for k in ("ONE_YEAR", "MULTI_SAME", "MULTI_CROSS", "UNC")}
    pooled = [d for d in CORE if m.first(d, "DAT08", "UNC") == "MULTI_CROSS"]
    out["temporal_validation_among_pooled"] = sum(m.has(d, "VAL02", {"TEMPORAL"}) for d in pooled)
    out["survey_year_scope_220_unclear"] = sum(m.first(d, "DAT08", "UNC") == "UNC" for d in m.ALL)
    # Weights in model fitting: the two not-applicable studies trained on other data (rationale in the records).
    out["weights_in_fitting_not_applicable"] = sorted(d["study_id"] for d in CORE if (m.flat_values(d, "SUR06") or ["NR"])[0] == "NA")
    # Figure 3C on its applicable denominator (studies producing a ranking).
    rank = [d for d in CORE if PRACTICES["importance_ranking"](d)]
    out["later_use_among_ranking"] = {"n": len(rank), "reduced_predictor_set": sum(m.has(d, "VI10", {"USED"}) for d in rank),
                                      "subsequent_statistical_analysis": sum(m.has(d, "VI11", {"USED"}) for d in rank)}
    # Positive preprocessing indicator: all applied data-dependent steps kept within the training data.
    def applied(d):
        return [s for s in (preprocessing_status(d, k, w, b, u) for _, k, w, b, u in PRE_SPECS) if s != "NA"]
    out["preprocessing_applied"] = [sum(bool(applied(d)) for d in x) for x in g]
    out["preprocessing_all_within"] = [sum(bool(applied(d)) and all(s == "WITHIN" for s in applied(d)) for d in x) for x in g]
    out["preprocessing_applied_rows"] = {name: len(CORE) - out["preprocessing_timing"][name]["NA"] for name, *_ in PRE_SPECS}  # prompt 106
    # Optional check: ranking and SHAP trend inside the largest topic (metabolic/endocrine).
    topic = lambda d: m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"]
    met = [[d for d in x if topic(d) == "METABOLIC_ENDOCRINE"] for x in g]
    out["metabolic_endocrine"] = {"n": [len(x) for x in met],
                                  "importance_ranking": [sum(map(PRACTICES["importance_ranking"], x)) for x in met],
                                  "shap": [sum(map(PRACTICES["shap"], x)) for x in met]}
    return out


def check_095(o):
    lc = o["little_changed"]
    _pin(lc, {"tuning_kept_apart": [16, 10, 20, 26], "predictor_set_rebuildable": [6, 5, 6, 9],                   "final_model_fully_specified": [3, 0, 3, 5]}, "practice_trends.py:194")  # prompt 106 pin
    _pin(sum(lc["tuning_kept_apart"]), 72, "practice_trends.py:196")  # prompt 106 pin
    _pin(sum(lc["predictor_set_rebuildable"]), 26, "practice_trends.py:196")  # prompt 106 pin
    _pin(sum(lc["final_model_fully_specified"]), 11, "practice_trends.py:196")  # prompt 106 pin
    s = o["latest_period_by_year"]
    _pin((s["2025"]["n"], s["2026"]["n"]), (27, 22), "practice_trends.py:198")  # prompt 106 pin
    for k in ("validation_beyond_development", "calibration", "code_link"):
        assert s["2025"][k] + s["2026"][k] == o["practices"][k][-1], k
    _pin((o["validation_beyond_development_184"], o["validation_beyond_development_165"]), (41, 38), "practice_trends.py:201")  # prompt 106 pin
    _pin(o["validation_beyond_development_noncore_ids"], ["KHM067", "KHM069", "KHM143"], "practice_trends.py:202")  # prompt 106 pin
    _pin(o["temporal_validation_165"], 23, "practice_trends.py:203")  # prompt 106 pin
    _pin(o["core_year_scope"]["MULTI_CROSS"], 93, "practice_trends.py:204")  # prompt 106 pin
    _pin(o["temporal_validation_among_pooled"], 17, "practice_trends.py:204")  # prompt 106 pin
    _pin(o["survey_year_scope_220_unclear"], 6, "practice_trends.py:205")  # prompt 106 pin
    _pin(sum(o["survey_year_scope_220"].values()), 214, "practice_trends.py:205")  # prompt 106 pin
    _pin(o["weights_in_fitting_not_applicable"], ["KHM003", "KHM005"], "practice_trends.py:206")  # prompt 106 pin
    _pin(o["later_use_among_ranking"], {"n": 129, "reduced_predictor_set": 24, "subsequent_statistical_analysis": 12}, "practice_trends.py:207")  # prompt 106 pin
    _pin(o["preprocessing_applied"], [31, 32, 52, 48], "practice_trends.py:208")  # prompt 106 pin
    _pin(o["preprocessing_all_within"], [5, 0, 2, 8], "practice_trends.py:208")  # prompt 106 pin
    _pin(o["preprocessing_applied_rows"], {"missing_value_handling": 79, "scaling_or_other_preprocessing": 163,                                                "feature_selection": 80, "class_rebalancing": 62}, "practice_trends.py:209")  # prompt 106 pin


def preprocessing_state(d):
    """Three states among studies applying at least one data-dependent step (prompt 096)."""
    s = [x for x in (preprocessing_status(d, k, w, b, u) for _, k, w, b, u in PRE_SPECS) if x != "NA"]
    if not s: return "NONE"
    if "BEFORE" in s: return "ANY_BEFORE"
    if all(x == "WITHIN" for x in s): return "WITHIN_ONLY"
    return "UNCLEAR_NO_BEFORE"


def author_key(a):
    """Surname plus first initial, for both "Kim H" and "Hana Kim" author formats."""
    parts = str(a).replace(".", " ").split()
    if not parts: return ""
    if len(parts) >= 2 and len(parts[-1]) <= 2 and parts[-1].isupper():
        return (parts[0] + " " + parts[-1][0]).lower()
    return (parts[-1] + " " + parts[0][0]).lower()


def build_096(o):
    """Prompt 096 (review v34) [S5 calculation] items, added to the 095 values in a separate file."""
    g = groups()
    out = dict(o)
    # Tuning kept apart: Figure 4B/Table 1 definition includes studies without tuning; former S6D excluded them.
    sep = lambda d: EXP[d["study_id"]]["algorithm_development"]["tuning_selection_status"] == "TUNING_REPORTED_SEPARATED"
    out["tuning_definitions"] = {"separated_or_no_tuning": o["little_changed"]["tuning_kept_apart"],
                                 "separated_only": [sum(map(sep, x)) for x in g]}
    # Composition of the 2026 rise.
    d26 = [d for d in CORE if int(d["metadata"]["publication_year"]) == 2026]
    val = [d for d in d26 if PRACTICES["validation_beyond_development"](d)]
    cal = {d["study_id"] for d in d26 if PRACTICES["calibration"](d)}
    kinds = Counter("both" if {"EXTERNAL", "TEMPORAL"} <= set(m.flat_values(d, "VAL02")) else
                    "later_survey_period" if "TEMPORAL" in m.flat_values(d, "VAL02") else "external_data" for d in val)
    authors = Counter()
    for d in val:
        authors.update({author_key(a) for a in d["metadata"].get("authors") or []} - {""})
    out["rise_2026"] = {"n": len(d26), "validation": len(val), "calibration": len(cal),
                        "validation_and_calibration": len({d["study_id"] for d in val} & cal),
                        "validation_kind": dict(kinds), "journals": len({d["metadata"].get("journal") for d in val}),
                        "authors_in_more_than_one_validation_study": sorted(a for a, n in authors.items() if n > 1),
                        "max_validation_studies_per_author_name": max(authors.values())}
    # Preprocessing states by period (Supplementary Figure S6E).
    out["preprocessing_states"] = [{k: Counter(map(preprocessing_state, x))[k] for k in ("WITHIN_ONLY", "UNCLEAR_NO_BEFORE", "ANY_BEFORE", "NONE")} for x in g]
    # How stability was checked (study-level coding in the expanded audit; one study can use two methods).
    stab = [d for d in CORE if m.has(d, "VI16", {"USED"})]
    meth = Counter(); known = 0
    for d in stab:
        v = set(EXP[d["study_id"]]["importance_stability_methods"]) - {"METHOD_NOT_RECOVERABLE"}
        known += bool(v); meth.update(v)
    out["stability_methods"] = {"n": len(stab), "method_identified": known, **dict(sorted(meth.items()))}
    # Shares used for "rose in every period".
    share = lambda num, den: [round(100 * a / b, 1) for a, b in zip(num, den)]
    out["shares"] = {"code_link": share(o["practices"]["code_link"], o["period_n"]),
                     "stability_among_ranking": share(o["stability_among_ranking"], o["ranking_n"]),
                     "validation_beyond_development": share(o["practices"]["validation_beyond_development"], o["period_n"]),
                     "calibration": share(o["practices"]["calibration"], o["period_n"])}
    return out


def check_096(o):
    t = o["tuning_definitions"]
    _pin(t["separated_or_no_tuning"], [16, 10, 20, 26], "practice_trends.py:273")  # prompt 106 pin
    _pin(t["separated_only"], [11, 6, 18, 22], "practice_trends.py:273")  # prompt 106 pin
    r = o["rise_2026"]
    _pin((r["n"], r["validation"], r["calibration"], r["validation_and_calibration"]), (22, 13, 12, 9), "practice_trends.py:275")  # prompt 106 pin
    _pin(r["validation_kind"], {"external_data": 7, "later_survey_period": 4, "both": 2}, "practice_trends.py:276")  # prompt 106 pin
    _pin(r["journals"], 12, "practice_trends.py:277")  # prompt 106 pin
    _pin(r["max_validation_studies_per_author_name"], 2, "practice_trends.py:277")  # prompt 106 pin
    ps = o["preprocessing_states"]
    assert [p["ANY_BEFORE"] for p in ps] == o["any_step_before_split"]
    assert [p["WITHIN_ONLY"] for p in ps] == o["preprocessing_all_within"]
    _pin(o["preprocessing_all_within"], [5, 0, 2, 8], "practice_trends.py:296")  # prompt 106 pin
    _pin([p["UNCLEAR_NO_BEFORE"] for p in ps], [8, 15, 23, 19], "practice_trends.py:281")  # prompt 106 pin
    s = o["stability_methods"]
    _pin((s["n"], s["method_identified"]), (25, 11), "practice_trends.py:299")  # prompt 106 pin
    _pin("ACROSS_CYCLE_STABILITY" in s, False, "practice_trends.py:299b")  # prompt 106 pin
    sh = o["shares"]
    for k in ("code_link", "stability_among_ranking"):
        _pin(all(a < b for a, b in zip(sh[k], sh[k][1:])), True, f"practice_trends.py:302 rose-every-period {k} {sh[k]}")  # prompt 106 pin: monotone claim re-checked


def WORKBOOK():
    """Study-level workbook: Supplementary Data 1 (prompt 097); the earlier name is used if it is the one present."""
    new, old = ROOT / "manuscript/bmc_supplementary_data1.xlsx", ROOT / "manuscript/bmc_supplementary_table_s5.xlsx"
    return new if new.exists() else old


DOMAINS = ["AGE", "SEX", "ADIPOSITY_BODY_SIZE", "BLOOD_PRESSURE", "LIPIDS", "GLYCAEMIA_DIABETES", "KIDNEY_URINE", "SMOKING",
           "ALCOHOL", "PHYSICAL_ACTIVITY_FUNCTION", "DIET", "SOCIOECONOMIC", "MENTAL_SUBJECTIVE_HEALTH", "WORK_CLINICAL_HISTORY",
           "PAIN_MUSCULOSKELETAL", "OTHER"]


def important_domains(d):
    """Standardised domains (VI07) of the variables each study named as most important, over all interpreted models."""
    s = set()
    for x in d["protocol_items"].get("VI07", []):
        v = x.get("value")
        if v in (None, "NA", "NR", "", []): continue
        s |= set(v if isinstance(v, list) else [v])
    return s


def build_097(o):
    """Prompt 097 (review v35) [S5 calculation] items: literature map (new Figure 2) and what the rankings pointed to (new Figure 4)."""
    import itertools
    import statistics
    from openpyxl import load_workbook
    out = dict(o)
    # Literature map: every included study (Table S5 workbook = Supplementary Data 1, the published study-level dataset).
    wb = load_workbook(WORKBOOK(), read_only=True)  # prompt 098: renamed Supplementary Data 1 in prompt 097
    it = wb["STUDIES"].iter_rows(values_only=True)
    hdr = list(next(it)); ix = {h: i for i, h in enumerate(hdr)}
    pts = []
    for r in it:
        n = str(r[ix["D_final_sample"]]).split("|")[0].strip()
        pts.append({"id": r[ix["A_study_id"]], "year": int(r[ix["A_publication_year"]]),
                    "group": ("core" if r[ix["B_core_health_classification"]] == "Y" else
                              "other_health" if r[ix["B_health_focused"]] == "Y" else "method"),
                    "topic": r[ix["B_health_topic"]],
                    "n": int(n) if n.isdigit() else None, "ranking": "USED" in str(r[ix["I_importance_reported"]]).split(" | ")})
    out["literature_map"] = sorted(pts, key=lambda p: p["id"])
    out["per_year"] = {str(k): v for k, v in sorted(Counter(p["year"] for p in pts).items())}
    ns = [p["n"] for p in pts if p["n"]]
    q1, med, q3 = statistics.quantiles(ns, n=4)
    out["sample_summary"] = {"reported": len(ns), "not_reported": len(pts) - len(ns), "median": med, "q1": q1, "q3": q3,
                             "weight_replicated_records": {"KHM019": 217598}}
    # What the rankings pointed to: domains named important by each ranking study, by primary health topic.
    rank = [d for d in CORE if PRACTICES["importance_ranking"](d)]
    topic = lambda d: m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"]
    by_topic = {}
    for d in rank:
        by_topic.setdefault(topic(d), []).append(d)
    shown = sorted((t for t, v in by_topic.items() if len(v) >= 5 and t != "OTHER_OR_CROSS_CUTTING"), key=lambda t: -len(by_topic[t]))  # prompt 106
    out["ranking_domains_by_topic"] = {t: {"n": len(by_topic[t]), **{k: sum(k in important_domains(d) for d in by_topic[t]) for k in DOMAINS}}
                                       for t in shown}
    out["ranking_domains_all"] = {"n": len(rank), **{k: sum(k in important_domains(d) for d in rank) for k in DOMAINS}}
    out["ranking_domains_metabolic_studies"] = [
        {"id": d["study_id"], "year": int(d["metadata"]["publication_year"]), "domains": sorted(important_domains(d) - {"OTHER"})}
        for d in sorted(by_topic["METABOLIC_ENDOCRINE"], key=lambda d: (int(d["metadata"]["publication_year"]), d["study_id"]))]
    # Agreement of domain sets (other domains excluded): pairs of studies within the same topic vs different topics.
    sets = {d["study_id"]: (topic(d), important_domains(d) - {"OTHER"}) for d in rank}
    jac = lambda a, b: len(a & b) / len(a | b) if a | b else 0.0
    within, between = [], []
    for (_, (ta, a)), (_, (tb, b)) in itertools.combinations(sets.items(), 2):
        (within if ta == tb else between).append(jac(a, b))
    out["domain_agreement"] = {"pairs_within_topic": len(within), "mean_jaccard_within": round(statistics.mean(within), 3),
                               "pairs_between_topics": len(between), "mean_jaccard_between": round(statistics.mean(between), 3),
                               "median_jaccard_within": round(statistics.median(within), 3),
                               "median_jaccard_between": round(statistics.median(between), 3),
                               "quartiles_within": [round(q, 3) for q in statistics.quantiles(within, n=4)],
                               "quartiles_between": [round(q, 3) for q in statistics.quantiles(between, n=4)],
                               "share_no_overlap_within": round(sum(j == 0 for j in within) / len(within), 3),
                               "mean_domains_per_study": round(statistics.mean(len(s) for _, s in sets.values()), 2)}
    # Per-topic within-topic agreement (topics with at least five ranking studies).
    out["domain_agreement_by_topic"] = {}
    for t in shown:
        ids = [d["study_id"] for d in by_topic[t]]
        js = [jac(sets[a][1], sets[b][1]) for a, b in itertools.combinations(ids, 2)]
        out["domain_agreement_by_topic"][t] = {"pairs": len(js), "median": round(statistics.median(js), 3)}
    # Literature map panel B: health topic x period among the 184 health-focused studies.
    per = lambda y: 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3
    tp = {}
    for p in pts:
        if p["group"] != "method":
            tp.setdefault(p["topic"], [0, 0, 0, 0])[per(p["year"])] += 1
    out["topic_by_period_184"] = dict(sorted(tp.items(), key=lambda kv: -sum(kv[1])))
    out["importance_selection_rules"] = dict(Counter(r for d in rank for x in d["protocol_items"].get("VI08", [])
                                                     for r in (x["value"] if isinstance(x["value"], list) else [x["value"]])))
    return out


def check_097(o):
    _pin(len(o["literature_map"]), 220, "practice_trends.py:380")  # prompt 106 pin
    _pin(sum(o["per_year"].values()), 220, "practice_trends.py:380")  # prompt 106 pin
    _pin((o["per_year"]["2019"], o["per_year"]["2025"], o["per_year"]["2026"]), (12, 39, 27), "practice_trends.py:381")  # prompt 106 pin
    s = o["sample_summary"]
    _pin((s["reported"], s["not_reported"]), (215, 5), "practice_trends.py:383")  # prompt 106 pin
    _pin(s["median"], 7176, "practice_trends.py:383")  # prompt 106 pin
    _pin(Counter(p["group"] for p in o["literature_map"]), {"core": 165, "other_health": 19, "method": 36}, "practice_trends.py:384")  # prompt 106 pin
    _pin(sum(p["ranking"] for p in o["literature_map"] if p["group"] == "core"), 129, "practice_trends.py:385")  # prompt 106 pin
    t = o["ranking_domains_by_topic"]
    _pin(list(t), ["METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR", "ORAL_HEALTH", "RESPIRATORY"], "practice_trends.py:387")  # prompt 106 pin
    _pin([t[k]["n"] for k in t], [35, 31, 20, 13, 7, 5], "practice_trends.py:388")  # prompt 106 pin
    _pin((t["METABOLIC_ENDOCRINE"]["AGE"], t["METABOLIC_ENDOCRINE"]["ADIPOSITY_BODY_SIZE"]), (24, 24), "practice_trends.py:389")  # prompt 106 pin
    _pin((t["MUSCULOSKELETAL"]["AGE"], t["MUSCULOSKELETAL"]["ADIPOSITY_BODY_SIZE"]), (19, 18), "practice_trends.py:390")  # prompt 106 pin
    _pin((t["CARDIOVASCULAR"]["AGE"], t["CARDIOVASCULAR"]["ADIPOSITY_BODY_SIZE"]), (12, 12), "practice_trends.py:391")  # prompt 106 pin
    _pin((t["MENTAL_HEALTH"]["SOCIOECONOMIC"], t["MENTAL_HEALTH"]["MENTAL_SUBJECTIVE_HEALTH"]), (24, 23), "practice_trends.py:392")  # prompt 106 pin
    a = o["ranking_domains_all"]
    _pin((a["n"], a["AGE"], a["ADIPOSITY_BODY_SIZE"], a["SOCIOECONOMIC"]), (129, 97, 79, 72), "practice_trends.py:394")  # prompt 106 pin
    g = o["domain_agreement"]
    _pin((g["mean_jaccard_within"], g["mean_jaccard_between"]), (0.285, 0.269), "practice_trends.py:396")  # prompt 106 pin
    _pin(len(o["ranking_domains_metabolic_studies"]), 35, "practice_trends.py:397")  # prompt 106 pin
    tbp = o["topic_by_period_184"]
    _pin(sum(map(sum, tbp.values())), 184, "practice_trends.py:399")  # prompt 106 pin
    _pin(tbp["METABOLIC_ENDOCRINE"], [10, 8, 13, 18], "practice_trends.py:399")  # prompt 106 pin
    _pin(tbp["MENTAL_HEALTH"], [5, 7, 11, 14], "practice_trends.py:399")  # prompt 106 pin
    _pin([sum(v[i] for v in tbp.values()) for i in range(4)], [36, 34, 56, 58], "practice_trends.py:400")  # prompt 106 pin
    _pin((g["median_jaccard_within"], g["median_jaccard_between"], g["quartiles_within"]), (0.286, 0.25, [0.167, 0.286, 0.4]), "practice_trends.py:401")  # prompt 106 pin
    _pin(o["domain_agreement_by_topic"]["METABOLIC_ENDOCRINE"], {"pairs": 595, "median": 0.222}, "practice_trends.py:402")  # prompt 106 pin


# ----------------------------------------------------------------- prompt 098 (review v36)
OUTCOME_GROUPS = [("diabetes", r"diabet|glyc|prediabet"), ("metabolic syndrome", r"metabolic syndrome|\bmets\b"),
                  ("hypertension", r"hypertens|blood pressure"), ("dyslipidaemia", r"dyslip|cholesterol|triglycer|lipid"),
                  ("obesity", r"obes|overweight|\bbmi\b|adipos|weight"), ("fatty liver", r"fatty liver|nafld|masld|steato"),
                  ("kidney", r"kidney|ckd|egfr|renal|albuminur"), ("depression", r"depress|phq"), ("suicide", r"suicid"),
                  ("stress or anxiety", r"stress|anxi|gad"), ("bone", r"osteopor|bone|bmd|osteopen"),
                  ("muscle", r"sarcopen|muscle|grip"), ("arthritis or pain", r"arthrit|osteoarth|pain"),
                  ("cardiovascular", r"cardio|coronary|stroke|myocard|angina|cvd"), ("oral", r"periodont|dental|oral|tooth|teeth"),
                  ("hearing", r"hearing|tinnitus"), ("respiratory or smoking", r"copd|asthma|lung|pulmon|smok"),
                  ("quality of life", r"quality of life|eq-5d|hrqol")]
EXCLUDED_FROM_DIABETES = r"retinopath|chronic diseases"


def first_value(d, item):
    for x in d["protocol_items"].get(item, []):
        v = x.get("value")
        if v not in (None, "NA", "NR", ""):
            return str(v)
    return ""


def outcome_source_codes(d):
    """Outcome-source codes of a study; a definition drawing on several sources keeps all of them (review 20261023),
    so the source counts are of studies using each source and can add up to more than the studies."""
    v = d.get("adjudication", {}).get("analytic_flow", {}).get("fields", {}).get("outcome_ascertainment_source_category", {}).get("value", "NOT_REPORTED")
    return list(dict.fromkeys(v if isinstance(v, list) else [v]))


def _derived_overrides():
    """Review-loop decisions on derived columns both reviewers agreed on (additional_file_review/DERIVED_OVERRIDES.tsv):
    study_id, column, value for Harmonised variables (Figure 5), Outcome group (Figure 5) and Outcome group (Figure S7A)."""
    import csv
    f = ROOT / "additional_file_review/DERIVED_OVERRIDES.tsv"
    return {(r["study_id"], r["column"]): r["value"] for r in csv.DictReader(f.open(encoding="utf-8"), delimiter="\t")} if f.exists() else {}


DERIVED = _derived_overrides()


def outcome_group(d):
    """Outcome group from the recorded primary outcome name (first outcome unit), by keyword; 'other' when none matches."""
    if (d["study_id"], "Outcome group (Figure S7A)") in DERIVED:
        return DERIVED[(d["study_id"], "Outcome group (Figure S7A)")]
    name = first_value(d, "OUT02").lower()
    for g, pat in OUTCOME_GROUPS:
        if re.search(pat, name):
            return g
    return "other"


LEAD = re.compile(r"^[^:]{0,60}\b(top|rank|ranks|importance|figure|contributors|significant)\b[^:]{0,40}:\s*", re.I)


def named_variables(d):
    """Variables the report named as most important (VI06, first interpreted model), in the recorded order, lightly cleaned:
    leading labels ('RF importance top 15:'), parenthetical values and trailing importance numbers are removed."""
    text = LEAD.sub("", first_value(d, "VI06"))
    # review 20261023: a relative in parentheses marks a family-history item; keep that before parentheses are dropped
    text = re.sub(r"\(([^()]*\b(father|mother|sibling|siblings|parent|parents|brother|sister|family)\b[^()]*)\)", " family history", text, flags=re.I)
    text = re.sub(r"[ \t]{2,}", " ", text)
    for _ in range(2):  # parentheticals (values, coefficients, glosses) may contain commas: remove before splitting
        text = re.sub(r"\([^()]*\)", "", text)
    text = re.sub(r"\([^()]*$", "", text)  # an unclosed trailing parenthesis
    out = []
    for part in re.split(r",|;|\|", text):
        part = re.sub(r"\([^()]*\)", "", part)
        part = re.sub(r"\b[A-Z]{2,4}\d{3}-[A-Z]\d{2}\b:?\s*", "", part.strip())  # internal unit IDs (KHM164-M01), review 20261023
        part = re.sub(r"(?<=\s)[-−]?\d+(\.\d+)?\s*$|^[-−]?\d+(\.\d+)?\s*$", "", part.strip())  # a trailing value, not a code digit (BP8), review 20261023
        part = re.sub(r"^(and|then|followed by)\s+", "", part.strip(), flags=re.I).strip(" .")
        if part and not re.fullmatch(r"[-−]?\d+(\.\d+)?|[\d\s–-]+years.*", part):
            out.append(part)
    return out


# Harmonised variable names for the variable-level Figure 4B (diabetes and prediabetes studies): pattern -> label.
DIABETES_VARIABLES = [("Age", r"^age\b|age group|age at enrollment"), ("Sex", r"^sex\b|gender"),
                      ("BMI", r"\bbmi\b|body mass index"), ("Waist circumference or WHtR", r"waist|whtr|abdominal obesity|neck circ"),
                      ("HbA1c or fasting glucose", r"hba1c|glucose|\bfbg\b|\bglyc"), ("Cholesterol or triglycerides", r"cholesterol|triglycer|\bldl\b|\bhdl\b|dyslip"),
                      ("Hypertension or blood pressure", r"hypertens|\bsbp\b|\bdbp\b|blood pressure"),
                      ("Family history of diabetes", r"family history"), ("Liver enzymes", r"\bast\b|\balt\b|got|gpt"),
                      ("Urine markers", r"urine|urinary"), ("Smoking", r"smok"), ("Alcohol", r"alcohol|drink"),
                      ("Physical activity", r"walking|exercise|physical activity"),
                      ("Education, income or occupation", r"education|income|occupation|employment|working hours|unemploy|marital"),
                      ("Diet or nutrients", r"thiamine|water|food|calcium|fatty acid|carbohydrate|potassium|energy|sugar|vitamin|riboflavin|protein|\bfat\b|meal")]


NUTRIENT_ONLY = {"KHM050"}  # nutrient-intake sensitivity indices (dietary cholesterol, not serum lipids)


def harmonise(name, table, sid=None):
    low = name.lower()
    if sid in NUTRIENT_ONLY:
        return "Diet or nutrients"
    for label, pat in table:
        if re.search(pat, low):
            return label
    return None


def build_098(o):
    """Prompt 098 (review v36) [data calculation]: comparability of the rankings (Figure 4C), a variable-level panel for
    one outcome (Figure 4B), and the top-ranked variables per study (Table S8)."""
    import itertools
    import statistics
    out = dict(o)
    rank = [d for d in CORE if PRACTICES["importance_ranking"](d)]
    named = {d["study_id"]: named_variables(d) for d in rank}
    counts = [len(v) for v in named.values()]
    q = statistics.quantiles(counts, n=4)
    out["named_variable_count"] = {"n": len(counts), "median": statistics.median(counts), "q1": q[0], "q3": q[2],
                                   "min": min(counts), "max": max(counts)}
    topic = lambda d: m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"]
    og = {d["study_id"]: outcome_group(d) for d in rank}
    tp = {d["study_id"]: topic(d) for d in rank}
    dom = {d["study_id"]: important_domains(d) - {"OTHER"} for d in rank}
    core3 = {"AGE", "SEX", "ADIPOSITY_BODY_SIZE"}
    jac = lambda a, b: len(a & b) / len(a | b) if a | b else None
    rows = {"same_outcome": [], "same_topic_other_outcome": [], "different_topic": []}
    rows_x = {k: [] for k in rows}
    for a, b in itertools.combinations(sorted(dom), 2):
        if og[a] != "other" and og[a] == og[b]:
            k = "same_outcome"
        elif tp[a] == tp[b]:
            k = "same_topic_other_outcome"
        else:
            k = "different_topic"
        rows[k].append(jac(dom[a], dom[b]))
        jx = jac(dom[a] - core3, dom[b] - core3)
        if jx is not None:
            rows_x[k].append(jx)
    summ = lambda xs: {"pairs": len(xs), "median": round(statistics.median(xs), 3),
                       "q1": round(statistics.quantiles(xs, n=4)[0], 3), "q3": round(statistics.quantiles(xs, n=4)[2], 3)}
    out["domain_agreement_098"] = {"all_domains": {k: summ(v) for k, v in rows.items()},
                                   "without_age_sex_body_size": {k: summ(v) for k, v in rows_x.items()}}
    out["outcome_groups_ranking"] = dict(Counter(og.values()).most_common())
    # Variable-level panel: diabetes and prediabetes studies (first outcome unit), harmonised names, reported position.
    dia = [d for d in rank if og[d["study_id"]] == "diabetes" and not re.search(EXCLUDED_FROM_DIABETES, first_value(d, "OUT02").lower())]
    dia.sort(key=lambda d: (int(d["metadata"]["publication_year"]), d["study_id"]))
    panel = []
    for d in dia:
        pos = {}
        for i, v in enumerate(named[d["study_id"]], start=1):
            lab = harmonise(v, DIABETES_VARIABLES, d["study_id"])
            if lab and lab not in pos:
                pos[lab] = i
        panel.append({"id": d["study_id"], "year": int(d["metadata"]["publication_year"]), "n_named": len(named[d["study_id"]]),
                      "outcome": first_value(d, "OUT02")[:80], "positions": pos})
    out["diabetes_variable_panel"] = {"labels": [l for l, _ in DIABETES_VARIABLES], "studies": panel}
    # Top-ranked variables for every ranking study (Table S8): up to five, in the recorded order.
    out["top_variables"] = {sid: v[:5] for sid, v in sorted(named.items())}
    return out


def check_098(o):
    c = o["named_variable_count"]
    _pin((c["n"], c["median"]), (129, 10), "practice_trends.py:536")  # prompt 106 pin
    g = o["domain_agreement_098"]
    _pin(sum(v["pairs"] for v in g["all_domains"].values()), 129 * 128 // 2, "practice_trends.py:558")  # prompt 106 pin
    _pin(len(o["diabetes_variable_panel"]["studies"]), 12, "practice_trends.py:539")  # prompt 106 pin
    assert all(1 <= len(v) <= 5 for v in o["top_variables"].values())
    _pin(len(o["top_variables"]), 129, "practice_trends.py:560")  # prompt 106 pin


# ----------------------------------------------------------------- prompt 099 (review v37 storyline)
def build_099(o):
    """Prompt 099 [data calculation]: Figure 2 bridge (algorithm families by period, familiar evaluation work, what the
    classifiers classified), Figure 3B (ranking share by major topic, first and last period), Figure 5 slope chart
    inputs (already in the JSON) and Figure 6 summary rows (all applied preprocessing steps; survey-cycle comparison)."""
    out = dict(o)
    groups = [[d for d in CORE if m.period(int(d["metadata"]["publication_year"])) == p] for p in PERIODS]
    fam = lambda d, names: bool(set(EXP[d["study_id"]]["algorithm_development"]["algorithm_family"]) & set(names))
    out["algorithm_families_by_period"] = {lab: [sum(fam(d, names) for d in g) for g in groups] for lab, names in (
        ("boosting", {"XGBoost", "LightGBM", "Gradient boosting"}), ("random_forest", {"Random forest"}),
        ("logistic_regression", {"Logistic regression"}), ("svm", {"SVM"}), ("neural_network", {"DNN/MLP"}))}
    cls_a = [x for x in EXP.values() if x["task_group"] == "CLS" and x["study_id"] in {d["study_id"] for d in CORE}]
    tm = Counter(x["algorithm_development"]["hyperparameter_tuning_method"] for x in cls_a)
    csum = m.classification_summary(CORE)
    vc, q, mr = csum["validation"], csum["metrics"], csum["metric_reporting"]
    out["familiar_evaluation"] = {
        "n": len(CORE),
        "algorithms_compared": sum(m.has(d, "FUN_COMPARE", {"PRESENT"}) for d in CORE),
        "systematic_tuning_search": sum(tm[k] for k in ("RANDOM_SEARCH", "BAYESIAN_OR_OTHER_OPTIMISATION", "GRID_SEARCH", "OTHER_REPORTED")),
        "train_test_split": vc["SPLIT"], "cross_validation": vc["CV"], "auroc": q["AUROC"], "confidence_interval": mr["MET_CI"]}
    src = Counter(c for d in CORE for c in outcome_source_codes(d))
    out["classified_outcome"] = {
        "n": len(CORE), "current_state_same_survey": o["use_composition"]["classify_current_state"],
        "timing_unclear": o["use_composition"]["classification_timing_unclear"], "future_event": 0,
        "source": {"questionnaire_or_scale": src["VALIDATED_QUESTIONNAIRE_OR_SCALE"], "physical_measurement": src["CLINICAL_OR_PHYSICAL_MEASUREMENT"],
                   "laboratory_value": src["LABORATORY_THRESHOLD"], "diagnosis_or_history": src["SELF_REPORTED_DIAGNOSIS"] + src["PHYSICIAN_DIAGNOSIS"],
                   "other_or_not_reported": src["OTHER_REPORTED_SOURCE"] + src["DATA_DERIVED_CLASS"] + src["COMPOSITE_DEFINITION"] + src["NOT_REPORTED"]}}
    topic = lambda d: m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"]
    rank = PRACTICES["importance_ranking"]
    out["ranking_by_topic_period"] = {t: {"n": [sum(topic(d) == t for d in g) for g in groups],
                                          "ranking": [sum(topic(d) == t and rank(d) for d in g) for g in groups]}
                                      for t in ("METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR")}
    applied = sum(o["preprocessing_applied"])
    within = sum(o["preprocessing_all_within"])
    out["preprocessing_summary"] = {"applied": applied, "all_within_training": within,
                                    "any_before_split": o["any_step_before_split_total"],
                                    "unclear_only": applied - within - o["any_step_before_split_total"]}
    named = ("SHAP", "MODEL_NATIVE", "COEFFICIENT_STATISTIC", "PERMUTATION")
    small = {"TREE_RULE", "PERTURBATION_ABLATION", "LIME", "PDP"}
    main_named = set(named) | small
    out["importance_methods_grouped"] = {**{k: o["importance_methods"][k] for k in named},
                                         "OTHER_GROUPED": sum(bool(set(m.flat_values(d, "VI02")) - main_named - {"NA", "NR", "NOT_USED"} or
                                                                   set(m.flat_values(d, "VI02")) & small) for d in CORE if PRACTICES["importance_ranking"](d))}
    out["stability_by_survey_cycle"] = 0  # no study compared rankings across survey cycles (check_096 asserts the code is absent)
    return out


def check_099(o):
    af = o["algorithm_families_by_period"]
    _pin(af["boosting"], [1, 15, 34, 42], "practice_trends.py:593")  # prompt 106 pin
    fe = o["familiar_evaluation"]
    _pin((fe["algorithms_compared"], fe["systematic_tuning_search"], fe["train_test_split"], fe["cross_validation"], fe["auroc"],             fe["confidence_interval"]), (132, 95, 116, 79, 134, 57), "practice_trends.py:595")  # prompt 106 pin
    co = o["classified_outcome"]
    _pin((co["current_state_same_survey"], co["timing_unclear"]), (164, 1), "practice_trends.py:598")  # prompt 106 pin
    _pin(sum(co["source"].values()), 165, "practice_trends.py:598")  # prompt 106 pin
    rt = o["ranking_by_topic_period"]
    _pin(rt["METABOLIC_ENDOCRINE"], {"n": [7, 7, 13, 16], "ranking": [2, 5, 13, 15]}, "practice_trends.py:600")  # prompt 106 pin
    _pin(o["importance_methods_grouped"]["SHAP"], 57, "practice_trends.py:601")  # prompt 106 pin
    ps = o["preprocessing_summary"]
    _pin((ps["applied"], ps["all_within_training"], ps["any_before_split"]), (163, 15, 83), "practice_trends.py:603")  # prompt 106 pin


def build_100(o):
    """Prompt 100 (review v38, straight storyline): values for the workflow-ordered Figure 2 (B purpose and task,
    D outcome structure, E predictor data) and the four-topic domain columns of Figure 3B."""
    import numpy as np
    out = dict(o)
    scheme = Counter()
    for d in CORE:
        scales = set(m.flat_values(d, "OUT09"))
        units = {x.get("unit_id") for x in d.get("protocol_items", {}).get("OUT09", []) if x.get("value") == "BINARY"}
        if len(scales) > 1: scheme["MIXED"] += 1
        elif "MULTICLASS" in scales: scheme["MULTICLASS"] += 1
        elif "MULTIBIN" in scales or len(units) > 1: scheme["MULTIBIN"] += 1
        else: scheme["BINARY"] += 1
    out["outcome_structure"] = {k: scheme[k] for k in ("BINARY", "MULTIBIN", "MULTICLASS", "MIXED")}
    vals = []
    for d in CORE:
        fld = d.get("adjudication", {}).get("analytic_flow", {}).get("fields", {}).get("initial_candidate_predictor_count", {})
        v = fld.get("value")
        if fld.get("value_status") == "REPORTED" and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            vals.append(float(v))
    q1, med, q3 = np.percentile(vals, [25, 50, 75])
    out["candidate_predictors"] = {"reported": len(vals), "median": float(med), "q1": float(q1), "q3": float(q3)}
    uc = o["use_composition"]
    out["task_composition"] = {
        "health": {"classification": uc["classify_current_state"] + uc["classification_timing_unclear"],
                   "continuous_or_ordered": uc["estimate_continuous_or_ordered"], "other": uc["other_health_analyses"]},
        "method": {"develop_or_improve": uc["develop_or_improve_method"], "compare_existing": uc["compare_existing_methods"]}}
    out["domain_topics_at_least_ten"] = [t for t, v in o["ranking_domains_by_topic"].items() if v["n"] >= 10 and t != "OTHER_OR_CROSS_CUTTING"]  # prompt 106: the residual category is not a topic
    return out


def check_100(o):
    _pin(o["outcome_structure"], {"BINARY": 130, "MULTIBIN": 25, "MULTICLASS": 6, "MIXED": 4}, "practice_trends.py:638")  # prompt 106 pin
    c = o["candidate_predictors"]
    _pin((c["reported"], c["median"], c["q1"], c["q3"]), (61, 23.0, 14.0, 48.0), "practice_trends.py:640")  # prompt 106 pin
    t = o["task_composition"]
    _pin(t, {"health": {"classification": 165, "continuous_or_ordered": 10, "other": 9},                  "method": {"develop_or_improve": 26, "compare_existing": 10}}, "practice_trends.py:642")  # prompt 106 pin
    _pin(sum(t["health"].values()), 184, "practice_trends.py:644")  # prompt 106 pin
    _pin(sum(t["method"].values()), 36, "practice_trends.py:644")  # prompt 106 pin
    _pin(o["domain_topics_at_least_ten"], ["METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR"], "practice_trends.py:645")  # prompt 106 pin
    _pin(o["survey_components_220"]["EXAMINATION"], 191, "practice_trends.py:646")  # prompt 106 pin
    _pin(o["survey_components_220"]["LABORATORY"], 128, "practice_trends.py:646")  # prompt 106 pin
    _pin(o["survey_year_scope_220"]["MULTI_CROSS"], 121, "practice_trends.py:647")  # prompt 106 pin
    _pin(o["preprocessing_applied_rows"]["scaling_or_other_preprocessing"], o["preprocessing_summary"]["applied"],
         "practice_trends.py check_100 scaling rows = applied studies")  # review 20261023: data property, not a rule (fixed recodings are not PRE14)
    _pin(o["preprocessing_summary"]["applied"], 163, "practice_trends.py:669")  # prompt 106 pin
    _pin(o["rise_2026"]["validation"], 13, "practice_trends.py:649")  # prompt 106 pin
    _pin(o["rise_2026"]["calibration"], 12, "practice_trends.py:649")  # prompt 106 pin


def build_101(o):
    """Prompt 101 (review v39): Figure 2E on the 165 core studies (same denominator as 2D, 2F and 2G); the 220-study
    counts stay in Supplementary Figure S1B."""
    out = dict(o)
    comps = Counter(); [comps.update(set(m.flat_values(d, "DAT14"))) for d in CORE]
    out["survey_components_165"] = {k: comps[k] for k in ("HEALTH_INTERVIEW", "EXAMINATION", "LABORATORY", "ORAL_HEALTH", "NUTRITION")}
    return out


def check_101(o):
    c = o["survey_components_165"]
    _pin(c, {"HEALTH_INTERVIEW": 159, "EXAMINATION": 144, "LABORATORY": 99, "ORAL_HEALTH": 12, "NUTRITION": 48}, "practice_trends.py:663")  # prompt 106 pin
    assert all(c[k] <= o["survey_components_220"][k] for k in c), c
    _pin(o["core_year_scope"]["MULTI_CROSS"], 93, "practice_trends.py:665")  # prompt 106 pin
    _pin(o["familiar_evaluation"]["algorithms_compared"], 132, "practice_trends.py:666")  # prompt 106 pin
    _pin(o["familiar_evaluation"]["systematic_tuning_search"], 95, "practice_trends.py:666")  # prompt 106 pin


SELECTED_FAMILY = [("Boosting", r"xgboost|\bxgb|lightgbm|\blgbm|catboost|adaboost|samme|gradient boost|\bgbm\b|boost"),
                   ("Neural network", r"\bmlp|neural|\bdnn|\bann\b|perceptron|\bcnn|lstm|deep|transformer"),
                   ("Logistic regression", r"logistic|\blr\b"),
                   ("Random forest", r"random forest|\brf\b|extra.?trees"),
                   ("SVM", r"\bsvm|support vector"),
                   ("Other", r".")]


def build_104(o):
    """Prompt 104 (review v42): Figure 2 grows to A-K. F final analytic sample of the core studies (log scale);
    G initial candidate predictors (reported in 61); H missing-value handling (method; timing is Figure 5C);
    J family of the first-listed model the authors selected (G_author_selected_model, as the Table S8 bold marker)
    among the 132 core studies comparing several algorithms (FUN_COMPARE). Ensembles, trees, naive Bayes and the rest
    are Other; the selection criterion is not coded."""
    import re
    import statistics
    from openpyxl import load_workbook
    out = dict(o)
    wb = load_workbook(WORKBOOK(), read_only=True)
    it = wb["STUDIES"].iter_rows(values_only=True)
    hdr = list(next(it)); ix = {h: i for i, h in enumerate(hdr)}
    core_ids = {d["study_id"] for d in CORE}
    cmp_ids = {d["study_id"] for d in CORE if m.has(d, "FUN_COMPARE", {"PRESENT"})}
    ns, fam = [], Counter()
    for r in it:
        sid = r[ix["A_study_id"]]
        if sid not in core_ids:
            continue
        n = str(r[ix["D_final_sample"]]).split("|")[0].strip()
        if n.isdigit():
            ns.append(int(n))
        if sid in cmp_ids:
            chosen = str(r[ix["G_author_selected_model"]]).split("|")[0].strip().lower()
            fam[next(f for f, pat in SELECTED_FAMILY if re.search(pat, chosen))] += 1
    q1, med, q3 = statistics.quantiles(ns, n=4)
    out["core_sample"] = {"values": sorted(ns), "reported": len(ns), "median": med, "q1": q1, "q3": q3}
    flow = lambda d: d.get("adjudication", {}).get("analytic_flow", {}).get("fields", {})
    vals = []
    for d in CORE:
        fld = flow(d).get("initial_candidate_predictor_count", {}); v = fld.get("value")
        if fld.get("value_status") == "REPORTED" and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            vals.append(float(v))
    out["candidate_predictor_values"] = sorted(vals)
    mc = m.classification_summary(CORE)["missing_strategy"]
    out["missing_handling_165"] = {"complete_case": mc.get("COMPLETE", 0), "single_imputation": mc.get("SINGLE_IMP", 0),
                                   "multiple_imputation": mc.get("MULTI_IMP", 0), "model_native": mc.get("MODEL_NATIVE", 0),
                                   "other_or_several": sum(mc.get(k, 0) for k in ("MULTIPLE", "INDICATOR", "OTHER")),
                                   "not_reported": mc.get("NR", 0)}
    out["selected_model_family"] = {"n": len(cmp_ids), **{f: fam[f] for f, _ in SELECTED_FAMILY}}
    return out


def check_104(o):
    cs = o["core_sample"]
    _pin(cs["reported"], 162, "practice_trends.py:723")  # prompt 106 pin
    _pin(round(cs["median"]), 7262, "practice_trends.py:723")  # prompt 106 pin
    assert len(o["candidate_predictor_values"]) == o["candidate_predictors"]["reported"]
    _pin(o["candidate_predictors"]["reported"], 61, "practice_trends.py:748")  # prompt 106 pin
    mh = o["missing_handling_165"]
    _pin(list(mh.values()), [97, 27, 6, 1, 10, 24], "practice_trends.py:726")  # prompt 106 pin
    _pin(sum(mh.values()), 165, "practice_trends.py:726")  # prompt 106 pin
    sf = o["selected_model_family"]
    _pin(sf["n"], 132, "practice_trends.py:728")  # prompt 106 pin
    _pin(sum(v for k, v in sf.items() if k != "n"), 132, "practice_trends.py:728")  # prompt 106 pin
    _pin(max((v, k) for k, v in sf.items() if k != "n")[1], "Boosting", "practice_trends.py:729")  # prompt 106 pin


# author decision D17 (2026-10-23): "Not reported" when the authors designated no model
SELECTED_FAMILY_107 = [("Not designated", r"^(not reported|not designated)$")] + SELECTED_FAMILY[:4] + [("Decision tree", r"decision tree|\bcart\b|chaid|c4\.5|\bdt\b")] + SELECTED_FAMILY[4:]
FITTED_FAMILIES_107 = [("boosting", {"XGBoost", "LightGBM", "Gradient boosting"}), ("random_forest", {"Random forest"}),
                       ("logistic_regression", {"Logistic regression"}), ("decision_tree", {"Decision tree"}), ("svm", {"SVM"}),
                       ("neural_network", {"DNN/MLP"})]


def build_107(o):
    """Prompt 107 (review v44, fixed denominators): every panel after Figure 2 counts all 192 core studies, with the
    studies that did not report a value (not reported) and those to which a step did not apply (not applicable) kept
    as their own bars. New values: the survey years used by the core studies (Figure 2D), the health topic of the 192
    (Figure 2C), algorithm families fitted over the 192 (Figure 3F), the selected-model family with decision trees split
    out plus the single-algorithm studies (Figure 3G), and the not-applicable counts of Figure 6."""
    import re
    from openpyxl import load_workbook
    out = dict(o)
    core_ids = {d["study_id"] for d in CORE}
    wb = load_workbook(WORKBOOK(), read_only=True)
    it = wb["STUDIES"].iter_rows(values_only=True)
    hdr = list(next(it)); ix = {h: i for i, h in enumerate(hdr)}
    cmp_ids = {d["study_id"] for d in CORE if m.has(d, "FUN_COMPARE", {"PRESENT"})}
    years, nr, fam = Counter(), 0, Counter()
    for r in it:
        sid = r[ix["A_study_id"]]
        if sid not in core_ids:
            continue
        ys = {int(y) for y in re.findall(r"(?:19|20)\d{2}", str(r[ix["C_survey_years"]]))}
        if ys:
            years.update(ys)
        else:
            nr += 1
        if sid in cmp_ids:
            chosen = str(r[ix["G_author_selected_model"]]).split("|")[0].strip().lower()
            fam[next(f for f, pat in SELECTED_FAMILY_107 if re.search(pat, chosen))] += 1
    out["core_survey_years"] = {"counts": {str(y): years[y] for y in sorted(years)}, "not_reported": nr, "n": len(CORE)}
    out["core_topics"] = dict(Counter(m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"] for d in CORE).most_common())
    fams = lambda d: set(EXP[d["study_id"]]["algorithm_development"]["algorithm_family"])
    named = set().union(*(s for _, s in FITTED_FAMILIES_107))
    out["algorithms_fitted_192"] = {**{k: sum(bool(fams(d) & s) for d in CORE) for k, s in FITTED_FAMILIES_107},
                                    "other": sum(bool(fams(d) - named) for d in CORE), "n": len(CORE)}
    out["selected_model_family_192"] = {"n": len(CORE), **{f: fam[f] for f, _ in SELECTED_FAMILY_107},
                                        "single_algorithm": len(CORE) - len(cmp_ids)}
    src = Counter(c for d in CORE for c in outcome_source_codes(d))
    out["outcome_other_vs_not_reported"] = {"other": src["OTHER_REPORTED_SOURCE"] + src["DATA_DERIVED_CLASS"] + src["COMPOSITE_DEFINITION"],
                                            "not_reported": src["NOT_REPORTED"]}
    st = o["survey_design_stages"]
    out["survey_design_192"] = {k: {"used": v["used"], "not_used": v["applicable"] - v["used"], "not_applicable": len(CORE) - v["applicable"]}
                                for k, v in st.items()}
    ps = o["preprocessing_summary"]
    out["preprocessing_192"] = {"all_applied_steps": {"WITHIN": ps["all_within_training"], "BEFORE": ps["any_before_split"],
                                                      "UNCLEAR": ps["unclear_only"], "NA": len(CORE) - ps["applied"]},
                                **{k: {z: v[z] for z in ("WITHIN", "BEFORE", "UNCLEAR", "NA")} for k, v in o["preprocessing_timing"].items()}}
    # review 20261023 (Codex rule 4): of the feature-selection "not applied" studies, those that did not report whether
    # variables were selected (PRE11 NR/UNC) are shown as not reported; the computations keep them as not applied.
    out["feature_selection_not_reported"] = sum(feature_selection_not_reported(d) for d in CORE)
    return out


def check_107(o):
    n = len(CORE)
    sy = o["core_survey_years"]
    assert 0 < sy["not_reported"] < n and max(sy["counts"].values()) <= n, sy
    tp = o["core_topics"]
    assert sum(tp.values()) == n, tp
    af = o["algorithms_fitted_192"]
    assert af["boosting"] == sum(o["practices"]["boosting"]), af
    sm = o["selected_model_family_192"]
    assert sum(v for k, v in sm.items() if k not in ("n", "single_algorithm")) + sm["single_algorithm"] == n, sm
    assert sm["Boosting"] == o["selected_model_family"]["Boosting"]  # the decision-tree row only splits "Other"
    assert sm["single_algorithm"] + o["selected_model_family"]["n"] == n
    ov = o["outcome_other_vs_not_reported"]
    assert sum(ov.values()) == o["classified_outcome"]["source"]["other_or_not_reported"], ov
    for k, v in o["survey_design_192"].items():
        assert sum(v.values()) == n, (k, v)
    for k, v in o["preprocessing_192"].items():
        assert sum(v.values()) == n, (k, v)
    assert o["preprocessing_192"]["all_applied_steps"]["NA"] == n - o["preprocessing_summary"]["applied"]
    _pin((n - o["candidate_predictors"]["reported"], n - o["core_sample"]["reported"]), (118, 3), "practice_trends.py:837 NR bars")  # review 20261023 pin


def build_108(o):
    """Prompt 108 (review v45): Figure 6A on all 192 core studies (checked / not checked / no ranking), and the counts
    behind three caption lines: which studies were not applicable for combined-year weights, why six studies lack
    survey years but only five have an unclear pooling scope, and how complete-case handling maps to "step not applied"."""
    import re
    from openpyxl import load_workbook
    out = dict(o)
    first = lambda d, k: (m.flat_values(d, k) or ["NR"])[0]
    scope = {d["study_id"]: m.first(d, "DAT08", "UNC") for d in CORE}
    rank = [d for d in CORE if PRACTICES["importance_ranking"](d)]
    checked = sum(m.has(d, "VI16", {"USED"}) for d in rank)
    out["stability_192"] = {"checked": checked, "not_checked": len(rank) - checked, "no_ranking": len(CORE) - len(rank)}
    na = Counter(scope[d["study_id"]] for d in CORE if first(d, "SUR11") == "NA")
    out["combined_weights_na_by_scope"] = {k: na[k] for k in ("ONE_YEAR", "MULTI_SAME", "MULTI_CROSS", "UNC")}
    wb = load_workbook(WORKBOOK(), read_only=True)
    it = wb["STUDIES"].iter_rows(values_only=True)
    hdr = list(next(it)); ix = {h: i for i, h in enumerate(hdr)}
    no_years = {r[ix["A_study_id"]] for r in it if r[ix["A_study_id"]] in scope
                and not re.findall(r"(?:19|20)\d{2}", str(r[ix["C_survey_years"]]))}
    out["survey_years_vs_scope"] = {"years_not_reported": len(no_years), "scope_unclear": sum(v == "UNC" for v in scope.values()),
                                    "years_not_named_scope_known": dict(Counter(scope[i] for i in no_years if scope[i] != "UNC"))}
    spec = PRE_SPECS[0]
    assert spec[0] == "missing_value_handling"
    cc = Counter((m.categorical_methods(d, "PRE01"), preprocessing_status(d, *spec[1:])) for d in CORE)
    out["missing_step_not_applied"] = {"complete_case": cc[("COMPLETE", "NA")],
                                       "other_methods": sum(v for (mm, st), v in cc.items() if st == "NA" and mm != "COMPLETE"),
                                       "complete_case_with_timing": sum(v for (mm, st), v in cc.items() if mm == "COMPLETE" and st != "NA")}
    return out


def check_108(o):
    n = len(CORE)
    sb = o["stability_192"]
    assert sum(sb.values()) == n and sb["checked"] == sum(o["stability_among_ranking"]), sb
    assert sb["checked"] + sb["not_checked"] == o["importance_ranking_total"], sb
    na = o["combined_weights_na_by_scope"]
    assert sum(na.values()) == n - o["survey_design_stages"]["combined_cycle_weights"]["applicable"], na
    assert na["ONE_YEAR"] == o["core_year_scope"]["ONE_YEAR"], na  # every one-year study is n/a; the rest are the extra ones
    sv = o["survey_years_vs_scope"]
    assert sv["years_not_reported"] == o["core_survey_years"]["not_reported"], sv
    assert sv["years_not_reported"] - sv["scope_unclear"] == sum(sv["years_not_named_scope_known"].values()), sv
    ms = o["missing_step_not_applied"]
    assert ms["complete_case"] + ms["other_methods"] == o["preprocessing_192"]["missing_value_handling"]["NA"], ms
    assert ms["complete_case"] + ms["complete_case_with_timing"] == o["missing_handling_165"]["complete_case"], ms


def build_109(o):
    """Prompt 109 (review v46): Table 1 = methodological practices by publication period (45/35/59/53; all 192).
    Each row reuses the definition behind the figure or sentence that reports it overall; asserted against those totals."""
    out = dict(o)
    g = groups()
    core_ids = {d["study_id"] for d in CORE}
    first = lambda d, k: (m.flat_values(d, k) or ["NR"])[0]
    cls_by_id = {x["study_id"]: x for x in EXP.values() if x["task_group"] == "CLS" and x["study_id"] in core_ids}
    sys_tune = ("RANDOM_SEARCH", "BAYESIAN_OR_OTHER_OPTIMISATION", "GRID_SEARCH", "OTHER_REPORTED")

    def cand(d):
        fld = d.get("adjudication", {}).get("analytic_flow", {}).get("fields", {}).get("initial_candidate_predictor_count", {})
        v = fld.get("value")
        return fld.get("value_status") == "REPORTED" and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0

    def applied(d):
        return [s_ for s_ in (preprocessing_status(d, k, w, b, u) for _, k, w, b, u in PRE_SPECS) if s_ != "NA"]

    def auroc(d):
        return m.classification_summary([d])["metrics"].get("AUROC", 0) > 0

    rows = {
        "outcome_rebuildable": lambda d: m.reduce_recoverability(d, "OUT16") == "FULL",
        "predictor_set_rebuildable": lambda d: m.reduce_recoverability(d, "PRD13") == "FULL",
        "candidate_predictors_reported": cand,
        "preprocessing_all_within": lambda d: bool(applied(d)) and all(x == "WITHIN" for x in applied(d)),
        "preprocessing_any_before": any_before,
        "algorithms_compared": lambda d: m.has(d, "FUN_COMPARE", {"PRESENT"}),
        "systematic_tuning_search": lambda d: cls_by_id.get(d["study_id"], {}).get("algorithm_development", {}).get("hyperparameter_tuning_method") in sys_tune,
        "tuning_kept_apart": lambda d: ce.tuning_status(d) in ("TUNING_REPORTED_SEPARATED", "NO_TUNING_OR_DEFAULT_MODEL"),
        "auroc": auroc,
        "calibration": PRACTICES["calibration"],
        "validation_beyond_development": PRACTICES["validation_beyond_development"],
        "importance_ranking": PRACTICES["importance_ranking"],
        "shap": PRACTICES["shap"],
        "stability": lambda d: PRACTICES["importance_ranking"](d) and m.has(d, "VI16", {"USED"}),
        "weights_mentioned": lambda d: m.has(d, "SUR04", {"USED"}),
        "weights_in_fitting": lambda d: first(d, "SUR06") == "USED",
        "weights_in_evaluation": lambda d: first(d, "SUR07") == "USED",
        "strata_or_psu": lambda d: first(d, "SUR10") == "USED",
        "combined_year_weights": lambda d: first(d, "SUR11") == "USED",
        "code_shared": PRACTICES["code_link"],
        "final_model_fully_specified": lambda d: m.has(d, "REP17", {"R"}),
    }
    out["table1_by_period"] = {"period_n": [len(x) for x in g], "n": len(CORE),
                               **{k: [sum(map(f, x)) for x in g] for k, f in rows.items()}}
    return out


def check_109(o):
    t = o["table1_by_period"]
    assert t["period_n"] == o["period_n"] and t["n"] == len(CORE) == sum(t["period_n"])
    tot = {k: sum(v) for k, v in t.items() if isinstance(v, list) and k != "period_n"}
    r, fe, sd, ps = o["reproducibility"], o["familiar_evaluation"], o["survey_design_stages"], o["preprocessing_summary"]
    exp = {"outcome_rebuildable": r["outcome_fully_specified"], "predictor_set_rebuildable": r["predictor_set_rebuildable"],
           "candidate_predictors_reported": o["candidate_predictors"]["reported"],
           "preprocessing_all_within": ps["all_within_training"], "preprocessing_any_before": ps["any_before_split"],
           "algorithms_compared": fe["algorithms_compared"], "systematic_tuning_search": fe["systematic_tuning_search"],
           "tuning_kept_apart": r["tuning_kept_apart"], "auroc": fe["auroc"],
           "calibration": sum(o["practices"]["calibration"]), "validation_beyond_development": sum(o["practices"]["validation_beyond_development"]),
           "importance_ranking": o["importance_ranking_total"], "shap": sum(o["practices"]["shap"]),
           "stability": sum(o["stability_among_ranking"]), "weights_mentioned": sd["any_weight_mention"]["used"],
           "weights_in_fitting": sd["weights_in_fitting"]["used"], "weights_in_evaluation": sd["weights_in_evaluation"]["used"],
           "strata_or_psu": sd["strata_or_psu_in_variance"]["used"], "combined_year_weights": sd["combined_cycle_weights"]["used"],
           "code_shared": sum(o["practices"]["code_link"]), "final_model_fully_specified": sum(o["little_changed"]["final_model_fully_specified"])}
    bad = {k: (tot[k], v) for k, v in exp.items() if tot[k] != v}
    assert not bad, bad
    assert t["tuning_kept_apart"] == o["little_changed"]["tuning_kept_apart"]
    assert t["predictor_set_rebuildable"] == o["little_changed"]["predictor_set_rebuildable"]
    assert t["stability"] == o["stability_among_ranking"] and t["code_shared"] == o["practices"]["code_link"]


ROMANISED_SURNAME = {"김": "Kim", "이": "Lee", "박": "Park", "최": "Choi", "정": "Jung", "강": "Kang", "조": "Cho", "윤": "Yoon",
                     "장": "Jang", "임": "Lim", "한": "Han", "오": "Oh", "서": "Seo", "신": "Shin", "권": "Kwon", "황": "Hwang",
                     "안": "Ahn", "송": "Song", "전": "Jeon", "홍": "Hong", "유": "Yoo", "고": "Ko", "문": "Moon", "양": "Yang",
                     "손": "Son", "배": "Bae", "백": "Baek", "허": "Heo", "남": "Nam", "노": "Noh", "하": "Ha", "곽": "Kwak"}


def first_author_surname(authors):
    """Surname of the first listed author as printed in the study record: "Surname INITIALS" keeps the first token,
    "Given Surname" keeps the last, a Korean name is romanised by its first syllable."""
    first = str(authors).split("|")[0].strip().replace(",", " ").replace("，", " ")
    if first and "\uac00" <= first[0] <= "\ud7a3":
        return ROMANISED_SURNAME[first[0]]
    parts = first.split()
    if len(parts) >= 2 and len(parts[-1]) <= 3 and parts[-1].isupper():
        return parts[0]
    return parts[-1]


def build_110(o):
    """Prompt 110 (review v47): study labels for Figure 4C, the topic-mix test for the Results, threshold counts."""
    import openpyxl
    out = dict(o)
    wb = openpyxl.load_workbook(WORKBOOK(), read_only=True)
    it = wb["STUDIES"].iter_rows(values_only=True); hdr = next(it)
    rows = {r[hdr.index("A_study_id")]: dict(zip(hdr, r)) for r in it}
    dp = dict(o["diabetes_variable_panel"]); studies = []
    base = {}
    for st in dp["studies"]:
        r = rows[st["id"]]
        lab = f"{first_author_surname(r['A_authors'])} {r['A_publication_year']}"
        assert int(r["A_publication_year"]) == int(st["year"]), st["id"]
        base.setdefault(lab, []).append(st["id"])
        studies.append(dict(st, label=lab))
    for lab, ids in base.items():  # same surname and year: a, b in study-ID order
        if len(ids) > 1:
            for k, sid in enumerate(sorted(ids)):
                next(x for x in studies if x["id"] == sid)["label"] = f"{lab}{'abcdefgh'[k]}"
    dp["studies"] = studies
    out["diabetes_variable_panel"] = dp
    temporal = json.loads((ROOT / "results/derived/exploratory_temporal_practice_analysis.json").read_text())
    hc = temporal["health_focused_classification"]
    assert hc["period_denominators"] == o["period_n"]
    out["topic_mix_test"] = {"monte_carlo_chi_square_p": hc["health_topics"]["monte_carlo_chi_square_p"],
                             "cramers_v": hc["health_topics"]["cramers_v"], "period_n": hc["period_denominators"]}
    return out


def check_110(o):
    labs = [st["label"] for st in o["diabetes_variable_panel"]["studies"]]
    assert len(labs) == len(set(labs)), labs
    _pin(len(labs), 16, "practice_trends.py:1007 diabetes panel")  # review 20261023 pin
    assert all(l.split()[-1][:4].isdigit() for l in labs)
    _pin(round(o["topic_mix_test"]["monte_carlo_chi_square_p"], 2), 0.52, "practice_trends.py:1009 topic mix p")  # review 20261023 pin


# ----------------------------------------------------------------- prompt 112 (review v49): Figure 5 data
VARIABLE_FAMILIES = ["Person", "Body", "Behaviour", "Mind and pain", "Clinical and laboratory"]
# label, family, extracted domains that confirm it (VI07), pattern on the recorded variable name. First match wins.
HARMONISED_VARIABLES = [
    ("Family history of diabetes", "Clinical and laboratory", ("GLYCAEMIA_DIABETES", "WORK_CLINICAL_HISTORY", "OTHER"),
     r"family history of diabetes|당뇨가족력|^family history$"),
    ("Age", "Person", ("AGE",), r"^(age_n|age1|age\d+|age level|age group|age groups|연령|나이)\b|^age\b(?!-related| when| of onset| at (menopause|menarche|first|last|diagnosis|onset|giving|osteo|hypert|angina|dyslip))|age at enrollment|mother's age|\bchild(?:'s)? age\b"),
    ("Sex", "Person", ("SEX",), r"\bsex\b|gender|\bfemale\b|\bmale\b|\bwomen\b|\bmen\b|성별"),
    ("Education, income or occupation", "Person", ("SOCIOECONOMIC", "WORK_CLINICAL_HISTORY"),
     r"educ|\bedu\b|school|graduate|college|university degree|academic|income|incm|ainc|\bpir\b|livelihood|소득|기초생활|insurance|"
     r"occup|occp|\bjob\b|employ|worker|working|work week|work stress|economic activity|ec_wht|직업|교육|labor|labour|compensation|ergonomic|hazardous substances|\bec1_\d|경제활동|economic status"),
    ("Marital status or household", "Person", ("SOCIOECONOMIC", "OTHER"),
     r"marri|marital|marriage|widow|divorc|spouse|living alone|living arrangement|living status|household (members|composition)|"
     r"number of households|household_composition|number_of_family|family structure|cfam|cohabitation|house_ownership|^house$|house ownership|home ?ownership|1인 가구|독거"),
    ("Region or residence", "Person", ("SOCIOECONOMIC", "OTHER"), r"region|residen|거주|live_t|housing|\burban|rural|\barea\b|metropolitan|apartment|park_area|_dist\b"),
    ("Waist circumference or WHtR", "Body", ("ADIPOSITY_BODY_SIZE",), r"waist|whtr|he_wc|\bwc\b|abdominal obesity|neck circ|wc sds"),
    ("BMI", "Body", ("ADIPOSITY_BODY_SIZE",), r"\bbmi\b|body mass index|he_bmi|he_obe|(?<!abdominal )(?<!subjective )(?<!perceived )(?<!self-perceived )obes|overweight|체질량|bmi sds"),
    ("Height or weight", "Body", ("ADIPOSITY_BODY_SIZE",), r"height|\bweight\b(?! (control|management))|he_ht|he_wt|weight change|weight gain|\bbo1_1\b|body weight(?! control)|arm (length|circ)"),
    ("Body composition or grip", "Body", ("ADIPOSITY_BODY_SIZE", "PHYSICAL_ACTIVITY_FUNCTION"),
     r"body fat|fat mass|fat percentage|\bbfm\b|\bffm\b|bffmi|bsmi|wsmi|\basm\b|lean mass|\blra\b|\blla\b|\blrl\b|\blll\b|grip|sarcopen|dynapen|phase angle|\bpha\b|\bicw\b|\becw\b|\btbw\b|bia_"),
    ("Smoking", "Behaviour", ("SMOKING",), r"smok|cotinine|bs3_|bs2_|bs9_|sm_g|\bshs\b|cigarett|tobacco"),
    ("Alcohol", "Behaviour", ("ALCOHOL",), r"alcohol|drink|\bbd1_|\bbd2_|\bbd\b|audit|risk_drink|hr_drink|drunk|sobriety|음주"),
    ("Physical activity", "Behaviour", ("PHYSICAL_ACTIVITY_FUNCTION",),
     r"physical activity|exercise|운동|walking|(?<!equipment to )\bwalk|aerobic|strength training|resistance training|be3_|be5_|be8_|pa_|sitting|sedentary|vigorous|moderate pa|moderate-intensity|moderate physical"),
    ("Diet or nutrients", "Behaviour", ("DIET",),
     r"intake|diet|food|nutri|carbohydrate|(?<!urine )(?<!urinary )protein(?!uria)|\bfat\b|fatty acid|(?<!urine )(?<!urinary )sodium|potassium|calcium|vitamin|riboflavin|thiamine|fiber|energy|sugar|water|omega|"
     r"folate|retinol|phosphorus|magnesium|niacin|meal|breakfast|dinner|dining|eating|supplement|qfiber|qprotein|beta-carotene|\biron\b|monounsaturated|n-3|meat|lunch|weight control by skipping"),
    ("Sleep", "Behaviour", ("PHYSICAL_ACTIVITY_FUNCTION", "MENTAL_SUBJECTIVE_HEALTH", "OTHER"), r"sleep|slpwk|bp16_|\bbp8\b"),
    ("Stress", "Mind and pain", ("MENTAL_SUBJECTIVE_HEALTH",), r"stress|\bbp1\b"),
    ("Depression or mood", "Mind and pain", ("MENTAL_SUBJECTIVE_HEALTH", "WORK_CLINICAL_HISTORY"),
     r"depress|mood|sadness|despair|worthless|psychomotor|suicid|anxiety"),
    ("Self-rated health or quality of life", "Mind and pain", ("MENTAL_SUBJECTIVE_HEALTH", "OTHER"),
     r"perceived health|self-rated|subjective health|subjective_health|health status|health awareness|self-perceived health|self-reported health|health perception|"
     r"eq-?5d|eq-vas|euroqol|quality of life|\bqol\b|삶의질|lq_3eql|\bd_1_|perceived oral health|self-perceived oral|self-reported oral|body image|body-image|body shape|body-shape|subjective obesity|subjective body|\bbo1\b(?!_)|삶의 질"),
    ("Activity limitation or pain", "Mind and pain", ("PAIN_MUSCULOSKELETAL", "PHYSICAL_ACTIVITY_FUNCTION", "MENTAL_SUBJECTIVE_HEALTH"),
     r"activity restrict|activity limitation|restriction of activity|limitation|\bpain\b|discomfort|sick days|sickbed|usual activit|mobility|self-care|lq4_|\bd_2_|bedridden|stiff knee|knee pain|joint pain|toothache|equipment to walk|outdoor_activity|outdoor activity|육체적 불편"),
    ("HbA1c or fasting glucose", "Clinical and laboratory", ("GLYCAEMIA_DIABETES",), r"hba1c|glucose|\bfbg\b|\bglyc|he_glu|\bglu\b|insulin|homa|tyg|glycohemoglobin"),
    ("Cholesterol or triglycerides", "Clinical and laboratory", ("LIPIDS",),
     r"(?<!dietary )cholesterol|triglycer|\bldl|\bhdl|dyslip|\bdl\b|lipid|\btg\b|he_tg|\bchol\b|he_chol|\btc\b|\baip\b|hypercholest"),
    ("Hypertension or blood pressure", "Clinical and laboratory", ("BLOOD_PRESSURE",),
     r"(?<!family history of )hypertens|\bdi1_2\b|\bsbp\b|\bdbp\b|he_sbp|he_dbp|blood pressure|\bbp\b|systolic|diastolic|\bhtn\b|he_hp"),
    ("Diabetes diagnosis", "Clinical and laboratory", ("GLYCAEMIA_DIABETES", "WORK_CLINICAL_HISTORY"), r"(?<!family history of )diabet|당뇨|\bdm\b|dm_|he_dm|dme"),
    ("Liver enzymes", "Clinical and laboratory", ("OTHER", "WORK_CLINICAL_HISTORY"), r"\bast\b|\balt\b|\bgot\b|\bgpt\b|sgot|he_ast|he_alt|\balp\b|alkaline phosphatase|got_gpt|ast/alt"),
    ("Urine markers", "Clinical and laboratory", ("KIDNEY_URINE", "OTHER"), r"urine|urinary|he_upro|he_ubil|he_uph|specific gravity|\bph\b|proteinuria|^nitrate$|nitrite|unitr"),
    ("Kidney function or uric acid", "Clinical and laboratory", ("KIDNEY_URINE", "OTHER"), r"creatin|\bcrea\b|he_crea|\bbun\b|urea nitrogen|egfr|uric|uacid"),
    ("Blood count", "Clinical and laboratory", ("OTHER", "WORK_CLINICAL_HISTORY"),
     r"\bwbc\b|\brbc\b|hemoglobin|haemoglobin|hematocrit|\bhb\b|he_hb|anemi|anaemi|platelet|bplt|white blood|red blood|ferritin|he_wbc|eosinophil"),
    ("Other diagnosed conditions", "Clinical and laboratory", ("WORK_CLINICAL_HISTORY", "OTHER", "PAIN_MUSCULOSKELETAL"),
     r"stroke|\bcvd\b|cardiac|cardio|angina|myocard|heart|arthritis|asthma|cancer|hepatitis|hbsag|tubercul|thyroid|chronic disease|comorbid|osteopor|cataract|"
     r"rhinitis|disease|diagnos|periodont|caries|atopic|_dg\b|underlying|mi/angina|osteoarthritis|질병|family history|ischemic|medication|antihypert|lipid-lowering|macular degeneration|pterygium|renal failure|kidney failure"),
]
# Single-domain variables: the extracted domain alone confirms the variable (the domain coder saw the full report).
DOMAIN_IMPLIES = {"AGE": "Age", "SEX": "Sex", "SMOKING": "Smoking", "ALCOHOL": "Alcohol", "DIET": "Diet or nutrients",
                  "LIPIDS": "Cholesterol or triglycerides", "BLOOD_PRESSURE": "Hypertension or blood pressure"}
OUTCOME_PARENT = {"diabetes": "METABOLIC_ENDOCRINE", "metabolic syndrome": "METABOLIC_ENDOCRINE", "obesity": "METABOLIC_ENDOCRINE",
                  "dyslipidaemia": "METABOLIC_ENDOCRINE", "fatty liver": "METABOLIC_ENDOCRINE", "hypertension": "CARDIOVASCULAR",
                  "cardiovascular": "CARDIOVASCULAR", "kidney": "KIDNEY_UROLOGIC", "depression": "MENTAL_HEALTH", "suicide": "MENTAL_HEALTH",
                  "stress or anxiety": "MENTAL_HEALTH", "quality of life": "MENTAL_HEALTH", "bone": "MUSCULOSKELETAL",
                  "muscle": "MUSCULOSKELETAL", "arthritis or pain": "MUSCULOSKELETAL", "oral": "ORAL_HEALTH",
                  "hearing": "OTORHINOLARYNGOLOGIC", "respiratory or smoking": "RESPIRATORY"}
VAR_PREFIX = re.compile(r"^(?:[^:*]{0,40}:\s*)+")


def harmonised_label(name):
    low = name.lower().strip()
    low = VAR_PREFIX.sub("", low) if "*" not in low else low
    if re.search(r"management education|medication (adherence|compliance)|cancer screening|vaccin|dose series|urinary leakage|near-field working", low):
        return None  # review 20261024 (third reviewer): exposures and services, not the named condition or trait
    for lab_, pat_ in (("Self-rated health or quality of life", r"general health condition|days (physical |mental )?health was not good"),
                       ("Activity limitation or pain", r"inactive days"), ("Diabetes diagnosis", r"taking insulin"),
                       ("Other diagnosed conditions", r"ever told .*(liver|kidney|thyroid|cancer|asthma) condition")):
        if re.search(pat_, low):
            return lab_  # review 20261024 (both reviewers, KHM123 NHANES-style items)
    if re.search(r"family history|family \w+ history|fh\d|_fh|가족력|fraternal|paternal|maternal|close relative|relative had", low):  # review 20261023: a relative's disease is not the person's
        return "Family history of diabetes" if re.search(r"diabet|당뇨|dmfh|\bdm|t2d|t2dm", low) else "Other diagnosed conditions"
    for lab, fam, doms, pat in HARMONISED_VARIABLES:
        if re.search(pat, low):
            return lab
    return None


def named_variables_all(d):
    """named_variables() over every interpreted model (VI06 units), in recorded order."""
    out = []
    for x in d["protocol_items"].get("VI06", []):
        v = x.get("value")
        if v not in (None, "NA", "NR", ""):
            out += named_variables({"protocol_items": {"VI06": [{"value": v}]}})
    return out


def study_variables(d):
    """Harmonised variables a ranking study named as most important, confirmed by its extracted domains."""
    if (d["study_id"], "Harmonised variables (Figure 5)") in DERIVED:  # review loop, both reviewers
        v = DERIVED[(d["study_id"], "Harmonised variables (Figure 5)")]
        return {lab.strip(): 0 for lab in v.split(";") if lab.strip() and lab.strip() != "None harmonised"}
    dom = important_domains(d)
    fam = {lab: set(doms) for lab, _, doms, _ in HARMONISED_VARIABLES}
    found = {}
    for i, v in enumerate(named_variables_all(d), start=1):
        lab = harmonised_label(v)
        if d["study_id"] in NUTRIENT_ONLY and lab in ("Cholesterol or triglycerides", "Diabetes diagnosis", "HbA1c or fasting glucose"):
            lab = "Diet or nutrients"  # review 20261023: nutrient-intake indices (dietary cholesterol, sugar), as in the diabetes panel
        if lab and fam[lab] & dom and lab not in found:
            found[lab] = i
    for D, lab in DOMAIN_IMPLIES.items():
        if D in dom and lab not in found:
            found[lab] = 0  # named, position not recoverable from the recorded text
    return found


def study_outcome_row(d, topic):
    g = outcome_group(d)
    if g == "diabetes" and re.search(EXCLUDED_FROM_DIABETES, first_value(d, "OUT02").lower()):
        g = "other"
    g = DERIVED.get((d["study_id"], "Outcome group (Figure 5)"), g)  # review loop, both reviewers
    return (OUTCOME_PARENT[g], g) if g != "other" else (topic, "other")


def build_112(o):
    """Prompt 112 (review v49): data for the new Figure 5 (what the rankings named) and Figure 3C timing bar."""
    import numpy as np
    from scipy.cluster.hierarchy import linkage, leaves_list, dendrogram
    out = dict(o)
    rank = [d for d in CORE if PRACTICES["importance_ranking"](d)]
    topic = lambda d: m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"]
    var = {d["study_id"]: study_variables(d) for d in rank}
    labels = [lab for lab, _, _, _ in HARMONISED_VARIABLES]
    family = {lab: f for lab, f, _, _ in HARMONISED_VARIABLES}
    tot = Counter(l for v in var.values() for l in v)
    # Rows (prompt 112): the seven named topics of Figure 3A in its order, then "Other topics"; an outcome sits under the
    # topic its outcome group belongs to (OUTCOME_PARENT), so the diabetes row is the 16 studies of Figure 5B.
    cell = {}
    for d in rank:
        cell.setdefault(study_outcome_row(d, topic(d)), []).append(d["study_id"])
    topics = [t for t in o["core_topics"] if t not in ("KIDNEY_UROLOGIC", "OTHER_OR_CROSS_CUTTING")][:7]  # Figure 3A rows
    rows = []
    for t in topics:
        groups = [(g, ids) for (tt, g), ids in cell.items() if tt == t]
        named = [(g, ids) for g, ids in groups if g != "other" and len(ids) >= 5]
        pooled = [i for g, ids in groups if not (g != "other" and len(ids) >= 5) for i in ids]
        allids = sorted(i for _, ids in groups for i in ids)
        if len(named) >= 2:  # order outcome groups within the topic by their variable profiles (average linkage)
            prof = np.array([[sum(l in var[i] for i in ids) / len(ids) for l in labels] for _, ids in named])
            named = [named[k] for k in leaves_list(linkage(prof, "average", metric="euclidean"))]
            rows.append({"level": "topic", "topic": t, "group": "all", "ids": allids})
            rows += [{"level": "outcome", "topic": t, "group": g, "ids": sorted(ids)} for g, ids in named]
            if pooled:
                rows.append({"level": "outcome", "topic": t, "group": "other", "ids": sorted(pooled)})
        else:
            rows.append({"level": "topic", "topic": t, "group": "all", "ids": allids, "leaf": True})
    rest = sorted(i for (t, g), ids in cell.items() if t not in topics for i in ids)
    rows.append({"level": "topic", "topic": "OTHER_TOPICS", "group": "all", "ids": rest, "leaf": True})
    leaves = [r for r in rows if r["level"] == "outcome" or r.get("leaf")]
    assert sum(len(r["ids"]) for r in leaves) == sum(len(r["ids"]) for r in rows if r["level"] == "topic") == len(rank)
    _pin(len(rank), 154, "practice_trends.py:1151 ranking studies")  # review 20261023 pin
    # Columns: harmonised variables named by at least ten studies, family order, descending count within family.
    cols = [l for f in VARIABLE_FAMILIES for l in sorted((l for l in labels if family[l] == f and tot[l] >= 15), key=lambda l: -tot[l])]  # prompt 112: >= 15
    for r in rows:
        r["n"] = len(r["ids"])
        r["counts"] = {l: sum(l in var[i] for i in r["ids"]) for l in labels}
    allrow = {"n": len(rank), "counts": {l: tot[l] for l in labels}}
    # Data-only tree over the same rows (Supplementary Figure S7C).
    leaf_idx = [k for k, r in enumerate(rows) if r["level"] == "outcome" or r.get("leaf")]
    prof = np.array([[rows[k]["counts"][l] / rows[k]["n"] for l in cols] for k in leaf_idx])
    Z = linkage(prof, "average", metric="euclidean")
    out["rankings_named_112"] = {
        "families": VARIABLE_FAMILIES, "family": family, "columns": cols, "all": allrow, "rows": rows,
        "variables_per_study": {k: sorted(v) for k, v in sorted(var.items())},
        "dictionary": [{"variable": lab, "family": f, "confirming_domains": list(doms), "pattern": pat} for lab, f, doms, pat in HARMONISED_VARIABLES],
        "domain_implies": DOMAIN_IMPLIES,
        "data_tree": {"rows": leaf_idx, "linkage": Z.tolist(), "order": [int(i) for i in leaves_list(Z)]},
        "row_rule": "the seven named topics of Figure 3A, then other topics; outcome groups with at least five ranking studies shown under a topic with two or more such groups, other outcomes pooled",
        "column_rule": "harmonised variables named by at least 15 of the 154 studies; rarer variables pooled per family",
    }
    # Figure 5B: the diabetes row, study by study, from the same harmonised variables.
    dia = next(r for r in rows if r["group"] == "diabetes")
    by = {d["study_id"]: d for d in rank}
    lab_of = {st["id"]: st["label"] for st in o["diabetes_variable_panel"]["studies"]}
    panel = []
    for sid in dia["ids"]:
        d = by[sid]
        nm = named_variables_all(d)
        panel.append({"id": sid, "label": lab_of[sid], "year": int(d["metadata"]["publication_year"]),
                      "n_named": len({x.lower().strip() for x in nm}), "variables": sorted(var[sid])})
    out["diabetes_variable_panel_112"] = {"studies": panel}
    import statistics
    cnt_all = [len({x.lower().strip() for x in named_variables_all(d)}) for d in rank]
    q = statistics.quantiles(cnt_all, n=4, method="inclusive")
    strings = [v for d in rank for v in named_variables_all(d)]
    out["named_variable_count_all_models"] = {"n": len(cnt_all), "median": statistics.median(cnt_all), "q1": q[0], "q3": q[2],
                                              "min": min(cnt_all), "max": max(cnt_all), "strings": len(strings),
                                              "strings_mapped": sum(harmonised_label(v) is not None for v in strings)}
    co = o["classified_outcome"]
    out["outcome_timing_192"] = {"current_state_same_survey": co["current_state_same_survey"], "timing_unclear": co["timing_unclear"],
                                 "future_event": co["future_event"]}
    return out


def check_112(o):
    r = o["rankings_named_112"]
    _pin(r["all"]["n"], 154, "practice_trends.py:1197 ranking studies")  # review 20261023 pin
    c = r["all"]["counts"]
    _pin((c["Age"], c["Sex"]), (113, 62), "practice_trends.py:1199 age and sex")  # review 20261023 pin (extracted domains, VI07)
    assert sum(x["n"] for x in r["rows"] if x["level"] == "topic") == r["all"]["n"]
    dia = next(x for x in r["rows"] if x["group"] == "diabetes")
    assert dia["n"] == len(o["diabetes_variable_panel_112"]["studies"])
    _pin(dia["n"], 16, "practice_trends.py:1202 diabetes panel")  # review 20261023 pin
    t = o["outcome_timing_192"]
    assert sum(t.values()) == len(CORE) and t["future_event"] == 0


def build_113(o):
    """Prompt 113 (external publishability review): (1) sensitivity of the headline practices to the studies added under
    the final eligibility criterion (single decision trees); (2) survey design and preprocessing among the studies that
    produced a ranking and those that did not; (3) 2025 and 2026 separately; (4) ranking agreement in pairs whose lists
    name a similar number of domains."""
    import itertools
    import statistics
    out = dict(o)
    first = lambda d, k: (m.flat_values(d, k) or ["NR"])[0]
    t1 = {"ranking": PRACTICES["importance_ranking"], "shap": PRACTICES["shap"],
          "stability": lambda d: PRACTICES["importance_ranking"](d) and m.has(d, "VI16", {"USED"}),
          "weights_mentioned": lambda d: m.has(d, "SUR04", {"USED"}),
          "weights_in_fitting": lambda d: first(d, "SUR06") == "USED", "weights_in_evaluation": lambda d: first(d, "SUR07") == "USED",
          "strata_or_psu": lambda d: first(d, "SUR10") == "USED",
          "preprocessing_all_within": lambda d: bool(_applied(d)) and all(x == "WITHIN" for x in _applied(d)),
          "preprocessing_any_before": any_before, "code_shared": PRACTICES["code_link"], "calibration": PRACTICES["calibration"],
          "validation_beyond_development": PRACTICES["validation_beyond_development"]}
    tab = lambda s: {"n": len(s), **{k: sum(map(f, s)) for k, f in t1.items()}}
    verdicts = json.loads((ROOT / "results/derived/verdicts.json").read_text())
    added = {x.get("study_id") for x in verdicts.values() if x.get("criterion_a") and x["verdict"] == "INCLUDE"
             and x["criterion_a"].get("previous_verdict") == "INCLUDE_ADJACENT"}
    # review 20261023 (both reviewers): a study whose report entered under the old rule only through a linked record of the
    # same report that the old rule had set aside (single decision tree) also counts as added under the final criterion.
    rescreen = json.loads((ROOT / "results/derived/criterion_a_rescreen.json").read_text())
    added |= {m_.group(1) for x in rescreen["new_include"] if x.get("previous_verdict") == "INCLUDE_ADJACENT"
              for m_ in [re.search(r"same report as included (KHM\d+)", x.get("note", ""))] if m_}
    for (sid, col), v in DERIVED.items():  # review loop (both reviewers): flag set from the report's algorithms
        if col == "Added under the final eligibility criterion":
            (added.add if v == "Yes" else added.discard)(sid)
    added_core = sorted({d["study_id"] for d in CORE} & added)
    kept = [d for d in CORE if d["study_id"] not in added]
    g = groups()
    out["sensitivity_without_added_113"] = {
        "added_studies": len(added), "added_core": len(added_core), "added_core_ids": added_core, "added_ids": sorted(added - {None}),
        "all": tab(CORE), "without_added": tab(kept), "added_only": tab([d for d in CORE if d["study_id"] in added]),
        "by_period_without_added": {"period_n": [sum(d["study_id"] not in added for d in x) for x in g],
                                    "ranking": [sum(PRACTICES["importance_ranking"](d) for d in x if d["study_id"] not in added) for x in g]}}
    rank = [d for d in CORE if PRACTICES["importance_ranking"](d)]
    out["ranking_by_design_113"] = {"ranking": tab(rank), "no_ranking": tab([d for d in CORE if not PRACTICES["importance_ranking"](d)]),
                                    "ranking_stability_and_weights_in_fitting": sum(t1["stability"](d) and t1["weights_in_fitting"](d) for d in rank),
                                    "ranking_stability_and_training_only": sum(t1["stability"](d) and t1["preprocessing_all_within"](d) for d in rank)}
    year = lambda d: int(d["metadata"]["publication_year"])
    out["years_2025_2026_113"] = {"2025": tab([d for d in CORE if year(d) == 2025]), "2026": tab([d for d in CORE if year(d) == 2026])}
    # Ranking agreement (without age, sex and body size, as in the text) in pairs naming a similar number of domains.
    core3 = {"AGE", "SEX", "ADIPOSITY_BODY_SIZE"}
    og = {d["study_id"]: outcome_group(d) for d in rank}
    tp = {d["study_id"]: m.PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"] for d in rank}
    dom = {d["study_id"]: important_domains(d) - {"OTHER"} for d in rank}
    pairs = {"same_outcome": [], "different_topic": []}
    for a, b in itertools.combinations(sorted(dom), 2):
        k = "same_outcome" if og[a] != "other" and og[a] == og[b] else "different_topic" if tp[a] != tp[b] else None
        x, y = dom[a] - core3, dom[b] - core3
        if k and x | y and abs(len(dom[a]) - len(dom[b])) <= 1:
            pairs[k].append(len(x & y) / len(x | y))
    out["agreement_similar_length_113"] = {k: {"pairs": len(v), "median": round(statistics.median(v), 3)} for k, v in pairs.items()}
    # PROBAST+AI overall judgements counted in units (Supplementary Figure S8B), for the Discussion sentence.
    out["probast_overall_113"] = {k: dict(Counter(v for d in CORE for v in m.flat_values(d, k) if v != "NA"))
                                  for k in ("PD_OVERALL", "PE_OVERALL")}
    return out


def _applied(d):
    return [s_ for s_ in (preprocessing_status(d, k, w, b, u) for _, k, w, b, u in PRE_SPECS) if s_ != "NA"]


def check_113(o):
    s = o["sensitivity_without_added_113"]
    assert s["all"]["n"] == len(CORE), s["all"]
    _pin((s["all"]["n"], s["all"]["ranking"], s["all"]["weights_in_fitting"]), (192, 154, 9), "practice_trends.py:1266")  # review 20261023 pin
    assert s["without_added"]["n"] + s["added_core"] == len(CORE), s
    _pin(s["added_studies"], 32, "practice_trends.py:1267 added studies")  # review 20261023 pin
    assert all(s["all"][k] == s["without_added"][k] + s["added_only"][k] for k in s["all"])
    t = o["table1_by_period"]
    assert s["all"]["preprocessing_all_within"] == sum(t["preprocessing_all_within"]) and s["all"]["strata_or_psu"] == sum(t["strata_or_psu"])
    r = o["ranking_by_design_113"]
    assert r["ranking"]["n"] + r["no_ranking"]["n"] == len(CORE)
    _pin(r["ranking"]["n"], 154, "practice_trends.py:1272")  # review 20261023 pin
    assert all(r["ranking"][k] + r["no_ranking"][k] == s["all"][k] for k in s["all"])
    y = o["years_2025_2026_113"]
    _pin((y["2025"]["n"], y["2026"]["n"], y["2025"]["calibration"], y["2026"]["calibration"]), (31, 22, 2, 12), "practice_trends.py:1275")  # review 20261023 pin


if __name__ == "__main__":
    o = build()
    check(o)
    o95 = build_095(o)
    check_095(o95)
    o96 = build_096(o95)
    check_096(o96)
    o97 = build_097(o96)
    check_097(o97)
    o98 = build_098(o97)
    check_098(o98)
    print(json.dumps({k: o98[k] for k in ("named_variable_count", "domain_agreement_098", "outcome_groups_ranking")}, ensure_ascii=False))
    print(json.dumps(o98["diabetes_variable_panel"]["studies"], ensure_ascii=False))
    o99 = build_099(o98)
    check_099(o99)
    print(json.dumps({k: o99[k] for k in ("algorithm_families_by_period", "familiar_evaluation", "classified_outcome",
                                          "ranking_by_topic_period", "preprocessing_summary")}, ensure_ascii=False))
    o100 = build_100(o99)  # prompt 100
    check_100(o100)
    print(json.dumps({k: o100[k] for k in ("outcome_structure", "candidate_predictors", "task_composition", "domain_topics_at_least_ten")}))
    o101 = build_101(o100)  # prompt 101
    check_101(o101)
    print(json.dumps({"survey_components_165": o101["survey_components_165"], "core_year_scope": o101["core_year_scope"]}))
    o104 = build_104(o101)  # prompt 104
    check_104(o104)
    print(json.dumps({k: o104[k] for k in ("missing_handling_165", "selected_model_family")}),
          {k: v for k, v in o104["core_sample"].items() if k != "values"})
    (ROOT / "results/derived/practice_trends_106.json").write_text(json.dumps(o104, indent=1, ensure_ascii=False) + "\n")  # prompt 106: criterion A (250 studies); earlier files unchanged
    o107 = build_107(o104)  # prompt 107: fixed denominators (192 core studies with not-reported and not-applicable bars)
    check_107(o107)
    print(json.dumps({k: o107[k] for k in ("core_topics", "algorithms_fitted_192", "selected_model_family_192", "outcome_other_vs_not_reported")}))
    (ROOT / "results/derived/practice_trends_107.json").write_text(json.dumps(o107, indent=1, ensure_ascii=False) + "\n")  # prompt 107: superset; _106 unchanged
    o108 = build_108(o107)  # prompt 108: Figure 6A on 192 and three caption reconciliations
    check_108(o108)
    print(json.dumps({k: o108[k] for k in ("stability_192", "combined_weights_na_by_scope", "survey_years_vs_scope", "missing_step_not_applied")}))
    (ROOT / "results/derived/practice_trends_108.json").write_text(json.dumps(o108, indent=1, ensure_ascii=False) + "\n")  # prompt 108: superset; _107 unchanged
    o109 = build_109(o108)  # prompt 109: Table 1 by publication period
    check_109(o109)
    print(json.dumps(o109["table1_by_period"]))
    (ROOT / "results/derived/practice_trends_109.json").write_text(json.dumps(o109, indent=1, ensure_ascii=False) + "\n")  # prompt 109: superset; _108 unchanged
    o110 = build_110(o109)  # prompt 110: Figure 4C labels, topic-mix test
    check_110(o110)
    print(json.dumps([st["label"] for st in o110["diabetes_variable_panel"]["studies"]], ensure_ascii=False))
    (ROOT / "results/derived/practice_trends_110.json").write_text(json.dumps(o110, indent=1, ensure_ascii=False) + "\n")  # prompt 110: superset; _109 unchanged
    o112 = build_112(o110)  # prompt 112: Figure 5 (what the rankings named), Figure 3C timing
    check_112(o112)
    r112 = o112["rankings_named_112"]
    print(json.dumps({"columns": r112["columns"], "rows": [(x["topic"], x["group"], x["n"]) for x in r112["rows"]],
                      "all": {k: v for k, v in r112["all"]["counts"].items() if v >= 10}}, ensure_ascii=False))
    (ROOT / "results/derived/practice_trends_112.json").write_text(json.dumps(o112, indent=1, ensure_ascii=False) + "\n")  # prompt 112: superset; _110 unchanged
    o113 = build_113(o112)  # prompt 113: single-tree sensitivity, ranking x survey design, 2025/2026, length-matched agreement
    check_113(o113)
    print(json.dumps({k: o113[k] for k in ("sensitivity_without_added_113", "ranking_by_design_113", "years_2025_2026_113",
                                           "agreement_similar_length_113")}, ensure_ascii=False))
    (ROOT / "results/derived/practice_trends_113.json").write_text(json.dumps(o113, indent=1, ensure_ascii=False) + "\n")  # prompt 113: superset; _112 unchanged
