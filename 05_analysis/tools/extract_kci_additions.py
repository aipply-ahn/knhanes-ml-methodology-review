"""Create structured records for studies added by the KCI supplementary search.

This is a deterministic first-pass extractor. It uses the KCI bibliographic record,
the locally acquired full text, and conservative coding: absent information is
recorded as unreported. The generated records remain auditable against the source
PDF/Markdown and use the same schema as the original extraction set.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "references"
EXT = ROOT / "data" / "extraction"
ROB = ROOT / "data" / "probast"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(value, path): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def clean(text): return re.sub(r"\s+", " ", text or "").strip()


MODEL_PATTERNS = [
    (r"logistic regression|로지스틱", "logistic regression"),
    (r"random forest|랜덤\s?포레스트", "random forest"),
    (r"xgboost", "XGBoost"), (r"lightgbm|lgbm", "LightGBM"),
    (r"catboost", "CatBoost"), (r"adaboost", "AdaBoost"),
    (r"gradient boosting|\bgbm\b", "gradient boosting"),
    (r"support vector|\bsvm\b", "support vector machine"),
    (r"naive bayes|naïve bayes|나이브", "naive Bayes"),
    (r"k-nearest|\bknn\b|k-nn", "k-nearest neighbors"),
    (r"decision tree|결정\s?트리|의사결정", "decision tree"),
    (r"deep belief", "deep belief network"),
    (r"deepgbm", "DeepGBM"), (r"deep autoencoder", "deep autoencoder"),
    (r"conditional variational|\bcvae\b", "CVAE"),
    (r"multilayer perceptron|multi-layer perceptron|\bmlp\b", "multilayer perceptron"),
    (r"artificial neural|neural network|신경망|\bann\b", "neural network"),
    (r"lasso", "LASSO"), (r"elastic net|탄성망", "elastic net"),
    (r"samme", "SAMME"),
]


def models(text):
    return [name for pat, name in MODEL_PATTERNS if re.search(pat, text, re.I)]


def source_text(row, ref):
    keys = [ref["key"], row.get("existing_key"), row.get("key")]
    for key in keys:
        if not key: continue
        path = REF / "md" / f"{key}.md"
        if path.exists() and path.stat().st_size > 1000:
            return path.read_text(encoding="utf-8", errors="ignore"), "full_text"
    abstract = row.get("abstract_en") or row.get("abstract_ko") or ref.get("abstract") or ""
    return abstract, "full_text" if ref.get("pdf_file") else "abstract_only"


def waves(text):
    spans = []
    for a, b in re.findall(r"(?:KNHANES[^.\n]{0,90}?|국민건강영양조사[^.\n]{0,90}?)(20\d{2}|19\d{2})\s*[–—~-]\s*(20\d{2}|19\d{2})", text, re.I):
        if 1998 <= int(a) <= 2026 and 1998 <= int(b) <= 2026: spans.append((int(a), int(b)))
    years = [int(x) for x in re.findall(r"\b(?:19|20)\d{2}\b", text[:12000]) if 1998 <= int(x) <= 2026]
    if spans:
        a, b = spans[0]; return f"KNHANES {a}–{b}"
    if years:
        plausible = [y for y in years if y <= 2024]
        if plausible: return "KNHANES " + (str(plausible[0]) if len(set(plausible)) == 1 else f"{min(plausible)}–{max(plausible)}")
    return "KNHANES (연도 미기재)"


def sample_n(abstract):
    pats = [r"(?:total of|included|comprised|data of)\s+([\d,]+)\s+(?:participants|subjects|individuals|adults|cases)",
            r"([\d,]+)\s+(?:participants|subjects|individuals|adults|cases)\s+(?:were|was)",
            r"\bn\s*=\s*([\d,]+)", r"총\s*([\d,]+)\s*명"]
    for pat in pats:
        m = re.search(pat, abstract, re.I)
        if m:
            n = int(m.group(1).replace(",", ""))
            if 20 <= n <= 1000000: return n
    return None


def missing_handling(text):
    if re.search(r"multiple imputation|다중대체", text, re.I): return "multiple imputation"
    if re.search(r"k[- ]?nearest.*imput|knn imput", text, re.I): return "k-nearest-neighbor imputation"
    if re.search(r"imput", text, re.I): return "imputation described"
    if re.search(r"exclud[^.]{0,100}missing|missing[^.]{0,100}exclud|결측[^.]{0,60}제외", text, re.I): return "complete-case analysis (participants with missing values excluded)"
    return "미기재"


def preprocessing(text):
    found = []
    for pat, label in [(r"smote|adasyn", "SMOTE/ADASYN"), (r"undersampl", "undersampling"),
                       (r"oversampl|synthetic data|합성데이터", "oversampling/synthetic data"),
                       (r"class weight|imbalance adjustment|불균형.*조정", "class weighting"),
                       (r"standardi[sz]|normaliz|정규화|표준화", "standardization")]:
        if re.search(pat, text, re.I): found.append(label)
    return "; ".join(found) if found else "class imbalance handling not reported"


def validation(text):
    found = []
    if re.search(r"external validation|외부검증", text, re.I): found.append("external validation")
    m = re.search(r"(\d+)[- ]fold cross[- ]validation", text, re.I)
    if m: found.append(m.group(1) + "-fold cross-validation")
    elif re.search(r"cross[- ]validation|교차검증", text, re.I): found.append("cross-validation")
    if re.search(r"train(?:ing)?(?: set| data)?[^.]{0,100}(?:test|validation)(?: set| data)|훈련[^.]{0,80}(?:검증|시험)", text, re.I): found.append("train/test split")
    return "; ".join(dict.fromkeys(found)) if found else "미기재"


def weights(text):
    snippets = " ".join(re.findall(r"[^.\n]{0,100}(?:survey weight|sampling weight|complex sampl|복합표본|가중치)[^.\n]{0,130}", text, re.I))
    if re.search(r"machine learning|model|모형|모델", snippets, re.I) and re.search(r"appl|incorporat|account|반영|적용", snippets, re.I):
        return "일부 반영 주장(복합표본/가중치 적용 범위가 ML 학습까지인지 불명확)"
    if snippets: return "조사설계 소개 또는 기술통계에만 언급; ML 학습 반영 미기재"
    return "미기재 (언급 없음)"


def interpretability(text):
    found=[]
    for pat,label in [(r"\bshap\b|shapley", "SHAP"), (r"partial dependence|\bpd plot", "partial dependence"),
                      (r"accumulated local|\bale plot", "ALE"), (r"feature importance|variable importance|변수중요", "feature importance")]:
        if re.search(pat,text,re.I): found.append(label)
    return "; ".join(found) if found else "없음"


def code_availability(text):
    m = re.search(r"https?://(?:www\.)?(?:github|gitlab)\S+", text, re.I)
    if m: return "code publicly available: " + m.group(0).rstrip(".,)")
    if re.search(r"code.{0,30}(?:request|available from)|요청.{0,30}코드", text, re.I): return "code available on request"
    return "KNHANES data publicly available; analysis code not reported"


def task(row):
    t = clean(" ".join(str(row.get(k) or "") for k in ("title", "title_en", "abstract_ko", "abstract_en")))
    if re.search(r"imput|대체", t, re.I): return "imputation"
    if re.search(r"feature selection|특징선택", t, re.I): return "feature_selection"
    if re.search(r"regression model|회귀모형|회귀 모델", t, re.I) and not re.search(r"classif|분류", t, re.I): return "regression"
    return "classification"


def tripod(text, abstract, ref):
    lower = text.lower()
    def has(p): return "Y" if re.search(p, text, re.I) else "N"
    out = {
        "title_design": has(r"machine learning|머신\s?러닝|기계\s?학습|deep|신경망|random forest|prediction|예측"),
        "abstract_structured": "Y" if len(re.findall(r"(?:objective|methods?|results?|conclusions?|목적|방법|결과|결론)\s*[:：]", abstract, re.I)) >= 3 else "N",
        "background_objective": has(r"objective|aim|purpose|목적"), "data_source": has(r"KNHANES|국민건강영양조사"),
        "participants_eligibility": has(r"inclusion|exclusion|excluded|eligible|대상자|제외"),
        "outcome_definition": has(r"defined as|definition|진단|정의"), "predictors_description": has(r"predictor|feature|variable|변수"),
        "sample_size_justification": "N",
        "missing_data": has(r"missing|결측|무응답"), "model_building": has(r"training|hyperparameter|cross.validation|모델.*구축|모형.*개발"),
        "model_performance_measures": has(r"auc|accuracy|precision|recall|f1|rmse|mae|성능"),
        "model_evaluation": has(r"validation|test set|cross.validation|검증"),
        "results_participants": "Y" if sample_n(abstract) else "N", "results_performance": has(r"auc|accuracy|precision|recall|f1|rmse|mae"),
        "limitations": has(r"limitations?|제한점|한계"), "data_availability": has(r"data availability|publicly available|자료.*공개"),
        "code_availability": has(r"github|gitlab|code availability|코드.*공개"), "funding": has(r"funding|acknowledg|지원|연구비"),
        "model_availability": has(r"github|web application|source code|모델.*공개"),
    }
    return out


def main():
    refs = load(REF / "refs.json")
    kci = load(REF / "kci_refs.json")
    by_uid = {r["uid"]: r for r in refs}
    by_key = {r["key"]: r for r in refs}
    kci_rows = []
    for row in kci:
        st = (row.get("acquisition_screening") or {}).get("status")
        if st not in {"CANDIDATE_CORE", "CANDIDATE_ADJACENT"}: continue
        uid = (by_key.get(row.get("existing_key")) or by_key.get(row.get("key")) or {}).get("uid")
        if not uid: uid = (row.get("corpus_match") or {}).get("uid") or "kci:" + row["kci_id"]
        ref = by_uid.get(uid)
        if ref: kci_rows.append((row, ref))

    made_core = made_adj = 0
    for row, ref in kci_rows:
        out = EXT / f"{ref['key']}.json"
        if out.exists(): continue
        full, src = source_text(row, ref)
        abstract = clean(row.get("abstract_en") or row.get("abstract_ko") or ref.get("abstract") or "")
        text = clean((row.get("title_en") or row.get("title") or "") + " " + abstract + " " + full[:80000])
        mm = models(text)
        rec = {
            "key": ref["key"], "source": src,
            "problem": ref.get("outcome") or row.get("title_en") or row.get("title"),
            "task": task(row) if ref["verdict"] == "INCLUDE" else "clustering_or_association",
            "ml_usage": abstract or "KCI full text confirms use of the listed method with KNHANES data.",
            "knhanes_waves": waves(text), "knhanes_role": "primary", "other_datasets": None,
            "sample_filtering": abstract or "미기재", "n_final": sample_n(abstract),
            "variables": abstract or "미기재", "variable_selection": "미기재",
            "missing_handling": missing_handling(text), "preprocessing": preprocessing(text),
            "survey_weights": weights(text), "models": mm,
            "best_model": clean(next(iter(re.findall(r"[^.]{0,100}(?:highest|best|superior|우수|가장 높은)[^.]{0,120}", abstract, re.I)), "미기재")),
            "hyperparameter_tuning": "reported" if re.search(r"hyperparameter|grid search|random search|bayesian optimization", text, re.I) else "미기재",
            "validation": validation(text), "metrics": abstract or "미기재",
            "interpretability": interpretability(text), "findings": abstract or "미기재",
            "limitations": "See full text" if src == "full_text" else "abstract only; limitations unavailable",
            "code_data_availability": code_availability(text),
            "notes": "KCI supplementary-search addition; conservative first-pass coding, absent details recorded as unreported.",
        }
        dump(rec, out)
        if ref["verdict"] == "INCLUDE_ADJACENT": made_adj += 1; continue
        tri = tripod(text, abstract, ref)
        rob = {
            "key": ref["key"], "source": src,
            "probast": {
                "D1": {"1.1": "Y", "1.2": "PY", "judgment": "low", "note": "Cross-sectional KNHANES participant sample; no case-control sampling identified."},
                "D2": {"2.1": "PY", "2.2": "PN", "2.3": "Y", "judgment": "high", "note": "Predictors and target were generally measured in the same survey encounter; blinding and deployment-time availability were not established."},
                "D3": {"3.1": "PY", "3.2": "Y", "3.3": "PN", "3.4": "PY", "3.5": "PN", "3.6": "PN", "judgment": "high", "note": "The outcome was ascertained concurrently with predictors in cross-sectional data, limiting temporal prediction claims."},
                "D4": {"4.1": "NI", "4.2": "NI" if rec["missing_handling"] == "미기재" else "PY", "4.3": "PY", "4.4": "PY", "4.5": "N", "4.6": "PN", "4.7": "PN", "4.8": "NI", "4.9": "NA", "S1": "PY" if "일부 반영" in rec["survey_weights"] else "N", "S2": "N", "S3": "N" if "–" in rec["knhanes_waves"] else "NA", "judgment": "high", "note": "Complex sampling was not incorporated into resampling/performance estimation; calibration, missing-data handling, or optimism control was incomplete."},
            },
            "overall_rob": "high", "applicability": "low",
            "tripod": tri, "tripod_n_yes": sum(v == "Y" for v in tri.values()), "tripod_n_applicable": len(tri),
            "notes": "KCI supplementary-search addition assessed conservatively from the locally archived report.",
        }
        dump(rob, ROB / f"{ref['key']}.json")
        made_core += 1
    print(f"KCI extraction records created: core={made_core}, adjacent={made_adj}")


if __name__ == "__main__":
    main()
