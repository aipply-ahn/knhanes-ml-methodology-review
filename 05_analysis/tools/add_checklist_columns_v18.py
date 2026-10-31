"""v18 (coding audit 2026-10-29; was v17, v16): core checklist judgements RC01-RC46 in Additional Data 1, with two documentation sheets:
'RC Codebook' (criterion, not-met and NA conditions, stage, type, source and rule of each item) and 'Scoring definitions'.
Raw protocol codes stay in the other columns, so a 0 for reporting can be told apart from a step not performed.
Replaces any earlier RC block. Called at the end of build_data1_workbook.py."""
import json, sys
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, Alignment, PatternFill
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx"
NA = {"RC05": "only one survey year analysed (established; the item applies when the years are unclear)", "RC46": "only one survey year analysed (established; the item applies when the years are unclear)",
      "RC07": "years not combined, or weights not used in the analysis", "RC16": "no derived predictors",
      "RC20": "no data-dependent preprocessing step", "RC21": "no class rebalancing", "RC24": "the model was fitted on non-KNHANES data (KNHANES used only for validation; KHM003)",
      "RC25": "no hyperparameter tuning", "RC31": "no threshold-based measure reported",
      "RC39": "no variable-importance ranking", "RC40": "no variable-importance ranking", "RC41": "no variable-importance ranking",
      "RC42": "no variable-importance ranking", "RC43": "no variable-importance ranking", "RC44": "no variable-importance ranking",
      "RC45": "ranking not used to carry variables into a reduced model or later analysis"}
HDR = PatternFill("solid", fgColor="DDEBF7")


