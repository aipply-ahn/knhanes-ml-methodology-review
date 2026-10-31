#!/usr/bin/env python3
"""Prompt 114: Additional Data 1 (Additional file 2) as one reader-facing workbook of the coded data, in the form of
paper_EHR_survival_review/manuscript/Additional_File_1_studies_and_tasks.xlsx: a Columns dictionary that ties every column to
the figure or table it feeds, one row per study, the unit-level sheets behind the supplementary figures, the selection
flow and exclusions, the sensitivity analyses, and a Reproduce sheet.

Every study-level value is computed with the functions that draw the figures and Table 1 (practice_trends,
make_streamlined_figures, claim_evidence_analysis, study_reporting), and check() re-adds each column to the published
counts before the file is written. The 41-sheet study-level workbook (manuscript/bmc_supplementary_data1.xlsx, built by
build_standalone_supplements.py) is kept unchanged as the full internal coding log; the analysis code reads it.

    python tools/build_data1_workbook.py      ->  manuscript/Additional_File_2_Supplementary_Data_1.xlsx
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from main_figure_map import remap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import practice_trends as pt  # noqa: E402
from build_standalone_supplements import OTHER_HEALTH_SHORT  # noqa: E402  (Supplementary Table S5 target labels)
from study_reporting import reporting_summary  # noqa: E402

m, ce, EXP, CORE = pt.m, pt.ce, pt.EXP, pt.CORE
OUT = ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx"  # prompt 115: Additional Data 1 (Additional file 2)
O = json.loads((ROOT / "results/derived/practice_trends_113.json").read_text())
FULL_LOG = pt.WORKBOOK()
HEADER_FILL = PatternFill("solid", fgColor="E8ECF1")
NA_CORE = "–"  # not coded: outside the core cohort

TOPIC = {"METABOLIC_ENDOCRINE": "Metabolic and endocrine", "MENTAL_HEALTH": "Mental health", "CARDIOVASCULAR": "Cardiovascular",
         "MUSCULOSKELETAL": "Musculoskeletal", "ORAL_HEALTH": "Oral health", "RESPIRATORY": "Respiratory",
         "OTORHINOLARYNGOLOGIC": "Ear, nose and throat", "GENERAL_HEALTH_MULTIMORBIDITY": "General health",
         "KIDNEY_UROLOGIC": "Kidney and urologic", "OPHTHALMOLOGIC": "Eye health", "NUTRITION_DIET": "Nutrition and diet",
         "HEALTH_BEHAVIOUR": "Health behaviour", "CANCER": "Cancer", "DERMATOLOGIC_ALLERGIC": "Skin and allergy",
         "OTHER_OR_CROSS_CUTTING": "Other or cross-cutting"}
SCOPE = {"ONE_YEAR": "One survey year", "MULTI_SAME": "Several years of one cycle", "MULTI_CROSS": "Several cycles", "UNC": "Unclear"}
COMPONENT = {"HEALTH_INTERVIEW": "Health interview", "EXAMINATION": "Examination", "LABORATORY": "Laboratory",
             "NUTRITION": "Nutrition", "ORAL_HEALTH": "Oral health"}
TIMING = {"CURRENT": "Current state measured in the same survey", "UNC": "Timing unclear", "FUTURE": "Future event"}
SOURCE = {"VALIDATED_QUESTIONNAIRE_OR_SCALE": "Questionnaire or scale", "CLINICAL_OR_PHYSICAL_MEASUREMENT": "Physical measurement",
          "LABORATORY_THRESHOLD": "Laboratory value", "SELF_REPORTED_DIAGNOSIS": "Diagnosis or history",
          "PHYSICIAN_DIAGNOSIS": "Diagnosis or history", "OTHER_REPORTED_SOURCE": "Other", "DATA_DERIVED_CLASS": "Other",
          "COMPOSITE_DEFINITION": "Other", "NOT_REPORTED": "Not reported"}
MISSING = {"COMPLETE": "Complete-case analysis", "SINGLE_IMP": "Single imputation", "MULTI_IMP": "Multiple imputation",
           "MODEL_NATIVE": "Model-native", "MULTIPLE": "Other or several", "INDICATOR": "Other or several", "OTHER": "Other or several",
           "NR": "Not reported"}
FAMILY = [("Boosting", {"XGBoost", "LightGBM", "Gradient boosting"}), ("Random forest", {"Random forest"}),
          ("Logistic regression", {"Logistic regression"}), ("Decision tree", {"Decision tree"}), ("SVM", {"SVM"}),
          ("Neural network", {"DNN/MLP"})]
IMPORTANCE = {"SHAP": "SHAP", "MODEL_NATIVE": "Model-native", "COEFFICIENT_STATISTIC": "Coefficient or statistic",
              "PERMUTATION": "Permutation", "TREE_RULE": "Tree or rule", "PERTURBATION_ABLATION": "Perturbation or ablation",
              "LIME": "LIME", "PDP": "Partial dependence", "ALE": "Other", "ICE": "Other", "NETWORK_SPECIFIC": "Other", "OTHER": "Other"}
EXCL = {"no_eligible_machine_learning": "no eligible machine learning", "not_knhanes": "not KNHANES data",
        "review_or_non_primary_synthesis": "review or non-primary synthesis", "no_eligible_knhanes_analysis": "no eligible KNHANES analysis",
        "abbreviation_false_positive": "abbreviation false positive", "other_or_unassessable": "other or not assessable",
        "ml_adjacent_catalogued_separately": "only regression-family or unsupervised methods"}
STATE = {"USED": "Yes", "NOT_USED": "No", "NR": "Not reported", "UNC": "Unclear", "NA": "Not applicable"}
TUNING_KEPT = {"TUNING_REPORTED_SEPARATED": "Yes", "NO_TUNING_OR_DEFAULT_MODEL": "Yes", "TUNING_NOT_REPORTED": "Not reported",
               "NOT_ASSESSABLE": "Unclear"}  # review 20261023 (Codex rules 2, 8): other states are "No"
REBALANCE = {"NA": "No active intervention reported"}  # review 20261023 (Codex rule 1, protocol IMB01/IMB03)
STEP = {"WITHIN": "Within the training data", "BEFORE": "Before the split", "UNCLEAR": "Timing unclear", "NA": "Not applied"}
OVERALL = {"WITHIN_ONLY": "All within the training data", "ANY_BEFORE": "At least one step before the split",
           "UNCLEAR_NO_BEFORE": "Timing unclear", "NONE": "No data-dependent step"}
STAB = {"SUBGROUP_STABILITY": "Subgroups", "RESAMPLING_STABILITY": "Resamples", "EXTERNAL_STABILITY": "External data",
        "INTERVAL_STABILITY": "Intervals", "METHOD_NOT_RECOVERABLE": "Not described",
        # review loop cycle 3: the codes actually stored in the audit (Figure 7A counts these)
        "SUBGROUP_CONSISTENCY": "Subgroups", "EXTERNAL_DATA_REPLICATION": "External data", "UNCERTAINTY_INTERVAL": "Intervals",
        "SENSITIVITY_ANALYSIS": "Sensitivity analyses"}  # D20 A


ABSENCE = {"NA", "NR", "NOT_USED", "ABSENT", "R0", "UNC", "NONE_NR", "N"}
EVIDENCE_ITEMS = {  # protocol items behind the Studies columns (prompt 116)
    "TSK01": "Study group / task", "DAT08": "Combining survey years", "DAT14": "KNHANES survey components used",
    "OUT10": "Outcome timing", "OUT16": "Outcome rebuildable from the report", "PRD13": "Predictor set rebuildable from the report",
    "PRE01": "Missing-value handling", "PRE05": "Missing-value handling timing", "PRE14": "Data-driven preprocessing separation",
    "PRE13": "Supervised feature selection timing", "IMB03": "Class rebalancing timing", "FUN_COMPARE": "Several algorithms compared",
    "VAL02": "Train-test split; Cross-validation; Validation on a later survey period; Validation on external data",
    "THR01": "Decision threshold reported", "VI01": "Importance ranking produced", "VI02": "Importance methods; SHAP used",
    "VI06": "Most important variables as reported", "VI07": "Variable domains", "VI10": "Ranking used for a reduced predictor set",
    "VI11": "Ranking used to guide a statistical analysis", "VI16": "Ranking stability checked", "SUR04": "KNHANES sampling weights mentioned",
    "SUR06": "Weights in model fitting", "SUR07": "Weights in performance evaluation", "SUR10": "Strata or PSUs in variance estimation",
    "SUR11": "Combined-year weights", "MOD15": "Analysis code shared", "REP17": "Final model fully specified"}


def readable(v):
    """A coded value as words: JSON lists joined, codes in lower case without underscores."""
    if v in (None, "", "NA"):
        return "Not applicable"
    if v == "NR":
        return "Not reported"
    t = str(v)
    if t.startswith("["):
        try:
            t = "; ".join(map(str, json.loads(t)))
        except ValueError:
            pass
    t = {"METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT": "Develops or improves a method",
         "EXISTING_METHODS_COMPARISON_OR_EVALUATION": "Compares existing methods"}.get(t, t)
    if re.fullmatch(r"[A-Z0-9_ |]+", t):
        t = "; ".join(x.strip().replace("_", " ").lower() for x in t.split("|"))
        t = t[:1].upper() + t[1:]
    return t.replace(" | ", "; ")


def j(vals):
    vals = [v for v in vals if v not in (None, "", "NA", "NR")]
    return "; ".join(dict.fromkeys(vals))


def first(d, k):
    return (m.flat_values(d, k) or ["NR"])[0]


def full_log_rows():
    wb = load_workbook(FULL_LOG, read_only=True)
    it = wb["STUDIES"].iter_rows(values_only=True)
    hdr = list(next(it))
    rows = {r[hdr.index("A_study_id")]: dict(zip(hdr, r)) for r in it}
    dic = {r[0]: r for r in list(wb["DATA_DICTIONARY"].iter_rows(values_only=True))[1:]}
    wb.close()
    return rows, dic


AFFILIATION = re.compile(r"대학교|학과|교수|연구소|연구원|University|Department|Institute", re.I)


def surname(authors):
    """practice_trends.first_author_surname, falling back to the first author as recorded (Korean-script names).
    Review loop cycle 1: author entries that are affiliations are skipped, and an all-capital surname is capitalised."""
    authors = " | ".join(a for a in str(authors).split("|") if a.strip() and not AFFILIATION.search(a))
    try:
        name = pt.first_author_surname(authors)
    except KeyError:
        name = str(authors).split("|")[0].strip()
    return name.capitalize() if name.isupper() and len(name) > 1 else name


def study_labels(rows):
    """Surname-year labels, lettered a, b, ... where they recur. A review override of the Study column sets the
    surname-year base of that study (any letter in it is ignored), and the lettering is recomputed over all studies."""
    fixed = {}
    if OVERRIDES.exists():
        import csv
        with OVERRIDES.open(encoding="utf-8") as fh:
            fixed = {o["study_id"]: re.sub(r"(\d{4})[a-z]$", r"\1", o["new_value"].strip())
                     for o in csv.DictReader(fh, delimiter="\t") if o["column"] == "Study"}
    base = {}
    for sid, r in rows.items():
        base.setdefault(fixed.get(sid) or f"{surname(r['A_authors'])} {r['A_publication_year']}", []).append(sid)
    lab = {}
    for b, ids in base.items():
        for k, sid in enumerate(sorted(ids)):
            lab[sid] = b + ("abcdefghijklmnopqrstuvwxyz"[k] if len(ids) > 1 else "")
    lab.update(LABEL_PIN)
    assert len(set(lab.values())) == len(lab), "duplicate study labels"
    return lab


# Author 2026-10-24: existing labels stay as first published until the final re-sequencing (new studies take the next
# free letter). KHM220 would become "Jeong 2024a" (KHM258 added); KHM237 would shift to "Kim 2019c" (KHM233's year
# corrected 2017 -> 2019, so KHM233 takes the next free letter).
LABEL_PIN = {"KHM220": "Jeong 2024", "KHM237": "Kim 2019b", "KHM233": "Kim 2019c"}


def build_studies(rows):
    core = {d["study_id"]: d for d in CORE}
    other_ids = {d["study_id"] for d in pt.HEALTH} - set(core)
    rep = reporting_summary(CORE)["members"]
    thr, thr_ind = set(rep["threshold_reported"]), set(rep["threshold_independent"])
    cmp_ids = {sid for sid, d in core.items() if m.has(d, "FUN_COMPARE", {"PRESENT"})}
    sys_tune = ("RANDOM_SEARCH", "BAYESIAN_OR_OTHER_OPTIMISATION", "GRID_SEARCH", "OTHER_REPORTED")
    named = O["rankings_named_112"]
    row_of = {}
    for x in named["rows"]:
        if x["level"] != "topic":
            for sid in x["ids"]:
                row_of[sid] = x["group"]
    added = set(O["sensitivity_without_added_113"]["added_ids"])  # review 20261023: the set practice_trends uses (verdicts + review flags)
    lab = study_labels(rows)
    out = []
    for sid in sorted(rows):
        r = rows[sid]
        d = core.get(sid)
        grp = "Core classification" if d else "Other health analysis" if sid in other_ids else "Method-focused"
        y = int(r["A_publication_year"])
        rec = {"Study ID": sid, "Study": lab[sid], "Title": r["A_title"], "Journal": r["A_journal"], "Year": y,
               "Publication period": m.period(y), "DOI or PMID": r["A_DOI"] if r["A_DOI"] not in ("NR", "NA", None) else
               (f"PMID {r['A_PMID']}" if r["A_PMID"] not in ("NR", "NA", None) else "no DOI (citation in Title and Journal)"),
               "Report type": r["A_report_type"], "Study group": grp,
               "Added under the final eligibility criterion": "Yes" if sid in added else "No",
               "Survey years": r["C_survey_years"] if r["C_survey_years"] not in ("NR", None) else "Not reported"}
        if not d:
            out.append(rec)
            continue
        fl = d.get("adjudication", {}).get("analytic_flow", {}).get("fields", {})
        cand = fl.get("initial_candidate_predictor_count", {})
        cv = cand.get("value")
        n = str(r["D_final_sample"]).split("|")[0].strip()
        fams = set(EXP[sid]["algorithm_development"]["algorithm_family"])
        fitted = [f for f, s in FAMILY if fams & s] + (["Other"] if fams - set().union(*(s for _, s in FAMILY)) else [])
        chosen = str(r["G_author_selected_model"]).split("|")[0].strip().lower()
        sel = next(f for f, pat in pt.SELECTED_FAMILY_107 if re.search(pat, chosen)) if sid in cmp_ids else "Several algorithms not compared"
        csum = m.classification_summary([d])
        rank = pt.PRACTICES["importance_ranking"](d)
        stab = m.has(d, "VI16", {"USED"}) if rank else None
        vi02 = [IMPORTANCE.get(v, "Other") for v in m.flat_values(d, "VI02") if v in IMPORTANCE]
        val = set(m.flat_values(d, "VAL02"))
        pre = {name: pt.preprocessing_status(d, k, w, b, u) for name, k, w, b, u in pt.PRE_SPECS}
        rec.update({
            "Health topic": TOPIC.get(m.PURPOSE_V13_BY_ID[sid]["health_topic"]["primary_topic_18"], "Other or cross-cutting"),
            "Combining survey years": SCOPE.get(m.first(d, "DAT08", "UNC"), "Unclear"),
            "KNHANES survey components used": j(COMPONENT.get(v) for v in m.flat_values(d, "DAT14")) or "Not reported",
            "Outcome": str(r["E_outcome_name"]).split("|")[0].strip(),
            "Outcome timing": TIMING.get(m.first_applicable(d, "OUT10"), "Timing unclear"),
            "Outcome source": j(dict.fromkeys(SOURCE.get(c, "Not reported") for c in pt.outcome_source_codes(d))),  # review 20261023: all sources
            "Outcome group (Figure 5)": row_of.get(sid, "other") if rank else NA_CORE,
            "Outcome group (Figure S7A)": pt.outcome_group(d) if rank else NA_CORE,
            "Final analytic sample": int(n) if n.isdigit() else "Not reported",
            "Initial candidate predictors": cv if cand.get("value_status") == "REPORTED" and isinstance(cv, (int, float)) and not isinstance(cv, bool) and cv > 0 else "Not reported",
            "Missing-value handling": MISSING.get(m.categorical_methods(d, "PRE01"), "Other or several"),
            "Algorithm families fitted": "; ".join(fitted) or "Not recorded",
            "Several algorithms compared": "Yes" if sid in cmp_ids else "No",
            "Family of the selected model": sel,
            "Systematic hyperparameter search": "Yes" if EXP[sid]["algorithm_development"].get("hyperparameter_tuning_method") in sys_tune else "No",
            "Tuning kept apart from the final evaluation": TUNING_KEPT.get(ce.tuning_status(d), "No"),  # review 20261023: Codex rules 2 and 8
            "Train-test split": "Yes" if "SPLIT" in val else "No", "Cross-validation": "Yes" if "CV" in val else "No",
            "AUROC reported": "Yes" if csum["metrics"].get("AUROC", 0) > 0 else "No",
            "Confidence interval reported": "Yes" if csum["metric_reporting"].get("MET_CI", 0) > 0 else "No",
            "Decision threshold reported": "Yes" if sid in thr else "No",
            "Threshold chosen without the final evaluation data": ("Yes" if sid in thr_ind else "No") if sid in thr else "Not applicable",
            "Calibration reported": "Yes" if pt.PRACTICES["calibration"](d) else "No",
            "Validation on a later survey period": "Yes" if "TEMPORAL" in val else "No",
            "Validation on external data": "Yes" if "EXTERNAL" in val else "No",
            "Importance ranking produced": "Yes" if rank else "No",
            "Importance methods": j(vi02) if rank else NA_CORE,
            "SHAP used": "Yes" if pt.PRACTICES["shap"](d) else "No",
            "Ranking stability checked": ("Yes" if stab else "No") if rank else "Not applicable",
            "Stability approach": (j(STAB.get(v, v) for v in EXP[sid]["importance_stability_methods"]) or "Not described") if stab else NA_CORE,
            "Ranking used for a reduced predictor set": ("Yes" if m.has(d, "VI10", {"USED"}) else "No") if rank else "Not applicable",
            "Ranking used to guide a statistical analysis": ("Yes" if m.has(d, "VI11", {"USED"}) else "No") if rank else "Not applicable",
            "Most important variables as reported": "; ".join(pt.named_variables_all(d)) if rank else NA_CORE,
            "Harmonised variables (Figure 5)": ("; ".join(named["variables_per_study"].get(sid, [])) or "None harmonised") if rank else NA_CORE,
            "Variable domains": "; ".join(sorted(pt.important_domains(d) - {"OTHER"})).replace("_", " ").lower() if rank else NA_CORE,
            "KNHANES sampling weights mentioned": "Yes" if m.has(d, "SUR04", {"USED"}) else "No",
            "Weights in model fitting": STATE.get(first(d, "SUR06"), "Not reported"),
            "Weights in performance evaluation": STATE.get(first(d, "SUR07"), "Not reported"),
            "Strata or PSUs in variance estimation": STATE.get(first(d, "SUR10"), "Not reported"),
            "Combined-year weights": STATE.get(first(d, "SUR11"), "Not reported"),
            "Missing-value handling timing": STEP[pre["missing_value_handling"]],
            "Data-driven preprocessing separation": STEP[pre["scaling_or_other_preprocessing"]],
            "Supervised feature selection timing": "Not reported" if pt.feature_selection_not_reported(d) else STEP[pre["feature_selection"]],  # Codex rule 4
            "Class rebalancing timing": REBALANCE.get(pre["class_rebalancing"], STEP[pre["class_rebalancing"]]),  # Codex rule 1
            "Preprocessing over all applied steps": OVERALL[pt.preprocessing_state(d)],
            "Outcome rebuildable from the report": "Yes" if m.reduce_recoverability(d, "OUT16") == "FULL" else "No",
            "Predictor set rebuildable from the report": "Yes" if m.reduce_recoverability(d, "PRD13") == "FULL" else "No",
            "Analysis code shared": "Yes" if pt.PRACTICES["code_link"](d) else "No",
            "Final model fully specified": "Yes" if m.has(d, "REP17", {"R"}) else "No",
        })
        out.append(rec)
    return out


COLUMNS = {  # Studies sheet: column -> meaning (figure or table it feeds)
    "Study ID": "Identifier used in every sheet and in the figures (KHM + number).",
    "Study": "First author and year (letters separate studies with the same first author and year; Figure 5B labels).",
    "Title": "Title of the representative report.", "Journal": "Journal, preprint server or proceedings.",
    "Year": "Publication year of the representative report.",
    "Publication period": "Figures 4, 6 and 7 and Table 1: up to 2019, 2020-2022, 2023-2024, 2025-2026 (through September 2026).",
    "DOI or PMID": "Identifier of the representative report.", "Report type": "Journal article, Conference paper (including proceedings and book-series chapters), Preprint, Thesis or Abstract, from the report's first page.",
    "Study group": "Figure 2: core classification (192), other health analysis (22, Supplementary Table S5) or method-focused (36, Supplementary Figure S1).",
    "Added under the final eligibility criterion": "Yes = added when single decision trees were counted as ML (Methods); sheet Sensitivity.",
    "Survey years": "Supplementary Figure S2B; KNHANES years analysed, as reported.",
    "Health topic": "Figure 3A; primary health topic (core studies). Columns from here on are coded for the 192 core studies (– elsewhere).",
    "Combining survey years": "Figure 3B.", "KNHANES survey components used": "Figure 3D (a study can use several). Protocol item DAT14, study level: components used anywhere in the analysis, including those that only define the outcome.",
    "Outcome": "Classified outcome as named in the report (first outcome).", "Outcome timing": "Figure 3C (upper rows).",
    "Outcome source": "Figure 3C (lower rows). Every source the outcome definition draws on (e.g. glucose threshold, physician diagnosis or medication = Laboratory value; Diagnosis or history); a study can count under several.", "Outcome group (Figure 5)": "Figure 5A row below the topic (other = pooled outcomes of the topic).",
    "Outcome group (Figure S7A)": "Outcome group from the recorded outcome name, used for the same-outcome pairs of Supplementary Figure S7A (other = no group).",
    "Final analytic sample": "Figure 3E and Supplementary Figure S4.", "Initial candidate predictors": "Figure 3F.",
    "Missing-value handling": "Figure 3G (method; timing is in the preprocessing columns).",
    "Algorithm families fitted": "Figure 3H (a study can fit several).", "Several algorithms compared": "Figure 3I and Table 1.",
    "Family of the selected model": "Figure 3I; family of the model the authors selected (Not designated = several algorithms compared but no final model named).",
    "Systematic hyperparameter search": "Figure 3J.", "Tuning kept apart from the final evaluation": "Table 1 counts Yes (studies without tuning count as Yes). No = tuning, the final model or the threshold was chosen on the evaluation data, or separation was not demonstrated; Not reported = tuning not reported; Unclear = not assessable.",
    "Train-test split": "Figure 3J. A held-out test, temporal or external set used to report performance.",
    "Cross-validation": "Figure 3J. Yes only when cross-validation produced the reported performance; cross-validation used only to tune inside the training data is No.", "AUROC reported": "Figure 3J and Table 1.",
    "Confidence interval reported": "Figure 3J.",
    "Decision threshold reported": "Results (44 studies).", "Threshold chosen without the final evaluation data": "Results (21 of the 44).",
    "Calibration reported": "Figure 6B and Table 1.",
    "Validation on a later survey period": "Figure 6C, Table 1 and Supplementary Figure S6C (Yes in either validation column = validation beyond the development data).",
    "Validation on external data": "Figure 6C and Table 1.", "Importance ranking produced": "Figure 4 and Table 1.",
    "Importance methods": "Supplementary Figure S6E.", "SHAP used": "Figure 4 and Table 1.",
    "Ranking stability checked": "Figure 7A and Table 1 (not applicable without a ranking).", "Stability approach": "Figure 7A, right.",
    "Ranking used for a reduced predictor set": "Results (25 of the 154).", "Ranking used to guide a statistical analysis": "Results (12 of the 154).",
    "Most important variables as reported": "As reported, in the listed order, over every interpreted model.",
    "Harmonised variables (Figure 5)": "Figure 5; harmonised names kept when the study's domains include them (sheet Variable_harmonisation).",
    "Variable domains": "Supplementary Figure S7A; the 15 standardised domains (Jaccard index).",
    "KNHANES sampling weights mentioned": "Figure 7B and Table 1.", "Weights in model fitting": "Figure 7B and Table 1 (Table 1 counts Yes).",
    "Weights in performance evaluation": "Figure 7B and Table 1.", "Strata or PSUs in variance estimation": "Figure 7B and Table 1.",
    "Combined-year weights": "Figure 7B and Table 1.", "Missing-value handling timing": "Figure 7C.",
    "Data-driven preprocessing separation": "Figure 7C (row 'Scaling or other'). Protocol item PRE14: whether other data-dependent preprocessing was fitted within the training data.",
    "Supervised feature selection timing": "Figure 7C. Not reported = the report does not say whether variables were selected (counted with 'not applied' in the computations).",
    "Class rebalancing timing": "Figure 7C. No active intervention reported = no rebalancing step was reported (the figure's 'step not applied').",
    "Preprocessing over all applied steps": "Figure 7C top row and Table 1.",
    "Outcome rebuildable from the report": "Table 1 and Supplementary Figure S3.", "Predictor set rebuildable from the report": "Table 1 and Supplementary Figure S3.",
    "Analysis code shared": "Figure 6A and Table 1.", "Final model fully specified": "Table 1.",
}


NINC = json.loads((ROOT / "results/derived/final_selection_flow.json").read_text())["flow"]["unique_full_report_studies_included"]


def check(studies):
    """Re-add the columns to the published counts (practice_trends_113.json); any mismatch stops the build."""
    core = [r for r in studies if r["Study group"] == "Core classification"]
    C = lambda col, val="Yes", rows=core: sum(r.get(col) == val for r in rows)
    assert (len(studies), len(core)) == (NINC, sum(O["period_n"]))  # review 20261023: group sizes follow the records
    t = O["table1_by_period"]
    for col, key in (("Outcome rebuildable from the report", "outcome_rebuildable"), ("Predictor set rebuildable from the report", "predictor_set_rebuildable"),
                     ("Several algorithms compared", "algorithms_compared"), ("Tuning kept apart from the final evaluation", "tuning_kept_apart"),
                     ("AUROC reported", "auroc"), ("Calibration reported", "calibration"), ("Importance ranking produced", "importance_ranking"),
                     ("SHAP used", "shap"), ("Ranking stability checked", "stability"), ("KNHANES sampling weights mentioned", "weights_mentioned"),
                     ("Weights in model fitting", "weights_in_fitting"), ("Weights in performance evaluation", "weights_in_evaluation"),
                     ("Strata or PSUs in variance estimation", "strata_or_psu"), ("Combined-year weights", "combined_year_weights"),
                     ("Analysis code shared", "code_shared"), ("Final model fully specified", "final_model_fully_specified"),
                     ("Systematic hyperparameter search", "systematic_tuning_search")):
        for p, period in enumerate(pt.PERIODS):
            got = C(col, "Yes", [r for r in core if r["Publication period"] == period])
            assert got == t[key][p], (col, period, got, t[key][p])
    assert C("Preprocessing over all applied steps", "All within the training data") == sum(t["preprocessing_all_within"])
    assert C("Preprocessing over all applied steps", "At least one step before the split") == sum(t["preprocessing_any_before"])
    assert sum(r["Validation on a later survey period"] == "Yes" or r["Validation on external data"] == "Yes" for r in core) == sum(t["validation_beyond_development"])
    assert C("Validation on a later survey period") == sum(1 for d in CORE if "TEMPORAL" in m.flat_values(d, "VAL02"))
    af = O["algorithms_fitted_192"]
    for f, k in (("Boosting", "boosting"), ("Random forest", "random_forest"), ("Logistic regression", "logistic_regression"),
                 ("Decision tree", "decision_tree"), ("SVM", "svm"), ("Neural network", "neural_network"), ("Other", "other")):
        assert sum(f in r["Algorithm families fitted"].split("; ") for r in core) == af[k], (f, af[k])
    sm = O["selected_model_family_192"]
    assert C("Family of the selected model", "Several algorithms not compared") == sm["single_algorithm"]
    assert all(C("Family of the selected model", f) == sm[f] for f, _ in pt.SELECTED_FAMILY_107)
    mh = O["missing_handling_165"]
    for lab, k in (("Complete-case analysis", "complete_case"), ("Single imputation", "single_imputation"), ("Not reported", "not_reported")):
        assert C("Missing-value handling", lab) == mh[k], lab
    tm = O["outcome_timing_192"]
    assert (C("Outcome timing", TIMING["CURRENT"]), C("Outcome timing", TIMING["UNC"])) == (tm["current_state_same_survey"], tm["timing_unclear"])
    cs = O["classified_outcome"]["source"]
    H = lambda col, lab: sum(lab in str(r[col]).split("; ") for r in core)  # list column: studies naming the value
    assert (H("Outcome source", "Questionnaire or scale"), H("Outcome source", "Physical measurement"), H("Outcome source", "Laboratory value")) == \
        (cs["questionnaire_or_scale"], cs["physical_measurement"], cs["laboratory_value"])
    assert sum(isinstance(r["Final analytic sample"], int) for r in core) == O["core_sample"]["reported"]
    assert sum(r["Initial candidate predictors"] != "Not reported" for r in core) == O["candidate_predictors"]["reported"]
    ct = O["core_topics"]
    assert all(C("Health topic", TOPIC[k]) == v for k, v in ct.items()), ct
    sc = O["core_year_scope"]
    assert all(C("Combining survey years", SCOPE[k]) == v for k, v in sc.items()), sc
    pr = O["preprocessing_192"]
    for col, k in (("Missing-value handling timing", "missing_value_handling"), ("Data-driven preprocessing separation", "scaling_or_other_preprocessing"),
                   ("Supervised feature selection timing", "feature_selection"), ("Class rebalancing timing", "class_rebalancing")):
        lab = dict(STEP, **(REBALANCE if col == "Class rebalancing timing" else {}))
        nr = C(col, "Not reported") if col == "Supervised feature selection timing" else 0
        assert all(C(col, lab[s]) + (nr if s == "NA" else 0) == pr[k][s] for s in STEP), col
    assert C("Supervised feature selection timing", "Not reported") == O["feature_selection_not_reported"]
    sd = O["survey_design_192"]
    for col, k in (("Weights in model fitting", "weights_in_fitting"), ("Weights in performance evaluation", "weights_in_evaluation"),
                   ("Combined-year weights", "combined_cycle_weights"), ("Strata or PSUs in variance estimation", "strata_or_psu_in_variance")):
        assert C(col, "Not applicable") == sd[k]["not_applicable"], col
    pt._pin((C("Decision threshold reported"), C("Threshold chosen without the final evaluation data"), C("Ranking used for a reduced predictor set"),
             C("Ranking used to guide a statistical analysis")), (44, 21, 25, 12), "build_data1_workbook.py check thresholds/ranking use")
    rk = [r for r in core if r["Importance ranking produced"] == "Yes"]
    allc = O["rankings_named_112"]["all"]["counts"]
    for v in ("Age", "Sex", "BMI"):
        assert sum(v in r["Harmonised variables (Figure 5)"].split("; ") for r in rk) == allc[v], v
    assert sum("SHAP" in r["Importance methods"].split("; ") for r in rk) == sum(t["shap"])
    stab = [r for r in core if r["Ranking stability checked"] == "Yes"]
    # JCE Results 3.7 (review 2026-10-24): joint uptake among the ranking studies (stability, weights in fitting, all
    # preprocessing within the training data): one study reports all three, 108 none.
    three = [(r["Ranking stability checked"] == "Yes", r["Weights in model fitting"] == "Yes",
              r["Preprocessing over all applied steps"] == "All within the training data") for r in rk]
    pt._pin((sum(all(x) for x in three), sum(not any(x) for x in three)), (1, 108), "build_data1_workbook.py joint uptake")
    pt._pin(sum(r["Stability approach"] == "Not described" for r in stab), 14, "build_data1_workbook.py stability not described")
    sm = O["stability_methods"]  # Figure 7A, right: one study can use two approaches
    for lab, code in (("Subgroups", "SUBGROUP_CONSISTENCY"), ("Resamples", "RESAMPLING_STABILITY"), ("External data", "EXTERNAL_DATA_REPLICATION"),
                      ("Intervals", "UNCERTAINTY_INTERVAL"), ("Sensitivity analyses", "SENSITIVITY_ANALYSIS")):
        assert sum(lab in r["Stability approach"].split("; ") for r in stab) == sm.get(code, 0), (lab, sm.get(code, 0))
    # Supplementary Figure S7A from the Studies columns alone (prompt 115: the Reproduce rule is checked).
    import itertools, statistics
    core3 = {"age", "sex", "adiposity body size"}
    dom = {r["Study ID"]: set(r["Variable domains"].split("; ")) - {""} for r in rk}
    og = {r["Study ID"]: r["Outcome group (Figure S7A)"] for r in rk}
    tp = {r["Study ID"]: r["Health topic"] for r in rk}
    pairs = {"same_outcome": [], "different_topic": []}
    for a, b in itertools.combinations(sorted(dom), 2):
        k = "same_outcome" if og[a] != "other" and og[a] == og[b] else "different_topic" if tp[a] != tp[b] else None
        x, y = dom[a] - core3, dom[b] - core3
        if k and x | y:
            pairs[k].append(len(x & y) / len(x | y))
    ref = O["domain_agreement_098"]["without_age_sex_body_size"]
    assert all((len(v), round(statistics.median(v), 3)) == (ref[k]["pairs"], ref[k]["median"]) for k, v in pairs.items()), \
        {k: (len(v), statistics.median(v)) for k, v in pairs.items()}
    s = O["sensitivity_without_added_113"]
    assert sum(r["Added under the final eligibility criterion"] == "Yes" for r in core) == s["added_core"]
    assert sum(r["Added under the final eligibility criterion"] == "Yes" for r in studies) == s["added_studies"]


def sheet(wb, title, headers, rows, widths=None, freeze="A2", title_rows=None):
    ws = wb.create_sheet(title)
    start = 1
    if title_rows:
        for t in title_rows:
            ws.append([t]); ws.cell(ws.max_row, 1).font = Font(bold=bool(t) and t is title_rows[0])
        start = ws.max_row + 1
    ws.append(headers)
    for c in ws[start]:
        c.font = Font(bold=True); c.fill = HEADER_FILL; c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in rows:
        ws.append(list(r))
    ws.freeze_panes = freeze if not title_rows else f"A{start + 1}"
    ws.auto_filter.ref = f"A{start}:{get_column_letter(len(headers))}{ws.max_row}"
    for i, h in enumerate(headers, 1):
        w = (widths or {}).get(h) or min(60, max(10, len(str(h)) + 2, *(len(str(r[i - 1])) + 1 for r in rows[:200] if i - 1 < len(r))))
        ws.column_dimensions[get_column_letter(i)].width = w
    return ws


OVERRIDES = ROOT / "additional_file_review/OVERRIDES.tsv"


def _regrouped():
    import csv
    p = ROOT / "additional_file_review/RECORD_CORRECTIONS.tsv"
    return {r["study_id"] for r in csv.DictReader(p.open(encoding="utf-8"), delimiter="\t") if r["column"] == "Study group"} if p.exists() else set()


REGROUPED = _regrouped()


def report_type(v, journal):
    """Author decision D18: Journal article, Conference paper, Preprint, Thesis or Abstract (from the recorded type)."""
    t = f"{v} {journal or ''}".lower()
    if re.search(r"preprint|research square|medrxiv|biorxiv|arxiv|ssrn", t):
        return "Preprint"
    if re.search(r"thesis|dissertation|학위", t):
        return "Thesis"
    if re.search(r"conference|proceedings|symposium|congress|book chapter|lecture notes", str(v).lower()):
        return "Conference paper"
    if re.search(r"\babstract\b", str(v).lower()):
        return "Abstract"
    return "Journal article"


def apply_overrides(rows_by_id, final=False):
    """Corrections agreed by the two AI reviews and integrated (additional_file_review/CYCLE.md): study_id, column,
    new_value, reason, source, revision. Applied before check(), so a correction that would change a published count
    stops the build; with final=True, an override naming an unknown row or column also stops the build."""
    if not OVERRIDES.exists():
        return 0
    import csv
    n = 0
    with OVERRIDES.open(encoding="utf-8") as fh:
        for o in csv.DictReader(fh, delimiter="\t"):
            r = rows_by_id.get(o["study_id"])
            if r is None or (final and o["column"] not in r):
                if final and o["study_id"] in REGROUPED:  # review 20261023: the cell left with the study's old group
                    print(f"override skipped (study regrouped): {o['study_id']} | {o['column']}")
                    continue
                if final:
                    raise SystemExit(f"override for unknown cell: {o['study_id']} | {o['column']}")
                continue
            if o["column"] == "Study" and o["study_id"].startswith("KHM"):
                n += 1; continue  # applied as the label base in study_labels (lettering recomputed)
            if o["column"] in r or final:
                r[o["column"]] = o["new_value"]; n += 1
    return n


def main():
    """Prompt 117 (author): Additional Data 1 is ONE sheet. Each included study is one row and every result is a column
    (the former side sheets became columns); the 97 regression-only or unsupervised reports of Figure 1 follow as rows of
    their own group. Column definitions are notes on the header cells."""
    from collections import defaultdict
    from openpyxl.comments import Comment
    rows, dic = full_log_rows()
    studies = build_studies(rows)
    apply_overrides({r["Study ID"]: r for r in studies})  # review-loop corrections, checked against the published counts
    check(studies)
    by_id = {r["Study ID"]: r for r in studies}
    lab = study_labels(rows)
    cols = list(COLUMNS)
    extra = {}  # column -> meaning, for columns added below

    def add(sid, col, val, meaning):
        extra.setdefault(col, meaning)
        by_id[sid][col] = val

    # Task, other health-focused and method-focused studies (Figure 2B, Supplementary Table S5, Supplementary Figure S1).
    hdocs = {d["study_id"]: d for d in pt.HEALTH}
    core_ids = {d["study_id"] for d in CORE}
    task_other = {"CONT": "Continuous or ordered outcome", "OTHER": "Other analysis"}
    for sid, r in rows.items():
        if sid in core_ids:
            task = "Classification"
        elif sid in hdocs:
            task = task_other.get(m.first(hdocs[sid], "TSK01"), "Other analysis")
        else:
            task = readable(r["B_method_contribution"])
        add(sid, "Task", task, "Figure 2B: classification (core), continuous or ordered outcome or other analysis (other health-focused), "
            "develops or improves a method or compares existing methods (method-focused).")
        if sid in hdocs and sid not in core_ids:
            target = str(r["E_outcome_name"]).split("|")[0].strip()
            target = OTHER_HEALTH_SHORT.get(sid, target) if target in ("NA", "NR", "") else target
            by_id[sid]["Outcome"] = target
            add(sid, "Other-health algorithms", readable(r["G_algorithm_families"]), "Supplementary Table S5 (other health-focused studies).")
            add(sid, "Other-health internal validation", readable(r["H_internal_validation"]), "Supplementary Table S5.")
            add(sid, "Other-health validation beyond the development data",
                j(("Earlier survey period" if sid == "KHM067" else t) for t, k in (("Later survey period", "H_later_period_validation"), ("External data", "H_external_validation")) if r[k] == "Y") or "None reported",  # D21 B: KHM067 validated on 2010-2011
                "Supplementary Table S5.")
            add(sid, "Other-health importance", readable(r["I_importance_methods"]) if r["I_importance_reported"] == "USED" else "No ranking",
                "Supplementary Table S5.")
        if r["B_method_focused"] == "Y":
            add(sid, "Method workflow stages", readable(r["B_method_target_stages_display"]), "Supplementary Figure S1B (method-focused studies).")
            add(sid, "Method evaluation design", readable(r["B_method_evaluation_design"]), "Supplementary Figure S1C.")
            add(sid, "Method comparators", readable(r["B_method_comparators"]), "Supplementary Figure S1 (as coded).")
            add(sid, "Role of KNHANES", readable(r["B_KNHANES_role"]), "Supplementary Figure S1 and S2A.")
    pt._pin((sum(by_id[s]["Task"] == "Continuous or ordered outcome" for s in by_id), sum(by_id[s]["Task"] == "Develops or improves a method" for s in by_id)),
            (14, 26), "build_data1_workbook.py tasks")  # review 20261023 pin

    # Variable names as recorded with their harmonised label (Figure 5; 2,029 of 2,233 matched).
    r112 = O["rankings_named_112"]
    n_all = n_hit = 0
    for d in CORE:
        if not pt.PRACTICES["importance_ranking"](d):
            continue
        pairs = []
        for v in pt.named_variables_all(d):
            labv = pt.harmonised_label(v); n_all += 1; n_hit += labv is not None
            if d["study_id"] in pt.NUTRIENT_ONLY and labv in ("Cholesterol or triglycerides", "Diabetes diagnosis", "HbA1c or fasting glucose"):
                labv = "Diet or nutrients"  # as study_variables() (nutrient-intake indices)
            pairs.append(f"{v} = {labv or 'not matched'}")
        add(d["study_id"], "Variable names and harmonised labels", "; ".join(pairs),
            "Figure 5: each recorded name = its harmonised label (not matched = no pattern); a label counts for the study when its coded domains include it.")
    nv = O["named_variable_count_all_models"]
    assert (n_all, n_hit) == (nv["strings"], nv["strings_mapped"])
    pt._pin((n_all, n_hit), (2233, 2029), "build_data1_workbook.py variable strings")  # review 20261023 pin

    # Reporting (Supplementary Figure S8A): 19 TRIPOD+AI-derived elements, core studies.
    code = {"R": "Reported", "P": "Partly reported", "NR": "Not reported", "NA": "Not applicable"}
    for k in (f"K_REP{i:02d}" for i in range(1, 20)):
        labk = str(dic[k][2]).replace("Reporting completeness for: ", "").split(". ")[0].rstrip(".")
        for sid in core_ids:
            add(sid, f"Reporting {int(k[5:]):02d}: {labk}", code.get(str(rows[sid][k]), str(rows[sid][k])),
                "Supplementary Figure S8A; TRIPOD+AI-derived element (Supplementary Table S6).")

    # PROBAST+AI (Supplementary Figure S8B), counted in units: per study, number of units with each judgement.
    tot = Counter()
    for kind, f in (("development", "PROBAST_AI_development_units.tsv"), ("evaluation", "PROBAST_AI_evaluation_units.tsv")):
        lines = (ROOT / "data/repository_release" / f).read_text().splitlines()
        h = lines[0].split("\t")
        per = defaultdict(lambda: defaultdict(Counter))
        for l in lines[1:]:
            x = dict(zip(h, l.split("\t")))
            if x["study_id"] not in core_ids:
                continue
            tot[kind] += 1
            for c in ("domain_1", "domain_2", "domain_3", "domain_4", "overall"):
                per[x["study_id"]][c][x[c]] += 1
            tot[(kind, "HIGH")] += x["overall"] == "HIGH"
        for sid in core_ids:
            for c, name in (("overall", "overall"), ("domain_1", "domain 1"), ("domain_2", "domain 2"), ("domain_3", "domain 3"), ("domain_4", "domain 4")):
                cnt = per[sid][c]
                assert set(cnt) <= {"LOW", "HIGH", "UNCLEAR"}, cnt
                add(sid, f"PROBAST+AI {kind} units, {name}", "; ".join(f"{v} {cnt[v]}" for v in ("LOW", "HIGH", "UNCLEAR") if cnt[v]) or "No units",
                    f"Supplementary Figure S8B: number of {kind} units of the study with each judgement (LOW, HIGH, UNCLEAR); counted in units.")
    pt._pin((tot["development"], tot["evaluation"], tot[("evaluation", "HIGH")]), (297, 378, 375), "build_data1_workbook.py PROBAST units")  # review 20261023 pin

    # Source locations of the evidence behind the coded columns (item: PDF page and object or section).
    anchors = {}
    wbf = load_workbook(FULL_LOG, read_only=True)
    it = wbf["EVIDENCE_ANCHORS"].iter_rows(values_only=True)
    ah = list(next(it)); ax = {k: i for i, k in enumerate(ah)}
    for r in it:
        obj = r[ax["object_label"]] if r[ax["object_label"]] not in (None, "NR", "NA") else r[ax["section"]]
        anchors[r[ax["evidence_id"]]] = f"p.{r[ax['pdf_page']]} {obj}".strip()
    loc = defaultdict(dict)
    it = wbf["ITEM_RESPONSES"].iter_rows(values_only=True)
    ih = list(next(it)); ix = {k: i for i, k in enumerate(ih)}
    for r in it:
        item = r[ix["item_id"]]
        if item not in EVIDENCE_ITEMS:
            continue
        for e in str(r[ix["evidence_ids"]] or "").split("\n"):
            e = e.strip()
            if e in anchors:
                loc[r[ix["study_id"]]].setdefault(item, set()).add(anchors[e])
    wbf.close()
    for sid in by_id:
        txt = " | ".join(f"{item}: " + "; ".join(sorted(v)) for item, v in sorted(loc.get(sid, {}).items()))
        by_id[sid]["Evidence locations"] = txt[:32000] or "None linked"
    extra["Evidence locations"] = ("Source locations of the evidence for the coded items (protocol item: PDF page and table, figure or section); "
                                   "items: " + "; ".join(f"{k} = {v}" for k, v in EVIDENCE_ITEMS.items()) + ".")
    assert sum(by_id[s]["Evidence locations"] != "None linked" for s in core_ids) >= len(core_ids) - 2

    # The 97 reports using only regression-family or unsupervised methods (Figure 1) as rows of their own group.
    sf = json.loads((ROOT / "results/derived/final_selection_flow.json").read_text())
    wbf = load_workbook(FULL_LOG, read_only=True)
    adj = list(wbf["ML_ADJACENT_REPORTS"].iter_rows(values_only=True)); wbf.close()
    gone = {str(u).replace("kci:", "KCI ").lower() for u in sf["unified_screening"]["kci_advanced_records_now_screened_out"]}
    dup = {c["record"].split(" ")[0] for c in sf.get("coordinator_corrections", [])}  # review 20261023: yeonyu2015three = X015's report
    adj_rows = [r for r in adj[1:] if str(r[2]).lower() not in gone and not dup & {str(x) for x in r}]
    assert len(adj_rows) == sf["flow"]["ml_adjacent_reports_catalogued"], (len(adj_rows), sf["flow"]["ml_adjacent_reports_catalogued"])
    # Prompt 119 (review v54): journal and first author of the reports not included, from the search records.
    meta = {}
    corpus = json.loads((ROOT / "results/derived/corpus.json").read_text())
    corpus = corpus if isinstance(corpus, list) else corpus.get("records", list(corpus.values()))
    for x in corpus:
        a = x.get("author_list") or x.get("authors") or ""
        a = (a[0] if isinstance(a, list) and a else a) if not isinstance(a, str) else a.split(";")[0].split(",")[0]
        a = a.get("name", "") if isinstance(a, dict) else str(a)
        for key in (x.get("doi"), f"PMID {x['pmid']}" if x.get("pmid") else None, x.get("uid"), x.get("oa_id")):
            if key:
                meta.setdefault(str(key).lower(), (x.get("journal") or "", a))
    import csv
    with open(ROOT / "data/KCI_CANDIDATES.tsv", encoding="utf-8-sig") as fh:
        for x in csv.DictReader(fh, delimiter="\t"):
            v = (x["journal"], x["authors"].split(";")[0].strip())
            for key in (x.get("doi"), f"KCI {x['kci_id']}", x.get("corpus_uid")):
                if key:
                    meta.setdefault(key.lower(), v)
    def surname_year(author, year):
        author = str(author).strip()
        if not author:
            return ""
        parts = author.replace(",", " ").split()
        last = parts[0] if (len(parts) > 1 and len(parts[-1]) <= 2 and parts[-1].isupper()) else parts[-1]
        return f"{last} {year}"
    out_rows = [by_id[s] for s in sorted(by_id)]
    missing_meta = 0
    # Review 2026-10-23/24: rows left the catalogue (X016 duplicate, X019 isolated abstract, four reports included):
    # each remaining report keeps the X ID it had in the first Additional Data 1 (matched by title).
    first = ROOT / "prompts/implementation_records/review_corrections_20261023/pristine/paper/KNHANES_ML_review_Additional_Data_1.xlsx"
    old_id = {}
    if first.exists():
        _r = list(load_workbook(first, read_only=True).active.iter_rows(values_only=True))
        _h = list(_r[0])
        for x in _r[1:]:  # first ID wins (X016 repeated X015's title)
            if str(x[0]).startswith("X"):
                old_id.setdefault(str(x[_h.index("Title")]).strip().lower(), x[0])
    xids = [int(str(old_id.get(str(r[1]).strip().lower(), "X%03d" % (900 + i)))[1:]) for i, r in enumerate(adj_rows)]
    assert len(set(xids)) == len(xids), "X IDs collide"
    for k, r in zip(xids, adj_rows):
        jn, au = meta.get(str(r[2]).lower(), ("", ""))
        missing_meta += not jn
        out_rows.append({"Study ID": f"X{k:03d}", "Study": surname_year(au, r[0]) or "not recorded", "Journal": jn or "not recorded",
                         "Title": r[1], "Year": int(r[0]) if str(r[0]).isdigit() else r[0], "DOI or PMID": r[2],
                         "Study group": "Not included: only regression-family or unsupervised methods",
                         "Reason not included": re.sub(r"\b(INCLUDE_ADJACENT|INCLUDE|EXCLUDE)\s*:\s*", "", f"{r[3]}. {r[4]}")})  # review 20261023
    print("reports not included without a recorded journal:", missing_meta)
    extra["Reason not included"] = "Figure 1: methods used and why the report is not included (not included rows only)."

    n_ov = apply_overrides({r["Study ID"]: r for r in out_rows}, final=True)
    print("review overrides applied:", n_ov)
    for r in out_rows:  # author decision D18 (2026-10-23): five report types; "NR" rows are journal articles (journal recorded)
        if r.get("Report type") not in (None, "", NA_CORE):
            r["Report type"] = report_type(r["Report type"], r.get("Journal"))
    order = cols[:cols.index("Survey years")] + ["Task", "Reason not included"] + cols[cols.index("Survey years"):] + \
        [c for c in extra if c not in ("Task", "Reason not included")]
    meaning = {**COLUMNS, **extra}
    from collections import Counter as _C  # review 20261023: header counts follow the data
    grp = _C(r["Study group"] for r in out_rows); nx = len(out_rows) - NINC; lu = O["later_use_among_ranking"]
    meaning["Study ID"] = f"KHM + number for the {NINC} included studies; X + number for the {nx} reports not included (Figure 1)."
    meaning["Study group"] = (f"Figure 2: core classification ({grp['Core classification']}), other health analysis ({grp['Other health analysis']}, "
                              f"Supplementary Table S5) or method-focused ({grp['Method-focused']}, Supplementary Figure S1). "
                              f"Not included: the {nx} reports using only regression-family or unsupervised methods.")
    meaning["Health topic"] = COLUMNS["Health topic"].replace("192 core", f"{grp['Core classification']} core")
    meaning["Ranking used for a reduced predictor set"] = f"Results ({lu['reduced_predictor_set']} of the {lu['n']})."
    meaning["Ranking used to guide a statistical analysis"] = f"Results ({lu['subsequent_statistical_analysis']} of the {lu['n']})."

    wb = Workbook(); ws = wb.active; ws.title = "Additional Data 1"
    ws.append([remap(c) for c in order])  # header names cite the journal's figure numbers (internal names keep BMC numbers)
    for c, name in zip(ws[1], order):
        c.font = Font(bold=True); c.fill = HEADER_FILL; c.alignment = Alignment(wrap_text=True, vertical="top")
        c.comment = Comment(remap(meaning[name]), "Additional Data 1", width=360, height=140)  # journal figure numbers
    for r in out_rows:
        ws.append([r.get(c, "" if r["Study group"].startswith("Not included") else NA_CORE) for c in order])
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(order))}{ws.max_row}"
    for i, name in enumerate(order, 1):
        ws.column_dimensions[get_column_letter(i)].width = {"Title": 50, "Most important variables as reported": 50,
                                                            "Variable names and harmonised labels": 60, "Evidence locations": 60,
                                                            "Reason not included": 50}.get(name, min(28, max(10, len(name) // 2 + 4)))
    assert len(out_rows) == NINC + sf["flow"]["ml_adjacent_reports_catalogued"] and len(wb.sheetnames) == 1
    wb.save(OUT)
    import add_checklist_columns_v22  # v22: 43 core items incl. data availability, IDs C01-C43 (Table 1, Figure 5)
    add_checklist_columns_v22.main()
    print(json.dumps({"written": str(OUT.relative_to(ROOT)), "sheets": wb.sheetnames, "rows": len(out_rows), "columns": len(order)}))


if __name__ == "__main__":
    main()
