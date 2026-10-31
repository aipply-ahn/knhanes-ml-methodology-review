"""v17 core checklist (author 2026-10-28, prompt 135): v16 plus three criterion checks. RC03 judged from the full text
(components named in the report, not inferred from variables; re-read); RC30 requires the evaluation data to be
identifiable (AUROC reported and VAL07 known); RC44 judged from the interpretation itself: a disclaimer does not offset a
population-association claim made without a survey-aware analysis. RC20 and RC38 wording clarified (reporting, not
practice). Run: python tools/checklist_v17.py -> results/derived/checklist_v17_scores.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import checklist_v15 as V15  # noqa: E402
import checklist_v16 as V16  # noqa: E402
from checklist_v12 import _ctx  # noqa: E402

STAGE, TYPE, GROUPS = V16.STAGE, V16.TYPE, V16.GROUPS
RECODE17 = ROOT / "prompts/implementation_records/v17_recode"
CLAIMS = V16.CLAIMS


def items(ms):
    base = {r[0]: list(r) for r in V16.items(ms)}
    f = lambda d, k: ms.first(d, k)

    def upd(i, **kw):
        pos = {"iko": 2, "ien": 3, "cko": 4, "cen": 5, "src": 8, "met": 9, "app": 10}
        for k, v in kw.items():
            base[i][pos[k]] = v
    upd("RC03", cko="사용한 조사 구성요소(건강설문, 검진, 혈액·소변 검사, 영양조사)를 명시함(변수로부터 추정되는 경우는 미충족)",
        cen="Names the survey components used (interview, examination, laboratory, nutrition); components only inferable from the variables do not meet it",
        src="N", met=None)
    upd("RC20", cko="자료 의존 전처리 단계마다 자료 분할 전후 어디서 수행했는지 보고함(학습자료 안 수행 여부는 판정하지 않음)",
        cen="Reports, for each data-dependent preprocessing step, whether it was done before or after the split (not whether it was done within the training data)")
    upd("RC30", cko="판별 성능 지표(예: AUROC)와 그것을 계산한 평가자료(시험자료, 교차검증, 개발자료)를 보고함",
        cen="Reports discrimination measures (such as AUROC) and the evaluation data on which they were calculated (test set, cross-validation or development data)",
        met=lambda d, r: r["AUROC reported"] == "Yes" and f(d, "VAL07") in ("USED", "NOT_USED", "NA"))
    upd("RC38", cko="가중치 적용 여부에 따른 민감도 분석을 수행했는지 밝히고, 수행한 경우 결과를, 하지 않은 경우 근거를 보고함",
        cen="States whether a sensitivity analysis to weighting was done, with its results, or the reason it was not")
    upd("RC44", cko="순위의 해석 범위가 분명함: 순위로 변수나 연관을 해석한 경우 모형의 예측 기여임을 밝히고, 조사설계를 반영한 분석 없이 모집단 연관을 주장하지 않음",
        cen="The scope of interpretation is clear: when the ranking is used to interpret variables or associations, the report states that it reflects model contributions and makes no population-association claim without a survey-aware analysis",
        met=None)
    return [tuple(v) for v in base.values()]


RULE = dict(V16.RULE)
RULE.update({
 "RC03": "full-text reading v17 (components named in the report; inference from variables not accepted)",
 "RC20": "existing code: timing of each data-dependent preprocessing step determinable (practice coded separately)",
 "RC30": "existing code: AUROC reported and evaluation data identifiable (VAL07 known)",
 "RC38": "full-text reading v15 (applies to all studies: every KNHANES analysis chooses whether to weight)",
 "RC44": "interpretation in the Discussion/Conclusion (existing claim codes, claim_evidence_synthesis) and full-text reading v15: met when the ranking is not used to interpret variables or associations; when it is, met only with an explicit scoping statement and no population-association claim lacking a survey-aware analysis"})


def recoded17():
    out = {}
    for p in sorted(RECODE17.glob("batch_*_output.json")):
        for rec in json.load(open(p)):
            out[rec["study_id"]] = rec
    ov = RECODE17 / "review_overrides.json"  # one wording rule applied to all batches (CODING_GUIDE clarification)
    for sid, its in (json.load(open(ov)).items() if ov.exists() else []):
        for k, v in its.items():
            out[sid][k] = {"v": v["v"], "e": out[sid][k]["e"] + " [review: " + v["why"] + "]"}
    return out


if __name__ == "__main__":
    ms, CORE, rows = _ctx()
    I = items(ms); R15 = V15.recoded(); R16 = V16.recoded16(); R17 = recoded17()
    missing = [d["study_id"] for d in CORE if d["study_id"] not in R17]
    out = {"items": [], "studies": {}, "missing_recode": missing}
    for k, it in enumerate(I):
        out["items"].append({"idx": k, "id": it[0], "tripod": it[1], "item_en": it[3], "item_ko": it[2], "stage": it[6], "note": it[7],
                             "source": it[8], "rule": RULE[it[0]], "repro": it[6] in ("D", "M", "I"), "scored": True})
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; rec = {}; ev = {}
        for k, it in enumerate(I):
            if not it[10](d, r):
                continue
            if it[0] == "RC03":
                g = R17.get(sid, {}).get("RC03")
            elif it[0] in ("RC04", "RC05", "RC46"):
                g = R16.get(sid, {}).get(it[0])
            elif it[0] == "RC44":
                g15 = R15[sid][V15.GUIDE_ID["RC44"]]
                expl = str(g15["v"]) == "1"; cl = CLAIMS[sid]
                used = cl["claims"]["interpretation"] or cl["claims"]["association"]
                unsup = cl["claims"]["association"] and not cl["evidence_met"]["association"]
                rec[str(k)] = (not used) or (expl and not unsup)
                ev["RC44"] = ("ranking not used to interpret variables or associations" if not used else
                              (g15.get("e", "") if rec[str(k)] else ("population-association claim without a survey-aware analysis" if unsup
                                                                     else "ranking interpreted without stating the scope")))
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
    json.dump(out, open(ROOT / "results/derived/checklist_v17_scores.json", "w"), indent=1, ensure_ascii=False)
    S = out["studies"]
    print("missing recode", len(missing))
    for k, it in enumerate(I):
        v = [S[s]["items"][str(k)] for s in S if str(k) in S[s]["items"]]
        print(it[0], it[8], it[3][:40], f"{sum(v)}/{len(v)}")
