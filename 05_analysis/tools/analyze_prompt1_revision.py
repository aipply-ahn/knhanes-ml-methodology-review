"""Derive the audit requested in 프롬프트1.txt from structured study records.

Metric indicators are deliberately non-mutually-exclusive.  Outcome timing is not
inferred from prose: the script creates a blank human-review registry instead.
"""
import csv
import glob
import json
import math
import re
from pathlib import Path

import numpy as np

from analyze_extraction import canon_model, metric_depth, posthoc, validation, weights
from canonical_data import included_extractions

ROOT = Path(__file__).resolve().parents[1]


def flag(text, pattern):
    return bool(re.search(pattern, text, re.I))


def metric_flags(d):
    t = " ".join(str(d.get(k) or "") for k in
                 ("metrics", "validation", "findings", "interpretability", "notes"))
    # AUPRC is tested separately so its substring does not create an AUROC hit.
    auprc = flag(t, r"auprc|pr[- ]?auc|precision[- ]recall(?:\s+(?:auc|curve))")
    auroc = flag(t, r"auroc|roc[- ]?auc|area under (?:the )?(?:roc|receiver)|(?<!pr[- ])\bauc\b")
    any_calibration = (metric_depth(d.get("metrics")) == "판별력 + 보정" or
                       "보정 평가" in posthoc(t))
    return {
        "AUROC": auroc,
        "AUPRC": auprc,
        "Accuracy": flag(t, r"\bacc(?:uracy)?\b|정확도"),
        "Sensitivity/recall": flag(t, r"sensitiv|\brecall\b|민감도"),
        "Specificity": flag(t, r"specificit|\bspec\b|특이도"),
        "Precision/PPV": flag(t, r"\bprecision\b|\bppv\b|양성예측"),
        "F1": flag(t, r"\bf1(?:[- ]?score)?\b"),
        "Calibration plot": flag(t, r"calibration (?:plot|curve)|보정 ?곡선"),
        "Calibration intercept": flag(t, r"calibration intercept|보정 ?절편"),
        "Calibration slope": flag(t, r"calibration slope|보정 ?기울기"),
        "Brier score": flag(t, r"brier"),
        "Hosmer--Lemeshow": flag(t, r"hosmer|lemeshow"),
        "Any calibration assessment": any_calibration,
        "Decision curve/net benefit": flag(t, r"decision curve|\bdca\b|net benefit|결정 ?곡선|순편익"),
        "Confidence interval": flag(t, r"95\s*%?\s*ci|confidence interval|신뢰구간|\(0\.\d+[–-]0\.\d+\)"),
        "Repeated resampling": flag(t, r"repeated .{0,12}(?:cross[- ]?validation|resampl)|\d+회 반복|bootstrap|부트스트랩"),
        "Paired/DeLong/bootstrap comparison": flag(t, r"delong|mcnemar|paired (?:test|t[- ]?test)|paired bootstrap|bootstrap difference|대응.*검정"),
    }


