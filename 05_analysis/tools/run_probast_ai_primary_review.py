#!/usr/bin/env python3
"""Evidence-assisted primary PROBAST+AI review of the active prediction-model cohort.

The unit of interest is each report's final/index model.  Development quality and
each distinct internal versus external/temporal evaluation are separate units.
This script never imports legacy PROBAST answers or judgements.  It records
conservative NI/PN responses when the structured full-text extraction does not
support a definitive response.  All units are labelled as a Codex primary review
and require independent human verification before submission.
"""
from __future__ import annotations

import csv
import glob
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path

from analyze_extraction import metric_depth, posthoc, validation
from probast_ai_reassessment import phase_template

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data/probast_ai_reassessment/records"
TODAY = date.today().isoformat()
REVIEWER = "codex_primary_evidence_review"


def text(d, *fields):
    return " ".join(str(d.get(k) or "") for k in fields)


def has(s, pattern):
    return bool(re.search(pattern, s, re.I))


def clip(value, n=420):
    s = re.sub(r"\s+", " ", str(value or "")).strip()
    return s[:n] + ("…" if len(s) > n else "")


def task_timing(d):
    """Classify the index target, not prognostic language in the discussion.

    Most KNHANES models classify an outcome measured at the same survey visit.
    A future target therefore requires explicit ordering in the model description;
    generic words such as risk, incidence, future work, or mortality background do
    not suffice.  Abstract-only records without an operational target remain unclear.
    """
    core = text(d, "problem", "ml_usage")
    if d.get("key") == "jo2023development":
        return "prognostic_future"
    explicit_future = (
        r"(?:predict|예측).{0,80}(?:subsequent|next[- ]day|during follow[- ]?up|time[- ]to[- ]event|"
        r"향후|추적.*발생|다음 날)|(?:baseline|기준시점).{0,100}(?:mortality|death|incident|사망|발생)"
    )
    if has(core, explicit_future):
        return "prognostic_future"
    if d.get("source") == "abstract_only":
        return "unclear"
    if (has(core, r"prevalen|cross[- ]?section|current state|diagnos|screen|유병|단면|횡단|진단|분류")
            or "KNHANES" in core or "국민건강영양조사" in core):
        return "diagnostic_current"
    return "unclear"


def formal_calibration(d):
    combined = text(d, "metrics", "validation", "findings", "notes")
    return (metric_depth(d.get("metrics")) == "판별력 + 보정" or
            "보정 평가" in posthoc(combined))


def evaluation_types(d):
    val = validation(d.get("validation"))
    raw = text(d, "validation", "other_datasets", "knhanes_waves")
    out = []
    if "단일 분할" in val or "교차검증" in val:
        out.append(("internal", "internal_validation"))
    if "외부검증" in val:
        if d.get("knhanes_role") == "external_validation" or has(raw, r"NHANES|clinical|hospital|cohort|claims|보험|병원|코호트"):
            out.append(("external", "external_validation"))
        else:
            out.append(("temporal", "temporal_validation"))
    if not out:
        out.append(("apparent", "apparent_or_unreported"))
    # retain one unit per distinct evaluation type
    seen = set()
    return [x for x in out if not (x[0] in seen or seen.add(x[0]))]


def leakage_signal(d):
    t = text(d, "problem", "variables", "notes")
    # Outcome components used as predictors create incorporation/availability concerns.
    patterns = [
        (r"hypertension|고혈압", r"systolic|diastolic|blood pressure|수축기|이완기|혈압"),
        (r"diabet|당뇨", r"fasting glucose|hba1c|blood sugar|공복혈당|당화혈색소"),
        (r"metabolic syndrome|대사증후군", r"waist|triglycer|hdl|blood pressure|glucose|허리|중성지방|혈압|혈당"),
        (r"obes|비만", r"\bbmi\b|waist|body mass|체질량|허리둘레"),
    ]
    return any(has(t, outcome) and has(t, predictor) for outcome, predictor in patterns)


def evidence(d, field, rationale):
    return {"location": f"structured full-report extraction: {field}",
            "quote": clip(d.get(field)), "rationale": rationale}


