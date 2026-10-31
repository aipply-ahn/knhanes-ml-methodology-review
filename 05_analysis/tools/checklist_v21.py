"""v21 core checklist (prompt 138, 2026-10-31): 42 items. Changes from v20:
- RC05 (how yearly data were combined) removed from the core score: when the years (RC02), the harmonisation of
  variables across years (RC46) and the weights for combined years (RC07) are reported, a simple pooling of the yearly
  data adds no independent reproduction information. RC02 now asks whether the years were analysed singly, pooled or
  separately by year; its judgements are unchanged (the year list identifies this).
- Publication IDs C01-C42 run consecutively in Table 1 order; the internal RC IDs stay in the audit records and the
  Additional Data 1 columns (mapping in the RC Codebook sheet).
- RC36 criterion wording names the unmet cases (app or inference code only, code on request, empty or broken link).
Run: python tools/checklist_v21.py -> results/derived/checklist_v21_scores.json"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import checklist_v20 as V20  # noqa: E402

STAGE, TYPE, GROUPS = V20.STAGE, V20.TYPE, V20.GROUPS
REMOVED = dict(V20.REMOVED)
REMOVED["RC05"] = "removed: pooling the yearly data adds no independent information once the years, harmonisation (RC46) and combined-year weights (RC07) are reported"


def items(ms):
    out = []
    for r in V20.items(ms):
        r = list(r)
        if r[0] == "RC05":
            continue
        if r[0] == "RC02":
            r[4] = "분석한 조사연도(기수)와 사용한 조사 구성요소(설문·검진·검사·영양)를 밝힘(한 해 분석, 여러 해 통합, 연도별 분석의 구분 포함)"
            r[5] = "Identifies the survey years (cycles) and KNHANES components used, including whether years were analysed singly, pooled or separately"
        if r[0] == "RC36":
            r[4] = "분석 코드를 공개함(앱·추론 전용 코드, 요청 시 제공, 비어 있거나 열리지 않는 저장소는 미충족)"
            r[5] = "Analysis code is publicly available (app-only or inference-only code, code on request, or an empty or broken repository does not meet it)"
        out.append(tuple(r))
    return out


RULE = dict(V20.RULE)


def display_ids(ms=None):
    """RC id -> publication id C01... in Table 1 order."""
    import checklist_v21_table as TB
    return {r[0]: f"C{k + 1:02d}" for k, r in enumerate(TB.ordered())}


if __name__ == "__main__":
    subprocess.run([sys.executable, str(ROOT / "tools/checklist_v20.py")], check=True, stdout=subprocess.DEVNULL)
    t20 = json.load(open(ROOT / "results/derived/checklist_v20_scores.json"))
    i20 = {i["id"]: str(i["idx"]) for i in t20["items"]}
    meta = {i["id"]: i for i in t20["items"]}
    from checklist_v12 import _ctx
    ms, CORE, rows = _ctx()
    I = items(ms)
    D = display_ids()
    out = {"items": [], "studies": {}, "removed": REMOVED}
    for k, it in enumerate(I):
        m = dict(meta[it[0]]); m.update(idx=k, item_en=it[3], item_ko=it[2], crit_en=it[5], crit_ko=it[4], pub_id=D[it[0]])
        out["items"].append(m)
    for sid, st in t20["studies"].items():
        rec = {str(k): st["items"][i20[it[0]]] for k, it in enumerate(I) if i20[it[0]] in st["items"]}
        ref = dict(st["reference"]); ref["RC05"] = st["items"].get(i20["RC05"])
        out["studies"][sid] = {"items": rec, "tripod": st["tripod"], "evidence": st["evidence"], "reference": ref}
    json.dump(out, open(ROOT / "results/derived/checklist_v21_scores.json", "w"), indent=1, ensure_ascii=False)
    S = out["studies"]
    for i in out["items"]:
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        print(i["pub_id"], i["id"], i["item_en"][:40], f"{sum(v)}/{len(v)}")