def main():
    import checklist_v18_table as TB, checklist_v18 as CK
    from checklist_v12 import TRIPOD
    t = json.load(open(ROOT / "results/derived/checklist_v18_scores.json"))
    assert not t["missing_recode"], f"recoding incomplete: {len(t['missing_recode'])} studies"
    idx = {i["id"]: str(i["idx"]) for i in t["items"]}
    wb = load_workbook(OUT); ws = wb["Additional Data 1"]
    hdr = [c.value for c in ws[1]]
    if any(str(h).startswith("RC01") for h in hdr):  # rerun: replace the RC block
        k0 = next(i for i, h in enumerate(hdr) if str(h).startswith("RC01"))
        ws.delete_cols(k0 + 1, len(hdr) - k0); hdr = hdr[:k0]
    for name in ("RC Codebook", "Scoring definitions"):
        if name in wb.sheetnames:
            del wb[name]
    col0 = len(hdr) + 1
    rows = TB.ordered()
    for k, r in enumerate(rows):
        c = ws.cell(row=1, column=col0 + k, value=f"{r[0]} {r[3]}")
        c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical="top")
        c.comment = Comment(f"Core checklist item {r[0]} (Table 1). Met (1) if: {r[5]} NA: {NA.get(r[0], 'never')}. Source: {CK.RULE[r[0]]}.", "Additional Data 1", width=320, height=140)
    ev_col = col0 + len(rows)
    for row in range(2, ws.max_row + 1):
        st = t["studies"].get(ws.cell(row=row, column=1).value)
        if not st:
            continue
        for k, r in enumerate(rows):
            v = st["items"].get(idx[r[0]])
            ws.cell(row=row, column=col0 + k, value="NA" if v is None else int(v))
        ws.cell(row=row, column=ev_col, value=" | ".join(f"{k}: {e}" for k, e in sorted(st["evidence"].items()))[:32000])
    c = ws.cell(row=1, column=ev_col, value="Core checklist evidence (full-text items)")
    c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical="top")
    c.comment = Comment("Short quotes from the full text supporting the judgements of the items read from the full text "
                        "(source 'full-text reading' in the RC Codebook sheet). Evidence for items judged from existing codes is in 'Evidence locations' under the protocol codes named in the RC Codebook.",
                        "Additional Data 1", width=320, height=120)
    cb = wb.create_sheet("RC Codebook")
    cb.append(["ID", "TRIPOD+AI-derived element", "Core item", "Met (1)", "Not met (0)", "Not applicable (NA)", "Stage", "Type", "Source and rule", "Studies met / applicable"])
    S = t["studies"]
    for r in rows:
        el = f"{r[1]}. {TRIPOD[r[1] - 1][1]}" if isinstance(r[1], int) else "(None) " + CK.GROUPS[r[1]][1]
        v = [S[s]["items"][idx[r[0]]] for s in S if idx[r[0]] in S[s]["items"]]
        cb.append([r[0], el, r[3], r[5], "The report does not meet the requirement (information absent or insufficient).", NA.get(r[0], "never (applies to all 193 core studies)"),
                   CK.STAGE[r[6]][1], CK.TYPE[r[7]][1], CK.RULE[r[0]], f"{sum(v)}/{len(v)}"])
    sd = wb.create_sheet("Scoring definitions")
    for line in [("Term", "Definition"),
                 ("Item value", "1 = met, 0 = not met, NA = not applicable (condition in the RC Codebook). Items judge reporting, not practice: for example, RC24 is met when a study states that weights were not used in model fitting and why."),
                 ("Study score", "Percentage of applicable items met (items with NA excluded from numerator and denominator)."),
                 ("Stage scores", "Same percentage over the items of one stage: Data (rebuilding the analysis dataset), Model (reproducing the model and performance estimates), Importance (reproducing the variable-importance results); Reporting items are needed for interpretation and appraisal."),
                 ("KNHANES-specific score", "Same percentage over the items of type Specified (KNHANES) or New (KNHANES)."),
                 ("Item percentage (Figure 5)", "Studies meeting the item divided by the studies to which it applies."),
                 ("Comparing scores", "Scores over different item sets (stages, KNHANES-specific items, all items) describe completeness of different information; they are not quality comparisons between studies or between stages."),
                 ("Reporting versus practice", "A met item means the information was reported, not that the practice was appropriate (for example, RC20 is met when preprocessing was reported as done before the split; whether it was done within the training data is a separate practice code)."),
                 ("Interpretation", "A descriptive measure of the completeness of the information needed for reproduction; not verified reproducibility, not a validated quality score. The checklist was developed and applied in the same 193 studies (a demonstration, not an external validation)."),
                 ("Coding audit", "All 8,878 judgements were checked against the full texts by two independent AI reviewers (Claude Code and Codex) in rounds until neither raised a new issue (6 rounds); disagreements were re-read and decided by written rules (prompts/implementation_records/coding_audit). The author verified the process; inter-rater agreement between human raters was not assessed."),
                 ("Definitional differences", "Some items are stricter than the related raw columns, so their counts differ by design: RC09 needs counts per selection step (raw traceability needs the five items present); RC30 needs the data partition of the AUROC; RC31 needs the applied cutoff; RC33 also accepts SDs; RC43 excludes rankings of separately built subgroup models (raw VI16 counts them, Supplementary Table S6). A decision-tree diagram or its split variables alone is not a variable-importance ranking (raw VI01 corrected for KHM224, KHM241, KHM252 in the coding audit)."),
                 ("Raw codes", "The protocol codes from which items were derived remain in the other columns of the Additional Data 1 sheet, so not reporting can be told apart from a step not performed.")]:
        sd.append(list(line))
    for sh, widths in ((cb, [7, 34, 32, 60, 30, 34, 12, 20, 60, 12]), (sd, [26, 120])):
        for c in sh[1]:
            c.font = Font(bold=True); c.fill = HDR
        for i, w in enumerate(widths):
            sh.column_dimensions[chr(65 + i)].width = w
        for row in sh.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(OUT)
    print("RC columns added:", len(rows), "sheets:", wb.sheetnames)


if __name__ == "__main__":
    main()
