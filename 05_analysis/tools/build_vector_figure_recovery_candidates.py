#!/usr/bin/env python3
"""Recover vector-drawn PDF figures using drawing geometry, without OCR."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/visual_object_audit/recrop_candidates/candidate_manifest.tsv"
OUT = ROOT / "data/visual_object_audit/vector_recrop_candidates"
INDEX = OUT / "vector_candidate_manifest.tsv"
SHEETS = OUT / "contact_sheets"


def cap_pattern(text):
    m = re.match(r"\s*((?:figure|fig\.?|그림)\s*\.?\s*[^\s.:]+)", text, re.I)
    return re.compile(r"^\s*" + re.escape(m.group(1)), re.I) if m else None


def find_caption(page, caption_text):
    pat = cap_pattern(caption_text)
    for b in page.get_text("blocks", sort=True):
        txt = " ".join(str(b[4]).split())
        if (pat and pat.search(txt)) or (caption_text and txt.startswith(caption_text[:35])):
            return fitz.Rect(b[:4])
    return None


def vector_clip(page, cap):
    pr = page.rect
    if cap is None: return pr, 0
    rects = []
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if r.width * r.height < 2 or r.y0 < 35 or r.y1 > cap.y1 + 3:
            continue
        if r.y1 < cap.y0 - pr.height * .68:
            continue
        # Ignore journal separator rules unless they intersect other artwork.
        if r.height < 1.5 and r.width > pr.width * .72:
            continue
        rects.append(r)
    if not rects: return pr, 0
    nearest = max(r.y1 for r in rects if r.y1 <= cap.y1 + 3)
    selected = [r for r in rects if r.y1 >= nearest - pr.height * .58]
    clip = fitz.Rect(selected[0])
    for r in selected[1:]: clip |= r
    # Include text labels within and immediately around the drawing assembly.
    for b in page.get_text("blocks", sort=True):
        br = fitz.Rect(b[:4])
        if br.y0 <= cap.y0 and br.y1 >= clip.y0 - 12 and br.x1 >= clip.x0 - 12 and br.x0 <= clip.x1 + 12:
            clip |= br
    clip |= cap
    clip.x0 -= 10; clip.x1 += 10; clip.y0 -= 10; clip.y1 += 6
    return clip & pr, len(selected)


def main():
    with SRC.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t") if r["method"] == "vector_safe_region"]
    records=[]; tiles=[]
    for r in rows:
        doc=fitz.open(ROOT/r["source_pdf"]); page=doc[int(r["located_pdf_page"])-1]
        cap=find_caption(page,r["caption_text"]); clip,n=vector_clip(page,cap)
        dst=OUT/r["study_key"]/f"{r['object_id']}.png"; dst.parent.mkdir(parents=True,exist_ok=True)
        page.get_pixmap(dpi=450,clip=clip,alpha=False).save(dst); doc.close()
        records.append({"object_id":r["object_id"],"study_key":r["study_key"],"source_pdf":r["source_pdf"],
                        "pdf_page":r["located_pdf_page"],"caption_found":"Y" if cap else "N",
                        "drawing_count":n,"clip_points":json.dumps([round(x,2) for x in clip]),
                        "dpi":450,"candidate_path":str(dst.relative_to(ROOT)),
                        "verification":"pending_direct_visual_review"})
        with Image.open(dst) as im: thumb=ImageOps.contain(im.convert("RGB"),(570,390))
        tile=Image.new("RGB",(590,440),"white"); tile.paste(thumb,((590-thumb.width)//2,42+(390-thumb.height)//2))
        ImageDraw.Draw(tile).text((8,8),r["object_id"],fill="black"); tiles.append(tile)
    with INDEX.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(records)
    SHEETS.mkdir(parents=True,exist_ok=True)
    for s in range((len(tiles)+8)//9):
        canvas=Image.new("RGB",(1770,1320),"white")
        for j,tile in enumerate(tiles[s*9:(s+1)*9]): canvas.paste(tile,((j%3)*590,(j//3)*440))
        canvas.save(SHEETS/f"sheet_{s+1:03d}.jpg",quality=94)
    print({"vector_candidates":len(records),"sheets":(len(tiles)+8)//9,"manifest":str(INDEX.relative_to(ROOT))})


if __name__ == "__main__": main()
