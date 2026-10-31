#!/usr/bin/env python3
"""Integrate phase of the Additional Data 1 review loop (additional_file_review/CYCLE.md).

    python tools/data1_integrate.py revNN_YYYYMMDD     merge review_A/B.tsv of that revision into OVERRIDES.tsv and ISSUES.tsv

Rules
- both reviewers `correct` with the same proposed value:
    * cell in a column that feeds a published count (core rows: the coded columns behind Figures 2-7 and Table 1, and the
      variable-name harmonisation behind Figure 5) -> issue `needs-author` (changing it changes the paper's numbers);
    * Study label -> override only if the label does not collide with another row's label, else `needs-author`;
    * otherwise -> appended to OVERRIDES.tsv.
- both `ok` -> the issue (if any) is `accepted` with both reasons.
- anything else -> issue `open`, type `disputed`, with both views.
Writes revNN/.integration.json for INTEGRATION.md. The rebuild and `data1_review.py new` are separate steps.
"""
import csv
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

from main_figure_map import internal_header

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "additional_file_review"
FIELDS = ["issue_id", "status", "type", "study_id", "column", "value", "question", "raised_rev", "closed_rev", "resolution"]
# Columns whose values are not counted in any published figure or table (display, identification, notes).
FREE = {"Study", "Title", "Journal", "Year", "DOI or PMID", "Report type", "Reason not included", "Outcome",
        "Most important variables as reported", "Evidence locations", "Other-health algorithms", "Other-health internal validation",
        "Other-health validation beyond the development data", "Other-health importance", "Method workflow stages",
        "Method evaluation design", "Method comparators"}
ALL_GROUP_COUNTED = {"Added under the final eligibility criterion", "Study group", "Task", "Year", "Publication period"}  # counted for every group
HARMONISATION = {"Variable names and harmonised labels", "Harmonised variables (Figure 5)", "Variable domains"}


LOOP = DIR / "LOOP_RECORD_CORRECTIONS.tsv"  # read by tools/compile_review_corrections.py
RECORD_COLUMNS = {  # columns tools/review_corrections.py can write back to the records
    "Outcome rebuildable from the report", "Source sample and total excluded",  # coding audit 2026-10-29
    "Algorithm families fitted", "Systematic hyperparameter search", "Tuning kept apart from the final evaluation", "Family of the selected model",
    "Initial candidate predictors", "Final analytic sample", "Outcome source", "Health topic", "Importance ranking produced",
    "Ranking stability checked", "Several algorithms compared", "Confidence interval reported", "KNHANES sampling weights mentioned",
    "Ranking used for a reduced predictor set", "Ranking used to guide a statistical analysis", "Analysis code shared",
    "Final model fully specified", "Weights in model fitting", "Weights in performance evaluation", "Strata or PSUs in variance estimation",
    "Combined-year weights", "Importance methods", "Stability approach", "Train-test split", "Cross-validation",
    "Validation on a later survey period", "Validation on external data", "Missing-value handling timing",
    "Data-driven preprocessing separation", "Supervised feature selection timing", "Class rebalancing timing", "Missing-value handling",
    "Survey years", "Combining survey years", "Year", "Most important variables as reported", "Study group", "Task", "Variable domains"}
DERIVED_COLUMNS = {"Harmonised variables (Figure 5)", "Outcome group (Figure 5)", "Outcome group (Figure S7A)",
                   "Added under the final eligibility criterion"}  # -> DERIVED_OVERRIDES.tsv


def load(f):
    with open(f, encoding="utf-8") as fh:
        return {(r["study_id"], r["column"]): r for r in csv.DictReader(fh, delimiter="\t")}


def view(r):
    if not r:
        return "no row"
    s = r["verdict"] + (f" -> {r['proposed_value']}" if r.get("proposed_value") else "")
    return s + (f" ({r['note'][:200]})" if r.get("note") else "")


