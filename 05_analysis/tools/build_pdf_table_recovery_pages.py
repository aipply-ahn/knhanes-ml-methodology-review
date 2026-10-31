#!/usr/bin/env python3
"""Render high-resolution source pages for every flagged PDF table.

The output is intentionally page-complete so wide tables and continuations are
not silently clipped. Caption matching uses native PDF text only; no OCR.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from zipfile import ZipFile

import fitz

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/visual_manual_review/manual_review_manifest.tsv"
OUT = ROOT / "data/visual_object_audit/table_recovery_pages"
INDEX = OUT / "table_recovery_manifest.tsv"


def pattern(label: str):
    num = re.escape(label.split(":", 1)[-1].strip()).replace(r"\ ", r"\s*")
    return re.compile(rf"^\s*(?:supplementary\s+)?(?:table|표)\s*\.?\s*{num}(?:\b|[.:])", re.I)


def locate(doc, row):
    pat = pattern(row["object_label"])
    claimed = int(row["page_or_sheet"]) - 1 if row["page_or_sheet"].isdigit() else None
    order = []
    if claimed is not None:
        order += [p for d in (0, 1, -1, 2, -2, 3, -3) if 0 <= (p := claimed + d) < len(doc)]
    order += [p for p in range(len(doc)) if p not in order]
    for pno in order:
        for b in doc[pno].get_text("blocks", sort=True):
            txt = " ".join(str(b[4]).split())
            if pat.search(txt):
                return pno, txt
    return (claimed if claimed is not None and 0 <= claimed < len(doc) else 0), ""


def open_source(source_file: str):
    if "::" not in source_file:
        return fitz.open(ROOT / source_file)
    archive, member = source_file.split("::", 1)
    with ZipFile(ROOT / archive) as z:
        return fitz.open(stream=z.read(member), filetype="pdf")


def main():
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t")
                if r["object_type"] == "table" and r["source_file"].lower().endswith(".pdf")]
    records = []
    for r in rows:
        doc = open_source(r["source_file"])
        pno, cap = locate(doc, r)
        page = doc[pno]
        # Trim only the printer margin; retain the full page body to guarantee
        # that wide tables, notes, and continuation markers remain present.
        m = 10
        clip = fitz.Rect(page.rect.x0 + m, page.rect.y0 + m,
                         page.rect.x1 - m, page.rect.y1 - m)
        dst = OUT / r["study_key"] / f"{r['object_id']}__source_page.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(dpi=350, clip=clip, alpha=False).save(dst)
        doc.close()
        records.append({
            "object_id": r["object_id"], "study_key": r["study_key"],
            "source_pdf": r["source_file"], "ledger_page": r["page_or_sheet"],
            "located_pdf_page": pno + 1, "caption_found": "Y" if cap else "N",
            "caption_text": cap, "initial_vision_status": r.get("chatgpt_vision_status", ""),
            "render_dpi": 350, "page_image_path": str(dst.relative_to(ROOT)),
            "review_status": "source_page_recovered_no_ocr",
        })
    with INDEX.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(records)
    print({"tables": len(records), "caption_found": sum(r["caption_found"] == "Y" for r in records),
           "output": str(INDEX.relative_to(ROOT))})


if __name__ == "__main__":
    main()
