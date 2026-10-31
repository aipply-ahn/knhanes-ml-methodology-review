"""v18 core checklist (coding audit round 1, 2026-10-29): v17 plus
(1) RC31 applies when any threshold-based measure is reported (MET_ACC/BACC/SENS/SPEC/PPV/NPV/F1/MCC/KAPPA = R) or a
    threshold is reported (was: only when a threshold was reported, which hid studies that never state it);
(2) cell-level corrections from the Claude Code/Codex coding audit (prompts/implementation_records/coding_audit/
    overrides.json: agreed findings and adjudicated decisions under RULES_r1.md), applied last.
Run: python tools/checklist_v18.py -> results/derived/checklist_v18_scores.json"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import checklist_v17 as V17  # noqa: E402
from checklist_v12 import _ctx  # noqa: E402

STAGE, TYPE, GROUPS = V17.STAGE, V17.TYPE, V17.GROUPS
AUDIT = ROOT / "prompts/implementation_records/coding_audit/overrides.json"
THRESH = ["MET_ACC_R", "MET_BACC_R", "MET_SENS_R", "MET_SPEC_R", "MET_PPV_R", "MET_NPV_R", "MET_F1_R", "MET_MCC_R", "MET_KAPPA_R"]


def items(ms):
    base = {r[0]: list(r) for r in V17.items(ms)}
    base["RC31"][10] = lambda d, r: r["Decision threshold reported"] == "Yes" or any(ms.has(d, k, {"R"}) for k in THRESH)
    # criteria as finally applied in the coding audit (coding_audit/RULES_r4.md)
    C = {
     "RC08": ("연령·성별·질환 등 분석 표본의 포함·제외 조건을 보고함(연령 제한이 필수는 아님)", "Reports the inclusion and exclusion conditions of the analytic sample (an age limit is not required)"),
     "RC13": ("모형 표본의 결과변수 범주별 수(또는 한 범주의 수와 전체 수)를 직접 보고함", "States the number in each outcome class of the modelling sample directly (or one class's count with the total)"),
     "RC17": ("결측이 있는 변수마다(또는 함께 빠진 검사·조사 단위마다) 결측 규모를 보고함", "Reports the amount of missingness for each variable with missing data (or each test or survey component missing together)"),
     "RC20": ("자료 의존 전처리 단계마다 자료 분할 전후 어디서 수행했는지 보고함", "Reports, for each data-dependent preprocessing step, whether it was done before or after the split"),
     "RC29": ("분할 인덱스, 난수 시드 값과 분할 규칙, 또는 결정적 분할 규칙(예: 조사연도)을 보고함", "Reports the split indices, the seed value with the split rule, or a deterministic split rule (such as by survey year)"),
     "RC30": ("판별 성능 지표(AUROC, c-통계량, 이득·향상도)와 그것을 계산한 자료 구간을 명시함", "Reports a discrimination measure (AUROC, c-statistic, gains or lift) and states the data partition on which it was computed"),
     "RC31": ("임계값 기반 지표를 보고한 경우 최종 모형에 적용한 임계값(또는 자기완결적 분류 규칙)과 선택 방법을 보고함", "When threshold-based measures are reported, reports the cutoff (or a self-contained assignment rule) applied to the final model and how it was chosen"),
     "RC33": ("성능 추정치의 신뢰구간, 표준편차 또는 재표집 분포를 보고함", "Reports confidence intervals, standard deviations or resampling distributions of performance"),
     "RC34": ("분산 추정에 층·PSU(집락)를 썼는지 명시하고, 쓴 경우 방법을 보고함", "States whether strata and PSUs (clusters) were used for variance estimation and, if so, how"),
     "RC35": ("새 자료에 적용할 수 있게 최종 모형(식·계수, 저장 모형과 전처리, 또는 입력이 정의된 나무 규칙)을 명세함", "Specifies the final model for new data (equation or coefficients, a saved model with its preprocessing, or tree rules with defined inputs)"),
     "RC36": ("분석 코드를 공개함(앱·추론 전용 코드나 요청 시 제공은 미충족)", "Analysis code is publicly available (app-only or inference-only code, or code on request, does not meet it)"),
     "RC44": ("순위로 변수나 연관을 해석한 경우, 그것이 모형의 예측 기여이며 인과·모집단 연관이 아님을 밝힘", "When the ranking is used to interpret variables or associations, states that it reflects model contributions, not causal effects or population associations"),
     "RC46": ("연도 간에 바뀐 변수를 비교 가능하게 만든 방법이나 공통 측정 변수로의 제한을 명시함(결과변수가 측정된 연도의 선택은 미충족)", "States how variables that changed across years were made comparable, or a restriction to identically measured variables (choosing years in which the outcome was measured does not meet it)"),
    }
    for k, (ko, en) in C.items():
        base[k][4], base[k][5] = ko, en
    return [tuple(v) for v in base.values()]


RULE = dict(V17.RULE)
RULE["RC31"] = "existing code: THR01; applies when any threshold-based measure (MET_*) or a threshold is reported"
for k in RULE:
    RULE[k] += "; corrected cell by cell by the Claude Code/Codex coding audit (coding_audit/overrides.json)"


if __name__ == "__main__":
    subprocess.run([sys.executable, str(ROOT / "tools/checklist_v17.py")], check=True, stdout=subprocess.DEVNULL)
    t = json.load(open(ROOT / "results/derived/checklist_v17_scores.json"))
    ms, CORE, rows = _ctx()
    I = items(ms)
    idx = {i["id"]: str(i["idx"]) for i in t["items"]}
    k31 = idx["RC31"]; it31 = [x for x in I if x[0] == "RC31"][0]
    for d in CORE:
        st = t["studies"][d["study_id"]]; r = rows[d["study_id"]]
        if it31[10](d, r):
            st["items"][k31] = bool(it31[9](d, r))
        else:
            st["items"].pop(k31, None)
    ov = json.load(open(AUDIT)) if AUDIT.exists() else {}
    n = 0
    for sid, cells in ov.items():
        st = t["studies"][sid]
        for rc, o in cells.items():
            k = idx[rc]
            if o["value"] == "NA":
                st["items"].pop(k, None)
            else:
                st["items"][k] = int(o["value"]) == 1
            st.setdefault("audit", {})[rc] = o.get("reason", "")
            n += 1
    for i in t["items"]:
        i["rule"] = RULE[i["id"]]
    t["audit_overrides"] = n
    json.dump(t, open(ROOT / "results/derived/checklist_v18_scores.json", "w"), indent=1, ensure_ascii=False)
    S = t["studies"]
    print("audit overrides", n)
    for i in t["items"]:
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        print(i["id"], i["item_en"][:40], f"{sum(v)}/{len(v)}")
