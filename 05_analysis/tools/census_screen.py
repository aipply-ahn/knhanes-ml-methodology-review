"""제목+초록+키워드 규칙 선별 — ML 용어 사전. 3단계 tier.

    python tools/census_screen.py

  T1  ML/AI 방법 명시 (machine learning · random forest · XGBoost · neural network …)
  T2  ML 인접 — 벌점회귀(LASSO·elastic net) · 군집(k-means·hierarchical) · 결정나무류
  T3  예측모형 일반 (prediction model · nomogram · risk score) — ML 용어 없음. 수동검토용
  --  해당 없음

결과: results/derived/screen.json · screen.tsv
판정(verdict)은 별도 파일 results/derived/verdicts.json 에서 손으로 관리한다.
"""
import csv, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

# 약어는 (?-i:…) 로 대소문자 구분 — mL·dL·RF(radiofrequency) 오탐 방지
T1 = {
 "machine learning": r"machine[- ]learning|(?-i:\bML\b)(?![/-])",
 "deep learning": r"deep[- ]learning|(?-i:\bDL\b)(?![/-])",
 "artificial intelligence": r"artificial intelligence|(?-i:\bAI\b)(?![/-])",
 "neural network": r"neural[- ]network|(?-i:\b(ANN|DNN|MLP)s?\b)|multi-?layer perceptron|perceptron",
 "CNN": r"convolutional|(?-i:\bCNNs?\b)|ResNet|EfficientNet|(?-i:\bVGG)|DenseNet",
 "RNN/LSTM": r"(?-i:\b(LSTM|GRU|RNN)s?\b)|recurrent neural",
 "transformer/attention": r"\btransformer\b|self-attention|(?-i:\bBERT\b)",
 "random forest": r"random[- ]forest|(?-i:\bRF\b)(?= (model|classifier|algorithm|regress))",
 "gradient boosting": r"gradient[- ]boost|(?-i:\b(GBM|GBDT|XGB|LGBM)\b)|XGBoost|LightGBM|CatBoost|AdaBoost|\bboosting",
 "SVM": r"support[- ]vector|(?-i:\b(SVM|SVR)s?\b)",
 "decision tree": r"decision[- ]tree|classification and regression tree|(?-i:\bCART\b)|regression tree|C4\.5|C5\.0|(?-i:\bCHAID\b)|extra[- ]trees|ExtraTrees",
 "kNN": r"k-?nearest|(?-i:\b(KNN|k-NN|kNN)\b)",
 "naive Bayes": r"na[ïi]ve[- ]bayes",
 "ensemble": r"ensemble (model|learning|method|algorithm|classifier|approach)|\bstacking\b|\bbagging\b|voting classifier",
 "explainable/SHAP": r"(?-i:\bSHAP\b)|shapley|(?-i:\bLIME\b)|explainable|interpretable machine|(?-i:\bXAI\b)",
 "AutoML/TabPFN/TabNet": r"AutoML|TabPFN|TabNet",
 "autoencoder/GAN": r"autoencoder|generative adversarial|(?-i:\bGANs?\b)",
 "LLM": r"large language model|(?-i:\bLLMs?\b)|ChatGPT|(?-i:GPT-?\d)",
 "reinforcement": r"reinforcement learning",
 "Bayesian network": r"bayesian network",
 "federated/transfer": r"federated learning|transfer learning",
 "supervised/unsupervised learning": r"\b(un)?supervised (machine )?learning",
 "feature selection (ML)": r"boruta|recursive feature elimination|(?-i:\bRFE\b)|feature importance",
 "(한국어) ML/AI": r"머신\s?러닝|기계\s?학습|딥\s?러닝|심층\s?학습|인공\s?지능|인공\s?신경망|신경망|랜덤\s?포레스트|의사\s?결정\s?나무|결정\s?트리|부스팅|앙상블|서포트\s?벡터|나이브\s?베이즈|최근접\s?이웃|설명\s?가능",
}
T2 = {
 "penalized regression": r"(?-i:\bLASSO\b)|\blasso\b|elastic[- ]net|ridge regression|penalized regression|regulari[sz]ed regression",
 "clustering": r"k-?means|hierarchical clust|cluster analysis|clustering|latent class|latent profile|(?-i:\bDBSCAN\b)|self-organizing map",
 "dimensionality reduction": r"(?-i:\bt-SNE\b)|(?-i:\bUMAP\b)|principal component analysis|(?-i:\bPCA\b)",
 "data mining": r"data[- ]mining|association rule|apriori",
 "GAM/spline (flexible)": r"generalized additive|multivariate adaptive regression",
 "(한국어) ML 인접": r"군집\s?분석|클러스터|잠재\s?계층|잠재\s?프로파일|데이터\s?마이닝|주성분|라쏘|연관\s?규칙",
}
T3 = {
 "prediction model": r"predict(ion|ive) model|risk prediction|risk score|scoring system|nomogram|prognostic model|predictive performance|(?-i:\bAUC\b)|area under the (receiver|curve|ROC)|(?-i:\bC-statistic)|discrimination and calibration",
 "(한국어) 예측모형": r"예측\s?모형|예측\s?모델|위험\s?점수|노모그램|알고리즘",
}
NEG = r"\bNHANES\b(?! ?(korea|korean))"  # 미국 NHANES 만 언급 (참고용)


