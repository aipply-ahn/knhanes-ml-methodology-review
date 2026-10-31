"""data/extraction/*.json → results/derived/analysis.json · data/ANALYSIS.md

리뷰 본문 표·그림의 원자료. 모든 수치는 여기서 나온다. 손으로 고치지 않는다.
    python tools/analyze_extraction.py
"""
import sys, re, json, os
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, DER, dump, load
from canonical_data import included_extractions
import glob

# ---------- 정규화 ----------
MODEL_CANON = [
 (r"xgb|extreme gradient", "XGBoost"), (r"lightgbm|light gradient|lgbm", "LightGBM"), (r"catboost", "CatBoost"),
 (r"adaboost|adaptive boost", "AdaBoost"), (r"gradient boost|\bgbm\b|gbdt", "Gradient boosting"),
 (r"random forest|\brf\b", "Random forest"), (r"extra ?trees", "Extra trees"),
 (r"logistic|\blr\b", "Logistic regression"), (r"support vector|\bsvm\b|\bsvc\b", "SVM"),
 (r"decision tree|\bdt\b|\bcart\b|c5\.0|c4\.5|chaid|classification tree|regression tree|의사결정나무", "Decision tree"),
 (r"k-?nearest|\bknn\b", "kNN"), (r"na[iï]ve bayes|\bnb\b", "Naive Bayes"),
 (r"multilayer|multi-layer|\bmlp\b|perceptron", "MLP"), (r"deep neural|\bdnn\b|deep learning|심층", "DNN"),
 (r"artificial neural|\bann\b|neural network|신경망", "ANN"), (r"convolution|\bcnn\b", "CNN"),
 (r"lstm|recurrent|\bgru\b", "RNN/LSTM"), (r"tabnet|tabpfn", "TabNet/TabPFN"), (r"autoencoder", "Autoencoder"),
 (r"bayesian network", "Bayesian network"), (r"lasso|elastic|ridge|penali", "LASSO/EN/Ridge"),
 (r"k-?means|clustering|hierarchical|군집", "Clustering"), (r"latent class|latent profile|\blca\b|\blpa\b", "LCA/LPA"),
 (r"stacking|voting|ensemble|앙상블", "Ensemble"), (r"linear discriminant|\blda\b", "LDA"),
 (r"linear regression", "Linear regression"), (r"gpt|llm|chatgpt", "LLM-assisted"),
 (r"association rule|apriori|연관규칙", "Association rules"),
]
def canon_model(m):
    t = str(m).lower()
    for pat, name in MODEL_CANON:
        if re.search(pat, t): return name
    return None

def weights(v):
    t = str(v or "").lower()
    if t.startswith("yes"):
        return "일부(기술통계·회귀만)" if re.search(r"기술통계|descriptive|표 ?1|table 1|일부|partial|regression|회귀", t) else "학습에 반영"
    if t.startswith("no"): return "미적용 명시"
    return "언급 없음"

def missing(v):
    t = str(v or "").lower()
    if not t or "미기재" in t or t in ("—","none","null"): return "미기재"
    if re.search(r"mice|multiple imputation|다중대체", t): return "다중대체"
    if re.search(r"knn|k-nearest|최근접", t): return "KNN 대체"
    if re.search(r"평균|중앙값|최빈|mean|median|mode", t): return "단순 대체"
    if re.search(r"완전제거|complete|listwise|제거|삭제|excluded|결측.*제외", t): return "완전제거"
    if re.search(r"내장|native|xgboost 자체|모델 내장", t): return "모델 내장"
    return "기타"

