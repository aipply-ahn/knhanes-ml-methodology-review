"""v17 (prompt 135): logical checks between raw practice codes and the RC judgements of tools/checklist_v17.py.
Each rule names a raw state that implies an RC value; violations are listed for re-reading. Writes
prompts/implementation_records/v17_recode/consistency_checks.json."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from checklist_v12 import _ctx  # noqa: E402


def main():
    ms, CORE, rows = _ctx()
    t = json.load(open(ROOT / "results/derived/checklist_v17_scores.json"))
    idx = {i["id"]: str(i["idx"]) for i in t["items"]}
    v = lambda sid, rc: t["studies"][sid]["items"].get(idx[rc], "NA")
    f = ms.first
    R = [  # (name, condition on raw codes, RC, expected value(s))
     ("weights used in fitting -> RC24 met or weights named but method missing", lambda d, r: f(d, "SUR06") == "USED", "RC24", {True, False}),
     ("weights explicitly not used in fitting -> RC24 judged", lambda d, r: f(d, "SUR06") == "NOT_USED", "RC24", {True, False}),
     ("weights in evaluation used -> RC32 met", lambda d, r: f(d, "SUR07") == "USED", "RC32", {True}),
     ("all preprocessing within training data -> RC20 met", lambda d, r: r["Preprocessing over all applied steps"] == "All within the training data", "RC20", {True}),
     ("timing unclear -> RC20 not met", lambda d, r: r["Preprocessing over all applied steps"] == "Timing unclear", "RC20", {False, "NA"}),
     ("stability checked -> RC43 met", lambda d, r: r["Ranking stability checked"] == "Yes", "RC43", {True}),
     ("no ranking -> RC39-RC44 NA", lambda d, r: r["Importance ranking produced"] != "Yes", "RC40", {"NA"}),
     ("single survey year -> RC05/RC46 NA", lambda d, r: r["Combining survey years"] not in ("Several cycles", "Several years of one cycle"), "RC46", {"NA"}),
     ("code shared -> RC36 met", lambda d, r: f(d, "MOD15") == "USED", "RC36", {True}),
     ("calibration reported -> RC37 met", lambda d, r: r["Calibration reported"] == "Yes", "RC37", {True}),
     ("outcome rebuildable -> RC10 met", lambda d, r: r["Outcome rebuildable from the report"] == "Yes", "RC10", {True}),
     ("AUROC not reported -> RC30 not met", lambda d, r: r["AUROC reported"] != "Yes", "RC30", {False}),
    ]
    out = []
    for name, cond, rc, ok in R:
        bad = [d["study_id"] for d in CORE if cond(d, rows[d["study_id"]]) and v(d["study_id"], rc) not in ok]
        n = sum(cond(d, rows[d["study_id"]]) for d in CORE)
        out.append({"rule": name, "item": rc, "studies_with_condition": n, "violations": bad})
        print(f"{name}: {n} studies, {len(bad)} violations {bad[:6]}")
    json.dump(out, open(ROOT / "prompts/implementation_records/v17_recode/consistency_checks.json", "w"), indent=1)


if __name__ == "__main__":
    main()