def domain_judgement(answers, domain, phase):
    """Operational primary judgement, not a mechanical N-to-high conversion.

    PROBAST+AI explicitly requires assessor judgement after signalling questions.
    Here, high concern is reserved for prespecified critical failures that directly
    compromise development quality or performance evaluation.  PN/NI remains
    unclear.  Every judgement remains subject to independent human consensus.
    """
    critical = {
        "development": {"D2.3", "D2.4", "D3.3", "D4.4", "D4.5"},
        "evaluation": {"D2.3", "D2.4", "D3.3", "D4.1", "D4.4", "D4.5", "D4.6", "D4.7"},
    }[phase]
    qs = {q: v for q, v in answers.items() if q.startswith(domain + ".")}
    if any(v == "N" and q in critical for q, v in qs.items()):
        return "high"
    if any(v in ("N", "NI", "PN") for v in qs.values()):
        return "unclear"
    return "low"


def complete_unit(unit, answers, ev, rationale, applicability, phase):
    unit["status"] = "complete"
    unit["questions"].update(answers)
    unit["domains"] = {d: domain_judgement(answers, d, phase) for d in ("D1", "D2", "D3", "D4")}
    unit["overall_judgement"] = ("high" if "high" in unit["domains"].values() else
                                  "unclear" if "unclear" in unit["domains"].values() else "low")
    unit["applicability"] = applicability
    unit["evidence"] = ev
    unit["judgement_rationale"] = rationale
    unit["reviewer"] = REVIEWER
    unit["assessment_date"] = TODAY
    return unit


def common_answers(d, timing):
    source = d.get("source")
    full = source == "full_text"
    sample = text(d, "sample_filtering")
    variables = text(d, "variables")
    prep = text(d, "preprocessing", "missing_handling")
    problem = text(d, "problem")
    leakage = leakage_signal(d)
    ans = {
        "D1.1": "PY" if full else "NI",
        "D1.2": "Y" if timing == "diagnostic_current" else "PY" if timing == "prognostic_future" else "NI",
        "D1.3": "PY" if sample and not has(sample, r"미기재|unclear|not reported") else "NI",
        "D2.1": "PY" if variables and not has(variables, r"미기재|not reported") else "NI",
        "D2.2": "PY" if prep and not has(prep, r"미기재|not reported") else "NI",
        "D2.3": "N" if leakage else "PY" if full else "NI",
        "D2.4": "N" if leakage else "PY" if timing == "diagnostic_current" and variables else "NI",
        "D3.1": "PY" if problem and not has(problem, r"미기재|unclear") else "NI",
        "D3.2": "PY" if problem and full else "NI",
        "D3.3": "N" if leakage else "PY" if full else "NI",
        "D3.4": "Y" if timing in ("diagnostic_current", "prognostic_future") else "NI",
    }
    ev = {
        "D1.1": evidence(d, "knhanes_role", "Data-source role was assessed against the index-model purpose."),
        "D1.2": evidence(d, "ml_usage", f"Design was judged for a {timing} target; cross-sectional data were not automatically penalised for current-state classification."),
        "D1.3": evidence(d, "sample_filtering", "Eligibility and exclusions had to support a representative analysis set for the stated target."),
        "D2.1": evidence(d, "variables", "Predictor definition and consistency were judged from the reported candidate set."),
        "D2.2": evidence(d, "preprocessing", "A blank or unreported preprocessing sequence was coded NI."),
        "D2.3": evidence(d, "notes", "Possible incorporation of outcome-defining measurements was treated as a critical concern."),
        "D2.4": evidence(d, "variables", "Availability was judged at the intended use, not merely at retrospective analysis."),
        "D3.1": evidence(d, "problem", "Outcome definition and ascertainment were judged from the operational target."),
        "D3.2": evidence(d, "problem", "Consistency required a common reported outcome rule."),
        "D3.3": evidence(d, "notes", "Outcome assessment using predictor components was treated as incorporation concern."),
        "D3.4": evidence(d, "problem", f"Predictor-to-outcome timing classified as {timing}."),
    }
    return ans, ev


