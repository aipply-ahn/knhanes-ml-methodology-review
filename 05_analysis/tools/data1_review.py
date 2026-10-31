#!/usr/bin/env python3
"""Review folder for Additional Data 1 (additional_file_review/): numbered revisions with flagged cells and an issue list.

    python tools/data1_review.py new      snapshot manuscript/KNHANES_ML_review_Additional_Data_1.xlsx as the next revision
    python tools/data1_review.py status   print open issues by type

Each revision folder revNN_YYYYMMDD/ holds
    KNHANES_ML_review_Additional_Data_1_revNN.xlsx  review copy: the submitted sheet, open-issue cells filled yellow with
                                                    the question as a cell note, changed cells (vs the previous revision)
                                                    filled light blue
    CHANGES.md                                      cells changed since the previous revision, issues opened and closed
ISSUES.tsv (one row per questionable cell) is the running list; edit status/resolution by hand
(open | resolved | accepted). REVISIONS.md is the revision log. The submitted file in paper/ is never modified here.
"""
import csv
import hashlib
import shutil
import sys
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from main_figure_map import internal_header
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx"
DIR = ROOT / "additional_file_review"
ISSUES = DIR / "ISSUES.tsv"
LOG = DIR / "REVISIONS.md"
FIELDS = ["issue_id", "status", "type", "study_id", "column", "value", "question", "raised_rev", "closed_rev", "resolution"]
YELLOW, BLUE = PatternFill("solid", fgColor="FFF2A8"), PatternFill("solid", fgColor="DCEBFA")

# Values that mark a gap or doubt in OUR record (to be resolved), not a state the source report itself left unclear
# ("Timing unclear", "Not reported", PROBAST+AI "UNCLEAR" are recorded source states and are not flagged).
GAP_RULES = [
    ("missing", lambda col, v: v in ("Not recorded", "not recorded"), "No value in our record: find it in the source or state why it cannot be given."),
    ("coder-unclear", lambda col, v: v in ("Unclear", "UNCLEAR") and not col.startswith("PROBAST"), "Coded as unclear: re-read the source and decide, or keep with a reason."),
    ("no-evidence", lambda col, v: col == "Evidence locations" and v == "None linked", "No evidence location linked for this study's coded items."),
    ("no-harmonised", lambda col, v: col == "Harmonised variables (Figure 5)" and v == "None harmonised", "Ranking variables named but none matched the harmonisation patterns."),
]


