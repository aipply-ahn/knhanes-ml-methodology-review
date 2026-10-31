"""Content analysis of why ML was used, what it did, and how authors interpreted it.

Introduction and Discussion coding is limited to locally available full reports.
Actual analytic function is coded for every included study from the structured
extraction. Categories are non-exclusive and every match retains a source excerpt
for audit.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from analyze_extraction import validation as validation_codes, importance_kind

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "references"
EXT = ROOT / "data" / "extraction"
OUT = ROOT / "results" / "derived"

JUSTIFICATION = {
    "clinical_screening_or_personalization": r"early (?:detection|identification|screening)|screening tool|clinical decision|personalized|tailored (?:care|intervention|management)|preventive intervention|고위험군|조기 (?:발견|식별)|맞춤형",
    "complexity_nonlinearity_high_dimension": r"complex (?:relationship|interaction|pattern|data)|nonlinear|non-linear|high[- ]dimensional|large number of variables|hidden pattern|복잡한 (?:관계|상호작용)|비선형|고차원",
    "performance_beyond_conventional_methods": r"traditional|conventional|statistical model.{0,80}limit|logistic regression.{0,80}limit|improv.{0,50}(?:accuracy|performance|prediction)|outperform|예측 (?:정확도|성능).{0,40}(?:향상|개선)|전통적|기존 (?:통계|방법).{0,50}한계",
    "factor_discovery_or_interpretability": r"identify (?:important|key|major|risk) (?:factor|predictor|feature)|feature importance|interpret(?:ability|able)|explainable|risk factor identification|영향요인|위험요인|변수 중요도|설명 가능한",
    "methodological_or_data_problem": r"class imbalance|missing data|imputation|feature selection|dimensionality reduction|synthetic data|algorithm comparison|불균형|결측|대체|특징 선택|차원 축소|합성데이터|알고리즘 비교",
    "dynamic_or_deployed_prediction": r"real[- ]time|continuous monitoring|streaming|prospective alert|alarm system|deployed|deployment|electronic health record|manufacturing|실시간|지속적 모니터링|경보|배포",
}

DISCUSSION = {
    "claims_better_prediction": r"outperform|superior performance|improved (?:accuracy|performance|prediction)|highest (?:auc|accuracy)|우수한 (?:성능|예측)|성능이 (?:향상|개선)|가장 높은",
    "emphasizes_factor_or_association_insight": r"important (?:factor|predictor|feature)|key (?:factor|predictor|feature)|associated with|feature importance|영향요인|위험요인|관련 요인|변수 중요도",
    "proposes_screening_or_personalized_use": r"screening tool|clinical practice|clinical decision|personalized|tailored (?:care|intervention|management)|early (?:detection|identification)|고위험군 (?:선별|식별)|임상 (?:활용|적용)|맞춤형|조기 (?:발견|식별)",
    "reports_implemented_tool_or_deployment": r"(?:we )?deployed .{0,100}(?:system|application|electronic health record)|integrated (?:into|with) (?:an? )?electronic health record|(?:web[- ]based |online )?(?:application|tool|calculator) (?:was|is|has been) (?:developed|implemented|available)|smartphone application (?:was|is|has been) developed|calculator (?:worked|is available) .{0,80}(?:browser|http)|실제로 (?:구현|배포)|웹 (?:도구|애플리케이션).{0,30}(?:구현|개발)",
    "acknowledges_cross_sectional_noncausal_limit": r"cross[- ]sectional.{0,120}(?:caus|temporal|direction)|cannot (?:establish|infer|determine) caus|causal relationship cannot|인과.{0,40}(?:확인|추론|해석).{0,20}(?:없|어렵)|단면.{0,80}인과",
    "calls_for_external_validation_or_calibration": r"external validation|prospective validation|independent (?:cohort|dataset).{0,50}valid|calibration.{0,40}(?:needed|required|future)|외부 검증|전향적 검증|보정.{0,30}필요",
    "acknowledges_survey_design_limit": r"survey weight|sampling weight|complex survey|survey stratification|stratified (?:multistage |cluster )?sampling|cluster sampling|복합표본|표본 가중치|층화.{0,20}집락",
}


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def clean(text): return re.sub(r"\s+", " ", text or "").strip()


def section(text, starts, ends, fallback):
    lines = text.splitlines()
    begin = None
    for i, line in enumerate(lines):
        if re.fullmatch(starts, line.strip(), re.I): begin = i + 1; break
    if begin is not None:
        stop = len(lines)
        for j in range(begin, len(lines)):
            if re.fullmatch(ends, lines[j].strip(), re.I): stop = j; break
        return "\n".join(lines[begin:stop])
    return text[fallback[0]:fallback[1]]


def evidence(text, pattern):
    for sent in re.split(r"(?<=[.!?])\s+|\n+", clean(text)):
        if re.search(pattern, sent, re.I): return sent[:420]
    return ""


def code_patterns(text, patterns):
    return {key: evidence(text, pat) for key, pat in patterns.items() if re.search(pat, text, re.I | re.S)}


def actual_functions(e, full):
    out = {}
    task = e.get("task") or ""
    if task in {"classification", "regression"}: out["prediction_or_classification"] = e.get("problem") or task
    if len(e.get("models") or []) >= 2: out["algorithm_comparison"] = ", ".join((e.get("models") or [])[:8])
    interp = str(e.get("interpretability") or "")
    ik = importance_kind(interp)
    if ik not in (["없음"], ["기타"]): out["feature_or_risk_factor_interpretation"] = interp[:420]
    if task in {"clustering", "feature_selection"}: out["pattern_or_feature_discovery"] = task
    prep = " ".join(str(e.get(k) or "") for k in ("ml_usage", "preprocessing"))
    if task == "imputation" or (re.search(r"synthetic data|oversampl|smote|adasyn|합성데이터|오버샘플", prep, re.I) and not re.search(r"no |not |none|미기재|처리 안", prep, re.I)):
        out["data_processing_or_augmentation"] = str(e.get("preprocessing") or e.get("ml_usage"))[:420]
    if "외부검증" in validation_codes(e.get("validation")): out["external_validation_or_transport"] = str(e.get("validation"))[:420]
    deployed = evidence(full, DISCUSSION["reports_implemented_tool_or_deployment"])
    if deployed: out["implemented_decision_tool"] = deployed
    return out


def main():
    refs = {r["key"]: r for r in load(REF / "refs.json") if r.get("verdict") == "INCLUDE"}
    rows = []
    for key, ref in refs.items():
        e = load(EXT / f"{key}.json")
        mp = REF / "md" / f"{key}.md"
        text = mp.read_text(encoding="utf-8", errors="ignore") if mp.exists() else ""
        full_ok = e.get("source") == "full_text" and "full_text: true" in text[:800]
        intro = section(text, r"(?:\d+[.]?\s*)?(?:introduction|background|서론)",
                        r"(?:\d+[.]?\s*)?(?:materials? and methods?|methods?|대상 및 방법|연구방법)", (0, max(6000, len(text)//4))) if full_ok else ""
        disc = section(text, r"(?:\d+[.]?\s*)?(?:discussion|conclusions?|고찰|논의|결론)",
                       r"(?:references|acknowledg(?:e)?ments?|funding|conflicts?|참고문헌)", (max(0, len(text)*2//3), len(text))) if full_ok else ""
        just = code_patterns(intro, JUSTIFICATION) if full_ok else {}
        discussion = code_patterns(disc, DISCUSSION) if full_ok else {}
        functions = actual_functions(e, text)
        if full_ok:
            rows.append({"key": key, "year": ref.get("year"), "full_text": full_ok,
                         "justification": just, "analytic_function": functions,
                         "discussion": discussion})

    def counts(field, denom=None):
        c = Counter(k for row in rows if denom is None or denom(row)
                    for k, value in row[field].items() if value)
        return dict(c.most_common())
    n_full = sum(r["full_text"] for r in rows)
    result = {
        "n_studies": len(rows), "n_full_text_coded": n_full,
        "denominators": {"justification": n_full, "analytic_function": len(rows), "discussion": n_full},
        "justification": counts("justification", lambda r: r["full_text"]),
        "analytic_function": counts("analytic_function"),
        "discussion": counts("discussion", lambda r: r["full_text"]),
        "no_explicit_justification": sum(r["full_text"] and not r["justification"] for r in rows),
        "no_discussion_category": sum(r["full_text"] and not any(r["discussion"].values()) for r in rows),
        "factor_insight_with_noncausal_caveat": sum(r["full_text"] and "emphasizes_factor_or_association_insight" in r["discussion"] and "acknowledges_cross_sectional_noncausal_limit" in r["discussion"] for r in rows),
        "per_study": rows,
    }
    (OUT / "ml_rationale.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (ROOT / "data" / "ml_rationale.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t"); w.writerow(["key", "year", "full_text", "justification", "analytic_function", "discussion"])
        for r in rows: w.writerow([r["key"], r["year"], r["full_text"], ";".join(r["justification"]), ";".join(r["analytic_function"]), ";".join(r["discussion"])])
    lines = ["# ML 사용 정당화·분석 기능·토의 해석 내용분석", "",
             f"포함 {len(rows)}편; 서론·토의 분석이 가능한 전문 {n_full}편. 범주는 중복 허용.", ""]
    for title, field, den in [("서론의 ML 사용 정당화", "justification", n_full), ("실제 분석 기능", "analytic_function", len(rows)), ("토의에서의 평가", "discussion", n_full)]:
        lines += [f"## {title}", "", "| 범주 | 편수 | 비율 |", "|---|---:|---:|"]
        for k, n in result[field].items(): lines.append(f"| {k} | {n} | {100*n/den:.1f}% |")
        lines.append("")
    (ROOT / "data" / "ML_RATIONALE_ANALYSIS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_study"}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