NEG_IMB = re.compile(r"불균형[^.;]{0,12}(처리)?[^.;]{0,8}(없|미기재|해당 없음|안 함|미시행|하지 않)|no (class )?imbalance|imbalance[^.;]{0,20}not")
def imbalance(v):
    t = str(v or "").lower()
    if re.search(r"smote|adasyn|borderline-?smote", t): return "SMOTE/ADASYN 계열"
    if re.search(r"undersampl|언더샘플|하향|down-?sampl", t): return "언더샘플링"
    if re.search(r"oversampl|오버샘플|상향|up-?sampl", t): return "오버샘플링(기타)"
    if re.search(r"class weight|클래스 가중|cost-sensitive|scale_pos_weight", t): return "클래스 가중"
    if re.search(r"층화 k-?fold|stratified (k-?fold|split)|층화 분할", t): return "층화 분할만"
    if NEG_IMB.search(t) or re.search(r"불균형", t): return "처리 안 함/미기재(명시)"
    return "미기재"

NEG_EXT = re.compile(r"외부\s?검증[^.;]{0,10}(없|미|안|불|부재|미실시|수행하지|아님)|no external|not[^.;]{0,15}external|external[^.;]{0,15}(not|없|미)|별도[^.;]{0,10}외부[^.;]{0,10}(없|검증 없)|'external validation'이라 표현")
def validation(v):
    t = str(v or "").lower()
    out = []
    if re.search(r"외부검증|external valid", t) and not NEG_EXT.search(t): out.append("외부검증")
    if (re.search(r"\bk-?fold|교차검증|cross-?valid", t)
            and not re.search(r"(?:no|without|not)\s+(?:\w+\s+){0,2}(?:k-?fold|cross-?validation)|교차검증.{0,12}(?:없|않)", t)):
        out.append("교차검증")
    if re.search(r"train.{0,6}test|holdout|hold-?out|분할|split|\d\s*:\s*\d|7:3|8:2", t): out.append("단일 분할")
    if not out:
        if re.search(r"없|미기재|not|no valid", t): return ["검증 없음/미기재"]
        return ["기타/미기재"]
    return out

def interp(v):
    t = str(v or "").lower()
    if re.search(r"shap", t): return "SHAP"
    if re.search(r"\blime\b", t): return "LIME"
    if re.search(r"permutation", t): return "순열 중요도"
    if re.search(r"중요도|importance|기여", t): return "변수 중요도(기타)"
    if re.search(r"없음|해당 없음|미기재|none", t): return "없음/미기재"
    return "기타"

def code_open(v):
    t = str(v or "").lower()
    if re.search(r"github|zenodo|osf|공개함|available at|http", t) and not re.search(r"공개 언급 없음|미공개|not available|없음", t):
        return "공개"
    if re.search(r"요청 시|on request|upon request", t): return "요청 시 제공"
    return "미공개/미기재"

LAYER = [("검진(검사·계측)", r"검진|계측|신체계측|혈압|혈액|검사|anthropometr|blood|laborator|examination|bmi|허리둘레|dxa|골밀도|폐기능|spiromet"),
         ("영양(식이)", r"영양|식이|식품|nutrit|diet|food|섭취|intake|24시간 회상|ffq"),
         ("설문(건강행태·사회경제)", r"설문|건강행태|흡연|음주|신체활동|소득|교육|직업|question|survey|behavio|socioeconom|smok|alcohol|physical activity"),
         ("구강", r"구강|치아|치주|oral|dental|periodont"),
         ("연계자료", r"연계|linkage|링크|사망|통계청|건강보험|claims|mortality follow")]
def layers(v):
    t = str(v or "").lower()
    return [n for n, p in LAYER if re.search(p, t)] or ["불명"]

def waves(v):
    # \b 대신 숫자 전후 부정 전방·후방탐색 — "2015년" 처럼 한글이 바로 붙으면 \b 가 성립하지 않아
    # 연도를 놓치던 문제가 있었다(2026-09-04 수정).
    ys = [int(y) for y in re.findall(r"(?<!\d)(19[89]\d|20[0-2]\d)(?!\d)", str(v or "")) if 1998 <= int(y) <= 2026]
    return (min(ys), max(ys)) if ys else None