def development_unit(d, timing):
    ans, ev = common_answers(d, timing)
    n = d.get("n_final") if isinstance(d.get("n_final"), (int, float)) else None
    missing = text(d, "missing_handling")
    prep = text(d, "preprocessing")
    tuning = text(d, "hyperparameter_tuning", "validation")
    imbalance = has(prep, r"smote|adasyn|undersampl|oversampl|class weight|cost-sensitive|불균형|언더샘플|오버샘플")
    calibrated = formal_calibration(d)
    ans.update({
        "D4.1": "PN" if n and n < 1000 else "NI",
        "D4.2": "PY" if has(prep, r"standard|normaliz|scal|one.?hot|encoding|표준|정규|인코딩") else "NI",
        "D4.3": "PN" if has(missing, r"complete case|완전제거|listwise|simple|mean|median|단순") else "PY" if has(missing, r"multiple imputation|mice|다중대체") else "NI",
        "D4.4": "Y" if imbalance and calibrated else "N" if imbalance else "NA",
        "D4.5": "Y" if has(tuning, r"nested|외부검증|external valid") else "PY" if has(tuning, r"cross.?validation|교차검증|bootstrap") else "PN" if has(tuning, r"split|분할") else "N",
    })
    ev.update({
        "D4.1": evidence(d, "n_final", "Without recoverable event and candidate-predictor information, a large nominal n alone was coded NI."),
        "D4.2": evidence(d, "preprocessing", "Continuous/categorical predictor handling required an explicit method."),
        "D4.3": evidence(d, "missing_handling", "Complete-case or simple imputation was treated as a potential concern; MI as probably appropriate."),
        "D4.4": evidence(d, "preprocessing", "When imbalance correction was used, evidence of recalibration was required."),
        "D4.5": evidence(d, "validation", "Resampling/external evaluation informed the judgement about optimism control."),
    })
    app = applicability(d, timing, ans)
    rationale = "Primary index-model development assessment. Critical N responses produce a high domain; unresolved NI/PN responses produce unclear concern. Nominal sample size was not accepted as evidence of adequate effective information without events and predictor dimension."
    return complete_unit(phase_template("development"), ans, ev, rationale, app, "development")


def evaluation_unit(d, timing, eval_type, assessment_id):
    ans, ev = common_answers(d, timing)
    val = text(d, "validation", "preprocessing", "notes")
    metrics = text(d, "metrics", "validation")
    missing = text(d, "missing_handling")
    imbalance = has(text(d, "preprocessing"), r"smote|adasyn|undersampl|oversampl|class weight|cost-sensitive|언더샘플|오버샘플")
    natural = has(val, r"train(?:ing)? only|within (?:each )?(?:fold|training)|학습.*내|fold.*내|원래.*분포|natural.*distribution")
    split = has(val, r"split|분할|hold.?out|train.{0,8}test")
    resampling = has(val, r"cross.?validation|교차검증|bootstrap|부트스트랩")
    leakage_avoided = has(val, r"before.*split") is False and has(val, r"within (?:each )?(?:fold|training)|학습.*내|patient.?level|participant.?level|대상자.*단위")
    depth = metric_depth(d.get("metrics"))
    ans.update({
        "D4.1": "N" if eval_type == "apparent" else "Y",
        "D4.2": "PN" if isinstance(d.get("n_final"), (int, float)) and d["n_final"] < 1000 else "NI",
        "D4.3": "PN" if has(missing, r"complete case|완전제거|simple|mean|median|단순") else "PY" if has(missing, r"multiple imputation|mice|다중대체") else "NI",
        "D4.4": "Y" if imbalance and natural else "NI" if imbalance else "NA",
        "D4.5": "Y" if split and leakage_avoided else "PN" if split else "NA",
        "D4.6": "Y" if resampling and has(val, r"within (?:each )?(?:fold|training)|학습.*내|nested") else "NI" if resampling else "NA",
        "D4.7": "Y" if formal_calibration(d) or has(metrics, r"decision curve|net benefit|결정 ?곡선|순편익") else "PY" if depth.startswith("판별력") else "PN" if depth == "정확도 중심" else "N",
    })
    ev.update({
        "D4.1": evidence(d, "validation", f"Primary evaluation classified as {eval_type}."),
        "D4.2": evidence(d, "sample_filtering", "Evaluation n and outcome events were required for a definitive adequacy judgement."),
        "D4.3": evidence(d, "missing_handling", "Handling had to be appropriate in the evaluation data."),
        "D4.4": evidence(d, "preprocessing", "Corrected training data were acceptable only when evaluation retained the natural outcome distribution."),
        "D4.5": evidence(d, "notes", "Split-sample leakage safeguards were judged from explicit ordering or participant-level separation."),
        "D4.6": evidence(d, "hyperparameter_tuning", "All development steps had to be repeated within resampling; otherwise NI."),
        "D4.7": evidence(d, "metrics", "Appropriateness considered discrimination, calibration, and utility for intended use."),
    })
    unit = phase_template("evaluation")
    unit["assessment_id"] = assessment_id
    unit["performance_evaluation_type"] = eval_type
    rationale = "Primary index-model evaluation assessment. Internal and external/temporal evaluations were separated. Absence of explicit leakage, effective-sample-size, or within-resampling workflow evidence was coded conservatively as PN or NI rather than inferred."
    return complete_unit(unit, ans, ev, rationale, applicability(d, timing, ans), "evaluation")


