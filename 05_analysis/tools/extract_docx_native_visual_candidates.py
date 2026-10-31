#!/usr/bin/env python3
"""Extract native DOCX media for flagged figures without OCR."""
from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data/visual_manual_review/manual_review_manifest.tsv"
OUT = ROOT / "data/visual_object_audit/docx_native_candidates"
INDEX = OUT / "docx_native_candidate_manifest.tsv"
SHEET = OUT / "docx_native_media_contact_sheet.jpg"


def main():
    with MANUAL.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t") if r["source_file"].endswith(".docx")]
    by_source = defaultdict(list)
    for r in rows:
        by_source[r["source_file"]].append(r)
    source_media = {}
    tiles = []
    for source in sorted(by_source):
        study = by_source[source][0]["study_key"]
        destdir = OUT / study
        destdir.mkdir(parents=True, exist_ok=True)
        extracted = []
        with ZipFile(ROOT / source) as z:
            for member in sorted(n for n in z.namelist() if n.startswith("word/media/") and not n.endswith("/")):
                ext = Path(member).suffix.lower()
                raw = destdir / Path(member).name
                with z.open(member) as src, raw.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                display = raw
                if ext in {".tif", ".tiff"}:
                    display = raw.with_suffix(".png")
                    with Image.open(raw) as im:
                        im.seek(0); im.convert("RGB").save(display)
                extracted.append(str(display.relative_to(ROOT)))
                try:
                    with Image.open(display) as im:
                        thumb = ImageOps.contain(im.convert("RGB"), (520, 390))
                    tile = Image.new("RGB", (540, 440), "white")
                    tile.paste(thumb, ((540-thumb.width)//2, 36+(390-thumb.height)//2))
                    ImageDraw.Draw(tile).text((8, 8), f"{study} / {Path(member).name}", fill="black")
                    tiles.append(tile)
                except Exception:
                    pass
        source_media[source] = extracted

    records = []
    for r in rows:
        media = source_media[r["source_file"]]
        records.append({
            "object_id": r["object_id"], "study_key": r["study_key"],
            "object_label": r["object_label"], "source_docx": r["source_file"],
            "native_media_count": len(media), "native_media_candidates": json.dumps(media, ensure_ascii=False),
            "review_status": "native_media_extracted_pending_object_match" if media else "no_embedded_media_in_docx",
            "ocr_engine_used": "N",
        })
    with INDEX.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(records)
    if tiles:
        cols = 3; rows_n = (len(tiles)+cols-1)//cols
        canvas = Image.new("RGB", (540*cols, 440*rows_n), "white")
        for i, tile in enumerate(tiles):
            canvas.paste(tile, ((i%cols)*540, (i//cols)*440))
        canvas.save(SHEET, quality=94)
    print({"flagged_docx_objects": len(records), "native_media": len(tiles),
           "manifest": str(INDEX.relative_to(ROOT)), "contact_sheet": str(SHEET.relative_to(ROOT))})


if __name__ == "__main__":
    main()
