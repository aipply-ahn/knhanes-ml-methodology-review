#!/usr/bin/env python3
"""Compile additional_file_review/RECORD_CORRECTIONS.tsv: every review-loop correction that changes a counted column,
as decided on 2026-10-23 (author: apply every warranted correction; composite outcomes keep all sources).

Sources, in order (a later source overrides an earlier one for the same cell):
  1. ISSUES.tsv needs-author cells that both Claude reviewers proposed with the same value;
  2. PENDING_RECLASS.tsv (method-focused columns of the studies reclassified as method-focused);
  3. OVERRIDES.tsv "Most important variables as reported" (written back to VI06 so the derived columns follow);
  4. rule decisions (coef: conventional-regression coefficients are not a model-based ranking);
  5. recode/adjudication.tsv (single adjudicator on the cells where the review chains differed): decision apply;
  6. recode/out_chunk*_A/B.tsv (two independent re-coding passes on all core studies): cells where A and B agree,
     else recode/recode_resolved.tsv when present.
Columns handled elsewhere: KNHANES survey components used (kept, rule labonly), derived variable columns
(Harmonised variables, Variable domains, Variable names and harmonised labels, outcome groups: recomputed).
"""
from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "additional_file_review"
OUT = D / "RECORD_CORRECTIONS.tsv"
SKIP = {"KNHANES survey components used", "Variable names and harmonised labels", "Harmonised variables (Figure 5)",
        "Variable domains", "Outcome group (Figure 5)", "Outcome group (Figure S7A)", "Role of KNHANES",
        "Outcome source", "Cross-validation", "Train-test split"}  # the last three come from the re-coding pass
RECODE = {"outcome_source": "Outcome source", "train_test_split": "Train-test split", "cv_evaluation": "Cross-validation"}


def tsv(p):
    return list(csv.DictReader(Path(p).open(encoding="utf-8"), delimiter="\t")) if Path(p).exists() else []


