#!/usr/bin/env python3
"""Merge the independent Codex review chain (additional_file_review/cycles/, two Codex reviewers, final rev05) into the
Claude chain (OVERRIDES.tsv, ISSUES.tsv). The Codex final file is treated as one more reviewer pair's integrated result.

For every cell where the Codex final differs from the current submitted file:
- a systematic vocabulary change (the same old -> new pair across many rows, or a renamed column) becomes a RULE question
  for the author (not applied);
- a cell in a column that feeds a published count (core rows, or a column counted for every group) becomes a
  `needs-author` issue carrying the Codex evidence; if the Claude chain already proposes the same value, it is marked
  as agreed by both chains;
- otherwise the value is applied as an override, unless a Claude reviewer's latest verdict on that cell kept the
  current value (then it becomes a `disputed` issue), or the Codex value is the generic "Journal article" replacing a
  specific report type.
Writes additional_file_review/codex_merge/{MERGE.json, RULES.json}.
"""
import csv
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "additional_file_review"
CODEX_FINAL = D / "cycles/cycle004_20261023_0800/integrated/KNHANES_ML_review_Additional_Data_1_rev05.xlsx"
sys.path.insert(0, str(ROOT / "tools"))
from data1_integrate import FREE, HARMONISATION, ALL_GROUP_COUNTED, FIELDS  # noqa: E402

RULE_MIN = 8  # an old -> new pair repeated in at least this many rows is a vocabulary rule, not a cell finding


def sheet(p):
    rows = list(load_workbook(p, read_only=True).active.iter_rows(values_only=True))
    return list(rows[0]), {r[0]: r for r in rows[1:]}


def main():
    out = D / "codex_merge"; out.mkdir(exist_ok=True)
    hm, M = sheet(ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx")
    hc, C = sheet(CODEX_FINAL)
    assert len(hm) == len(hc) and set(M) == set(C)
    group = {s: M[s][hm.index("Study group")] for s in M}
    # Codex evidence: latest correction per cell across its cycles
    ev = {}
    for f in sorted(glob.glob(str(D / "cycles/cycle00*/DECISIONS.json"))):
        for c in json.load(open(f)).get("corrections", []):
            ev[(c["study_id"], c["column"])] = {k: c.get(k, "") for k in ("old_value", "new_value", "evidence", "reason", "adoption")} | {"cycle": Path(f).parent.name}
    # Claude reviewers' latest verdict per cell
    claude = {}
    for f in sorted(glob.glob(str(D / "rev*_*/review_[AB].tsv"))):
        for r in csv.DictReader(open(f, encoding="utf-8"), delimiter="\t"):
            claude[(r["study_id"], r["column"], f[-5])] = r
    issues = list(csv.DictReader((D / "ISSUES.tsv").open(encoding="utf-8"), delimiter="\t"))
    idx = {(i["study_id"], i["column"]): i for i in issues if i["status"] in ("open", "needs-author", "disputed")}
    ovs = list(csv.DictReader((D / "OVERRIDES.tsv").open(encoding="utf-8"), delimiter="\t"))
    ov_keys = {(o["study_id"], o["column"]) for o in ovs}
    diffs = []
    for s in M:
        for j, col in enumerate(hm):
            a, b = M[s][j], C[s][j]
            if str(a) != str(b):
                diffs.append((s, col, str(a), str(b)))
    pair = Counter((col, a, b) for s, col, a, b in diffs)
    rules = defaultdict(list)
    res = {"rules": 0, "applied": [], "needs_author": [], "corroborated": [], "disputed": [], "skipped": []}
    for s, col, a, b in diffs:
        k = (s, col)
        e = ev.get(k) or ev.get((s, hc[hm.index(col)])) or {}
        if pair[(col, a, b)] >= RULE_MIN:
            rules[f"{col}: {a} -> {b}"].append(s); continue
        counted = (group[s] == "Core classification" and col not in FREE) or col in ALL_GROUP_COUNTED or col in HARMONISATION
        kept = [claude.get((s, col, w)) for w in "AB"]
        if col == "Report type" and b == "Journal article" and a not in ("NR", ""):
            res["skipped"].append([s, col, a, b, "Codex generic type; specific type kept"]); continue
        q = f"Codex chain (two reviewers, {e.get('cycle', 'final file')}) proposes '{b}'. Evidence: {e.get('evidence', 'see cycles/')[:400]} Reason: {e.get('reason', '')[:250]}"
        if counted:
            i = idx.get(k)
            if i and i["status"] == "needs-author" and f"'{b}'" in i["question"]:
                i["question"] = (i["question"] + " | Also proposed by the Codex chain.")[:900]
                res["corroborated"].append([s, col, b]); continue
            if i:
                i.update(status="needs-author", question=(i["question"] + " | " + q)[:900])
            else:
                i = dict(issue_id=f"I{len(issues) + 1:03d}", status="needs-author", type="codex-count-change", study_id=s, column=col,
                         value=a, question=q[:900], raised_rev="codex", closed_rev="", resolution="")
                issues.append(i); idx[k] = i
            res["needs_author"].append([s, col, a, b]); continue
        if any(r and r["verdict"] == "ok" for r in kept):
            i = idx.get(k) or dict(issue_id=f"I{len(issues) + 1:03d}", status="open", type="disputed", study_id=s, column=col, value=a,
                                   question="", raised_rev="codex", closed_rev="", resolution="")
            if k not in idx:
                issues.append(i); idx[k] = i
            i.update(status="open", type="disputed", question=("A Claude reviewer kept the current value; " + q)[:900])
            res["disputed"].append([s, col, a, b]); continue
        ovs = [o for o in ovs if (o["study_id"], o["column"]) != k]
        ovs.append(dict(study_id=s, column=col, new_value=b, reason="Codex chain (two reviewers) correction; free column",
                        source=(e.get("evidence", "") or "cycles/ final rev05")[:500].replace("\t", " ").replace("\n", " "), revision="rev06"))
        if k in idx and idx[k]["status"] in ("open", "disputed"):
            idx[k].update(status="resolved", closed_rev="rev06", resolution=f"Codex chain correction applied: {b}"[:300])
        res["applied"].append([s, col, a, b])
    renamed = [[x, y] for x, y in zip(hm, hc) if x != y]
    rule_list = [{"key": f"codex{n + 1}", "change": ch, "n": len(ids), "examples": ids[:12],
                  "evidence": next((ev[(s, ch.split(':')[0])]["reason"] for s in ids if (s, ch.split(':')[0]) in ev), "")}
                 for n, (ch, ids) in enumerate(sorted(rules.items(), key=lambda x: -len(x[1])))]
    rule_list.append({"key": "codex_rename", "change": "Rename columns: " + "; ".join(f"{x} -> {y}" for x, y in renamed), "n": len(renamed),
                      "examples": [], "evidence": "Codex: the column definitions (protocol items DAT14, SUR04, PRE14, PRE13) are wider than the current names."})
    res["rules"] = len(rule_list)
    with (D / "OVERRIDES.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["study_id", "column", "new_value", "reason", "source", "revision"], delimiter="\t"); w.writeheader(); w.writerows(ovs)
    with (D / "ISSUES.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS, delimiter="\t"); w.writeheader(); w.writerows(issues)
    json.dump(res, open(out / "MERGE.json", "w"), ensure_ascii=False, indent=1)
    json.dump(rule_list, open(out / "RULES.json", "w"), ensure_ascii=False, indent=1)
    print({k: (v if isinstance(v, int) else len(v)) for k, v in res.items()}, "diff cells", len(diffs))


if __name__ == "__main__":
    main()