def hits(text, d):
    return [k for k, p in d.items() if re.search(p, text, re.I)]


def main():
    C = load(os.path.join(DER, "corpus.json"))
    rows = []
    for r in C["records"]:
        text = " ".join([r.get("title") or "", r.get("title_ko") or r.get("kdca_title_ko") or "", r.get("abstract") or "",
                         " ".join(r.get("keywords") or []), " ".join(r.get("mesh") or [])])
        h1, h2, h3 = hits(text, T1), hits(text, T2), hits(text, T3)
        tier = "T1" if h1 else "T2" if h2 else "T3" if h3 else "--"
        # 전문검색 층 B 에서만 잡힌 논문 — 초록엔 ML 없음. 수동검토 대상으로 승격
        if tier == "--" and (r.get("epmc_layer") in ("B",)):
            tier = "T3"; h3 = h3 + ["(EPMC 전문검색 B 층)"]
        rows.append(dict(uid=r["uid"], tier=tier, t1=h1, t2=h2, t3=h3,
                         year=r.get("year"), title=r.get("title"), journal=r.get("journal"),
                         cited=r.get("cited"), doi=r.get("doi"), pmid=r.get("pmid"),
                         pmcid=r.get("pmcid"), sources=r.get("sources"),
                         knhanes_in_ta=r.get("knhanes_in_ta"), has_abstract=bool(r.get("abstract")),
                         epmc_layer=r.get("epmc_layer"), pdf_url=r.get("pdf_url"),
                         oa_type=r.get("oa_type"), lang=r.get("lang")))
    from collections import Counter
    cnt = Counter(x["tier"] for x in rows)
    out = dict(screened_on=time.strftime("%Y-%m-%d"), n=len(rows), tiers=dict(cnt),
               dictionaries=dict(T1=T1, T2=T2, T3=T3), rows=rows)
    dump(out, os.path.join(DER, "screen.json"))
    with open(os.path.join(DER, "screen.tsv"), "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["uid", "tier", "terms", "year", "cited", "journal", "title", "doi", "pmid", "sources", "knhanes_in_ta", "has_abstract", "layer"])
        for x in sorted(rows, key=lambda x: (x["tier"], -(x["cited"] or 0))):
            w.writerow([x["uid"], x["tier"], "; ".join(x["t1"] + x["t2"] + x["t3"]), x["year"], x["cited"],
                        x["journal"], x["title"], x["doi"], x["pmid"], ",".join(x["sources"] or []),
                        x["knhanes_in_ta"], x["has_abstract"], x["epmc_layer"]])
    print(f"  선별 {len(rows)} → " + " · ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    t1 = Counter(t for x in rows if x["tier"] == "T1" for t in x["t1"])
    print("  T1 용어 분포:", dict(t1.most_common()))


if __name__ == "__main__":
    main()
