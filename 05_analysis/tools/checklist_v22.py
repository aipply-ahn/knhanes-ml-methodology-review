"""v22 core checklist (author 2026-10-31): 43 items. TRIPOD+AI element 19 (registration, data and code availability)
asks where and how the study data can be obtained again; v21 specified only code availability. RC47 'Data
availability' is added (judged from the full texts: coding_audit/rc47_data_availability.tsv) and placed before code
availability in Table 1. Rest = v21.
Run: python tools/checklist_v22.py -> results/derived/checklist_v22_scores.json"""
import csv, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import checklist_v21 as V21  # noqa: E402

STAGE, TYPE, GROUPS, REMOVED = V21.STAGE, V21.TYPE, V21.GROUPS, V21.REMOVED
RC47 = ("RC47", 19, "자료 공개", "Data availability",
        "연구 자료를 이용할 수 있는지와 그 방법(예: KNHANES 누리집과 이용 절차, 저장소, 요청 시 제공과 조건, 공유가 제한되는 이유)을 밝힘(TRIPOD+AI 18e). 자료원만 밝힌 것(5a)은 미충족",
        "Gives details of the availability of the study data: whether and how they can be accessed (such as the KNHANES website and access procedure, a repository, availability on request with any conditions, or why sharing is restricted) (TRIPOD+AI 18e); naming the data source only (item 5a) does not meet it",
        "D", "R", "N", lambda d, r: None, lambda d, r: True)
FILE = ROOT / "prompts/implementation_records/coding_audit/rc47_data_availability.tsv"


def items(ms):
    return list(V21.items(ms)) + [RC47]


RULE = dict(V21.RULE)
RULE["RC47"] = "full-text reading 2026-10-31 against TRIPOD+AI item 18e (details of the availability of the study data, in a data availability statement or elsewhere in the text); basis per study in coding_audit/rc47_data_availability.tsv"
ORDER = {"RC47": "RC355"}  # Table 1: data availability before code availability (RC36)


if __name__ == "__main__":
    subprocess.run([sys.executable, str(ROOT / "tools/checklist_v21.py")], check=True, stdout=subprocess.DEVNULL)
    t = json.load(open(ROOT / "results/derived/checklist_v21_scores.json"))
    da = {r["study_id"]: (int(r["RC47"]), r["basis"]) for r in csv.DictReader(open(FILE), delimiter="\t")}
    import checklist_v22_table as TB
    D = {r[0]: f"C{k + 1:02d}" for k, r in enumerate(TB.ordered())}
    k = len(t["items"])
    t["items"].append({"idx": k, "id": "RC47", "tripod": 19, "item_en": RC47[3], "item_ko": RC47[2], "stage": "D", "note": "R",
                       "source": "N", "rule": RULE["RC47"], "repro": True, "scored": True, "crit_en": RC47[5], "crit_ko": RC47[4]})
    for i in t["items"]:
        i["pub_id"] = D[i["id"]]
    for sid, st in t["studies"].items():
        st["items"][str(k)] = bool(da[sid][0])
        st["evidence"]["RC47"] = da[sid][1]
    json.dump(t, open(ROOT / "results/derived/checklist_v22_scores.json", "w"), indent=1, ensure_ascii=False)
    S = t["studies"]
    for i in sorted(t["items"], key=lambda i: i["pub_id"]):
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        print(i["pub_id"], i["id"], i["item_en"][:40], f"{sum(v)}/{len(v)}")