# KNHANES 기수 경계. 조사가 없던 해(1999·2000·2002–2004·2006)는 직전 기수에 붙여
# 어느 연도든 하나의 기수로 사상되게 한다. 기수가 바뀌면 표본추출틀이 새로 설계되므로
# 기수를 넘는 통합은 같은 기수 안의 연차 통합보다 가중치 산출이 까다롭다.
CYCLE = [(1998, 2000, "제1기"), (2001, 2004, "제2기"), (2005, 2006, "제3기"),
         (2007, 2009, "제4기"), (2010, 2012, "제5기"), (2013, 2015, "제6기"),
         (2016, 2018, "제7기"), (2019, 2021, "제8기"), (2022, 2024, "제9기"),
         (2025, 2027, "제10기")]


def cycle_of(y):
    for a, b, name in CYCLE:
        if a <= y <= b: return name
    return None


def wave_scope(v):
    """사용한 조사연도가 단년인지, 같은 기수 안의 복수년인지, 기수를 넘는지.

    최소·최대 연도만으로 판정하므로 중간 연도를 건너뛴 경우(예: 2010·2011·2015)도
    바르게 '복수 기수'가 된다. 연도를 못 읽으면 None.
    """
    w = waves(v)
    if not w: return None
    a, b = w
    ca, cb = cycle_of(a), cycle_of(b)
    if ca is None or cb is None: return None
    if ca != cb: return "복수년 · 기수 넘음"
    return "단년" if a == b else "복수년 · 같은 기수"


# ---------- 성능 보고 깊이 · 변수중요도 · 사후 통계분석 ----------
def metric_depth(v):
    """성능 보고가 어디까지 갔나 — 단순 정확도에서 그쳤는지."""
    t = str(v or "").lower()
    if not t or t in ("—", "none", "null") or re.search(r"미보고|없음|지표 없음|report(ed)? no", t):
        return "성능 미보고"
    has_auc = bool(re.search(r"auc|auroc|auprc|c-?index|c-?statistic", t))
    has_cal = bool(re.search(r"calibration|보정곡선|brier|hosmer|보정 ?기울기", t))
    has_ci = bool(re.search(r"95% ?ci|신뢰구간|\(0\.\d+[–\-]0\.\d+\)", t))
    has_pr = bool(re.search(r"auprc|precision-?recall|\bf1\b|precision|recall|sens|spec|ppv|npv", t))
    if has_cal: return "판별력 + 보정"
    if has_auc and has_ci: return "판별력 + 신뢰구간"
    if has_auc and has_pr: return "판별력 + 분류지표"
    if has_auc: return "판별력만(AUC)"
    if re.search(r"정확도|accuracy|acc\b", t): return "정확도 중심"
    return "기타"


def importance_kind(v):
    """변수중요도 유형 — 중복 허용 목록."""
    t = str(v or "").lower()
    out = []
    if re.search(r"shap|shapley", t): out.append("SHAP")
    if re.search(r"permutation|순열|정확도 감소", t): out.append("순열 중요도(PI)")
    if re.search(r"lime\b", t): out.append("LIME")
    if re.search(r"impurity|gini|gain|내장|feature importance|variable importance|변수 ?중요도|feature sensitivity", t):
        out.append("모델 내장 중요도(FI)")
    if re.search(r"회귀계수|coefficient|\bor\b |오즈비|odds ratio|β|beta", t): out.append("회귀계수·오즈비")
    if re.search(r"partial dependence|\bpdp\b|ice plot|rcs|restricted cubic", t): out.append("부분의존·스플라인")
    if not out and re.search(r"없음|미보고|해당 없음|미기재", t): return ["없음"]
    return out or ["기타"]


def posthoc(v):
    """사후 통계분석 — 중복 허용 목록. 모형 성능 비교를 통계적으로 뒷받침했나."""
    t = str(v or "").lower()
    out = []
    if re.search(r"delong", t): out.append("DeLong 검정")
    if re.search(r"mcnemar", t): out.append("McNemar 검정")
    if re.search(r"bootstrap|부트스트랩", t): out.append("부트스트랩 신뢰구간")
    if re.search(r"decision curve|\bdca\b|결정곡선", t): out.append("결정곡선분석(DCA)")
    if re.search(r"calibration|보정곡선|brier|hosmer", t): out.append("보정 평가")
    if re.search(r"하위군|subgroup|성별 분리|sex-specific|연령대별|층화 분석", t): out.append("하위군 분석")
    if re.search(r"민감도 분석|sensitivity analysis", t): out.append("민감도 분석")
    if re.search(r"로지스틱 회귀|logistic regression|다변량 회귀|multivariable|오즈비|odds ratio", t):
        out.append("회귀 병행 분석")
    return out