def applicability(d, timing, answers):
    d1 = "low" if d.get("knhanes_role") in ("primary", "one_of_several", "external_validation") else "unclear"
    d2 = "high" if answers.get("D2.4") == "N" else "unclear" if answers.get("D2.4") in ("NI", "PN") else "low"
    d3 = "unclear" if timing == "unclear" else "high" if answers.get("D3.3") == "N" else "low"
    overall = "high" if "high" in (d1, d2, d3) else "unclear" if "unclear" in (d1, d2, d3) else "low"
    return {"D1": d1, "D2": d2, "D3": d3, "overall": overall}


def main():
    refs = {r["key"]: r for r in json.load(open(ROOT / "references/refs.json"))}
    rationale = json.load(open(ROOT / "results/derived/ml_rationale.json"))
    implemented = {r["key"] for r in rationale["per_study"]
                   if "implemented_decision_tool" in r.get("analytic_function", {})}
    studies = []
    for p in glob.glob(str(ROOT / "data/extraction/*.json")):
        d = json.load(open(p))
        if refs.get(d.get("key"), {}).get("verdict") == "INCLUDE" and d.get("task") in ("classification", "regression"):
            studies.append(d)
    timing_rows = []
    for d in sorted(studies, key=lambda x: x["key"]):
        p = RECORDS / f"{d['key']}.json"
        rec = json.load(open(p))
        timing = task_timing(d)
        evals = evaluation_types(d)
        model_name = clip(d.get("best_model") or (d.get("models") or ["Reported index model"])[0], 240)
        model = {"model_id": "index_model", "model_name": model_name, "selection_rule": "Final/best model reported by the study; comparator-only algorithms were not separate review units.", "evaluations": []}
        if d.get("knhanes_role") != "external_validation":
            model["development"] = development_unit(d, timing)
        for eval_type, aid in evals:
            model["evaluations"].append(evaluation_unit(d, timing, eval_type, aid))
        rec.update({
            "source": d.get("source"), "task": d.get("task"), "task_timing": timing,
            "intended_use": clip(d.get("findings") or d.get("ml_usage"), 600),
            "target_population": clip(d.get("sample_filtering"), 600),
            "outcome": clip(d.get("problem"), 600), "scope_status": "complete",
            "scope_rationale": "Index/final model assessed; comparator-only algorithms excluded. Separate internal and external/temporal evaluation units retained.",
            "models": [model], "primary_review_requires_independent_verification": True,
        })
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        flags = {t for t, _ in evals}
        timing_rows.append({
            "study_id": d["key"], "analytic_target": timing,
            "predictors_available_before_or_independently_of_outcome": "N" if leakage_signal(d) else "PY" if timing == "diagnostic_current" else "NI",
            "external_or_temporal_validation": "Y" if flags & {"external", "temporal"} else "N",
            "calibration": "Y" if formal_calibration(d) else "N",
            "implementation": "Y" if d["key"] in implemented else "N",
            "evidence_page": "structured extraction fields", "evidence_quote": clip(d.get("problem"), 300),
            "reviewer": REVIEWER, "second_reviewer": "", "consensus": "", "date": TODAY,
        })
    out = ROOT / "data/outcome_timing_appraisal.tsv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(timing_rows[0]), delimiter="\t")
        w.writeheader(); w.writerows(timing_rows)
    print(f"completed primary review for {len(studies)} studies")
    print(f"outcome-timing rows: {len(timing_rows)}")


if __name__ == "__main__":
    main()