def logistic_or(years, outcomes):
    """Univariable logistic regression by IRLS; returns OR/year and Wald CI."""
    x = np.asarray(years, dtype=float) - 2020.0
    y = np.asarray(outcomes, dtype=float)
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(2)
    for _ in range(100):
        eta = np.clip(X @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        w = np.maximum(p * (1 - p), 1e-9)
        info = X.T @ (w[:, None] * X)
        step = np.linalg.solve(info, X.T @ (y - p))
        beta += step
        if np.max(np.abs(step)) < 1e-10:
            break
    cov = np.linalg.inv(info)
    se = math.sqrt(cov[1, 1])
    return {"events": int(y.sum()), "n": len(y), "or_per_year": math.exp(beta[1]),
            "ci95_low": math.exp(beta[1] - 1.96 * se),
            "ci95_high": math.exp(beta[1] + 1.96 * se)}


def main():
    refs = {r["key"]: r for r in json.load(open(ROOT / "references/refs.json"))}
    ext = included_extractions()
    pred = [d for d in ext if d.get("task") == "classification"]

    indicators = {k: 0 for k in metric_flags(pred[0])}
    per_study = {}
    for d in pred:
        f = metric_flags(d)
        per_study[d["key"]] = f
        for k, v in f.items():
            indicators[k] += int(v)

    model_eval, model_best = {}, {}
    for d in pred:
        for m in set(filter(None, (canon_model(x) for x in d.get("models", [])))):
            model_eval[m] = model_eval.get(m, 0) + 1
        b = canon_model(d.get("best_model"))
        if b:
            model_best[b] = model_best.get(b, 0) + 1
    selection = []
    for m, n in sorted(model_eval.items(), key=lambda z: (-z[1], z[0])):
        b = model_best.get(m, 0)
        selection.append({"model": m, "evaluated": n, "reported_best": b,
                          "selection_rate_pct": 100 * b / n})

    rationale = json.load(open(ROOT / "results/derived/ml_rationale.json"))
    rows = {r["key"]: r for r in rationale["per_study"]}
    screen = [r for r in rows.values() if "proposes_screening_or_personalized_use" in r.get("discussion", {})]
    factor = [r for r in rows.values() if "emphasizes_factor_or_association_insight" in r.get("discussion", {})]
    claim_evidence = {
        "screening_or_personalisation_claims": len(screen),
        "with_external_or_temporal_validation": sum(
            "external_validation_or_transport" in r.get("analytic_function", {}) for r in screen),
        "with_implemented_tool": sum("implemented_decision_tool" in r.get("analytic_function", {}) for r in screen),
        "with_prospective_deployment": 0,
        "factor_or_association_claims": len(factor),
        "with_noncausal_caveat": sum(
            "acknowledges_cross_sectional_noncausal_limit" in r.get("discussion", {}) for r in factor),
    }

    pathway = {r["key"]: r for r in json.load(open(ROOT / "results/derived/importance_pathway.json"))["studies"]}
    trends = {}
    tripod_rows = {r["key"]: r for r in csv.DictReader(
        open(ROOT / "data/backdata/03_tripod_items.tsv", encoding="utf-8-sig"), delimiter="\t")}
    trend_defs = {
        "Variable importance as final output": lambda d: bool(pathway.get(d["key"], {}).get("explicit_importance_method")) and not bool(pathway.get(d["key"], {}).get("importance_guided_inference")),
        "SHAP": lambda d: flag(pathway.get(d["key"], {}).get("importance_methods", ""), r"shap|shapley"),
        "External/temporal validation": lambda d: "외부검증" in validation(d.get("validation")),
        "Any calibration assessment": lambda d: metric_flags(d)["Any calibration assessment"],
        "Code available": lambda d: tripod_rows.get(d["key"], {}).get("code_availability") == "Y",
        "Survey-weight reporting": lambda d: weights(d.get("survey_weights")) != "언급 없음",
    }
    for name, fn in trend_defs.items():
        # Temporal evidence-support comparisons use one fixed cohort so changes in
        # task composition cannot create denominator artefacts.
        cohort = pred
        years = [int(refs[d["key"]]["year"]) for d in cohort]
        trends[name] = logistic_or(years, [fn(d) for d in cohort])

    out = {"definitions": {"performance_metrics": f"Non-mutually-exclusive text indicators across {len(pred)} predictive-model records.",
                            "selection_rate": "Studies reporting a model as best divided by studies evaluating that model; heterogeneous criteria and ties preclude an intrinsic ranking.",
                            "trend": "Univariable logistic regression with publication year as a continuous predictor; Wald 95% CI."},
           "metric_counts": indicators, "model_selection": selection,
           "claim_evidence": claim_evidence, "temporal_logistic": trends,
           "per_study_metric_flags": per_study}
    (ROOT / "results/derived/prompt1_revision.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n")

    registry = ROOT / "data/outcome_timing_appraisal.tsv"
    fields = ["study_id", "analytic_target", "predictors_available_before_or_independently_of_outcome",
              "external_or_temporal_validation", "calibration", "implementation", "evidence_page",
              "evidence_quote", "reviewer", "second_reviewer", "consensus", "date"]
    existing = {}
    if registry.exists():
        with open(registry, encoding="utf-8-sig") as f:
            existing = {r["study_id"]: r for r in csv.DictReader(f, delimiter="\t")}
    with open(registry, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for d in sorted(pred, key=lambda z: z["key"]):
            w.writerow({k: existing.get(d["key"], {}).get(k, "") for k in fields} | {"study_id": d["key"]})
    print(ROOT / "results/derived/prompt1_revision.json")
    print(registry)


if __name__ == "__main__":
    main()