def main():
    R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
    # Included studies come from the canonical JSON middle layer. Adjacent
    # records are outside its 223-study scope and remain a legacy screening
    # catalogue input only.
    E = included_extractions()
    E += [d for f in sorted(glob.glob(os.path.join(PROJ, "data", "extraction", "*.json")))
          for d in [load(f)] if R.get(d.get("key"), {}).get("verdict") == "INCLUDE_ADJACENT"]
    inc = [d for d in E if R.get(d["key"], {}).get("verdict") == "INCLUDE"]
    adj = [d for d in E if R.get(d["key"], {}).get("verdict") == "INCLUDE_ADJACENT"]
    A = {"n_include": len(inc), "n_adjacent": len(adj),
         "n_fulltext": sum(1 for d in inc if d.get("source") == "full_text")}

    A["year"] = dict(sorted(Counter(R[d["key"]].get("year") for d in inc).items(), key=lambda x: (x[0] or 0)))
    A["category"] = dict(Counter(R[d["key"]].get("category") or "미분류" for d in inc).most_common())
    A["task"] = dict(Counter(d.get("task") or "미기재" for d in inc).most_common())
    A["knhanes_role"] = dict(Counter(d.get("knhanes_role") or "미기재" for d in inc).most_common())
    A["weights"] = dict(Counter(weights(d.get("survey_weights")) for d in inc).most_common())
    A["missing"] = dict(Counter(missing(d.get("missing_handling")) for d in inc).most_common())
    A["imbalance"] = dict(Counter(imbalance(d.get("preprocessing")) for d in inc).most_common())
    A["interp"] = dict(Counter(interp(d.get("interpretability")) for d in inc).most_common())
    A["code"] = dict(Counter(code_open(d.get("code_data_availability")) for d in inc).most_common())
    vc = Counter()
    for d in inc:
        for v in set(validation(d.get("validation"))): vc[v] += 1
    A["validation"] = dict(vc.most_common())
    mc, bc = Counter(), Counter()
    for d in inc:
        names = set(filter(None, (canon_model(m) for m in (d.get("models") or []))))
        for n in names: mc[n] += 1
        b = canon_model(d.get("best_model"))
        if b: bc[b] += 1
    A["models_compared"] = dict(mc.most_common())
    A["best_model"] = dict(bc.most_common())
    A["n_models_per_paper"] = dict(sorted(Counter(len(set(filter(None,(canon_model(m) for m in (d.get("models") or []))))) for d in inc).items()))
    lc = Counter()
    for d in inc:
        for l in set(layers(d.get("variables"))): lc[l] += 1
    A["data_layer"] = dict(lc.most_common())
    ns = sorted(d["n_final"] for d in inc if isinstance(d.get("n_final"), int) and d["n_final"] > 0)
    A["n_final"] = {"count": len(ns), "median": ns[len(ns)//2], "q1": ns[len(ns)//4], "q3": ns[3*len(ns)//4],
                    "min": ns[0], "max": ns[-1],
                    "bins": dict(Counter(("<1,000" if n < 1000 else "1,000–4,999" if n < 5000 else
                                          "5,000–9,999" if n < 10000 else "10,000–29,999" if n < 30000 else "≥30,000") for n in ns))}
    yr = Counter(); span = Counter(); first = Counter()
    for d in inc:
        w = waves(d.get("knhanes_waves"))
        if not w: continue
        a, b = w
        for y in range(a, b + 1): yr[y] += 1
        span[("1년" if b - a == 0 else "2–3년" if b - a <= 2 else "4–6년" if b - a <= 5 else "7년 이상")] += 1
        first[a] += 1
    A["wave_year_usage"] = dict(sorted(yr.items()))
    A["wave_span"] = dict(span.most_common())
    A["wave_parsed"] = sum(span.values())
    # 단년 / 같은 기수 안의 복수년 / 기수를 넘는 복수년 — 통합 가중치가 필요해지는 지점
    P = {k: v for k, v in
         ((d["key"], (load(os.path.join(PROJ, "data", "probast", d["key"] + ".json")) or {}))
          for d in inc) if v}
    sc = Counter(); n_cycles = Counter(); sc_s3 = defaultdict(Counter); sc_w = defaultdict(Counter)
    for d in inc:
        s_ = wave_scope(d.get("knhanes_waves"))
        if not s_:
            sc["연도 불명"] += 1
            continue
        sc[s_] += 1
        w = waves(d.get("knhanes_waves"))
        n_cycles[len({cycle_of(y) for y in range(w[0], w[1] + 1)})] += 1
        s3 = ((P.get(d["key"], {}).get("probast") or {}).get("D4") or {}).get("S3", "미평가")
        sc_s3[s_][s3] += 1
        sc_w[s_][weights(d.get("survey_weights"))] += 1
    ORD = ["단년", "복수년 · 같은 기수", "복수년 · 기수 넘음", "연도 불명"]
    A["wave_scope"] = {k: sc[k] for k in ORD if k in sc}
    A["wave_n_cycles"] = {str(k): v for k, v in sorted(n_cycles.items())}
    A["wave_scope_x_s3"] = {k: dict(sc_s3[k].most_common()) for k in ORD if k in sc_s3}
    A["wave_scope_x_weights"] = {k: dict(sc_w[k].most_common()) for k in ORD if k in sc_w}
    # 결과변수 × 가중치, 결과변수 × 연도
    cw = defaultdict(Counter)
    for d in inc: cw[R[d["key"]].get("category") or "미분류"][weights(d.get("survey_weights"))] += 1
    A["category_x_weights"] = {k: dict(v) for k, v in sorted(cw.items(), key=lambda x: -sum(x[1].values()))}
    cy = defaultdict(Counter)
    for d in inc:
        y = R[d["key"]].get("year")
        p = "–2019" if (y or 0) <= 2019 else "2020–2022" if y <= 2022 else "2023–2024" if y <= 2024 else "2025–2026"
        cy[p][R[d["key"]].get("category") or "미분류"] += 1
    A["period_x_category"] = {k: dict(v.most_common()) for k, v in cy.items()}
    py = defaultdict(Counter)
    for d in inc:
        y = R[d["key"]].get("year")
        p = "–2019" if (y or 0) <= 2019 else "2020–2022" if y <= 2022 else "2023–2024" if y <= 2024 else "2025–2026"
        py[p]["n"] += 1
        py[p][weights(d.get("survey_weights"))] += 1
        py[p][missing(d.get("missing_handling"))] += 1
        if "외부검증" in validation(d.get("validation")): py[p]["외부검증"] += 1
        if interp(d.get("interpretability")) in ("SHAP", "LIME", "순열 중요도", "변수 중요도(기타)"): py[p]["해석기법 사용"] += 1
        if code_open(d.get("code_data_availability")) == "공개": py[p]["코드 공개"] += 1
    A["period_trend"] = {k: dict(v) for k, v in sorted(py.items())}
    # ADJACENT
    A["metric_depth"] = dict(Counter(metric_depth(d.get("metrics")) for d in inc).most_common())
    ic = Counter()
    for d in inc:
        for k in set(importance_kind(d.get("interpretability"))): ic[k] += 1
    A["importance_kind"] = dict(ic.most_common())
    A["n_any_importance"] = sum(1 for d in inc if importance_kind(d.get("interpretability")) != ["없음"]
                                and importance_kind(d.get("interpretability")) != ["기타"])
    pc = Counter(); npost = 0
    for d in inc:
        t = " ".join(str(d.get(k) or "") for k in ("metrics", "validation", "findings", "interpretability", "notes"))
        got = set(posthoc(t))
        for k in got: pc[k] += 1
        if got: npost += 1
    A["posthoc"] = dict(pc.most_common())
    A["n_any_posthoc"] = npost
    A["n_no_posthoc"] = len(inc) - npost
    # 판별력·보정 보고 — 초록 문장의 근거. 보정은 성능 보고 깊이와 사후 보정평가의 합집합.
    nd = nc = 0
    for d in inc:
        md = metric_depth(d.get("metrics"))
        t = " ".join(str(d.get(k) or "") for k in ("metrics", "validation", "findings", "interpretability", "notes"))
        if md.startswith("판별력"): nd += 1
        if md == "판별력 + 보정" or "보정 평가" in posthoc(t): nc += 1
    A["n_discrimination"] = nd
    A["n_calibration"] = nc
    # 모형 비교 방식: 여러 모형을 비교했는데 통계 검정 없이 수치만 나열했나
    cmp_rows = Counter()
    for d in inc:
        nm = len(set(filter(None, (canon_model(m) for m in (d.get("models") or [])))))
        t = " ".join(str(d.get(k) or "") for k in ("metrics", "validation", "findings", "notes"))
        stat = bool(re.search(r"delong|mcnemar|bootstrap|부트스트랩|95% ?ci|신뢰구간|p ?[<=]|유의", t, re.I))
        if nm <= 1: cmp_rows["단일 모형(비교 없음)"] += 1
        elif stat: cmp_rows["복수 모형 + 통계적 뒷받침"] += 1
        else: cmp_rows["복수 모형, 수치 나열만"] += 1
    A["model_comparison"] = dict(cmp_rows.most_common())
    A["adjacent_method"] = dict(Counter((("LCA/LPA" if re.search(r"latent class|latent profile|잠재",str(d.get('ml_methods') or d.get('models') or ''),re.I)
        else "군집(k-means 등)" if re.search(r"k-?means|cluster|군집",str(d.get('models') or ''),re.I)
        else "PCA/요인분석" if re.search(r"pca|주성분|factor",str(d.get('models') or ''),re.I)
        else "LASSO/벌점회귀" if re.search(r"lasso|penal|elastic",str(d.get('models') or ''),re.I)
        else "연관규칙" if re.search(r"association rule|apriori|연관",str(d.get('models') or ''),re.I)
        else "기타")) for d in adj).most_common())
    dump(A, os.path.join(DER, "analysis.json"))

    L = []; a = L.append
    a("# 분석 결과 — 리뷰 본문 표·그림의 원자료\n")
    a(f"생성 자동 · `python tools/analyze_extraction.py` · 포함연구 원자료 `data/study_json/*.json` · 기계용 `results/derived/analysis.json`\n")
    a(f"대상: ML 적용 {A['n_include']}편 (전문 근거 {A['n_fulltext']}편) · ML 인접 {A['n_adjacent']}편\n")
    def tbl(title, d, c1="값", c2="편수"):
        a(f"### {title}\n"); a(f"| {c1} | {c2} |"); a("|---|---:|")
        for k, v in d.items(): a(f"| {k} | {v} |")
        a("")
    tbl("연도별 출판", A["year"], "연도")
    tbl("결과변수 영역", A["category"])
    tbl("과제 유형", A["task"])
    tbl("KNHANES 역할", A["knhanes_role"])
    tbl("자료층 사용 (중복 허용)", A["data_layer"], "자료층")
    tbl("조사 연차별 사용 빈도", A["wave_year_usage"], "조사연도")
    tbl("사용 연차 폭", A["wave_span"], "폭")
    tbl("조사연도 범위 — 단년 / 같은 기수 / 기수 넘음", A["wave_scope"], "구분")
    tbl("사용한 기수 수", A["wave_n_cycles"], "기수 수")
    a("KNHANES 는 기수마다 표본추출틀을 새로 설계하므로, 기수를 넘어 자료를 합치면 통합 가중치 산출이 필요해진다.\n"
      "아래 표는 그 필요가 실제로 충족되었는지를 PROBAST 확장 신호질문 S3 판정과 대조한 것이다.\n")
    a("### 조사연도 범위 × 통합 가중치 기술(S3)\n")
    lv = sorted({k for v in A["wave_scope_x_s3"].values() for k in v},
                key=lambda x: ["Y", "PY", "PN", "N", "NI", "NA", "미평가"].index(x)
                if x in ["Y", "PY", "PN", "N", "NI", "NA", "미평가"] else 99)
    a("| 구분 | " + " | ".join(lv) + " | 계 |")
    a("|---|" + "---:|" * (len(lv) + 1))
    for k, v in A["wave_scope_x_s3"].items():
        a(f"| {k} | " + " | ".join(str(v.get(x, 0)) for x in lv) + f" | {sum(v.values())} |")
    a("")
    a("### 조사연도 범위 × 설문 가중치 처리\n")
    lw = ["학습에 반영", "일부(기술통계·회귀만)", "미적용 명시", "언급 없음"]
    a("| 구분 | " + " | ".join(lw) + " | 계 |")
    a("|---|" + "---:|" * (len(lw) + 1))
    for k, v in A["wave_scope_x_weights"].items():
        a(f"| {k} | " + " | ".join(str(v.get(x, 0)) for x in lw) + f" | {sum(v.values())} |")
    a("")
    tbl("표본 크기 구간", A["n_final"]["bins"], "최종 n")
    a(f"최종 n: 중앙값 {A['n_final']['median']:,} · 사분위 {A['n_final']['q1']:,}–{A['n_final']['q3']:,} · 범위 {A['n_final']['min']:,}–{A['n_final']['max']:,} ({A['n_final']['count']}편)\n")
    tbl("설문 가중치 처리", A["weights"])
    tbl("결측 처리", A["missing"])
    tbl("클래스 불균형 처리", A["imbalance"])
    tbl("검증 방식 (중복 허용)", A["validation"])
    tbl("해석 기법", A["interp"])
    tbl("코드·데이터 공개", A["code"])
    tbl("비교에 쓰인 모델 (논문 수)", A["models_compared"], "모델")
    tbl("최고 성능 모델", A["best_model"], "모델")
    tbl("한 논문이 비교한 모델 수", A["n_models_per_paper"], "모델 수")
    a("### 결과변수 영역 × 가중치 처리\n")
    ws = ["학습에 반영", "일부(기술통계·회귀만)", "미적용 명시", "언급 없음"]
    a("| 영역 | " + " | ".join(ws) + " | 계 |"); a("|---" * (len(ws) + 2) + "|")
    for k, v in A["category_x_weights"].items():
        a(f"| {k} | " + " | ".join(str(v.get(w, 0)) for w in ws) + f" | {sum(v.values())} |")
    a("")
    a("### 시기별 방법론 관행 추이\n")
    ks = ["n", "학습에 반영", "언급 없음", "완전제거", "미기재", "외부검증", "해석기법 사용", "코드 공개"]
    a("| 시기 | " + " | ".join(ks) + " |"); a("|---" * (len(ks) + 1) + "|")
    for p, v in A["period_trend"].items():
        a(f"| {p} | " + " | ".join(str(v.get(k, 0)) for k in ks) + " |")
    a("")
    tbl("성능 보고 깊이", A["metric_depth"], "보고 수준")
    tbl("변수중요도 유형 (중복 허용)", A["importance_kind"], "유형")
    tbl("사후 통계분석 (중복 허용)", A["posthoc"], "분석")
    a(f"사후 통계분석을 하나라도 수행: {A['n_any_posthoc']}/{A['n_include']} · 전혀 없음: {A['n_no_posthoc']}\n")
    tbl("모형 비교 방식", A["model_comparison"], "방식")
    tbl("ML 인접 75편의 방법", A["adjacent_method"], "방법")
    open(os.path.join(PROJ, "data", "ANALYSIS.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"  ANALYSIS.md · analysis.json — INCLUDE {A['n_include']} · ADJACENT {A['n_adjacent']}")


if __name__ == "__main__":
    main()
