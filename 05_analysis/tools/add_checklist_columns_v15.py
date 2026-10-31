"""v15 (author 2026-10-28): append the core checklist judgements RC01-RC45 to Additional Data 1, so the workbook, Table 1
and Figure 5 are aligned. Core rows get 1 (met), 0 (not met) or NA; other rows stay blank. Header comments give the
criterion and the source (existing coding or full-text reading). Called at the end of build_data1_workbook.py."""
import json, sys
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, Alignment
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx"


def main():
    import checklist_v15_table as TB
    t = json.load(open(ROOT / "results/derived/checklist_v15_scores.json"))
    assert not t["missing_recode"], f"recoding incomplete: {len(t['missing_recode'])} studies"
    idx = {i["id"]: str(i["idx"]) for i in t["items"]}
    wb = load_workbook(OUT); ws = wb.active
    hdr = [c.value for c in ws[1]]
    if any(str(h).startswith("RC01") for h in hdr):  # rerun: replace the RC block
        k0 = next(i for i, h in enumerate(hdr) if str(h).startswith("RC01"))
        ws.delete_cols(k0 + 1, len(hdr) - k0)
        hdr = hdr[:k0]
    col0 = len(hdr) + 1
    rows = TB.ordered()
    for k, r in enumerate(rows):
        c = ws.cell(row=1, column=col0 + k, value=f"{r[0]} {r[3]}")
        c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical="top")
        src = "existing coding" if r[8] == "E" else "full-text reading (v15)"
        c.comment = Comment(f"Core checklist item {r[0]} (Table 1). Met (1) if: {r[5]} NA = not applicable. Source: {src}.", "Additional Data 1", width=320, height=120)
    for row in range(2, ws.max_row + 1):
        sid = ws.cell(row=row, column=1).value
        st = t["studies"].get(sid)
        if not st:
            continue
        for k, r in enumerate(rows):
            v = st["items"].get(idx[r[0]])
            ws.cell(row=row, column=col0 + k, value="NA" if v is None else int(v))
        ws.cell(row=row, column=col0 + len(rows), value=" | ".join(f"{k}: {e}" for k, e in st["evidence"].items())[:32000])
    c = ws.cell(row=1, column=col0 + len(rows), value="Core checklist evidence (full-text items)")
    c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical="top")
    c.comment = Comment("Short quotes from the full text supporting the judgements of the items read in the v15 recoding "
                        "(RC04, RC05, RC06, RC12, RC16, RC19, RC23, RC24, RC32, RC38, RC40, RC42, RC44, RC45).", "Additional Data 1", width=320, height=100)
    wb.save(OUT)
    print("RC columns added:", len(rows))


if __name__ == "__main__":
    main()
