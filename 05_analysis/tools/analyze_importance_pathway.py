"""예측모형 연구에서 성능 비교 이후 변수 해석과 후속 통계분석의 경로를 재구성한다.

출력
  results/derived/importance_pathway.json
  data/IMPORTANCE_PATHWAY.tsv
  data/IMPORTANCE_PATHWAY.md

후속 통계분석은 단순히 회귀모형을 함께 사용한 경우가 아니다. 모형 중요도 또는
모형 기반 변수선택 결과가 뒤따르는 추론 분석의 변수 집합을 결정했다고 원문 근거에서
확인되는 경우만 ``importance_guided_inference``로 코딩한다.
"""
import csv
import glob
import json
import os
import re
from collections import Counter

from common import PROJ, REF, DER, load
from canonical_data import included_extractions


NEGATIVE_START = re.compile(
    r"^\s*(없음|해당 없음|미기재|변수중요도(를| 기법을|·)|"
    r"shap·permutation 등 없음|ann 자체에 대한 변수중요도)", re.I
)

METHODS = [
    ("SHAP", r"\bshap(?:ley)?\b"),
    ("Model-native importance", r"feature importance|variable importance|변수 ?중요도|"
                                r"\bgini\b|\bgain\b|relative influence|dropout loss|"
                                r"feature sensitivity|\bf-score\b|attention 값"),
    ("Permutation importance", r"permutation|순열|leave-one-feature-out 정확도 감소량"),
    ("LIME", r"\blime\b"),
    ("PDP/ALE/ICE", r"partial dependence|\bpdp\b|\bale\b|ice plot"),
    ("Tree/rule structure", r"의사결정나무 구조|트리 구조|분지 구조|노드 규칙|"
                            r"tree structure|decision tree rule"),
]

# 원문 재검토에서 확인된, 일반 명칭 정규식으로는 안정적으로 구별하기 어려운
# 모형별 중요도 산출법이다. 단순 회귀계수 보고는 여기에 포함하지 않는다.
EXTRA_METHODS = {
    "chang2023classification": ["Perturbation/ablation importance"],
    "oh2019identifying": ["Coefficient/statistic ranking"],
    "costello2020identifying": ["Network/model-specific importance"],
    "kim2021deepa": ["Perturbation/ablation importance"],
    "kim2021building": ["Coefficient/statistic ranking"],
    # Temporal attention is explicitly defined as a learned importance weighting
    # over sequence steps, although the paper does not plot a named-variable rank.
    "vallathan2025feature": ["Model-native importance"],
}

METHOD_NEGATIVE = {
    "SHAP": r"shap(?:ley)?[^.;]{0,35}(없음|미보고|미사용|사용하지|않았|않음)",
    "Model-native importance": r"(?:feature importance|variable importance|변수 ?중요도)[^.;]{0,35}(없음|미보고|미사용|사용하지|않았|않음)",
    "Permutation importance": r"(?:permutation|순열)[^.;]{0,35}(없음|미보고|미사용|사용하지|않았|않음)",
    "LIME": r"lime[^.;]{0,35}(없음|미보고|미사용|사용하지|않았|않음)",
    "PDP/ALE/ICE": r"(?:partial dependence|pdp|ale|ice plot)[^.;]{0,35}(없음|미보고|미사용|사용하지|않았|않음)",
}


def importance_methods(value):
    """명시적으로 수행한 모형 기반 중요도·설명 방법만 반환한다.

    추출문이 ``없음 (SHAP 미보고)``처럼 부재 사유에 방법명을 포함할 수 있으므로
    양성 정규식보다 부재 서두를 먼저 판정한다.
    """
    text = str(value or "").strip()
    if NEGATIVE_START.search(text):
        return []
    found = []
    for name, pattern in METHODS:
        hits = list(re.finditer(pattern, text, re.I))
        if not hits:
            continue
        negative = METHOD_NEGATIVE.get(name)
        if negative and all(
            re.search(negative, text[max(0, hit.start() - 10):hit.end() + 45], re.I)
            for hit in hits
        ):
            continue
        found.append(name)
    return found


