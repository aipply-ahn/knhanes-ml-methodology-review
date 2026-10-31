"""v14 core checklist (author 2026-10-28): about 35 binary items at an intermediate level of abstraction. Each item is one
reporting requirement judged met (1), not met (0) or not applicable (NA); information that serves the same purpose is
bundled into one item, separate analytic acts are separate items. Items judge reporting, not practice (for survey weights:
whether and how they were applied, or why not). Judgements use only the components coded in this review; items whose
components were not coded are marked uncoded and not scored. The detailed specification (v13) is kept as Appendix Table A2.
Run: python tools/checklist_v14.py -> results/derived/checklist_v14_scores.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from checklist_v12 import TRIPOD, NRSET, _ctx  # noqa: E402

STAGE = {"D": ("자료", "Data"), "M": ("모형", "Model"), "I": ("중요도", "Importance"), "R": ("보고·해석", "Reporting")}
TYPE = {"R": ("구체화", "Specified"), "RS": ("구체화(특화)", "Specified (KNHANES)"), "N": ("신설", "New"), "NS": ("신설(특화)", "New (KNHANES)")}
GROUPS = {"importance": ("변수중요도", "Variable importance"), "after": ("순위 이후 분석", "Analyses after the ranking")}


def build(ms):
    f = lambda d, k: ms.first(d, k)

    def ok(v):
        if isinstance(v, list):
            return any(ok(x) for x in v)
        return v not in NRSET and not str(v).startswith(("Not reported", "NR"))
    rep = lambda *ks: (lambda d, r: all(ok(f(d, k)) for k in ks))
    ALL = lambda d, r: True
    rank = lambda d, r: r["Importance ranking produced"] == "Yes"
    num = lambda x: str(x).replace(".", "", 1).isdigit()
    # (element, item ko, en, criterion ko, en, stage, type, met, app); met None = not coded
    return [
     (3, "분석 목적과 결과가 기술하는 대상", "Analytic purpose and the population the results describe",
      "분석 과제(현재 상태 분류인지 미래 사건 예측인지)와 결과가 기술하는 대상(분석 표본, 목표 모집단, 새 개인)을 밝힘",
      "States the analytic task (current state or future event) and whom the results describe (analytic sample, target population, new individuals)",
      "R", "RS", rep("SUR02"), ALL),
     (4, "조사 구성요소와 분석 조사연도", "Survey components and survey years",
      "사용한 조사 구성요소, 분석한 조사연도 목록, 원자료 파일·공개 버전을 확인할 수 있음",
      "The survey components, the exact years analysed and the raw data files and release can be identified",
      "D", "RS", lambda d, r: ok(f(d, "DAT14")) and f(d, "DAT18") == "R", ALL),
     (4, "조사연도 결합과 연도 간 변수 조화", "Combining survey years and harmonising variables",
      "여러 해를 결합한 방식과 연도별 변수명·코드 변경의 조화 규칙을 보고함",
      "Reports how years were combined and how changes in variable names and codes across years were harmonised",
      "D", "RS", lambda d, r: r["Combining survey years"] != "Unclear", ALL),
     (4, "조사가중치의 식별과 구성", "Identification and construction of survey weights",
      "사용한 가중치 변수와 선택 근거(조사 구성요소, 조사연도, 분석 대상) 또는 쓰지 않은 근거, 여러 해 결합 시 가중치 조정 방법을 보고함",
      "Reports the weight variable and why it was chosen (component, years, analysed group), or why weights were not used, and how weights were adjusted when years were combined",
      "D", "RS", lambda d, r: f(d, "SUR06") in ("USED", "NOT_USED") and (f(d, "DAT11") != "NR" if f(d, "SUR06") == "USED" else True), ALL),
     (5, "표본 선정", "Sample selection",
      "연령·성별 등 포함·제외 조건과 그 적용 순서, 단계별 표본 수를 보고함",
      "Reports the inclusion and exclusion conditions (such as age and sex), the order in which they were applied and the sample size at each step",
      "D", "R", lambda d, r: (num(f(d, "POP03")) or num(f(d, "POP04"))) and ok(f(d, "POP06")) and ok(f(d, "POP11")), ALL),
     (6, "결과변수 재구성", "Rebuilding the outcome",
      "결과변수의 원자료 변수·코드와 생성·범주화 규칙(수식, 기준값)을 보고해 결과변수를 다시 만들 수 있음",
      "Reports the raw variables and codes and the derivation and categorisation rule (formula, cut-off), so the outcome can be rebuilt",
      "D", "R", lambda d, r: f(d, "OUT16") == "R2" and ok(f(d, "OUT08")), ALL),
     (6, "결과변수의 측정 시점", "Timing of the outcome",
      "결과변수가 설명변수와 같은 조사에서 측정되었는지, 이후 사건인지 확인할 수 있음",
      "Whether the outcome was measured in the same survey as the predictors or later can be determined",
      "D", "RS", lambda d, r: f(d, "OUT10") != "UNC", ALL),
     (6, "결과변수와 설명변수의 정의상 중복", "Overlap between outcome definition and predictors",
      "결과 정의에 쓴 원자료 변수가 설명변수에 포함되었는지와 그 처리 방법을 보고함",
      "Reports whether raw variables used to define the outcome were among the predictors and how this was handled",
      "D", "RS", None, None),
     (8, "결과변수의 분포", "Distribution of the outcome",
      "분석 표본의 결과변수 범주별 수와 비율을 보고함", "Reports the number and proportion in each outcome class in the analytic sample",
      "D", "R", rep("POP12", "POP14"), ALL),
     (7, "최종 입력변수와 코딩", "Final input variables and their coding",
      "모형에 투입한 설명변수 목록과 각 변수의 파생·코딩 규칙(연도별 대응 변수 포함)을 보고해 입력행렬을 다시 만들 수 있음",
      "Reports the predictors entered into the model and how each was derived and coded (including corresponding variables by year), so the input matrix can be rebuilt",
      "D", "R", lambda d, r: f(d, "PRD13") == "R2", ALL),
     (7, "변수 선택 과정", "Variable selection process",
      "후보 설명변수 수, 선택·필터링 단계, 최종 설명변수 수를 보고함", "Reports the number of candidate predictors, the selection and filtering steps and the final number of predictors",
      "D", "R", rep("PRD02", "PRD04"), ALL),
     (10, "결측값과 특수 응답 코드의 처리", "Missing values and special response codes",
      "결측 규모, 처리·대체 방법, 변수별 규칙, 특수 응답 코드(예: 해당없음 8888, 모름 9999)의 처리를 보고함",
      "Reports the amount of missingness, the handling or imputation method, variable-specific rules and the handling of special response codes (such as 8888, 9999)",
      "D", "RS", rep("PRE04", "PRE01", "PRE03"), ALL),
     (11, "자료 의존 전처리의 방법과 시점", "Methods and timing of data-dependent preprocessing",
      "결측 대체, 척도화, 변수선택 등 자료 의존 단계마다 방법과 자료 분할 전후의 수행 시점을 확인할 수 있음",
      "For each data-dependent step (imputation, scaling, selection), the method and whether it was done before or after the split can be determined",
      "M", "R", lambda d, r: r["Preprocessing over all applied steps"] != "Timing unclear", lambda d, r: r["Preprocessing over all applied steps"] != "No data-dependent step"),
     (11, "클래스 재균형", "Class rebalancing",
      "클래스 재균형의 방법과 수행 시점을 보고함", "Reports the rebalancing method and when it was applied",
      "M", "R", lambda d, r: f(d, "IMB03") not in ("ORDER_NR", "NA", "NR", "UNC"), lambda d, r: f(d, "IMB01") != "NONE"),
     (11, "알고리즘과 실행 환경", "Algorithms and software",
      "적합한 알고리즘과 소프트웨어·패키지·버전, 전처리·학습 파이프라인의 순서를 보고함",
      "Reports the algorithms fitted, the software, packages and versions and the order of the preprocessing and training pipeline",
      "M", "R", rep("MOD02", "MOD09"), ALL),
     (13, "자료 분할의 재현 정보", "Information to reproduce the data split",
      "난수 시드, 분할 비율·층화 또는 분할 인덱스를 보고해 같은 분할을 다시 만들 수 있음",
      "Reports the random seed and the split proportions and stratification, or the split indices, so the same split can be made",
      "M", "R", lambda d, r: ok(f(d, "MOD10")) and (ok(f(d, "VAL03")) if ms.has(d, "VAL02", {"SPLIT"}) else True), ALL),
     (13, "내부 검증 설계", "Internal-validation design",
      "학습·시험 분할 또는 교차검증의 방식과 겹 수, 반복 횟수를 보고함", "Reports the split or cross-validation scheme with the number of folds and repetitions",
      "M", "R", lambda d, r: ms.has(d, "VAL02", {"SPLIT", "CV"}) and (ok(f(d, "VAL04")) if ms.has(d, "VAL02", {"CV"}) else True) and (ok(f(d, "VAL03")) if ms.has(d, "VAL02", {"SPLIT"}) else True), ALL),
     (12, "튜닝 절차", "Tuning procedure",
      "튜닝 방법과 탐색 공간을 보고함", "Reports the tuning method and the search space",
      "M", "R", rep("MOD07", "MOD08"), lambda d, r: f(d, "MOD12") == "USED"),
     (12, "튜닝과 최종 평가의 분리", "Separation of tuning from the final evaluation",
      "모형 선택·튜닝·임계값 결정에 최종 평가자료를 썼는지 확인할 수 있음", "Whether the final evaluation data were used for model choice, tuning or thresholds can be determined",
      "M", "R", lambda d, r: r["Tuning kept apart from the final evaluation"] != "Not reported", ALL),
     (12, "최종 모형 설정", "Final model settings",
      "최종 모형과 그 하이퍼파라미터 값을 보고함", "Reports the final model and its hyperparameter values",
      "M", "R", rep("MOD06"), ALL),
     (17, "최종 모형 명세", "Final model specification",
      "새 자료에 적용할 수 있을 만큼 최종 모형(입력, 전처리, 모수 또는 저장된 모형, 임계값)을 명세함",
      "Specifies the final model fully enough to apply it to new data (inputs, preprocessing, parameters or saved model, threshold)",
      "M", "R", lambda d, r: f(d, "MOD14") == "USED", ALL),
     (19, "코드 공개", "Code availability", "분석 코드를 공개함", "Analysis code is available", "M", "R", lambda d, r: f(d, "MOD15") == "USED", ALL),
     (11, "모형 적합의 가중치", "Survey weights in model fitting",
      "모형 적합에서 가중치를 적용했는지와 그 방법(학습 알고리즘에 전달한 방식), 또는 쓰지 않은 근거를 보고함",
      "Reports whether and how weights were applied in model fitting (how they were passed to the algorithm), or why not",
      "M", "RS", lambda d, r: f(d, "SUR06") in ("USED", "NOT_USED"), ALL),
     (14, "성능 평가의 가중치", "Survey weights in performance evaluation",
      "성능 지표를 가중 또는 비가중으로 산출했는지와 계산 방법을 보고함", "Reports whether performance measures were weighted and how they were calculated",
      "M", "RS", lambda d, r: f(d, "SUR07") in ("USED", "NOT_USED"), ALL),
     (14, "성능 지표와 평가자료", "Performance measures and evaluation data",
      "판별 성능 지표와 그것을 계산한 평가자료를 보고함", "Reports discrimination measures and the data on which they were calculated",
      "M", "R", lambda d, r: r["AUROC reported"] == "Yes", ALL),
     (14, "판단 임계값", "Decision threshold",
      "임계값 지표를 보고한 경우 임계값과 그 선택 방법을 보고함", "When threshold-based measures are reported, reports the threshold and how it was chosen",
      "M", "R", lambda d, r: ok(f(d, "THR01")), lambda d, r: r["Decision threshold reported"] == "Yes"),
     (16, "성능의 불확실성", "Uncertainty of performance", "성능 추정치의 신뢰구간 또는 재표집 분포를 보고함", "Reports confidence intervals or resampling distributions for performance",
      "R", "R", lambda d, r: r["Confidence interval reported"] == "Yes", ALL),
     (16, "층·PSU의 반영", "Strata and primary sampling units",
      "설계 기반 불확실성 추정에서 층·PSU를 썼는지와 그 방법을 보고함", "Reports whether and how strata and primary sampling units were used in design-based uncertainty estimates",
      "M", "RS", lambda d, r: r["Strata or PSUs in variance estimation"] in ("Yes", "No"), ALL),
     (14, "보정도", "Calibration", "예측확률의 보정도를 보고함", "Reports calibration of predicted probabilities", "R", "R", lambda d, r: r["Calibration reported"] == "Yes", ALL),
     (14, "개발자료 밖 검증", "Validation beyond the development data",
      "이후 조사 기간이나 외부 자료로 평가한 경우 그 자료와 결과를 보고함", "When evaluated on a later survey period or external data, reports those data and results",
      "R", "RS", lambda d, r: ms.has(d, "VAL02", {"TEMPORAL", "EXTERNAL"}), ALL),
     (18, "가중치에 따른 민감도", "Sensitivity to weighting",
      "가중치 적용 여부에 따른 주요 결과의 차이를 보고하거나, 하지 않은 근거를 밝힘", "Reports how main results differ with and without weights, or why this was not examined",
      "R", "RS", None, None),
     ("importance", "중요도 계산", "Importance calculation",
      "중요도 방법, 계산한 모형과 자료 구간, 계산 설정(예: SHAP 배경자료, 출력 척도, 집계 방식)을 보고함",
      "Reports the importance method, the model and data partition used and the settings (such as SHAP background data, output scale, aggregation)",
      "I", "N", lambda d, r: ok(f(d, "VI02")) and ok(f(d, "VI04")), rank),
     ("importance", "순위 보고 규칙", "Rule for reporting the ranking",
      "전체 순위 또는 상위 변수를 고른 규칙을 보고함", "Reports the full ranking or the rule used to choose the top variables",
      "I", "N", lambda d, r: ok(f(d, "VI08")), rank),
     ("importance", "중요도 집계의 가중치", "Survey weights in importance aggregation",
      "중요도를 참여자에 걸쳐 집계할 때 가중치를 썼는지와 그 방법을 보고함", "Reports whether and how weights were used when aggregating importance across participants",
      "I", "NS", None, None),
     ("importance", "순위 안정성", "Ranking stability",
      "재표집, 조사 기수, 하위집단에 걸친 순위 안정성을 점검한 방법과 결과를 보고함", "Reports how ranking stability across resamples, survey cycles or subgroups was checked and the result",
      "R", "NS", lambda d, r: r["Ranking stability checked"] == "Yes", rank),
     ("importance", "중요도 해석의 범위", "Scope of importance interpretation",
      "순위를 모형 작동의 기술로 해석하고 모집단 연관성이나 인과효과로 해석하지 않음을 밝힘", "States that the ranking describes model behaviour, not population associations or causal effects",
      "R", "N", None, None),
     ("after", "순위 이후 분석", "Analyses after the ranking",
      "순위로 변수를 넘긴 경우 그 규칙의 사전 지정, 학습자료 안 선택, 모집단 연관성의 조사가중 추정을 보고함",
      "When the ranking guided later analyses, reports the prespecified rule, selection within the training data and survey-weighted estimation of population associations",
      "R", "NS", None, None),
    ]


if __name__ == "__main__":
    ms, CORE, rows = _ctx()
    I = build(ms)
    out = {"items": [], "studies": {}}
    for k, it in enumerate(I):
        out["items"].append({"idx": k, "tripod": it[0], "item_en": it[2], "note": it[6], "stage": it[5],
                             "repro": it[5] in ("D", "M", "I"), "scored": it[7] is not None})
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; rec = {}
        for k, it in enumerate(I):
            if it[7] is not None and it[8](d, r):
                rec[str(k)] = bool(it[7](d, r))
        tri = {str(i): r[[h for h in r if str(h).startswith(f"Reporting {i:02d}:")][0]] for i in range(1, 20)}
        out["studies"][sid] = {"items": rec, "tripod": tri}
    json.dump(out, open(ROOT / "results/derived/checklist_v14_scores.json", "w"), indent=1)
    S = out["studies"]
    for k, it in enumerate(I):
        v = [S[s]["items"][str(k)] for s in S if str(k) in S[s]["items"]]
        print(it[0], it[5], it[2][:42], f"{sum(v)}/{len(v)}" if it[7] else "uncoded")
