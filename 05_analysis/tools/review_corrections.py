#!/usr/bin/env python3
"""Review-loop corrections (2026-10-23): write the corrections the two-AI review of Additional Data 1 settled into the
adjudicated study records, so every figure, table and count is recomputed from corrected records.

    python tools/review_corrections.py            # restore the pristine records, then apply RECORD_CORRECTIONS.tsv

Input: additional_file_review/RECORD_CORRECTIONS.tsv (study_id, column, value, basis, evidence), one row per
Additional Data 1 cell, in the sheet's vocabulary. Each column has a handler that changes the record fields the
column is derived from (protocol items, analytic flow, model-task audit, purpose audits). Every change is logged in
the record (adjudication.coordinator_corrections, stage REVIEW_20261023), as prompt 106 did.
Idempotent: the records are first restored from the pre-correction copies in
prompts/implementation_records/review_corrections_20261023/pristine/ (extracted from before.tar.gz).
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "prompts/implementation_records/review_corrections_20261023"
PRISTINE = REC / "pristine"
TSV = ROOT / "additional_file_review/RECORD_CORRECTIONS.tsv"
FINAL = ROOT / "data/protocol_v1_2/final"
EXPF = ROOT / "results/derived/expanded_model_task_audit.json"
PURF = ROOT / "results/derived/study_purpose_audit.json"
V13F = ROOT / "data/protocol_v1_3/purpose_evidence_addendum.json"
STAGE = "REVIEW_20261023"

FAMILY = {"Boosting": {"XGBoost", "LightGBM", "Gradient boosting"}, "Random forest": {"Random forest"},
          "Logistic regression": {"Logistic regression"}, "Decision tree": {"Decision tree"}, "SVM": {"SVM"},
          "Neural network": {"DNN/MLP"}}
FAMILY_TOKEN = {"Boosting": "Gradient boosting", "Random forest": "Random forest", "Logistic regression": "Logistic regression",
                "Decision tree": "Decision tree", "SVM": "SVM", "Neural network": "DNN/MLP", "Other": "Other"}
SOURCE = {"Questionnaire or scale": "VALIDATED_QUESTIONNAIRE_OR_SCALE", "Physical measurement": "CLINICAL_OR_PHYSICAL_MEASUREMENT",
          "Laboratory value": "LABORATORY_THRESHOLD", "Diagnosis or history": "PHYSICIAN_DIAGNOSIS", "Other": "OTHER_REPORTED_SOURCE",
          "Not reported": "NOT_REPORTED"}
TOPIC = {"Metabolic and endocrine": "METABOLIC_ENDOCRINE", "Mental health": "MENTAL_HEALTH", "Cardiovascular": "CARDIOVASCULAR",
         "Musculoskeletal": "MUSCULOSKELETAL", "Oral health": "ORAL_HEALTH", "Respiratory": "RESPIRATORY",
         "Ear, nose and throat": "OTORHINOLARYNGOLOGIC", "General health": "GENERAL_HEALTH_MULTIMORBIDITY",
         "Kidney and urologic": "KIDNEY_UROLOGIC", "Eye health": "OPHTHALMOLOGIC", "Nutrition and diet": "NUTRITION_DIET",
         "Health behaviour": "HEALTH_BEHAVIOUR", "Cancer": "CANCER", "Skin and allergy": "DERMATOLOGIC_ALLERGIC",
         "Other or cross-cutting": "OTHER_OR_CROSS_CUTTING"}
IMPORTANCE = {"SHAP": "SHAP", "Model-native": "MODEL_NATIVE", "Coefficient or statistic": "COEFFICIENT_STATISTIC",
              "Permutation": "PERMUTATION", "Tree or rule": "TREE_RULE", "Perturbation or ablation": "PERTURBATION_ABLATION",
              "LIME": "LIME", "Partial dependence": "PDP", "Other": "OTHER"}
STAB = {"Subgroups": "SUBGROUP_CONSISTENCY", "Resamples": "RESAMPLING_STABILITY", "External data": "EXTERNAL_DATA_REPLICATION",
        "Intervals": "UNCERTAINTY_INTERVAL", "Sensitivity analyses": "SENSITIVITY_ANALYSIS",  # D20 A
        "Not described": "METHOD_NOT_RECOVERABLE"}
MISSING = {"Complete-case analysis": "COMPLETE", "Single imputation": "SINGLE_IMP", "Multiple imputation": "MULTI_IMP",
           "Model-native": "MODEL_NATIVE", "Other or several": "OTHER", "Not reported": "NR"}
# Timing columns: item and the code written for each state (practice_trends.PRE_SPECS reads them back).
TIMING = {"Missing-value handling timing": ("PRE05", {"Within the training data": "USED", "Before the split": "NOT_USED",
                                                      "Timing unclear": "NR", "Not applied": "NA"}),
          "Data-driven preprocessing separation": ("PRE14", {"Within the training data": "USED", "Before the split": "NOT_USED",
                                                               "Timing unclear": "NR", "Not applied": "NA"}),
          "Supervised feature selection timing": ("PRE13", {"Within the training data": "WITHIN", "Before the split": "BEFORE",
                                                 "Timing unclear": "ORDER_NR", "Not applied": "NA", "Not reported": "NA"}),
          "Class rebalancing timing": ("IMB03", {"Within the training data": "WITHIN", "Before the split": "BEFORE",
                                                 "Timing unclear": "ORDER_NR", "Not applied": "NA",
                                                 "No active intervention reported": "NA"})}
VALIDATION = {"Train-test split": "SPLIT", "Cross-validation": "CV", "Validation on a later survey period": "TEMPORAL",
              "Validation on external data": "EXTERNAL"}
YESNO_ITEM = {"Importance ranking produced": ("VI01", "USED", "NOT_USED"), "Ranking stability checked": ("VI16", "USED", "NOT_USED"),
              "Several algorithms compared": ("FUN_COMPARE", "PRESENT", "ABSENT"), "Confidence interval reported": ("MET_CI", "Y", "N"),
              "KNHANES sampling weights mentioned": ("SUR04", "USED", "NOT_USED"), "Ranking used for a reduced predictor set": ("VI10", "USED", "NOT_USED"),
              "Ranking used to guide a statistical analysis": ("VI11", "USED", "NOT_USED"), "Analysis code shared": ("MOD15", "USED", "NOT_USED"),
              "Final model fully specified": ("REP17", "R", "P")}  # coding audit 2026-10-29: not fully specified = partly reported
STATE_ITEM = {"Weights in model fitting": "SUR06", "Weights in performance evaluation": "SUR07",
              "Strata or PSUs in variance estimation": "SUR10", "Combined-year weights": "SUR11"}
STATE = {"Yes": "USED", "No": "NOT_USED", "Not reported": "NR", "Unclear": "UNC", "Not applicable": "NA"}
TUNING = {"Yes": "TUNING_REPORTED_SEPARATED", "No": "TUNING_REPORTED_EVALUATION_DATA_INVOLVED",
          "Not demonstrated": "TUNING_REPORTED_SEPARATION_NOT_DEMONSTRATED", "Not reported": "TUNING_NOT_REPORTED",
          "Unclear": "NOT_ASSESSABLE", "No tuning": "NO_TUNING_OR_DEFAULT_MODEL"}
GROUP = {"Core classification": ("HEALTH_ANALYSIS", "CLASSIFICATION", "HEALTH_FOCUSED"),
         "Other health analysis": ("HEALTH_ANALYSIS", None, "HEALTH_FOCUSED"),
         "Method-focused": ("METHOD_RESEARCH", None, "METHOD_FOCUSED")}
METHOD_TASK = {"Develops or improves a method": ("METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT", "NEW_OR_IMPROVED_METHOD"),
               "Compares existing methods": ("EXISTING_METHODS_COMPARISON_OR_EVALUATION", "EXISTING_METHOD_COMPARISON_BENCHMARK")}
STAGES = {"data preparation": "DATA_INTEGRATION", "data integration or harmonisation": "DATA_INTEGRATION",
          "feature construction or selection": "FEATURE_CONSTRUCTION_OR_SELECTION",
          "variable construction or selection": "FEATURE_CONSTRUCTION_OR_SELECTION", "model development": "MODEL_DEVELOPMENT",
          "validation or performance": "VALIDATION_OR_PERFORMANCE", "explanation or interpretation": "EXPLANATION_OR_INTERPRETATION",
          "missing data": "MISSING_DATA", "user tool or workflow": "USER_TOOL_OR_WORKFLOW", "causal or structure": "CAUSAL_OR_STRUCTURE"}
PURPOSE_STAGE = {"DATA_INTEGRATION": "DATA_INTEGRATION_OR_HARMONISATION", "FEATURE_CONSTRUCTION_OR_SELECTION": "FEATURE_ENGINEERING_OR_SELECTION",
                 "MODEL_DEVELOPMENT": "PREDICTION_OR_CLASSIFICATION", "VALIDATION_OR_PERFORMANCE": "VALIDATION_OR_PERFORMANCE_EVALUATION",
                 "EXPLANATION_OR_INTERPRETATION": "EXPLAINABLE_AI", "MISSING_DATA": "MISSING_DATA", "USER_TOOL_OR_WORKFLOW": "USER_TOOL_OR_WORKFLOW",
                 "CAUSAL_OR_STRUCTURE": "CAUSAL_OR_STRUCTURE_LEARNING"}
EVAL = {"application or demonstration": ("APPLICATION_DEMONSTRATION", "APPLICATION_OR_DEMONSTRATION"),
        "empirical comparator evaluation": ("EMPIRICAL_COMPARATOR", "EMPIRICAL_COMPARATOR_EVALUATION"),
        "simulation and empirical application": ("SIMULATION_PLUS_EMPIRICAL", "SIMULATION_AND_EMPIRICAL_APPLICATION")}


def items(d, key):
    return d["protocol_items"].setdefault(key, [])


def set_all(d, key, value):
    rows = items(d, key)
    if not rows:
        rows.append({"item_role": "reviewer_entered", "unit_id": d["study_id"], "value": value, "value_status": "ANSWERED",
                     "evidence_ids": [], "status": "COMPLETE", "rationale": None})
    for r in rows:
        r["value"] = value
        r["review_stage"] = STAGE


def mr(rec):
    if not isinstance(rec.get("method_research"), dict):
        rec["method_research"] = {"target_analysis_stages": [], "comparators": [], "evaluation_datasets": [],
                                  "primary_evaluation_criteria": [], "evidence_ids": []}
    return rec["method_research"]


def split(v):
    return [x.strip() for x in str(v).split(";") if x.strip()]


class Ctx:
    def __init__(self):
        self.docs = {p.name[:6]: json.loads(p.read_text()) for p in sorted(FINAL.glob("KHM*_final.json"))}
        self.exp = json.loads(EXPF.read_text())
        self.pur = json.loads(PURF.read_text())
        self.v13 = json.loads(V13F.read_text())
        self.E = {x["study_id"]: x for x in self.exp["studies"]}
        self.P = {x["study_id"]: x for x in self.pur["records"]}
        self.V = {x["study_id"]: x for x in self.v13["records"]}
        self.touched = set()

    def log(self, sid, column, old, new, basis, evidence):
        d = self.docs[sid]
        d.setdefault("adjudication", {}).setdefault("coordinator_corrections", []).append(
            {"column": column, "from": old, "to": new, "stage": STAGE, "basis": basis, "evidence": evidence[:600]})
        self.touched.add(sid)

    def save(self):
        for sid in self.touched:
            d = self.docs[sid]
            d["protocol_items_sha256"] = hashlib.sha256(json.dumps(d["protocol_items"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            (FINAL / f"{sid}_final.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        EXPF.write_text(json.dumps(self.exp, ensure_ascii=False, indent=2) + "\n")
        from collections import Counter  # summary block follows the corrected records (as built, NOT_APPLICABLE is not counted)
        S, R = self.pur.get("summary", {}), self.pur["records"]
        for k, v in list(S.items()):
            if isinstance(v, dict) and R and k in R[0]:
                c = Counter(x for r in R for x in (r[k] if isinstance(r[k], list) else [r[k]]))
                if "NOT_APPLICABLE" not in v:
                    c.pop("NOT_APPLICABLE", None)
                S[k] = dict(c)
        PURF.write_text(json.dumps(self.pur, ensure_ascii=False, indent=2) + "\n")
        V13F.write_text(json.dumps(self.v13, ensure_ascii=False, indent=2) + "\n")


def apply(c: Ctx, sid, column, value, basis, evidence):
    d = c.docs[sid]
    fl = d.setdefault("adjudication", {}).setdefault("analytic_flow", {}).setdefault("fields", {})
    alg = c.E[sid]["algorithm_development"] if sid in c.E else None
    if column == "Algorithm families fitted":
        want = set(split(value)) - {"Not recorded"}
        toks = list(alg["algorithm_family"])
        known = set().union(*FAMILY.values())
        for fam, s in FAMILY.items():
            has = bool(set(toks) & s)
            if fam in want and not has:
                toks.append(FAMILY_TOKEN[fam])
            if fam not in want and has:
                toks = [t for t in toks if t not in s]
        other = [t for t in toks if t not in known]
        if "Other" in want and not other:
            toks.append("Other")
        if "Other" not in want:
            toks = [t for t in toks if t in known]
        old, alg["algorithm_family"] = alg["algorithm_family"], toks
    elif column == "Outcome rebuildable from the report":  # coding audit 2026-10-29 (RC10 = same concept as OUT16 FULL)
        old = [r.get("value") for r in items(d, "OUT16")]
        set_all(d, "OUT16", "R2" if value == "Yes" else "R1")
    elif column == "Systematic hyperparameter search":
        old = alg["hyperparameter_tuning_method"]
        alg["hyperparameter_tuning_method"] = "OTHER_REPORTED" if value == "Yes" else (
            "MANUAL_OR_DEFAULT" if old in ("GRID_SEARCH", "RANDOM_SEARCH", "BAYESIAN_OR_OTHER_OPTIMISATION", "OTHER_REPORTED") else old)
    elif column == "Tuning kept apart from the final evaluation":
        old = alg["tuning_selection_status"]
        if value == "Yes" and old not in ("TUNING_REPORTED_SEPARATED", "NO_TUNING_OR_DEFAULT_MODEL"):
            alg["tuning_selection_status"] = "TUNING_REPORTED_SEPARATED"
        elif value != "Yes":
            alg["tuning_selection_status"] = TUNING[value]
    elif column == "Family of the selected model":
        sel = d.setdefault("best_model_selections", [{}]) or [{}]
        if not d["best_model_selections"]:
            d["best_model_selections"] = sel
        old = sel[0].get("review_selected_family")
        sel[0]["review_selected_family"] = value
    elif column == "Source sample and total excluded":  # coding audit S03 (2026-10-29): "POP08 n; POP10 n" from the flow chart
        old = [[r.get("value") for r in items(d, k)] for k in ("POP08", "POP10")]
        n8, n10 = [x.strip() for x in value.split(";")]
        set_all(d, "POP08", n8)
        set_all(d, "POP10", n10)
    elif column in ("Initial candidate predictors", "Final analytic sample"):
        key = "initial_candidate_predictor_count" if column.startswith("Initial") else "final_analytic_sample_n"
        f = fl.setdefault(key, {})
        old = f.get("value")
        if value == "Not reported":
            f.update(value="NR", value_status="NOT_REPORTED")
        else:
            f.update(value=int(value), value_status="REPORTED")
        f["derivation_note"] = f"{STAGE}: {basis}"
    elif column == "Outcome source":
        f = fl.setdefault("outcome_ascertainment_source_category", {})
        old = f.get("value")
        codes = [SOURCE[v] for v in split(value)]
        f.update(value=codes if len(codes) > 1 else codes[0], value_status="DERIVED")
        f["derivation_note"] = f"{STAGE}: every source of the outcome definition (author rule: composite definitions keep all components)"
    elif column == "Health topic":
        ht = c.V[sid]["health_topic"]
        old = ht["primary_topic_18"]
        ht["primary_topic_18"] = TOPIC[value]
        d["adjudication"].get("purpose_evidence_v1_3", {}).get("health_topic", {})["primary_topic_18"] = TOPIC[value]
    elif column in YESNO_ITEM:
        key, yes, no = YESNO_ITEM[column]
        old = [r.get("value") for r in items(d, key)]
        if value == "Yes":
            rows = items(d, key)
            if rows:
                rows[0]["value"] = yes; rows[0]["review_stage"] = STAGE
            else:
                set_all(d, key, yes)
        else:
            set_all(d, key, no)
            if key == "VI01":  # no ranking: the items that depend on a ranking do not apply
                for dep in ("VI02", "VI10", "VI11", "VI16"):
                    if items(d, dep):
                        set_all(d, dep, "NA")
    elif column in STATE_ITEM:
        old = [r.get("value") for r in items(d, STATE_ITEM[column])]
        set_all(d, STATE_ITEM[column], STATE[value])
    elif column == "Importance methods":
        old = [r.get("value") for r in items(d, "VI02")]
        set_all(d, "VI02", [IMPORTANCE[v] for v in split(value)])
    elif column == "Stability approach":
        old = c.E[sid]["importance_stability_methods"]
        c.E[sid]["importance_stability_methods"] = [STAB[v] for v in split(value)]
    elif column in VALIDATION:
        code = VALIDATION[column]
        rows = items(d, "VAL02")
        old = [r.get("value") for r in rows]
        if not rows:
            set_all(d, "VAL02", [])
            rows = items(d, "VAL02")
        for r in rows:
            v = r["value"] if isinstance(r["value"], list) else [r["value"]]
            v = [x for x in v if x != code and x != "NONE_NR"]
            r["value"] = v; r["review_stage"] = STAGE
        if value == "Yes":
            rows[0]["value"].append(code)
        for r in rows:
            if not r["value"]:
                r["value"] = ["NONE_NR"]
    elif column in TIMING:
        key, codes = TIMING[column]
        old = [r.get("value") for r in items(d, key)]
        set_all(d, key, codes[value])
        if column == "Supervised feature selection timing" and value == "Not reported":
            set_all(d, "PRE11", "NR")
    elif column == "Missing-value handling":
        old = [r.get("value") for r in items(d, "PRE01")]
        set_all(d, "PRE01", MISSING[value])
    elif column == "Survey years":
        old = [r.get("value") for r in items(d, "DAT04")]
        ys = [int(y) for y in split(value.replace("|", ";").replace(",", ";")) if y.isdigit()]
        set_all(d, "DAT04", ys or "NR")
    elif column == "Combining survey years":
        old = [r.get("value") for r in items(d, "DAT08")]
        set_all(d, "DAT08", {"One survey year": "ONE_YEAR", "Several years of one cycle": "MULTI_SAME", "Several cycles": "MULTI_CROSS",
                             "Unclear": "UNC"}[value])
    elif column == "Year":
        old = d["metadata"]["publication_year"]
        y = int(value)
        d["metadata"]["publication_year"] = y
        set_all(d, "BIB05", y)
        for rec in (c.P.get(sid), c.V.get(sid)):
            if rec:
                rec["publication_year"] = y
    elif column == "Variable domains":  # VI07: standardised domains of the most important variables
        rows = items(d, "VI07")
        old = [r.get("value") for r in rows]
        codes = [v.strip().upper().replace(" ", "_") for v in split(value)]
        for i, r in enumerate(rows or [None]):
            if r is None:
                set_all(d, "VI07", codes); break
            r["value"] = codes if i == 0 else []
            r["review_stage"] = STAGE
    elif column == "Most important variables as reported":
        rows = items(d, "VI06")
        old = [r.get("value") for r in rows]
        for i, r in enumerate(rows):
            r["value"] = value if i == 0 else "NA"
            r["review_stage"] = STAGE
    elif column == "Study group":
        cat, task, orient = GROUP[value]
        old = c.P[sid]["study_category"]
        for rec in (c.P[sid], d["adjudication"].get("study_category_and_dataset_use")):
            if rec is not None:
                rec["study_category"] = cat
                if task:
                    rec["knhanes_actual_ml_task"] = task
                if cat == "HEALTH_ANALYSIS":
                    rec["method_research_category"] = rec["method_evaluation_mode"] = "NOT_APPLICABLE"
                    rec["health_topic_role"] = "HEALTH_RESEARCH_TOPIC"
                    if rec.get("knhanes_position") == "APPLICATION_OR_TEST_DATASET":
                        rec["knhanes_position"] = "PRIMARY_ANALYSIS_DATASET"
                    rec["method_intervention_stages"] = ["NOT_APPLICABLE"]
                else:
                    rec["health_analysis_purpose"] = rec["purpose_component_combination"] = "NOT_APPLICABLE"
                    rec["health_topic_role"] = "METHOD_APPLICATION_EXAMPLE"
                    rec["knhanes_position"] = "APPLICATION_OR_TEST_DATASET"
        for rec in (c.V[sid], d["adjudication"].get("purpose_evidence_v1_3")):
            if rec is not None:
                rec["primary_orientation"] = orient
                rec["orientation_components"] = ["METHODOLOGICAL"] if orient == "METHOD_FOCUSED" else ["HEALTH_SUBSTANTIVE"]
                if orient == "METHOD_FOCUSED" and not rec.get("method_research"):
                    rec["method_research"] = {"target_analysis_stages": [], "comparators": [], "evaluation_datasets": [],
                                              "primary_evaluation_criteria": [], "evidence_ids": []}
        if value == "Core classification":
            set_all(d, "TSK01", "CLS")
    elif column == "Task":
        old = c.P[sid].get("method_research_category")
        if value in METHOD_TASK:
            cat, detail = METHOD_TASK[value]
            for rec in (c.P[sid], d["adjudication"].get("study_category_and_dataset_use")):
                if rec is not None:
                    rec["method_research_category"] = cat
            for rec in (c.V[sid], d["adjudication"].get("purpose_evidence_v1_3")):
                if rec is not None:
                    mr(rec).update(method_research_type_detailed=detail, method_research_type_figure4=cat)
        elif value == "Classification":
            set_all(d, "TSK01", "CLS")
    elif column == "Method workflow stages":
        old = None
        for rec in (c.V[sid], d["adjudication"].get("purpose_evidence_v1_3")):
            if rec is not None:
                mr(rec)["target_analysis_stages"] = [STAGES[v.lower()] for v in split(value)]
        for rec in (c.P[sid], d["adjudication"].get("study_category_and_dataset_use")):  # Supplementary Figure S1 reads these
            if rec is not None:
                rec["method_intervention_stages"] = [PURPOSE_STAGE[STAGES[v.lower()]] for v in split(value)]
    elif column == "Method evaluation design":
        old = None
        mode, pmode = EVAL[value.lower()]
        for rec in (c.V[sid], d["adjudication"].get("purpose_evidence_v1_3")):
            if rec is not None:
                mr(rec)["evaluation_mode"] = mode
        for rec in (c.P[sid], d["adjudication"].get("study_category_and_dataset_use")):
            if rec is not None:
                rec["method_evaluation_mode"] = pmode
    elif column == "Method comparators":
        old = None
        for rec in (c.V[sid], d["adjudication"].get("purpose_evidence_v1_3")):
            if rec is not None:
                mr(rec)["comparators"] = split(value)
    else:
        raise SystemExit(f"no handler for column {column!r} ({sid})")
    c.log(sid, column, old, value, basis, evidence)


def restore():
    if not PRISTINE.exists():
        import tarfile
        PRISTINE.mkdir(parents=True)
        with tarfile.open(REC / "before.tar.gz") as t:
            names = [m for m in t.getmembers() if m.name.startswith("data/protocol_v1_2/final/") or m.name in (
                "results/derived/expanded_model_task_audit.json", "results/derived/study_purpose_audit.json",
                "data/protocol_v1_3/purpose_evidence_addendum.json")]
            t.extractall(PRISTINE, members=names, filter="data")
    for p in (PRISTINE / "data/protocol_v1_2/final").glob("KHM*_final.json"):
        shutil.copyfile(p, FINAL / p.name)
    for rel in ("results/derived/expanded_model_task_audit.json", "results/derived/study_purpose_audit.json",
                "data/protocol_v1_3/purpose_evidence_addendum.json"):
        shutil.copyfile(PRISTINE / rel, ROOT / rel)


def main():
    restore()
    if "--restore-only" in sys.argv:
        print("restored")
        return
    c = Ctx()
    rows = list(csv.DictReader(TSV.open(encoding="utf-8"), delimiter="\t"))
    rows.sort(key=lambda r: r["column"] not in ("Study group", "Task"))  # group first: the method columns need it
    for r in rows:
        apply(c, r["study_id"], r["column"], r["value"].strip(), r["basis"], r.get("evidence", ""))
    c.save()
    print(json.dumps({"corrections": len(rows), "studies": len(c.touched)}))


if __name__ == "__main__":
    main()
