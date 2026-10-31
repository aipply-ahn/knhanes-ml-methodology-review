"""원고의 수치가 results/derived/*.json 과 일치하는지 검증.

    python tools/verify_numbers.py [--ko]

각 검사는 (이름, 기대값, 정규식) 이며 정규식의 첫 그룹을 기대값과 비교한다.
재추출로 자료가 바뀔 때마다 반드시 돌린다. 원고 수치는 손으로 고치지 않고 여기서 잡아 고친다.
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, DER, load

A = load(os.path.join(DER, "analysis.json"))
B = load(os.path.join(DER, "probast.json"))
T = load(os.path.join(DER, "tripod_stats.json"))
ta, tf, S, D, ap = B["tripod_adherence"], B["tripod_adherence_full_text"], B["signalling"], B["domain"], B["applicability"]
V, W, M, I, C, MD, PH, L = (A["validation"], A["weights"], A["missing"], A["importance_kind"],
                            A["model_comparison"], A["metric_depth"], A["posthoc"], A["data_layer"])
NI, NF, NA_ = A["n_include"], A["n_fulltext"], A["n_adjacent"]

def s(q, k): return S[q].get(k, 0)

CHECKS = [
    ("포함 편수",        NI,  r"(\d+) studies met inclusion"),
    ("전문 확보",        NF,  r"full text obtained for (\d+)"),
    ("인접",            NA_, r"and (\d+) used ML-adjacent methods only\. Annual"),
    ("분류 과제",        A["task"]["classification"], r"classification \(n=(\d+)\), with regression"),
    ("검진 자료층",      L["검진(검사·계측)"], r"examination data by (\d+) studies"),
    ("설문 자료층",      L["설문(건강행태·사회경제)"], r"questionnaire data by (\d+), but dietary"),
    ("영양 자료층",      L["영양(식이)"], r"dietary data by only (\d+),"),
    ("결측 완전제거",     M["완전제거"], r"[Cc]omplete-case analysis was used by (\d+) studies"),
    ("결측 미기재",      M["미기재"], r"handling was unreported by (\d+)"),
    ("SMOTE",          A["imbalance"]["SMOTE/ADASYN 계열"], r"SMOTE or ADASYN was applied by (\d+) studies"),
    ("단일 분할",        V["단일 분할"], r"single train--test split in (\d+)"),
    ("교차검증",         V["교차검증"], r"cross-validation in (\d+)"),
    ("외부검증",         V["외부검증"], r"external\s+validation in (\d+)"),
    ("가중치 학습반영",   W["학습에 반영"], r"survey weights entered model\s+fitting in (\w+)"),
    ("가중치 언급없음",   W["언급 없음"], r"remaining (\d+) studies did not mention weights"),
    ("판별력",          A["n_discrimination"], r"Discrimination was reported by (\d+) studies"),
    ("보정",            A["n_calibration"], r"but calibration\s+by (\d+),"),
    ("성능 미보고",      MD["성능 미보고"], r"and (\d+) reported no\s+performance\s+metric"),
    ("사후분석 있음",     A["n_any_posthoc"], r"(\d+) of \d+ studies performed at least one"),
    ("사후분석 없음",     A["n_no_posthoc"], r"(\d+) performed none"),
    ("SHAP",           I["SHAP"], r"SHAP was used by (\d+) studies"),
    ("모델내장 FI",      I["모델 내장 중요도(FI)"], r"such as Gini or gain by\s+(\d+)\."),
    ("순열 중요도",      I["순열 중요도(PI)"], r"was used by (\d+)\."),
    ("모형비교 통계",     C["복수 모형 + 통계적 뒷받침"], r"\(Figure 5F\), (\d+) studies compared several model"),
    ("모형비교 나열만",   C["복수 모형, 수치 나열만"], r"(\d+) compared several model\s+families but reported only point"),
    ("단일 모형",        C["단일 모형(비교 없음)"], r"(\d+) fitted a single model"),
    ("코드 공개",        A["code"]["공개"], r"Code or data were shared by (\d+) studies"),
    ("코드 요청시",      A["code"]["요청 시 제공"], r"offered on request by (\d+),"),
    ("코드 미공개",      A["code"]["미공개/미기재"], r"neither shared\s+nor mentioned by (\d+)\."),
    ("적용가능성 낮음",   ap["low"], r"low concern in (\d+) studies"),
    ("적용가능성 높음",   ap["high"], r"high concern in (\d+), and unclear"),
    ("적용가능성 불명",   ap["unclear"], r"and unclear in (\d+)\."),
    ("D1 낮음",         D["D1"]["low"], r"participants domain was low risk in (\d+) studies"),
    ("D1 높음",         D["D1"]["high"], r"low risk in \d+ studies, high in (\d+),"),
    ("D1 불명",         D["D1"]["unclear"], r"high in \d+, and unclear in (\d+)\."),
    ("D2 높음",         D["D2"]["high"], r"predictors domain was high risk in (\d+) studies"),
    ("D3 높음",         D["D3"]["high"], r"and the outcome domain in (\d+),"),
    ("4.5 N",          s("D4.4.5", "N"), r"item 4\.5: No in (\d+)"),
    ("4.5 PN",         s("D4.4.5", "PN"), r"item 4\.5: No in \d+\s+studies, Probably No in (\d+)\)"),
    ("4.6 PN",         s("D4.4.6", "PN"), r"item 4\.6:\s+Probably No in (\d+),"),
    ("4.6 N",          s("D4.4.6", "N"), r"item 4\.6:\s+Probably No in \d+, No in (\d+),"),
    ("4.4 부적절",      s("D4.4.4","N")+s("D4.4.4","PN"), r"probably inappropriate in (\d+) studies"),
    ("4.4 NI",         s("D4.4.4", "NI"), r"and was unreported in (\d+)\."),
    ("4.7 미흡",        s("D4.4.7","N")+s("D4.4.7","PN"), r"inadequately addressed in (\d+) studies"),
    ("S1 N",           s("D4.S1", "N"), r"omission justified in (\d+)\s+studies"),
    ("S1 NI",          s("D4.S1", "NI"), r"with (\d+) providing no information"),
    ("S2 N",           s("D4.S2", "N"), r"performance estimation in (\d+)\s+studies"),
    # 통합 여부가 확인된 연구만 분모 — S3 NI 5편(조사연차 자체가 미기재)은 제외한다
    ("S3 적용대상",     sum(n for k_, v_ in A["wave_scope_x_s3"].items() if k_ != "단년"
                          for c_, n in v_.items() if c_ != "NA"),
                       r"Among the (\d+) studies that combined survey years into one"),
    ("S3 Y",           s("D4.S3", "Y"), r"weight construction was described in (\d+) "),
    ("TRIPOD 목적",     ta["background_objective"]["yes"], r"reporting the objective \((\d+)/"),
    ("TRIPOD 자료원",   ta["data_source"]["yes"], r"the data source \((\d+)/"),
    ("TRIPOD 결측",     ta["missing_data"]["yes"], r"missing data \((\d+)/"),
    ("TRIPOD 초록",     ta["abstract_structured"]["yes"], r"a structured abstract \((\d+)/"),
    ("TRIPOD 적격기준",  ta["participants_eligibility"]["yes"], r"eligibility criteria \((\d+)/"),
    ("TRIPOD 표본크기",  ta["sample_size_justification"]["yes"], r"sample size\s+justification \((\d+)/"),
    ("TRIPOD 코드",     ta["code_availability"]["yes"], r"code availability \((\d+)/"),
    ("TRIPOD 모형공개",  ta["model_availability"]["yes"], r"permits use or replication \((\d+)/"),
    ("초록만",          NI - NF, r"depressed by the (\d+) studies for which only"),
    ("전문 표본크기",    tf["sample_size_justification"]["yes"], r"sample size was justified in (\d+) of"),
    ("전문 코드",        tf["code_availability"]["yes"], r"code was available\s+in (\d+),"),
    ("전문 모형",        tf["model_availability"]["yes"], r"and the final model in (\d+)\."),
    ("TRIPOD 일반 중앙값", round(T["general"]["median_pct"]), r"adherence was (\d+)\\% for general"),
]
src = open(os.path.join(PROJ, "manuscript/submission/main.tex")).read()
bad = 0
for name, want, pat in CHECKS:
    m = re.search(pat, src)
    got = m.group(1) if m else None
    ok = got is not None and str(want) == got
    if not ok:
        bad += 1
        print(f"  !! {name:18s} 자료 {str(want):>6s}  원고 {str(got):>6s}")
print(f"\n  검사 {len(CHECKS)}건 · 불일치 {bad}건" + ("  — 모두 일치" if not bad else ""))

# ── 한글본 검증 (python tools/verify_numbers.py --ko) ──────────────────────────
KO_CHECKS = [
    ("포함 편수",     NI, r"(\d+)편이 포함 기준을 충족"),
    ("전문 확보",     NF, r"전문 확보\s*\n?(\d+)편\)"),
    ("인접",         NA_, r"(\d+)편은 머신러닝 인접"),
    ("분류 과제",     A["task"]["classification"], r"분류가 (\d+)편으로 압도적"),
    ("검진 자료층",   L["검진(검사·계측)"], r"검진 자료는 (\d+)편"),
    ("설문 자료층",   L["설문(건강행태·사회경제)"], r"검진 자료는 \d+편, 설문\s*\n?자료는 (\d+)편"),
    ("결측 완전제거",  M["완전제거"], r"(\d+)편이 완전제거를 사용했고"),
    ("결측 미기재",   M["미기재"], r"완전제거를 사용했고 (\d+)편은 처리 방법"),
    ("단일 분할",     V["단일 분할"], r"검증은 단일 훈련·시험 분할 (\d+)편"),
    ("교차검증",      V["교차검증"], r"검증은 단일 훈련·시험 분할 \d+편, 교차검증 (\d+)편"),
    ("외부검증",      V["외부검증"], r"교차검증 \d+편, 외부검증 (\d+)편이었고"),
    ("판별력",       A["n_discrimination"], r"판별력은 (\d+)편이 보고했으나"),
    ("보정",         A["n_calibration"], r"보정은 (\d+)편이었고"),
    ("SHAP",        I["SHAP"], r"SHAP을 (\d+)편이"),
    ("모델내장 FI",   I["모델 내장 중요도(FI)"], r"모형 내장 중요도를 (\d+)편이"),
    ("사후분석 있음",  A["n_any_posthoc"], r"\d+편 중 (\d+)편이 하나 이상을"),
    ("사후분석 없음",  A["n_no_posthoc"], r"(\d+)편은 사후 통계분석을 전혀"),
    ("모형비교 통계",  C["복수 모형 + 통계적 뒷받침"], r"그림 5F\) (\d+)편은"),
    ("가중치 학습반영", W["학습에 반영"], r"모형 적합에 반영한 연구는 (\d+)편"),
    ("가중치 언급없음", W["언급 없음"], r"나머지 (\d+)편은 분석에서 가중치"),
    ("적용가능성 낮음", ap["low"], r"적용가능성은 (\d+)편이 낮은 우려"),
    ("D1 낮음",      D["D1"]["low"], r"참여자 영역은 (\d+)편이 낮음"),
    ("D2 높음",      D["D2"]["high"], r"예측변수 영역은 (\d+)편"),
    ("S1 N",        s("D4.S1", "N"), r"근거를 밝히지도 않은 연구가 (\d+)편"),
    ("TRIPOD 결측",   ta["missing_data"]["yes"], r"결측 자료\s*\n?보고\((\d+)/"),
    ("초록만",        NI - NF, r"초록만 확보한 (\d+)편 때문에"),
    ("성능 미보고",    MD["성능 미보고"], r"(\d+)편은 성능 지표를 전혀 보고하지"),
    ("판별력+분류지표", MD["판별력 + 분류지표"], r"그림 5D\)\. (\d+)편은 판별력과 함께"),
]
if "--ko" in sys.argv:
    src = open(os.path.join(PROJ, "manuscript/submission/main_ko.tex")).read()
    bad = 0
    for name, want, pat in KO_CHECKS:
        m = re.search(pat, src); got = m.group(1) if m else None
        if got is None or str(want) != got:
            bad += 1; print(f"  !! {name:16s} 자료 {str(want):>6s}  원고 {str(got):>6s}")
    print(f"\n  한글 검사 {len(KO_CHECKS)}건 · 불일치 {bad}건" + ("  — 모두 일치" if not bad else ""))

# ── 조사연도 범위 축 (2026-09-04 추가) ─────────────────────────────────────────
SCOPE = A["wave_scope"]; XS = A["wave_scope_x_s3"]
_pooled = sum(n for k, v in XS.items() if k != "단년" for c, n in v.items() if c != "NA")
_p1 = sum(n for c, n in XS["복수년 · 같은 기수"].items() if c != "NA")
_p2 = sum(n for c, n in XS["복수년 · 기수 넘음"].items() if c != "NA")
SCOPE_CHECKS = [
    ("단년",        SCOPE["단년"], r"\(Figure 8A\)\. (\d+) studies used a single survey year"),
    ("같은 기수",    SCOPE["복수년 · 같은 기수"], r"single survey year, (\d+) combined"),
    ("기수 넘음",    SCOPE["복수년 · 기수 넘음"], r"and (\d+) combined years across two or more"),
    ("연도 불명",    SCOPE["연도 불명"], r"could not be determined for (\d+)\."),
    ("2기수",       A["wave_n_cycles"]["2"], r"cycle boundaries, (\d+) spanned two cycles"),
    ("3기수",       A["wave_n_cycles"]["3"], r"spanned two cycles, (\d+) spanned three"),
    ("통합 분모",    _pooled, r"Of the (\d+) studies\nthat did combine survey years"),
    ("같은기수 통합",  _p1, r"none of the (\d+) pooling"),
    ("기수넘음 통합",  _p2, r"of the (\d+) pooling across cycles"),
    ("S3 Y",       XS["복수년 · 기수 넘음"].get("Y", 0), r"within one cycle and (\d+) of the \d+ pooling across"),
]
if "--scope" in sys.argv or "--all" in sys.argv:
    src = open(os.path.join(PROJ, "manuscript/submission/main.tex")).read()
    bad = 0
    for name, want, pat in SCOPE_CHECKS:
        m = re.search(pat, src); got = m.group(1) if m else None
        if got is None or str(want) != got:
            bad += 1; print(f"  !! {name:14s} 자료 {str(want):>6s}  원고 {str(got):>6s}")
    print(f"\n  범위축 검사 {len(SCOPE_CHECKS)}건 · 불일치 {bad}건" + ("  — 모두 일치" if not bad else ""))
