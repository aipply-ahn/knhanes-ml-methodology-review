"""v12 checklist (author 2026-10-25): TRIPOD+AI items and components against KNHANES checklist items, split so that each
row is one concrete piece of information needed to reproduce or interpret the analysis. One source for Table 1, the
per-study scores and Figure 5. Note: K retained, R refined, RS refined (KNHANES-specific), N new, NS new (KNHANES).
repro: needed to reproduce the analysis. met/app: scoring functions (None = not coded, not scored).
Run: python tools/checklist_v12.py  -> results/derived/checklist_v12_scores.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

NRSET = {"NR", "NA", "UNC", "UNCLEAR", "", "None", None, "NOT_PROVIDED_OR_NOT_REPORTED", "INSUFFICIENT"}
TRIPOD = [("제목", "Title"), ("초록", "Abstract"), ("목적과 의도한 용도", "Objective and intended use"),
          ("자료원·설계·기간", "Data source, design and dates"), ("선정 기준과 참여자 선택", "Eligibility and participant selection"),
          ("결과변수 정의·시점·출처", "Outcome definition, timing and source"), ("설명변수 정의·시점", "Predictor definition and timing"),
          ("표본과 사건 수", "Sample and event counts"), ("표본 크기 근거", "Sample-size rationale"), ("결측값 처리", "Missing-data handling"),
          ("전처리·변수선택·모형 개발", "Preprocessing, selection and model development"), ("하이퍼파라미터·튜닝", "Hyperparameters and tuning"),
          ("내부 검증·재표집", "Internal validation or resampling"), ("평가자료·지표·임계값", "Evaluation data, measures and threshold"),
          ("참여자 흐름과 특성", "Participant flow and characteristics"), ("성능 추정과 불확실성", "Performance estimates and uncertainty"),
          ("재사용 가능한 최종 모형", "Reusable final model"), ("한계와 일반화", "Limitations and generalisability"),
          ("등록·자료·코드 공개", "Registration, data and code availability")]


def _ctx():
    import openpyxl
    import make_streamlined_figures as ms, claim_evidence_analysis as ce
    wb = openpyxl.load_workbook(ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx", read_only=True)
    ws = wb[wb.sheetnames[0]]; it = ws.iter_rows(values_only=True); hdr = next(it)
    rows = {r[0]: dict(zip(hdr, r)) for r in it if r and r[8] == "Core classification"}
    return ms, ce.CORE, rows


def build(ms):
    f = lambda d, k: ms.first(d, k)
    def _ok(v):
        if isinstance(v, list):
            return any(_ok(x) for x in v)
        return v not in NRSET and not str(v).startswith(("Not reported", "NR"))
    rep = lambda k: (lambda d, r: _ok(f(d, k)))
    has = lambda k, vals: (lambda d, r: ms.has(d, k, vals))
    yes = lambda col: (lambda d, r: r[col] == "Yes")
    ALL = lambda d, r: True
    rank = lambda d, r: r["Importance ranking produced"] == "Yes"
    num = lambda x: str(x).replace(".", "", 1).isdigit()
    # (tripod no or None, component ko, en, item ko, en, note, repro, met, app)
    I = [
     (1, "예측·모형·ML 연구 표시", "Identifies a prediction, model or ML study", None, None, "K", False, None, None),
     (2, "목적", "Objective", None, None, "K", False, None, None), (2, "자료원", "Data source", None, None, "K", False, None, None),
     (2, "모형", "Model(s)", None, None, "K", False, None, None), (2, "주요 결과", "Principal results", None, None, "K", False, None, None),
     (3, "목적", "Objective", None, None, "K", False, None, None), (3, "의도한 용도", "Intended use", None, None, "K", False, None, None),
     (3, "목표 모집단", "Target population", None, None, "K", True, rep("SUR02"), ALL),
     (3, "", "", "분석 과제(현재 상태 분류인지 미래 사건 예측인지)", "Analytic task (classifying a current state or predicting a future event)", "RS", False, None, None),
     (4, "자료원", "Data source", "사용한 조사 구성요소(건강설문, 검진, 혈액·소변 검사, 영양조사)", "Survey components used (interview, examination, laboratory, nutrition)", "RS", True, rep("DAT14"), ALL),
     (4, "", "", "외부 자료 연계 여부와 방법", "Linkage to external data and how", "RS", True, lambda d, r: f(d, "DAT15") in ("Y", "N"), ALL),
     (4, "연구 설계", "Study design", None, None, "K", False, None, None), (4, "장소", "Setting", None, None, "K", False, None, None),
     (4, "기간", "Dates", "분석한 조사연도 목록", "Exact survey years analysed", "RS", True, lambda d, r: f(d, "DAT18") == "R", ALL),
     (4, "", "", "조사연도 결합 방식(한 해, 한 주기, 여러 주기)", "How survey years were combined (one year, one cycle, several cycles)", "RS", True, lambda d, r: r["Combining survey years"] != "Unclear", ALL),
     (5, "선정 기준", "Eligibility criteria", "분석 표본의 연령 범위", "Age range of the analytic sample", "R", True,
      lambda d, r: num(f(d, "POP03")) or num(f(d, "POP04")), ALL),
     (5, "", "", "분석 표본의 성별", "Sex of the analytic sample", "R", True, lambda d, r: f(d, "POP05") not in ("NR", "UNC"), ALL),
     (5, "", "", "그 밖의 포함 조건(조사 구성요소 참여, 응답 완료, 질환·건강상태 등)", "Other inclusion conditions (participation in survey components, complete responses, conditions)", "R", True, rep("POP06"), ALL),
     (5, "선택 과정", "Selection process", "표본 선택 단계와 단계별 제외 인원", "Sample-selection steps and numbers excluded at each step", "R", True, rep("POP11"), ALL),
     (5, "제외", "Exclusions", "제외 조건(질환, 임신, 약물 복용, 결측 등)", "Exclusion conditions (conditions, pregnancy, medication, missing data)", "R", True, rep("POP07"), ALL),
     (6, "정의", "Definition", "결과변수의 변수명·코드(재구성 가능한 정의)", "Outcome variables and codes (rebuildable definition)", "R", True, lambda d, r: f(d, "OUT16") == "R2", ALL),
     (6, "", "", "목적변수 코딩 규칙(수식·기준값)", "Outcome coding rule (formula or cut-off)", "R", True, rep("OUT08"), ALL),
     (6, "", "", "범주화 기준의 근거", "Basis of the cut-off", "R", False, lambda d, r: f(d, "OUT12") not in ("NR", "UNEXPLAINED"), lambda d, r: f(d, "OUT11") == "Y"),
     (6, "", "", "결과 정의에 쓴 변수와 설명변수의 중복 여부", "Overlap between variables defining the outcome and the predictors", "RS", False, None, None),
     (6, "측정 시점", "Assessment timing", "설명변수와 같은 조사에서 측정했는지", "Measured in the same survey as the predictors or not", "RS", False, lambda d, r: f(d, "OUT10") != "UNC", ALL),
     (6, "출처·평가자", "Source or assessor", "결과변수 출처", "Outcome source", "K", True, lambda d, r: r["Outcome source"] != "Not reported", ALL),
     (7, "정의", "Definition", "후보 설명변수 전체 목록과 코딩", "Full list and coding of candidate predictors", "R", True, lambda d, r: f(d, "PRD13") == "R2", ALL),
     (7, "", "", "후보 설명변수 수", "Number of candidate predictors", "R", True, rep("PRD02"), ALL),
     (7, "", "", "변수 선택·필터링 단계와 단계별 변수 수", "Variable selection and filtering steps with the number of variables at each step", "R", True, None, None),
     (7, "", "", "최종 설명변수 수", "Final number of predictors", "R", True, rep("PRD04"), ALL),
     (7, "", "", "모형에 투입한 최종 설명변수 목록", "List of predictors entered into the final model", "R", True, None, None),
     (7, "측정 시점", "Measurement timing", None, None, "K", False, None, None),
     (7, "사용 시점의 가용성", "Availability at intended use", None, None, "K", False, None, None),
     (8, "분석 표본 수", "Analysed sample size", "최종 분석 표본 수", "Final analytic sample size", "K", True, rep("POP09"), ALL),
     (8, "사건·비사건 또는 범주별 수", "Event and non-event or class counts", "목적변수 라벨별 수", "Number in each outcome class", "K", True, rep("POP12"), ALL),
     (8, "", "", "목적변수 라벨별 비율", "Proportion in each outcome class", "R", True, rep("POP14"), ALL),
     (9, "표본 크기의 근거 또는 계산", "Sample-size rationale or calculation", None, None, "K", False, None, None),
     (10, "결측 규모", "Amount of missingness", "변수별 결측 규모", "Missingness by variable", "R", True, rep("PRE04"), ALL),
     (10, "처리 방법", "Handling method", "결측값 처리·대체 방법", "Missing-value handling or imputation method", "K", True, rep("PRE01"), ALL),
     (10, "", "", "변수별 결측 처리 규칙(제외 또는 대체)", "Variable-specific rules for exclusion or imputation", "R", True, rep("PRE03"), ALL),
     (10, "", "", "해당없음(8888)·모름(9999) 등 특수 응답 코드의 처리", "Handling of special response codes such as not applicable (8888) and don't know (9999)", "RS", True, None, None),
     (10, "분석 단계", "Analysis stage", "자료 의존 결측값 처리의 수행 시점(학습자료 안)", "Timing of data-dependent handling (within the training data)", "R", True,
      lambda d, r: r["Missing-value handling timing"] == "Within the training data", lambda d, r: r["Missing-value handling timing"] != "Not applied"),
     (11, "전처리", "Preprocessing", "전처리 방법(척도화, 부호화 등)", "Preprocessing methods (scaling, encoding and similar)", "R", True, rep("PRE12"), lambda d, r: f(d, "PRE12") != "NA"),
     (11, "", "", "모든 자료 의존 전처리를 학습자료 안에서 수행", "All data-dependent preprocessing within the training data", "R", True,
      lambda d, r: str(r["Preprocessing over all applied steps"]).startswith("All within"), lambda d, r: r["Preprocessing over all applied steps"] != "No data-dependent step"),
     (11, "", "", "클래스 재균형 방법과 수행 시점(학습자료 안)", "Class rebalancing method and timing (within the training data)", "R", True,
      lambda d, r: f(d, "IMB03") in ("TRAIN", "WITHIN"), lambda d, r: f(d, "IMB01") != "NONE"),
     (11, "변수선택", "Variable selection", "자료 기반 변수선택 방법과 수행 시점(학습자료 안)", "Data-driven selection method and timing (within the training data)", "R", True,
      lambda d, r: f(d, "PRE13") == "TRAIN", lambda d, r: f(d, "PRE11") == "USED"),
     (11, "모형 개발", "Model development", "적합한 알고리즘 목록", "Algorithms fitted", "R", True, rep("MOD02"), ALL),
     (11, "", "", "소프트웨어·패키지·버전", "Software, packages and versions", "R", True, rep("MOD09"), ALL),
     (11, "", "", "난수 시드", "Random seed", "R", True, rep("MOD10"), ALL),
     (12, "하이퍼파라미터", "Hyperparameters", "최종 하이퍼파라미터 값", "Final hyperparameter values", "R", True, rep("MOD06"), ALL),
     (12, "튜닝 방법", "Tuning method", None, None, "K", True, rep("MOD07"), lambda d, r: f(d, "MOD12") != "NOT_USED"),
     (12, "", "", "탐색 공간", "Search space", "R", True, rep("MOD08"), lambda d, r: f(d, "MOD12") == "USED"),
     (12, "튜닝과 평가의 분리", "Tuning/evaluation separation", "조율을 최종 평가와 분리", "Tuning kept apart from the final evaluation", "K", True, yes("Tuning kept apart from the final evaluation"), ALL),
     (13, "내부 검증 방법", "Internal-validation method", "학습·시험 분할 또는 교차검증", "Train--test split or cross-validation", "K", True, lambda d, r: ms.has(d, "VAL02", {"SPLIT", "CV"}), ALL),
     (13, "재표집 세부", "Resampling details", "분할 비율", "Split proportions", "R", True, rep("VAL03"), lambda d, r: ms.has(d, "VAL02", {"SPLIT"})),
     (13, "", "", "교차검증 겹 수", "Number of folds", "R", True, rep("VAL04"), lambda d, r: ms.has(d, "VAL02", {"CV"})),
     (13, "", "", "반복 횟수", "Number of repetitions", "R", True, rep("VAL05"), lambda d, r: f(d, "VAL05") != "NA"),
     (13, "개발 단계의 중첩", "Nesting of development steps", None, None, "K", True, None, None),
     (14, "평가자료", "Evaluation dataset", "개발자료 밖 검증(이후 조사 기간, 외부 자료)", "Validation beyond the development data (later survey period, external data)", "RS", False,
      lambda d, r: ms.has(d, "VAL02", {"TEMPORAL", "EXTERNAL"}), ALL),
     (14, "성능 지표", "Performance metrics", "AUROC", "AUROC", "K", True, yes("AUROC reported"), ALL),
     (14, "", "", "보정도", "Calibration", "R", False, yes("Calibration reported"), ALL),
     (14, "임계값", "Threshold", "판단 임계값", "Decision threshold", "K", True, yes("Decision threshold reported"), ALL),
     (14, "", "", "임계값 선택 방법", "Threshold selection method", "R", True, rep("THR01"), lambda d, r: f(d, "THR01") != "NA"),
     (14, "", "", "임계값을 최종 평가자료 없이 선택", "Threshold chosen without the final evaluation data", "R", False,
      yes("Threshold chosen without the final evaluation data"), lambda d, r: r["Decision threshold reported"] == "Yes"),
     (15, "참여자 흐름", "Participant flow", None, None, "K", True, None, None), (15, "제외", "Exclusions", None, None, "K", False, None, None),
     (15, "분석 참여자의 특성", "Characteristics of analysed participants", None, None, "K", False, None, None),
     (16, "성능 추정치", "Performance estimate", None, None, "K", True, None, None),
     (16, "불확실성", "Uncertainty", "성능 신뢰구간", "Confidence interval for performance", "K", False, yes("Confidence interval reported"), ALL),
     (17, "완전한 모형 명세", "Complete model specification", None, None, "K", True, lambda d, r: f(d, "MOD14") == "USED", ALL),
     (17, "사용 안내", "Use instructions", None, None, "K", False, None, None),
     (18, "한계", "Limitations", None, None, "K", False, None, None), (18, "일반화 가능성", "Generalisability", None, None, "K", False, None, None),
     (18, "적용 가능성", "Applicability", None, None, "K", False, None, None),
     (19, "등록·프로토콜", "Registration or protocol", None, None, "K", False, None, None),
     (19, "자료 공개", "Data availability", None, None, "K", True, None, None),
     (19, "코드·모형 공개", "Code or model availability", "분석 코드 공개", "Analysis code shared", "K", True, lambda d, r: f(d, "MOD15") == "USED", ALL),
     ("survey", "", "", "표본가중치 사용 여부", "Whether sampling weights were used", "NS", True, lambda d, r: f(d, "SUR06") in ("USED", "NOT_USED"), ALL),
     ("survey", "", "", "사용한 가중치 변수", "Weight variable used", "NS", True, None, None),
     ("survey", "", "", "통합 연도 가중치 산출 방식", "Construction of combined-year weights", "NS", True, lambda d, r: f(d, "DAT11") == "R", lambda d, r: f(d, "DAT11") != "NA"),
     ("survey", "", "", "모형 적합의 조사가중치", "Survey weights in model fitting", "NS", False, lambda d, r: f(d, "SUR06") == "USED", ALL),
     ("survey", "", "", "성능 평가의 조사가중치", "Survey weights in performance evaluation", "NS", False, lambda d, r: f(d, "SUR07") == "USED", ALL),
     ("survey", "", "", "분산 추정의 층·PSU", "Strata or PSUs in variance estimation", "NS", False, yes("Strata or PSUs in variance estimation"), ALL),
     ("importance", "", "", "중요도 방법", "Importance method", "N", True, lambda d, r: _ok(f(d, "VI02")), rank),
     ("importance", "", "", "중요도를 계산한 모형과 자료 구간", "Model and data partition used for importance", "N", True, rep("VI04"), rank),
     ("importance", "", "", "상위 변수 선정 규칙 또는 전체 순위", "Rule for the top variables or full ranking", "N", True, lambda d, r: _ok(f(d, "VI08")), rank),
     ("importance", "", "", "순위 안정성 점검(재표집, 조사 기수, 하위집단)", "Ranking stability check (resamples, survey cycles, subgroups)", "NS", False, yes("Ranking stability checked"), rank),
     ("importance", "", "", "중요도 집계의 조사가중치", "Survey weights in importance aggregation", "NS", False, None, None),
     ("importance", "", "", "해석 범위(모형 작동의 기술이며 모집단 연관·인과가 아님)", "Scope of interpretation (model behaviour, not population association or causation)", "N", False, None, None),
     ("after", "", "", "변수를 넘기는 규칙의 사전 지정", "Prespecified rule for carrying variables forward", "N", False, None, None),
     ("after", "", "", "축소 집합 선택을 학습자료 안에서 수행", "Reduced-set selection within the training data", "N", True, None, None),
     ("after", "", "", "모집단 연관성은 조사가중 회귀로 추정", "Population associations by survey-weighted regression", "NS", False, None, None),
    ]
    return I


GROUPS = {"survey": ("조사설계", "Survey design"), "importance": ("변수중요도", "Variable importance"), "after": ("순위 이후 분석", "Analyses after the ranking")}

if __name__ == "__main__":
    ms, CORE, rows = _ctx()
    I = build(ms)
    out = {"items": [], "studies": {}}
    for k, it in enumerate(I):
        out["items"].append({"idx": k, "tripod": it[0], "item_en": it[4] or it[2], "note": it[5], "repro": it[6], "scored": it[7] is not None})
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; rec = {}
        for k, it in enumerate(I):
            if it[7] is None:
                continue
            if it[8](d, r):
                rec[k] = bool(it[7](d, r))
        tri = {i: r[[h for h in r if str(h).startswith(f"Reporting {i:02d}:")][0]] for i in range(1, 20)}
        out["studies"][sid] = {"items": rec, "tripod": tri}
    json.dump(out, open(ROOT / "results/derived/checklist_v12_scores.json", "w"), indent=1)
    S = out["studies"]
    for k, it in enumerate(I):
        if it[7] is None:
            continue
        v = [S[s]["items"][k] for s in S if k in S[s]["items"]]
        print(it[0], (it[4] or it[2])[:45], f"{sum(v)}/{len(v)}", "repro" if it[6] else "")