# 원문 추출 근거를 다시 읽어 순차 연결을 확인한 연구만 수록한다. selected_n은
# 중요도/모형 기반 선택 단계가 남긴 변수 수이며, inferential_n은 뒤따르는 통계분석에
# 실제 들어간 수를 원문에서 확정할 수 있을 때만 기록한다.
GUIDED = {
    "ahn2025discovering": {
        "exact_carryover": True,
        "selected_n": "17",
        "inferential_n": "17",
        "method": "repeated CatBoost feature-importance ranking",
        "inference": "sex- and age-stratified survey-weighted linear and logistic regression",
        "evidence": "The top 20 CatBoost-ranked variables were reduced by three prespecified exclusions; the remaining 17 were assessed in stratified multivariable regressions.",
    },
    "bhak2024machine": {
        "exact_carryover": False,
        "selected_n": "11 core",
        "inferential_n": "NR (expanded by domain)",
        "method": "XGBoost importance/RFE; BorutaShap",
        "inference": "survey-weighted multivariable logistic regression",
        "evidence": "119 variables were reduced to 11 primary factors; regression also examined domain-specific additions.",
    },
    "byeon2022exploring": {
        "exact_carryover": True,
        "selected_n": "8",
        "inferential_n": "8",
        "method": "CatBoost impurity importance",
        "inference": "multivariable logistic regression and nomogram",
        "evidence": "The eight highest-ranked CatBoost variables were carried into adjusted logistic regression.",
    },
    "nam2021discovery": {
        "exact_carryover": False,
        "selected_n": "18",
        "inferential_n": "NR (expanded set)",
        "method": "XGBoost gain/elimination; SHAP",
        "inference": "survey-weighted logistic regression",
        "evidence": "Importance-based elimination retained 18 variables; regression tested these and additional prespecified factors.",
    },
    "kim2026predicting": {
        "exact_carryover": True,
        "selected_n": "7 adults; 10 older adults",
        "inferential_n": "7; 10",
        "method": "boosting relative influence; dropout loss",
        "inference": "stratum-specific logistic regression",
        "evidence": "Only the top-ranked variables in each age stratum were entered into logistic regression.",
    },
    "wu2026development": {
        "exact_carryover": False,
        "selected_n": "5",
        "inferential_n": "3 continuous",
        "method": "Boruta after LASSO; SHAP",
        "inference": "restricted cubic splines",
        "evidence": "Five predictors formed the model; nonlinear inference was reported for age, waist circumference, and AIP.",
    },
    "zhang2026online": {
        "exact_carryover": False,
        "selected_n": "15",
        "inferential_n": "3 continuous",
        "method": "gradient-boosting RFE; SHAP",
        "inference": "restricted cubic splines",
        "evidence": "Fifteen predictors formed the model; spline analyses followed for age, BMI, and ALP.",
    },
}


