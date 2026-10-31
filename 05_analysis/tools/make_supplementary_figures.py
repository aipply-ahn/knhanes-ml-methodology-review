#!/usr/bin/env python3
"""Supplementary Figures S1-S8 (prompts 093-100): one-page figures in the main-text style.

Each figure shows only material that is not already drawn in a main-text figure, uses the main-text
colour rule (navy plain counts, teal complete or more common, light teal partial, amber low quality or
next-step practice, dark grey not reported, light grey not applicable; no red) and the main-text fonts. All counts come from the same
adjudicated records as Supplementary Table S5 (make_streamlined_figures / claim_evidence_analysis).
Output: manuscript/supplementary/figures/Supplementary_Figure_S0N_<slug>.pdf
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import claim_evidence_analysis as ce
import make_streamlined_figures as m
import practice_trends as pt  # review 20261023: outcome_source_codes
from make_claim_figures import TEAL, AMBER, VERM, DGREY, LGREY, NAVY, SLATE, FS_TITLE, FS_LABEL, FS_TICK, FS_VALUE, style
from study_reporting import reporting_summary

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/supplementary/figures"
LIGHT_TEAL = "#A7D3D2"  # prompt 096: "Partial" reporting (amber keeps one meaning)
CORE, HEALTH, METHOD = ce.CORE, m.HEALTH, m.METHOD
# prompt 106: study-set counts from the data (criterion A changed them)
N_CORE, N_HEALTH, N_METHOD = len(CORE), len(HEALTH), len(METHOD)
N_ALL = N_HEALTH + N_METHOD
N_RANK = sum(m.has(dd, "VI01", {"USED"}) for dd in CORE)
EXP = ce.EXP
W = 7.4
PALE = "#A9B8CC"
BEFORE = "#6B7280"  # prompt 099: dark grey instead of amber (review v37: no warning colour)


def title(fig, ax, text, dy=.012):
    pos = ax.get_position()
    fig.text(.012, pos.y1 + dy, text, ha="left", va="bottom", fontsize=FS_TITLE, weight="bold")


def bars(ax, labels, values, denom=None, color=NAVY, xmax=None, fmt=None):
    y = np.arange(len(labels))
    colors = color if isinstance(color, list) else [color] * len(values)
    ax.barh(y, values, color=colors, height=.64)
    ax.set_yticks(y); ax.set_yticklabels(labels, linespacing=1.0); ax.invert_yaxis()
    top = xmax or max(values) * 1.35
    for i, v in enumerate(values):
        text = fmt(v) if fmt else (f"{v} ({100 * v / denom:.0f}%)" if denom else str(v))
        ax.text(v + top * .015, i, text, va="center", fontsize=FS_VALUE)
    ax.set_xlim(0, top)
    ax.grid(axis="x", color="#E5E7EB", linewidth=.6); ax.set_axisbelow(True)


def save(fig, number, slug):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"Supplementary_Figure_S{number:02d}_{slug}.pdf"
    fig.savefig(path, facecolor="white")
    fig.savefig(path.with_suffix(".png"), dpi=160, facecolor="white")
    plt.close(fig)
    return path


def grid_axes(fig, rows, cols, top=.93, bottom=.06, left=.30, right=.97, hgap=.10, wgap=.40):
    axes = []
    h = (top - bottom - hgap * (rows - 1)) / rows
    w = (right - left - wgap * (cols - 1)) / cols if cols > 1 else right - left
    for r in range(rows):
        for c in range(cols):
            x0 = left + c * (w + wgap)
            y0 = top - (r + 1) * h - r * hgap
            axes.append(fig.add_axes([x0, y0, w, h]))
    return axes


# --------------------------------------------------------------------------- S1
def s1():
    """Prompt 097: study characteristics (former main Figure 2B-C and the role of KNHANES)."""
    o = json.load(open(ROOT / "results/derived/practice_trends_107.json"))
    fig = plt.figure(figsize=(W, 6.6))  # prompt 110: B survey years (former main Figure 3C)
    c = fig.add_axes([.44, .62, .44, .32])
    f = dict(o["health_functions"]); f["FUN_TRANSPORT"] = o["validation_beyond_development_184"]
    _pin(f["FUN_TRANSPORT"], 41, "make_supplementary_figures.py:87")  # prompt 106 pin
    _pin(f["FUN_INTERP"], 151, "make_supplementary_figures.py:87")  # prompt 106 pin
    frows = [("FUN_PRED", "Classification or estimation"), ("FUN_INTERP", "Variable interpretation"), ("FUN_COMPARE", "Algorithm comparison"),
             ("FUN_TRANSPORT", "Validation beyond the\ndevelopment data"), ("FUN_TOOL", "Tool, score or calculator"),
             ("FUN_PROCESS", "Data processing"), ("FUN_PATTERN", "Pattern discovery")]
    cc, sc = o["survey_components_220"], o["survey_year_scope_220"]
    crow = [("Several cycles pooled", sc["MULTI_CROSS"], NAVY), ("Several years, one cycle", sc["MULTI_SAME"], PALE),
            ("Single survey year", sc["ONE_YEAR"], PALE), ("Examination", cc["EXAMINATION"], NAVY),
            ("Laboratory data", cc["LABORATORY"], NAVY), ("Nutrition survey", cc["NUTRITION"], NAVY)]
    _pin(crow[0][1], 121, "make_supplementary_figures.py:98")  # prompt 106 pin
    pc = m.PURPOSE["summary"]["knhanes_position"]
    keys = [("PRIMARY_ANALYSIS_DATASET", "Sole primary dataset"), ("ONE_OF_MULTIPLE_PRIMARY_DATASETS", "One of several\nprimary datasets"),
            ("EXTERNAL_OR_TRANSPORTABILITY_EVALUATION", "External evaluation\ndataset"), ("APPLICATION_OR_TEST_DATASET", "Application or\ntest dataset"),
            ("UNCLEAR", "Role not clear\nfrom the report")]
    assert sum(pc.get(k, 0) for k, _ in keys) == N_ALL, pc  # prompt 107: the panel adds to all 250 studies
    bars(c, [l for _, l in keys], [pc.get(k, 0) for k, _ in keys], N_ALL, color=[NAVY] * 4 + ["white"], xmax=260)
    c.patches[-1].set_edgecolor("#9CA3AF"); c.patches[-1].set_hatch("/////"); c.patches[-1].set_linewidth(.6)
    title(fig, c, f"A. Role of KNHANES (N={N_ALL})", dy=.02)
    o110 = json.load(open(ROOT / "results/derived/practice_trends_110.json"))
    sy = o110["core_survey_years"]; yrs = [int(k) for k in sy["counts"]]; n_core = o110["classified_outcome"]["n"]
    b = fig.add_axes([.10, .08, .86, .36])
    b.bar(yrs, [sy["counts"][str(k)] for k in yrs], color=NAVY, width=.72)
    b.set_xlim(1997.4, 2025.6); b.set_xticks([2000, 2005, 2010, 2015, 2020, 2024])
    b.set_ylabel("Core studies"); b.grid(axis="y", color="#E5E7EB", linewidth=.6); b.set_axisbelow(True)
    b.text(2025.4, b.get_ylim()[1] * .97, f"Survey years not named: {sy['not_reported']}", ha="right", va="top", fontsize=FS_VALUE, color=DGREY)
    title(fig, b, f"B. KNHANES survey years analysed (N={n_core}; overlap)", dy=.03)
    return save(fig, 2, "Study_characteristics")  # prompt 102: S1 -> S3; prompt 110: S3 -> S2


# --------------------------------------------------------------------------- S2
def s2():
    fig = plt.figure(figsize=(W, 6.2))  # prompt 107: C (sample by year) removed; main Figure 3C shows the sample
    b = fig.add_axes([.44, .60, .50, .31])
    d = fig.add_axes([.44, .08, .44, .38])
    labels_en = {"MENTAL_HEALTH": "Mental health", "METABOLIC_ENDOCRINE": "Metabolic and endocrine", "CARDIOVASCULAR": "Cardiovascular",
                 "MUSCULOSKELETAL": "Musculoskeletal", "ORAL_HEALTH": "Oral health", "RESPIRATORY": "Respiratory",
                 "KIDNEY_UROLOGIC": "Kidney and urologic", "CANCER": "Cancer", "NUTRITION_DIET": "Nutrition and diet",
                 "HEALTH_BEHAVIOUR": "Health behaviour", "OPHTHALMOLOGIC": "Eye health", "OTORHINOLARYNGOLOGIC": "Ear, nose and throat",
                 "DERMATOLOGIC_ALLERGIC": "Skin and allergy", "INFECTIOUS_IMMUNE": "Infectious and immune",
                 "REPRODUCTIVE_WOMENS_HEALTH": "Reproductive and women's", "AGING_GERIATRIC": "Ageing",
                 "GENERAL_HEALTH_MULTIMORBIDITY": "General health, multimorbidity", "OTHER_OR_CROSS_CUTTING": "Other or cross-cutting"}
    restr = lambda dd: dd.get("adjudication", {}).get("selection_restriction_dimensions", {}).get("fields", {})
    rk = [("age_restriction", "Age"), ("sex_restriction", "Sex"), ("disease_or_risk_restriction", "Disease or risk group"),
          ("measurement_or_data_availability_restriction", "Measurement or data\navailability")]
    bars(b, [l for _, l in rk], [sum(restr(dd).get(k, {}).get("value") is True for dd in CORE) for k, _ in rk], N_CORE, xmax=190)
    title(fig, b, f"A. Participant restrictions (N={N_CORE} core studies; overlap)")  # prompt 107: 192
    flow = lambda dd: dd.get("adjudication", {}).get("analytic_flow", {}).get("fields", {})
    # D. Participant-selection reporting in the core cohort (moved from the main text, prompt 093).
    s = ce.build()
    fkeys = [("source_population_size_reported", "Source population size"), ("eligibility_criteria_reported", "Eligibility criteria"),
             ("exclusion_numbers_reported", "Numbers excluded"), ("exclusion_reasons_reported", "Reasons for exclusion"),
             ("final_analytic_sample_reported", "Final analytic sample"), ("complete_cohort_traceability", "Every selection step")]
    vals = [s["participant_flow_core"][k] for k, _ in fkeys]
    _pin(vals[-1], 117, "make_supplementary_figures.py:135")  # prompt 106 pin
    bars(d, [l for _, l in fkeys], vals, N_CORE, color=[NAVY] * 5 + [TEAL], xmax=215)
    d.axhline(4.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    title(fig, d, f"B. Participant-selection items reported (N={N_CORE} core studies)")
    return save(fig, 4, "Participants_and_sample_size")  # prompt 102: S2 -> S4


# --------------------------------------------------------------------------- S3
def s3():
    csum = m.classification_summary(CORE)
    fig = plt.figure(figsize=(W, 4.6))  # prompt 104: missing values and candidate predictors moved to main Figure 2H and 2G
    d = fig.add_axes([.44, .60, .50, .30])
    e = fig.add_axes([.44, .10, .50, .27])
    source = Counter(c for dd in CORE for c in pt.outcome_source_codes(dd))
    sv = [source["VALIDATED_QUESTIONNAIRE_OR_SCALE"], source["CLINICAL_OR_PHYSICAL_MEASUREMENT"], source["LABORATORY_THRESHOLD"],
          source["SELF_REPORTED_DIAGNOSIS"] + source["PHYSICIAN_DIAGNOSIS"],
          source["DATA_DERIVED_CLASS"] + source["OTHER_REPORTED_SOURCE"] + source["COMPOSITE_DEFINITION"], source["NOT_REPORTED"]]
    _pin(sum(sv), 165, "make_supplementary_figures.py:166")  # prompt 106 pin
    scheme = Counter()
    for dd in CORE:
        scales = set(m.flat_values(dd, "OUT09")); units = {x.get("unit_id") for x in dd.get("protocol_items", {}).get("OUT09", []) if x.get("value") == "BINARY"}
        if len(scales) > 1: scheme["MIXED"] += 1
        elif "MULTICLASS" in scales: scheme["MULTICLASS"] += 1
        elif "MULTIBIN" in scales or len(units) > 1: scheme["MULTIBIN"] += 1
        else: scheme["BINARY"] += 1
    bars(d, ["Binary", "Several binary outcomes", "Multiclass", "Mixed"],
         [scheme[k] for k in ("BINARY", "MULTIBIN", "MULTICLASS", "MIXED")], N_CORE, xmax=190)
    title(fig, d, f"A. Outcome structure (N={N_CORE})")  # prompt 104: C -> A
    # Prompt 096: moved from former main Figure 6C (predictor set and tuning separation are in Figure 4B).
    r = json.load(open(ROOT / "results/derived/practice_trends_106.json"))["reproducibility"]
    _pin((r["outcome_fully_specified"], r["predictor_set_rebuildable"], r["all_three"]), (79, 26, 12), "make_supplementary_figures.py:179")  # prompt 106 pin
    # Prompt 103 (review v41): predictor set added so every Table 1 adoption value appears in a figure.
    bars(e, ["Outcome", "Predictor set", "Outcome, predictor set and\ntuning separation (all three)"],
         [r["outcome_fully_specified"], r["predictor_set_rebuildable"], r["all_three"]], N_CORE, color=[NAVY, NAVY, NAVY], xmax=190)
    title(fig, e, f"B. Rebuildable from the report (N={N_CORE})")  # prompt 104: D -> B
    return save(fig, 3, "Outcome_and_predictor_construction")  # prompt 102: S4 -> S2; prompt 110: S2 -> S3


# --------------------------------------------------------------------------- S4
def s4():
    csum = m.classification_summary(CORE)
    cls_a = [x for x in EXP.values() if x["task_group"] == "CLS" and x["study_id"] in {d["study_id"] for d in CORE}]
    fig = plt.figure(figsize=(W, 12.4))  # prompt 100: E importance methods (former main Figure 3C)
    a = fig.add_axes([.44, .785, .50, .175])
    b = fig.add_axes([.44, .635, .50, .09])
    c = fig.add_axes([.44, .455, .50, .115])
    d = fig.add_axes([.44, .265, .50, .13])
    e = fig.add_axes([.44, .035, .50, .17])
    ac = Counter(f for x in cls_a for f in set(x["algorithm_development"]["algorithm_family"]))
    order = ["Random forest", "Logistic regression", "XGBoost", "SVM", "DNN/MLP", "LightGBM", "Decision tree", "Naive Bayes"]
    other = sum(bool(set(x["algorithm_development"]["algorithm_family"]) - set(order)) for x in cls_a)
    names = dict(zip(order, ["Random forest", "Logistic regression", "XGBoost", "Support-vector machine", "Neural network", "LightGBM",
                             "Decision tree", "Naive Bayes"]))
    ranked = sorted(order, key=lambda k: -ac[k])  # prompt 096: sorted by size, "Other families" last
    bars(a, [names[k] for k in ranked] + ["Other families"], [ac[k] for k in ranked] + [other], N_CORE, xmax=130)
    title(fig, a, f"A. Algorithm families evaluated (N={N_CORE}; overlap)")
    tm = Counter(x["algorithm_development"]["hyperparameter_tuning_method"] for x in cls_a)
    no_tuning = sum(x["algorithm_development"]["tuning_selection_status"] == "NO_TUNING_OR_DEFAULT_MODEL" for x in cls_a)
    search = sum(tm[k] for k in ("RANDOM_SEARCH", "BAYESIAN_OR_OTHER_OPTIMISATION", "GRID_SEARCH", "OTHER_REPORTED"))
    manual = sum(x["algorithm_development"]["hyperparameter_tuning_method"] == "MANUAL_OR_DEFAULT" and
                 x["algorithm_development"]["tuning_selection_status"] != "NO_TUNING_OR_DEFAULT_MODEL" for x in cls_a)
    nr = N_CORE - search - manual - no_tuning
    bars(b, ["Systematic search", "Manual tuning", "Default or no tuning", "Not reported"], [search, manual, no_tuning, nr], N_CORE,
         color=[NAVY, NAVY, NAVY, DGREY], xmax=135)
    title(fig, b, f"B. Hyperparameter tuning (N={N_CORE})")
    vc = csum["validation"]
    both = sum(m.has(dd, "VAL02", {"TEMPORAL"}) and m.has(dd, "VAL02", {"EXTERNAL"}) for dd in CORE)
    bars(c, ["Single train–test split", "Cross-validation", "Bootstrap", "Apparent only", "Later survey period", "External dataset", "Status unclear"],
         [vc["SPLIT"], vc["CV"], vc["BOOT"], vc["APPARENT"], vc["TEMPORAL"], vc["EXTERNAL"], vc["NONE_NR"]], N_CORE,
         color=[NAVY] * 4 + [TEAL, TEAL, DGREY], xmax=160)
    title(fig, c, f"C. Evaluation designs (N={N_CORE}; overlap; {vc['TEMPORAL'] + vc['EXTERNAL'] - both} beyond development data)")
    q = csum["metrics"]; mr = csum["metric_reporting"]
    calib = sum(any(m.has(dd, k, {"R"}) for k in ("MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R")) for dd in CORE)
    measures = sorted(zip(["AUROC", "AUPRC", "Calibration", "Brier score", "Decision-curve analysis", "Confidence interval", "Paired model comparison"],
                          [q["AUROC"], q["AUPRC"], calib, q["BRIER"], q["DCA"], mr["MET_CI"], mr["MET_PAIR"]]), key=lambda t: -t[1])
    bars(d, [t[0] for t in measures], [t[1] for t in measures], N_CORE, xmax=160)  # prompt 096: sorted by size
    title(fig, d, f"D. Performance measures reported (N={N_CORE}; overlap)")
    named = [("SHAP", "SHAP"), ("MODEL_NATIVE", "Model-native"), ("COEFFICIENT_STATISTIC", "Coefficient or statistic"),
             ("PERMUTATION", "Permutation"), ("TREE_RULE", "Tree or rule"), ("PERTURBATION_ABLATION", "Perturbation or ablation"),
             ("LIME", "LIME"), ("PDP", "Partial dependence")]
    residual = {"ALE", "ICE", "NETWORK_SPECIFIC", "OTHER"}
    ivals = [sum(m.has(dd, "VI02", {k}) for dd in CORE) for k, _ in named] + [sum(bool(set(m.flat_values(dd, "VI02")) & residual) for dd in CORE)]
    _pin(ivals[:4], [57, 43, 20, 18], "make_supplementary_figures.py:231")  # prompt 106 pin
    bars(e, [l for _, l in named] + ["Other methods"], ivals, N_RANK, color=[TEAL] + [NAVY] * 8, xmax=80)
    title(fig, e, f"E. Importance methods (N={N_RANK} producing a ranking; overlap)")
    rep = reporting_summary(CORE)
    thr = len(rep["members"]["threshold_reported"]); ind = len(rep["members"]["threshold_independent"])
    return save(fig, 6, "Algorithms_tuning_evaluation_and_measures"), (thr, ind)  # prompt 102: S5 -> S6


# --------------------------------------------------------------------------- S5
def s5():
    fig = plt.figure(figsize=(W, 8.4))
    a = fig.add_axes([.44, .47, .50, .46])
    b = fig.add_axes([.44, .08, .50, .26])
    named = [("SHAP", "SHAP"), ("MODEL_NATIVE", "Model-native"), ("COEFFICIENT_STATISTIC", "Coefficient or statistic"),
             ("PERMUTATION", "Permutation"), ("TREE_RULE", "Tree or rule"), ("PERTURBATION_ABLATION", "Perturbation or ablation"),
             ("LIME", "LIME"), ("PDP", "Partial dependence")]
    residual = {"ALE", "ICE", "NETWORK_SPECIFIC", "OTHER"}
    vals = [sum(m.has(dd, "VI02", {k}) for dd in CORE) for k, _ in named] + [sum(bool(set(m.flat_values(dd, "VI02")) & residual) for dd in CORE)]
    bars(a, [l for _, l in named] + ["Other methods"], vals, N_RANK, xmax=75)
    title(fig, a, f"A. Importance methods (N={N_RANK} core studies producing a ranking; overlap)")
    path = [sum(m.has(dd, k, {"USED"}) for dd in CORE) for k in ("VI16", "VI10", "VI11", "VI14")]
    _pin(path, [25, 24, 12, 5], "make_supplementary_figures.py:252")  # prompt 106 pin
    labels = [f"Stability checked\n(of {N_RANK} producing a ranking)", f"Reduced predictor set built\n(of {N_CORE})",
              f"Used in a subsequent statistical\nanalysis (of {N_CORE})", f"Same variables carried into that\nanalysis (of the {path[2]})"]
    dens = [N_RANK, N_CORE, N_CORE, path[2]]
    y = np.arange(4)
    b.scatter([100 * p / d for p, d in zip(path, dens)], y, s=70, color=NAVY, zorder=3)
    for i, (p, d) in enumerate(zip(path, dens)):
        b.text(100 * p / d + 2.5, i, f"{p}/{d}", va="center", fontsize=FS_VALUE)
    b.set_yticks(y); b.set_yticklabels(labels, linespacing=1.0); b.invert_yaxis(); b.set_xlim(0, 60)
    b.set_xticks([0, 20, 40, 60]); b.set_xticklabels(["0", "20", "40", "60%"]); b.grid(axis="x", color="#E5E7EB", linewidth=.6)
    title(fig, b, "B. Stability and downstream use of rankings (denominator in each row)")
    return save(fig, 5, "Variable_importance_methods_and_downstream_use")


# --------------------------------------------------------------------------- S6
def s6():
    method = [r for r in m.PURPOSE_RECORDS if r["study_category"] == "METHOD_RESEARCH"]
    fig = plt.figure(figsize=(W, 8.4))
    a = fig.add_axes([.44, .80, .50, .12])
    b = fig.add_axes([.44, .45, .50, .26])
    c = fig.add_axes([.44, .08, .50, .26])
    kc = Counter(r["method_research_category"] for r in method)
    bars(a, ["Develop or improve a method", "Compare existing methods"],
         [kc["METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT"], kc["EXISTING_METHODS_COMPARISON_OR_EVALUATION"]], len(method), color=SLATE, xmax=42)
    title(fig, a, f"A. Type of contribution (N={len(method)})")
    sc = Counter(x for r in method for x in r["method_intervention_stages"])
    stage_vals = [sc["DATA_INTEGRATION_OR_HARMONISATION"], sc["MISSING_DATA"], sc["FEATURE_ENGINEERING_OR_SELECTION"],
                  sum(any(x in r["method_intervention_stages"] for x in ("PREDICTION_OR_CLASSIFICATION", "CLUSTERING_OR_REPRESENTATION", "CAUSAL_OR_STRUCTURE_LEARNING")) for r in method),
                  sc["EXPLAINABLE_AI"], sc["VALIDATION_OR_PERFORMANCE_EVALUATION"], sc["USER_TOOL_OR_WORKFLOW"]]
    bars(b, ["Data integration", "Missing data", "Variable construction\nor selection", "Model development", "Explanation",
             "Validation or performance\nevaluation", "User tool or workflow"], stage_vals, len(method), color=SLATE, xmax=42)
    title(fig, b, f"B. Analysis stages addressed (N={len(method)}; overlap)")
    # Evaluation categories that match the method-claim requirement in the main text.
    def cat(r):
        if r["method_evaluation_mode"] == "SIMULATION_AND_EMPIRICAL_APPLICATION":
            return "Simulation"
        if r["method_evaluation_mode"] == "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION" or r["knhanes_position"] == "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION":
            return "Independent population"
        if r["knhanes_position"] == "ONE_OF_MULTIPLE_PRIMARY_DATASETS":
            return "KNHANES one of several\nprimary datasets"
        if r["method_evaluation_mode"] == "EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED":
            return "Not reported"
        return "Single KNHANES\napplication"
    order = ["Simulation", "Independent population", "KNHANES one of several\nprimary datasets", "Single KNHANES\napplication", "Not reported"]
    cc = Counter(cat(r) for r in method)
    _pin(cc["Simulation"] + cc["Independent population"] + cc["KNHANES one of several\nprimary datasets"], 5, "make_supplementary_figures.py:297")  # prompt 106 pin
    bars(c, order, [cc[k] for k in order], len(method), color=[TEAL, TEAL, TEAL, VERM, DGREY], xmax=42)
    title(fig, c, f"C. How the method was evaluated (N={len(method)})")
    return save(fig, 6, "Method_focused_studies")


# --------------------------------------------------------------------------- S7
def s7():
    # Prompt 094: survey design by stage moved to main Figure 6B; this is Supplementary Figure S5.
    fig = plt.figure(figsize=(W, 9.4))  # prompt 096: portrait page
    a = fig.add_axes([.40, .51, .56, .40])
    c = fig.add_axes([.40, .07, .56, .29])
    rep = []
    for i in range(1, 20):
        cnt = Counter(v for dd in CORE for v in m.flat_values(dd, f"REP{i:02d}"))
        rep.append([cnt.get("R", 0), cnt.get("P", 0), cnt.get("NR", 0) + cnt.get("UNC", 0)])
    rep = np.array(rep); idx = [5, 6, 7, 9, 11, 12, 16, 18]
    labels = ["Outcome definition,\ntiming and source", "Predictor definition\nand timing", "Sample and event counts", "Missing-data handling",
              "Hyperparameters and tuning", "Internal validation", "Final-model specification", "Registration, data\nand code availability"]
    sel = rep[idx]; pct = 100 * sel / N_CORE; left = np.zeros(len(sel)); y = np.arange(len(sel))
    for j, col in enumerate([TEAL, LIGHT_TEAL, DGREY]):
        a.barh(y, pct[:, j], left=left, color=col, height=.64, edgecolor="white", linewidth=.6)
        for i, p in enumerate(pct[:, j]):
            if p >= 8:
                a.text(left[i] + p / 2, i, f"{p:.0f}%", ha="center", va="center", fontsize=FS_VALUE, color="#111827" if col == LIGHT_TEAL else "white")
        left += pct[:, j]
    a.set_yticks(y); a.set_yticklabels(labels, linespacing=1.0); a.invert_yaxis(); a.set_xlim(0, 100)
    a.set_xticks([0, 25, 50, 75, 100]); a.set_xticklabels(["0", "25", "50", "75", "100%"])
    # Prompt 094: anchored at the right edge so the three-item legend extends left, not past the canvas.
    a.legend(handles=[Patch(color=TEAL, label="Complete"), Patch(color=LIGHT_TEAL, label="Partial"), Patch(color=DGREY, label="Not reported or unclear")],
             frameon=False, ncol=3, loc="lower right", bbox_to_anchor=(1.0, 1.0), columnspacing=1.2, handlelength=1.4)
    title(fig, a, f"A. Eight of the 19 reporting elements (N={N_CORE})", dy=.04)
    dev = Counter(v for dd in CORE for v in m.flat_values(dd, "PD_OVERALL") if v != "NA")
    eva = Counter(v for dd in CORE for v in m.flat_values(dd, "PE_OVERALL") if v != "NA")
    ddom = [Counter(v for dd in CORE for v in m.flat_values(dd, f"PE_D{i}") if v != "NA") for i in range(1, 5)]
    rows = [(f"Development: overall\n({sum(dev.values())} models)", [dev.get("LOW", 0), dev.get("UNC", 0), dev.get("HIGH", 0)], True)]
    for name, cnt in zip(["Evaluation: participants", "Evaluation: predictors", "Evaluation: outcome", "Evaluation: analysis"], ddom):
        rows.append((name, [cnt.get("HIGH", 0), cnt.get("UNC", 0), cnt.get("LOW", 0)], False))
    rows.append((f"Evaluation: overall\n({sum(eva.values())} evaluations)", [eva.get("HIGH", 0), eva.get("UNC", 0), eva.get("LOW", 0)], False))
    yy = np.arange(len(rows))
    for i, (lab, cnt, is_dev) in enumerate(rows):
        tot = sum(cnt); left = 0
        cols = [BEFORE, LGREY, TEAL]  # prompt 094: no red; prompt 099: no amber
        for n, col in zip(cnt, cols):
            w = 100 * n / tot
            if n:
                c.barh(i, w, left=left, color=col, height=.64, edgecolor="white", linewidth=.6)
                if w >= 8:
                    c.text(left + w / 2, i, f"{n}", ha="center", va="center", fontsize=FS_VALUE, color="#111827" if col == LGREY else "white")
            left += w
    c.set_yticks(yy); c.set_yticklabels([r[0] for r in rows], linespacing=1.0); c.invert_yaxis(); c.set_xlim(0, 100)
    c.set_xticks([0, 25, 50, 75, 100]); c.set_xticklabels(["0", "25", "50", "75", "100%"])
    c.legend(handles=[Patch(color=BEFORE, label="Low quality or high risk"), Patch(color=LGREY, label="Unclear"), Patch(color=TEAL, label="High quality or low risk")],
             frameon=False, ncol=3, loc="lower right", bbox_to_anchor=(1.0, 1.0), columnspacing=1.2, handlelength=1.4)
    title(fig, c, f"B. PROBAST+AI judgements (N={N_CORE} studies)", dy=.04)
    return save(fig, 8, "Reporting_completeness_and_PROBAST_AI")  # prompt 109: S7 -> S8


# --------------------------------------------------------------------------- S8
def s8():
    """Supplementary Figure S6 (prompts 095-096): 2x3 portrait grid of period differences not drawn in a main figure
    (A algorithm comparison, B families, C paired comparison, D survey-weight mention), E preprocessing state and
    F topic mix. Amber is reserved for next-step practices (any preprocessing step before the split)."""
    temporal = json.load(open(ROOT / "results/derived/exploratory_temporal_practice_analysis.json"))
    topics = temporal["health_focused_classification"]["health_topics"]
    periods = ["≤2019", "2020–2022", "2023–2024", "2025–2026"]
    groups = [[dd for dd in CORE if m.period(int(dd["metadata"]["publication_year"])) == p] for p in periods]
    den = [len(g) for g in groups]
    fam = lambda dd, names: bool(set(EXP[dd["study_id"]]["algorithm_development"]["algorithm_family"]) & set(names))
    series = {
        "A": ("A. Algorithms by period", [("Algorithms compared", NAVY, lambda dd: m.has(dd, "FUN_COMPARE", {"PRESENT"})),  # prompt 107: former main Figure 2I
                                          ("Boosting", TEAL, lambda dd: fam(dd, {"XGBoost", "LightGBM", "Gradient boosting"})),
                                          ("Random forest", "#6D86A6", lambda dd: fam(dd, {"Random forest"})),
                                          ("Logistic regression", "#9FB2C8", lambda dd: fam(dd, {"Logistic regression"})),
                                          ("SVM", "#B9C6D6", lambda dd: fam(dd, {"SVM"})), ("Neural network", "#C9D4E1", lambda dd: fam(dd, {"DNN/MLP"}))]),
        "B": ("B. Paired model comparison", [("Paired comparison of models", NAVY, lambda dd: m.has(dd, "MET_PAIR", {"Y", "USED"}))]),  # prompt 107: grey = method-focused
    }  # prompt 110: survey weights, preprocessing timing and no-change rows removed (they repeat Table 1)
    fig = plt.figure(figsize=(W, 6.2))  # prompt 110: A, B and C (rankings by topic)
    left, wgap, w = .08, .14, .31
    tops = [.85, .85, .40]; h = .27
    boxes = [(left, tops[0] - h), (left + w + wgap, tops[1] - h), (left, tops[2] - h), (left + w + wgap, tops[2] - h),
             (left, .085)]
    x = np.arange(4)
    for key, (bx, by) in zip("AB", boxes):
        ax = fig.add_axes([bx, by, w, h])
        ttl, specs = series[key]
        ends = []
        for lab, col, fn in specs:
            vals = [100 * sum(fn(dd) for dd in g) / n for g, n in zip(groups, den)]
            lw = 2.0 if col in (NAVY, TEAL) else 1.1
            ax.plot(x, vals, color=col, lw=lw, alpha=.95, zorder=3 if col == NAVY else 2)
            ax.scatter(x, vals, color=col, s=26 if col == NAVY else 16, zorder=3)
            ends.append([vals[-1], lab, col])
        if False:  # prompt 099: the family panel moved to main Figure 2C
            ends.sort(key=lambda e: e[0])
            for i in range(1, len(ends)):
                ends[i][0] = max(ends[i][0], ends[i - 1][0] + 8.5)
            for yv, lab, col in ends:
                ax.text(3.18, yv, lab, va="center", ha="left", fontsize=FS_VALUE - 2.6, color=NAVY if col == NAVY else DGREY,
                        weight="bold" if col == NAVY else "normal", clip_on=False)
        ax.set_xticks(x); ax.set_xticklabels(["≤19", "20–22", "23–24", "25–26"], fontsize=FS_TICK - 1.2); ax.set_xlim(-.25, 3.25)
        ax.set_ylim(0, 100); ax.set_yticks([0, 50, 100]); ax.set_yticklabels(["0", "50", "100%"], fontsize=FS_TICK - 1.2)
        ax.grid(axis="y", color="#E5E7EB", linewidth=.6)
        if True:
            ax.legend(handles=[Line2D([], [], color=c, marker="o", ms=4, lw=1.2, label=l) for l, c, _ in specs], frameon=False,
                      loc="upper left", bbox_to_anchor=(-.02, -.16), ncol=3 if len(specs) > 2 else 2, fontsize=FS_VALUE - 2.4 - (1.0 if len(specs) > 2 else 0),
                      handlelength=1.0, columnspacing=.5, labelspacing=.2)
        fig.text(bx - .06, by + h + .022, ttl, ha="left", va="bottom", fontsize=FS_TITLE - .6, weight="bold")
    # C. Rankings within the four largest topics (former main Figure 3B); prompt 110: the preprocessing-timing and
    # no-consistent-change panels were removed because Table 1 gives those practices by period.
    import make_main_figures as mm
    o100 = json.load(open(ROOT / "results/derived/practice_trends_107.json"))
    ex = fig.add_axes([left, .07, w * .55, .27])
    mm.figure_topic_slopes(ex, o100)
    style("en")
    ex.tick_params(labelsize=FS_TICK - 1.2)
    fig.text(left - .06, .07 + .27 + .03, "C. Rankings by topic", ha="left", va="bottom", fontsize=FS_TITLE - .6, weight="bold")
    fig.text(.012, .975, f"Core studies by publication period (period n = {', '.join(map(str, den))})", ha="left", va="top",
             fontsize=FS_TITLE, weight="bold")
    return save(fig, 5, "Differences_by_publication_period")  # prompt 102: S3 -> S5


def s_testbed():
    """Prompt 097: former main Figure 5 (methods testbed), drawn by make_main_figures.figure_testbed."""
    import make_main_figures as mm
    mm.figure_testbed("en", out=str(OUT))
    style("en")
    target = OUT / "Supplementary_Figure_S01_Methods_testbed.pdf"  # prompt 102: S6 -> S1
    (OUT / "fig5_methods_testbed.pdf").replace(target)
    (OUT / "fig5_methods_testbed.png").replace(target.with_suffix(".png"))
    return target


def s_agreement():
    """Prompt 099: former main Figure 4C (agreement between pairs of rankings)."""
    import make_main_figures as mm
    mm.figure_agreement("en", out=str(OUT))
    style("en")
    target = OUT / "Supplementary_Figure_S07_Agreement_between_rankings.pdf"  # prompt 109: S8 -> S7
    (OUT / "figS_ranking_agreement.pdf").replace(target)
    (OUT / "figS_ranking_agreement.png").replace(target.with_suffix(".png"))
    return target


def main():
    style("en")
    # Prompt 097: numbered in citation order (S1 characteristics, S2 participants, S3 period, S4 outcome/predictor,
    # S5 algorithms, S6 methods testbed, S7 reporting and PROBAST+AI).
    out = [s1(), s2(), s8(), s3(), s4()[0], s_testbed(), s_agreement(), s7()]  # prompt 099: S7 agreement, S8 reporting
    print("built", len(out), "supplementary figures")


if __name__ == "__main__":
    main()
