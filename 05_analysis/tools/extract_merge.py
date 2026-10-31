"""data/extraction/<key>.json 전부 → data/EXTRACTION.md (논문별 정리) + data/extraction.tsv (표)

    python tools/extract_merge.py
"""
import csv, glob, sys
from collections import Counter
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

F = ["problem", "task", "ml_usage", "knhanes_waves", "knhanes_role", "other_datasets", "sample_filtering", "n_final",
     "variables", "variable_selection", "missing_handling", "preprocessing", "survey_weights", "models", "best_model",
     "hyperparameter_tuning", "validation", "metrics", "interpretability", "findings", "limitations",
     "code_data_availability", "notes", "source"]
KO = dict(problem="문제·결과변수", task="과제", ml_usage="ML 활용 방식", knhanes_waves="기수·연차", knhanes_role="KNHANES 역할",
          other_datasets="병용 자료", sample_filtering="샘플 필터링", n_final="최종 n", variables="입력변수",
          variable_selection="변수 선택", missing_handling="결측 처리", preprocessing="전처리·불균형", survey_weights="가중치",
          models="모델", best_model="최고 모델", hyperparameter_tuning="HP 튜닝", validation="검증", metrics="성능",
          interpretability="해석", findings="발견·보고", limitations="한계", code_data_availability="코드·데이터 공개", notes="메모",
          source="근거")


def coarse_w(v):
    t = s(v).lower()
    if t.startswith("yes"): return "yes — 분석에 반영" if not re.search(r"기술통계|descriptive|표 ?1|table 1|일부|partial", t) else "yes — 기술통계/일부에만"
    if t.startswith("no"): return "no — 미적용 명시"
    return "미기재 (언급 없음)"


def coarse_m(v):
    t = s(v).lower()
    if "미기재" in t or t in ("—", "null", "none"): return "미기재"
    if re.search(r"mice|multiple imputation|다중대체", t): return "다중대체 (MICE 등)"
    if re.search(r"knn|k-nearest|최근접", t): return "KNN 대체"
    if re.search(r"평균|중앙값|최빈|mean|median|mode", t): return "단순 대체 (평균/중앙값/최빈값)"
    if re.search(r"완전제거|complete|listwise|제거|삭제|excluded", t): return "완전제거 (complete-case)"
    if re.search(r"내장|native|xgboost|lightgbm|catboost", t): return "모델 내장 처리"
    return "기타/혼합"


CANON = [
 (r"xgb|extreme gradient", "XGBoost"), (r"lightgbm|light gradient|lgbm", "LightGBM"), (r"catboost", "CatBoost"),
 (r"adaboost|adaptive boost", "AdaBoost"), (r"gradient boost|gbm\b|gbdt", "Gradient boosting (GBM)"),
 (r"random forest|\brf\b", "Random forest"), (r"extra ?trees", "Extra trees"),
 (r"logistic|\blr\b", "Logistic regression"), (r"support vector|\bsvm\b|\bsvc\b", "SVM"),
 (r"decision tree|\bdt\b|cart|c5\.0|c4\.5|chaid|classification tree|regression tree", "Decision tree"),
 (r"k-?nearest|\bknn\b", "kNN"), (r"na[iï]ve bayes|\bnb\b", "Naive Bayes"),
 (r"multilayer|multi-layer|\bmlp\b|perceptron", "MLP"), (r"deep neural|\bdnn\b|deep learning", "DNN"),
 (r"artificial neural|\bann\b|neural network", "ANN (기타 신경망)"), (r"convolution|\bcnn\b", "CNN"),
 (r"lstm|recurrent|\bgru\b", "RNN/LSTM"), (r"tabnet|tabpfn", "TabNet/TabPFN"), (r"autoencoder", "Autoencoder"),
 (r"bayesian network", "Bayesian network"), (r"lasso|elastic|ridge|penali", "LASSO/EN/Ridge"),
 (r"k-?means|clustering|hierarchical", "Clustering (k-means 등)"), (r"latent class|latent profile|\blca\b|\blpa\b", "LCA/LPA"),
 (r"stacking|voting|ensemble", "Ensemble (stacking/voting)"), (r"linear discriminant|\blda\b", "LDA"),
 (r"linear regression", "Linear regression"), (r"gpt|llm|chatgpt", "LLM-assisted"),
]


def canon(m):
    t = str(m).lower()
    for pat, name in CANON:
        if re.search(pat, t): return name
    return str(m)[:30]


def s(v):
    if v is None: return "—"
    if isinstance(v, list): return "; ".join(str(x) for x in v)
    return str(v).replace("\n", " ")


