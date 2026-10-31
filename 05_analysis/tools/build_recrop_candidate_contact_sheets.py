#!/usr/bin/env python3
"""Build 3x3 contact sheets for direct verification of recrop candidates."""
import csv, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/visual_object_audit/recrop_candidates/candidate_manifest.tsv"
OUT = ROOT / "data/visual_object_audit/recrop_candidates/contact_sheets"
CW, CH, LH = 900, 700, 82

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with SRC.open(encoding="utf-8-sig", newline="") as f: rows=[r for r in csv.DictReader(f,delimiter="\t") if r["candidate_path"]]
    font=ImageFont.load_default(size=22)
    for bn in range(math.ceil(len(rows)/9)):
        sheet=Image.new("RGB",(2700,2100),"white"); d=ImageDraw.Draw(sheet)
        for pos,r in enumerate(rows[bn*9:(bn+1)*9]):
            x0=(pos%3)*CW; y0=(pos//3)*CH
            with Image.open(ROOT/r["candidate_path"]) as z:
                im=z.convert("RGB"); im.thumbnail((CW-18,CH-LH-18),Image.Resampling.LANCZOS)
            sheet.paste(im,(x0+(CW-im.width)//2,y0+LH+(CH-LH-im.height)//2))
            d.rectangle((x0,y0,x0+CW-1,y0+CH-1),outline="#4d4d4d",width=4)
            d.text((x0+10,y0+8),f"{bn+1:03d}-{pos+1} {r['object_id']}",fill="black",font=font)
            d.text((x0+10,y0+38),f"{r['method']} p{r['located_pdf_page']} (ledger {r['ledger_page']})",fill="#333399",font=font)
        sheet.save(OUT/f"sheet_{bn+1:03d}.jpg",quality=92,subsampling=0)
    print({"candidates":len(rows),"sheets":math.ceil(len(rows)/9)})

if __name__=="__main__": main()
