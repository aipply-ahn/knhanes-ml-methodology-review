"""v15 core checklist (author 2026-10-28): every core item (RC01-RC45) is judged for all 193 core studies, so the
checklist, Additional Data 1 and Figure 5 are aligned (no uncoded item). Items are single reporting requirements judged
met (1), not met (0) or not applicable (NA). Source per item: 'E' = derived from the existing coded data with the rule
below; 'N' = read from the full text in the v15 recoding (prompts/implementation_records/v15_recode, guide
CODING_GUIDE.md). Run: python tools/checklist_v15.py -> results/derived/checklist_v15_scores.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from checklist_v12 import TRIPOD, NRSET, _ctx  # noqa: E402

STAGE = {"D": ("자료", "Data"), "M": ("모형", "Model"), "I": ("중요도", "Importance"), "R": ("보고·해석", "Reporting")}
TYPE = {"R": ("구체화", "Specified"), "RS": ("구체화(특화)", "Specified (KNHANES)"), "N": ("신설", "New"), "NS": ("신설(특화)", "New (KNHANES)")}
GROUPS = {"importance": ("변수중요도", "Variable importance"), "after": ("순위 이후 분석", "Analyses after the ranking")}
RECODE = ROOT / "prompts/implementation_records/v15_recode"


def items(ms):
    f = lambda d, k: ms.first(d, k)

    def ok(v):
        if isinstance(v, list):
            return any(ok(x) for x in v)
        return v not in NRSET and not str(v).startswith(("Not reported", "NR"))
    rep = lambda *ks: (lambda d, r: all(ok(f(d, k)) for k in ks))
    num = lambda x: str(x).replace(".", "", 1).isdigit()
    ALL = lambda d, r: True
    multi = lambda d, r: r["Combining survey years"] in ("Several cycles", "Several years of one cycle")
    rank = lambda d, r: r["Importance ranking produced"] == "Yes"
    N = None  # read from the full text
    # (id, element, item ko, en, criterion ko, en, stage, type, source, met, app)
    return [
     ("RC01", 3, "결과가 기술하는 대상", "Population the results describe", "결과가 기술하는 대상(분석 표본, 목표 모집단)을 명시함", "States whom the results describe (analytic sample or target population)", "R", "RS", "E", rep("SUR02"), ALL),
     ("RC02", 4, "분석 조사연도", "Survey years analysed", "분석한 조사연도(기수) 목록을 확인할 수 있음", "The exact survey years (cycles) analysed can be identified", "D", "RS", "E", lambda d, r: f(d, "DAT18") == "R", ALL),
     ("RC03", 4, "조사 구성요소", "Survey components", "사용한 조사 구성요소(건강설문, 검진, 혈액·소변 검사, 영양조사)를 밝힘", "States the survey components used (interview, examination, laboratory, nutrition)", "D", "RS", "E", rep("DAT14"), ALL),
     ("RC04", 4, "원자료 파일", "Raw data files", "사용한 원자료 파일명이나 공개 버전을 밝힘", "Identifies the raw data files or release used", "D", "RS", "N", N, ALL),
     ("RC05", 4, "연도 결합과 변수 조화", "Combining years and harmonising variables", "여러 해를 결합한 방식과 연도 간에 바뀐 변수의 조화 방법을 보고함", "Reports how years were combined and how variables that changed across years were made comparable", "D", "RS", "N", N, multi),
     ("RC06", 4, "조사가중치 선택", "Choice of survey weights", "가중치 사용 여부와, 사용 시 가중치 변수를, 비사용 시 이유를 보고함", "States whether weights were used and which weight, or why not", "D", "RS", "N", N, ALL),
     ("RC07", 4, "다연도 가중치 구성", "Combined-year weights", "여러 해를 결합해 가중치를 쓴 경우 가중치 조정·산출 방법을 보고함", "When weights were used with combined years, reports how they were adjusted", "D", "RS", "E", lambda d, r: f(d, "DAT11") == "R", lambda d, r: multi(d, r) and f(d, "DAT11") != "NA" and f(d, "SUR04") == "USED"),
     ("RC08", 5, "포함·제외 조건", "Inclusion and exclusion conditions", "연령·성별 등 분석 표본의 포함·제외 조건을 보고함", "Reports the inclusion and exclusion conditions of the analytic sample, such as age and sex", "D", "R", "E", lambda d, r: (num(f(d, "POP03")) or num(f(d, "POP04"))) and ok(f(d, "POP06")), ALL),
     ("RC09", 5, "표본 선정 단계", "Sample-selection steps", "제외 조건의 적용 단계와 단계별 표본 수를 보고함", "Reports the selection steps and the sample size at each step", "D", "R", "E", rep("POP11"), ALL),
     ("RC10", 6, "결과변수 재구성", "Rebuilding the outcome", "결과변수의 원자료 변수·코드와 생성·범주화 규칙을 보고함", "Reports the raw variables and codes and the derivation and categorisation rule of the outcome", "D", "R", "E", lambda d, r: f(d, "OUT16") == "R2" and ok(f(d, "OUT08")), ALL),
     ("RC11", 6, "결과변수 측정 시점", "Timing of the outcome", "결과변수가 설명변수와 같은 조사에서 측정됐는지 확인할 수 있음", "Whether the outcome was measured in the same survey as the predictors can be determined", "D", "RS", "E", lambda d, r: f(d, "OUT10") != "UNC", ALL),
     ("RC12", 6, "결과변수와 설명변수의 중복", "Outcome-predictor overlap", "결과 정의에 쓴 변수가 설명변수에 포함됐는지와 처리 방법을 보고함", "Reports whether variables defining the outcome were among the predictors and how this was handled", "D", "RS", "N", N, ALL),
     ("RC13", 8, "결과변수 분포", "Outcome distribution", "분석 표본의 결과변수 범주별 수와 비율을 보고함", "Reports the number and proportion in each outcome class", "D", "R", "E", rep("POP12", "POP14"), ALL),
     ("RC14", 7, "최종 입력변수와 코딩", "Final input variables and coding", "모형에 투입한 설명변수 목록과 코딩을 보고함", "Reports the predictors entered into the model and their coding", "D", "R", "E", lambda d, r: f(d, "PRD13") == "R2", ALL),
     ("RC15", 7, "변수 선택 과정", "Variable selection process", "후보 설명변수 수와 최종 설명변수 수를 보고함", "Reports the number of candidate and final predictors", "D", "R", "E", rep("PRD02", "PRD04"), ALL),
     ("RC16", 7, "파생 설명변수", "Derived predictors", "파생 설명변수의 생성 규칙(수식, 기준값, 범주)을 보고함", "Reports derivation rules (formulas, cut-offs, categories) for derived predictors", "D", "R", "N", N, ALL),
     ("RC17", 10, "결측 규모", "Amount of missingness", "변수별 결측 규모를 보고함", "Reports the amount of missingness by variable", "D", "R", "E", rep("PRE04"), ALL),
     ("RC18", 10, "결측 처리 규칙", "Missing-value rules", "결측값 처리·대체 방법과 변수별 규칙을 보고함", "Reports the handling or imputation method and variable-specific rules", "D", "R", "E", rep("PRE01", "PRE03"), ALL),
     ("RC19", 10, "특수 응답 코드", "Special response codes", "해당없음·모름 등 특수 응답 코드(예: 8888, 9999)의 처리를 보고함", "Reports the handling of special response codes (such as not applicable or don't know)", "D", "RS", "N", N, ALL),
     ("RC20", 11, "전처리 시점", "Timing of preprocessing", "자료 의존 전처리 단계의 자료 분할 전후 수행 시점을 확인할 수 있음", "Whether each data-dependent preprocessing step was done before or after the split can be determined", "M", "R", "E",
      lambda d, r: r["Preprocessing over all applied steps"] != "Timing unclear", lambda d, r: r["Preprocessing over all applied steps"] != "No data-dependent step"),
     ("RC21", 11, "클래스 재균형", "Class rebalancing", "클래스 재균형의 방법과 수행 시점을 보고함", "Reports the rebalancing method and when it was applied", "M", "R", "E", lambda d, r: f(d, "IMB03") not in ("ORDER_NR", "NA", "NR", "UNC"), lambda d, r: f(d, "IMB01") != "NONE"),
     ("RC22", 11, "알고리즘과 실행 환경", "Algorithms and software", "적합한 알고리즘과 소프트웨어·패키지를 보고함", "Reports the algorithms fitted and the software and packages", "M", "R", "E", rep("MOD02", "MOD09"), ALL),
     ("RC23", 11, "파이프라인 순서", "Pipeline order", "전처리와 학습 단계의 순서를 재현할 수 있게 보고함", "Reports the order of preprocessing and training steps so it can be repeated", "M", "R", "N", N, ALL),
     ("RC24", 11, "모형 적합의 가중치", "Weights in model fitting", "모형 적합에 가중치를 썼는지와, 쓴 경우 방법을, 안 쓴 경우 이유를 보고함", "States whether weights were used in model fitting and how, or why not", "M", "RS", "N", N, ALL),
     ("RC25", 12, "튜닝 절차", "Tuning procedure", "튜닝 방법과 탐색 공간을 보고함", "Reports the tuning method and search space", "M", "R", "E", rep("MOD07", "MOD08"), lambda d, r: f(d, "MOD12") == "USED"),
     ("RC26", 12, "튜닝과 최종 평가의 분리", "Tuning kept apart from evaluation", "모형 선택·튜닝에 최종 평가자료를 썼는지 확인할 수 있음", "Whether the final evaluation data were used for model choice or tuning can be determined", "M", "R", "E",
      lambda d, r: r["Tuning kept apart from the final evaluation"] != "Not reported", ALL),
     ("RC27", 12, "최종 하이퍼파라미터", "Final hyperparameters", "최종 모형의 하이퍼파라미터 값을 보고함", "Reports the hyperparameter values of the final model", "M", "R", "E", rep("MOD06"), ALL),
     ("RC28", 13, "내부 검증 설계", "Internal-validation design", "분할 비율 또는 교차검증 겹 수를 보고함", "Reports the split proportions or the number of cross-validation folds", "M", "R", "E",
      lambda d, r: ms.has(d, "VAL02", {"SPLIT", "CV"}) and (ok(f(d, "VAL04")) if ms.has(d, "VAL02", {"CV"}) else True) and (ok(f(d, "VAL03")) if ms.has(d, "VAL02", {"SPLIT"}) else True), ALL),
     ("RC29", 13, "분할 재현 정보", "Reproducible split", "난수 시드 또는 분할 인덱스를 보고함", "Reports the random seed or the split indices", "M", "R", "E", rep("MOD10"), ALL),
     ("RC30", 14, "성능 지표", "Performance measures", "판별 성능 지표(예: AUROC)와 그것을 계산한 평가자료를 보고함", "Reports discrimination measures (such as AUROC) and the data on which they were calculated", "M", "R", "E", lambda d, r: r["AUROC reported"] == "Yes", ALL),
     ("RC31", 14, "판단 임계값", "Decision threshold", "임계값 지표를 보고한 경우 임계값과 선택 방법을 보고함", "When threshold-based measures are reported, reports the threshold and how it was chosen", "M", "R", "E", rep("THR01"), lambda d, r: r["Decision threshold reported"] == "Yes"),
     ("RC32", 14, "성능 평가의 가중치", "Weights in performance evaluation", "성능 지표를 가중했는지와 방법 또는 이유를 보고함", "States whether performance measures were weighted and how, or why not", "M", "RS", "N", N, ALL),
     ("RC33", 16, "성능의 불확실성", "Uncertainty of performance", "성능 추정치의 신뢰구간 또는 재표집 분포를 보고함", "Reports confidence intervals or resampling distributions", "R", "R", "E", lambda d, r: r["Confidence interval reported"] == "Yes", ALL),
     ("RC34", 16, "층·PSU", "Strata and PSUs", "설계 기반 불확실성에 층·PSU를 썼는지와 방법을 보고함", "Reports whether and how strata and PSUs were used for design-based uncertainty", "M", "RS", "E", lambda d, r: r["Strata or PSUs in variance estimation"] in ("Yes", "No"), ALL),
     ("RC35", 17, "최종 모형 명세", "Final model specification", "새 자료에 적용할 수 있게 최종 모형을 명세함", "Specifies the final model fully enough to apply it to new data", "M", "R", "E", lambda d, r: f(d, "MOD14") == "USED", ALL),
     ("RC36", 19, "코드 공개", "Code availability", "분석 코드를 공개함", "Analysis code is available", "M", "R", "E", lambda d, r: f(d, "MOD15") == "USED", ALL),
     ("RC37", 14, "보정도", "Calibration", "예측확률의 보정도를 보고함", "Reports calibration of predicted probabilities", "R", "R", "E", lambda d, r: r["Calibration reported"] == "Yes", ALL),
     ("RC38", 18, "가중치 민감도", "Sensitivity to weighting", "가중 여부에 따른 결과 차이를 보고하거나 하지 않은 이유를 밝힘", "Reports results with and without weights, or why not", "R", "RS", "N", N, ALL),
     ("RC39", "importance", "중요도 방법과 대상", "Importance method and object", "중요도 방법과 계산한 모형·자료 구간을 보고함", "Reports the importance method and the model and data partition used", "I", "N", "E", rep("VI02", "VI04"), rank),
     ("RC40", "importance", "중요도 계산 설정", "Importance settings", "중요도를 다시 계산하는 데 필요한 설정(예: SHAP 설명기·배경자료)을 보고함", "Reports the settings needed to recompute importance (such as the SHAP explainer and background data)", "I", "N", "N", N, rank),
     ("RC41", "importance", "순위 보고 규칙", "Ranking rule", "전체 순위 또는 상위 변수를 고른 규칙을 보고함", "Reports the full ranking or the rule used to choose the top variables", "I", "N", "E", rep("VI08"), rank),
     ("RC42", "importance", "중요도 집계의 가중치", "Weights in importance aggregation", "중요도를 집계할 때 가중치를 썼는지 보고함", "States whether weights were used when aggregating importance", "I", "NS", "N", N, rank),
     ("RC43", "importance", "순위 안정성", "Ranking stability", "재표집, 조사 기수, 하위집단에 걸친 순위 안정성을 점검함", "Checks ranking stability across resamples, survey cycles or subgroups", "R", "NS", "E", lambda d, r: r["Ranking stability checked"] == "Yes", rank),
     ("RC44", "importance", "중요도 해석의 범위", "Scope of interpretation", "순위가 모형 작동을 기술하며 인과나 모집단 연관이 아님을 밝힘", "States that the ranking describes model behaviour, not causal effects or population associations", "R", "N", "N", N, rank),
     ("RC45", "after", "순위 이후 분석의 규칙", "Rule after the ranking", "순위로 변수를 넘긴 규칙과 그 선택에 쓴 자료를 보고함", "Reports the rule for carrying variables forward and the data used for that selection", "R", "N", "N", N,
      lambda d, r: ms.has(d, "VI10", {"USED"}) or ms.has(d, "VI11", {"USED"})),
    ]


GUIDE_ID = {"RC04": "RC04", "RC05": "RC05", "RC06": "RC06", "RC12": "RC12", "RC16": "RC16", "RC19": "RC19", "RC23": "RC23",
            "RC24": "RC24", "RC32": "RC32", "RC38": "RC39", "RC40": "RC41", "RC42": "RC43", "RC44": "RC45", "RC45": "RC46"}


def recoded():
    out = {}
    for p in sorted(RECODE.glob("batch_*_output.json")):
        for rec in json.load(open(p)):
            out[rec["study_id"]] = rec
    ov = RECODE / "review_overrides.json"  # author-side review of the full-text judgements (criterion applied strictly)
    for sid, items in (json.load(open(ov)).items() if ov.exists() else []):
        for k, v in items.items():
            out[sid][k] = {"v": v["v"], "e": out[sid][k]["e"] + " [review: " + v["why"] + "]"}
    return out


if __name__ == "__main__":
    ms, CORE, rows = _ctx()
    I = items(ms); R = recoded()
    missing = [d["study_id"] for d in CORE if d["study_id"] not in R]
    out = {"items": [], "studies": {}, "missing_recode": missing}
    for k, it in enumerate(I):
        out["items"].append({"idx": k, "id": it[0], "tripod": it[1], "item_en": it[3], "item_ko": it[2], "stage": it[6], "note": it[7],
                             "source": it[8], "repro": it[6] in ("D", "M", "I"), "scored": True})
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; rec = {}; ev = {}
        for k, it in enumerate(I):
            if it[8] == "E":
                if it[10](d, r):
                    rec[str(k)] = bool(it[9](d, r))
            else:
                g = R.get(sid, {}).get(GUIDE_ID[it[0]])
                if g is None:
                    continue
                v = g.get("v")
                if v in ("NA", None) or not it[10](d, r):
                    continue
                rec[str(k)] = int(v) == 1; ev[it[0]] = g.get("e", "")
        tri = {str(i): r[[h for h in r if str(h).startswith(f"Reporting {i:02d}:")][0]] for i in range(1, 20)}
        out["studies"][sid] = {"items": rec, "tripod": tri, "evidence": ev}
    json.dump(out, open(ROOT / "results/derived/checklist_v15_scores.json", "w"), indent=1, ensure_ascii=False)
    S = out["studies"]
    print("missing recode", len(missing))
    for k, it in enumerate(I):
        v = [S[s]["items"][str(k)] for s in S if str(k) in S[s]["items"]]
        print(it[0], it[8], it[3][:40], f"{sum(v)}/{len(v)}")