def main():
    R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
    E = {}
    for f in glob.glob(os.path.join(PROJ, "data", "extraction", "*.json")):
        try:
            d = load(f); E[d.get("key") or os.path.basename(f)[:-5]] = d
        except Exception as e:
            print("  !! 파싱 실패", os.path.basename(f), e)
    rows = sorted(E.values(), key=lambda d: (R.get(d["key"], {}).get("verdict", ""), -(R.get(d["key"], {}).get("year") or 0), d["key"]))
    # TSV
    with open(os.path.join(PROJ, "data", "extraction.tsv"), "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["key", "verdict", "year", "journal", "title", "category"] + F)
        for d in rows:
            r = R.get(d["key"], {})
            w.writerow([d["key"], r.get("verdict"), r.get("year"), r.get("journal"), r.get("title"), r.get("category")] + [s(d.get(k)) for k in F])
    # MD
    L = []; A = L.append
    inc = [d for d in rows if R.get(d["key"], {}).get("verdict") == "INCLUDE"]
    adj = [d for d in rows if R.get(d["key"], {}).get("verdict") == "INCLUDE_ADJACENT"]
    A(f"# KNHANES × 머신러닝 — 논문별 추출 정리\n")
    A(f"생성 {time.strftime('%Y-%m-%d')} · `python tools/extract_merge.py` 자동생성. 원본은 `data/extraction/<key>.json`, 표는 `data/extraction.tsv`. "
      f"지침은 `tools/EXTRACT_GUIDE.md`. 논문 전문 md 는 `references/md/<key>.md`.\n")
    A(f"| | 건수 | 전문 근거 | 초록만 |"); A("|---|---:|---:|---:|")
    for name, g in (("ML 적용 (INCLUDE)", inc), ("ML 인접 (INCLUDE_ADJACENT)", adj)):
        A(f"| {name} | {len(g)} | {sum(1 for d in g if d.get('source') == 'full_text')} | {sum(1 for d in g if d.get('source') != 'full_text')} |")
    A("")
    A("## 한눈에 — 집계 (INCLUDE)\n")
    for k, title, fn in (("survey_weights", "가중치 사용 (요약)", coarse_w), ("missing_handling", "결측 처리 (요약)", coarse_m),
                         ("task", "과제", s), ("knhanes_role", "KNHANES 역할", s), ("best_model", "최고 모델 (정규화)", lambda v: canon(v) if v else "—")):
        c = Counter(fn(d.get(k)) for d in inc)
        A(f"**{title}**  "); A("| 값 | 건수 |"); A("|---|---:|")
        for v, n in c.most_common(12): A(f"| {v} | {n} |")
        A("")
    c = Counter()
    for d in inc:
        for name in set(canon(m) for m in (d.get("models") or []) if m): c[name] += 1
    A("**비교 모델 — 논문 수 (정규화, 한 논문에 한 번)**  "); A("| 모델 | 건수 |"); A("|---|---:|")
    for v, n in c.most_common(25): A(f"| {v} | {n} |")
    A("")
    A("## 요약표\n")
    A("| key | 연도 | 문제 | 기수·연차 | n | 가중치 | 결측 | 최고 모델 | 성능 |")
    A("|---|---:|---|---|---:|---|---|---|---|")
    for d in inc + adj:
        r = R.get(d["key"], {})
        A(f"| `{d['key']}` | {r.get('year')} | {s(d.get('problem'))[:60]} | {s(d.get('knhanes_waves'))[:30]} | {s(d.get('n_final'))} | {s(d.get('survey_weights'))[:25]} | {s(d.get('missing_handling'))[:30]} | {s(d.get('best_model'))[:30]} | {s(d.get('metrics'))[:50]} |")
    A("")
    for name, g in (("ML 적용 (INCLUDE)", inc), ("ML 인접 (INCLUDE_ADJACENT)", adj)):
        A(f"# {name} — {len(g)}편\n")
        for d in g:
            r = R.get(d["key"], {})
            pdf = f" · [PDF](../references/pdf/{r['pdf_file']})" if r.get("pdf_file") else ""
            A(f"## `{d['key']}` — {r.get('title')}\n")
            A(f"{(r.get('authors') or '')[:120]} · {r.get('journal')} · {r.get('year')} · [md](../references/md/{d['key']}.md){pdf}"
              + (f" · [doi](https://doi.org/{r['doi']})" if r.get("doi") else "") + f" · 근거: {s(d.get('source'))}\n")
            A("| 항목 | 내용 |"); A("|---|---|")
            for k in F:
                if k == "source": continue
                A(f"| {KO[k]} | {s(d.get(k))} |")
            A("")
    open(os.path.join(PROJ, "data", "EXTRACTION.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  EXTRACTION.md · extraction.tsv — {len(rows)} 편 (INCLUDE {len(inc)} · ADJACENT {len(adj)})")


if __name__ == "__main__":
    main()
