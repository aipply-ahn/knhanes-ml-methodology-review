#!/usr/bin/env python3
"""Build high-resolution recovery candidates from source PDF pages.

No OCR is used. Caption locations and PDF image geometry only choose a region;
every candidate remains pending direct image-model verification before it can
replace the canonical crop.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/visual_manual_review/manual_review_manifest.tsv"
OUT = ROOT / "data/visual_object_audit/recrop_candidates"
INDEX = OUT / "candidate_manifest.tsv"


def num_from_label(label: str) -> str:
    return label.split(":", 1)[-1].strip()


def caption_pattern(kind: str, num: str):
    n = re.escape(num).replace(r"\ ", r"\s*")
    lead = r"(?:figure|fig\.?|그림)" if kind == "figure" else r"(?:table|표)"
    return re.compile(rf"^\s*{lead}\s*\.?\s*{n}(?:\b|[.:])", re.I)


def find_caption(doc, row):
    kind, num = row["object_type"], num_from_label(row["object_label"])
    pat = caption_pattern(kind, num)
    claimed = int(row["page_or_sheet"]) - 1 if row["page_or_sheet"].isdigit() else None
    order = []
    if claimed is not None:
        order += [p for delta in (0, 1, -1, 2, -2, 3, -3) if 0 <= (p := claimed + delta) < len(doc)]
    order += [p for p in range(len(doc)) if p not in order]
    for pno in order:
        page = doc[pno]
        blocks = page.get_text("blocks", sort=True)
        for b in blocks:
            text = " ".join(str(b[4]).split())
            if pat.search(text):
                return pno, fitz.Rect(b[:4]), text
    return (claimed if claimed is not None and 0 <= claimed < len(doc) else 0), None, ""


def choose_figure_clip(page, caption):
    pr = page.rect
    infos = []
    for info in page.get_image_info():
        b = fitz.Rect(info["bbox"])
        area = b.width * b.height
        if area > pr.width * pr.height * .8 or area < pr.width * pr.height * .002:
            continue
        infos.append(b)
    if caption and infos:
        above = [b for b in infos if b.y1 <= caption.y1 + 8]
        if above:
            nearest = min(above, key=lambda b: max(0, caption.y0 - b.y1))
            gap = max(12, nearest.height * .12)
            group = [b for b in above if abs(b.y1 - nearest.y1) <= max(gap, 25) or
                     (b.y0 <= nearest.y1 + gap and b.y1 >= nearest.y0 - gap)]
            # Join strip-encoded artwork and adjacent multi-panel image blocks.
            clip = fitz.Rect(group[0])
            for b in group[1:]: clip |= b
            clip |= caption
            clip.x0 -= 8; clip.x1 += 8; clip.y0 -= 8; clip.y1 += 5
            return clip & pr, "embedded_image_geometry"
    if caption:
        # Safe uncut region for vector artwork. It may include nearby prose and
        # is therefore a candidate, not an automatically accepted final crop.
        return fitz.Rect(pr.x0 + 12, max(pr.y0, caption.y0 - pr.height * .55),
                         pr.x1 - 12, min(pr.y1, caption.y1 + 6)), "vector_safe_region"
    return pr, "caption_not_found_full_page"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    records = []
    for row in rows:
        src = ROOT / row["source_file"]
        if row["object_type"] != "figure" or src.suffix.lower() != ".pdf" or not src.exists():
            continue
        try:
            doc = fitz.open(src)
            pno, cap, cap_text = find_caption(doc, row)
            page = doc[pno]
            clip, method = choose_figure_clip(page, cap)
            dst = OUT / row["study_key"] / f"{row['object_id']}.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            page.get_pixmap(dpi=400, clip=clip, alpha=False).save(dst)
            doc.close()
            records.append({
                "object_id": row["object_id"], "study_key": row["study_key"],
                "source_pdf": row["source_file"], "ledger_page": row["page_or_sheet"],
                "located_pdf_page": pno + 1, "caption_found": "Y" if cap else "N",
                "caption_text": cap_text, "method": method,
                "clip_points": json.dumps([round(x, 3) for x in clip]), "dpi": 400,
                "candidate_path": str(dst.relative_to(ROOT)), "verification": "pending_direct_visual_review",
            })
        except Exception as e:
            records.append({"object_id": row["object_id"], "study_key": row["study_key"],
                "source_pdf": row["source_file"], "ledger_page": row["page_or_sheet"],
                "located_pdf_page": "", "caption_found": "N", "caption_text": "", "method": "ERROR",
                "clip_points": "", "dpi": 400, "candidate_path": "", "verification": f"error: {e}"})
    with INDEX.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(records)
    from collections import Counter
    print({"candidates": len(records), "methods": dict(Counter(r["method"] for r in records))})


if __name__ == "__main__":
    main()