def read_sheet(path):
    ws = load_workbook(path, read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    return [internal_header(h) for h in rows[0]], {r[0]: r for r in rows[1:]}


def load_issues():
    if not ISSUES.exists():
        return []
    with ISSUES.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def save_issues(issues):
    with ISSUES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(issues)


def revisions():
    return sorted(p for p in DIR.glob("rev[0-9][0-9]_*") if p.is_dir())


def new():
    DIR.mkdir(exist_ok=True)
    prev = revisions()
    n = len(prev) + 1
    tag = f"rev{n:02d}"
    out = DIR / f"{tag}_{date.today():%Y%m%d}"
    out.mkdir()
    head, rows = read_sheet(SRC)
    issues = load_issues()
    known = {(i["study_id"], i["column"]) for i in issues}
    opened = []
    for sid, r in rows.items():
        for col, v in zip(head, r):
            for kind, rule, question in GAP_RULES:
                if rule(col, v) and (sid, col) not in known:
                    issue = dict(issue_id=f"I{len(issues) + 1:03d}", status="open", type=kind, study_id=sid, column=col, value=str(v),
                                 question=question, raised_rev=tag, closed_rev="", resolution="")
                    issues.append(issue); opened.append(issue); known.add((sid, col))
    # An open issue whose cell no longer holds the flagged value is closed by this revision.
    closed = []
    for i in issues:
        if i["status"] == "open" and i["study_id"] in rows:
            v = rows[i["study_id"]][head.index(i["column"])] if i["column"] in head else None
            if str(v) != i["value"]:
                if i["type"] in ("disputed", "label"):  # reviewer disagreement is settled by the reviews, not by a display change
                    i["value"] = str(v)
                    continue
                i.update(status="resolved", closed_rev=tag, resolution=i["resolution"] or f"value changed to: {v}")
                closed.append(i)
    save_issues(issues)
    # Cell-level changes against the previous revision.
    changes = []
    if prev:
        ph, prows = read_sheet(next(prev[-1].glob("*.xlsx")))
        for sid, r in rows.items():
            old = prows.get(sid)
            for col, v in zip(head, r):
                o = old[ph.index(col)] if old is not None and col in ph else None
                if old is None or str(o) != str(v):
                    changes.append((sid, col, o, v))
        changes += [(sid, "(row removed)", None, None) for sid in prows if sid not in rows]
    # Review copy: submitted sheet with flags.
    dst = out / f"KNHANES_ML_review_Additional_Data_1_{tag}.xlsx"
    shutil.copy2(SRC, dst)
    wb = load_workbook(dst)
    ws = wb.active
    rix = {ws.cell(i, 1).value: i for i in range(2, ws.max_row + 1)}
    cix = {c.value: c.column for c in ws[1]}
    for sid, col, _, _ in changes:
        if sid in rix and col in cix:
            ws.cell(rix[sid], cix[col]).fill = BLUE
    for i in issues:
        if i["status"] == "open" and i["study_id"] in rix and i["column"] in cix:
            c = ws.cell(rix[i["study_id"]], cix[i["column"]])
            c.fill = YELLOW
            # Neutral note only: earlier reviewers' views stay in ISSUES.tsv so the next reviews remain blind to them.
            c.comment = Comment(f"{i['issue_id']}: open issue, check this cell against the source.", "review", width=260, height=50)
    wb.save(dst)
    sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    n_open = sum(i["status"] == "open" for i in issues)
    md = [f"# Additional Data 1, {tag} ({date.today():%Y-%m-%d})", "",
          f"Source: manuscript/KNHANES_ML_review_Additional_Data_1.xlsx (sha256 {sha[:16]}), {len(rows)} rows x {len(head)} columns.",
          "In the review copy: yellow = open issue (cell note gives the question), light blue = changed since the previous revision.", "",
          f"## Changed cells since {prev[-1].name if prev else '(first revision)'}: {len(changes)}"]
    md += [f"- {sid} | {col}: {o!r} -> {v!r}" for sid, col, o, v in changes[:300]]
    if len(changes) > 300:
        md.append(f"- ... {len(changes) - 300} more")
    md += ["", f"## Issues opened: {len(opened)}"] + [f"- {i['issue_id']} {i['study_id']} | {i['column']}: {i['value']} ({i['type']})" for i in opened]
    md += ["", f"## Issues closed: {len(closed)}"] + [f"- {i['issue_id']} {i['study_id']} | {i['column']}: {i['resolution']}" for i in closed]
    md += ["", f"Open issues after this revision: {n_open}"]
    (out / "CHANGES.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if not LOG.exists():
        LOG.write_text("# Additional Data 1 revisions\n\n| Revision | Date | Source sha256 | Changed cells | Opened | Closed | Open after |\n|---|---|---|---|---|---|---|\n", encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"| {tag} | {date.today():%Y-%m-%d} | {sha[:16]} | {len(changes) if prev else '-'} | {len(opened)} | {len(closed)} | {n_open} |\n")
    print(f"{out.relative_to(ROOT)}: {len(changes)} changed cells, {len(opened)} opened, {len(closed)} closed, {n_open} open")


def status():
    from collections import Counter
    issues = load_issues()
    print(Counter((i["status"], i["type"]) for i in issues))


if __name__ == "__main__":
    {"new": new, "status": status}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
