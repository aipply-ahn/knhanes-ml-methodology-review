#!/usr/bin/env python3
"""Build 3x3 sheets for every still-pending recovered visual (no OCR)."""
from __future__ import annotations
import csv, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv"
OUT = ROOT / "data/visual_manual_review/latest_after_recrop/pending_reread_contact_sheets"
COLS = ROWS = 3
CW, CH, LH = 1000, 760, 72


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    with LEDGER.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t")
                if r["scientific_interpretation_status"] ==
                "REINTERPRETATION_REQUIRED_FOR_NEWLY_EXPOSED_CONTENT"]
    font = ImageFont.load_default(size=21)
    idx = []
    for typ in ("figure", "table"):
        subset = [r for r in rows if r["object_type"] == typ]
        dest = OUT / typ; dest.mkdir()
        for n in range(0, len(subset), 9):
            batch = subset[n:n+9]
            sheet = Image.new("RGB", (COLS*CW, ROWS*CH), "white")
            draw = ImageDraw.Draw(sheet)
            sheet_no = n//9 + 1
            for j, row in enumerate(batch):
                x0, y0 = (j%COLS)*CW, (j//COLS)*CH
                p = ROOT / row["latest_review_image"]
                try:
                    with Image.open(p) as src:
                        im = src.convert("RGB")
                        im.thumbnail((CW-20, CH-LH-20), Image.Resampling.LANCZOS)
                    sheet.paste(im, (x0+(CW-im.width)//2,
                                     y0+LH+(CH-LH-im.height)//2))
                    note = ""
                except Exception as exc:
                    note = f"OPEN ERROR: {type(exc).__name__}"
                draw.rectangle((x0,y0,x0+CW-1,y0+CH-1), outline="#8c2d04", width=4)
                label = f"{j+1}: {row['object_id']} | {row['latest_image_kind']}"
                draw.text((x0+10,y0+10), label, fill="black", font=font)
                if note: draw.text((x0+10,y0+38), note, fill="red", font=font)
                idx.append({"object_type":typ,"sheet":f"{typ}/sheet_{sheet_no:03d}.jpg",
                            "slot":j+1,"object_id":row["object_id"],
                            "image_path":row["latest_review_image"]})
            sheet.save(dest/f"sheet_{sheet_no:03d}.jpg", quality=94, subsampling=0)
    with (OUT/"index.tsv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(idx[0]),delimiter="\t",lineterminator="\n")
        w.writeheader();w.writerows(idx)
    print({t:len([r for r in rows if r['object_type']==t]) for t in ('figure','table')})
    print({'sheets':len(list(OUT.glob('*/*.jpg')))})

if __name__ == "__main__": main()
