"""v16 core checklist (author 2026-10-28, prompt 134): criteria fixed first, then re-judged. Changes from v15:
RC02 = survey years identifiable; RC04 strict (file names or release version; website/access date alone = 0, re-read);
RC05 split into RC05 (how years were combined) and RC46 (harmonising variables across years), both re-read; RC09, RC10
and RC35 use the same definitions as the review's existing measures (participant-flow traceability, outcome rebuildable,
final model fully specified); RC15 adds the selection method; RC22 requires a software version; RC27 accepts a stated
use of defaults; RC29 requires the seed together with the split rule; RC38, RC43 and RC44 reworded (RC44 judges whether
the object and scope of the ranking's interpretation are clear). Each item carries its source and rule (RULE) for the
codebook sheet of Additional Data 1. Run: python tools/checklist_v16.py -> results/derived/checklist_v16_scores.json"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import checklist_v15 as V15  # noqa: E402
from checklist_v12 import NRSET, _ctx  # noqa: E402

STAGE, TYPE, GROUPS = V15.STAGE, V15.TYPE, V15.GROUPS
RECODE16 = ROOT / "prompts/implementation_records/v16_recode"
CLAIMS = {x["study_id"]: x for x in json.load(open(ROOT / "results/derived/claim_evidence_synthesis.json"))["studies"]}


def items(ms):
    base = {r[0]: list(r) for r in V15.items(ms)}
    f = lambda d, k: ms.first(d, k)

    def ok(v):
        if isinstance(v, list):
            return any(ok(x) for x in v)
        return v not in NRSET and not str(v).startswith(("Not reported", "NR"))
    multi = lambda d, r: r["Combining survey years"] in ("Several cycles", "Several years of one cycle")
    rank = lambda d, r: r["Importance ranking produced"] == "Yes"
    num = lambda x: str(x).replace(".", "", 1).isdigit()

    def upd(i, **kw):
        pos = {"iko": 2, "ien": 3, "cko": 4, "cen": 5, "src": 8, "met": 9, "app": 10}
        for k, v in kw.items():
            base[i][pos[k]] = v
    upd("RC02", cko="사용한 KNHANES 조사연도 또는 기수를 식별할 수 있음", cen="The KNHANES survey years or cycles used can be identified",
        met=lambda d, r: r["Survey years"] not in ("Not reported", "UNCLEAR"))
    upd("RC04", cko="사용한 원자료의 파일명 또는 공개 버전을 특정함(홈페이지 주소나 접근 일자만으로는 미충족)",
        cen="Names the raw data files or their release version (a website address or access date alone is not enough)")
    upd("RC05", iko="조사연도 결합 방법", ien="How survey years were combined",
        cko="여러 해 자료를 결합한 방법(파일 병합, 통합 파일, 연도 변수, 가중치 조정)을 보고함",
        cen="Reports how the yearly data were combined (merging, integrated file, year variable or weight adjustment)")
    base["RC46"] = ["RC46", 4, "연도 간 변수 조화", "Harmonising variables across years",
                    "연도 간에 바뀐 변수를 비교 가능하게 만든 방법을 보고하거나, 모든 연도에서 같게 측정된 변수만 썼음을 밝힘",
                    "Reports how variables that changed across years were made comparable, or that only identically measured variables were used",
                    "D", "RS", "N", None, multi]
    upd("RC09", cko="원천 표본 수, 선정·제외 조건, 단계별 제외 수와 사유, 최종 분석 표본 수를 보고함",
        cen="Reports the source sample size, eligibility criteria, numbers and reasons excluded and the final analytic sample",
        met=lambda d, r: all(ok(f(d, k)) for k in ("POP06", "POP08", "POP09", "POP10", "POP11")))
    upd("RC10", cko="결과변수의 원자료 변수·코드와 생성·범주화 규칙을 보고해 결과변수를 다시 만들 수 있음",
        cen="Reports the raw variables and codes and the derivation and categorisation rule, so the outcome can be rebuilt",
        met=lambda d, r: r["Outcome rebuildable from the report"] == "Yes")
    upd("RC15", cko="변수 선택·제외 방법과 후보·최종 설명변수 수를 보고함", cen="Reports the variable selection or exclusion method and the number of candidate and final predictors",
        met=lambda d, r: ok(f(d, "PRD02")) and ok(f(d, "PRD04")) and (f(d, "PRE11") in ("USED", "NOT_USED") or str(f(d, "PRD02")) == str(f(d, "PRD04"))))
    upd("RC22", cko="적합한 알고리즘과 구현 소프트웨어·패키지의 버전을 보고함", cen="Reports the algorithms fitted and the software or packages with version",
        met=lambda d, r: ok(f(d, "MOD02")) and bool(re.search(r"\d+\.\d+", str(f(d, "MOD09")))))
    upd("RC27", cko="최종 모형의 하이퍼파라미터 값 또는 기본값 사용 사실을 보고함", cen="Reports the final hyperparameter values or that defaults were used")
    upd("RC29", cko="분할 인덱스, 또는 난수 시드와 분할 규칙을 함께 보고함", cen="Reports the split indices, or the random seed together with the split rule",
        met=lambda d, r: ok(f(d, "MOD10")) and base["RC28"][9](d, r))
    upd("RC34", cko="분산 추정에 층·PSU를 썼는지 보고하고, 쓴 경우 방법을 보고함", cen="States whether strata and PSUs were used for variance estimation and, if so, how")
    upd("RC35", met=lambda d, r: r["Final model fully specified"] == "Yes")
    upd("RC38", cko="가중치 민감도 분석의 수행 여부와, 수행한 경우 결과를, 하지 않은 경우 근거를 보고함",
        cen="States whether a sensitivity analysis to weighting was done, with its results, or why not")
    upd("RC43", cko="순위 안정성 점검(재표집, 조사 기수, 하위집단)의 방법과 결과를 보고함", cen="Reports the method and results of a ranking-stability check (resamples, survey cycles or subgroups)")
    upd("RC44", cko="순위의 해석 대상과 추론 범위가 분명함: 순위로 변수나 모집단 연관을 해석한 경우, 그것이 모형의 예측 기여이며 인과·모집단 연관이 아님을 밝힘",
        cen="The object and scope of interpretation are clear: when the ranking is used to interpret variables or population associations, the report states that it reflects the model's contributions, not causal effects or population associations",
        src="EN", met=None)
    return [tuple(v) for v in base.values()]


RULE = {  # source of each judgement, for the codebook sheet (protocol item codes in Additional Data 1 'Evidence locations')
 "RC01": "existing code: target population reported (SUR02)", "RC02": "existing code: survey years reported (DAT01; column 'Survey years')",
 "RC03": "existing code: survey components reported (DAT14)", "RC04": "full-text reading v16 (strict criterion)",
 "RC05": "full-text reading v16", "RC06": "full-text reading v15", "RC07": "existing code: combined-year weight construction reported (DAT11 = R)",
 "RC08": "existing code: age limits (POP03/POP04) and eligibility criteria (POP06)", "RC09": "existing code: POP06, POP08, POP09, POP10 and POP11 all reported (participant-flow traceability)",
 "RC10": "existing code: outcome rebuildable from the report (OUT16; column 'Outcome rebuildable from the report')",
 "RC11": "existing code: outcome timing assessable (OUT10)", "RC12": "full-text reading v15", "RC13": "existing code: POP12 and POP14",
 "RC14": "existing code: predictor set rebuildable (PRD13 = R2)", "RC15": "existing code: PRD02 and PRD04 reported and selection stated (PRE11) or counts equal",
 "RC16": "full-text reading v15", "RC17": "existing code: PRE04", "RC18": "existing code: PRE01 and PRE03", "RC19": "full-text reading v15",
 "RC20": "existing code: timing of data-dependent preprocessing determinable", "RC21": "existing code: IMB03 (applies if IMB01 used)",
 "RC22": "existing code: MOD02 and a version number in MOD09", "RC23": "full-text reading v15", "RC24": "full-text reading v15",
 "RC25": "existing code: MOD07 and MOD08 (applies if tuned, MOD12)", "RC26": "existing code: tuning kept apart from final evaluation determinable",
 "RC27": "existing code: MOD06 (values or default use)", "RC28": "existing code: VAL02-VAL04", "RC29": "existing code: MOD10 and RC28",
 "RC30": "existing code: AUROC reported", "RC31": "existing code: THR01 (applies if threshold reported)", "RC32": "full-text reading v15",
 "RC33": "existing code: confidence interval reported", "RC34": "existing code: strata or PSUs in variance estimation reported (yes or no)",
 "RC35": "existing code: final model fully specified (REP17 = R)", "RC36": "existing code: MOD15", "RC37": "existing code: calibration reported",
 "RC38": "full-text reading v15", "RC39": "existing code: VI02 and VI04", "RC40": "full-text reading v15", "RC41": "existing code: VI08",
 "RC42": "full-text reading v15", "RC43": "existing code: ranking stability checked (VI16)",
 "RC44": "full-text reading v15 (explicit scoping statement); not applicable as a requirement and met when the ranking was not used to interpret variables or population associations (existing claim codes, claim_evidence_synthesis)",
 "RC45": "full-text reading v15", "RC46": "full-text reading v16"}


def recoded16():
    out = {}
    for p in sorted(RECODE16.glob("batch_*_output.json")):
        for rec in json.load(open(p)):
            out[rec["study_id"]] = rec
    ov = RECODE16 / "review_overrides.json"  # one wording rule applied to all batches (CODING_GUIDE clarification)
    for sid, its in (json.load(open(ov)).items() if ov.exists() else []):
        for k, v in its.items():
            out[sid][k] = {"v": v["v"], "e": out[sid][k]["e"] + " [review: " + v["why"] + "]"}
    return out


if __name__ == "__main__":
    ms, CORE, rows = _ctx()
    I = items(ms); R15 = V15.recoded(); R16 = recoded16()
    missing = [d["study_id"] for d in CORE if d["study_id"] not in R16]
    out = {"items": [], "studies": {}, "missing_recode": missing}
    for k, it in enumerate(I):
        out["items"].append({"idx": k, "id": it[0], "tripod": it[1], "item_en": it[3], "item_ko": it[2], "stage": it[6], "note": it[7],
                             "source": it[8], "rule": RULE[it[0]], "repro": it[6] in ("D", "M", "I"), "scored": True})
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; rec = {}; ev = {}
        for k, it in enumerate(I):
            if not it[10](d, r):
                continue
            if it[0] in ("RC04", "RC05", "RC46"):
                g = R16.get(sid, {}).get(it[0])
            elif it[0] == "RC44":
                g15 = R15[sid][V15.GUIDE_ID["RC44"]]
                expl = str(g15["v"]) == "1"
                used = CLAIMS[sid]["claims"]["interpretation"] or CLAIMS[sid]["claims"]["association"]
                rec[str(k)] = expl or not used
                ev["RC44"] = g15.get("e", "") if expl else ("ranking not used to interpret variables or population associations" if rec[str(k)]
                                                             else "ranking used to interpret variables or associations without stating the scope")
                continue
            elif it[8] == "N":
                g = R15[sid].get(V15.GUIDE_ID[it[0]])
            else:
                rec[str(k)] = bool(it[9](d, r)); continue
            if g is None or g.get("v") in ("NA", None):
                continue
            rec[str(k)] = int(g["v"]) == 1; ev[it[0]] = g.get("e", "")
        tri = {str(i): r[[h for h in r if str(h).startswith(f"Reporting {i:02d}:")][0]] for i in range(1, 20)}
        out["studies"][sid] = {"items": rec, "tripod": tri, "evidence": ev}
    json.dump(out, open(ROOT / "results/derived/checklist_v16_scores.json", "w"), indent=1, ensure_ascii=False)
    S = out["studies"]
    print("missing recode", len(missing))
    for k, it in enumerate(I):
        v = [S[s]["items"][str(k)] for s in S if str(k) in S[s]["items"]]
        print(it[0], it[8], it[3][:40], f"{sum(v)}/{len(v)}")
