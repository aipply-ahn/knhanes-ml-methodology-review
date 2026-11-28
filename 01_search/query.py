"""Database search query, written once and reported verbatim:
    (survey names) AND (machine-learning terms), in title, abstract or keywords.
Each database receives the same terms in its own syntax (query strings printed by this file)."""
SURVEY = ["KNHANES", "Korea National Health and Nutrition Examination Survey", "Korean National Health and Nutrition Examination Survey",
          "Korea National Health and Nutrition Examination Surveys", "Korean National Health and Nutrition Examination Surveys",
          "Korea National Health and Nutrition Survey", "Korean National Health and Nutrition Survey",
          "Korea National Health and Nutritional Examination Survey", "Korean National Health and Nutritional Examination Survey"]
SURVEY_KO = ["국민건강영양조사", "국민건강 영양조사", "국민건강·영양조사", "국건영", "KNHANES", "KNHNAES", "National Health and Nutrition Examination Survey"]
ML = [
    "machine learning", "deep learning", "artificial intelligence", "supervised learning", "unsupervised learning",
    "reinforcement learning", "transfer learning", "federated learning", "AutoML", "large language model*", "ChatGPT",
    "decision tree*", "classification tree*", "regression tree*", "tree-based", "random forest*", "XGBoost", "LightGBM",
    "CatBoost", "AdaBoost", "boosting", "gradient boost*", "bagging", "ensemble learning", "ensemble model*", "CHAID", "CART",
    "neural network*", "perceptron", "convolutional", "recurrent neural", "transformer", "autoencoder*", "LSTM",
    "support vector", "SVM", "k-nearest", "naive Bayes", "Bayesian network*", "classifier*", "TabPFN",
    "SHAP", "Shapley", "explainable", "interpretable machine", "feature selection", "feature importance", "variable importance",
    "lasso", "elastic net", "clustering", "cluster analysis", "k-means", "latent class", "data mining", "association rule*",
    "prediction model*", "predictive model*", "risk prediction", "nomogram*", "area under the curve", "AUC",
]
ML_KO = ["머신러닝", "기계학습", "딥러닝", "인공지능", "의사결정나무", "결정나무", "랜덤포레스트", "부스팅", "앙상블", "신경망",
         "서포트벡터", "설명가능", "특징선택", "변수중요도", "라쏘", "군집분석", "잠재계층", "데이터마이닝", "연관규칙", "예측모형", "예측모델"]


def q(t):
    return f'"{t}"' if (" " in t or "-" in t) else t


def europepmc():
    # survey names in any field including the full text; ML terms in title, abstract or keywords
    s = " OR ".join(q(t) for t in SURVEY); m = " OR ".join(q(t) for t in ML)
    return f"({s}) AND (TITLE_ABS:({m}) OR KW:({m}))"


def pubmed():
    s = " OR ".join(f"{q(t)}[tiab]" for t in SURVEY)
    m = " OR ".join(f"{q(t)}[tiab] OR {q(t)}[ot]" for t in ML)
    return f"({s}) AND ({m})"


def expand(t):
    """singular and plural for a trailing wildcard (for exact-match fields without wildcard support)"""
    if not t.endswith("*"):
        return [t]
    b = t[:-1]
    return [b] if b.endswith("s") else [b, b + "s"]


def openalex_filter():
    # exact matching (no stemming) on title, abstract and keywords: stemming made 'clustering' match 'cluster sampling',
    # 'explainable' match 'explained' and 'classifier' match 'classified' (checked)
    f = "title_abstract_keywords.search.exact"
    s = " OR ".join(q(t) for t in SURVEY); m = " OR ".join(q(x) for t in ML for x in expand(t))
    return f"{f}:({s}),{f}:({m})"


def openalex():
    # OpenAlex stems words and does not allow wildcards inside phrases, so '*' is dropped
    s = " OR ".join(q(t) for t in SURVEY); m = " OR ".join(q(t.rstrip("*")) for t in ML)
    return f"({s}) AND ({m})"


if __name__ == "__main__":
    print(len(ML), "English ML terms;", len(ML_KO), "Korean ML terms (KCI)")
    for f in (europepmc, pubmed, openalex):
        print(f"\n[{f.__name__}] ({len(f())} chars)\n{f()}")
