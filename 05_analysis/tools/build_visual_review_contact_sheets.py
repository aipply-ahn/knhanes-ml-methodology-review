#!/usr/bin/env python3
"""Build labelled contact sheets for direct image-model review (no OCR)."""
from __future__ import annotations

import csv
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/visual_manual_review/manual_review_manifest.tsv"
OUT = ROOT / "data/visual_manual_review/contact_sheets"
COLS, ROWS = 3, 3
CELL_W, CELL_H, LABEL_H = 900, 700, 76


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    font = ImageFont.load_default(size=24)
    index_rows = []
    for batch_no in range(math.ceil(len(rows) / (COLS * ROWS))):
        batch = rows[batch_no * COLS * ROWS:(batch_no + 1) * COLS * ROWS]
        sheet = Image.new("RGB", (COLS * CELL_W, ROWS * CELL_H), "white")
        draw = ImageDraw.Draw(sheet)
        for pos, row in enumerate(batch):
            col, line = pos % COLS, pos // COLS
            x0, y0 = col * CELL_W, line * CELL_H
            path = ROOT / "data/visual_manual_review" / row["review_image"]
            with Image.open(path) as im0:
                im = im0.convert("RGB")
                im.thumbnail((CELL_W - 20, CELL_H - LABEL_H - 20), Image.Resampling.LANCZOS)
            x = x0 + (CELL_W - im.width) // 2
            y = y0 + LABEL_H + (CELL_H - LABEL_H - im.height) // 2
            sheet.paste(im, (x, y))
            color = "#b2182b" if row["review_status"] == "unreadable" else "#b35806"
            draw.rectangle((x0, y0, x0 + CELL_W - 1, y0 + CELL_H - 1), outline=color, width=5)
            label = f"{batch_no+1:03d}-{pos+1}  {row['object_id']}  [{row['review_status']}]"
            draw.text((x0 + 12, y0 + 12), label, fill="black", font=font)
            index_rows.append({"sheet": f"sheet_{batch_no+1:03d}.jpg", "slot": pos + 1,
                               "object_id": row["object_id"], "review_status": row["review_status"],
                               "object_type": row["object_type"], "source_file": row["source_file"],
                               "page_or_sheet": row["page_or_sheet"]})
        sheet.save(OUT / f"sheet_{batch_no+1:03d}.jpg", quality=92, subsampling=0)
    with (OUT / "index.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(index_rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(index_rows)
    print({"objects": len(rows), "sheets": math.ceil(len(rows)/(COLS*ROWS)), "grid": f"{COLS}x{ROWS}"})


if __name__ == "__main__":
    main()
