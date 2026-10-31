#!/usr/bin/env python3
"""Prompt 115/118: the three submission files, alone in paper/ (sources and working files are in manuscript/).

    KNHANES_ML_review_Main.pdf              manuscript without the appended supplement (build/submission/bmc_main.pdf)
    KNHANES_ML_review_Supplementary.pdf     Additional file 1: Supplementary Tables S1-S8 and Figures S1-S8
    KNHANES_ML_review_Additional_Data_1.xlsx Additional file 2: Additional Data 1 (tools/build_data1_workbook.py)

manuscript/bmc_main.pdf (manuscript + supplement, for reading) and manuscript/bmc_supplementary_data1.xlsx (full coding log) stay
as working files. MANIFEST.tsv records size, pages and sha256 of each submission file.
"""
import hashlib
import shutil
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper"  # prompt 118: paper/ holds only the final files
MANIFEST = ROOT / "manuscript/submission_MANIFEST.tsv"
FILES = [("KNHANES_ML_review_Main.pdf", ROOT / "build/submission/bmc_main.pdf", "Main manuscript"),
         ("KNHANES_ML_review_Supplementary.pdf", ROOT / "manuscript/bmc_supplementary.pdf", "Additional file 1: Supplementary Tables S1-S8 and Figures S1-S8"),
         ("KNHANES_ML_review_Additional_Data_1.xlsx", OUT / "KNHANES_ML_review_Additional_Data_1.xlsx", "Additional file 2: Additional Data 1, coded data of the review")]


def main():
    raise SystemExit("superseded 2026-10-24: the current submission is built by paper/src/Makefile (make); "
                     "the BMC files are in paper_backup/BMC_MRM_20261024/")
    OUT.mkdir(exist_ok=True)
    rows = ["file\trole\tbytes\tpages\tsha256"]
    for name, src, role in FILES:
        dst = OUT / name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        b = dst.read_bytes()
        pages = len(fitz.open(dst)) if name.endswith(".pdf") else ""
        if name == "KNHANES_ML_review_Main.pdf":
            with fitz.open(dst) as d:  # the submitted manuscript must not carry the appended supplement
                assert "Supplementary contents" not in " ".join(p.get_text() for p in d), "supplement appended to main"
        rows.append(f"{name}\t{role}\t{len(b)}\t{pages}\t{hashlib.sha256(b).hexdigest()}")
    stray = sorted(p.name for p in OUT.iterdir() if p.name not in {n for n, _, _ in FILES})
    assert not stray, stray
    MANIFEST.write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