def main():
    refs = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
    ext = included_extractions()
    pred = [d for d in ext if refs.get(d["key"], {}).get("verdict") == "INCLUDE"
            and d.get("task") == "classification"]
    rationale = {r["key"]: r for r in load(os.path.join(DER, "ml_rationale.json"))["per_study"]}

    rows = []
    method_counts = Counter()
    for d in pred:
        key = d["key"]
        funcs = rationale[key]["analytic_function"]
        compared = bool(funcs.get("algorithm_comparison"))
        interpreted = bool(funcs.get("feature_or_risk_factor_interpretation"))
        methods = importance_methods(d.get("interpretability"))
        methods = list(dict.fromkeys(methods + EXTRA_METHODS.get(key, [])))
        method_counts.update(set(methods))
        guided = GUIDED.get(key)
        rows.append({
            "key": key,
            "year": refs[key].get("year"),
            "algorithm_comparison": int(compared),
            "feature_or_risk_interpretation": int(interpreted),
            "explicit_importance_method": int(bool(methods)),
            "importance_methods": "; ".join(methods),
            "importance_guided_inference": int(bool(guided)),
            "selected_n": guided["selected_n"] if guided else "",
            "inferential_n": guided["inferential_n"] if guided else "",
            "inference": guided["inference"] if guided else "",
            "evidence": guided["evidence"] if guided else "",
        })

    summary = {
        "n_predictive": len(pred),
        "cohort": "full-report primary classification studies",
        "n_algorithm_comparison": sum(r["algorithm_comparison"] for r in rows),
        "n_comparison_without_interpretation": sum(
            r["algorithm_comparison"] and not r["feature_or_risk_interpretation"] for r in rows),
        "n_feature_or_risk_interpretation": sum(r["feature_or_risk_interpretation"] for r in rows),
        "n_comparison_and_interpretation": sum(
            r["algorithm_comparison"] and r["feature_or_risk_interpretation"] for r in rows),
        "n_explicit_importance_method": sum(r["explicit_importance_method"] for r in rows),
        "n_comparison_and_explicit_importance": sum(
            r["algorithm_comparison"] and r["explicit_importance_method"] for r in rows),
        "n_comparison_without_explicit_importance": sum(
            r["algorithm_comparison"] and not r["explicit_importance_method"] for r in rows),
        "n_no_comparison_and_explicit_importance": sum(
            not r["algorithm_comparison"] and r["explicit_importance_method"] for r in rows),
        "importance_method_counts": dict(method_counts.most_common()),
        "n_importance_guided_inference": sum(r["importance_guided_inference"] for r in rows),
        "n_exact_carryover": sum(v["exact_carryover"] for v in GUIDED.values()),
        "guided_studies": [{"key": k, **v} for k, v in GUIDED.items()],
        "definition": {
            "comparison_without_interpretation": "Algorithm comparison reported without feature/risk-factor interpretation.",
            "explicit_importance_method": "A named or operationally defined model-based importance/explanation method was reported.",
            "importance_guided_inference": "Model-derived importance/selection explicitly determined variables in a later inferential analysis.",
        },
    }
    os.makedirs(DER, exist_ok=True)
    with open(os.path.join(DER, "importance_pathway.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "studies": rows}, f, ensure_ascii=False, indent=2)

    tsv = os.path.join(PROJ, "data", "IMPORTANCE_PATHWAY.tsv")
    with open(tsv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
        w.writeheader(); w.writerows(rows)

    md = [
        "# 예측모형 이후의 변수 해석·통계분석 경로", "",
        "단순 회귀 비교모형은 후속 통계분석으로 세지 않았다. 모형 중요도 또는 모형 기반 선택이",
        "뒤따르는 추론 분석의 변수 집합을 결정했다고 원문에서 확인되는 경우만 엄격하게 집계했다.", "",
        f"- 예측모형 연구: {summary['n_predictive']}편",
        f"- 알고리즘 비교: {summary['n_algorithm_comparison']}편",
        f"- 알고리즘 비교 후 명시적 모형 중요도 분석으로 진행: {summary['n_comparison_and_explicit_importance']}편",
        f"- 알고리즘 비교 후 명시적 모형 중요도 분석 없음: {summary['n_comparison_without_explicit_importance']}편",
        f"- 변수·위험요인 해석 수행: {summary['n_feature_or_risk_interpretation']}편",
        f"- 명시적 모형 기반 중요도·설명 방법 사용: {summary['n_explicit_importance_method']}편",
        f"- 중요도/선택 결과를 후속 추론 분석으로 명확히 전달: {summary['n_importance_guided_inference']}편", "",
        "## 중요도·설명 방법(중복 허용)", "", "| 방법 | 편수 |", "|---|---:|",
    ]
    md += [f"| {k} | {v} |" for k, v in summary["importance_method_counts"].items()]
    md += ["", "## 중요도 기반 후속 추론 분석", "",
           "| 연구 | 중요도 단계 선택 수 | 추론 분석 투입 수 | 방법 | 후속 분석 |",
           "|---|---:|---:|---|---|"]
    for k, v in GUIDED.items():
        md.append(f"| {k} | {v['selected_n']} | {v['inferential_n']} | {v['method']} | {v['inference']} |")
    md += ["", "`NR`은 후속 분석의 전체 투입 수를 원문에서 고정할 수 없음을 뜻한다.",
           "중요도 분석과 회귀를 병렬로 수행했지만 중요도 결과가 회귀 변수선택을 결정하지 않은 연구는",
           "이 마지막 6편에 포함하지 않았다."]
    with open(os.path.join(PROJ, "data", "IMPORTANCE_PATHWAY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
