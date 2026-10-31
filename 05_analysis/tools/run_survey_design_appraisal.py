#!/usr/bin/env python3
"""Evidence-assisted primary KNHANES complex-survey appraisal.

This instrument is deliberately separate from PROBAST+AI. It distinguishes
reporting, applicability to the stated analytic target, and adherence. The
study-level TSV is generated from canonical JSON plus the retained full-report
text; the compact result is joined back into each canonical JSON record.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "data/study_json"
OUT = ROOT / "data/survey_design_appraisal/study_level_appraisal.tsv"
SUMMARY = ROOT / "results/derived/survey_design_appraisal.json"
ML = json.load(open(ROOT / "results/derived/ml_rationale.json", encoding="utf-8"))
ML_BY_ID = {x["key"]: x for x in ML["per_study"]}
with open(ROOT / "data/POOLING_OPERATION_AUDIT.tsv", encoding="utf-8-sig") as _f:
    POOL_BY_ID = {r["key"]: r for r in csv.DictReader(_f, delimiter="\t")}

FIELDS = (ROOT / "data/survey_design_appraisal/appraisal_template.tsv").read_text(encoding="utf-8").splitlines()[0].split("\t")

def yn(flag: bool) -> str:
    return "Yes" if flag else "No"

def text_for(d: dict) -> tuple[str, str]:
    source = d.get("source_document", {})
    candidates = []
    if isinstance(source, dict):
        for key in ("markdown_path", "text_path", "source_path"):
            if source.get(key): candidates.append(ROOT / source[key])
    candidates.append(ROOT / "references/md" / f"{d['study_id']}.md")
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore"), str(p.relative_to(ROOT))
    return "", ""

def snippet(text: str, patterns: list[str], width: int = 420) -> str:
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            start = max(0, text.rfind(".", 0, m.start()) + 1)
            end = text.find(".", m.end())
            if end < 0 or end - start > width: end = min(len(text), start + width)
            return re.sub(r"\s+", " ", text[start:end + 1]).strip()
    return ""

def value(a: dict, key: str, default: str = "") -> str:
    x = a.get(key, default)
    return str(x if x is not None else default)

def main() -> None:
    rows = []
    for path in sorted(JSON_DIR.glob("*.json")):
        d = json.load(open(path, encoding="utf-8")); sid = d["study_id"]
        if d.get("source_document", {}).get("availability") != "full_report":
            continue
        a = d["appendix15_fields"]; ml = ML_BY_ID.get(sid, {})
        text, source_path = text_for(d); low = text.lower()
        survey = value(a, "survey_weights", "언급 없음")
        weights_reported = survey != "언급 없음" or bool(re.search(r"sampling weight|survey weight|sample weight|weighted analysis|가중치", low))
        weights_used = survey in {"학습에 반영", "일부(기술통계·회귀만)"}
        # Canonical coding distinguishes survey weights from class/cost weights.
        # Requiring the curated category avoids false positives such as
        # "F1-weighted" and "class-weighted training".
        training_weight = survey == "학습에 반영"
        evaluation_weight = bool(re.search(
            r"(?:sample|survey)[- ]weighted (?:auc|auroc|accuracy|sensitivity|specificity|performance|evaluation)"
            r"|weighted (?:auc|auroc|accuracy|sensitivity|specificity|performance|evaluation)[^.]{0,100}(?:sample|survey) weight",
            low))
        if survey == "학습에 반영" and re.search(r"weighted (?:assessment|evaluation)", low):
            evaluation_weight = True
        strata_clusters_reported = bool(re.search(r"stratif(?:ied|ication)|primary sampling unit|\bpsu\b|cluster sampling|complex sample|복합표본|층화|집락", low))
        uncertainty_design = bool(re.search(r"survey(?: package| design)|svyglm|Taylor linear|jackknife|balanced repeated|replicate weight|strata[^.]{0,100}(?:cluster|psu)", text, re.I))
        cluster_resampling = bool(re.search(r"cluster[- ]aware|cluster bootstrap|resampl[^.]{0,100}(?:strata|psu|cluster)", low))
        years = value(a, "survey_years")
        year_tokens = set(re.findall(r"(?:19|20)\d{2}", years))
        pooled = len(year_tokens) > 1 or bool(re.search(r"–|-|~|to", years))
        pool = POOL_BY_ID.get(sid, {})
        integrated_reported = pool.get("combined_weight_reporting") == "Described"
        integrated_used = integrated_reported and bool(re.search(
            r"(?:wt_tot\s*/\s*12|integrated weight|통합가중치)[^.]{0,120}(?:appl|used|지정|적용)",
            low + " " + pool.get("weight_evidence", "").lower(), re.I))
        variance_reported = uncertainty_design or bool(re.search(r"variance estimat|standard error[^.]{0,80}(?:survey|weight)|95% confidence interval[^.]{0,80}(?:survey|weight)", low))
        subpop = bool(re.search(r"domain analysis|subpopulation|subpop|survey subset|nomcar", low))
        weighted_cal = bool(re.search(r"weighted calibration|survey-weighted calibration", low))
        weighted_disc = bool(re.search(r"weighted (?:auc|auroc|c-statistic)", low))
        weighted_class = bool(re.search(r"weighted (?:accuracy|sensitivity|specificity|precision|f1)", low))

        discussion = ml.get("discussion", {})
        factor_claim = "emphasizes_factor_or_association_insight" in discussion
        screen_claim = "proposes_screening_or_personalized_use" in discussion
        importance = value(a, "variable_importance") not in {"", "NR", "해당 없음", "미보고"}
        population_words = bool(re.search(r"Korean (?:adult|population|people|national)|general population|nationally representative|population-level|한국 (?:성인|국민|인구)", text, re.I))
        population_claim = population_words and (factor_claim or screen_claim or value(a, "type") == "Non-predictive")
        pop_importance = population_claim and importance and factor_claim
        pop_association = population_claim and factor_claim
        causal = bool(re.search(r"causal|determinant|protective effect|risk factor|influenc(?:e|ing)|cause|인과|결정요인", " ".join(discussion.values()), re.I))
        pop_performance = population_words and screen_claim
        prevalence_claim = bool(re.search(r"prevalence|유병률", " ".join(discussion.values()), re.I))
        external = "external_validation_or_transport" in ml.get("analytic_function", {})
        implemented = "implemented_decision_tool" in ml.get("analytic_function", {})
        calibration = bool(re.search(r"calibration|brier|hosmer", value(a, "reported_metrics_full"), re.I))
        ci = bool(re.search(r"confidence interval|95% ci|bootstrap", value(a, "reported_metrics_full") + " " + value(a, "evaluation"), re.I))
        threshold = value(a, "threshold", "Not reported")

        typ = value(a, "type")
        if pop_importance: role = "population_variable_importance_or_association"
        elif pop_association: role = "population_association"
        elif screen_claim: role = "clinical_screening_or_prediction"
        elif typ in {"Classification", "Regression"}: role = "sample_conditional_prediction"
        else: role = "structural_or_data_analytic"
        estimand = ("population association/importance" if population_claim else
                    "sample-conditional predictive or analytic quantity")
        target = "Korean/KNHANES target population" if population_claim else "analysed sample; broader target not explicit"
        if population_claim:
            applicability = "Required for population interpretation"
            if training_weight and (not pooled or integrated_used) and strata_clusters_reported and uncertainty_design:
                adherence = "Adequate"
            elif weights_used or strata_clusters_reported:
                adherence = "Partial"
            else:
                adherence = "Inadequate"
        elif role == "clinical_screening_or_prediction":
            applicability = "Conditional on intended-use population"
            adherence = "Partial" if weights_used else "Unclear"
        else:
            applicability = "Not required for sample-conditional fitting; required for population claims"
            adherence = "Not applicable" if not population_words else "Unclear"

        ev = snippet(text, [r"sampling weight|survey weight|weighted analysis|complex sample|stratif(?:ied|ication)|primary sampling unit|\bpsu\b|cluster sampling|복합표본|가중치"])
        rationale = (f"Canonical survey_weights={survey}. Analytic role={role}. "
                     f"Population interpretation={'present' if population_claim else 'not explicit'}. "
                     "Training and evaluation weighting were judged separately; nonuse was not automatically penalised for a sample-conditional target.")
        row = {k: "Not reported" for k in FIELDS}
        row.update({
            "study_id": sid, "model_id": "study-level primary analytic pipeline", "analytic_role": role,
            "estimand": estimand, "target_population": target, "intended_clinical_use": yn(screen_claim),
            "clinical_setting": "Not reported", "intended_user": "Not reported", "moment_of_use": value(a, "original_task_label", "Unclear"),
            "population_prevalence_claim": yn(prevalence_claim), "population_effect_or_association_claim": yn(pop_association),
            "population_variable_importance_claim": yn(pop_importance), "population_performance_claim": yn(pop_performance),
            "causal_language_used": yn(causal), "weights_reported": yn(weights_reported),
            "weight_type_appropriate": "Yes" if weights_used else ("No" if population_claim and not weights_used else "Not applicable/unclear"),
            "weights_used_in_training": yn(training_weight), "weights_used_in_evaluation": yn(evaluation_weight),
            "weight_nonuse_justified": yn(bool(re.search(r"unweighted|weight[^.]{0,80}not (?:used|applied)|sample-conditional", low))),
            "strata_clusters_reported": yn(strata_clusters_reported), "strata_clusters_used_in_uncertainty": yn(uncertainty_design),
            "cluster_aware_resampling": yn(cluster_resampling), "pooled_cycles": yn(pooled),
            "integrated_weights_reported": yn(integrated_reported), "integrated_weights_used": yn(integrated_used),
            "variance_method_reported": yn(variance_reported), "subpopulation_design_handled": yn(subpop),
            "weighted_discrimination": yn(weighted_disc), "weighted_classification_metrics": yn(weighted_class),
            "weighted_calibration": yn(weighted_cal), "performance_ci_reported": yn(ci),
            "population_prevalence_in_threshold_metrics": "Yes" if evaluation_weight else "Not reported",
            "importance_interpretation_level": "population_predictive/effect" if pop_importance else "sample_predictive",
            "performance_interpretation_level": "population_performance" if pop_performance else "sample_internal",
            "external_or_temporal_validation": yn(external), "clinical_calibration": yn(calibration),
            "threshold_rationale": threshold, "clinical_utility": yn(bool(re.search(r"decision curve|net benefit|clinical utility", low))),
            "predictor_availability_at_use": "Not reported", "implementation_and_monitoring": yn(implemented),
            "fairness_evaluation": yn(bool(re.search(r"fairness|algorithmic bias|equalized odds|demographic parity", low))),
            "population_claim": yn(population_claim), "applicability": applicability,
            "methodological_adherence": adherence, "evidence_page": source_path,
            "evidence_quote": ev, "rationale": rationale, "reviewer": "Codex evidence-assisted primary review",
            "date": str(date.today()),
        })
        rows.append(row)
        compact = {k: row[k] for k in ("analytic_role", "estimand", "target_population", "population_claim",
                   "weights_reported", "weights_used_in_training", "weights_used_in_evaluation",
                   "strata_clusters_reported", "strata_clusters_used_in_uncertainty", "pooled_cycles",
                   "integrated_weights_reported", "integrated_weights_used", "applicability",
                   "methodological_adherence", "evidence_page", "evidence_quote", "rationale")}
        d["analysis"]["complex_survey_appraisal"] = compact
        d["appendix15_fields"]["survey_applicability"] = applicability
        d["appendix15_fields"]["survey_methodological_adherence"] = adherence
        d["appendix15_fields"]["survey_appraisal_evidence"] = ev or "No explicit design-method statement located in retained report text"
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    summary = {
        "n_studies": len(rows), "review_status": "evidence-assisted primary review; independent duplicate review pending",
        "analytic_role": Counter(r["analytic_role"] for r in rows),
        "applicability": Counter(r["applicability"] for r in rows),
        "methodological_adherence": Counter(r["methodological_adherence"] for r in rows),
        "design_reporting": {k: sum(r[k] == "Yes" for r in rows) for k in (
            "weights_reported", "weights_used_in_training", "weights_used_in_evaluation",
            "strata_clusters_reported", "strata_clusters_used_in_uncertainty",
            "integrated_weights_reported", "integrated_weights_used")},
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