def main():
    cells = {}

    rename = {"Survey components for predictors": "KNHANES survey components used", "Sampling weights mentioned": "KNHANES sampling weights mentioned",
              "Scaling or other transformation timing": "Data-driven preprocessing separation",
              "Feature selection timing": "Supervised feature selection timing"}  # Codex rule (column names), 2026-10-23

    def put(sid, col, val, basis, ev):
        cells[(sid, rename.get(col, col))] = (val, basis, ev)

    for i in tsv(D / "recode/ISSUES_before_recoding.tsv"):  # frozen: ISSUES.tsv marks these resolved once applied
        m = re.match(r"Both reviewers propose '(.*?)'\. ", i["question"], re.S)
        if i["status"] == "needs-author" and m and i["column"] not in SKIP:
            put(i["study_id"], i["column"], m.group(1), f"both Claude reviewers ({i['issue_id']})", i["question"][m.end():])
    for o in tsv(D / "PENDING_RECLASS.tsv"):
        if o["column"].startswith("Method "):
            put(o["study_id"], o["column"], o["new_value"], "both Claude reviewers (reclassification)", o.get("source", ""))
    for o in tsv(D / "OVERRIDES.tsv"):
        if o["column"] == "Most important variables as reported":
            put(o["study_id"], o["column"], o["new_value"], "review override (variables)", o.get("source", ""))
    for sid in ("KHM013", "KHM036"):
        put(sid, "Importance ranking produced", "No", "rule coef (protocol VI01: conventional coefficients alone do not qualify)",
            "only logistic/linear regression coefficients or odds ratios are presented as the ranking")
    for a in tsv(D / "recode/adjudication.tsv"):
        if a["decision"] == "apply" and a["column"] and a["final_value"] and not a["study_id"].startswith("X"):
            put(a["study_id"], a["column"], a["final_value"], f"adjudicator ({a['issue_id']})", a["evidence"])
    for col, val in (("Method workflow stages", "Model development; validation or performance"), ("Method evaluation design", "Empirical comparator evaluation"),
                     ("Method comparators", "Proportional odds model (statistical health-space model)")):
        put("KHM143", col, val, "adjudicator (regrouped as method-focused)", "lee2025deep.md p.3 and Abstract: deep learning HS models proposed and compared with the POM-based statistical HS model")
    for sid in ("KHM186", "KHM196"):  # author decision D17 (2026-10-23): the authors designated no final model
        put(sid, "Family of the selected model", "Not reported", "author decision D17", "AUCs not significantly different; no model designated")
    for col, val in (("Method workflow stages", "Model development; validation or performance"), ("Method evaluation design", "Empirical comparator evaluation")):
        put("KHM251", col, val, "coordinator (regrouped as method-focused, rev15)", "kim2025obesity abstract: new tree plus elastic-net classifier compared with baselines; KNHANES as an illustration")
    put("KHM230", "Combining survey years", "One survey year", "adjudicator (follows survey years 2013)", "data reference: KNHANES 2013")
    put("KHM230", "Combined-year weights", "Not applicable", "follows: one survey year", "SUR11 is not applicable to one-year analyses")
    resolved = {(r["study_id"], r["column"]): r for r in tsv(D / "recode/recode_resolved.tsv")}
    order = ["Questionnaire or scale", "Physical measurement", "Laboratory value", "Diagnosis or history", "Other", "Not reported"]
    canon = lambda v: "; ".join(sorted({x.strip() for x in v.split(";") if x.strip()}, key=order.index)) if v else v
    cur_tuning = {r["Study ID"]: r["Tuning kept apart from the final evaluation"] for k in (1, 2, 3) for r in tsv(D / f"recode/chunk{k}.tsv")}
    for chunk in sorted(glob.glob(str(D / "recode/out_chunk*_A.tsv"))):
        A = {r["study_id"]: r for r in tsv(chunk)}
        B = {r["study_id"]: r for r in tsv(chunk.replace("_A.tsv", "_B.tsv"))}
        for sid, a in A.items():
            b = B[sid]
            for key, col in list(RECODE.items()) + [("selection_on_evaluation_data", "Selection on evaluation data")]:
                va, vb = a[key].strip(), b[key].strip()
                if key == "outcome_source":
                    va, vb = canon(va), canon(vb)
                if va == vb:
                    val, basis, ev = va, "re-coding pass, reviewers A and B agree", a["evidence"][:300]
                elif (sid, col) in resolved:
                    r = resolved[(sid, col)]
                    val, basis, ev = (canon(r["value"]) if key == "outcome_source" else r["value"].strip()), "re-coding pass, third reviewer", r["evidence"]
                else:
                    continue
                if col == "Selection on evaluation data":  # rule tuningtest: final model or tuning chosen on the evaluation data
                    if val == "Yes" and cur_tuning.get(sid) == "Yes":
                        put(sid, "Tuning kept apart from the final evaluation", "No", basis + " (rule tuningtest: selection on the evaluation data)", ev)
                else:
                    put(sid, col, val, basis, ev)
    for r in tsv(D / "LOOP_RECORD_CORRECTIONS.tsv"):  # review loop after 2026-10-23 (tools/data1_integrate.py)
        put(r["study_id"], r["column"], r["value"], r["basis"], r["evidence"])
    import openpyxl  # drop cells whose value already equals the current Additional Data 1 value
    rows = list(openpyxl.load_workbook(ROOT / "prompts/implementation_records/review_corrections_20261023/pristine/paper/KNHANES_ML_review_Additional_Data_1.xlsx", read_only=True).active.iter_rows(values_only=True))
    cur = {(r[0], h): str(v) for r in rows[1:] for h, v in zip(rows[0], r)}
    cells = {k: v for k, v in cells.items() if cur.get(k) != str(v[0]) or k[1] == "Most important variables as reported"}
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["study_id", "column", "value", "basis", "evidence"])
        for (sid, col), (val, basis, ev) in sorted(cells.items()):
            w.writerow([sid, col, val, basis, " ".join(str(ev).split())[:600]])
    print(len(cells), "corrections ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