def main(revdir):
    rev = DIR / revdir
    tag_next = f"rev{int(revdir[3:5]) + 1:02d}"
    A, B = load(rev / "review_A.tsv"), load(rev / "review_B.tsv")
    wb = load_workbook(next(rev.glob("*.xlsx")), read_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    head = [internal_header(h) for h in rows[0]]; data = {r[0]: r for r in rows[1:]}
    labels = {r[head.index("Study")]: r[0] for r in rows[1:]}
    group = {r[0]: r[head.index("Study group")] for r in rows[1:]}
    issues = list(csv.DictReader((DIR / "ISSUES.tsv").open(encoding="utf-8"), delimiter="\t"))
    idx = {(i["study_id"], i["column"]): i for i in issues if i["status"] in ("open", "needs-author")}
    with (DIR / "OVERRIDES.tsv").open(encoding="utf-8") as fh:
        ov = list(csv.DictReader(fh, delimiter="\t"))
    ov_keys = {(o["study_id"], o["column"]) for o in ov}
    out = {"applied": [], "accepted": [], "needs_author": [], "disputed": []}

    def issue(k, status, kind, question, value):
        i = idx.get(k)
        if i:
            i.update(status=status, question=question[:700])
            if status == "open" and i["type"] in ("missing",):
                i["type"] = kind
        else:
            i = dict(issue_id=f"I{len(issues) + 1:03d}", status=status, type=kind, study_id=k[0], column=k[1], value=value,
                     question=question[:700], raised_rev=revdir[:5], closed_rev="", resolution="")
            issues.append(i); idx[k] = i

    # A reviewer may check a whole row with one "(all cells)" / "(all other cells of the row)" ok line: it stands for every
    # cell of that row the reviewer did not list separately (review 20261023).
    rowok = {who: {k[0] for k, r in R.items() if k[1].startswith("(all") and r["verdict"] == "ok"} for who, R in (("A", A), ("B", B))}
    A = {k: r for k, r in A.items() if not k[1].startswith("(all")}
    B = {k: r for k, r in B.items() if not k[1].startswith("(all")}
    scope = {(r["study_id"], r["column"]) for r in csv.DictReader((rev / "SCOPE.tsv").open(encoding="utf-8"), delimiter="\t")} \
        if (rev / "SCOPE.tsv").exists() else set()
    for k in sorted(set(A) | set(B)):
        a, b = A.get(k), B.get(k)
        # Reviewers write a row for every SCOPE cell and for problem cells only: outside SCOPE a missing row means "no problem".
        if k not in scope:
            if a is None:
                a = dict(b, verdict="ok", note="no problem reported", evidence="")
            if b is None:
                b = dict(a, verdict="ok", note="no problem reported", evidence="")
        if a is None and k[0] in rowok["A"]:
            a = dict(b, verdict="ok", note="whole-row check", evidence="")
        if b is None and k[0] in rowok["B"]:
            b = dict(a, verdict="ok", note="whole-row check", evidence="")
        cur = (a or b)["current_value"]
        if a and b and a["verdict"] == b["verdict"] == "correct" and a["proposed_value"].strip() == b["proposed_value"].strip():
            val = a["proposed_value"].strip()
            sid, col = k
            counted = (group.get(sid) == "Core classification" and col not in FREE) or col in ALL_GROUP_COUNTED
            if col in DERIVED_COLUMNS:  # read by tools/practice_trends.py (DERIVED)
                f = DIR / "DERIVED_OVERRIDES.tsv"
                with f.open("a", encoding="utf-8") as fh:
                    if fh.tell() == 0:
                        fh.write("study_id\tcolumn\tvalue\tbasis\n")
                    fh.write(f"{sid}\t{col}\t{val}\tboth reviewers ({revdir[:5]})\n")
                if k in idx:
                    idx[k].update(status="resolved", closed_rev=tag_next, resolution=f"both reviewers agreed; derived override '{val[:80]}'")
                out.setdefault("records", []).append([sid, col, val]); continue
            if (counted or col in HARMONISATION) and col in RECORD_COLUMNS:
                # Author, 2026-10-23: apply every warranted correction to the records and recompute (rebuild.sh);
                # the manuscript numbers are refreshed once the loop stops.
                with LOOP.open("a", encoding="utf-8") as fh:
                    if fh.tell() == 0:
                        fh.write("study_id\tcolumn\tvalue\tbasis\tevidence\n")
                    ev = ("A: " + a["evidence"] + " | B: " + b["evidence"]).replace("\t", " ").replace("\n", " ")[:500]
                    fh.write(f"{sid}\t{col}\t{val}\tboth reviewers ({revdir[:5]})\t{ev}\n")
                if k in idx:
                    idx[k].update(status="resolved", closed_rev=tag_next, resolution=f"both reviewers agreed; written to the records '{val[:80]}'")
                out.setdefault("records", []).append([sid, col, val]); continue
            if col in HARMONISATION or counted:
                why = "Figure 5 harmonisation (derived: fix the source column or the patterns)" if col in HARMONISATION else "a published count with no record handler"
                issue(k, "needs-author", "agreed-count-change", f"Both reviewers propose '{val}'. Not applied: it changes {why}. "
                      f"A: {a['evidence'][:150]} | B: {b['evidence'][:150]}", cur)
                out["needs_author"].append([sid, col, val, why]); continue
            if False and col == "Study":  # prompt loop cycle 3: labels set the surname-year base; lettering is automatic
                issue(k, "needs-author", "label-collision", f"Both reviewers propose '{val}', but that label is already used by {labels[val]}; "
                      "the generator's lettering must be fixed.", cur)
                out["needs_author"].append([sid, col, val, "label collision"]); continue
            if k in ov_keys:
                ov = [o for o in ov if (o["study_id"], o["column"]) != k]
            ov.append(dict(study_id=sid, column=col, new_value=val, reason=f"both reviewers: correct ({revdir[:5]})",
                           source=("A: " + a["evidence"] + " | B: " + b["evidence"]).replace("\t", " ").replace("\n", " ")[:500], revision=tag_next))
            if k in idx:
                idx[k].update(status="resolved", closed_rev=tag_next, resolution=f"both reviewers agreed; applied '{val}'")
            out["applied"].append([sid, col, val])
        elif a and b and a["verdict"] == b["verdict"] == "ok":
            if k in idx:
                idx[k].update(status="accepted", closed_rev=tag_next,
                              resolution=("A: " + a["note"] + " | B: " + b["note"]).replace("\t", " ").replace("\n", " ")[:400])
            out["accepted"].append(list(k))
        else:
            issue(k, "open", "disputed", f"Reviewers differ. A: {view(a)}. B: {view(b)}".replace("\t", " ").replace("\n", " "), cur)
            out["disputed"].append(list(k))
    with (DIR / "OVERRIDES.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["study_id", "column", "new_value", "reason", "source", "revision"], delimiter="\t")
        w.writeheader(); w.writerows(ov)
    with (DIR / "ISSUES.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS, delimiter="\t")
        w.writeheader(); w.writerows(issues)
    (rev / ".integration.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main(sys.argv[1])
