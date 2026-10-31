"""명시적 모형 중요도 방법을 사용한 예측모형 연구의 상세표를 만든다.

출력:
  data/VARIABLE_IMPORTANCE_DETAILS.tsv
  data/VARIABLE_IMPORTANCE_DETAILS.md
"""
import csv
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compact(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def variable_count(text):
    """추출문에서 ML에 투입된 후보·입력 변수 수를 보수적으로 읽는다."""
    text = compact(text)
    patterns = [
        # 여러 단계가 함께 적혀 있으면 실제 적합에 들어간 최종 집합을 우선한다.
        r"final\s+(?:model\s+)?input\s*[:=]?\s*([\d,]{1,5})\s*(?:features?|predictors?|variables?)",
        r"최종(?:\s*입력)?(?:\s*후보)?(?:\s*변수)?\s*(?:수는?\s*)?([\d,]{1,5})\s*개",
        r"(?:ML\s*)?입력\s*변수\s*(?:수는?\s*)?([\d,]{1,5})\s*개",
        r"독립\s*변수\s*([\d,]{1,5})\s*개",
        r"(?:후보|입력|예측|초기|원|총|설문 기반|약)\s*(?:변수\s*)?(?:약\s*)?([\d,]{1,5})\s*개",
        r"^\s*([\d,]{1,5})\s*개\b",
        r"\bn\s*=\s*(\d{1,4})\s*(?:features?|predictors?|variables?)\b",
        r"\b(\d{1,4})\s*(?:features?|predictors?|variables?)\s*(?:were|was)?\s*(?:retained|used|included|selected)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).replace(",", "")
    return "NR"


STATISTICAL_FILTER_EXCLUDE = {
    # The extraction explicitly says that the named test/selection was not used,
    # or it appeared only in a separate conventional-regression sensitivity analysis.
    "lee2026development", "jung2024four", "hosseinzadeh2023evaluation",
    "park2022prediction", "oh2019identifying", "lee2019predictive",
    "park2021application", "bhak2024machine", "kim2026inferring",
    "kim2022oculomics", "kim2025machinea", "yu2025retinal",
}

RECURSIVE_FILTER_EXCLUDE = {
    # Backward elimination is mentioned only to say that it was not applied.
    "lee2026development",
}


def selection_strategy(value, key=None):
    """중요변수 선택 규칙을 다중범주로 보존한다."""
    text = compact(value)
    lower = text.lower()
    if not text or re.fullmatch(r"(?:미기재|nr|none)", lower):
        return ["Unreported"]
    if re.match(r"없음", text) or "전부 투입" in text or "전체 변수 사용" in text or "전량 투입" in text:
        base = ["No reduction/all prespecified inputs"]
    else:
        base = []
    rules = [
        ("Fixed top-k from model ranking", r"(?:shap|importance|중요도).{0,80}상위\s*\d+개|상위\s*\d+개.{0,80}(?:선택|선정|골랐)|top[- ]?k"),
        ("Recursive/wrapper or performance-guided subset", r"\brfe(?:cv)?\b|recursive feature|재귀적 제거|최하위.{0,35}제거|후진제거|backward elimination|forward feature|wrapper|성능.{0,30}(?:최대|유지|하락)"),
        ("Importance threshold, shadow, or cross-model consensus", r"boruta|shadow feature|shadow importance|importance\s*[>≥]|중요도\s*[>≥]|95th percentile|상위\s*5%|공통 선택|교집합|\d+개 모형.{0,30}(?:선택|다수)"),
        ("Penalized/statistical filter", r"\blasso\b|l1[- ]regular|단변량|univariable|anova|chi[- ]?square|카이제곱|p\s*[<≤]|상관계수|pearson|spearman|\bvif\b|stepwise"),
        ("Expert/domain judgment", r"전문가|의사\s*\d*인|임상적|도메인|문헌 기반|선행연구|이론|researcher|expert|manual|수동|a priori|사전 (?:선정|지정|선택)"),
        ("Availability/missingness filter", r"결측|missing|연차.{0,20}(?:가용|일관)|조사주기.{0,20}일관|모든 코호트.{0,25}공통|자료 일관성"),
    ]
    for label, pattern in rules:
        if label == "Penalized/statistical filter" and key in STATISTICAL_FILTER_EXCLUDE:
            continue
        if label == "Recursive/wrapper or performance-guided subset" and key in RECURSIVE_FILTER_EXCLUDE:
            continue
        if re.search(pattern, lower, re.I):
            base.append(label)
    if (re.search(r"전문가|의사\s*\d*인|수동|manual|expert", text, re.I)
            and re.search(r"importance|중요도|shap|boruta|\brfe", text, re.I)):
        base.append("Expert/manual combined with model-guided selection")
    return list(dict.fromkeys(base or ["Described but not classifiable"]))


def importance_selection_status(value):
    text = compact(value)
    if not text or re.fullmatch(r"(?:미기재|nr|none)", text, re.I):
        return "Unreported"
    if re.search(r"shap-guided|importance.{0,100}(?:선택|선정|제거|상위\s*\d+개)|중요도.{0,100}(?:선택|선정|제거|상위\s*\d+개)|boruta|\brfe(?:cv)?\b|recursive feature|민감도 분석.{0,80}제거", text, re.I):
        return "Importance/model-guided selection"
    return "Importance reported for ranking; subset determined otherwise or not reduced"


def main():
    refs = {r["key"]: r for r in load(ROOT / "references" / "refs.json")}
    pathway = {r["key"]: r for r in load(ROOT / "results" / "derived" / "importance_pathway.json")["studies"]}
    rows = []
    for path in sorted(glob.glob(str(ROOT / "data" / "extraction" / "*.json"))):
        study = load(path)
        coded = pathway.get(study["key"])
        if not coded or not coded["explicit_importance_method"]:
            continue
        ref = refs[study["key"]]
        variables = compact(study.get("variables"))
        selection = compact(study.get("variable_selection"))
        strategies = selection_strategy(selection, study["key"])
        rows.append({
            "key": study["key"],
            "year": ref.get("year", ""),
            "topic": ref.get("category", ""),
            "title": ref.get("title", ""),
            "outcome": ref.get("outcome") or compact(study.get("problem")),
            "task": study.get("task", ""),
            "n_participants": study.get("n_final") or "NR",
            "n_input_variables": variable_count(variables),
            "input_variables_source_text": variables or "NR",
            "importance_methods": coded["importance_methods"],
            "importance_result": compact(study.get("interpretability")) or "NR",
            "importance_selection_status": importance_selection_status(selection),
            "selection_strategies": "; ".join(strategies),
            "selection_rule_source_text": selection or "NR",
            "importance_guided_inference": coded["importance_guided_inference"],
            "selected_n": coded.get("selected_n") or "",
            "inferential_n": coded.get("inferential_n") or "",
        })

    rows.sort(key=lambda r: (r["topic"], -int(r["year"] or 0), r["key"]))
    out_tsv = ROOT / "data" / "VARIABLE_IMPORTANCE_DETAILS.tsv"
    with out_tsv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    known = sum(r["n_input_variables"] != "NR" for r in rows)
    status_counts = {status: sum(r["importance_selection_status"] == status for r in rows)
                     for status in sorted({r["importance_selection_status"] for r in rows})}
    all_strategies = sorted({s for r in rows for s in r["selection_strategies"].split("; ")})
    strategy_counts = {strategy: sum(strategy in r["selection_strategies"].split("; ") for r in rows)
                       for strategy in all_strategies}
    md = [
        "# 변수 중요도 분석 상세표", "",
        f"명시적 모형 기반 중요도·설명 방법을 사용한 예측모형 연구 {len(rows)}편을 수록했다.",
        f"ML 입력 변수 수는 구조화 추출문에서 확인 가능한 {known}편에 제시했고, 확인되지 않으면 `NR`로 표시했다.",
        "중요도 결과가 후속 추론의 변수 집합을 결정한 경우만 마지막 열에 표시했다.", "",
        "## 중요변수 선정 방식", "",
    ]
    md += [f"- {key}: {value}편" for key, value in status_counts.items()]
    md += ["", "선정 규칙은 한 연구에서 여러 단계를 사용할 수 있으므로 중복 집계한다."]
    md += [f"- {key}: {value}편" for key, value in strategy_counts.items()]
    md += ["", "## 연구별 상세", "",
           "| 연구 | 주제 | 목적변수 | 입력 변수 수 | 중요도 방법 | 중요변수 선정 | 주요 중요도 결과 | 후속 추론 |",
           "|---|---|---|---:|---|---|---|---|"]
    for row in rows:
        outcome = compact(row["outcome"])[:100].replace("|", "/")
        result = row["importance_result"][:220].replace("|", "/")
        follow = "아니오"
        if row["importance_guided_inference"]:
            follow = f"예: 선택 {row['selected_n']} → 추론 {row['inferential_n']}"
        md.append(
            f"| {row['key']} ({row['year']}) | {row['topic']} | {outcome} | "
            f"{row['n_input_variables']} | {row['importance_methods']} | "
            f"{row['importance_selection_status']} ({row['selection_strategies']}) | {result} | {follow} |"
        )
    rendered = "\n".join(md) + "\n"
    (ROOT / "data" / "VARIABLE_IMPORTANCE_DETAILS.md").write_text(rendered, encoding="utf-8")
    (ROOT / "manuscript/submission/appendices/appendix9_variable_importance.md").write_text(rendered, encoding="utf-8")
    print(json.dumps({"n": len(rows), "n_input_count_reported": known,
                      "importance_selection_status": status_counts,
                      "selection_strategies": strategy_counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
