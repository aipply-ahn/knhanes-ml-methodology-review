"""v20 core checklist (prompt 137, 2026-10-31): refinement for reporting economy - an item is kept only if missing
information would impair reproduction or interpretation, it is not covered by another item, the reporting burden is
reasonable and it can be judged without guessing. Changes from v18 (criteria fixed first; raw judgements kept):
- RC04 (raw data files) and RC38 (sensitivity to weighting) removed from the core score (kept in Additional Data 1 as
  reference; RC38 becomes a recommended analysis where relevant);
- RC03 merged into RC02 ("survey data used": survey years and the KNHANES components used; met only if both);
- RC05 judges how the yearly data were combined only (weight adjustment is RC07): 13 weight-only judgements -> 0;
- RC17 wording: missingness for individual variables or groups sharing a missingness pattern (rule unchanged);
- RC42 applies only when participant-level importance (SHAP, LIME) was aggregated.
Run: python tools/checklist_v20.py -> results/derived/checklist_v20_scores.json"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import checklist_v18 as V18  # noqa: E402
from checklist_v12 import _ctx  # noqa: E402

STAGE, TYPE, GROUPS = V18.STAGE, V18.TYPE, V18.GROUPS
REMOVED = {"RC03": "merged into RC02", "RC04": "removed: file names add little when years, components and variable definitions are reported",
           "RC38": "removed from the core score: a recommended sensitivity analysis where relevant, not reproduction information"}
RC05_WEIGHT_ONLY = ["KHM003", "KHM006", "KHM009", "KHM019", "KHM082", "KHM118", "KHM132", "KHM234", "KHM240", "KHM242", "KHM247",
                    "KHM248", "KHM253"]


def items(ms):
    base = {r[0]: list(r) for r in V18.items(ms)}
    C = {"RC02": ("사용한 조사 자료", "Survey data used", "분석한 조사연도(기수)와 사용한 조사 구성요소(설문·검진·검사·영양)를 밝힘",
                  "Identifies the survey years (cycles) and the KNHANES components used"),
         "RC05": (None, None, "여러 해 자료를 결합한 방법(파일 병합, 통합 파일, 공통 변수, 연도 변수)을 보고함(가중치 조정은 RC07)",
                  "Reports how the yearly data were combined (merging, integrated file, common variables, year variable); weight adjustment is RC07"),
         "RC17": (None, None, "변수별, 또는 결측 양상이 같은 변수 묶음별 결측 규모를 보고함",
                  "Reports the extent of missing data for individual variables or groups of variables with a common missingness pattern"),
         "RC42": (None, None, "참여자별 중요도(예: SHAP)를 집계한 경우 가중치를 썼는지와 방법을 보고함",
                  "When participant-level importance (such as SHAP) was aggregated, states whether and how survey weights were used")}
    for k, (iko, ien, cko, cen) in C.items():
        if iko:
            base[k][2], base[k][3] = iko, ien
        base[k][4], base[k][5] = cko, cen
    base["RC42"][10] = lambda d, r: r["Importance ranking produced"] == "Yes" and any(m in str(r["Importance methods"]) for m in ("SHAP", "LIME"))
    return [tuple(v) for k, v in base.items() if k not in REMOVED]


RULE = dict(V18.RULE)
RULE["RC02"] = "RC02 (survey years) and RC03 (components) of v18 both met"
RULE["RC05"] += "; v20: weight adjustment alone no longer meets RC05 (13 studies)"
RULE["RC42"] += "; v20: applies only when SHAP or LIME importance was aggregated"


if __name__ == "__main__":
    subprocess.run([sys.executable, str(ROOT / "tools/checklist_v18.py")], check=True, stdout=subprocess.DEVNULL)
    t18 = json.load(open(ROOT / "results/derived/checklist_v18_scores.json"))
    ms, CORE, rows = _ctx()
    I = items(ms)
    i18 = {i["id"]: str(i["idx"]) for i in t18["items"]}
    out = {"items": [], "studies": {}, "removed": REMOVED}
    meta = {i["id"]: i for i in t18["items"]}
    for k, it in enumerate(I):
        m = dict(meta[it[0]]); m.update(idx=k, item_en=it[3], item_ko=it[2], rule=RULE[it[0]])
        if it[0] == "RC02":
            m["source"] = "EN"  # RC03 (full-text re-read) merged in
        out["items"].append(m)
    for d in CORE:
        sid = d["study_id"]; r = rows[sid]; st = t18["studies"][sid]; rec = {}
        for k, it in enumerate(I):
            rid = it[0]; v = st["items"].get(i18[rid])
            if rid == "RC02":
                a, b = st["items"].get(i18["RC02"]), st["items"].get(i18["RC03"])
                v = bool(a) and bool(b)
            elif rid == "RC05" and sid in RC05_WEIGHT_ONLY and v is not None:
                v = False
            elif rid == "RC42":
                v = v if it[10](d, r) else None
            if v is not None:
                rec[str(k)] = bool(v)
        out["studies"][sid] = {"items": rec, "tripod": st["tripod"], "evidence": st.get("evidence", {}),
                               "reference": {x: st["items"].get(i18[x]) for x in ("RC03", "RC04", "RC38")}}
    json.dump(out, open(ROOT / "results/derived/checklist_v20_scores.json", "w"), indent=1, ensure_ascii=False)
    S = out["studies"]
    for i in out["items"]:
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        print(i["id"], i["item_en"][:40], f"{sum(v)}/{len(v)}")
