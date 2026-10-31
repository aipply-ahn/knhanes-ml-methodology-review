"""Merge the adjudicated KCI supplementary search into the master corpus.

The KCI acquisition audit assigns records to CANDIDATE_CORE or
CANDIDATE_ADJACENT after title/abstract review and selected full-text checks. This
script maps those decisions to the review's authoritative corpus, screen, and
verdict files. It also appends the 104 KCI records absent from the bibliographic
corpus so the source is represented in the PRISMA denominator.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "results" / "derived"
REF = ROOT / "references"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(value, path):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def screening_status(row):
    return (row.get("acquisition_screening") or {}).get("status")


def ml_methods(text):
    tests = [
        (r"logistic regression|로지스틱", "logistic regression"),
        (r"random forest|랜덤\s?포레스트", "random forest"),
        (r"xgboost", "XGBoost"), (r"lightgbm|lgbm", "LightGBM"),
        (r"catboost", "CatBoost"), (r"adaboost", "AdaBoost"),
        (r"gradient boosting|gbm", "gradient boosting"),
        (r"support vector|\bsvm\b", "support vector machine"),
        (r"naive bayes|naïve bayes|나이브", "naive Bayes"),
        (r"k-nearest|\bknn\b", "k-nearest neighbors"),
        (r"decision tree|결정\s?트리|의사결정", "decision tree"),
        (r"neural network|신경망|\bann\b|multilayer perceptron|\bmlp\b", "neural network"),
        (r"deepgbm", "DeepGBM"), (r"deep autoencoder", "deep autoencoder"),
        (r"cvae|variational autoencoder", "CVAE"),
        (r"lasso", "LASSO"), (r"elastic net|탄성망", "elastic net"),
        (r"latent class|latent profile|잠재계층|잠재프로파일", "latent class/profile analysis"),
        (r"cluster|군집", "clustering"), (r"association rule|연관규칙", "association rules"),
        (r"principal component|주성분|factor analysis|요인분석", "PCA/factor analysis"),
    ]
    return [name for pat, name in tests if re.search(pat, text, re.I)]


def category(title):
    t = title.lower()
    rules = [
        (r"depress|suicid|stress|mental|정신|우울|자살", "mental_health"),
        (r"osteoporosis|sarcopen|bone|골다공|근감소", "osteoporosis_sarcopenia"),
        (r"diabet|당뇨", "diabetes"),
        (r"hypertension|stroke|cardio|심혈관|뇌졸중|고혈압|심근|협심", "cvd"),
        (r"metabolic syndrome|대사증후군", "metabolic_syndrome"),
        (r"periodont|oral|dental|치주|구강|치과", "oral_health"),
        (r"obesity|비만", "obesity"),
        (r"cataract|vision|시력|백내장", "hearing_vision"),
        (r"kidney|renal|콩팥|신장", "ckd"),
        (r"cholesterol|dyslip|콜레스테롤|이상지질", "dyslipidemia"),
        (r"nutrition|diet|food|영양|식사|식품", "nutrition_diet"),
        (r"quality of life|삶의 질|hrqol|hint-8", "qol_health_behavior"),
    ]
    for pat, value in rules:
        if re.search(pat, t, re.I):
            return value
    return "other"


def task(row, methods):
    t = (row.get("title") or "") + " " + (row.get("abstract_en") or row.get("abstract_ko") or "")
    if re.search(r"imput|대체", t, re.I): return "imputation"
    if re.search(r"feature selection|특징선택", t, re.I): return "feature_selection"
    if screening_status(row) == "CANDIDATE_ADJACENT": return "clustering_or_association"
    if re.search(r"regression model|회귀모형|회귀 모델|predicting .*quality of life", t, re.I) and not re.search(r"classif|분류|high.risk|고위험", t, re.I):
        return "regression"
    return "classification"


def main():
    kci = load(REF / "kci_refs.json")
    corpus = load(DER / "corpus.json")
    screen = load(DER / "screen.json")
    verdicts = load(DER / "verdicts.json")
    refs = load(REF / "refs.json")
    ref_by_key = {r["key"]: r for r in refs}
    corpus_by_uid = {r["uid"]: r for r in corpus["records"]}
    screen_by_uid = {r["uid"]: r for r in screen["rows"]}

    added = 0
    for row in kci:
        match = row.get("corpus_match") or {}
        key = row.get("existing_key") or row.get("key")
        uid = (ref_by_key.get(key) or {}).get("uid") or match.get("uid")
        kci_uid = "kci:" + row["kci_id"]
        if uid not in corpus_by_uid and kci_uid in corpus_by_uid:
            uid = kci_uid
        if uid not in corpus_by_uid:
            uid = kci_uid
            author_list = row.get("authors") or [a.strip() for a in (row.get("author") or "").split("|") if a.strip()]
            rec = {
                "uid": uid, "title": row.get("title_en") or row.get("title"),
                "year": row.get("year"), "authors": " and ".join(author_list),
                "author_list": author_list, "journal": row.get("journal"),
                "doi": row.get("doi"), "abstract": row.get("abstract_en") or row.get("abstract_ko"),
                "keywords": row.get("keywords"), "sources": ["KCI"],
                "landing": row.get("url"), "pdf_url": row.get("pdf_src"),
                "kci_id": row.get("kci_id"), "language": row.get("language"),
            }
            corpus["records"].append(rec); corpus_by_uid[uid] = rec; added += 1
            screen_row = {"uid": uid, "tier": "--", "t1": [], "t2": [], "t3": [], "sources": ["KCI"]}
            screen["rows"].append(screen_row); screen_by_uid[uid] = screen_row
        else:
            src = corpus_by_uid[uid].setdefault("sources", [])
            if "KCI" not in src: src.append("KCI")
            screen_by_uid.setdefault(uid, {"uid": uid, "tier": "--", "t1": [], "t2": [], "t3": [], "sources": ["KCI"]})

        status = screening_status(row)
        if status not in {"CANDIDATE_CORE", "CANDIDATE_ADJACENT"}:
            continue
        text = " ".join(str(row.get(k) or "") for k in ("title", "title_en", "abstract_ko", "abstract_en", "keywords"))
        methods = ml_methods(text)
        verdict = "INCLUDE" if status == "CANDIDATE_CORE" else "INCLUDE_ADJACENT"
        tier = "T1" if verdict == "INCLUDE" else "T2"
        s = screen_by_uid[uid]
        s["tier"] = tier
        s["t1" if tier == "T1" else "t2"] = methods or (["KCI full-text adjudication"] if verdict == "INCLUDE" else ["KCI adjacent-method adjudication"])
        verdicts[uid] = {
            "uid": uid, "verdict": verdict,
            "reason": "KCI supplementary-search record; KNHANES analysis and " + ("ML method confirmed" if verdict == "INCLUDE" else "ML-adjacent method confirmed"),
            "category": category(text), "ml_methods": methods,
            "task": task(row, methods), "knhanes_role": "primary",
            "outcome": row.get("title_en") or row.get("title"),
            "reviewed_on": "2026-09-06", "source_file": "kci_supplementary_adjudication",
        }

    # Idempotence and repair for runs made before the KCI UID recheck above.
    corpus["records"] = list({r["uid"]: r for r in corpus["records"]}.values())
    screen["rows"] = list({r["uid"]: r for r in screen["rows"]}.values())
    for r in screen["rows"]:
        r.setdefault("sources", corpus_by_uid.get(r["uid"], {}).get("sources", []))
    corpus["n"] = len(corpus["records"])
    corpus["n_with_abstract"] = sum(bool(r.get("abstract")) for r in corpus["records"])
    corpus["n_knhanes_in_ta"] = sum(bool(re.search(r"KNHANES|Korea[n]? National Health and Nutrition Examination Survey|국민건강영양조사", (r.get("title") or "") + " " + (r.get("abstract") or ""), re.I)) for r in corpus["records"])
    corpus["merged_on"] = "2026-09-06"
    corpus.setdefault("inputs", {})["KCI"] = {"input": len(kci), "new": added}
    screen["n"] = len(screen["rows"])
    screen["screened_on"] = "2026-09-06"
    tiers = {}
    for r in screen["rows"]: tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    screen["tiers"] = tiers
    dump(corpus, DER / "corpus.json")
    dump(screen, DER / "screen.json")
    dump(verdicts, DER / "verdicts.json")
    print(f"KCI merged: {len(kci)} records, {added} new; corpus={len(corpus['records'])}")


if __name__ == "__main__":
    main()
